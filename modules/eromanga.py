import sys, os, glob, io
import requests
import re
import PIL
from PIL import UnidentifiedImageError, Image
from tqdm import tqdm
from bs4 import BeautifulSoup


def check_image_integrity(image: Image) -> bool:
    re = True
    try:
        image.load()
    except (IOError, PIL.UnidentifiedImageError) as e:
        print(f"Image is corrupted or invalid. Error: {e}")
        re = False
    return re

def get_images(url: str) -> list[Image]:
    """
    Downloads urls from urls.
    :param url: 'https://eromanga-show.com/viewer?articleId=n&page=n' Click the icon of the main page.
    :return:
    """

    images = []

    request = requests.get(url).content
    tree = BeautifulSoup(request, 'html.parser')

<<<<<<< HEAD
        index = 1
        formatt = ''
        for image_url in tqdm(images_url_list, desc=f'minssion : {missison_counter}/{mission_number}'):
            image = requests.get(image_url).content
            formatt = image_url.split('.')[-1]
            with open(f'{os.path.join("cache", f"{index}.{formatt}")}', 'wb') as out_file:
                out_file.write(image)
                index += 1
=======
    title = tree.find('title').text
>>>>>>> 7de61a86cddaed84c4deea249ca35fe72dcedcd1

    url_pattern = r'https?://[^\s",]+'
    image_urls = re.findall(url_pattern, tree.findAll('script')[-2].text)
    images_url_list = []
    for i in image_urls:
        print(i)
        if 'webp' in i or 'png' in i or 'png' in i:
            images_url_list.append(i[:-1:])

    for image_url in tqdm(images_url_list):
        image = requests.get(image_url).content
        image_data = io.BytesIO(image)
        image = Image.open(image_data)
        if check_image_integrity(image):
            images.append(image)


    return images
# try:
#     os.system('ptf')
# except PIL.UnidentifiedImageError as ie:
#     print(ie)
#     exit(1)
# else:
#     current_folder = os.getcwd()
#     current_folder_name = os.path.basename(current_folder)
#
#     os.rename(os.path.join(current_folder, current_folder_name+'.pdf'), os.path.join(current_folder, title+'.pdf'))
#     # os.system(f'rename "{current_folder_name}.pdf" "{title}.pdf"')
#     os.system(f'del *.{formatt} {current_folder_name}_lossless_compressed.pdf')
#     missison_counter += 1


