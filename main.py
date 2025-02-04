from modules import eromanga, nhentai
from modules.ptf import i2p

'''
param url: 'https://eromanga-show.com/viewer?articleId=n&page=n'
'''
urls = [
    'https://eromanga-show.com/viewer?articleId=3136036&page=1'
]

"""
    {
        'name': '[STUDIO PAL (南野琴、犬崎みくり)] クソ上から目線の姪っ子を催眠術で恥かしいお仕置きをする。 [中国翻訳] [DL版]',
        'final': 32,
        'id': 328358,
        'format': 'jpg'
    }
"""
infos = [

]


def is_empty(check: list) -> bool:
    return len(check) == 0


if __name__ == '__main__':
    if is_empty(infos) is False:

        for i in infos:
            images_stream = nhentai.get_images(info=i)

    # if is_empty(urls) is False:
    #     eromanga.download(urls=urls)
        for info in infos:
            image = nhentai.get_images(info)
            p1 = I2P(images=image, pdf_name=info['name'])
            p1.convert_images_to_pdf()





