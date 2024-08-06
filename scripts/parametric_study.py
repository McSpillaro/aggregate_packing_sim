import bpy
import bmesh
import random
import math
import time
import csv 

import numpy as np

from math import pi
from mathutils import Vector




### Cleaning the Scene 

def purge_orphans():
    if bpy.app.version >= (3, 0, 0):
        bpy.ops.outliner.orphans_purge(
            do_local_ids=True, do_linked_ids=True, do_recursive=True
        )
    else:
        # call purge_orphans() recursively until there are no more orphan data blocks to purge
        result = bpy.ops.outliner.orphans_purge()
        if result.pop() != "CANCELLED":
            purge_orphans()


def clean_scene():
    """
    Removing all of the objects, collection, materials, particles,
    textures, images, curves, meshes, actions, nodes, and worlds from the scene
    """
    if bpy.context.active_object and bpy.context.active_object.mode == "EDIT":
        bpy.ops.object.editmode_toggle()

    for obj in bpy.data.objects:
        obj.hide_set(False)
        obj.hide_select = False
        obj.hide_viewport = False

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    collection_names = [col.name for col in bpy.data.collections]
    for name in collection_names:
        bpy.data.collections.remove(bpy.data.collections[name])

    # in the case when you modify the world shader
    world_names = [world.name for world in bpy.data.worlds]
    for name in world_names:
        bpy.data.worlds.remove(bpy.data.worlds[name])
    # create a new world data block
    bpy.ops.world.new()
    bpy.context.scene.world = bpy.data.worlds["World"]

    purge_orphans()


### Generating Aggregates 

def create_sphere(location, radius=1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location)
    sphere = bpy.context.object
    return sphere

def random_unit_vector():
    theta = random.uniform(0, 2 * math.pi)
    phi = random.uniform(0, math.pi)
    x = math.sin(phi) * math.cos(theta)
    y = math.sin(phi) * math.sin(theta)
    z = math.cos(phi)
    return Vector((x, y, z))

def find_new_position(positions, radius, jump_chace = 0.5):
    if len(positions) > 1 and random.random() < jump_chace:
        base_pos = random.choice(positions[:-1])  # Choose a random previous sphere, not the last one
    else:
        base_pos = positions[-1]  # Choose the last placed sphere
    
    direction = random_unit_vector()
    new_pos = base_pos + direction * 2 * radius
    return new_pos

def create_aggregate(center, radius, num_spheres, jump_chance=0.5, density=1.0):
    positions = [center]
    spheres = []
    spheres.append(create_sphere(center, radius))

    for _ in range(1, num_spheres):
        while True:
            new_pos = find_new_position(positions, radius, jump_chance)
            no_overlap = True

            for pos in positions:
                if (new_pos - pos).length < 2 * radius:
                    no_overlap = False
                    break

            if no_overlap:
                spheres.append(create_sphere(new_pos, radius))
                positions.append(new_pos)
                break
    
    # Join all spheres into one mesh
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = spheres[0]
    bpy.ops.object.select_all(action='DESELECT')
    
    for sphere in spheres:
        sphere.select_set(True)
    
    bpy.context.view_layer.objects.active = spheres[0]
    bpy.ops.object.join()  # Join all selected spheres into one mesh

    aggregate = bpy.context.object

    # Add rigid body physics to the aggregate
    bpy.ops.rigidbody.object_add()
    aggregate.rigid_body.type = 'ACTIVE'
    aggregate.rigid_body.collision_shape = 'MESH'  # Set collision shape to mesh
    aggregate.rigid_body.friction = 0.25  # Adjust friction as needed

    # Calculate and set mass based on volume
    volume = (4/3) * math.pi * (radius**3) * num_spheres
    aggregate.rigid_body.mass = volume * density

    # Adjust collision bounds
    bpy.ops.object.select_all(action='DESELECT')
    aggregate.select_set(True)
    bpy.context.view_layer.objects.active = aggregate
    bpy.ops.rigidbody.shape_change(type='CONVEX_HULL')

    return aggregate

def distribute_on_sphere(n, r):
    indices = np.arange(0, n, dtype=float) + 0.5

    phi = (np.sqrt(5.0) - 1.0) / 2.0  # golden ratio
    y = 2*r * (1 - (indices / n)) - r  # y varies from -r to r
    radius = np.sqrt(r*r - y*y)  # radius at y
    theta = 2 * np.pi * phi * indices

    x, z = radius * np.cos(theta), radius * np.sin(theta)

    return list(zip(x, y, z))  # return as a list of tuples

def generate_force_field(strength):
    
    bpy.context.scene.gravity = (0, 0, 0)

    center_point = Vector((0,0,0))

    # Create a new force field object
    bpy.ops.object.effector_add(type='FORCE', location=center_point)

    # Get the force field object
    force_field = bpy.context.object

    # Set the strength of the force field (negative values attract)
    force_field.field.strength = strength

    # Set the maximum distance of the force field's effect (0 means no maximum)
    force_field.field.distance_max = 0.0
    
    return force_field 

### Running Simulation 

def bounding_sphere(objects, mode='BBOX'):
    # return the bounding sphere center and radius for objects (in global coordinates)
    if not isinstance(objects, list):
        objects = [objects]
    points_co_global = []
    if mode == 'GEOMETRY':
        # GEOMETRY - by all vertices/points - more precis, more slow
        for obj in objects:
            points_co_global.extend([obj.matrix_world @ vertex.co for vertex in obj.data.vertices])
    elif mode == 'BBOX':
        # BBOX - by object bounding boxes - less precis, quick
        for obj in objects:
            points_co_global.extend([obj.matrix_world @ Vector(bbox) for bbox in obj.bound_box])

    def get_center(l):
        return (max(l) + min(l)) / 2 if l else 0.0

    x, y, z = [[point_co[i] for point_co in points_co_global] for i in range(3)]
    b_sphere_center = Vector([get_center(axis) for axis in [x, y, z]]) if (x and y and z) else None
    b_sphere_radius = max(((point - b_sphere_center) for point in points_co_global)) if b_sphere_center else None
    return b_sphere_center, b_sphere_radius.length

def estimate_aggregate_volume(objects):
    
    total_volume = 0
    
    for obj in objects:
        if obj.data is not None:
            obj.data.update()
            
            # Create a BMesh object 
            bm = bmesh.new()
            
            # Load the mesh into the BMesh
            bm.from_mesh(obj.data)
            
            # Calculate the volume 
            volume = bm.calc_volume()
            
            # Clean up the BMMesh object 
            bm.free
            
            total_volume += volume
            
    return total_volume

def run_simulation(csv_filename, final_frame):

    start_time = time.time()

    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']

    aggregate_volume = estimate_aggregate_volume(mesh_objects)

    with open(csv_filename, 'w', newline='') as csvfile:

        fieldnames = ['time', 'aggregate_volume', 'bounding_radius', 'packing_fraction']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()

        for t in range(final_frame):
            bpy.context.scene.frame_set(t)
            
            if t%25==0:
                print(t)
            
            mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
            
            b_sphere_co, b_sphere_radius = bounding_sphere(
                objects=mesh_objects,
                mode='GEOMETRY'
            )

            bounding_sphere_volume = (4/3)*pi*(b_sphere_radius**3)
        
            writer.writerow({'time':t, 'aggregate_volume':aggregate_volume, 'bounding_radius': b_sphere_radius, 'packing_fraction':aggregate_volume/bounding_sphere_volume})

    final_time = time.time()-start_time
    print('Single Run: {final_time} sec'.format(final_time=final_time))
    
### Exporting to obj file 

def export_to_obj(obj_filename):
    # Deselect all objects
    bpy.ops.object.select_all(action='DESELECT')

    # Select all mesh objects
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.select_set(True)

    # Export selected objects as a single .obj file
    bpy.ops.export_scene.obj(filepath=obj_filename, use_selection=True)

## Particles 

num_primary_particles = [2, 5, 8, 15]
num_aggregates = [500, 650, 800]
jump_chance = [0.25, 0.50, 0.75]

#num_primary_particles = [2, 5]
#num_aggregates = [10]
#jump_chance = [0.5]

initial_placement_radius = 50
primary_particle_radius = 1
primary_particle_density = 1.5

## Force Field 
strength = -500

## Sim 

final_frame = 800


n_runs = len(num_primary_particles)*len(num_aggregates)*len(jump_chance)
itt = 0

total_start_time = time.time()

for n_primary in num_primary_particles:
    for n_aggregates in num_aggregates:
        for j_chance in jump_chance:
            clean_scene()
            bpy.context.scene.frame_set(0)
            
            save_name = r'D:\zachariah_group\packing\aggregate_data_Np_{npp}_Na_{na}_jc{jc}'.format(npp=n_primary, na=n_aggregates, jc=j_chance)
            print(save_name)

            save_name = save_name.replace('.', 'p')

            csv_file_name = save_name+'.csv'
            obj_file_name = save_name+'.obj'

            aggregate_locations = distribute_on_sphere(n_aggregates, initial_placement_radius)

            for i in range(len(aggregate_locations)):
                aggregate = create_aggregate(Vector(aggregate_locations[i]), primary_particle_radius, n_primary, j_chance, primary_particle_density)
                
            force_field = generate_force_field(strength)

            # Uncomment if you want to run simulation
            run_simulation(csv_file_name, final_frame)

            export_to_obj(obj_file_name)

            itt += 1
            print('{pct_complete}% Complete !'.format(pct_complete=(itt/n_runs)*100))
            
            bpy.ops.object.select_all(action='DESELECT')

print('Total Time: {total_time_hrs} hrs'.format(total_time_hrs=(time.time()-total_start_time)/3600))





