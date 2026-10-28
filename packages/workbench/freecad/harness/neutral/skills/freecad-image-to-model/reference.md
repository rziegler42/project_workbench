# Reference: image-to-model examples

Every Python example below was run headless with `freecadcmd` on FreeCAD 1.1.4, and the printed value is in the comment.
The measuring examples use a synthetic image made in memory, so the true sizes are known: a dark part of 64 x 48 mm
with a 16 mm hole, and a reference bar of 50 mm, drawn at 10 pixels per millimetre.

## Helpers

```python
import numpy as np
from PIL import Image


def synthetic_image():
    """Dark part 640 x 480 px with a hole of 160 px, and a 500 px reference bar below it, on white."""
    img = np.full((700, 900), 255, dtype=np.uint8)
    img[30:510, 100:740] = 0                               # the part: 64 x 48 mm at 10 px/mm
    rows, cols = np.ogrid[:700, :900]
    img[(cols - 420) ** 2 + (rows - 270) ** 2 <= 80 ** 2] = 255      # the hole: 16 mm across
    img[600:620, 100:600] = 0                              # the reference bar: 50 mm
    return Image.fromarray(img)
```

## Measure the part, the hole and the scale

```python
from scipy import ndimage

im = np.asarray(synthetic_image().convert("L"), dtype=float)
mask = im < 128                              # dark pixels; tune the threshold per image and check it by eye


def bbox(m):
    ys, xs = np.nonzero(m)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


REF_MM = 50.0                                # the real length of the reference object
ref = mask.copy()
ref[:560] = False                            # the reference bar sits below row 560
part = mask.copy()
part[560:] = False
rx0, _, rx1, _ = bbox(ref)
px_per_mm = (rx1 - rx0) / REF_MM
print(px_per_mm)                             # 10.0

x0, y0, x1, y1 = bbox(part)
print(round((x1 - x0) / px_per_mm, 2), round((y1 - y0) / px_per_mm, 2))      # 64.0 48.0

holes = ndimage.binary_fill_holes(part) & ~part       # light pixels enclosed by the part
labels, count = ndimage.label(holes)
for i in range(1, count + 1):
    ys, xs = np.nonzero(labels == i)
    diameter = 2 * np.sqrt(len(xs) / np.pi) / px_per_mm
    cx, cy = (xs.mean() - x0) / px_per_mm, (ys.mean() - y0) / px_per_mm
    print("hole", i, round(diameter, 2), round(cx, 2), round(cy, 2))          # hole 1 16.0 32.0 24.0 (from the top left)
```

## Image coordinates are upside down

```python
height_mm = 48.0
cx_mm, cy_down = 32.0, 24.0                  # measured from the part's top left, with Y pointing down
cy_up = height_mm - cy_down                  # FreeCAD's Y points up: measure from the bottom left
print(cx_mm, cy_up)                          # 32.0 24.0
print(height_mm - 3.0)                       # a feature 3 mm below the top is at Y = 45.0 in FreeCAD
```

## A reference image in the document

```python
import os
import shutil
import tempfile

import FreeCAD as App

folder = tempfile.mkdtemp()
path = os.path.join(folder, "photo.png")
synthetic_image().save(path)
doc = App.newDocument("Ref")
plane = doc.addObject("Image::ImagePlane", "FrontPhoto")
plane.ImageFile = path
plane.XSize = 90.0                           # the image width in mm: 900 px / 10 px per mm
plane.YSize = 70.0                           # the image height in mm
doc.recompute()
print(plane.TypeId, plane.XSize, plane.YSize, plane.State)
shutil.rmtree(folder)
```

## Compare two outlines numerically

```python
a = np.zeros((100, 100), dtype=bool)
b = np.zeros((100, 100), dtype=bool)
a[20:80, 20:80] = True                       # the reference outline
b[25:85, 20:80] = True                       # the model's outline, shifted down by 5 pixels
intersection = (a & b).sum()
union = (a | b).sum()
print(round(intersection / union, 4))        # 0.8462: one when they match exactly
```
