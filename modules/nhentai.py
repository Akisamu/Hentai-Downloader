import sys, os, io
import requests
from PIL import Image, UnidentifiedImageError
from PIL.Image import Image
from tqdm import tqdm

def check_image_integrity(image: Image) -> bool:
    re = True
    try:
        Image.load()
    except (IOError, UnidentifiedImageError) as e:
        print(f"Image is corrupted or invalid. Error: {e}")
        re = False
    return re


def get_images(info: dict) -> None:
    """
    :param info: 'final', 'formatt'
    :return:
    """
    final = info['final']
    id = info['id']
    formatt = info['format']
    images = []
    for i in tqdm(range(1, final + 1)):
        url = f'https://cdn.cartoonporn.to/nhentai/storage/images/{id}/{i}.{formatt}'
        r = requests.get(url)
        print(f'Status： {r}')
        image_data = io.BytesIO(r.content)
        image = Image.open(image_data)
        if check_image_integrity(image):
            images.append(Image.open(image_data))





















            # d:\Akisamu\Desktop\output\{i}.jpg
            # with open(
            #         os.path.join('..', 'cache', f'{i}.jpg'),
            #         'wb'
            # ) as out_file:
            #     out_file.write(r.content)

        # --- 把输出改了，改成类变量？  ---
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
        #               os.path.join(current_folder, name + '.pdf'))
        #     # os.system(f'rename "{current_folder_name}.pdf" "{title}.pdf"')
        #     os.system(f'del *.{formatt} {current_folder_name}_lossless_compressed.pdf')
        #     missison_counter += 1

    


