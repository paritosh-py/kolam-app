#test_upload.py

import requests, os, sys, glob
url = "http://127.0.0.1:5000/upload"

def pick_image():
    if len(sys.argv) > 1:
        return sys.argv[1]
    # try current working dir first
    for pattern in ("*.png", "*.jpg", "*.jpeg"):
        files = glob.glob(pattern)
        if files:
            return files[0]
    # fallback to Backend/input.png
    here = os.path.dirname(__file__)
    return os.path.join(here, 'input.png')

img_path = pick_image()
with open(img_path, 'rb') as f:
    files = {'image': f}
    res = requests.post(url, files=files)
print(res.status_code, res.text)