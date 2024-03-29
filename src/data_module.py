import os
from PIL import Image
from torchvision import transforms
from torch.utils.data import DataLoader, Dataset
import pytorch_lightning as pl
import json
import torch
from tqdm import tqdm
import albumentations as A
from numpy import asarray

class URBE_Dataset(Dataset):
	def __init__(self, dataset_dir: str, data_type: str, annotations_file_path, hparams):
		self.data = list()
		self.data_type = data_type
		self.dataset_dir = os.path.join(dataset_dir, self.data_type)
		self.annotations = json.load(open(annotations_file_path, "r"))
		self.hparams = hparams
		self.resize = transforms.Compose([
			transforms.Resize((self.hparams.img_size, self.hparams.img_size)),
		])
		if self.hparams.augmentation and self.data_type == "train": # a slightly image augmentation
				self.augmentation = A.Compose([A.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.0, p=0.4),
        									   A.VerticalFlip(p=0.5),
											   A.HorizontalFlip(p=0.5),
											   A.RandomBrightnessContrast(p=0.2),
											   A.Blur(p=0.05),
											   A.ChannelShuffle(p=0.05),
											  ], bbox_params=A.BboxParams(format='yolo', min_visibility=0.4, label_fields=['class_labels']))
		self.make_data()
	
	def make_data(self):
		# this function read the fresh downloaded dataset and make it ready for the training
		print(f"Loading {self.data_type} dataset...")
		images_folder = [os.path.join(self.dataset_dir,e) for e in os.listdir(self.dataset_dir)]
		max_number = round(self.hparams.max_number_images/8) if (self.data_type == "val" or self.data_type == "test") else self.hparams.max_number_images
		for file_name in tqdm(images_folder[:max_number]):
			image_id = (file_name.split("_")[-1])[:-4]
			img = self.resize(Image.open(file_name).convert('RGB')) # we only resize the PIL Image
			time = list(filter(lambda x: x["id"] == image_id, self.annotations["images"]))[0]["timeofday"]
			ann_list = list(filter(lambda x: x["image_id"] == image_id, self.annotations["annotations"]))
			labels = []
			for ann in ann_list:
				# we normalize the bounding boxes using the (xc, yc, w, h) format...
				x1 = ann["bbox"][0] / 1280
				y1 = ann["bbox"][1] / 720
				w = ann["bbox"][2] / 1280
				h = ann["bbox"][3] / 720
				xc = x1 + (w/2)
				yc = y1 + (h/2)
				# we skip these type of annotations in order to avoid future errors with albumentations (due to their internal bug)
				# see https://github.com/albumentations-team/albumentations/issues/922
				if x1+w>1 or y1+h>1:
					continue
				labels.append( [ann["category_id"], xc, yc, w, h] )
			self.data.append({"id" : image_id, "img" : img, "time" : time, "file_name" : file_name, "labels" : labels})
	
	def __len__(self):
		return len(self.data)

	def __getitem__(self, idx):
		## AUGMENTATION ## 
  		# is performed only on the training set
		if self.hparams.augmentation and self.data_type == "train": # a slightly image augmentation because the dataset is already heterogeneous!
			data_tmp = self.data[idx]			
			data_tmp["labels"] = torch.tensor(data_tmp["labels"])
   			# albumentations works with image numpy arrays
			augmentations = self.augmentation(image=asarray(data_tmp["img"]), bboxes=data_tmp["labels"][..., 1:].tolist(), class_labels=[e for e in data_tmp["labels"][..., 0].tolist()])
			data_tmp["img"] = augmentations["image"]
            # loss fx requires bboxes to be (class_idx,x,y,w,h)
			data_tmp["labels"] = []
			if len(augmentations["bboxes"]):
				# and restore the original order of bboxes
				data_tmp["labels"] = torch.cat((torch.tensor([[e] for e in augmentations["class_labels"]]), torch.tensor(augmentations["bboxes"])), dim=-1).tolist()
			return data_tmp
		else:
			return self.data[idx]

class URBE_DataModule(pl.LightningDataModule):
 
	def __init__(self, hparams: dict):
		super().__init__()
		self.save_hyperparameters(hparams, logger=False)
		self.totensor = transforms.Compose([
			# Converts a PIL Image or numpy.ndarray (H x W x C) in the range [0, 255] 
			# to a torch.FloatTensor of shape (C x H x W) in the range [0.0, 1.0]
			transforms.ToTensor()
		])

	def setup(self, stage=None):
		if not hasattr(self,"data_train"):
			# TRAIN
			self.data_train = URBE_Dataset(self.hparams.dataset_dir, "train", self.hparams.annotations_file_path, self.hparams)
			# VAL
			self.data_val = URBE_Dataset(self.hparams.dataset_dir, "val", self.hparams.annotations_file_path, self.hparams)
			# TEST
			self.data_test = URBE_Dataset(self.hparams.dataset_dir, "test", self.hparams.annotations_file_path, self.hparams)

	def train_dataloader(self):
		return DataLoader(
			self.data_train,
			batch_size=self.hparams.batch_size,
			shuffle=True,
			num_workers=self.hparams.n_cpu,
			collate_fn = self.collate,
			pin_memory=self.hparams.pin_memory,
			persistent_workers=True
		)

	def val_dataloader(self):
		return DataLoader(
			self.data_val,
			batch_size=self.hparams.batch_size,
			shuffle=False,
			num_workers=self.hparams.n_cpu,
			collate_fn = self.collate,
			pin_memory=self.hparams.pin_memory,
			persistent_workers=True
		)
  
	def test_dataloader(self):
		return DataLoader(
			self.data_test,
			batch_size=self.hparams.batch_size,
			shuffle=False,
			num_workers=self.hparams.n_cpu,
   			collate_fn = self.collate,
			pin_memory=self.hparams.pin_memory,
			persistent_workers=True
		)
  
	# we need a collate function because each image have a different number of bounding boxes
	def collate(self, batch):
		batch_out = dict()
		batch_out["id"] = [sample["id"] for sample in batch]
		batch_out["img"] = torch.stack([self.totensor(sample["img"]) for sample in batch], dim=0)
		batch_out["time"] = [sample["time"] for sample in batch]
		batch_out["file_name"] = [sample["file_name"] for sample in batch]
		max_number_bbox = torch.tensor([len(sample["labels"]) for sample in batch]).max()
		batch_out["labels"] = torch.stack( [ torch.tensor(sample["labels"] + [ [0,0,0,0,0] for _ in range(max_number_bbox - len(sample["labels"]))] ) for sample in batch] )
		return batch_out