import sys, os, glob
from processing import process_image

def pick_image(args):
    if len(args) > 1:
        return args[1]
    # fallback: first png/jpg/jpeg in current dir
    for pattern in ("*.png", "*.jpg", "*.jpeg"):
        files = glob.glob(pattern)
        if files:
            return files[0]
    # fallback to Backend/input.png relative to this file
    here = os.path.dirname(__file__)
    candidate = os.path.join(here, 'input.png')
    return candidate

img_path = pick_image(sys.argv)
print("Using image:", img_path)
out_path, dots, polylines, debug = process_image(img_path, debug=True)
print("dots:", len(dots))
print("polylines:", len(polylines))
print(debug)