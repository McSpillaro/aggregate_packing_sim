import bpy
import random
import math
from mathutils import Vector
import numpy as np

# Delete all existing objects
def delete_all_objects():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

# Create a UV sphere
def create_sphere(location, radius=1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location)
    sphere = bpy.context.object

    # Apply Subdivision Surface modifier
#    bpy.ops.object.modifier_add(type='SUBSURF')
#    sphere.modifiers["Subdivision"].levels = 2
#    sphere.modifiers["Subdivision"].render_levels = 2
#    bpy.ops.object.shade_smooth()
    
    return sphere

# Generate a random unit vector
def random_unit_vector():
    theta = random.uniform(0, 2 * math.pi)
    phi = random.uniform(0, math.pi)
    x = math.sin(phi) * math.cos(theta)
    y = math.sin(phi) * math.sin(theta)
    z = math.cos(phi)
    return Vector((x, y, z))

# Find a new position for a sphere in the aggregate
def find_new_position(positions, radius):
    while True:
        base_pos = random.choice(positions)
        direction = random_unit_vector()
        new_pos = base_pos + direction * 2 * radius
        no_overlap = all((new_pos - pos).length >= 2 * radius for pos in positions)
        if no_overlap:
            return new_pos

# Create an aggregate of spheres
def create_aggregate(center, radius, num_spheres):
    positions = [center]
    spheres = [create_sphere(center, radius)]

    for _ in range(1, num_spheres):
        new_pos = find_new_position(positions, radius)
        spheres.append(create_sphere(new_pos, radius))
        positions.append(new_pos)

    # Join all spheres into one mesh
    bpy.ops.object.select_all(action='DESELECT')
    for sphere in spheres:
        sphere.select_set(True)
    
    bpy.context.view_layer.objects.active = spheres[0]
    bpy.ops.object.join()
    
    aggregate = bpy.context.active_object

    # Add rigid body physics to the aggregate
    bpy.ops.rigidbody.object_add()
    aggregate.rigid_body.type = 'ACTIVE'
    aggregate.rigid_body.collision_shape = 'SPHERE'
    aggregate.rigid_body.mass = 1.0 # Units of kg
    aggregate.rigid_body.friction = 1 # How much each particle "sticks" to each other
    aggregate.rigid_body.restitution = 0 # Controls "bounciness" (lower = less)
    aggregate.rigid_body.linear_damping = 10 # How much linear velocity slows over time (increase = faster)
    aggregate.rigid_body.angular_damping = 1 # How much rotational velocity slows over time (increase = faster)
    aggregate.rigid_body.use_margin = True
    
#    for obj in bpy.context.scene.objects:
#        if obj.type == 'SPHERE':
#            obj.scale = (radius, radius, radius)
    
    return aggregate

# Distribute positions on a sphere
def distribute_on_sphere(n, r):
    indices = np.arange(0, n, dtype=float) + 0.5
    phi = (np.sqrt(5.0) - 1.0) / 2.0  # golden ratio
    y = 2*r * (1 - (indices / n)) - r  # y varies from -r to r
    radius = np.sqrt(r*r - y*y)  # radius at y
    theta = 2 * np.pi * phi * indices
    x, z = radius * np.cos(theta), radius * np.sin(theta)
    return list(zip(x, y, z))  # return as a list of tuples

# Main script execution
def main():
    delete_all_objects() # Deletes all the objects

    scale_factor = 0.01  # Conversion factor for meters -> millimeters

    # CHANGE SETTINGS BELOW TO CHANGE SIMULATION PARAMETERS
    primary_particle_radius = 1 * scale_factor
    num_primary_particles = 2  # Number of spheres per aggregate
    num_aggregates = 10
    initial_placement_radius = 50 * scale_factor  # Placement radius for aggregates
    # end of changes...
    
    aggregate_locations = distribute_on_sphere(num_aggregates, initial_placement_radius)

    for location in aggregate_locations:
        create_aggregate(Vector(location), primary_particle_radius, num_primary_particles)
    
    # Set up the scene's gravity and force field
    bpy.context.scene.gravity = (0, 0, 0)  # No gravity
    bpy.context.scene.rigidbody_world.time_scale = 50  # Adjusts the speed of the simulation relative to real time

    # Create and configure the force field at the center
    center_point = Vector((0, 0, 0))
    bpy.ops.object.effector_add(type='FORCE', location=center_point)
    force_field = bpy.context.object
    force_field.field.strength = -100.0 * scale_factor  # Increase the strength
    force_field.field.falloff_type = 'SPHERE'
    force_field.field.use_max_distance = False
    force_field.field.falloff_power = 2.0

if __name__ == "__main__":
    main()
