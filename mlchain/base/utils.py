import urllib.request
import mimetypes
from PIL import Image
from urllib.request import urlopen, Request
from io import BytesIO
import numpy as np
from mlchain import logger

cv2 = None


def import_cv2():
    global cv2
    if cv2 is None:
        import cv2 as cv
        cv2 = cv


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3'}


def is_url_image(url):
    mimetype, encoding = mimetypes.guess_type(url)
    return mimetype and mimetype.startswith('image')


def check_url(url):
    """Returns True if the url returns a response code between 200-300,
       otherwise return False.
    """
    try:
        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req)
        return response.code in range(200, 209)
    except Exception:
        return False


def is_image_url_and_ready(url):
    return is_url_image(url) and check_url(url)


def read_image_from_url_cv2(url, flag):
    import_cv2()
    logger.info("Read cv2 image from: {0}".format(url))
    byte_data = bytearray(urlopen(Request(url=url, headers=headers), timeout=100).read())
    return cv2.imdecode(np.asarray(byte_data, dtype="uint8"), flag)


def read_image_from_url_pil(url):
    logger.info("Read pil image from: {0}".format(url))
    file = BytesIO(urlopen(Request(url=url, headers=headers), timeout=100).read())
    img = Image.open(file)
    return img
