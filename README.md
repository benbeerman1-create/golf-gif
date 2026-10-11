# Golf GIF

An animated hole-in-one, made two ways.

## 3D (Blender)

![3D golf swing animation](golf_3d.gif)

Built and rendered with Blender's Python API (EEVEE), then assembled into a GIF with Pillow.

```
blender -b --python blender_golf.py -- frames_3d
python make_gif.py
```

## 2D (Pillow)

![2D golf swing animation](golf.gif)

```
pip install pillow
python render_golf.py
```
