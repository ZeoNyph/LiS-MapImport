import bpy
import os

def dedup_materials(material_name_to_replace, replacement_material_name):
    # replaces and deletes any duplicate materials in the scene

    materials = bpy.data.materials

    # Get the material to use as replacement
    replacement_material = materials.get(replacement_material_name)

    if replacement_material is None:
        print(f"Error: Material '{replacement_material_name}' not found.")
        return None
    
    # Iterate over all objects in the scene
    for obj in bpy.context.scene.objects:
        # Check if the object has a material slot with the material to replace
        for i, slot in enumerate(obj.material_slots):
            if slot.material is not None and slot.material.name == material_name_to_replace:
                # Replace the material with the replacement material
                slot.material = replacement_material
                print(f"Replaced material in object '{obj.name}', slot {i}.")


def search_directory(root_dir, file_name):
    # utility function to search for a file in a directory
    for subdir, dirs, files in os.walk(root_dir):
        for file in files:
            if file == file_name:
                file_path = os.path.join(subdir, file)
                return file_path
    return None

mat_dir = r"C:\Users\mithu\Downloads\umodel_win32\\" # add dir here

# Get all materials in the scene
materials = bpy.data.materials

# Iterate over all materials and print their names
for material in materials:
    if 'WorldGridMaterial' in material.name:
        #TODO: Also remove objects using this material
        bpy.data.materials.remove(material, do_unlink=True)
        continue
    
    # Disable Backface Culling - this will make the material double sided
    material.use_backface_culling = False

    mat_name = material.name
    split_matname = mat_name.split('.')
    
    # dedup material
    if len(split_matname) > 1:
        dedup_materials(material.name, split_matname[0])
        bpy.data.materials.remove(material, do_unlink=True)
        continue

    mat_name = split_matname[0]

    # Find the .mat file so we can pull the texture names out of it
    found_file = search_directory(mat_dir, mat_name + '.mat')
    if not found_file:
        print('No material found.')
        continue
    
    # TODO: this is ugly, clean it up
    diffuse_texturename = ''
    normal_texturename = ''
    spec_texturename = ''
    rough_texturename = ''
    with open(found_file) as mat_file:
        lines = mat_file.readlines()
        
        for line in lines:
            if line.startswith('Diffuse') or line.startswith('Normal') or line.startswith('SpecPower') or line.startswith('Other[0]'):
                splitline = line.split("=")
                if len(splitline) > 1:
                    if splitline[0] == 'Diffuse':
                        diffuse_texturename = splitline[1].strip()
                    if splitline[0] == 'Normal':
                        normal_texturename = splitline[1].strip()
                    if splitline[0] == 'SpecPower':
                        spec_texturename = splitline[1].strip()
                    if splitline[0].startswith('Other[') and splitline[1].endswith("R"):
                        rough_texturename = splitline[1].strip()
                    else: rough_texturename = diffuse_texturename[:len(diffuse_texturename)-1] + "R"


    if not diffuse_texturename and not normal_texturename:
        print('We have no textures. Skipping.')
        continue

    diffuse_texture_path = None
    normal_texture_path = None
    spec_texture_path = None
    rough_texture_path = None
    if diffuse_texturename != '':
        diffuse_texture_path = search_directory(mat_dir, diffuse_texturename + '.tga')
    if normal_texturename != '':
        normal_texture_path = search_directory(mat_dir, normal_texturename + '.tga')
    if spec_texturename != '':
        spec_texture_path = search_directory(mat_dir, spec_texturename + '.tga')
    if rough_texturename != '':
        rough_texture_path = search_directory(mat_dir, rough_texturename  + '.tga')
        print(rough_texture_path)

    # This convoluted mess is to set up the textures and connect all the material nodes
    
    # Create a new Principled BSDF shader node for the material
    # TODO: check if this node already exists
    
    shader_node = None
    
    if 'Decals' in material.name:
        shader_node = material.node_tree.nodes.new(type="ShaderNodeBsdfTransparent")
        
        if diffuse_texture_path is not None:
            print("DIFF: " + diffuse_texture_path)
            # Set the diffuse map for the material
            diffuse_texture = material.node_tree.nodes.new(type="ShaderNodeTexImage")
            diffuse_texture.image = bpy.data.images.load(diffuse_texture_path)
            material.node_tree.links.new(shader_node.inputs["Color"], diffuse_texture.outputs["Color"])
    else:   
        shader_node = material.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")

        if diffuse_texture_path is not None:
            print("DIFF: " + diffuse_texture_path)
            # Set the diffuse map for the material
            diffuse_texture = material.node_tree.nodes.new(type="ShaderNodeTexImage")
            diffuse_texture.image = bpy.data.images.load(diffuse_texture_path)
            material.node_tree.links.new(shader_node.inputs["Base Color"], diffuse_texture.outputs["Color"])
            material.node_tree.links.new(shader_node.inputs["Alpha"], diffuse_texture.outputs["Alpha"])

        if normal_texture_path is not None:
            # Set the normal map for the material
            normal_texture = material.node_tree.nodes.new(type="ShaderNodeTexImage")
            normal_texture.image = bpy.data.images.load(normal_texture_path)
            normal_texture.image.colorspace_settings.name = "Non-Color"
            normal_map_node = material.node_tree.nodes.new(type="ShaderNodeNormalMap")
            normal_map_node.inputs["Strength"].default_value = 1.0
            material.node_tree.links.new(shader_node.inputs["Normal"], normal_map_node.outputs["Normal"])
            
            ##
            # Create nodes to invert the green channel
            
            seperate_color = material.node_tree.nodes.new(type="ShaderNodeSeparateColor")
            invert_node = material.node_tree.nodes.new(type="ShaderNodeInvert")
            combine_color = material.node_tree.nodes.new(type="ShaderNodeCombineColor")
            
            # link remaining separate color inputs to combine color
            material.node_tree.links.new(combine_color.inputs["Red"], seperate_color.outputs["Red"])
            material.node_tree.links.new(combine_color.inputs["Blue"], seperate_color.outputs["Blue"])
            
            # link sep to invert
            material.node_tree.links.new(invert_node.inputs["Color"], seperate_color.outputs["Green"])
            # link invert to comb
            material.node_tree.links.new(combine_color.inputs["Green"], invert_node.outputs["Color"])
            
            # wire up the rest
            material.node_tree.links.new(seperate_color.inputs["Color"], normal_texture.outputs["Color"])   
            material.node_tree.links.new(normal_map_node.inputs["Color"], combine_color.outputs["Color"])

        if spec_texture_path is not None:
            print("SPEC:" + spec_texture_path)
            spec_texture = material.node_tree.nodes.new(type="ShaderNodeTexImage")
            spec_texture.image = bpy.data.images.load(spec_texture_path)
            spec_texture.image.colorspace_settings.name = "Non-Color"
            material.node_tree.links.new(shader_node.inputs[13], spec_texture.outputs["Color"])

        if rough_texture_path is not None:
            print("ROUGH: " + rough_texture_path)
            rough_texture = material.node_tree.nodes.new(type="ShaderNodeTexImage")
            rough_texture.image = bpy.data.images.load(rough_texture_path)
            rough_texture.image.colorspace_settings.name = "Non-Color"
            material.node_tree.links.new(shader_node.inputs[2], rough_texture.outputs["Color"])


    # Get the material output and wire it up to the shader node
    material_output = material.node_tree.nodes.get("Material Output")

    if material_output is None:
        print(f"Error: Material output node not found in material '{material.name}'.")

    material.node_tree.links.new(shader_node.outputs["BSDF"], material_output.inputs["Surface"])

print('Done')


# Remove objects without materials
# Iterate over all objects in the scene
for obj in bpy.context.scene.objects:
    # Check if the object has a material slot in the first position
    if len(obj.material_slots) > 0:
        # Check if the material slot in the first position is empty
        if obj.material_slots[0].material is None:
            # Object has no material assigned to the first slot
            print(f"Object '{obj.name}' has no material assigned to the first slot.")
            bpy.data.objects.remove(obj, do_unlink=True)
    else:
        # Object has no material slots
        print(f"Object '{obj.name}' has no material slots.")
