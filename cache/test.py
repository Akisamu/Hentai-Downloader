
import requests

if __name__ == '__main__':
  url = 'https://nhentai.com/en/comic/nyala-ponga-sekai-saisoku-no-panda-meshasei-nyuumon-introduction-to-female-ejaculation-chinese-digital'
  r = requests.get(url)

  print(r.content)
