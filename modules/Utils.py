import sys, os
import requests
import PIL
from ptf import i2p
from tqdm import tqdm
from PIL import Image


class Utils(object):
    @classmethod
    def check_image_integrity(cls, image: Image) -> bool:
        re = True
        try:
            image.load()
        except (IOError, PIL.UnidentifiedImageError) as e:
            print(f"Image is corrupted or invalid. Error: {e}")
            re = False
        return re