import time
import threading
from datetime import timedelta
import WaymoOpenDataset

if __name__=="__main__":

    training_dir = "/content/drive/MyDrive/VISIOPE/Project/dataset/training/tfrecord" # provide directory where .tfrecords are stored
    save_dir = "/content/drive/MyDrive/VISIOPE/Project/dataset/training/processed" # provide a directory where data should be extracted

    toolkit = WaymoOpenDataset.ToolKit(training_dir=training_dir, save_dir=save_dir)

    for segment in toolkit.list_training_segments(): # mi creo una lista di segmenti...
        toolkit.assign_segment(segment)
        
        # facciamo partire due thread (nel mio caso ne basta uno)
        threads = []
        start = time.time()
        t1 = threading.Thread(target=toolkit.extract_camera_images) # questo processo salva il dataset nel formato che desideriamo
        #t2 = threading.Thread(target=toolkit.extract_laser_images)
        t1.start()
        #t2.start()
        threads.append(t1)
        #threads.append(t2)
        for thread in threads:
            thread.join()
        end = time.time()
        elapsed = end - start
        
        toolkit.save_video()
        toolkit.consolidate()
        print(timedelta(seconds=elapsed))
        break # in questo modo processo un solo segmento