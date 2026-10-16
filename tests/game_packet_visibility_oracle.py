"""Float32 rectangle reference and existing bounded guest instruction oracle."""
from tools.experiments import game_packet_visibility as source
from tools.tests import game_visible_depth_oracle as depth

base=depth.previous
bits,floating,rounded,put,read=base.bits,base.floating,base.rounded,base.put,base.read
STACK,PACKET,STATUS,DESCRIPTOR=base.STACK,base.PACKET,depth.STATUS,0x32000
SCALE_X,SCALE_Y,OUTPUT=0x800380A0,0x800380A4,0x800D2C70
VIEW_FIELDS=(0x14,0x18,0x1C,0x20,0x24,0x28,0x2C,0x30)


def view_values(i):
    return (.25+i*.5,.5+i*.25,1.25+i*.5,2.+i*.75,-80.,80.,-100.,100.)


def fixture(extents=(1,1),dimensions=(2,2),position=(0.,0.),divisor=2.,projected=1,frame=0,
        scales=(1.,1.),alias=0):
    memory,_,_=depth.fixture()
    memory.update({DESCRIPTOR+i:0xA5 for i in range(16)})
    for i,v in enumerate(extents):
        put(memory,PACKET+6+i*2,v,2)
    put(memory,PACKET+16,DESCRIPTOR)
    for i,v in enumerate(dimensions):
        put(memory,DESCRIPTOR+4+i*2,v,2)
    for i in range(2):
        for at,v in zip(VIEW_FIELDS,view_values(i)):
            put(memory,base.VIEWS+i*0x180+at,bits(v))
    put(memory,base.source.FRAME_INDEX,frame)
    put(memory,SCALE_X,bits(scales[0]))
    put(memory,SCALE_Y,bits(scales[1]))
    for i in range(7):
        put(memory,OUTPUT+i*4,0xA5A5A5A5)
    status=(STATUS,PACKET+4,PACKET+8,DESCRIPTOR+4,SCALE_X,OUTPUT,
        base.VIEWS+0x2C,base.source.FRAME_INDEX)[alias]
    return memory,(PACKET,bits(position[0]),bits(position[1]),bits(divisor),projected&0xFFFFFFFF,status)


def reference(initial,args):
    memory=dict(initial)
    packet,x,y,divisor,projected,visible=args
    put(memory,visible,0)
    extentX=base.half(read(memory,packet+6,2))
    if not extentX:
        return memory
    extentY=base.half(read(memory,packet+8,2))
    if not extentY:
        return memory
    sx=floating(read(memory,SCALE_X))
    sy=floating(read(memory,SCALE_Y))
    sx,sy=rounded(float(extentX)*sx),rounded(float(extentY)*sy)
    view=(read(memory,base.source.VIEW_BASE)+read(memory,base.source.FRAME_INDEX)*0x180)&0xFFFFFFFF
    at=0x1C if projected else 0x14
    sx=rounded(sx*floating(read(memory,view+at)))
    sy=rounded(sy*floating(read(memory,view+at+4)))
    descriptor=read(memory,packet+16)
    inverse=base.edge.divide(1.,floating(divisor))
    width=rounded(rounded(float(read(memory,descriptor+4,2))*sx)*inverse)
    height=rounded(rounded(float(read(memory,descriptor+6,2))*sy)*inverse)
    left=rounded(floating(x)-rounded(width*.5))
    top=rounded(floating(y)-rounded(height*.5))
    if (floating(read(memory,view+0x2C))<=rounded(left+width) and
            left<floating(read(memory,view+0x30)) and
            floating(read(memory,view+0x24))<=rounded(top+height) and
            top<floating(read(memory,view+0x28))):
        put(memory,visible,1)
    for i,v in enumerate((sx,sy,left,top,floating(divisor),width,height)):
        put(memory,OUTPUT+i*4,bits(v))
    return memory


def run(words,memory,args,phase=0,**kwargs):
    return base.edge.EdgeOracle(words,memory,args,phase=phase,entry=source.ENTRY,**kwargs).run()


def connected_reference(initial,args,transformed,phase=0):
    private=STACK+phase-0x48
    outputs=tuple(private+i for i in (0x44,0x40,0x3C,0x38))
    memory,active=base.project_reference(initial,outputs,transformed)
    if not active:
        put(memory,args[2],0)
        return memory,args[0]
    memory=reference(memory,(args[1],read(memory,outputs[0]),read(memory,outputs[1]),
        read(memory,outputs[3]),1,args[2]))
    if not read(memory,args[2]):
        return memory,args[0]
    scale=floating(read(memory,source.previous.SCALE))
    value=rounded(rounded(rounded(floating(read(memory,outputs[2]))/floating(read(memory,outputs[3])))*scale)+scale)
    for i,v in enumerate((0xE7000000,0,0xEE000000,(depth.unsigned(value)<<16)&0xFFFFFFFF)):
        put(memory,args[0]+i*4,v)
    return memory,args[0]+16
