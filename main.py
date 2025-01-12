from modules import eromanga, nhentai
from modules.ptf.i2p import I2P

'''
param url: 'https://eromanga-show.com/viewer?articleId=n&page=n'
'''
urls = [
    '233'
]

"""
    {
        'name': '',
        'final': 1,
        'id': 1,
        'format': 'jpg'
    }
"""
infos = [
    {
        'name': '',
        'final': 1,
        'id': 1,
        'format': 'jpg'
    }
]


def is_empty(check: list) -> bool:
    return len(check) == 0


if __name__ == '__main__':
    # test out
    exit(0)

    if is_empty(infos) is False:
        for info in infos:
            image = nhentai.get_images(info)
            I2P(images=image, pdf_name=info['name'], quality=75)

    if is_empty(urls) is False:
        eromanga.download(urls=urls)


