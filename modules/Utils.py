import sys, os
import requests
import PIL
from ptf import i2p
from tqdm import tqdm


class Utils(object):
    @classmethod
    def download_image(name: str, images: list) -> None:

        # try:
        #     os.system('ptf')
        # except PIL.UnidentifiedImageError as ie:
        #     print(ie)
        #     exit(1)
        # else:
        #     current_folder = os.getcwd()
        #     current_folder_name = os.path.basename(current_folder)
        #
        #     os.rename(os.path.join(current_folder, current_folder_name + '.pdf'),
        #               os.path.join(current_folder, title + '.pdf'))
        #     # os.system(f'rename "{current_folder_name}.pdf" "{title}.pdf"')
        #     os.system(f'del *.{formatt} {current_folder_name}_lossless_compressed.pdf')
        #     missison_counter += 1

        pass