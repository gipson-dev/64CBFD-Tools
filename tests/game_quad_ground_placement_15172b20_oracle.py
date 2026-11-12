"""Compare a private quad-placement candidate to retail with modeled helpers."""
import itertools, json, struct, sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_quad_ground_placement_15172b20_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.test_game_point_transform_match import put, read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object

ENTRY=0x15172B20
COS=0x15047C00
SIN=0x15047D60
QUERY=0x1510E82C
PLACE=0x151725FC
VERTICES=0x30000
MARK=0x70000
CONVERT=0x800A7154
SENTINEL=0x800A7158

@dataclass(frozen=True)
class Case:
    xyz:tuple
    angle:int
    radius:int
    trig:tuple
    mode:int
    image:int
    answer:int
    phase:int=0
    seed:int=0

def cases():
    positions=((bits(1.),bits(2.),bits(3.)),(bits(-5.),bits(.25),bits(100.)),(bits(0.),bits(-9.),bits(-0.)))
    for xyz,trig,mode,image,answer,geometry,phase in itertools.product(positions,((bits(1.),bits(0.)),(bits(-.5),bits(.75))),range(3),(0,0x123456ff),(0,0x13579bdf),((bits(135.),0xfffffffd),(bits(90.),0),(bits(-45.),9)),(0,8)):
        yield Case(xyz,geometry[0],geometry[1],trig,mode,image,answer,phase)

def fixture(c):
    m={STACK+i:(i*17+0xa5)&255 for i in range(-1024,512)}
    for base,n in ((VERTICES,64),(MARK,4),(CONVERT,8)):
        m.update({base+i:0xa5 for i in range(n)})
    put(m,CONVERT,bits(.017453292));put(m,SENTINEL,bits(-1000.));put(m,MARK,0)
    return m

def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+512}

def reference(c):
    x,y,z=c.xyz;cosine,sine=c.trig
    radians=fp(fp(c.angle,bits(90.),'sub'),bits(.017453292),'mul')
    radius=(c.radius^0x80000000)-0x80000000
    x=fp(x,fp(bits(float(radius)),sine,'mul'),'add')
    z=fp(z,fp(bits(float(radius)),cosine,'mul'),'add')
    height=bits(-1000.) if c.mode==1 else bits(42.5)
    hit=0 if c.mode==0 else 0x50000
    calls=[(COS,(radians,)),(SIN,(radians,)),(QUERY,(0,0,0,0,0,0,x,y,z,y,0,0))]
    result=0
    if c.mode==2:
        calls.append((PLACE,(VERTICES,hit,x,height,z,c.angle,0x12345678,c.image&255)))
        result=c.answer
    return calls,result

class Oracle(FactoryOracle):
    def __init__(self, words, c):
        super().__init__(words,fixture(c),c,entry=ENTRY,arguments=(VERTICES,*c.xyz,c.angle,c.radius,0x12345678,c.image))
        self.before=self.r[:];self.before_f=self.f[:];self.calls=[]
    def record_call(self,t):
        if t in (COS,SIN):self.calls.append((t,(self.f[12],)))
        elif t==QUERY:
            args=list(self.arguments(12));self.outputs=(args[0],args[2],args[4])
            assert all(STACK-1024 <= p < STACK+self.case.phase for p in self.outputs)
            for i in (0,2,4):args[i]=0
            self.calls.append((t,tuple(args)))
        elif t==PLACE:self.calls.append((t,tuple(self.arguments(8))))
        else:raise AssertionError(hex(t))
    def hook(self,t):
        if t==QUERY:
            hit=0 if self.case.mode==0 else 0x50000
            height=bits(-1000.) if self.case.mode==1 else bits(42.5)
            for p,v in zip(self.outputs,(hit,height,0x42424242)):put(self.memory,p,v)
            put(self.memory,MARK,0x11223344)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
        if t==COS:self.f[0]=self.case.trig[0]
        elif t==SIN:self.f[0]=self.case.trig[1]
        elif t==PLACE:self.r[2]=self.case.answer

def main():
    data,fs,rs=parse_object(out/'independent-selected.o')
    a,n=fs['func_15172B20']['value'],fs['func_15172B20']['size']
    refs={i-a:v for i,v in rs.items() if a<=i<a+n}
    look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
    candidate=bound_blob(data[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es})
    retail=struct.unpack_from('>74I',(root/'conker/conker.us.bin').read_bytes(),0x19FFD0)
    seen=set();count=0
    for c in cases():
        calls,result=reference(c)
        for ws in (retail,candidate):
            m=Oracle(ws,c);m.run()
            assert (m.calls,m.r[2])==(calls,result),(c,m.calls,calls,hex(m.r[2]),hex(result))
            assert read(m.memory,MARK)==0x11223344
            assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
            if ws is retail:seen.update(m.visits)
        count+=1
    report=dict(cases=count,retail_words_visited=sum(ENTRY+4*i in seen for i in range(74)),helpers='modeled',source_installed=False)
    (out/'guest_15172B20_screen.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True);return report

if __name__=='__main__':main()
