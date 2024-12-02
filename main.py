import eromanga
import n_hentai


'''
param url: 'https://eromanga-show.com/viewer?articleId=n&page=n'
'''
urls = [
    'https://eromanga-show.com/viewer?articleId=3136036&page=1'
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

]


def is_empty(check: list) -> bool:
    return len(check) == 0


if __name__ == '__main__':
    if is_empty(infos) is False:
        n_hentai.download(infos=infos)
    if is_empty(urls) is False:
        eromanga.download(urls=urls)


