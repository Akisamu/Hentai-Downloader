from modules import eromanga, nhentai

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
        'format': 'jpg'
    }
"""
infos = [

]


def is_empty(check: list) -> bool:
    return len(check) == 0


if __name__ == '__main__':
    # test out
    exit(0)

    if is_empty(infos) is False:
        n_hentai.download(infos=infos)
    if is_empty(urls) is False:
        eromanga.download(urls=urls)


