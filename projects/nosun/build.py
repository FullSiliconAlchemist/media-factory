"""NoSun cultivation hall. All dimensions are metres, Z is up, north is +Y."""
import math
import random

import bpy
from mathutils import Vector
from math import cos, sin, pi

meshes = {}
section = None


def collection(name):
    global section
    section = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(section)


def place(name, data, pos):
    obj = bpy.data.objects.new(name, data)
    section.objects.link(obj)
    obj.location = pos
    return obj


def solid(name, pos, vertices, faces, mat, key=None, bevel=0):
    key = (key, mat.name) if key else None
    mesh = meshes.get(key)
    if mesh is None:
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        mesh.materials.append(mat)
        if key:
            meshes[key] = mesh
    obj = place(name, mesh, pos)
    if bevel:
        mod = obj.modifiers.new("Machined edges", "BEVEL")
        mod.width, mod.segments = bevel, 2
        obj.modifiers.new("Face normals", "WEIGHTED_NORMAL")
    return obj


def box(name, pos, size, mat, bevel=0):
    a,b,c = [v/2 for v in size]
    verts = [(x,y,z) for z in (-c,c) for y in (-b,b) for x in (-a,a)]
    faces = [(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
    return solid(name,pos,verts,faces,mat,("plate",size),bevel)


def drum(name, pos, radius, height, mat, axis="Z", top=None, sides=48):
    top = radius if top is None else top
    verts = [(r*cos(i*2*pi/sides),r*sin(i*2*pi/sides),z)
             for r,z in ((radius,-height/2),(top,height/2)) for i in range(sides)]
    faces = [(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
    faces += [tuple(reversed(range(sides))),tuple(range(sides,2*sides))]
    obj = solid(name,pos,verts,faces,mat,("spun",radius,height,top,sides))
    for f in list(obj.data.polygons)[:sides]:
        f.use_smooth = True
    if axis == "Y":
        obj.rotation_euler.x = pi/2
    if axis == "X":
        obj.rotation_euler.y = pi/2
    return obj


def rod(name, a, b, radius, mat):
    direction = Vector(b)-Vector(a)
    obj = drum(name,(Vector(a)+Vector(b))/2,radius,direction.length,mat,sides=12)
    obj.rotation_euler = direction.to_track_quat("Z","Y").to_euler()
    return obj


def label(body, pos, size, mat, align="CENTER"):
    font = bpy.data.curves.new(body,"FONT")
    font.body, font.size, font.align_x = body,size,align
    font.space_character = 1.08
    font.materials.append(mat)
    obj = place(body,font,pos)
    obj.rotation_euler.x = pi/2
    return obj


def material(name, color, metal=0, rough=.4, glow=0, texture=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color,1)
    mat.use_nodes = True
    tree = mat.node_tree
    p = tree.nodes.get("Principled BSDF")
    for slot,value in [("Base Color",(*color,1)),("Metallic",metal),("Roughness",rough),
                       ("Emission Color",(*color,1)),("Emission Strength",glow)]:
        p.inputs[slot].default_value = value
    if texture:
        n = tree.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = 32
        ramp = tree.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (.21,.21,.21,1)
        ramp.color_ramp.elements[1].color = (.71,.71,.71,1)
        tree.links.new(n.outputs["Fac"],ramp.inputs[0])
        tree.links.new(ramp.outputs[0],p.inputs["Roughness"])
        bump = tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .16
        bump.inputs["Distance"].default_value = .005
        tree.links.new(n.outputs["Fac"],bump.inputs["Height"])
        tree.links.new(bump.outputs[0],p.inputs["Normal"])
    return mat


def glass(name,color,opacity):
    mat = material(name,color,.45,.16)
    tree = mat.node_tree
    mix = tree.nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = opacity
    tree.links.new(tree.nodes.new("ShaderNodeBsdfTransparent").outputs[0],mix.inputs[1])
    tree.links.new(tree.nodes.get("Principled BSDF").outputs[0],mix.inputs[2])
    tree.links.new(mix.outputs[0],tree.nodes.get("Material Output").inputs["Surface"])
    mat.surface_render_method = "BLENDED"
    return mat


def area(name,pos,target,color,power,size):
    data = bpy.data.lights.new(name,"AREA")
    data.energy,data.color,data.shape,data.size = power,color,"DISK",size
    obj = place(name,data,pos)
    if name == "Actinic downlight":
        data.use_custom_distance = True
        data.cutoff_distance = 2.8
        data.use_shadow = False
    obj.rotation_euler = (Vector(target)-Vector(pos)).to_track_quat("-Z","Y").to_euler()


def crop(x,y,z,rng,greens,scale):
    # Individual plants have folded, cupped leaves with a raised central vein.
    for idx,(dx,dy) in enumerate([(0,0),(.46,.13),(-.42,.18),(.05,-.45)]):
        verts, faces, tones = [],[],[]
        for j in range(13):
            angle = j*2.4+rng.uniform(-.15,.15)
            length = rng.uniform(.30,.48) * (1 if j<8 else .72)
            rise = rng.uniform(.19,.4) + (.19 if j>=8 else 0)
            start = len(verts)
            strips = 14
            across = (-1.0, -.52, -.042, .042, .52, 1.0)
            for k in range(strips+1):
                t = k/strips
                width = .145 * sin(pi*t**1.25)**.78 + .002
                for side in across:
                    edge = abs(side)
                    lateral = side*width*(1+.13*cos(k*2+j)*edge)
                    radial = length*t + .026*edge*sin(t*pi)
                    h = rise*sin(t*pi*.68) + edge*width*.43
                    h += .028*cos(k*1.9+j)*edge**3*sin(t*pi)
                    verts.append((radial*cos(angle)-lateral*sin(angle),radial*sin(angle)+lateral*cos(angle),h))
            stride = len(across)
            for k in range(strips):
                for n in range(stride-1):
                    a = start+stride*k+n
                    faces.append((a,a+stride,a+stride+1,a+1))
                    tones.append(3 if n==2 and k<strips-2 else j%3)
        obj = solid("Brassica / rosette", (x+dx*scale,y+dy*scale,z),verts,faces,greens[0])
        obj.scale = (scale,)*3
        for mat in greens[1:]:
            obj.data.materials.append(mat)
        for face,tone in zip(obj.data.polygons,tones):
            face.material_index,face.use_smooth = tone,True


def build(plan):
    rng = random.Random(plan["seed"])
    width,length,height = plan["environment"]["dimensions_m"]
    w,l = width/2,length/2
    palette,lighting = plan["palette"],plan["lighting"]
    steel = material("Brushed stainless",(.32,.39,.40),.78,texture=True)
    iron = material("Graphite / powder coat",(.052,.077,.082),.64,texture=True)
    panel = material("Oxide teal / enamel",(.12,.22,.22),.54,texture=True)
    concrete = material("Cast basalt concrete",(.22,.21,.19),texture=True)
    ochre = material("Safety ochre / baked enamel",palette["enamel"],.46,texture=True)
    ink = material("Stencil / bone",(.88,.82,.63),glow=.25)
    violet = material("Actinic LED",palette["grow"],glow=5)
    warm = material("Tungsten diffuser",palette["task"],glow=6)
    blue = material("Telemetry phosphor",(.15,.85,.76),glow=2)
    screen = material("Instrument glass",(.009,.038,.042),.35)
    fluid = material("Return / nutrient water",(.028,.35,.34),.3,.13,.22)
    clear = glass("Acrylic / observation shell",(.45,.69,.74),.08)
    greens = [material("Chard / "+n,c,.07,.36) for n,c in
              [("sage",(.26,.47,.12)),("jade",(.05,.27,.10)),("lime",(.30,.53,.11)),("midrib",(.48,.65,.25))]]
    collection("01  |  Pressure envelope")
    box("Subfloor",(0,0,-.22),(width,length,.4),concrete)
    box("Soffit",(0,0,height+.14),(width,length,.28),concrete)
    box("North bulkhead",(0,l,.5*height),(width,.38,height),concrete)
    for side in (-1,1):
        box("Retaining wall",(side*w,0,height/2),(.36,length,height),concrete)
    for y in range(-16,18,4):
        box("Transverse roof frame",(0,y,height-.26),(width,.32,.48),iron,.04)
        for side in (-1,1):
            x = side*(w-.38)
            box("Buttress",(x,y,2.65),(.54,.55,5.3),iron,.06)
            rod("Sloped haunch",(x,y,4.7),(x-side*1.45,y,height-.25),.32,steel)
            box("Access lining",(x,y+1.85,2.03),(.14,3.42,3.54),panel,.06)
            box("Bulkhead marker",(x-side*.11,y+1.8,2.82),(.08,2.9,.085),ochre)
    collection("02  |  Ventilation and nutrient mains")
    for x in plan["services"]["vent_centers_x_m"]:
        drum("Galvanized supply duct",(x,0,height-1.18),.55,length-.5,steel,"Y")
        for y in range(-17,18,2):
            drum("Spiral seam",(x,y,height-1.18),.568,.065,iron,"Y")
        for y in (-10,-2,6,14):
            box("Damper housing",(x,y,height-1.75),(1.03,.94,.3),iron,.05)
            for k in range(6):
                box("Diffuser fin",(x,y-.36+k*.14,height-1.91),(.91,.052,.05),steel)
    for x in plan["services"]["water_centers_x_m"]:
        for r,mat,name in [(.13,clear,"Borosilicate sight main"),(.087,fluid,"Nutrient stream")]:
            drum(name,(x,0,.73),r,length-1,mat,"Y")
        for y in range(-16,17,2):
            drum("Compression union",(x,y,.73),.15,.14,steel,"Y")
    collection("03  |  Raised service aisle")
    aisle = plan["aisle"]["width_m"]
    deck = plan["aisle"]["deck_height_m"]
    for k in range(int(length)):
        y = -l+k+.5
        box("Removable tread",(0,y,deck-.12),(aisle,.986,.24),iron,.018)
        for side in (-1,1):
            box("Edge marking",(side*(aisle/2-.09),y,deck+.006),(.055,.81,.012),ochre)
            for i in range(4):
                box("Drain slot",(side*(aisle/2-.32),y-.30+i*.2,deck+.008),(.23,.038,.012),screen)
    for y in range(-15,16,3):
        for side in (-1,1):
            x = side*(aisle/2-.05)
            box("Rail stanchion",(x,y,.89),(.068,.068,1.1),steel,.009)
            if y<15:
                rod("Safety rail",(x,y,1.43),(x,y+3,1.43),.042,ochre)
                rod("Mid rail",(x,y,.99),(x,y+3,.99),.022,steel)
    pods = plan["pods"]
    r,h = pods["radius_m"],pods["height_m"]
    for row,y in enumerate(pods["rows_y_m"]):
        for col,x in enumerate(pods["columns_x_m"]):
            code = f"{chr(65+col)}{row+1:02d}"
            collection("Vessel  |  "+code)
            for name,z,rad,d,mat,upper in [
                ("Isolation foot",.09,.76,.16,iron,.76),("Reservoir",.22,.80,.23,panel,1),
                ("Reservoir rim",.35,1,.055,steel,1),("Service casing",.43,1,.14,ochre,.96),
                ("Nutrient bed",.51,.96,.04,iron,.96),("Inspection sleeve",.72,.95,.40,clear,.95),
                ("Canopy seal",.927,1,.045,iron,1),("Grow ring",.946,1.015,.024,violet,1.015),
                ("Luminaire cowl",.977,1.04,.055,panel,.94),("Canopy lid",1.013,.94,.024,steel,.83)]:
                drum(name,(x,y,z*h),rad*r,d*h,mat,top=upper*r)
            for angle in (pi/4,3*pi/4,5*pi/4,7*pi/4):
                px,py = x+.965*r*cos(angle),y+.965*r*sin(angle)
                box("Canopy tie",(px,py,.73*h),(.059,.063,.44*h),steel,.009)
            # Bolted lid and an off-centre service hatch break up the spun silhouette.
            drum("Access hatch",(x,y,h*1.036),.38*r,.063,iron,top=.36*r)
            drum("Hatch insert",(x,y,h*1.052),.31*r,.026,panel)
            for i in range(8):
                phi = i*pi/4
                drum("Captive hex bolt",(x+.73*r*cos(phi),y+.73*r*sin(phi),h*1.029),.040,.032,iron,sides=6)
            for sx in (-1,1):
                px,py = x+sx*.69*r,y-.67*r
                box("Full spectrum LED blade",(px,py,.755*h),(.028,.031,.24*h),violet)
            drum("Feed valve",(x,y-r*.96,.29*h),.104,.12,iron,"Y")
            drum("Valve index",(x,y-r*1.035,.29*h),.071,.035,ochre,"Y",sides=8)
            side = 1 if x>0 else -1
            main = min(plan["services"]["water_centers_x_m"],key=lambda pipe: abs(pipe-x))
            if abs(x-main) < 2*r:
                rod("Metered feed",(main,y,.73),(x-side*.9*r,y,.73),.067,steel)
                drum("Regulator",(main,y,.85),.092,.13,ochre)
            for dx,dy in [(0,0),(.46,.13),(-.42,.18),(.05,-.45)]:
                drum("Net cup rim",(x+dx*r,y+dy*r,h*.53),.18*r,.055,steel)
                drum("Root plug",(x+dx*r,y+dy*r,h*.543),.15*r,.038,iron)
            crop(x,y,h*.55,rng,greens,r)
            box("Serial plate",(x,y-r,.43*h),(.65,.042,.21),iron,.012)
            label("NS / "+code,(x,y-r-.024,.407*h),.108,ink)
            area("Actinic downlight",(x,y,h*.91),(x,y,0),(.54,.115,.83),lighting["pod_watts"],1.32*r)
    collection("04  |  Process control")
    sy = plan["services"]["station_y_m"]
    box("Control dais",(0,sy,.22),(6.5,4.6,.44),iron,.08)
    for x in (-1.5,0,1.5):
        box("Cabinet plinth",(x,sy,.99),(1.42,.89,1.17),panel,.08)
        obj = box("Angled console",(x,sy-.14,1.64),(1.48,1.1,.18),ochre,.05)
        obj.rotation_euler.x = .12
        box("Monitor frame",(x,sy+.13,2.04),(1.35,.14,.67),iron,.045)
        box("Monitor",(x,sy+.05,2.04),(1.24,.022,.55),screen)
        for i in range(9):
            v = rng.uniform(.06,.30)
            box("Flow histogram",(x-.5+i*.103,sy+.032,1.86+v/2),(.055,.008,v),blue)
    box("Enamel signboard",(0,l-.42,4.21),(9.5,.22,2.48),panel,.08)
    label("N O S U N",(0,l-.55,4.08),1.15,ink)
    depth = plan["environment"]["depth_below_desert_m"]
    label(f"SUBSURFACE CULTIVATION    /    LEVEL  -{depth} M",(0,l-.55,3.53),.225,ink)
    for side in (-1,1):
        box("Sign edge lamp",(side*4.47,l-.55,4.2),(.048,.05,1.95),warm)
    collection("05  |  Task luminaires")
    # A suspended bay marker gives the entrance a human-scale landmark.
    bx,by,bz = -2.97,-9.1,4.50
    box("Bay marker casing",(bx,by,bz),(2.56,.12,.81),iron,.045)
    box("Bay marker stripe",(bx-1.13,by-.068,bz),(.105,.018,.67),ochre)
    label("GROW HALL",(bx-1.01,by-.075,bz+.12),.205,ink,"LEFT")
    label("04   /   BRASSICA",(bx-1.01,by-.075,bz-.22),.205,ink,"LEFT")
    for off in (-1,1):
        rod("Sign hanger",(bx+off,by,bz+.4),(bx+off,by,height),.017,steel)
    for side in (-1,1):
        x = side*6.1
        box("Filter bank",(x,l-.43,3.56),(2.45,.30,4.16),iron,.12)
        for k in range(14):
            box("Filter louvre",(x,l-.62,1.75+k*.259),(2.14,.18,.10),steel,.02)
    for y in (-13,-5,3,11):
        for side in (-1,1):
            x = side*2.1
            box("Suspended housing",(x,y,height-1.03),(.38,2.8,.21),iron,.04)
            box("Prismatic lens",(x,y,height-1.15),(.24,2.6,.045),warm)
            for off in (-1,1):
                rod("Drop hanger",(x,y+off,height-.94),(x,y+off,height),.024,steel)
            area("Warm aisle practical",(x,y,height-1.23),(x*.6,y,.5),palette["task"],lighting["ceiling_watts"],2.8)
    area("Bulkhead wash",(0,l-5,5.5),(0,l,4),palette["task"],650,5)
    for y in (-12,-3,6,14):
        for side in (-1,1):
            area("Cool service fill",(side*7.7,y,4.6),(side*2,y+1,1.1),palette["cool"],270,3.5)
    scene = bpy.context.scene
    world = bpy.data.worlds.new("Subsurface ambient")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes.get("Background").inputs[0].default_value = (.035,.05,.062,1)
    world.node_tree.nodes.get("Background").inputs[1].default_value = .27
    collection("06  |  Air and optics")
    mist = bpy.data.materials.new("Suspended condensate")
    mist.use_nodes = True
    nodes = mist.node_tree.nodes
    nodes.remove(nodes.get("Principled BSDF"))
    vol = nodes.new("ShaderNodeVolumeScatter")
    vol.inputs["Density"].default_value = lighting["haze_density"]
    vol.inputs["Anisotropy"].default_value = .35
    mist.node_tree.links.new(vol.outputs[0],nodes.get("Material Output").inputs["Volume"])
    obj = box("Atmosphere bounds",(0,0,height/2),(width,length,height),mist)
    obj.display_type = "WIRE"
    camera = plan["camera"]
    data = bpy.data.cameras.new("Aisle survey")
    obj = place("Aisle survey",data,camera["position_m"])
    obj.rotation_euler = (Vector(camera["target_m"])-obj.location).to_track_quat("-Z","Y").to_euler()
    data.lens = camera["lens_mm"]
    scene.camera = obj
    scene.eevee.shadow_pool_size = '1024'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.unit_settings.system = "METRIC"
