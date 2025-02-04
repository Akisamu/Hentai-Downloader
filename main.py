from modules import eromanga, nhentai
from modules.eromanga import get_images
from modules.ptf.i2p import I2P

'''
param url: 'https://eromanga-show.com/viewer?articleId=n&page=n'
'''
urls = [

]

"""
    {
        'name': '',
        'final': 1,
        'id': 1,
        'format': 'webp'
    }
"""
infos = [
    {
        'name': '(C105) [えだまめ亭 (うこ)] 先生は私を××してくれない (ブルーアーカイブ) [中国翻訳]',
        'final': 98,
        'id': 583898,
        'format': 'webp'
    },
    {
        'name': '(C105) [えだまめ亭 (うこ)] 先生は私を××してくれない (ブルーアーカイブ) [中国翻訳]',
        'final': 98,
        'id': 583898,
        'format': 'webp'
    }
]


def is_empty(check: list) -> bool:
    return len(check) == 0


if __name__ == '__main__':
    # test out

    if is_empty(infos) is False:
        for info in infos:
            image = nhentai.get_images(info)
            p1 = I2P(images=image, pdf_name=info['name'], is_compress=False)
            p1.convert_images_to_pdf()

    if is_empty(urls) is False:
        for url in urls:
            image = get_images(url=url['url'])
            p2 = I2P(images=image, pdf_name=url['name'], is_compress=False)
            p2.convert_images_to_pdf()





