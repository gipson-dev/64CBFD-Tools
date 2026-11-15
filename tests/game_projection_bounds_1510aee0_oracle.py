"""Ordered projection model, pointer-home aliases and emitted memory prefixes."""
from dataclasses import dataclass
import itertools,json,math,struct
from tools.experiments import game_projection_bounds_1510aee0_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
MATRIX,OUTPUT=0x30000,0x50000
f32=lambda x:floating(bits(x))
def divide(a,b):return f32(a/b)if b else math.nan if not a else math.copysign(math.inf,a*math.copysign(1.,b))

def fixture(x,y,z,outputs=0,pattern=0,near=1.,far=10.,scale=1.,phase=0):
    m={STACK+i:(i*17+0x41)&255 for i in range(-512,512)}
    for p,n in((MATRIX,64),(OUTPUT,16),(0x3f800000,16),(0x3f400000,16)):
        for i in range(n):m[p+i]=0xa5
    for i in range(16):put(m,MATRIX+i*4,bits(1. if i in(0,5,10,15)else 0.))
    if pattern:
        for i,v in((0,1.25),(1,.25),(2,-.125),(4,.5),(5,1.5),(6,.125),(8,-.25),(9,.125),(10,1.),(12,.5),(13,-.25),(14,-1.)):put(m,MATRIX+i*4,bits(v))
    p=STACK+phase;ox,oy=((OUTPUT,OUTPUT+4),(0,OUTPUT+4),(OUTPUT,0),(OUTPUT,OUTPUT),(MATRIX,MATRIX+4),(0,0),(p-16,OUTPUT+4),(p+36,OUTPUT+4),(p+12,OUTPUT+4))[outputs]
    args=(MATRIX,*map(bits,(x,y,z,near,far,scale,scale)),ox,oy)
    for i,v in enumerate(args[4:],4):put(m,p+i*4,v)
    return m,args

def model(initial,args,phase=0):
    m=dict(initial);matrix,x,y,z,near,far,sx,sy,ox,oy=args;home=STACK+phase
    put(m,home+12,z);x,y,z,near,far,sx,sy=map(floating,(x,y,z,near,far,sx,sy))
    def transform(i):
        a,b,c,d=(floating(read(m,matrix+j*4))for j in(i,i+4,i+8,i+12))
        value=f32(a*x);value=f32(value+f32(b*y));value=f32(value+f32(c*z));return f32(d+value)
    depth=-transform(2)
    if depth<near:return 1,m,depth
    if far<depth:return 1,m,depth
    horizontal=f32(abs(transform(0))*sx)
    if depth<horizontal:return 1,m,depth
    vertical=f32(abs(transform(1))*sy);put(m,home-16,bits(vertical))
    if depth<vertical:return 1,m,depth
    if ox:put(m,ox,bits(f32(1.-divide(horizontal,depth))))
    oy=read(m,home+36)
    if oy:put(m,oy,bits(f32(1.-divide(floating(read(m,home-16)),depth))))
    return 0,m,depth

def corpus():
    for x,y,z,output,pattern,planes,scale in itertools.product((-2.,0.,2.),(-2.,0.,2.),(-1.,-4.,-10.,1.),range(6),range(2),((1.,10.),(0.,10.),(4.,4.)),(-1.,1.)):
        initial,args=fixture(x,y,z,output,pattern,*planes,scale);yield initial,args,0,True
    for output,phase in itertools.product((6,7,8),(0,8)):
        initial,args=fixture(0.,0.,-4.,output,phase=phase);yield initial,args,phase,False

class Oracle(FactoryOracle):
    def __init__(self,w,m,args,phase=0,entry=source.ENTRY,connected=None):
        super().__init__(w,m,Case(phase=phase),entry=entry,connected=connected,arguments=args)
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63 in(5,7):
            fs,fd=w>>11&31,w>>6&31;self.f[fd]=self.f[fs]&0x7fffffff if w&63==5 else self.f[fs]^0x80000000
        else:super().execute(w)
    def record_call(self,t):
        assert t==source.ENTRY;return
    def hook(self,t):raise AssertionError('Unexpected projection helper call')

def main():
    programs=[source.bound(*payload(source.OUT/n,source.NAME))for n in('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2]
    cases=0;seen=set();rows=[]
    for initial,args,phase,native in corpus():
        answer,want,depth=model(initial,args,phase);rows.append((initial,args,phase,native,answer,want,depth))
        for w in programs:
            m=Oracle(w,initial,args,phase).run();assert(m.r[2],m.memory)==(answer,want),(args,phase)
        seen.update(Oracle(programs[0],initial,args,phase).run().visits);cases+=1
    controls=[]
    for label,offset,change in(('near-boundary',0x4c,lambda w:w&~63|62),('matrix-column',0x80,lambda w:w&0xffff0000|0x24),('output-sign',0x148,lambda w:w&~63)):
        changed=programs[0][:];i=offset//4
        if label=='matrix-column':assert changed[i]>>26==49 and changed[i]&65535==16
        elif label=='output-sign':assert changed[i]>>26==17 and changed[i]&63==1
        else:assert changed[i]>>26==17 and changed[i]&63==60
        value=change(changed[i]);assert changed[i]!=value;changed[i]=value;caught=False
        for initial,args,phase,native,answer,want,depth in rows:
            m=Oracle(changed,initial,args,phase).run()
            if(m.r[2],m.memory)!=(answer,want):caught=True;break
        assert caught,label;controls.append(label)
    prefixes=0
    for initial,args,phase,native,answer,want,depth in rows[::max(1,len(rows)//8)]:
        full=Oracle(programs[0],initial,args,phase).run()
        for cut in range(full.all_accesses):
            pair=[]
            for w in(programs[0],programs[2]):
                m=Oracle(w,initial,args,phase);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing memory-prefix boundary')
                pair.append(m)
            a,b=pair;assert(a.memory,a.r,a.f,a.condition,a.trace,a.current_pc,a.delay_of)==(b.memory,b.r,b.f,b.condition,b.trace,b.current_pc,b.delay_of);prefixes+=1
    class NaNOracle(Oracle):
        prefer_left=True
        def execute(self,w):
            if w>>26==17 and w>>21&31==16 and w&63 in(0,1,2,3):
                left,right=self.f[w>>11&31],self.f[w>>16&31]
                nan=lambda v:v&0x7f800000==0x7f800000 and v&0x7fffff!=0
                if nan(left)or nan(right):
                    value=(left if nan(left)else right)if self.prefer_left else(right if nan(right)else left)
                    self.f[w>>6&31]=value|0x400000;return
            super().execute(w)
    nan_cases=0
    for rule in(True,False):
        NaNOracle.prefer_left=rule
        for column,a,b,c,d in itertools.product(range(3),(0x7fc00001,0x7fc10002),(0x7fc00003,0x7fc30004),(0,0x7fc50006),(0,0x7fc70008)):
            initial,args=fixture(2.,-2.,-5.)
            for at,value in((column,a),(column+4,b),(column+8,c),(column+12,d)):put(initial,MATRIX+at*4,value)
            pair=[NaNOracle(w,initial,args).run()for w in programs]
            assert all((m.r[2],m.memory)==(pair[0].r[2],pair[0].memory)for m in pair[1:]);nan_cases+=1
    report=dict(cases=cases,streams=3,visited_body_words=len(seen),body_words=97,emitted_controls=controls,full_state_prefixes=prefixes,raw_fault_order_claimed=False,nan_payload_cases=nan_cases,nan_rules_assumed=2,hardware_nan_rule_verified=False)
    (source.OUT/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
