import bpy
import bmesh
import random
import math
from mathutils import Vector
import numpy as np
import csv
from math import pi

D = bpy.data
C = bpy.context

# Delete all current objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

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

def find_new_position(positions, radius):
    if len(positions) > 1 and random.random() < 0.50:
        base_pos = random.choice(positions[:-1])  # Choose a random previous sphere, not the last one
    else:
        base_pos = positions[-1]  # Choose the last placed sphere
    
    direction = random_unit_vector()
    new_pos = base_pos + direction * 2 * radius
    return new_pos

def create_aggregate(center, radius, num_spheres):
    positions = [center]
    spheres = []
    spheres.append(create_sphere(center, radius))

    for _ in range(1, num_spheres):
        while True:
            new_pos = find_new_position(positions, radius)
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
    aggregate.rigid_body.friction = 1.0  # Adjust friction as needed

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


bpy.ops.object.select_all(action='DESELECT')

primary_particle_radius = 0.5  # Radius of each sphere
num_primary_particles = 5 # Number of spheres per aggregate

num_aggregates = 100
initial_placement_radius = 50
aggregate_locations = distribute_on_sphere(num_aggregates, initial_placement_radius)

for i in range(len(aggregate_locations)):
    aggregate = create_aggregate(Vector(aggregate_locations[i]), primary_particle_radius, num_primary_particles)

bpy.context.scene.gravity = (0, 0, 0)

center_point = Vector((0,0,0))

# Create a new force field object
bpy.ops.object.effector_add(type='FORCE', location=center_point)

# Get the force field object
force_field = bpy.context.object

# Set the strength of the force field (negative values attract)
force_field.field.strength = -50.0

# Set the maximum distance of the force field's effect (0 means no maximum)
force_field.field.distance_max = 0.0
