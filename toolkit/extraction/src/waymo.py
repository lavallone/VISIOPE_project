import os
import glob
import shutil
import threading
from typing_extensions import dataclass_transform
import numpy as np
import json
from json.decoder import JSONDecodeError
import cv2
from urllib.parse import urlparse
import tensorflow.compat.v1 as tf
tf.enable_eager_execution()

from google.protobuf.json_format import MessageToDict # utile per manipolare i proto buffers

from waymo_open_dataset.utils import  frame_utils
from waymo_open_dataset import dataset_pb2 as open_dataset

class WaymoToolKit:
    def __init__(self, tfrecord_dir=None,  images_dir=None, labels_json=None, image_or_label="label"):

        self.segment = None
        
        self.tfrecord_dir = tfrecord_dir
        self.images_dir = images_dir
        self.labels_json = labels_json
        
        self.image_or_label = image_or_label
        self.images_seg_dir = None
        self.json_dictionary = json.load(open(labels_json)) # vedere se funziona

        self.camera_list = ["UNKNOWN", "FRONT", "FRONT_LEFT", "FRONT_RIGHT", "SIDE_LEFT", "SIDE_RIGHT"]

    def assign_segment(self, segment):
        self.segment = segment
        self.dataset = tf.data.TFRecordDataset("{}/{}".format(self.tfrecord_dir, self.segment), compression_type='')

    def list_segments(self):
        seg_list = []
        for file in os.listdir(self.tfrecord_dir):
            if file.endswith(".tfrecord"):
                seg_list.append(file)
        return seg_list
    
    # Extract Camera Image
    def extract_image(self, ndx, frame):
        l = []
        for data in frame.images:
            decodedImage = tf.io.decode_jpeg(data.image, channels=3, dct_method='INTEGER_ACCURATE')
            decodedImage = cv2.cvtColor(decodedImage.numpy(), cv2.COLOR_RGB2BGR)
            if self.camera_list[data.name]=="FRONT" or  self.camera_list[data.name]=="FRONT_LEFT" or self.camera_list[data.name]=="FRONT_RIGHT":
                cv2.imwrite("{}/{}_{}.png".format(self.images_seg_dir, ndx, self.camera_list[data.name]), decodedImage)
                l.append({"name" : ndx + "_" + self.camera_list[data.name]+".png", "name_video" : self.segment[:-28], "width" : frame.context.camera_calibrations.width, "height" : frame.context.camera_calibrations.height})
        self.update_json_image(l)

    # Extract Camera Label
    def extract_labels(self, ndx, frame): # ogni volta devo aggiungere una label
        l=[]
        for data in frame.camera_labels:
            camera = MessageToDict(data) # converte dal .proto file
            camera_name = camera["name"]
            if camera_name=="FRONT" or  camera_name=="FRONT_LEFT" or camera_name=="FRONT_RIGHT":
                labels = camera["labels"]
                for label in labels: # iteriamo sulle labels di una singola immagine
                    if label["type"] == "TYPE_VEHICLE" or label["type"] == "TYPE_PEDESTRIAN" or label["type"] == "TYPE_CYCLIST":
                        x = label["box"]["centerX"]
                        y = label["box"]["centerY"]
                        width = label["box"]["width"]
                        length = label["box"]["length"]
                        x = x - 0.5 * length
                        y = y - 0.5 * width
                        if label["type"] == "TYPE_VEHICLE":
                            cat = "car"
                        elif label["type"] == "TYPE_PEDESTRIAN":
                            cat = "pedestrian"
                        else:
                            cat = "bicycle"
                        id = label["id"]
                        bbox = [x, y, length, width]
                        name_image = ndx + "_" + camera_name + ".png"
                        l.append({"id" : id, "name_image" : name_image, "bbox" :  bbox, "category" : cat})
        self.update_json_annotation(l)
               
    
    # Implemented Extraction as Threads
    def camera_image_extraction_thread(self, datasetAsList, range_value, totalFrames):
        
        frame = open_dataset.Frame() # estraggo il Frame
        
        for frameIdx in range_value:
            print("*************** processing frame {} ***************".format(frameIdx))
            frame.ParseFromString(datasetAsList[frameIdx])
            if frameIdx == 0: # aggiungo le informazioni del 'video' solo una volta!
                self.update_json_video(self.segment[:-28], totalFrames, frame.context.time_of_day, frame.context.weather)
            if self.image_or_label == "image":
                self.extract_image(frameIdx, frame)
            elif self.image_or_label == "label":
                self.extract_labels(frameIdx, frame)

    # Function to call to extract images
    def extract_camera_images(self): # we're processing only one segment
        
        self.images_seg_dir = self.images_dir + "/" + self.segment[:-28]
        
        if not os.path.exists(self.images_seg_dir):
            os.makedirs(self.images_seg_dir)
            
        print("cleaning directory from previous images...")
        # clear images from previous executions
        self.clean_directory(glob.glob('{}/**/*.png'.format(self.images_seg_dir), recursive=True))
        print("Done!")

        # Convert tfrecord to a list
        datasetAsList = list(self.dataset.as_numpy_iterator()) # lista dei frame relativi a un 'segment'
        totalFrames = len(datasetAsList)

        threads = []
        for i in self.batch(range(totalFrames), 30): # ogni thread si occupa di 30 frame alla volta
            t = threading.Thread(target=self.camera_image_extraction_thread, args=[datasetAsList, i, totalFrames])
            t.start()
            threads.append(t)
        
        for thread in threads:
            thread.join()

    def waymo_extraction(self):
        
        ##############  REMINDER !!!! #################
        # The segments that will be processed are the #
        # ones 'listed' in the "tfrecord_dir" folder. #
        # (both for image and label extraction)       #
        
        iteration = 0
        list_segments = self.list_segments() # list of segments stored in 'tfrecord_dir'
        num_segments = len(list_segments)
            
        for segment in list_segments:
            iteration = iteration + 1
            num_segments = num_segments - 1
            print("^^^^^^^^^^^^^^^^^^^^^^ Starting processing |{}| ^^^^^^^^^^^^^^^^^^^^^^".format(segment[:-28]))
            if num_segments != 0:
                print("^^^^^^^^^^^^^^^^^^^^^^     {} segments left     ^^^^^^^^^^^^^^^^^^^^^^".format(num_segments))
            else:
                print("^^^^^^^^^^^^^^^^^^^^^^  Last segment to process ^^^^^^^^^^^^^^^^^^^^^^")
            self.assign_segment(segment)
                
            t = threading.Thread(target=self.extract_camera_images)
            t.start()
            t.join()
                
            if iteration == 100: # for controlling how many segments we're going to process
                break 
            
        print("################# Processing is Finished ;) #################")
        print("Number of processed segments: {}".format(iteration))
            
    ######## Util Functions ########

    def batch(self, iterable, n=1):
        l = len(iterable)
        for ndx in range(0, l, n):
            yield iterable[ndx:min(ndx + n, l)]
            
    def clean_directory(self, files):
        for f in files:
            try:
                os.remove(f)
            except OSError as e:
                print("Error: %s : %s" % (f, e.strerror))
                
    def update_json_video(self, name, num_frames, time_of_day, weather):
        d = self.json_dictionary
        d["videos"].append({"name" : name, "num_frames" : num_frames, "time" : time_of_day, "weather" :weather })
        self.json_dictionary = d
        
    def update_json_image(self, list):
        d = self.json_dictionary
        d["images"] = d["images"] + list
        self.json_dictionary = d
        
    def update_json_annotation(self, list):
        d = self.json_dictionary
        d["annotations"] = d["annotations"] + list
        self.json_dictionary = d