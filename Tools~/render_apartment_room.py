import bpy, math, json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1] / 'Sources~'
OUT = ROOT.parent / 'Packages/com.sizimityper.fake-interior-shader/Samples/Residential'
ROOT.mkdir(exist_ok=True)
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

def material(name,color,roughness=.65):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color,1)
    m.use_nodes = True
    m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*color,1)
    m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=roughness
    return m

wall=material('暖色の壁',(0.66,.63,.54))
floor=material('オーク床',(.32,.20,.105))
white=material('天井と照明',(.78,.77,.72))
oak=material('家具の木部',(.25,.14,.065))
fabric=material('グレージュの布',(.28,.30,.27))
dark=material('テレビ・金属',(.025,.035,.035),.35)
green=material('観葉植物',(.10,.22,.10))
paper=material('絵と本',(.60,.48,.30))

def box(name,position,size,mat,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=position)
    ob=bpy.context.object
    ob.name=name
    ob.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    ob.data.materials.append(mat)
    if bevel:
        modifier=ob.modifiers.new('家具の角','BEVEL')
        modifier.width=bevel
        modifier.segments=3
    return ob

# 窓全体4.47×2.10m、奥行き3.2mを正確な一点透視で撮影する。
W,H,D,C=4.47,2.1,3.2,3.2
box('床',(0,D/2,-.055),(W,D,.11),floor)
box('天井',(0,D/2,H+.055),(W,D,.11),white)
box('奥壁',(0,D+.055,H/2),(W,.11,H),wall)
for side in [-1,1]:
    box('側壁',(side*(W/2+.055),D/2,H/2),(.11,D,H),wall)
    box('側壁巾木',(side*(W/2-.01),D/2,.06),(.025,D,.12),oak)
box('奥巾木',(0,D-.01,.06),(W,.025,.12),oak)
# 床板の線を微細な形状で付け、元の部屋モデルを編集可能に保持する。
for x in range(-11,12):
    box('床板目地',(x*.19,D/2,.002),(.006,D,.004),oak)
box('ソファ脚',(1.1,2.52,.10),(1.65,.67,.20),oak,.01)
box('ソファ座',(1.1,2.51,.31),(1.8,.79,.28),fabric,.065)
box('ソファ背',(1.1,2.88,.68),(1.8,.18,.65),fabric,.065)
for x in [.24,1.96]:
    box('ソファ肘',(x,2.52,.53),(.15,.79,.46),fabric,.035)
for x in [.65,1.52]:
    cushion=box('クッション',(x,2.76,.75),(.48,.16,.4),white,.055)
    cushion.rotation_euler[1]=.10 if x<1 else -.10
box('ローテーブル脚',(.6,1.63,.19),(.8,.48,.38),oak,.015)
box('ローテーブル',(.6,1.63,.40),(1.1,.65,.06),oak,.03)
box('ラグ',(.65,1.72,.011),(2.1,1.4,.014),material('ラグ',(.37,.35,.30)))
box('テレビ台',(-1.34,2.98,.26),(1.35,.40,.51),oak,.025)
box('テレビ',(-1.34,2.94,.87),(1.02,.075,.59),dark,.01)
box('テレビ脚',(-1.34,2.92,.55),(.32,.13,.05),dark)
for x in [-1.85,-1.25,-.55]:
    box('額縁',(x,D-.045,1.56),(.43,.03,.43),oak,.008)
    box('絵',(x,D-.065,1.56),(.38,.012,.38),paper)
for index in range(5):
    box('本',(-1.84+index*.065,2.9,.62),(.045,.17,.22+index*.013),paper if index%2 else fabric)
box('鉢',(-2.03,2.50,.15),(.22,.22,.30),white,.025)
bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=.25,location=(-2.03,2.5,.53))
bpy.context.object.name='植物';bpy.context.object.scale=(.7,.7,1.1);bpy.context.object.data.materials.append(green)
box('天井灯',(0,1.9,H-.022),(.7,.55,.035),white,.02)

def area(name,position,target,energy,color,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.color=color;data.shape='RECTANGLE';data.size=size;data.size_y=size*.65
    ob=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(ob);ob.location=position
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    return data

day=area('窓からの明かり',(0,-.12,1.4),(0,2,1),170,(.83,.9,1),3.5)
lamp=area('室内灯',(0,1.7,H-.09),(0,1.7,0),65,(1,.83,.62),.85)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.world=bpy.data.worlds.new('室内環境');scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(.10,.13,.17,1)
scene.world.node_tree.nodes.get('Background').inputs[1].default_value=.25
camera_data=bpy.data.cameras.new('一点透視カメラ');camera=bpy.data.objects.new('一点透視カメラ',camera_data);scene.collection.objects.link(camera)
camera.location=(0,-C,H/2);camera.rotation_euler=(Vector((0,1,H/2))-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='PERSP';camera_data.sensor_fit='HORIZONTAL';camera_data.lens=36*C/W;camera_data.sensor_width=36
scene.camera=camera;scene.render.resolution_x=1536;scene.render.resolution_y=round(1536*H/W);scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'ApartmentRoomSource_v001.blend'))
for name,lit in [('ApartmentRoom_Day',False),('ApartmentRoom_Lit',True)]:
    day.energy=130 if not lit else 12
    lamp.energy=28 if not lit else 130
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
(ROOT/'room_spec.json').write_text(json.dumps({'width':W,'height':H,'depth':D,'cameraDistance':C,'backWallScale':C/(C+D),'resolution':[scene.render.resolution_x,scene.render.resolution_y],'method':'Blender Cycles scene rendering'},indent=2),encoding='utf-8')
print('ROOM_TEXTURES_COMPLETE',flush=True)
