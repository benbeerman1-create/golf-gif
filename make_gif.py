"""Assemble the Blender frames in frames_3d/ into golf_3d.gif."""
from pathlib import Path
from PIL import Image

W, H = 640, 360
frames = [Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS)
          for p in sorted(Path("frames_3d").glob("frame_*.png"))]
# shared palette (built from a flight frame + the final frame) so colors don't flicker
sample = Image.new("RGB", (W, H * 2))
sample.paste(frames[len(frames) // 2], (0, 0))
sample.paste(frames[-1], (0, H))
palette = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
out = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
durations = [40] * len(out)
durations[-1] = 1500  # hold on the final frame
out[0].save("golf_3d.gif", save_all=True, append_images=out[1:], duration=durations, loop=0, optimize=True)
print(len(out), "frames")
