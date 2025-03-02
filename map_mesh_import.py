import bpy
import json
import mathutils
from mathutils import Euler
import math
import os

# This is the base dir that contains all the unpacked assets - unpack using the latest ACL compatible build UE Viewer
base_dir = r"C:\Users\mithu\Downloads\umodel_win32\\"

# This is a subdirectory where you can insert additional parts of the path to the assets
asset_sub_dir = ""

# This is the path to the JSON file that contains the map data - you can extract this from .umap files using FModel.exe
map_json = [
    r"C:\Users\mithu\Downloads\FModel\Output\Exports\LiS\Content\Maps\Episode01\Sequence04\E1_4A_CHouseFront_GRC.json"
]

# importer toggles
import_static = True
import_lights = False # enable to also import lights

# Import types supported by the script
static_mesh_types = [
    'StaticMeshComponent',
#    'InstancedStaticMeshComponent' # buggy, positions wrong, seems to be used with splines as well
]
light_types = [
    'SpotLightComponent',
    'AnimatedLightComponent',
    'PointLightComponent'
]

def split_object_path(object_path):
    # For some reason ObjectPaths end with a period and a digit.
    # This is kind of a sucky way to split that out.
        
    path_parts = object_path.split(".")
    
    if len(path_parts) > 1:
        # Usually works, but will fail If the path contains multiple periods.
        return path_parts[0]
    
    # Nothing to do
    return object_path
    

class StaticMesh:
    entity_name = ""
    import_path = ""
    pos = [0, 0, 0]
    rot = [0, 0, 0]
    scale = [1, 1, 1]
    
    # these are just properties to help with debugging
    no_entity = False
    no_file = False
    no_mesh = False
    no_path = False
    base_shape = False
    
    
    def __init__(self, json_entity, base_dir):
        self.entity_name = json_entity.get("Outer", 'Error')

        props = json_entity.get("Properties", None)
        if not props:
            print('Invalid Entity: Lacking property')
            self.no_entity = True
            return None
        
        if not props.get("StaticMesh", None):
            print('Invalid Property: does not contain a static mesh')
            self.no_mesh = True
            return None

        object_path = props.get("StaticMesh").get("ObjectPath", None)
        
        if not object_path or object_path == '':
            print('Invalid StaticMesh: does not contain ObjectPath.')
            self.no_path = True
            return None

        if 'BasicShapes' in object_path:
            # What is a BasicShape? Do we need these?
            print('This is a BasicShape - skipping for now')
            self.base_shape = True
            return None
        
        objpath = split_object_path(object_path)
        self.import_path = base_dir + asset_sub_dir + objpath + ".gltf"
        print('Mesh Path', self.import_path)
        self.no_file = not os.path.exists(self.import_path)

        if props.get("RelativeLocation", False):
            pos = props.get("RelativeLocation")
            self.pos = [pos.get("X")/100,pos.get("Y")/-100,pos.get("Z")/100]
        
        if props.get("RelativeRotation", False):
            rot = props.get("RelativeRotation")
            self.rot = [rot.get("Roll"),rot.get("Pitch")*-1,rot.get("Yaw")*-1]
        
        if props.get("RelativeScale3D", False):
            scale = props.get("RelativeScale3D")
            self.scale = [scale.get("X", 1),scale.get("Y", 1),scale.get("Z", 1)]
        
        return None
    
    @property
    def invalid(self):
        return self.no_path or self.no_file or self.no_entity or self.base_shape or self.no_mesh
        

    def import_staticmesh(self, collection):
        if self.invalid:
            print('Refusing to import due to failed checks.')
            return False
        # Import the file and apply transforms
        bpy.ops.import_scene.gltf(filepath=self.import_path)
        imported_obj = bpy.context.object
        
        imported_obj.name = self.entity_name
        imported_obj.scale = (self.scale[0], self.scale[1], self.scale[2])
        imported_obj.location = (self.pos[0], self.pos[1], self.pos[2])
        imported_obj.rotation_mode = 'XYZ'
        imported_obj.rotation_euler = Euler((math.radians(self.rot[0]), math.radians(self.rot[1]), math.radians(self.rot[2])), 'XYZ')
        collection.objects.link(imported_obj)
        bpy.context.scene.collection.objects.unlink(imported_obj)

        print('StaticMesh imported:', self.entity_name)
        return imported_obj


class GameLight:
    entity_name = ""
    type = ""

    pos = [0, 0, 0]
    rot = [0, 0, 0]
    scale = [1, 1, 1]

    energy = 1000

    no_entity = False

    def __init__(self, json_entity):
        self.entity_name = json_entity.get("Outer", 'Error')
        self.type = json_entity.get("SpotLightComponent", "SpotLightComponent")

        props = json_entity.get("Properties", None)
        if not props:
            print('Invalid Entity: Lacking property')
            self.no_entity = True
            return None
        
        if props.get("RelativeLocation", False):
            pos = props.get("RelativeLocation")
            self.pos = [pos.get("X")/100,pos.get("Y")/-100,pos.get("Z")/100]
        
        if props.get("RelativeRotation", False):
            rot = props.get("RelativeRotation")
            self.rot = [rot.get("Roll"),rot.get("Pitch")*-1,rot.get("Yaw")*-1]
        
        if props.get("RelativeScale3D", False):
            scale = props.get("RelativeScale3D")
            self.scale = [scale.get("X", 1),scale.get("Y", 1),scale.get("Z", 1)]

        #TODO: expand this method with more properties for the specific light types
        # Problem: I don't know how values for UE lights map to Blender's light types.
    
    def import_light(self, collection):
        if self.no_entity:
            print('Refusing to import due to failed checks.')
            return False
        print('importing light')
        if self.type == 'SpotLightComponent':
            light_data = bpy.data.lights.new(name=self.entity_name, type='SPOT')
        if self.type == 'PointLightComponent':
            light_data = bpy.data.lights.new(name=self.entity_name, type='POINT')
        
        light_obj = bpy.data.objects.new(name=self.entity_name, object_data=light_data)
        light_obj.scale = (self.scale[0], self.scale[1], self.scale[2])
        light_obj.location = (self.pos[0], self.pos[1], self.pos[2])
        light_obj.rotation_mode = 'XYZ'
        light_obj.rotation_euler = Euler((math.radians(self.rot[0]), math.radians(self.rot[1]), math.radians(self.rot[2])), 'XYZ')
        collection.objects.link(light_obj)
        bpy.context.scene.collection.objects.link(light_obj)


# SCRIPT STARTS DOING STUFF HERE
for map in map_json:
    print('Processing file', map)

    if not os.path.exists(map):
        print('File not found, skipping.', map)
        continue

    json_filename = os.path.basename(map)
    import_collection = bpy.data.collections.new(json_filename)
    
    bpy.context.scene.collection.children.link(import_collection)

    with open(map) as file: 
        json_object = json.load(file)
        print("-------------============================-------------")

        # Handle the different entity types
        for entity in json_object:
            if not entity.get('Type', None):
                continue

            if import_lights and entity.get('Type') in light_types:
                print(entity)
                light = GameLight(entity)
                light.import_light(import_collection)

            if import_static and entity.get('Type') in static_mesh_types:
                static_mesh = StaticMesh(entity, base_dir)
                # TODO: optimize by instancing certain meshes
                static_mesh.import_staticmesh(import_collection)
                continue
print('Done.')