#!/usr/bin/env python3
"""
Generate a procedural Bullitt cargo bike GLB (3 meshes, 3 PBR material slots).
Pure stdlib + numpy — no pygltflib or Blender required.
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
    idx = np.array(faces, dtype=np.uint16).flatten()
    return v, idx

def cylinder(cx, cy, cz, r, h, segs=16, axis='y'):
    """Return (positions, indices) for a cylinder."""
    verts = []
    for i in range(segs):
        a = 2*math.pi*i/segs
        x, z = r*math.cos(a), r*math.sin(a)
        if axis == 'y':
            verts.append([cx+x, cy,   cz+z])
            verts.append([cx+x, cy+h, cz+z])
        elif axis == 'x':
            verts.append([cx,   cy+x, cz+z])
            verts.append([cx+h, cy+x, cz+z])
    # cap centres
    if axis == 'y':
        verts.append([cx, cy,   cz])
        verts.append([cx, cy+h, cz])
    else:
        verts.append([cx,   cy, cz])
        verts.append([cx+h, cy, cz])
    v = np.array(verts, dtype=np.float32)
    bot_c, top_c = segs*2, segs*2+1
    tris = []
    for i in range(segs):
        n = (i+1)%segs
        b0,b1 = i*2, n*2
        t0,t1 = i*2+1, n*2+1
        tris += [[b0,t0,t1],[b0,t1,b1]]  # side
        tris += [[bot_c,b1,b0]]           # bottom cap
        tris += [[top_c,t0,t1]]           # top cap
    idx = np.array(tris, dtype=np.uint16).flatten()
    return v, idx

def merge(*meshes):
    verts_list, idx_list = [], []
    offset = 0
    for v, i in meshes:
        verts_list.append(v)
        idx_list.append(i + offset)
        offset += len(v)
    return np.vstack(verts_list), np.concatenate(idx_list)

# ---------- build geometry ----------

# Frame mesh: main tubes as boxes + cylinders
frame_parts = [
    box(0.0,  0.55, 0.0,  0.05, 0.55, 0.05),   # seat tube
    box(-0.15, 0.78, 0.0, 0.35, 0.04, 0.04),    # top tube
    box(-0.1,  0.6,  0.0, 0.32, 0.04, 0.04),    # down tube (approx)
    box(-0.5,  0.55, 0.0, 0.8,  0.04, 0.04),    # long cargo tube / chainstay area
    box(0.2,   0.55, 0.0, 0.04, 0.4,  0.04),    # seat stay (right of rear wheel)
    cylinder(0.18, 0.0, 0.0, 0.33, 0.04, 16, 'x'),  # rear wheel (tyre)
    cylinder(-0.55, 0.0, 0.0, 0.33, 0.04, 16, 'x'),  # front wheel (tyre)
    cylinder(0.18, -0.32, 0.0, 0.04, 0.0, 16, 'x'),   # rear axle dot
]
frame_v, frame_i = merge(*frame_parts)

# CargoDeck mesh
cargo_parts = [
    box(-0.53, 0.62, 0.0, 0.73, 0.06, 0.28),   # deck surface
    box(-0.53, 0.68, 0.15, 0.73, 0.06, 0.025),  # rail right
    box(-0.53, 0.68,-0.15, 0.73, 0.06, 0.025),  # rail left
]
cargo_v, cargo_i = merge(*cargo_parts)

# Accents mesh (handlebar + saddle + accent bits)
accent_parts = [
    box(-0.14, 0.88, 0.0, 0.04, 0.15, 0.04),   # handlebar stem
    box(-0.14, 1.0,  0.0, 0.04, 0.04, 0.28),    # handlebar bar
    box(0.0,   1.0,  0.0, 0.04, 0.04, 0.12),    # saddle post top
    box(0.0,   1.0,  0.0, 0.18, 0.025, 0.07),   # saddle
]
accent_v, accent_i = merge(*accent_parts)

meshes = [
    ("Frame",      frame_v,  frame_i,  [0.106, 0.106, 0.18, 1.0]),
    ("CargoDeck",  cargo_v,  cargo_i,  [0.784, 0.663, 0.431, 1.0]),
    ("Accents",    accent_v, accent_i, [0.902, 0.235, 0.184, 1.0]),
]

# ---------- GLB builder ----------

def pack_buffer(data_bytes):
    pad = (4 - len(data_bytes)%4)%4
    return data_bytes + b'\x00'*pad

def build_glb(meshes, out_path):
    bin_chunks = []
    accessors = []
    buffer_views = []
    mesh_defs = []
    materials = []
    offset = 0

    for name, verts, indices, color in meshes:
        # indices
        idx_bytes = indices.astype(np.uint16).tobytes()
        idx_padded = pack_buffer(idx_bytes)
        buffer_views.append({"buffer":0,"byteOffset":offset,"byteLength":len(idx_bytes),"target":34963})
        idx_acc = len(accessors)
        accessors.append({"bufferView":len(buffer_views)-1,"componentType":5123,"count":len(indices),"type":"SCALAR","byteOffset":0})
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
                "metallicFactor": 0.1,
                "roughnessFactor": 0.6
            }
        })

        mesh_defs.append({
            "name": name,
            "primitives": [{"attributes":{"POSITION":pos_acc},"indices":idx_acc,"material":mat_idx}]
        })

    bin_data = b''.join(bin_chunks)

    gltf = {
        "asset": {"version": "2.0", "generator": "bullitt-procedural-v1"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(meshes)))}],
        "nodes": [{"mesh": i, "name": m[0]} for i, m in enumerate(meshes)],
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
    out += struct.pack('<III', 0x46546C67, 2, total)          # glTF magic, version, length
    out += struct.pack('<II', len(json_padded), 0x4E4F534A)   # JSON chunk
    out += json_padded
    out += struct.pack('<II', len(bin_data), 0x004E4942)      # BIN chunk
    out += bin_data

    Path(out_path).write_bytes(bytes(out))
    print(f"Written {len(out)/1024:.1f} KB -> {out_path}")

out = "public/assets/3d/bullitt-cargo.glb"
Path(out).parent.mkdir(parents=True, exist_ok=True)
build_glb(meshes, out)
