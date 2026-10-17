"""Independent float32 projection/clamp reference over the actual matrix tail."""
import itertools
import math

from tools.experiments import game_overlay_projection as source
from tools.tests import game_view_point_projection_oracle as point
from tools.tests.game_animation_timeline_oracle import bits,floating

put,read,STACK=point.put,point.read,point.STACK
MASK,BASE,MATRICES,OUTPUT,LIMITS=0xFFFFFFFF,point.BASE,point.MATRICES,0x800DDDE8,0x800A7280
VIEWS=point.VIEWS
XYZ=((1.25,-2.5,3.75),(0.,-0.,-1.),(1.,1.,1.),(10001.,-10001.,0.),
    (9999.9990234375,-9999.9990234375,2.),(math.nan,math.inf,-math.inf))


def signed(v):return v if v<0x80000000 else v-0x100000000


def divide(a,b):
    x,y=floating(a),floating(b)
    if not y:return bits(math.nan if not x or math.isnan(x) else math.copysign(math.inf,x*math.copysign(1.,y)))
    return bits(x/y)


def fixture(view=0,mode=0,xyz=XYZ[0],pattern=0,alias=0,bounds=0):
    memory,_=point.fixture(0,xyz=xyz,pattern=pattern)
    old=point.MATRICES;matrix=(MATRICES+view*64)&MASK
    values=[read(memory,old+i*4) for i in range(16)]
    for i,value in enumerate(values):put(memory,(matrix+i*4)&MASK,value)
    output=(OUTPUT+view*8)&MASK;row=(VIEWS+view*384)&MASK
    if alias==1:row=(output-16)&MASK
    elif alias==2:row=(output-12)&MASK
    memory.update({(row+i)&MASK:0xA5 for i in range(384)})
    for at,value in ((12,141.5),(16,103.25),(36,2.5),(44,-3.75)):
        put(memory,(row+at)&MASK,bits(value))
    for i in range(-16,32):memory.setdefault((output+i)&MASK,0xA5)
    put(memory,BASE,(row-view*384)&MASK)
    for at,value in enumerate((10000.,-10000.,-10000.) if not bounds else (10.,-3.,-9.)):
        put(memory,LIMITS+at*4,bits(value))
    return memory,(mode&MASK,*(v if isinstance(v,int) else bits(v) for v in xyz),view&MASK)


def reference(initial,args):
    memory=dict(initial);mode,x,y,z,view=args;calls=[];packet=None;transformed=None
    if mode==0:
        matrix=(MATRICES+view*64)&MASK;result=[]
        for axis in range(4):
            values=[read(memory,(matrix+i*16+axis*4)&MASK) for i in range(4)]
            result.append(point.add(point.add(point.mul(values[0],x),point.mul(values[1],y)),
                point.add(point.mul(values[2],z),values[3])))
        x,y,_,w=result;transformed=tuple(result)
        if floating(w)==0.0:w=bits(1.)
        row=(read(memory,BASE)+view*384)&MASK
        x=divide(point.mul(read(memory,(row+12)&MASK),x),w)
        y=divide(point.mul(read(memory,(row+16)&MASK),y),w)
        x=point.add(x,read(memory,(row+12)&MASK))
        y=point.sub(read(memory,(row+16)&MASK),y)
        x=point.add(x,read(memory,(row+44)&MASK))
        y=point.add(y,read(memory,(row+36)&MASK))
        packet=(matrix,args[1],args[2],args[3]);calls=[packet]
    else:row=(read(memory,BASE)+view*384)&MASK
    upper=read(memory,LIMITS)
    if floating(upper)<floating(x):lower=read(memory,LIMITS+4);x=upper
    else:
        lower=read(memory,LIMITS+8)
        if floating(x)<floating(lower):x=lower
    if floating(upper)<floating(y):y=upper
    elif floating(y)<floating(lower):y=lower
    output=(OUTPUT+view*8)&MASK
    put(memory,output,point.sub(x,read(memory,(row+12)&MASK)))
    put(memory,(output+4)&MASK,point.sub(y,read(memory,(row+16)&MASK)))
    return memory,packet,transformed


def corpus():
    for view,mode,xyz,pattern in itertools.product((0,1,3,-1,0x10001,0x80000000),(0,1,0xFFFFFFFF),XYZ,range(9)):
        yield fixture(view,mode,xyz,pattern)
    for view,mode,alias,xyz,bounds in itertools.product((0,1,3,-1),(0,1),(1,2),XYZ,(0,1)):
        yield fixture(view,mode,xyz,1,alias,bounds)


class ProjectionOracle(point.PointProjectionOracle):
    def __init__(self,words,memory,args,helper,phase=0,entry=source.ENTRY,connected=None):
        super().__init__(words,memory,args,helper,phase,entry,connected)
        self.packet_snapshots=[]

    def record_call(self,target):
        if target==point.TAIL:
            args=self.arguments(8);self.calls.append((target,args));self.events.append(('CALL',target,args))
            self.packet_snapshots.append((self.r[29],self.get(self.r[29]+0x24,4),args))
            self.observations.append((self.f[12],self.f[14]))
            assert self.observations[-1]==args[1:3]
        elif target==source.ENTRY:
            args=self.arguments(5);self.calls.append((target,args));self.events.append(('CALL',target,args))
        else:raise ValueError('Unexpected overlay projection call: '+hex(target))

    def hook(self,target):raise ValueError('Actual matrix tail must execute')
