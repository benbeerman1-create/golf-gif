"""Render an animated golf swing GIF: a golfer swings, the ball flies to the green and drops in the hole."""
import math
from PIL import Image, ImageDraw

W, H = 480, 270
SCALE = 2  # draw at 2x then downsample for smooth edges
FRAMES = 90
GROUND_Y = 215

SKY_TOP = (110, 170, 235)
SKY_BOTTOM = (200, 228, 250)
FAIRWAY = (70, 150, 60)
FAIRWAY_DARK = (55, 125, 48)
GREEN = (95, 185, 80)
SKIN = (240, 200, 160)
SHIRT = (220, 60, 60)
PANTS = (40, 50, 80)

TEE = (95, GROUND_Y)
HOLE = (395, GROUND_Y + 4)


def s(v):
    return int(v * SCALE)


def pt(p):
    return (s(p[0]), s(p[1]))


def draw_background(d):
    for y in range(s(GROUND_Y)):
        t = y / s(GROUND_Y)
        c = tuple(int(SKY_TOP[i] + (SKY_BOTTOM[i] - SKY_TOP[i]) * t) for i in range(3))
        d.line([(0, y), (s(W), y)], fill=c)
    # sun
    d.ellipse([s(400), s(25), s(440), s(65)], fill=(255, 230, 120))
    # distant hills
    d.ellipse([s(-60), s(170), s(220), s(260)], fill=(120, 180, 100))
    d.ellipse([s(180), s(175), s(560), s(275)], fill=(110, 170, 95))
    # fairway with mowing stripes
    d.rectangle([0, s(GROUND_Y), s(W), s(H)], fill=FAIRWAY)
    for i in range(0, W, 40):
        d.polygon([pt((i, GROUND_Y)), pt((i + 20, GROUND_Y)), pt((i + 50, H)), pt((i + 30, H))], fill=FAIRWAY_DARK)
    # putting green, hole, flag
    d.ellipse([s(335), s(GROUND_Y - 6), s(455), s(GROUND_Y + 14)], fill=GREEN)
    d.ellipse([s(HOLE[0] - 5), s(HOLE[1] - 2), s(HOLE[0] + 5), s(HOLE[1] + 3)], fill=(20, 30, 20))
    d.line([pt((HOLE[0], HOLE[1])), pt((HOLE[0], HOLE[1] - 55))], fill=(240, 240, 240), width=s(2))


def draw_flag(d, f):
    wave = math.sin(f * 0.35) * 3
    top = HOLE[1] - 55
    d.polygon([pt((HOLE[0], top)), pt((HOLE[0] + 26, top + 7 + wave)), pt((HOLE[0], top + 15))], fill=(230, 40, 40))


def club_angle(f):
    """Club angle in degrees (0 = straight down, positive = back toward the left)."""
    if f < 12:  # address
        return 0
    if f < 30:  # backswing
        t = (f - 12) / 18
        return 200 * (1 - (1 - t) ** 2)
    if f < 36:  # pause at top
        return 200
    if f < 42:  # downswing, fast
        t = (f - 36) / 6
        return 200 - 200 * t ** 2
    if f < 52:  # follow-through
        t = (f - 42) / 10
        return -210 * (1 - (1 - t) ** 2)
    return -210


def draw_golfer(d, f):
    hip = (TEE[0] - 28, GROUND_Y - 38)
    shoulder = (TEE[0] - 24, GROUND_Y - 68)
    head = (TEE[0] - 20, GROUND_Y - 80)
    # legs
    d.line([pt(hip), pt((hip[0] - 9, GROUND_Y))], fill=PANTS, width=s(6))
    d.line([pt(hip), pt((hip[0] + 9, GROUND_Y))], fill=PANTS, width=s(6))
    # torso
    d.line([pt(hip), pt(shoulder)], fill=SHIRT, width=s(9))
    # head + cap
    d.ellipse([s(head[0] - 7), s(head[1] - 7), s(head[0] + 7), s(head[1] + 7)], fill=SKIN)
    d.chord([s(head[0] - 8), s(head[1] - 10), s(head[0] + 8), s(head[1] + 4)], 180, 360, fill=(30, 30, 30))
    # arms + club rotate around the shoulder
    a = math.radians(club_angle(f))
    arm_len, club_len = 26, 34
    hands = (shoulder[0] - math.sin(a) * arm_len + 6, shoulder[1] + math.cos(a) * arm_len)
    club_end = (hands[0] - math.sin(a) * club_len + 4 * math.cos(a), hands[1] + math.cos(a) * club_len)
    d.line([pt(shoulder), pt(hands)], fill=SKIN, width=s(4))
    d.line([pt(hands), pt(club_end)], fill=(180, 180, 190), width=s(2))
    d.ellipse([s(club_end[0] - 3), s(club_end[1] - 2), s(club_end[0] + 3), s(club_end[1] + 2)], fill=(90, 90, 100))


def ball_pos(f):
    impact, land, hole_in = 42, 74, 84
    if f <= impact:
        return TEE
    if f <= land:  # parabolic flight
        t = (f - impact) / (land - impact)
        end_x = HOLE[0] - 22
        x = TEE[0] + (end_x - TEE[0]) * t
        y = TEE[1] - 140 * 4 * t * (1 - t)
        return (x, y)
    if f <= hole_in:  # roll into the cup
        t = (f - land) / (hole_in - land)
        t = 1 - (1 - t) ** 2
        return (HOLE[0] - 22 + 22 * t, GROUND_Y + 2 * t)
    return None  # in the hole


def draw_ball(d, f):
    # trail
    for k in range(1, 7):
        p = ball_pos(f - k)
        if p and f - k > 42 and f < 76:
            r = 3 - k * 0.35
            g = 255 - k * 20
            d.ellipse([s(p[0] - r), s(p[1] - 3 - r), s(p[0] + r), s(p[1] - 3 + r)], fill=(g, g, g))
    p = ball_pos(f)
    if p:
        # shadow on the ground
        d.ellipse([s(p[0] - 4), s(GROUND_Y - 1), s(p[0] + 4), s(GROUND_Y + 2)], fill=(45, 100, 40))
        d.ellipse([s(p[0] - 3.5), s(p[1] - 7), s(p[0] + 3.5), s(p[1])], fill=(255, 255, 255), outline=(170, 170, 170))


def draw_text(d, f):
    if f >= 84:
        msg = "HOLE IN ONE!"
        x, y = s(W / 2 - 60), s(40)
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            d.text((x + dx, y + dy), msg, fill=(30, 30, 30), font_size=s(20))
        d.text((x, y), msg, fill=(255, 215, 0), font_size=s(20))


def render():
    base = Image.new("RGB", (s(W), s(H)))
    draw_background(ImageDraw.Draw(base))
    rgb_frames = []
    for f in range(FRAMES):
        img = base.copy()
        d = ImageDraw.Draw(img)
        draw_flag(d, f)
        draw_golfer(d, f)
        draw_ball(d, f)
        draw_text(d, f)
        rgb_frames.append(img.resize((W, H), Image.LANCZOS))
    # one shared palette (built from a frame with the text) so colors don't flicker between frames
    palette = rgb_frames[-1].quantize(colors=255, dither=Image.Dither.NONE)
    frames = [fr.quantize(palette=palette, dither=Image.Dither.NONE) for fr in rgb_frames]
    durations = [40] * FRAMES
    durations[-1] = 1500  # hold the final frame
    frames[0].save("golf.gif", save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)


if __name__ == "__main__":
    render()
