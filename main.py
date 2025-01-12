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
        'name': '[あくた～ (木家マユ)] イクのガマンゲーム!風紀委員長悶絶クリ責め地獄 [英訳]',
        'final': 10,
        'id': 545332,
        'format': 'jpg'
    }
]


def is_empty(check: list) -> bool:
    return len(check) == 0


if __name__ == '__main__':
    # test out

    if is_empty(infos) is False:
        for info in infos:
            image = nhentai.get_images(info)
            p1 = I2P(images=image, pdf_name=info['name'], quality=75)
            p1.convert_images_to_pdf()




