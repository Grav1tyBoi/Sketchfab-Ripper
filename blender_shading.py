import bpy
import json
import bmesh
import math
from mathutils import Vector

folder_path = R""
model_name = ""
STL_export = False
STL_size = 100
quad_recreation = False
fbx_export = False

json_pfad = folder_path + f"\\mat_info.json"
tex_folder = folder_path + f"\\textures\\"
blend_file = folder_path + f"\\{model_name}.blend"
stl_file = folder_path + f"\\{model_name}.stl"
gltf_path = folder_path + f"\\{model_name}.gltf"


#cleanup
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for collection in bpy.data.collections:
    bpy.data.collections.remove(collection)
materials_to_remove = [mat for mat in bpy.data.materials]
for mat in materials_to_remove:
    bpy.data.materials.remove(mat)

def tris_to_quads_optimized():

    import sys
    import subprocess
    import importlib

    def install_pulp():
        python_exe = sys.executable
        try:
            subprocess.run([python_exe, "-m", "pip", "install", "pulp"], check=True)
            print("PuLP erfolgreich installiert.")
        except Exception as e:
            print(f"Fehler bei der Installation von PuLP: {e}")
            return False
        return True

    try:
        from pulp import PULP_CBC_CMD, LpMaximize, LpProblem, LpVariable, lpSum, value
    except ImportError:
        if install_pulp():
            importlib.invalidate_caches()
            import site
            import os
            user_site = site.getusersitepackages()
            if user_site not in sys.path:
                sys.path.append(user_site)
            roaming_site = os.path.expanduser(r"~\AppData\Roaming\Python\Python311\site-packages")
            if os.path.exists(roaming_site) and roaming_site not in sys.path:
                sys.path.append(roaming_site)
            try:
                from pulp import PULP_CBC_CMD, LpMaximize, LpProblem, LpVariable, lpSum, value
            except ImportError:
                print("PuLP konnte nicht importiert werden, obwohl Installation versucht wurde.")
                print(f"sys.path: {sys.path}")
                return
        else:
            print("PuLP konnte nicht installiert werden.")
            return

    if bpy.context.active_object.mode != 'EDIT':
        bpy.ops.object.mode_set(mode="EDIT")

    obj = bpy.context.edit_object
    bm = bmesh.from_edit_mesh(obj.data)
    bm.edges.ensure_lookup_table()

    def is_valid_edge(edge):
        return (
            edge.select
            and len(edge.link_faces) == 2
            and edge.link_faces[0].select
            and edge.link_faces[1].select
            and len(edge.link_faces[0].edges) == 3
            and len(edge.link_faces[1].edges) == 3
        )

    m = LpProblem(sense=LpMaximize)
    edges = {}
    for edge in bm.edges:
        if not is_valid_edge(edge):
            continue
        ln = edge.calc_length()
        edges[edge] = LpVariable(f"v{len(edges):03}", cat="Binary"), ln

    if not edges:
        print(f"{obj.name}: Keine gültigen Dreieckspaare gefunden.")
        bm.free()
        return

    mx = max([i[1] for i in edges.values()], default=1)
    m.setObjective(lpSum(v * (1 + 0.1 * ln / mx) for edge, (v, ln) in edges.items()))

    for face in bm.faces:
        if len(face.edges) != 3:
            continue
        vv = [vln[0] for edge in face.edges if (vln := edges.get(edge)) is not None]
        if len(vv) > 1:
            m += lpSum(vv) <= 1

    solver = PULP_CBC_CMD(gapRel=0.01, timeLimit=60, msg=False)
    m.solve(solver)

    if m.status != 1:
        print(f"{obj.name}: Optimierung hat keine Lösung gefunden.")
    else:
        bpy.ops.mesh.select_all(action="DESELECT")
        n = 0
        for edge, (v, _) in edges.items():
            if value(v) > 0.5:
                edge.select_set(True)
                n += 1

        print(f"{obj.name}: {n} Kanten werden aufgelöst.")
        bpy.ops.mesh.dissolve_edges(use_verts=False)
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.mesh.select_face_by_sides(type="NOTEQUAL")
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.mode_set(mode="EDIT")
    bm.free()

def get_combined_dimensions_world(mesh_objects):
    if not mesh_objects:
        return None
    min_corner = Vector((float("inf"), float("inf"), float("inf")))
    max_corner = Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in mesh_objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ Vector(corner)
            min_corner = Vector((min(min_corner[i], world_corner[i]) for i in range(3)))
            max_corner = Vector((max(max_corner[i], world_corner[i]) for i in range(3)))
    return max_corner - min_corner

def apply_scale_only(mesh_objects):
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in mesh_objects:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

def scale_scene_uniform(mesh_objects, factor):
    for obj in mesh_objects:
        obj.scale = (obj.scale.x * factor, obj.scale.y * factor, obj.scale.z * factor)
    apply_scale_only(mesh_objects)

def normalize_scale_to_max_dimension(mesh_objects, max_mm):
    apply_scale_only(mesh_objects)
    dims = get_combined_dimensions_world(mesh_objects)
    if dims is None:
        return
    max_dim = max(dims)
    if 0 < max_dim <= 10.0:
        scale_scene_uniform(mesh_objects, 1000.0)
        dims = get_combined_dimensions_world(mesh_objects)
        max_dim = max(dims)
    if max_dim > max_mm and max_dim > 0:
        factor = max_mm / max_dim
        scale_scene_uniform(mesh_objects, factor)

bpy.ops.import_scene.gltf(
    filepath=gltf_path,
    guess_original_bind_pose= False,
    import_shading='NORMALS',
    bone_heuristic='TEMPERANCE'                                   
)

if str(quad_recreation) == "True":
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            tris_to_quads_optimized()
            obj.select_set(False)

if str(STL_export) == "True":
    bpy.ops.object.select_all(action='DESELECT')
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    for obj in mesh_objects:
        obj.select_set(True)
    if mesh_objects:
        bpy.context.view_layer.objects.active = mesh_objects[0]
        normalize_scale_to_max_dimension(mesh_objects, float(STL_size))
        bpy.ops.wm.stl_export(filepath=stl_file)

with open(json_pfad) as x:
    data = json.load(x)

def color_fac(active_channel):
    r, g, b, a = active_channel["color"]

    r = r * active_channel["factor"]
    g = g * active_channel["factor"]
    b = b * active_channel["factor"]

    active_channel["color"] = (r, g, b, a)
    return active_channel["color"]

for mat in data:
    material = bpy.data.materials.get(mat)
    if material is None:
        continue  
    
    material.use_nodes = True
    
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    
    #Cleanup
    nodes.clear()
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (600, 0)
    #Specular Workflow :c
    if "SpecularPBR" in data[mat]:
        print("Hate my Life")
        
        dbsdf_node = nodes.new(type='ShaderNodeBsdfDiffuse')
        dbsdf_node.location = (-300, 150)
        pbsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        pbsdf_node.location = (-300, 0)
        pbsdf_node.inputs['Metallic'].default_value = 1
        pbsdf_node.inputs['Specular IOR Level'].default_value = 1
        add_node = nodes.new(type='ShaderNodeAddShader')
        add_node.location = (0, 0)
        tbsdf_node = nodes.new(type='ShaderNodeBsdfTransparent')
        tbsdf_node.location = (0, 100)
        mix_node = nodes.new(type='ShaderNodeMixShader')
        mix_node.location = (300, 0)
        mix_node.inputs['Fac'].default_value = 1
        links.new(dbsdf_node.outputs['BSDF'], add_node.inputs[0])
        links.new(pbsdf_node.outputs['BSDF'], add_node.inputs[1])
        links.new(tbsdf_node.outputs['BSDF'], mix_node.inputs[1])
        links.new(add_node.outputs['Shader'], mix_node.inputs[2])
        links.new(mix_node.outputs['Shader'], output_node.inputs['Surface'])

        loaded_images = {}
        def createimage(path, location, outc, bsdf, fac = 1, colorspace = 'Non-Color', alpha = False ):
            global loaded_images
            image = loaded_images.get(path)
            if image is None:
                # Load the image if it's not already loaded
                image = bpy.data.images.load(path)
                # Store the loaded image in the dictionary
                loaded_images[path] = image

            if fac == 1:
                image_node = nodes.new(type='ShaderNodeTexImage')
                image_node.image = image
                image_node.location = (-700, location)
                if alpha == False:
                    links.new(image_node.outputs['Color'], bsdf.inputs[outc])
                else:
                    links.new(image_node.outputs['Alpha'], bsdf.inputs[outc])

            else:
                image_node = nodes.new(type='ShaderNodeTexImage')
                image_node.image = image
                image_node.location = (-1000, location)
                fac_node = nodes.new(type='ShaderNodeMix')
                fac_node.data_type = "RGBA"
                fac_node.location = (-700, location)
                fac_node.inputs['Factor'].default_value = fac
                fac_node.inputs['A'].default_value = (0,0,0,1)
                if alpha == False:
                    links.new(image_node.outputs['Color'], fac_node.inputs["B"])
                    links.new(fac_node.outputs['Result'], bsdf.inputs[outc])
                else:
                    links.new(image_node.outputs['Alpha'], fac_node.inputs["B"])
                    links.new(fac_node.outputs['Result'], bsdf.inputs[outc])
            image_node.image.colorspace_settings.name = colorspace
            image_node.image.alpha_mode = "CHANNEL_PACKED"
        
        for channel in data[mat]:
            active_channel = data[mat][channel]
            if channel == "Matcap":
                continue
            
            #Base Color
            elif channel == "DiffusePBR" or channel == "AlbedoPBR":
                if "texture" in active_channel:
                    image_path = tex_folder + active_channel["texture"]
                    createimage( image_path, 600, "Color", dbsdf_node, 1, "sRGB")
                elif "color" in active_channel:
                    dbsdf_node.inputs['Color'].default_value = active_channel["color"]
            
            #Specular Specular Workflow
            elif channel == "SpecularPBR":
                if "texture" in active_channel:
                    image_path = tex_folder + active_channel["texture"]
                    createimage( image_path, 0, "Base Color", pbsdf_node, active_channel["factor"], "sRGB")
                elif "color" in active_channel:
                    if active_channel["factor"] != 1:
                        active_channel["color"] = color_fac(active_channel)
                        
                    pbsdf_node.inputs['Base Color'].default_value = active_channel["color"]
                else:
                    pbsdf_node.inputs['Base Color'].default_value = active_channel["factor"]
            
            #Glossiness Specular Workflow
            elif channel == "GlossinessPBR":
                r = 1 - active_channel["factor"]
                dbsdf_node.inputs['Roughness'].default_value = r
                pbsdf_node.inputs['Roughness'].default_value = r

                
            #Roughness Specular Workflow
            elif channel == "RoughnessPBR":
                if "texture" in active_channel:
                    image_path = tex_folder + active_channel["texture"]
                    createimage( image_path, 300, "Roughness", pbsdf_node, active_channel["factor"])
                    createimage( image_path, 300, "Roughness", dbsdf_node, active_channel["factor"])
                elif "color" in active_channel:
                    r, g, b, a = active_channel["color"]
                    r = r * active_channel["factor"]

                    dbsdf_node.inputs['Roughness'].default_value = r
                    pbsdf_node.inputs['Roughness'].default_value = r
                else:
                    dbsdf_node.inputs['Roughness'].default_value = active_channel["factor"]
                    pbsdf_node.inputs['Roughness'].default_value = active_channel["factor"]

            #Normal
            elif channel == "NormalMap":
                if "texture" in active_channel:
                    image_node = nodes.new(type='ShaderNodeTexImage')
                    image_node.image = bpy.data.images.load(tex_folder + active_channel["texture"])
                    image_node.location = (-900, -600)
                    image_node.image.colorspace_settings.name = "Non-Color"
                    normal_map_node = nodes.new(type='ShaderNodeNormalMap')
                    normal_map_node.location = (-600, -650)
                    links.new(image_node.outputs['Color'], normal_map_node.inputs['Color'])
                    links.new(normal_map_node.outputs['Normal'], dbsdf_node.inputs['Normal'])
                    links.new(normal_map_node.outputs['Normal'], pbsdf_node.inputs['Normal'])
                    normal_map_node.inputs["Strength"].default_value = active_channel["factor"]
                else:
                    print("NO Texture?")

            #Opacity
            elif channel == "Opacity":
                material.blend_method = 'BLEND'
                if "texture" in active_channel:
                    image_path = tex_folder + active_channel["texture"]
                    createimage( image_path, -300, "Fac", mix_node, active_channel["factor"], "sRGB", True)
                elif "color" in active_channel:
                    r, g, b, a = active_channel["color"]
                    r = r * active_channel["factor"]
                    mix_node.inputs['Fac'].default_value = r
                else:
                    mix_node.inputs['Fac'].default_value = active_channel["factor"]
        
    
    
    
        
    else: #Metallic Workflow c:
        bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf_node.location = (0, 0)
        links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

        loaded_images = {}
        def createimage(path, location, outc, fac = 1, colorspace = 'Non-Color', alpha = False ):
            global loaded_images
            image = loaded_images.get(path)
            if image is None:
                image = bpy.data.images.load(path)
                loaded_images[path] = image

            if fac == 1:
                image_node = nodes.new(type='ShaderNodeTexImage')
                image_node.image = image
                image_node.location = (-400, location)
                if alpha == False:
                    links.new(image_node.outputs['Color'], bsdf_node.inputs[outc])
                else:
                    links.new(image_node.outputs['Alpha'], bsdf_node.inputs[outc])

            else:
                image_node = nodes.new(type='ShaderNodeTexImage')
                image_node.image = image
                image_node.location = (-700, location)
                fac_node = nodes.new(type='ShaderNodeMix')
                fac_node.data_type = "RGBA"
                fac_node.location = (-400, location)
                fac_node.inputs['Factor'].default_value = fac
                fac_node.inputs['A'].default_value = (0,0,0,1)
                if alpha == False:
                    links.new(image_node.outputs['Color'], fac_node.inputs["B"])
                    links.new(fac_node.outputs['Result'], bsdf_node.inputs[outc])
                else:
                    links.new(image_node.outputs['Alpha'], fac_node.inputs["B"])
                    links.new(fac_node.outputs['Result'], bsdf_node.inputs[outc])
            image_node.image.colorspace_settings.name = colorspace
            image_node.image.alpha_mode = "CHANNEL_PACKED"       
                    
        for channel in data[mat]:
            active_channel = data[mat][channel]
            if channel == "Matcap":
                continue
            
            #Base Color
            elif channel == "DiffusePBR" or channel == "AlbedoPBR":
                if "texture" in active_channel:
                    image_path = tex_folder + active_channel["texture"]
                    createimage( image_path, 600, "Base Color", active_channel["factor"], "sRGB")
                elif "color" in active_channel:
                    if active_channel["factor"] != 1:
                        active_channel["color"] = color_fac(active_channel)
                    bsdf_node.inputs['Base Color'].default_value = active_channel["color"]
            
            #Glossines Metalic Workflow
            elif channel == "GlossinessPBR":
                r = 1 - active_channel["factor"]
                bsdf_node.inputs['Roughness'].default_value = r
                
            #Rougness Metalic Workflow
            elif channel == "RoughnessPBR":
                if "texture" in active_channel:
                    image_path = tex_folder + active_channel["texture"]
                    createimage( image_path, 0, "Roughness", active_channel["factor"])
                elif "color" in active_channel:
                    r, g, b, a = active_channel["color"]
                    r = r * active_channel["factor"]
                    bsdf_node.inputs['Roughness'].default_value = r
                else:
                    bsdf_node.inputs['Roughness'].default_value = active_channel["factor"]
            
            #Metalic Metalic Workflow
            elif channel == "MetalnessPBR":
                if "texture" in active_channel:
                    image_path = tex_folder + active_channel["texture"]
                    createimage( image_path, 300, "Metallic", active_channel["factor"])
                elif "color" in active_channel:
                    r, g, b, a = active_channel["color"]
                    r = r * active_channel["factor"]
                    bsdf_node.inputs['Metallic'].default_value = r
                else:
                    bsdf_node.inputs['Metallic'].default_value = active_channel["factor"]
                
            #Specular Metalic Workflow
            elif channel == "SpecularF0":
                try:
                    if "texture" in active_channel:
                        image_path = tex_folder + active_channel["texture"]
                        createimage( image_path, 0, "Specular IOR Level", active_channel["factor"])
                    elif "color" in active_channel:
                        r, g, b, a = active_channel["color"]
                        r = r * active_channel["factor"]
                        bsdf_node.inputs['Specular IOR Level'].default_value = r
                    else:
                        bsdf_node.inputs['Specular IOR Level'].default_value = active_channel["factor"]
                except TypeError:
                    continue
                    
            #Emission
            elif channel == "EmitColor":
                bsdf_node.inputs["Emission Strength"].default_value = active_channel["factor"]
                if "texture" in active_channel:
                    image_path = tex_folder + active_channel["texture"]
                    createimage( image_path, -900, "Emission Color", 1, "sRGB")
                elif "color" in active_channel:
                    r, g, b, a = active_channel["color"]
                    r = r * active_channel["factor"]
                    g = g * active_channel["factor"]
                    b = b * active_channel["factor"]
                    bsdf_node.inputs['Emission Color'].default_value = (r, g, b, a)
            
            #Normal
            elif channel == "NormalMap":
                image_node = nodes.new(type='ShaderNodeTexImage')
                if "texture" in active_channel:
                    image_node.image = bpy.data.images.load(tex_folder + active_channel["texture"])
                    image_node.location = (-700, -600)
                    image_node.image.colorspace_settings.name = "Non-Color"
                    normal_map_node = nodes.new(type='ShaderNodeNormalMap')
                    normal_map_node.location = (-350, -650)
                    links.new(image_node.outputs['Color'], normal_map_node.inputs['Color'])
                    links.new(normal_map_node.outputs['Normal'], bsdf_node.inputs['Normal'])
                    normal_map_node.inputs["Strength"].default_value = active_channel["factor"]
                    
            #Opacity
            elif channel == "Opacity":
                material.blend_method = 'BLEND'
                if "texture" in active_channel:
                    image_path = tex_folder + active_channel["texture"]
                    createimage( image_path, -300, "Alpha", active_channel["factor"], "sRGB", True)
                elif "color" in active_channel:
                    r, g, b, a = active_channel["color"]
                    r = r * active_channel["factor"]
                    bsdf_node.inputs['Alpha'].default_value = r
                else:
                    bsdf_node.inputs['Alpha'].default_value = active_channel["factor"]

if str(fbx_export) == "True":
    bpy.ops.export_scene.fbx(filepath=folder_path + f"\\{model_name}.fbx", use_selection=False, path_mode='RELATIVE', apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', use_space_transform=True, axis_forward='-Z', axis_up='Y')

while bpy.ops.outliner.orphans_purge(do_recursive=True) != {'CANCELLED'}:
    pass
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=blend_file)