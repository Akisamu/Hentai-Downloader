import sys, os
import requests
import PIL
from tqdm import tqdm


class Nhentai:

    def __init__(self):
        self.name = ''
        self.final = ''
        self.id = ''
        self.formatt = ''

def get_images(infos: list) -> None:
    """
    :param infos: dict 'name', 'final', 'formatt'
    :return:
    """
    missison_counter = 1
    mission_number = len(infos)
    for info in infos:
        name = info['name']
        final = info['final']
        id = info['id']
        formatt = info['format']
        for i in tqdm(range(1, final + 1), desc=f'missino: {missison_counter} / {mission_number}'):
            url = f'https://cdn.cartoonporn.to/nhentai/storage/images/{id}/{i}.{formatt}'

            try:
                r = requests.get(url)
                print(f'Status： {r}')
            except Exception as e:
                print(e)
                exit(1)
            # d:\Akisamu\Desktop\output\{i}.jpg
            with open(
                    os.path.join('..', 'cache', f'{i}.jpg'),
                    'wb'
            ) as out_file:
                out_file.write(r.content)

        # --- 把输出改了，改成类变量？  ---
        try:
            os.system('ptf')
        except PIL.UnidentifiedImageError as ie:
            print(ie)
            exit(1)
        else:
            current_folder = os.getcwd()
            current_folder_name = os.path.basename(current_folder)

            os.rename(os.path.join(current_folder, current_folder_name + '.pdf'),
                      os.path.join(current_folder, name + '.pdf'))
            # os.system(f'rename "{current_folder_name}.pdf" "{title}.pdf"')
            os.system(f'del *.{formatt} {current_folder_name}_lossless_compressed.pdf')
            missison_counter += 1
    


