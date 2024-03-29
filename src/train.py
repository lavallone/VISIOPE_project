import pytorch_lightning as pl
import torch
from pytorch_lightning.loggers.wandb import WandbLogger
from pytorch_lightning.callbacks.early_stopping import EarlyStopping
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.callbacks import QuantizationAwareTraining # it doesn't work :(

def train_model(data, model, experiment_name, patience, metric_to_monitor, mode, epochs):
    logger =  WandbLogger()
    logger.experiment.watch(model, log = None, log_freq = 100000)
    early_stop_callback = EarlyStopping(
        monitor=metric_to_monitor, mode=mode, min_delta=0.00, patience=patience, verbose=True)
    checkpoint_callback = ModelCheckpoint(
        save_top_k=1, monitor=metric_to_monitor, mode=mode, dirpath="models",
        filename=experiment_name +
        "-{epoch:02d}-{map_50:.4f}", verbose=True)
    # quantization strategy in order to reduce the inference time of the trained models
    if model.hparams.quantization == True:
        quantization = QuantizationAwareTraining()
        callbacks = [early_stop_callback, checkpoint_callback, quantization]
    else:
        callbacks = [early_stop_callback, checkpoint_callback]
    
    # the trainer collect all the useful informations so far for the training
    n_gpus = 1 if torch.cuda.is_available() else 0
    if model.hparams.resume_from_checkpoint is not None:
        trainer = pl.Trainer(
            logger=logger, max_epochs=epochs, log_every_n_steps=1, gpus=n_gpus,
            callbacks=callbacks, precision = model.hparams.precision, # notice that we can decide the training float precision (32 by default)
            num_sanity_val_steps=0, resume_from_checkpoint=model.hparams.resume_from_checkpoint
            )
    else:
        trainer = pl.Trainer(
            logger=logger, max_epochs=epochs, log_every_n_steps=1, gpus=n_gpus,
            callbacks=callbacks, precision = model.hparams.precision,
            num_sanity_val_steps=0,
            )
    trainer.fit(model, data)
    return trainer
