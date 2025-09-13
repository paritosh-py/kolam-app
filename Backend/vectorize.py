# vectorize.py
# C:\Users\parit\Desktop\SIH\Backend\vectorize.py
import svgwrite
import os
import cv2
import numpy as np

def create_vector(dots, polylines, out_path=None, canvas_size=None):
    """
    dots: [(x,y), ...] coords in pixels (original image coordinates)
    polylines: [ [(x1,y1),(x2,y2)...], ... ]
    out_path: optional path (defaults to tmp/kolam.svg)
    canvas_size: optional (width,height) to set SVG viewbox; if None, auto-calc from data
    """
    os.makedirs("tmp", exist_ok=True)
    if out_path is None:
        out_path = os.path.join("tmp", "kolam.svg")

    # Determine canvas size
    all_x = []
    all_y = []
    for x,y in dots:
        all_x.append(x); all_y.append(y)
    for poly in polylines:
        for x,y in poly:
            all_x.append(x); all_y.append(y)
    if canvas_size is None and all_x and all_y:
        minx, maxx = min(all_x), max(all_x)
        miny, maxy = min(all_y), max(all_y)
        w = maxx - minx + 40
        h = maxy - miny + 40
        offset_x = minx - 20
        offset_y = miny - 20
    else:
        w, h = canvas_size if canvas_size else (800, 800)
        offset_x = 0
        offset_y = 0

    dwg = svgwrite.Drawing(out_path, size=(w, h), profile='tiny')
    g = dwg.g()
    # background white
    dwg.add(dwg.rect(insert=(0,0), size=(w,h), fill='white'))

    # Draw polylines first (so dots appear on top)
    for poly in polylines:
        # shift points by offset
        pts = [((x - offset_x), (y - offset_y)) for (x,y) in poly]
        # smooth path: use simple polyline (browser will render)
        g.add(dwg.polyline(pts, stroke='black', fill='none', stroke_width=2, stroke_linecap='round', stroke_linejoin='round'))

    # Draw dots
    for (x,y) in dots:
        cx = x - offset_x
        cy = y - offset_y
        g.add(dwg.circle(center=(cx, cy), r=4, fill='black'))

    dwg.add(g)
    dwg.save()
    return out_path


def create_vector_from_dotsmask(dotsmask_path, out_path=None, canvas_size=None):
    """
    Create SVG directly from a dotsmask image file
    dotsmask_path: path to the dotsmask image (white dots on black background)
    out_path: optional path (defaults to tmp/kolam.svg)
    canvas_size: optional (width,height) to set SVG viewbox; if None, uses image dimensions
    """
    os.makedirs("tmp", exist_ok=True)
    if out_path is None:
        out_path = os.path.join("tmp", "kolam.svg")

    # Read the dotsmask image
    img = cv2.imread(dotsmask_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image: {dotsmask_path}")
    
    # Find contours (dots) in the image
    contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Extract center points of contours (dots)
    dots = []
    for contour in contours:
        # Calculate moments to find center
        M = cv2.moments(contour)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            dots.append((cx, cy))
    
    # Use image dimensions if canvas_size not provided
    if canvas_size is None:
        h, w = img.shape
        canvas_size = (w, h)
    
    # Create SVG with dots only
    return create_vector(dots, [], out_path, canvas_size)