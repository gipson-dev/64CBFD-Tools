from pathlib import Path
import sys
from tools.experiments import game_actor_projection_scan_15036148_recovery as source
ROOT=source.ROOT
from dataclasses import dataclass
import json,struct
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK,put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
OUT=source.OUT;ENTRY=0x15036148;EXTENT=0x1507C3E0;SUBMIT=0x15035808
ACTORS=0x800CC2D0;VIEW_PTR=0x800DBFF0;VIEW=0x90000;ALT_VIEW=0x98000;SENTINEL=0x80097D74
FIELDS=(0,0x14,0x18,0x1C,0x28,0x118,0x180)
TOKEN=0xF0010000
@dataclass(frozen=True)
class Case:
    seed:int;gate:int;mode:int;phase:int
def cases():
    for i in range(768):yield Case(i,int(i%8==0),i%6,8*(i&1))
def fill_actor(m,i,seed,force=False):
    a=ACTORS+i*0x32C;p=(seed+i)%12
    values={0:1,0x14:(0x80000000,0x7FC12345,bits(float(i-12)))[(seed+i)%3],0x18:bits(40.),0x1C:bits(float(i*3-19)),0x28:bits(6.),0x118:bits(10.),0x180:bits(-10.)}
    for off,w in values.items():put(m,a+off,w)
    m[a+5]=i&1
    if not force:
        if p==0:put(m,a,0)
        elif p==1:m[a+5]=255
        elif p==2:put(m,a+0x118,0xC61C4000)
        elif p==3:put(m,a+0x118,bits(40.))
        elif p==4:put(m,a+0x180,bits(10.))
        elif p==5:put(m,a+0x28,bits(5.))
        elif p==6:put(m,a+0x28,bits(-1.))
        elif p==7:put(m,a+0x118,0x7FC12345)
        elif p==8:put(m,a+0x18,0x7FC12345)
        elif p==9:put(m,a+0x180,0x7FC12345)
        elif p==10:put(m,a+0x28,0x7F800000)
def fixture(c):
    m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-512,128)}
    for base,length in((ACTORS,26*0x32C),(VIEW,0x600),(ALT_VIEW,0x600)):
        m.update({base+i:0xA5 for i in range(length)})
    put(m,VIEW_PTR,VIEW);put(m,VIEW+0x5F0,c.gate);put(m,ALT_VIEW+0x5F0,1);put(m,SENTINEL,0xC61C4000)
    for i in range(26):fill_actor(m,i,c.seed)
    return m
def effect(m,c,target,args,ordinal,outputs):
    if target==EXTENT:
        i=(args[0]-ACTORS)//0x32C;a=args[0]
        value=(0,19,20,0x7FFF,0x8000,0xFFFF)[(c.seed+i)%6]
        for j,p in enumerate(outputs):
            v=value if j==0 else (c.seed+i*13+j*7)&65535
            m[p]=v>>8;m[p+1]=v&255
        if c.mode==1:put(m,a+0x118,bits(100.));put(m,a+0x180,bits(-40.))
        if c.mode==2:put(m,a+0x118,0x7FC12345 if ordinal&1 else bits(30.));put(m,a+0x180,bits(29.))
        if c.mode==3:
            if i<24:fill_actor(m,i+1,c.seed,True)
            put(m,VIEW_PTR,ALT_VIEW);put(m,VIEW+0x5F0,1)
        if c.mode==5:put(m,a+0x14,0x7FC12345);put(m,a+0x1C,0x80000000);put(m,a+0x18,bits(-999.))
    elif c.mode==4:
        i=args[1]
        if i<24:fill_actor(m,i+1,c.seed,True)
        for j,p in enumerate(outputs):v=(ordinal*17+j)&65535;m[p]=v>>8;m[p+1]=v&255
    return (0xB6000000+ordinal)&0xFFFFFFFF
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+128}
def reference(initial,c):
    m=dict(initial);trace=[];outputs=tuple(STACK+c.phase+x for x in(-6,-8,-10))
    def call(target,args):
        trace.append((target,tuple(args)));return effect(m,c,target,args,len(trace),outputs)
    if read(m,read(m,VIEW_PTR)+0x5F0)&1:return m,trace
    for i in range(25):
        a=ACTORS+i*0x32C;h=floating(read(m,a+0x118))
        if read(m,a)!=0 and m[a+5]in(0,1) and h!=-10000. and h<floating(read(m,a+0x18)) and floating(read(m,a+0x180))<h and 5.<floating(read(m,a+0x28)):
            call(EXTENT,(a,TOKEN,TOKEN+2,TOKEN+4))
            v=m[outputs[0]]*256+m[outputs[0]+1];signed=v if v<32768 else v-65536
            if float(signed)<floating(bits(floating(read(m,a+0x118))-floating(read(m,a+0x180)))):
                call(SUBMIT,(1,i,read(m,a+0x14),read(m,a+0x118),read(m,a+0x1C),0,0,bits(100.),bits(150.),bits(127.)))
    return m,trace
def hashseq(values):
    h=2166136261
    for v in values:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
    return h
def public_values(m):
    return [read(m,VIEW_PTR),read(m,VIEW+0x5F0),read(m,ALT_VIEW+0x5F0),*(m[ACTORS+i]for i in range(26*0x32C))]
class Oracle(TimingOracle):
    def __init__(self,words,memory,c):
        self.c=c;self.trace=[];self.boundaries=[];self.outputs=tuple(STACK+c.phase+x for x in(-6,-8,-10))
        super().__init__(words,memory,phase=c.phase,entry=ENTRY,arguments=())
    def record_call(self,target):
        assert target in(EXTENT,SUBMIT);args=list(self.arguments(4 if target==EXTENT else 10))
        if target==EXTENT:
            assert tuple(args[1:])==self.outputs,(args,self.outputs);args[1:]=[TOKEN,TOKEN+2,TOKEN+4]
        self.trace.append((target,tuple(args)));self.calls.append((target,tuple(args)))
        self.boundaries.append(bytes(self.memory[STACK+self.c.phase+i]for i in range(-152,16)))
    def hook(self,target):
        answer=effect(self.memory,self.c,target,self.trace[-1][1],len(self.trace),self.outputs)
        for i in range(4 if target==EXTENT else 10):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=answer;self.hi=self.lo=0xA5000010
def run():
    raw,refs=payload(OUT/'qualified-screen/candidate.o','func_15036148');anchors={n:0x80097D74 if n=='.rodata'else int(n.split('_')[1],16)for rows in refs.values()for _,n in rows}
    code=tuple(bound_blob(raw,refs,anchors));truth=struct.unpack_from('>112I',(ROOT/'conker/conker.us.bin').read_bytes(),0x635f8)
    seen=[set(),set()];count=calls=0
    for c in cases():
        initial=fixture(c);wanted,trace=reference(initial,c);models=[]
        for side,words in enumerate((code,truth)):
            model=Oracle(words,initial,c).run();assert model.trace==trace,(c,side,'trace',model.trace,trace)
            assert public(model.memory)==public(wanted),(c,side,'public');models.append(model)
            seen[side].update(pc for pc in model.visits if ENTRY<=pc<ENTRY+448)
        assert models[0].boundaries==models[1].boundaries,(c,'private call bytes')
        assert models[0].memory==models[1].memory,(c,'all final memory')
        count+=1;calls+=len(trace)
    assert list(map(len,seen))==[112,112]
    r=dict(cases=count,calls=calls,visited_words=list(map(len,seen)),private_bytes=168,complete_final_memory_equal_cases=count,
        private_call_boundaries_equal=calls,post_extent_reload=True,mutable_future_actors=True,signed_halfword=True,
        qNaN_signed_zero_infinity_cases=True,FCSR_emulation=False,matching_credit=0)
    (OUT/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
