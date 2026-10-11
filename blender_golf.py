"""Build and render a 3D hole-in-one scene in Blender.

Run headless:  blender -b --python blender_golf.py -- <output_dir>
Frames are written as PNGs to <output_dir>; make_gif.py turns them into golf_3d.gif.
"""
import math
import sys
import traceback

import bpy
from mathutils import Matrix, Vector

FRAMES = 100
IMPACT, LAND, ROLL_END, DROP_END = 42, 72, 84, 88
HOLE = Vector((24.0, 0.0, 0.0))
LAND_X = 20.5
BALL_R = 0.06  # oversized so it reads at GIF resolution


def out_dir():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return args[0] if args else "//frames_3d"


# ---------- helpers ----------

def material(name, color, rough=0.6, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = 2.0
    return m


def add(obj_op, mat, name, **kw):
    obj_op(**kw)
    o = bpy.context.active_object
    o.name = name
    if mat:
        o.data.materials.append(mat)
    bpy.ops.object.shade_smooth() if o.type == "MESH" else None
    return o


def limb(a, b, radius, mat, name):
    """Cylinder from point a to point b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    o = add(bpy.ops.mesh.primitive_cylinder_add, mat, name,
            radius=radius, depth=d.length, location=(a + b) / 2, vertices=16)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    return o


def parent_keep(child, parent):
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def ease_out(t):
    return 1 - (1 - t) ** 2


# ---------- scene ----------

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, FRAMES
    sc.render.fps = 25
    return sc


def build_world():
    w = bpy.data.worlds.new("Sky")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.55, 0.78, 0.98, 1)
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = (0.08, 0.3, 0.8, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.8

    bpy.ops.object.light_add(type="SUN", location=(0, 0, 20))
    sun = bpy.context.active_object
    sun.data.energy = 3.0
    sun.data.angle = math.radians(3)
    sun.rotation_euler = (math.radians(50), math.radians(-20), math.radians(-35))


def build_course():
    # fairway with mowing stripes (checker squashed to bands)
    fair = material("Fairway", (0.12, 0.38, 0.08))
    nt = fair.node_tree
    chk = nt.nodes.new("ShaderNodeTexChecker")
    chk.inputs["Color1"].default_value = (0.13, 0.42, 0.09, 1)
    chk.inputs["Color2"].default_value = (0.09, 0.32, 0.06, 1)
    chk.inputs["Scale"].default_value = 1.0
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.25, 0.0, 1.0)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], chk.inputs["Vector"])
    nt.links.new(chk.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    add(bpy.ops.mesh.primitive_plane_add, fair, "Ground", size=400, location=(0, 0, 0))

    green = material("Green", (0.2, 0.6, 0.15), rough=0.5)
    add(bpy.ops.mesh.primitive_cylinder_add, green, "PuttingGreen",
        radius=5, depth=0.02, location=(HOLE.x, HOLE.y, 0.01), vertices=64)
    cup = material("Cup", (0.01, 0.01, 0.01), rough=1.0)
    add(bpy.ops.mesh.primitive_cylinder_add, cup, "Cup",
        radius=0.11, depth=0.005, location=(HOLE.x, HOLE.y, 0.022), vertices=32)

    # flag
    white = material("Pole", (0.95, 0.95, 0.95), rough=0.3)
    limb((HOLE.x, HOLE.y, 0), (HOLE.x, HOLE.y, 2.4), 0.025, white, "Pole")
    red = material("Flag", (0.85, 0.05, 0.05), rough=0.7)
    mesh = bpy.data.meshes.new("FlagMesh")
    mesh.from_pydata([(0, 0, 0), (0.9, 0, -0.25), (0, 0, -0.5)], [], [(0, 1, 2)])
    flag = bpy.data.objects.new("Flag", mesh)
    flag.data.materials.append(red)
    bpy.context.collection.objects.link(flag)
    flag.location = (HOLE.x, HOLE.y, 2.4)
    for f in range(1, FRAMES + 1, 4):
        flag.rotation_euler = (0, 0, math.radians(-25 + 12 * math.sin(f * 0.3)))
        flag.keyframe_insert("rotation_euler", frame=f)

    # tee
    tee = material("Tee", (0.95, 0.8, 0.3))
    limb((0, 0, 0), (0, 0, 0.04), 0.008, tee, "Tee")

    # background trees and hills
    trunk = material("Trunk", (0.25, 0.15, 0.07))
    leaves = [material(f"Leaves{i}", c) for i, c in
              enumerate([(0.05, 0.25, 0.05), (0.08, 0.3, 0.06), (0.04, 0.2, 0.08)])]
    import random
    random.seed(7)
    for i in range(26):
        x = random.uniform(-25, 50)
        y = random.uniform(14, 40)
        h = random.uniform(4, 8)
        limb((x, y, 0), (x, y, h * 0.5), 0.2, trunk, f"Trunk{i}")
        if random.random() < 0.5:
            add(bpy.ops.mesh.primitive_cone_add, leaves[i % 3], f"Pine{i}",
                radius1=h * 0.3, depth=h, location=(x, y, h * 0.75), vertices=12)
        else:
            add(bpy.ops.mesh.primitive_ico_sphere_add, leaves[i % 3], f"Oak{i}",
                radius=h * 0.35, location=(x, y, h * 0.7), subdivisions=2)
    hill = material("Hill", (0.15, 0.4, 0.12))
    for i, (x, r) in enumerate([(-10, 35), (35, 45), (70, 40)]):
        o = add(bpy.ops.mesh.primitive_uv_sphere_add, hill, f"Hill{i}",
                radius=r, location=(x, 75, -r * 0.75))
        o.scale.z = 0.5


def build_golfer():
    """Simple figure facing -Y with the ball in front; returns the swing pivot."""
    skin = material("Skin", (0.9, 0.68, 0.5))
    shirt = material("Shirt", (0.8, 0.08, 0.08))
    pants = material("Pants", (0.08, 0.1, 0.22))
    shoe = material("Shoe", (0.95, 0.95, 0.95))
    cap = material("Cap", (0.05, 0.05, 0.08))
    steel = material("Steel", (0.8, 0.8, 0.85), rough=0.2)
    steel.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0
    grip = material("Grip", (0.05, 0.05, 0.05))

    gx, gy = -0.05, 0.75  # golfer stands behind the ball
    # legs
    for side, dx in (("L", 0.2), ("R", -0.2)):
        limb((gx + dx * 0.4, gy, 0.95), (gx + dx, gy - 0.05, 0.5), 0.07, pants, f"Thigh{side}")
        limb((gx + dx, gy - 0.05, 0.5), (gx + dx, gy, 0.06), 0.06, pants, f"Shin{side}")
        o = add(bpy.ops.mesh.primitive_cube_add, shoe, f"Shoe{side}", size=1,
                location=(gx + dx, gy - 0.05, 0.04))
        o.scale = (0.11, 0.26, 0.08)
    # torso leaning toward the ball
    hip = Vector((gx, gy, 0.98))
    neck = Vector((gx, gy - 0.28, 1.5))
    limb(hip, neck, 0.17, shirt, "Torso")
    add(bpy.ops.mesh.primitive_uv_sphere_add, shirt, "Hips", radius=0.17, location=hip)
    add(bpy.ops.mesh.primitive_uv_sphere_add, shirt, "Chest", radius=0.19, location=neck - Vector((0, -0.03, 0.08)))
    head_c = neck + Vector((0, -0.1, 0.2))
    add(bpy.ops.mesh.primitive_uv_sphere_add, skin, "Head", radius=0.12, location=head_c)
    c = add(bpy.ops.mesh.primitive_uv_sphere_add, cap, "Cap", radius=0.125, location=head_c + Vector((0, 0, 0.03)))
    c.scale.z = 0.6
    bill = add(bpy.ops.mesh.primitive_cube_add, cap, "Bill", size=1, location=head_c + Vector((0, -0.14, 0.04)))
    bill.scale = (0.16, 0.12, 0.015)

    # arms + club hang from the shoulders and swing as one unit
    shoulder = neck + Vector((0, 0, -0.04))
    hands = Vector((gx + 0.02, gy - 0.5, 0.85))
    head_pos = Vector((0.0, 0.05, 0.03))  # club head sits just behind the ball
    v = head_pos - shoulder
    normal = Vector((1, 0, 0)).cross(v).normalized()  # swing plane normal
    pivot = bpy.data.objects.new("SwingPivot", None)
    bpy.context.collection.objects.link(pivot)
    pivot.location = shoulder
    pivot.rotation_mode = "QUATERNION"
    pivot.rotation_quaternion = Vector((0, 1, 0)).rotation_difference(normal)

    parts = [
        limb(shoulder + Vector((0.16, 0, 0)), hands, 0.05, shirt, "ArmL"),
        limb(shoulder + Vector((-0.16, 0, 0)), hands, 0.05, shirt, "ArmR"),
        add(bpy.ops.mesh.primitive_uv_sphere_add, skin, "Hands", radius=0.06, location=hands),
        limb(hands, hands + (head_pos - hands) * 0.25, 0.018, grip, "Grip"),
        limb(hands, head_pos, 0.01, steel, "Shaft"),
    ]
    ch = add(bpy.ops.mesh.primitive_cube_add, steel, "ClubHead", size=1, location=head_pos)
    ch.scale = (0.11, 0.05, 0.04)
    parts.append(ch)
    for p in parts:
        parent_keep(p, pivot)
    return pivot, normal


def swing_angle(f):
    """Degrees around the swing-plane normal: negative = backswing (to the golfer's right)."""
    if f < 12:
        return 0
    if f < 30:
        return -150 * ease_out((f - 12) / 18)
    if f < 35:
        return -150
    if f <= IMPACT:
        t = (f - 35) / (IMPACT - 35)
        return -150 + 150 * t ** 2
    if f < IMPACT + 12:
        return 170 * ease_out((f - IMPACT) / 12)
    return 170


def animate_swing(pivot, normal):
    base = pivot.rotation_quaternion.copy()
    for f in range(1, FRAMES + 1):
        q = base.copy()
        from mathutils import Quaternion
        q = Quaternion(normal, math.radians(-swing_angle(f))) @ base
        pivot.rotation_quaternion = q
        pivot.keyframe_insert("rotation_quaternion", frame=f)


def ball_pos(f):
    if f <= IMPACT:
        return Vector((0, 0, 0.04 + BALL_R))
    if f <= LAND:
        t = (f - IMPACT) / (LAND - IMPACT)
        return Vector((LAND_X * t, 0, BALL_R + 0.04 * (1 - t) + 9.0 * 4 * t * (1 - t)))
    if f <= ROLL_END:
        t = ease_out((f - LAND) / (ROLL_END - LAND))
        return Vector((LAND_X + (HOLE.x - LAND_X) * t, 0, BALL_R + 0.02))
    t = min(1.0, (f - ROLL_END) / (DROP_END - ROLL_END))
    return Vector((HOLE.x, 0, BALL_R + 0.02 - 0.2 * t))


def build_ball():
    m = material("Ball", (0.98, 0.98, 0.98), rough=0.25)
    ball = add(bpy.ops.mesh.primitive_uv_sphere_add, m, "Ball", radius=BALL_R, location=(0, 0, 0.1))
    for f in range(1, FRAMES + 1):
        ball.location = ball_pos(f)
        ball.keyframe_insert("location", frame=f)
    # glowing streak: a cone from where the ball was a few frames ago (thin) to the ball (thick)
    glow = material("Trail", (1, 1, 1), emission=(1.0, 0.95, 0.8))
    streak = add(bpy.ops.mesh.primitive_cone_add, glow, "Streak",
                 radius1=0.0, radius2=BALL_R * 0.9, depth=1.0, vertices=16, location=(0, 0, -5))
    streak.visible_shadow = False
    streak.rotation_mode = "QUATERNION"
    for f in range(1, FRAMES + 1):
        head, tail = ball_pos(f), ball_pos(max(IMPACT, f - 4))
        d = head - tail
        if f <= IMPACT or f > LAND + 3 or d.length < 1e-3:
            streak.location, streak.scale = Vector((0, 0, -5)), Vector((1, 1, 0.01))
        else:
            streak.location = (head + tail) / 2
            streak.scale = Vector((1, 1, d.length))
            streak.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
        for prop in ("location", "scale", "rotation_quaternion"):
            streak.keyframe_insert(prop, frame=f)
    return ball


def build_camera():
    target = bpy.data.objects.new("CamTarget", None)
    bpy.context.collection.objects.link(target)
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    cam.data.lens = 32
    bpy.context.scene.camera = cam
    tr = cam.constraints.new("TRACK_TO")
    tr.target = target
    tr.track_axis = "TRACK_NEGATIVE_Z"
    tr.up_axis = "UP_Y"

    for f in range(1, FRAMES + 1):
        if f <= IMPACT + 2:
            # slow push-in on the golfer
            t = (f - 1) / (IMPACT + 1)
            tgt = Vector((0.6, 0.3, 0.9))
            cam_pos = Vector((2.2 - 0.6 * t, -6.5 + 1.5 * t, 1.6))
        else:
            # follow the ball toward the green, then settle on the hole
            b = ball_pos(min(f, ROLL_END))
            t = min(1.0, (f - IMPACT - 2) / 6)  # catch up with the ball quickly
            k = t * t * (3 - 2 * t)
            tgt = Vector((0.6, 0.3, 0.9)).lerp(Vector((b.x + 1.5, 0, max(0.3, b.z * 0.8))), k)
            end_cam = Vector((HOLE.x - 6, -7, 2.2))
            cam_pos = Vector((1.6, -5.0, 1.6)).lerp(Vector((b.x - 5, -13, 1.8 + b.z * 0.5)), k)
            if f > LAND:
                u = min(1.0, (f - LAND) / 14)
                cam_pos = cam_pos.lerp(end_cam, u * u * (3 - 2 * u))
        target.location = tgt
        cam.location = cam_pos
        target.keyframe_insert("location", frame=f)
        cam.keyframe_insert("location", frame=f)
    return cam


def build_title(cam):
    gold = material("Gold", (1.0, 0.75, 0.1), rough=0.3, emission=(1.0, 0.7, 0.05))
    bpy.ops.object.text_add()
    txt = bpy.context.active_object
    txt.name = "Title"
    txt.data.body = "HOLE IN ONE!"
    txt.data.align_x = "CENTER"
    txt.data.extrude = 0.02
    txt.data.size = 0.075
    txt.data.materials.append(gold)
    txt.parent = cam
    txt.location = (0, 0.25, -1.0)
    txt.visible_shadow = False
    for f, show in ((1, False), (DROP_END, False), (DROP_END + 1, True)):
        txt.hide_render = not show
        txt.keyframe_insert("hide_render", frame=f)
        txt.scale = (0.01, 0.01, 0.01) if not show else (1, 1, 1)
        txt.keyframe_insert("scale", frame=f)
    txt.scale = (1.15, 1.15, 1.15)
    txt.keyframe_insert("scale", frame=DROP_END + 4)
    txt.scale = (1, 1, 1)
    txt.keyframe_insert("scale", frame=DROP_END + 7)


def linear_keys():
    for a in bpy.data.actions:
        for fc in getattr(a, "fcurves", []):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


def setup_render(path):
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            continue
    try:
        sc.eevee.taa_render_samples = 32
    except AttributeError:
        pass
    sc.render.use_motion_blur = False
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path.rstrip("/\\") + "/frame_"
    sc.view_settings.view_transform = "Standard"


def main():
    path = out_dir()
    reset()
    build_world()
    build_course()
    pivot, normal = build_golfer()
    animate_swing(pivot, normal)
    build_ball()
    cam = build_camera()
    build_title(cam)
    linear_keys()
    setup_render(path)
    bpy.ops.wm.save_as_mainfile(filepath=path.rstrip("/\\") + "/../golf_3d.blend")
    if "--still" in sys.argv:
        for f in [int(x) for x in sys.argv[sys.argv.index("--still") + 1].split(",")]:
            bpy.context.scene.frame_set(f)
            bpy.context.scene.render.filepath = path.rstrip("/\\") + f"/still_{f:03d}"
            bpy.ops.render.render(write_still=True)
    else:
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    log = None
    try:
        main()
    except Exception:
        log = traceback.format_exc()
    p = out_dir().rstrip("/\\") + "/../blender_log.txt"
    with open(p, "w") as fh:
        fh.write(log or "ok\n")
