
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev_nb/Lesson1_matmul.ipynb

from pathlib import Path
from fastai import datasets as FA_datasets
import pickle, gzip, math, torch, matplotlib as mpl
import matplotlib.pyplot as plt

MNIST_URL='http://deeplearning.net/data/mnist/mnist.pkl'

# Path.home() # real home dir of the computer
HOME_DIR = Path('.').resolve()
DATA_DIR = HOME_DIR/"data"
HOME_DIR, DATA_DIR

fname = DATA_DIR/'mnist.pkl.gz'
fpath = FA_datasets.download_data(MNIST_URL,fname,ext='.gz');fpath