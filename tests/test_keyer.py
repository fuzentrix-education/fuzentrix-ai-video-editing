import numpy as np

from fzv import keyer


def test_difference_matte_keeps_subject_and_drops_plate():
    plate = np.full((120, 160, 3), 240, np.float32)
    frame = plate.copy().astype(np.uint8)
    frame[40:110, 60:100] = (30, 40, 60)                     # the instructor
    frame[5:9, 5:9] = (200, 200, 200)                        # a tiny speck that must not survive
    rgba = keyer.matte(frame, plate, "plate")
    a = rgba[..., 3]
    assert a[70, 80] > 250 and a[10, 140] == 0 and a[6, 6] == 0


def test_chroma_matte():
    frame = np.zeros((60, 80, 3), np.uint8); frame[:] = (20, 200, 30)
    frame[20:50, 30:50] = (200, 160, 140)
    a = keyer.matte(frame, np.zeros((60, 80, 3), np.float32), "chroma")[..., 3]
    assert a[35, 40] > 250 and a[5, 5] < 10


def test_fit_poly_reproduces_a_smooth_wall():
    ys, xs = np.mgrid[0:54, 0:96]
    wall = np.dstack([100 + xs * 0.5 + ys * 0.3] * 3).astype(np.float32)
    keep = np.ones((54, 96), bool)
    fit = keyer.fit_poly(wall, keep, (54, 96))
    assert np.abs(fit - wall).max() < 1.0


def test_region_mask_polygon():
    from fzv.keyer import region_mask
    m = region_mask(100, 200, {"exclude_poly": [[[0, 50], [100, 50], [120, 100], [0, 100]]], "cut_below": 95})
    assert m[10, 10] == 1 and m[70, 20] == 0 and m[70, 150] == 1 and m[97, 150] == 0
