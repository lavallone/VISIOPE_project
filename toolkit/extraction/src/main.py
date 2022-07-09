import argparse
import os
import json
import waymo
import bdd100k
from pycocotools.coco import COCO

def clean_json(coco, d, lookup_video):
    d["categories"] = [{"name" : "vehicle", "id" : 0}, {"name" : "person", "id" : 1}, {"name" : "two-wheeler", "id" : 2}]
    for img in coco.dataset["images"]:
        img["video_id"] = lookup_video[img["sid"]]
        img["file_name"] = img["video_id"] + "/" + img["name"]
        img.pop("sid",None)
        img.pop("fid",None)
        img.pop("name",None)
    d["images"] = coco.dataset["images"]
    #ann_ids = coco.getAnnIds(iscrowd=False) # andiamo ad allenare la rete solo con bboxes dove iscrowd=False
    ann_ids=[]
    for ann in coco.dataset["annotations"]:
        if ann["iscrowd"]==False:
            if ann["category_id"]==0 or ann["category_id"]==1 or ann["category_id"]==2 or ann["category_id"]==3 or ann["category_id"]==4 or ann["category_id"]==5:
                ann.pop("area",None)
                ann.pop("ignore",None)
                ann.pop("track",None)
                ann.pop("iscrowd",None)
                if ann["category_id"]==0: # quindi è una persona
                    ann["category_id"] = 1
                elif ann["category_id"]==2 or ann["category_id"]==4 or ann["category_id"]==5:
                    ann["category_id"] = 0
                else:
                    ann["category_id"] = 2
                ann_ids.append(ann["id"])
            else:
                continue
    d["annotations"] = coco.loadAnns(ann_ids)

if __name__=="__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=str)
    args = parser.parse_args()
    
    if args.dataset == "waymo":
        tfrecord_dir = "/content/drive/MyDrive/VISIOPE/Project/datasets/Waymo/images/train/tfrecord"
        images_dir = "/content/drive/MyDrive/VISIOPE/Project/datasets/Waymo/images/train/videos"
        labels_json = "/content/drive/MyDrive/VISIOPE/Project/datasets/Waymo/labels/train/train.json"
        
        toolkit = waymo.WaymoToolKit(tfrecord_dir=tfrecord_dir, images_dir=images_dir, labels_json=labels_json, image_or_label="label")
        toolkit.waymo_extraction()
        
    elif args.dataset == "bdd100k":
        labels_dir = "/content/drive/MyDrive/VISIOPE/Project/datasets/BDD100K/labels/train/old_json"
        labels_json = "/content/drive/MyDrive/VISIOPE/Project/datasets/BDD100K/labels/train/train_fast.json"
        
        toolkit = bdd100k.BDD100KToolKit(labels_dir=labels_dir, labels_json=labels_json)
        toolkit.bdd100k_extraction()
        
    elif args.dataset == "argoverse": # since the labels are COCO-like, we just need to clean the already existed json file!
        images_dir = "/content/drive/MyDrive/VISIOPE/Project/datasets/Argoverse/images/train/videos"
        old_labels_json = "/content/drive/MyDrive/VISIOPE/Project/datasets/Argoverse/labels/train/old_train.json"
        labels_json = "/content/drive/MyDrive/VISIOPE/Project/datasets/Argoverse/labels/train/train.json"

        
        d = {}
        coco = COCO(old_labels_json)
        list_videos = coco.dataset["sequences"] 
        d["info"] = coco.dataset["info"]
        d["videos"] = []
        lookup_video = {}
        for i, name_video in enumerate(list_videos):
            lookup_video[i] = name_video
            totalFrames = 0
            for f in os.listdir(images_dir+"/"+name_video):
                totalFrames = totalFrames + 1
            d["videos"].append({"id" : name_video, "num_frames" : totalFrames, "time" : None})
        # Ora che abbiamo agggiunto la sezione dei video al file 'json', possiamo iniziare a pulirlo un po'...
        print("cleaning 'old_train.json'...") 
        clean_json(coco, d, lookup_video)
        print("Done!")
        print("copying to 'train.json'...")
        json.dump(d, open(labels_json, "w"))
        print("Done!")
    else:
        pass