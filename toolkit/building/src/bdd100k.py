import os
import threading
import json
import random

# function for generating unique ids
#####################################
def uniqueid():
    seed = random.getrandbits(20)
    while True:
       yield seed
       seed += 1
#####################################

class BDD100KToolKit:
    def __init__(self, labels_json=None, labels_dir=None, timeofday_list=None):

        self.get_id = uniqueid()
        
        self.labels_dir = labels_dir
        self.labels_json = labels_json
        self.timeofday_list = timeofday_list # è la lista che contiene le info rigurdanti il 'timeofday' di ogni video
        
        self.json_dictionaries = []
        
    def list_json_videos(self):
        l = []
        for file in os.listdir(self.labels_dir):
            if file.endswith(".json"):
                l.append(file)
        return l
        
    def build_labels(self, json_video, index):
        
            d = json.load(open(self.labels_dir+"/"+json_video))
            name_video = d[0]["videoName"]
            timeofday = None
            for i in range(len(self.timeofday_list)):
                if self.timeofday_list[i]["video_name"] == name_video:
                    timeofday = self.timeofday_list.pop(i)["timeofday"]
                    break
            totalFrames = d[-1]["frameIndex"] + 1
            #self.update_json_video(name_video, totalFrames, i)

            list_image = []
            for image_dict in d:
                name_image = name_video +"/" + image_dict["name"]
                image_id = next(self.get_id)
                width = 1280
                height = 720
                list_image.append({"id" : image_id, "file_name" : name_image, "video_id" : name_video, "width" : width, "height" : height, "dataset" : "bdd100k", "timeofday" : timeofday})
                list_labels = []
                for label in image_dict["labels"]:
                    if label["category"] == "car" or label["category"] == "truck" or label["category"] == "bus" or label["category"] == "pedestrian" or label["category"] == "rider" or label["category"] == "other person"  or label["category"] == "motorcycle":
                        if label["attributes"]["truncated"] == False and label["attributes"]["crowd"] == False:
                            id = label["id"]
                            # (x1,y1) è l'angolo sx di sopra e (x2,y2) quello dx di sotto.
                            x1 = label["box2d"]["x1"]
                            y1 = label["box2d"]["y1"]
                            x2 = label["box2d"]["x2"]
                            y2 = label["box2d"]["y2"]
                            w = x2-x1
                            h = y2-y1
                            bbox = [x1, y1, w, h]
                            if label["category"] == "car" or label["category"] == "truck" or label["category"] == "bus":
                                cat_id = 0
                            elif label["category"] == "pedestrian" or label["category"] == "rider" or label["category"] == "other person":
                                cat_id = 1
                            elif label["category"] == "motorcycle":
                                cat_id = 2
                            list_labels.append({"id" : id, "image_id" : image_id, "category_id" : cat_id, "bbox" :  bbox})
                self.update_json_annotation(list_labels, index)
            self.update_json_image(list_image, index)
           
        
    def bdd100k_building(self):
        
        iteration = 0
        list_json_videos = self.list_json_videos()
        num_json_video = len(list_json_videos)
        
        num_dictionaries = int(num_json_video/100)
        for _ in range(num_dictionaries):
            self.json_dictionaries.append(json.load(open(self.labels_json)))
        print("----------- We created {} 'support dictionaries' to improve efficiency -----------".format(len(self.json_dictionaries)))
            
        for json_video in list_json_videos: # 1400 videos
            json_dict_index = int(iteration/100)
            iteration = iteration + 1
            num_json_video = num_json_video - 1
            print("^^^^^^^^^^^^^^^^^^^^^^ Starting processing {} ^^^^^^^^^^^^^^^^^^^^^^".format(json_video))
            if num_json_video != 0:
                print("^^^^^^^^^^^^^^^^^^^^^^     {} json files left     ^^^^^^^^^^^^^^^^^^^^^^".format(num_json_video))
            else:
                print("^^^^^^^^^^^^^^^^^^^^^^  Last json file to process ^^^^^^^^^^^^^^^^^^^^^^")
                
            t = threading.Thread(target=self.build_labels, args=[json_video, json_dict_index])
            t.start()
            t.join()
                
            if iteration == 1500:
                break
            
        print("################# Processing is Finished ;) #################")
        print("Number of processed json files: {}".format(iteration))
        print("loading the new label_json file...")
        d = self.json_dictionaries[0]
        for dict in self.json_dictionaries[1:]:
            #d["videos"] = d["videos"] + dict["videos"]
            d["images"] = d["images"] + dict["images"]
            d["annotations"] = d["annotations"] + dict["annotations"]
        f = open(self.labels_json, "w")
        json.dump(d, f)
        print("Done!")    
            
    #def update_json_video(self, name, num_frames, i, time_of_day=None):
    #   self.json_dictionaries[i]["videos"].append({"id" : name, "num_frames" : num_frames, "time" : time_of_day})
        
    def update_json_image(self, list, i):
        self.json_dictionaries[i]["images"] = self.json_dictionaries[i]["images"] + list
        
    def update_json_annotation(self, list, i):
        self.json_dictionaries[i]["annotations"] = self.json_dictionaries[i]["annotations"] + list