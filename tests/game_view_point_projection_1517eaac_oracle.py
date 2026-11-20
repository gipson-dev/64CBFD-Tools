"""Independent bounded projection contract with aliasing and effectful helpers."""
from dataclasses import dataclass
import itertools
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating

ENTRY,BUILD,PROJECT=0x1517EAAC,0x15110360,0x150A7A00
INDEX,CAMERAS,VIEWS=0x80082FA4,0x800DBFF0,0x800BE628
CAMERA,VIEW,OUTPUT=0x30000,0x60000,0x70000
DEPTHS=(0,0x41200000,0x41200001,0x42C80000,0xC0400000,0x80000000,0x7FC12345)

@dataclass(frozen=True)
class Case:
    view:int
    pattern:int
    mode:int
    alias:int
    phase:int

def cases():
    for values in itertools.product(range(4),range(7),range(4),range(4),(0,8)):
        yield Case(*values)

def values(c):return tuple(bits(v)for v in((c.pattern-3)*1.25, -0.0 if c.pattern==0 else(c.pattern+1)*0.5,17.25))
def projected(c):return(bits((c.pattern-3)*0.375),bits((c.pattern+1)*-0.25),bits(77.5),DEPTHS[c.pattern])
def locations(c):
    if c.alias==1:return OUTPUT,OUTPUT
    if c.alias==2:return VIEW+((c.view+1)&3)*0x180+12,VIEW+((c.view+1)&3)*0x180+16
    if c.alias==3:return CAMERA+c.view*0x9A0+0x380,CAMERA+c.view*0x9A0+0x388
    return OUTPUT,OUTPUT+4
def fixture(c):
    m={STACK+i:(i*17+c.pattern*19+0xA5)&255 for i in range(-512,256)}
    for base,size in((CAMERA-16,4*0x9A0+32),(VIEW-16,4*0x180+32),(OUTPUT-16,48)):
        m.update({base+i:(i*29+c.pattern*11+0x5A)&255 for i in range(size)})
    put(m,INDEX,c.view);put(m,CAMERAS,CAMERA);put(m,VIEWS,VIEW)
    for i in range(4):
        for off,value in((0x380,(i+1)*0.125),(0x388,-(i+2)*0.25),(0x5EC,(i-2)*0.5)):
            put(m,CAMERA+i*0x9A0+off,bits(value))
        put(m,VIEW+i*0x180+12,bits((i+1)*80.25));put(m,VIEW+i*0x180+16,bits((i+1)*60.5))
    return m
def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+256}
def matrix_words(c):return[bits((i-7)*(c.pattern+1)*0.125)for i in range(16)]
def effect(m,c,target):
    if target==BUILD and c.mode&1:put(m,INDEX,(c.view+1)&3)
    if target==PROJECT and c.mode&2:
        # Scales must have been captured before this helper changes the view.
        view=read(m,INDEX)
        put(m,VIEW+view*0x180+12,bits(-123.5));put(m,VIEW+view*0x180+16,bits(999.25))
        put(m,INDEX,(view+2)&3)
def reference(initial,c):
    m=dict(initial);sp=STACK+c.phase-152;matrix=sp+0x38
    camera=read(m,CAMERAS)+read(m,INDEX)*0x9A0
    first=(read(m,INDEX),matrix,read(m,camera+0x388)^0x80000000,
           read(m,camera+0x380)^0x80000000,read(m,camera+0x5EC))
    effect(m,c,BUILD)
    view=read(m,VIEWS)+read(m,INDEX)*0x180
    sx,sy=read(m,view+12),read(m,view+16)
    second=(matrix,*values(c),sp+0x84,sp+0x80,sp+0x7C,sp+0x78)
    effect(m,c,PROJECT)
    x,y,z,w=projected(c)
    if floating(w)>10.0:
        inverse=bits(1.0/floating(w))
        x=bits(floating(bits(floating(x)*floating(sx)))*floating(inverse))
        y=bits(floating(bits(floating(y)*floating(sy)))*floating(inverse))
        ox=bits(floating(sx)+floating(x));oy=bits(floating(sy)-floating(y));result=1
    else:ox=oy=result=0
    for address,value in zip(locations(c),(ox,oy)):put(m,address,value)
    return m,[(BUILD,first),(PROJECT,second)],result

class ProjectionOracle(TimingOracle):
    def __init__(self,words,memory,c,fault=None):
        self.case=c
        super().__init__(words,memory,phase=c.phase,entry=ENTRY,arguments=(0xBAD00000,0xBAD00001,values(c)[2],*locations(c)))
        self.f[12],self.f[14]=values(c)[:2]
        self.root_fault=fault
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63==7:
            self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
            return
        super().execute(w)
    def record_call(self,target):
        assert target in(BUILD,PROJECT),hex(target)
        args=tuple(self.arguments(5 if target==BUILD else 8))
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        c=self.case;args=self.calls[-1][1]
        if target==BUILD:
            for i,v in enumerate(matrix_words(c)):put(self.memory,args[1]+i*4,v)
        else:
            # The same matrix storage is observed by both calls.
            assert tuple(read(self.memory,args[0]+i*4)for i in range(16))==tuple(matrix_words(c))
            for p,v in zip(args[4:],projected(c)):put(self.memory,p,v)
        effect(self.memory,c,target)
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]

def run(words,retail,selected=None):
    coverage=[set(),set()];count=0
    for c in selected or cases():
        initial=fixture(c);want,calls,result=reference(initial,c);models=[]
        for side,body in enumerate((words,retail)):
            got=ProjectionOracle(body,initial,c).run()
            assert public(got.memory)==public(want),(c,side,'public memory')
            assert got.calls==calls,(c,side,'helper ABI')
            assert got.r[2]==result,(c,side,'result')
            coverage[side].update(got.visits);models.append(got)
        assert models[0].memory==models[1].memory,(c,'complete private memory')
        count+=1
    return dict(cases=count,visited_words=[len(s)for s in coverage],
        unreachable_word_indices=[i for i in range(92)if ENTRY+i*4 not in coverage[0]],
        exact_passed_homes=True,complete_private_memory_equal=True,helper_models=True,
        full_parent_or_hardware_or_gameplay_claim=False,FP_exception_behavior_qualified=False)

def run_caller(words,retail,rom):
    """Execute the original float/stack argument setup and result branch only."""
    import struct
    entry=0x1517E37C;window=struct.unpack_from('>7I',rom,0x1AB82C)
    class Caller(ProjectionOracle):
        def __init__(self,body,memory,c):
            super().__init__(body,memory,c)
            self.code.update({ENTRY+i*4:w for i,w in enumerate(body)})
            self.code.update({entry+i*4:w for i,w in enumerate(window)})
            self.entry=entry;self.r[2]=0x71000;self.r[7],self.r[24]=locations(c)
            self.r[19]=1;self.entry_calls=[]
        def record_call(self,target):
            if target==ENTRY:
                self.entry_calls.append((self.f[12],self.f[14],self.r[6],self.r[7],read(self.memory,self.r[29]+16)))
            else:super().record_call(target)
    count=0
    for view,pattern,mode,alias,phase in itertools.product((0,3),(0,1,2,3,6),(0,3),range(4),(0,8)):
        c=Case(view,pattern,mode,alias,phase);initial=fixture(c)
        for i,v in enumerate(values(c)):put(initial,0x71000+4*i,v)
        want,calls,result=reference(initial,c)
        for body in(words,retail):
            model=Caller(body,initial,c)
            try:model.run()
            except KeyError as error:
                assert error.args==((0x1517E39C if result else 0x1517E398),),error
            else:raise AssertionError('Caller boundary not reached')
            assert model.entry_calls==[(*values(c),*locations(c))]
            assert model.calls==calls and model.r[2]==result and model.r[18]==255
            assert model.r[29]==STACK+phase and model.f[20:]==model.saved_f
            assert public(model.memory)==public(want)
        count+=1
    return dict(cases=count,original_caller_words=7,root_function_words=92,
        helper_models=True,complete_parent_execution_qualified=False)
