"""Bounded list-depth behavior, aliases and IDO conversion-control sequences."""
from dataclasses import dataclass
import math
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating

ENTRY,PROJECT=0x1517EC1C,0x1509563C
NODE,CAMERA,VIEWS,OTHER_VIEWS,OUTPUT=0x30000,0x50000,0x60000,0x61000,0x70000
CAMERAS,VIEW_BASE,PAGE,TABLE=0x800DBFF0,0x800BE628,0x800BE9C0,0x80089630
RANGES=(6,0,5,0x20000,4,0x30000,3,0x38000,2,0x3C000,1,0x3E000,0,0x3F000,0,0x3F800)
DEPTHS=(0.25,1.5,1000.,67108864.,100000000.,134217728.,-0.03125,math.nan)
BLOCKS=((NODE-16,84),(CAMERA-16,2*0x9A0+32),(VIEWS-16,0x1A0),(OTHER_VIEWS-16,0x1A0),(OUTPUT-16,36))

@dataclass(frozen=True)
class Case:
    index:int
    mode:int
    alias:int
    phase:int
    fcsr:int=0

def cases():
    for i in range(256):
        for mode in range(4):yield Case(i,mode,(i+mode)%4,8*(i%2),0x00800004 if i%3 else 0)
def answer(c):return(1,0,2,0xFFFFFFFF,1)[(c.index+c.mode)%5]
def outputs(c):return(bits(17.25+c.index*0.125),bits(-9.5-c.mode),bits(DEPTHS[c.index%8]),bits(1. if c.index&8 else 2.))
def output_pointer(c):
    if c.alias==4:return STACK+c.phase+0x6C
    return(OUTPUT,NODE+0x2C,(OTHER_VIEWS if c.mode==3 else VIEWS)+16*((c.index&1)^int(c.mode==2))+0x44,NODE)[c.alias]
def fixture(c):
    m={STACK+i:(i*17+c.index*13+0xA5)&255 for i in range(-512,256)}
    for base,size in BLOCKS:m.update({base+i:(i*29+c.index*11+0x5A)&255 for i in range(size)})
    for i,w in enumerate(RANGES):put(m,TABLE+i*4,w)
    put(m,CAMERAS,CAMERA);put(m,VIEW_BASE,VIEWS);put(m,PAGE,c.index&1,1)
    positions=(0.,0.,0.)if c.index%4==3 else(1.,2.,2.)
    directions=((-1.,-1.,-1.),(1.,1.,1.),(2.,-1.,0.),(0.,0.,0.))[c.index%4]
    for i in range(3):
        put(m,NODE+4*i,bits(positions[i]));put(m,NODE+0x14+4*i,bits(directions[i]))
        put(m,CAMERA+0x2F8+4*i,bits(0.));put(m,CAMERA+0x9A0+0x2F8+4*i,bits(-2. if i==0 else 0.))
    put(m,NODE+0x20,bits(0.));put(m,NODE+0x2A,c.index*257,2);put(m,NODE+0x2E,4 if c.index&1 else 0,1)
    for base in(VIEWS,OTHER_VIEWS):
        for page in range(2):
            put(m,base+page*16+0x44,1 if page==0 else 0xFFFE,2)
            put(m,base+page*16+0x4C,0 if page==0 else 30,2)
    return m
def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+256}
def effect(m,c):
    put(m,NODE+0xC,outputs(c)[0]);put(m,NODE+0x10,outputs(c)[1])
    if c.mode==1:put(m,NODE+0x2E,read(m,NODE+0x2E,1)^4,1)
    if c.mode==2:
        put(m,CAMERAS,CAMERA+0x9A0);put(m,NODE+0x2A,(c.index*257)^65535,2)
        put(m,PAGE,(c.index&1)^1,1);put(m,NODE,bits(3.))
    if c.mode==3:
        put(m,VIEW_BASE,OTHER_VIEWS);put(m,NODE+0x14,bits(2.))
def mul(a,b):return bits(floating(a)*floating(b))
def add(a,b):return bits(floating(a)+floating(b))
def sub(a,b):return bits(floating(a)-floating(b))
def divide(a,b):
    x,y=floating(a),floating(b)
    return bits(x/y if y else math.nan if not x else math.copysign(math.inf,x*math.copysign(1.,y)))
def signed_half(w):return(w^32768)-32768
def converted(value):
    v=floating(value)
    return math.trunc(v)&0xFFFFFFFF if math.isfinite(v)and-1.<v<4294967296. else 0xFFFFFFFF
def expected_fcsr(c):return 0x00400004 if c.mode==3 else c.fcsr
def reference(initial,c):
    m=dict(initial);sp=STACK+c.phase-72
    args=tuple(read(m,NODE+4*i)for i in range(3))+(NODE+12,NODE+16,sp+0x2C,sp+0x28,bits(4000.))
    effect(m,c);calls=[(PROJECT,args)]
    if answer(c)!=1:return m,calls,0,None
    if read(m,NODE+0x2E,1)&4:
        base=read(m,CAMERAS);d=[sub(read(m,NODE+i*4),read(m,base+0x2F8+i*4))for i in range(3)]
        square=add(add(mul(d[0],d[0]),mul(d[1],d[1])),mul(d[2],d[2]))
        length=bits(math.sqrt(floating(square)))
        dot=add(add(mul(d[0],read(m,NODE+20)),mul(d[1],read(m,NODE+24))),mul(d[2],read(m,NODE+28)))
        if floating(divide(dot,length))<floating(read(m,NODE+32)):return m,calls,1,None
    sample=read(m,NODE+0x2A,2);shift,base=RANGES[2*(sample>>13):2*(sample>>13)+2]
    put(m,output_pointer(c),(base+(((sample>>2)&2047)<<shift))>>3)
    vp=read(m,VIEW_BASE)+16*read(m,PAGE,1)
    scale=bits(float(signed_half(read(m,vp+0x44,2))));translate=bits(float(signed_half(read(m,vp+0x4C,2))))
    ratio=divide(outputs(c)[2],outputs(c)[3]);value=mul(add(mul(ratio,scale),translate),bits(32.))
    put(m,NODE+0x2C,converted(value)&65535,2)
    return m,calls,1,value

class DepthOracle(TimingOracle):
    def __init__(self,words,memory,c):
        self.case=c;super().__init__(words,memory,phase=c.phase,entry=ENTRY,arguments=(NODE,output_pointer(c)))
        self.fcsr=c.fcsr;self.conversions=[]
    def execute(self,w):
        op,rs,fn=w>>26,w>>21&31,w&63
        if op==17 and(rs in(2,6)or(rs==16 and fn==36)):
            AreaOracle.execute(self,w)
            if rs==16:self.conversions.append((self.current_pc,self.fcsr))
        elif op==17 and rs==16 and fn==4:self.f[w>>6&31]=bits(math.sqrt(floating(self.f[w>>11&31])))
        else:super().execute(w)
    def record_call(self,target):
        assert target==PROJECT,hex(target)
        args=(self.f[12],self.f[14],self.r[6],self.r[7],*(read(self.memory,self.r[29]+16+i*4)for i in range(4)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        args=self.calls[-1][1];c=self.case;effect(self.memory,c)
        put(self.memory,args[5],outputs(c)[2]);put(self.memory,args[6],outputs(c)[3])
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=answer(c)
        self.fcsr=expected_fcsr(c)

def run(words,retail,selected=None):
    seen=[set(),set()];count=0;paths=set()
    for c in selected or cases():
        initial=fixture(c);want,calls,result,value=reference(initial,c);models=[]
        for side,body in enumerate((words,retail)):
            model=DepthOracle(body,initial,c).run()
            assert public(model.memory)==public(want),(c,side,'public')
            assert model.calls==calls and model.r[2]==result,(c,side,'call/return')
            assert model.fcsr==expected_fcsr(c),(c,side,'saved conversion control')
            seen[side].update(model.visits);models.append(model)
            if model.conversions:paths.add(len(model.conversions))
        assert models[0].memory==models[1].memory,(c,'complete private bytes')
        count+=1
    return dict(cases=count,visited_words=[len(s)for s in seen],unreachable_word_indices=[i for i in range(135)if ENTRY+4*i not in seen[0]],
        conversion_path_lengths=sorted(paths),frame_and_incoming_bytes_equal=True,FP_rounding='binary32 nearest',
        bounded_conversion_control=True,arithmetic_exception_flags_or_priority_qualified=False,hardware_or_gameplay_claim=False)

def run_caller(words,retail,rom):
    import struct
    entry=0x1517E3C0;window=struct.unpack_from('>4I',rom,0x1AB870)
    class Caller(DepthOracle):
        def __init__(self,body,memory,c):
            super().__init__(body,memory,c)
            self.code.update({ENTRY+4*i:w for i,w in enumerate(body)})
            self.code.update({entry+4*i:w for i,w in enumerate(window)})
            self.entry=entry;self.r[19]=1;self.entry_calls=[]
        def record_call(self,target):
            if target==ENTRY:self.entry_calls.append(tuple(self.arguments(2)))
            else:super().record_call(target)
    count=0
    for index in(0,1,2,3,4,5,7,16,32,64,127,128,254,255):
        for mode in range(4):
            for phase in(0,8):
                c=Case(index,mode,4,phase,0x00800004);initial=fixture(c)
                want,calls,result,value=reference(initial,c);models=[]
                for body in(words,retail):
                    model=Caller(body,initial,c)
                    try:model.run()
                    except KeyError as error:assert error.args==((0x1517E3D4 if result else 0x1517E3D0),)
                    else:raise AssertionError('Caller boundary not reached')
                    assert model.entry_calls==[(NODE,STACK+phase+0x6C)]
                    assert public(model.memory)==public(want)and model.calls==calls
                    assert model.r[2]==result and model.r[15]==read(want,STACK+phase+0x6C)
                    assert model.r[29]==STACK+phase and model.fcsr==expected_fcsr(c)
                    models.append(model)
                assert models[0].memory==models[1].memory
                count+=1
    return dict(cases=count,original_caller_words=4,target_body_words=135,complete_parent_execution_qualified=False,
        unchanged_output_on_early_return_observed=True,helper_models=True)
