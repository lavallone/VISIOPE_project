from dataclasses import dataclass


@dataclass
class Hparams:
    # dataloader params
    dataset_dir: str = "dataset/URBE_dataset/images"
    annotations_file_path: str = "dataset/URBE_dataset/labels/COCO/annotations.json"
    max_number_images: int = 350#3500
    obj_classes: int = 3 # number of classes in the dataset
    augmentation: bool = False # apply augmentation startegy to input images
    img_size: int = 640  # size of image in v1 256 works better, in v2 224
    img_channels: int = 3 # RGB channels
    batch_size: int = 64 # size of the batches
    n_cpu: int = 8 # number of cpu threads to use for the dataloaders
    pin_memory: bool = False # parameter to pin memory in dataloader
    
    # YOLOv5 params
    latent_size: int = 128
    lr: float = 2e-4 # 2e-4 or 1e-3
    threshold: float = 0.5 # initialization of the threshold
    gaussian_initialization: bool = True # perform or not the Gaussian inizialization
    t_weight: float = 0.65 # how much weight the new threshold wrt the old
    loss_weight: float = 1 # how much weight the reconstruction loss between two pixels 
    min_lr: float = 1e-8 # min lr for ReduceLROnPlateau
    adam_eps: float = 1e-6 # term added to the denominator to improve numerical stability
    w_std: float = +0.3 # this param weights how much we are going to add of the std in treshold update
    wd: float = 1e-6 # weight decay as regulation strategy
    slope: float = 0.5 # slope for the leaky relu in convolutions
    
    # LOGGING params
    log_images: int = 4 # how many images to log each time
    log_image_each_epoch: int = 2 # epochs interval we wait to log images   