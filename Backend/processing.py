# processing.py
# C:\Users\parit\Desktop\SIH\Backend\processing.py
import cv2
import os
import numpy as np

def _closest_point_index(pt, points, maxdist=30):
    """Linear nearest neighbor search returning index or None."""
    if not points:
        return None
    px, py = pt
    best_i = None
    best_d2 = maxdist * maxdist
    for i, (x, y) in enumerate(points):
        d2 = (x - px) ** 2 + (y - py) ** 2
        if d2 <= best_d2:
            best_d2 = d2
            best_i = i
    return best_i

def _dedupe_centers(centers, min_dist=8):
    kept = []
    for (x,y) in sorted(centers, key=lambda p:(p[0], p[1])):
        skip = False
        for (kx,ky) in kept:
            if (x-kx)**2 + (y-ky)**2 <= min_dist**2:
                skip = True
                break
        if not skip:
            kept.append((int(x), int(y)))
    return kept

def _save_debug(img, name):
    os.makedirs("tmp", exist_ok=True)
    path = os.path.join("tmp", name)
    cv2.imwrite(path, img)
    return path

def _auto_canny(image, sigma=0.33):
    v = np.median(image)
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    return cv2.Canny(image, lower, upper)

def process_image(img_path, debug=False,
                  resize_max=1200,
                  tophat_kernel=21,
                  dot_min_area=20,
                  dot_max_area=2000,
                  dot_circularity=0.55,
                  dedupe_dist=8,
                  line_snap_dist=30,
                  curve_approx_epsilon=3.0):
    """
    Returns (processed_path, dots_list, polylines_list, debug_files_or_None).
    - dots_list: [(x,y), ...] coordinates in original image pixels (ints)
    - polylines_list: [ [(x1,y1),(x2,y2),...], ... ] coordinates in original pixels
    - debug_files_or_None: dict of debug image paths if debug=True, otherwise None
    """

    if not os.path.exists(img_path):
        raise FileNotFoundError(img_path)

    orig = cv2.imread(img_path)
    if orig is None:
        raise ValueError("Image unreadable")

    H0, W0 = orig.shape[:2]
    scale = 1.0
    if resize_max and max(W0, H0) > resize_max:
        scale = resize_max / max(W0, H0)
        img = cv2.resize(orig, (int(W0*scale), int(H0*scale)), interpolation=cv2.INTER_AREA)
    else:
        img = orig.copy()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # contrast and denoise
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray_enh = clahe.apply(gray)
    gray_enh = cv2.medianBlur(gray_enh, 5)

    ######################
    # DOT EXTRACTION PIPE
    ######################

    # 1) Top-hat filter to emphasize small bright features (dots)
    #    top-hat = original - opening(original)
    ksize = max(3, int(tophat_kernel) // 2 * 2 + 1)  # ensure odd-ish
    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
    opened = cv2.morphologyEx(gray_enh, cv2.MORPH_OPEN, open_kernel, iterations=1)
    tophat = cv2.subtract(gray_enh, opened)

    # 2) Threshold the top-hat to get candidate dot mask
    _, dots_mask = cv2.threshold(tophat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # small cleanup
    small_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
    dots_mask = cv2.morphologyEx(dots_mask, cv2.MORPH_OPEN, small_k, iterations=1)
    dots_mask = cv2.morphologyEx(dots_mask, cv2.MORPH_CLOSE, small_k, iterations=1)

    # 3) Build a line mask (so we can remove line pixels from dot mask)
    thr = cv2.adaptiveThreshold(gray_enh, 255,
                                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 21, 5)
    # strengthen lines with closing
    line_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    line_mask = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, line_k, iterations=2)
    # optionally thin lines: (we don't skeletonize here, but it's okay)
    # remove intersection with dots_mask (we want dots separate)
    dots_mask_nolines = cv2.subtract(dots_mask, line_mask)
    if cv2.countNonZero(dots_mask_nolines) < 8:
        # if subtraction removed too much, fallback to dots_mask
        dots_mask_nolines = dots_mask.copy()

    # 4) Connected components on dots_mask_nolines
    contours, _ = cv2.findContours(dots_mask_nolines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centers = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < dot_min_area or area > dot_max_area:
            continue
        perim = cv2.arcLength(c, True)
        if perim <= 0:
            continue
        circ = 4 * np.pi * (area / (perim * perim))
        if circ < dot_circularity:
            continue
        M = cv2.moments(c)
        if M.get('m00', 0) == 0:
            continue
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])
        centers.append((cx, cy))

    # 5) If centers too few, use distance-transform peak detection on dots_mask
    if len(centers) < 6:
        # distance transform on original dots_mask (not subtracted)
        dt = cv2.distanceTransform(dots_mask, cv2.DIST_L2, 5)
        # normalize for processing
        norm = (dt / (dt.max() + 1e-9))
        # peaks where dt normalized > fraction of max
        peaks = (norm > 0.4).astype(np.uint8) * 255
        # small cleanup
        peaks = cv2.morphologyEx(peaks, cv2.MORPH_OPEN, small_k, iterations=1)
        cnts2, _ = cv2.findContours(peaks, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts2:
            area = cv2.contourArea(c)
            if area < 2:
                continue
            M = cv2.moments(c)
            if M.get('m00', 0) == 0:
                continue
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            centers.append((cx, cy))

    # dedupe centers and scale back to original coordinates
    centers = _dedupe_centers(centers, min_dist=dedupe_dist)
    centers_original_scale = [ (int(x/scale), int(y/scale)) for (x,y) in centers ]

    ######################
    # CURVE / LINE EXTRACTION
    ######################

    # Use auto-Canny on smoothed grayscale for robust edges
    blur_for_edges = cv2.GaussianBlur(gray_enh, (5,5), 0)
    edges = _auto_canny(blur_for_edges, sigma=0.33)

    # strengthen edges and close small gaps
    edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3)), iterations=1)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5)), iterations=1)

    # Find contours on edges (curves)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    polylines = []
    for c in cnts:
        if len(c) < 20:
            continue
        approx = cv2.approxPolyDP(c, curve_approx_epsilon, False)
        pts = [ (int(p[0][0]), int(p[0][1])) for p in approx ]
        if len(pts) < 3:
            continue
        polylines.append(pts)

    # Snap polyline endpoints to nearest centers (if close)
    snapped = []
    for poly in polylines:
        p2 = list(poly)
        for idx in [0, 1, -2, -1]:
            if abs(idx) == 1 and len(p2) < 2:
                continue
            real_idx = idx if idx >= 0 else len(p2) + idx
            pt = p2[real_idx]
            nearest_i = _closest_point_index(pt, centers, maxdist=line_snap_dist)
            if nearest_i is not None:
                p2[real_idx] = centers[nearest_i]
        # remove consecutive duplicates
        simplified = []
        for p in p2:
            if not simplified or p != simplified[-1]:
                simplified.append((int(p[0]), int(p[1])))
        if len(simplified) >= 3:
            snapped.append(simplified)

    # scale polylines back to original coords
    snapped_original_scale = []
    for poly in snapped:
        poly_scaled = [ (int(x/scale), int(y/scale)) for (x,y) in poly ]
        snapped_original_scale.append(poly_scaled)

    # Visualization on resized image (for quick view)
    vis = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    for (x,y) in centers:
        cv2.circle(vis, (int(x), int(y)), 5, (0,0,255), -1)
    for poly in snapped:
        for i in range(len(poly)-1):
            cv2.line(vis, (int(poly[i][0]), int(poly[i][1])), (int(poly[i+1][0]), int(poly[i+1][1])), (0,255,0), 2)

    out_name = os.path.basename(img_path).rsplit('.',1)[0] + "_processed.png"
    out_path = os.path.join("tmp", out_name)
    os.makedirs("tmp", exist_ok=True)
    cv2.imwrite(out_path, vis)

    # Prepare debug files if requested (save intermediate masks)
    debug_files = None
    if debug:
        debug_files = {}
        debug_files['opened'] = _save_debug(opened, os.path.basename(img_path).rsplit('.',1)[0] + "_opened.png")
        debug_files['tophat'] = _save_debug(tophat, os.path.basename(img_path).rsplit('.',1)[0] + "_tophat.png")
        debug_files['dots_mask'] = _save_debug(dots_mask, os.path.basename(img_path).rsplit('.',1)[0] + "_dotsmask.png")
        debug_files['dots_mask_nolines'] = _save_debug(dots_mask_nolines, os.path.basename(img_path).rsplit('.',1)[0] + "_dots_nolines.png")
        debug_files['line_mask'] = _save_debug(line_mask, os.path.basename(img_path).rsplit('.',1)[0] + "_linemask.png")
        debug_files['edges'] = _save_debug(edges, os.path.basename(img_path).rsplit('.',1)[0] + "_edges.png")
        debug_files['final_vis'] = out_path

    return out_path, centers_original_scale, snapped_original_scale, debug_files