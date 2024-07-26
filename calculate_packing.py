import bpy
import bmesh
import csv
import time
from mathutils import Vector
from math import pi

D = bpy.data
C = bpy.context

def bounding_sphere(objects):
    points_co_global = []
    for obj in objects:
        points_co_global.extend([obj.matrix_world @ vertex.co for vertex in obj.data.vertices])

    def get_center(l):
        return (max(l) + min(l)) / 2 if l else 0.0

    x, y, z = [[point_co[i] for point_co in points_co_global] for i in range(3)]
    b_sphere_center = Vector([get_center(axis) for axis in [x, y, z]]) if (x and y and z) else None
    b_sphere_radius = max((point - b_sphere_center).length for point in points_co_global) if b_sphere_center else None
    return b_sphere_center, b_sphere_radius

def estimate_aggregate_volume(objects):
    total_volume = 0
    for obj in objects:
        if obj.data is not None:
            obj.data.update()
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            volume = bm.calc_volume()
            bm.free()
            total_volume += volume
    return total_volume

def max_distance_from_center(objects, center):
    return max((vertex.co - center).length for obj in objects for vertex in obj.data.vertices)

# Main code
start_time = time.time()

# Collect all mesh objects once
mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']

# Calculate initial aggregate volume
aggregate_volume = estimate_aggregate_volume(mesh_objects)

# Output results to CSV
#mac
with open(r"/Users/espiller/Documents/Research - Zachariah Group/aggregate_packing_data.csv", 'w', newline='') as csvfile:
#win
#with open(r"E:\Documents\Research - Zachariah Group\aggregate_packing_data.csv", 'w', newline='') as csvfile:   
    fieldnames = ['time', 'aggregate_volume', 'bounding_radius', 'packing_fraction', 'max_radius']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    
    for t in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end + 1):
        bpy.context.scene.frame_set(t)
        
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        
        b_sphere_co, b_sphere_radius = bounding_sphere(mesh_objects)
        bounding_sphere_volume = (4/3)*pi*(b_sphere_radius**3)
        max_radius = max_distance_from_center(mesh_objects, b_sphere_co)

        writer.writerow({
            'time': t,
            'aggregate_volume': aggregate_volume,
            'bounding_radius': b_sphere_radius,
            'packing_fraction': aggregate_volume / bounding_sphere_volume,
            'max_radius': max_radius
        })

final_time = time.time() - start_time
print(final_time)