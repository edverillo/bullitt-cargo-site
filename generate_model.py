#!/usr/bin/env python3
"""
Generate a procedural Bullitt cargo bike GLB (3 meshes, 3 PBR material slots).
Dimensions based on the official technical drawing:
  - Overall length: 2430 mm
  - Rear wheel: 26" (radius 330mm), Front wheel: 20" (radius 254mm)
  - Cargo platform: 710 mm rail, 400 mm wide
  - Head tube angle: 88°, Seat tube angle: 73.5°
  - Fork: BMX Cr-Mo, Linkage steering

The model is scaled so 1 unit = 1 meter.
Output: bullitt-cargo.glb
"""
import struct, json, math, numpy as np
from pathlib import Path

# ---------- geometry helpers ----------

def box(cx, cy, cz, lx, ly, lz):
    """Return (positions, indices) for an axis-aligned box."""
    hx, hy, hz = lx/2, ly/2, lz/2
    v = np.array([
        [cx-hx, cy-hy, cz-hz],[cx+hx, cy-hy, cz-hz],[cx+hx, cy+hy, cz-hz],[cx-hx, cy+hy, cz-hz],
        [cx-hx, cy-hy, cz+hz],[cx+hx, cy-hy, cz+hz],[cx+hx, cy+hy, cz+hz],[cx-hx, cy+hy, cz+hz],
    ], dtype=np.float32)
    faces = [
        [0,1,2],[0,2,3],[4,6,5],[4,7,6],
        [0,4,5],[0,5,1],[1,5,6],[1,6,2],
        [2,6,7],[2,7,3],[3,7,4],[3,4,0],
    ]
    idx = np.array(faces, dtype=np.uint32).flatten()
    return v, idx

def tube_segment(x0, y0, x1, y1, z, r, segs=12):
    """Short tube segment between (x0,y0) and (x1,y1) with given radius, centered at z."""
    dx = x1-x0; dy = y1-y0
    length = math.hypot(dx, dy)
    if length < 0.001:
        return np.empty((0,3), np.float32), np.array([], np.uint32)
    angle = math.atan2(dy, dx)
    verts = []
    for i in range(segs):
        theta = 2*math.pi*i/segs
        rx = r*math.cos(theta); ry = r*math.sin(theta)
        # local: x along tube, y perpendicular
        px = rx*math.cos(angle) - ry*math.sin(angle)
        py = rx*math.sin(angle) + ry*math.cos(angle)
        # start cap
        verts.append([x0 + px, y0 + py, z])
        # end cap
        verts.append([x1 + px, y1 + py, z])
    # Also add cap centers
    verts.append([x0, y0, z])  # start center
    verts.append([x1, y1, z])  # end center
    v = np.array(verts, dtype=np.float32)
    bot_c, top_c = segs*2, segs*2+1
    tris = []
    for i in range(segs):
        n = (i+1) % segs
        s0, s1 = i*2, n*2
        e0, e1 = i*2+1, n*2+1
        tris += [[s0, e0, e1], [s0, e1, s1]]  # side
        tris += [[bot_c, s1, s0]]              # start cap
        tris += [[top_c, e0, e1]]              # end cap
    idx = np.array(tris, dtype=np.uint32).flatten()
    return v, idx

def circle_pts(cx, cy, r, n=32):
    pts = []
    for i in range(n):
        a = 2*math.pi*i/n
        pts.append([cx + r*math.cos(a), cy + r*math.sin(a)])
    return np.array(pts, dtype=np.float32)

def wheel(axle_x, axle_y, z, radius, rim_r, tire_r=0.035, spokes=28):
    """Build a wheel with rim, tire, spokes, hub."""
    verts = []
    idx = []
    offset = 0

    # Tire ring: torus-like band
    pts = circle_pts(axle_x, axle_y, radius, 36)
    pts_rim = circle_pts(axle_x, axle_y, rim_r, 36)
    # Sidewall ring: extruded circle
    tire_verts = []
    for i in range(36):
        a = 2*math.pi*i/36
        x = axle_x + radius*math.cos(a)
        y = axle_y + radius*math.sin(a)
        # Inner
        tire_verts.append([x, y, z-tire_r])
        tire_verts.append([x, y, z+tire_r])
    v_tire = np.array(tire_verts, dtype=np.float32)
    tris = []
    for i in range(36):
        n = (i+1)%36
        b0,b1 = i*2,n*2
        t0,t1 = i*2+1,n*2+1
        tris += [[b0,t0,t1],[b0,t1,b1]]
    idx_tire = np.array(tris, dtype=np.uint32).flatten()
    tire_len = len(v_tire)
    verts.append(v_tire)
    idx.append(idx_tire)

    # Rim (inner ring)
    rim_verts = []
    for i in range(24):
        a = 2*math.pi*i/24
        x = axle_x + rim_r*math.cos(a)
        y = axle_y + rim_r*math.sin(a)
        rim_verts.append([x, y, z-tire_r*0.6])
        rim_verts.append([x, y, z+tire_r*0.6])
    v_rim = np.array(rim_verts, dtype=np.float32)
    tris = []
    for i in range(24):
        n = (i+1)%24
        b0,b1 = i*2,n*2
        t0,t1 = i*2+1,n*2+1
        tris += [[b0,t0,t1],[b0,t1,b1]]
    idx_rim = np.array(tris, dtype=np.uint32).flatten() + offset
    offset += len(v_rim)
    verts.append(v_rim)
    idx.append(idx_rim)

    # Spokes
    spoke_len = radius - rim_r - 0.02
    hub_r = 0.04
    for i in range(max(spokes, 16)):
        a = 2*math.pi*i/spokes
        sx = hub_r*math.cos(a); sy = hub_r*math.sin(a)
        ex = (radius-0.02)*math.cos(a); ey = (radius-0.02)*math.sin(a)
        sv, si = tube_segment(axle_x+sx, axle_y+sy, axle_x+ex, axle_y+ey, z, 0.006, 4)
        if len(sv) > 0:
            si = si + offset if len(idx)>0 else si
            verts.append(sv)
            idx.append(si)
            offset += len(sv)

    # Hub
    hub_v, hub_i = box(axle_x, axle_y, z, 0.08, 0.08, 0.08)
    hub_i = hub_i + offset
    verts.append(hub_v)
    idx.append(hub_i)
    offset += len(hub_v)

    # Disc brake rotor (thin ring)
    disc_v = []
    for i in range(20):
        a = 2*math.pi*i/20
        x = axle_x + 0.07*math.cos(a)
        y = axle_y + 0.07*math.sin(a)
        disc_v.append([x, y, z-0.025])
    disc_i = np.array([list(range(20)) + [0]], dtype=np.uint32).flatten()  # triangle fan
    # Convert to triangles
    tris = []
    for i in range(1, 19):
        tris += [[0, i, i+1]]
    disc_idx = np.array(tris, dtype=np.uint32).flatten() + offset
    v_disc = np.array(disc_v, dtype=np.float32)
    verts.append(v_disc)
    idx.append(disc_idx)
    offset += len(v_disc)

    return merge_batch(verts, idx)

def merge_batch(verts_list, idx_list):
    total_verts = sum(len(v) for v in verts_list)
    total_idx = sum(len(i) for i in idx_list)
    if total_verts == 0:
        return np.empty((0,3), np.float32), np.array([], np.uint32)
    merged_v = np.vstack(verts_list) if len(verts_list) > 1 else verts_list[0]
    merged_i = np.concatenate(idx_list) if len(idx_list) > 1 else idx_list[0]
    return merged_v.astype(np.float32), merged_i.astype(np.uint32)

# ---------- geometry helpers for strut/beam ----------
def beam_from_to(x0, y0, z0, x1, y1, z1, w, h, segs=8):
    """Rectangular beam between (x0,y0,z0) and (x1,y1,z1)."""
    dx = x1-x0; dy = y1-y0; dz = z1-z0
    length = math.sqrt(dx*dx + dy*dy + dz*dz)
    if length < 0.001:
        return np.empty((0,3), np.float32), np.array([], np.uint32)
    # Build box centered at origin, oriented along x-axis
    hx, hy, hz = length/2, h/2, w/2
    v = np.array([
        [-hx, -hy, -hz],[hx, -hy, -hz],[hx, hy, -hz],[-hx, hy, -hz],
        [-hx, -hy, hz],[hx, -hy, hz],[hx, hy, hz],[-hx, hy, hz],
    ], dtype=np.float32)
    # Face indices (6 faces)
    faces = np.array([
        [0,1,2],[0,2,3],[4,6,5],[4,7,6],
        [0,4,5],[0,5,1],[1,5,6],[1,6,2],
        [2,6,7],[2,7,3],[3,7,4],[3,4,0],
    ], dtype=np.uint32)

    # Rotate from x-axis to direction vector
    u = np.array([1.0, 0.0, 0.0])
    v_dir = np.array([dx, dy, dz])
    v_norm = v_dir / length
    rot_axis = np.cross(u, v_norm)
    rot_angle = math.acos(np.clip(np.dot(u, v_norm), -1.0, 1.0))
    
    if np.linalg.norm(rot_axis) > 1e-6:
        rot_axis = rot_axis / np.linalg.norm(rot_axis)
        # Rodrigues rotation
        c, s = math.cos(rot_angle), math.sin(rot_angle)
        K = np.array([
            [0, -rot_axis[2], rot_axis[1]],
            [rot_axis[2], 0, -rot_axis[0]],
            [-rot_axis[1], rot_axis[0], 0]
        ])
        R = np.eye(3) + s*K + (1-c)*K@K
        v = v @ R.T
    
    # Translate
    cx = (x0+x1)/2; cy = (y0+y1)/2; cz = (z0+z1)/2
    v[:,0] += cx; v[:,1] += cy; v[:,2] += cz
    return v, faces.flatten()

# ---------- build geometry ----------

GND = 0.0  # ground level (y = 0)

# Wheel positions (mm converted to meters)
REAR_Y = 0.330   # 26" radius
FRONT_Y = 0.254  # 20" radius

# Axle positions
REAR_AXLE = (0.0, REAR_Y)
FRONT_AXLE = (1.843, FRONT_Y)  # such that total length = 2.43m

# Key frame points
# From the technical drawing: head tube at ~88°, BB height ~0.28m
BB = (0.58, 0.28)          # Bottom bracket
HEAD_BOTTOM = (1.05, 0.50)  # Head tube bottom (steering pivot)
HEAD_TOP = (1.05, 0.90)     # Head tube top
SEAT_TOP = (0.50, 0.78)     # Seat tube top (seatpost insertion)

# Cargo platform
CARGO_BACK = (0.32, 0.32)   # Rear of cargo platform
CARGO_FRONT = (1.70, 0.32)  # Front of cargo platform
CARGO_WIDTH = 0.200          # Half-width of cargo area (400mm total)

# Handlebar
STEM_TOP = (1.05, 1.00)     # Handlebar
HANDLEBAR_W = 0.295         # Half width (590mm total)

frame_parts = []  # (verts, indices, material_name)

def add_part(name, verts, idx, color, metallic=0.1, roughness=0.6):
    if len(verts) > 0:
        frame_parts.append((name, verts, idx, color, metallic, roughness))

# --- FRAME MESH (material slot "Frame") ---

# Main top tube: BB to head bottom
v, i = beam_from_to(BB[0], BB[1], 0, HEAD_BOTTOM[0], HEAD_BOTTOM[1], 0, 0.030, 0.030)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# Top tube extension: seat top to head top
v, i = beam_from_to(SEAT_TOP[0], SEAT_TOP[1], 0, HEAD_TOP[0], HEAD_TOP[1], 0, 0.025, 0.025)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# Seat tube: BB to seat top at 73.5° angle
angle_rad = math.radians(73.5)
st_len = 0.55  # ~530mm
st_x = SEAT_TOP[0]; st_y = SEAT_TOP[1]
v, i = beam_from_to(BB[0], BB[1], 0, st_x, st_y, 0, 0.035, 0.035)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# Head tube at 88° angle
ht_angle = math.radians(88.0)
ht_len = 0.40
ht_x = HEAD_BOTTOM[0] + ht_len * math.cos(ht_angle)
ht_y = HEAD_BOTTOM[1] + ht_len * math.sin(ht_angle)
v, i = beam_from_to(HEAD_BOTTOM[0], HEAD_BOTTOM[1], 0, HEAD_TOP[0], HEAD_TOP[1], 0, 0.040, 0.040)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# Down tube: BB to head bottom
v, i = beam_from_to(BB[0], BB[1], 0, HEAD_BOTTOM[0], HEAD_BOTTOM[1], 0, 0.028, 0.028)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# Cargo platform lower rail (710mm): from behind BB area to front
cp_back_x = 0.25
cp_front_x = cp_back_x + 0.710  # 710mm rail
v, i = beam_from_to(cp_back_x, 0.31, -CARGO_WIDTH-0.015, cp_front_x, 0.31, -CARGO_WIDTH-0.015, 0.025, 0.025)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])
v, i = beam_from_to(cp_back_x, 0.31, CARGO_WIDTH+0.015, cp_front_x, 0.31, CARGO_WIDTH+0.015, 0.025, 0.025)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# Cargo platform cross members (backend)
v, i = beam_from_to(CARGO_BACK[0], CARGO_BACK[1], -CARGO_WIDTH, CARGO_BACK[0], CARGO_BACK[1], CARGO_WIDTH, 0.020, 0.015)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# Cargo platform front cross member
v, i = beam_from_to(cp_front_x, 0.31, -CARGO_WIDTH-0.015, cp_front_x, 0.31, CARGO_WIDTH+0.015, 0.020, 0.015)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# Cargo platform middle cross members
for x in [0.4, 0.6, 0.8, 1.0]:
    v, i = beam_from_to(x, 0.31, -CARGO_WIDTH-0.015, x, 0.31, CARGO_WIDTH+0.015, 0.012, 0.012)
    add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# Chainstay: BB to rear axle
v, i = beam_from_to(BB[0], BB[1]-0.02, -0.06, REAR_AXLE[0], REAR_AXLE[1], -0.06, 0.020, 0.015)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])
v, i = beam_from_to(BB[0], BB[1]-0.02, 0.06, REAR_AXLE[0], REAR_AXLE[1], 0.06, 0.020, 0.015)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# Seatstay: seat tube to rear axle
v, i = beam_from_to(SEAT_TOP[0]-0.02, SEAT_TOP[1]-0.1, -0.04, REAR_AXLE[0], REAR_AXLE[1]+0.02, -0.04, 0.015, 0.012)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])
v, i = beam_from_to(SEAT_TOP[0]-0.02, SEAT_TOP[1]-0.1, 0.04, REAR_AXLE[0], REAR_AXLE[1]+0.02, 0.04, 0.015, 0.012)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# Front fork (BMX Cr-Mo): head bottom to front axle
# Fork blades
v, i = beam_from_to(HEAD_BOTTOM[0]-0.01, HEAD_BOTTOM[1]-0.05, -0.05, FRONT_AXLE[0], FRONT_AXLE[1], -0.05, 0.020, 0.015)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])
v, i = beam_from_to(HEAD_BOTTOM[0]-0.01, HEAD_BOTTOM[1]-0.05, 0.05, FRONT_AXLE[0], FRONT_AXLE[1], 0.05, 0.020, 0.015)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# Steering linkage rod
v, i = beam_from_to(HEAD_BOTTOM[0]-0.12, HEAD_BOTTOM[1]-0.15, 0.07, FRONT_AXLE[0]+0.05, FRONT_AXLE[1]+0.20, 0.07, 0.010, 0.010)
add_part("Frame", v, i, [0.106, 0.106, 0.18, 1.0])

# --- CARGO DECK MESH (material slot "CargoDeck") ---

# Deck surface - flat platform
deck_v = []
for side in [-1, 1]:
    v, i = box(CARGO_BACK[0]+0.79, 0.33, side*CARGO_WIDTH*0.45, 0.78, 0.02, CARGO_WIDTH*1.1)
    if len(v) > 0:
        deck_v.append(v)
if deck_v:
    v = np.vstack(deck_v)
    n = len(v)
    # Generate triangle indices for a box
    faces = [0,1,2,0,2,3, 4,6,5,4,7,6, 0,4,5,0,5,1, 1,5,6,1,6,2, 2,6,7,2,7,3, 3,7,4,3,4,0]
    # Apply to each of 2 boxes
    i = np.concatenate([np.array(faces, dtype=np.uint32), np.array(faces, dtype=np.uint32)+8])

# Actually let me do it properly
# Deck is one big box
v_deck, i_deck = box(CARGO_BACK[0]+0.79, 0.34, 0, 0.78, 0.025, CARGO_WIDTH*0.9)
add_part("CargoDeck", v_deck, i_deck, [0.784, 0.663, 0.431, 1.0], metallic=0.2, roughness=0.7)

# Deck side rails
for side_z in [-CARGO_WIDTH*0.9, CARGO_WIDTH*0.9]:
    v, i = beam_from_to(CARGO_BACK[0], 0.36, side_z, CARGO_BACK[0]+1.5, 0.36, side_z, 0.015, 0.030)
    add_part("CargoDeck", v, i, [0.784, 0.663, 0.431, 1.0], metallic=0.2, roughness=0.7)

# Deck front rail
v, i = beam_from_to(CARGO_BACK[0]+1.5, 0.36, -CARGO_WIDTH*0.9, CARGO_BACK[0]+1.5, 0.36, CARGO_WIDTH*0.9, 0.015, 0.030)
add_part("CargoDeck", v, i, [0.784, 0.663, 0.431, 1.0], metallic=0.2, roughness=0.7)

# --- ACCENTS MESH (handlebars, saddle, pedals, disc brakes) ---

# Handlebars (stem + bar)
v, i = beam_from_to(HEAD_TOP[0], HEAD_TOP[1], 0, HEAD_TOP[0], HEAD_TOP[1]+0.12, 0, 0.025, 0.025)
add_part("Accents", v, i, [0.902, 0.235, 0.184, 1.0], metallic=0.3, roughness=0.3)

# Handlebar bar
v, i = beam_from_to(HEAD_TOP[0], HEAD_TOP[1]+0.12, -HANDLEBAR_W, HEAD_TOP[0], HEAD_TOP[1]+0.12, HANDLEBAR_W, 0.022, 0.022)
add_part("Accents", v, i, [0.902, 0.235, 0.184, 1.0], metallic=0.3, roughness=0.3)

# Grips
for side in [-1, 1]:
    v, i = beam_from_to(HEAD_TOP[0], HEAD_TOP[1]+0.12, side*HANDLEBAR_W, HEAD_TOP[0], HEAD_TOP[1]+0.12, side*(HANDLEBAR_W-0.06), 0.028, 0.028)
    add_part("Accents", v, i, [0.902, 0.235, 0.184, 1.0], metallic=0.1, roughness=0.8)

# Saddle
v, i = box(0.48, 0.83, 0, 0.18, 0.03, 0.07)
add_part("Accents", v, i, [0.0, 0.0, 0.0, 1.0], metallic=0.0, roughness=0.9)

# Seatpost
v, i = beam_from_to(SEAT_TOP[0], SEAT_TOP[1], 0, 0.48, 0.82, 0, 0.015, 0.015)
add_part("Accents", v, i, [0.0, 0.0, 0.0, 1.0], metallic=0.3, roughness=0.3)

# Disc brake rotors on wheels
for side in [-1, 1]:
    for ax, ay in [REAR_AXLE, FRONT_AXLE]:
        # Brake caliper
        v, i = box(ax-0.02, ay-0.03, side*0.04, 0.03, 0.05, 0.02)
        if len(v) > 0:
            add_part("Accents", v, i, [0.8, 0.8, 0.8, 1.0], metallic=0.5, roughness=0.3)

# Kickstand
v, i = beam_from_to(CARGO_BACK[0]+0.05, 0.31, -0.06, CARGO_BACK[0]+0.05, GND-0.02, -0.10, 0.015, 0.015)
add_part("Accents", v, i, [0.6, 0.6, 0.6, 1.0], metallic=0.5, roughness=0.5)
v, i = beam_from_to(CARGO_BACK[0]+0.05, 0.31, 0.06, CARGO_BACK[0]+0.05, GND-0.02, 0.10, 0.015, 0.015)
add_part("Accents", v, i, [0.6, 0.6, 0.6, 1.0], metallic=0.5, roughness=0.5)
# Cross bar
v, i = beam_from_to(CARGO_BACK[0]+0.05, GND-0.02, -0.10, CARGO_BACK[0]+0.05, GND-0.02, 0.10, 0.012, 0.012)
add_part("Accents", v, i, [0.6, 0.6, 0.6, 1.0], metallic=0.5, roughness=0.5)

# --- WHEELS (built as Frame material) ---

# Rear wheel (26")
rv, ri = wheel(REAR_AXLE[0], REAR_AXLE[1], 0, 0.330, 0.290)
add_part("Frame", rv, ri, [0.2, 0.2, 0.22, 1.0], metallic=0.3, roughness=0.6)

# Front wheel (20")
fv, fi = wheel(FRONT_AXLE[0], FRONT_AXLE[1], 0, 0.254, 0.220)
add_part("Frame", fv, fi, [0.2, 0.2, 0.22, 1.0], metallic=0.3, roughness=0.6)

# ---------- GLB builder ----------

def pack_buffer(data_bytes):
    pad = (4 - len(data_bytes)%4)%4
    return data_bytes + b'\x00'*pad

def build_glb(parts, out_path):
    bin_chunks = []
    accessors = []
    buffer_views = []
    mesh_defs = []
    materials = []
    offset = 0

    for name, verts, indices, color, metallic, roughness in parts:
        # indices
        idx_bytes = indices.astype(np.uint32).tobytes()
        idx_padded = pack_buffer(idx_bytes)
        buffer_views.append({"buffer":0,"byteOffset":offset,"byteLength":len(idx_bytes),"target":34963})
        idx_acc = len(accessors)
        accessors.append({"bufferView":len(buffer_views)-1,"componentType":5125,"count":len(indices),"type":"SCALAR","byteOffset":0})
        offset += len(idx_padded)
        bin_chunks.append(idx_padded)

        # positions
        pos_bytes = verts.astype(np.float32).tobytes()
        pos_padded = pack_buffer(pos_bytes)
        buffer_views.append({"buffer":0,"byteOffset":offset,"byteLength":len(pos_bytes),"target":34962})
        pos_acc = len(accessors)
        mn = verts.min(axis=0).tolist()
        mx = verts.max(axis=0).tolist()
        accessors.append({"bufferView":len(buffer_views)-1,"componentType":5126,"count":len(verts),"type":"VEC3","min":mn,"max":mx,"byteOffset":0})
        offset += len(pos_padded)
        bin_chunks.append(pos_padded)

        mat_idx = len(materials)
        materials.append({
            "name": name,
            "pbrMetallicRoughness": {
                "baseColorFactor": color,
                "metallicFactor": metallic,
                "roughnessFactor": roughness
            }
        })

        mesh_defs.append({
            "name": name,
            "primitives": [{"attributes":{"POSITION":pos_acc},"indices":idx_acc,"material":mat_idx}]
        })

    bin_data = b''.join(bin_chunks)

    gltf = {
        "asset": {"version": "2.0", "generator": "bullitt-procedural-v3"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(parts)))}],
        "nodes": [{"mesh": i, "name": p[0]} for i, p in enumerate(parts)],
        "meshes": mesh_defs,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_data)}],
    }

    json_bytes = json.dumps(gltf, separators=(',',':')).encode('utf-8')
    json_padded = pack_buffer(json_bytes)

    total = 12 + 8 + len(json_padded) + 8 + len(bin_data)
    out = bytearray()
    out += struct.pack('<III', 0x46546C67, 2, total)
    out += struct.pack('<II', len(json_padded), 0x4E4F534A)
    out += json_padded
    out += struct.pack('<II', len(bin_data), 0x004E4942)
    out += bin_data

    Path(out_path).write_bytes(bytes(out))
    print(f"Written {len(out)/1024:.1f} KB -> {out_path}")

out = "public/assets/3d/bullitt-cargo.glb"
Path(out).parent.mkdir(parents=True, exist_ok=True)
build_glb(frame_parts, out)
