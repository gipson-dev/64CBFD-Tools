import itertools, json, math, struct, sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_effect_descriptor_150c1e34_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_point_transform_match import put, read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object

ENTRY=0x150C1E34; COLOR=0x151429E0; RANDOM=0x150ADA20; EMIT=0x1518CA80; CONST=0x800A0228
def double_bits(v):return struct.unpack('>Q',struct.pack('>d',v))[0]
def double(v):return struct.unpack('>d',struct.pack('>Q',v))[0]
@dataclass(frozen=True)
class Case:
    x:float; y:float; z:float; px:float; py:float; pz:float; scale:float
    random:int; phase:int=0; seed:int=0
def cases():
    values=((0.,0.,0.,0.,0.,0.,0.),(1.25,-2.,3.5,-1.5,7.,8.,4.5),
        (-23.125,4.25,17.75,19.,-2.,-4.125,-19.75),
        (3000.,-0.,-3000.,-200.,1.,200.,32767.0),
        (-1.000000119,11.,0.99999994,0.000000119,2.,-0.99999994,5.75),
        (0.125,3.,-0.125,0.,7.,0.,-32768.0))
    return [Case(*v,r,p,s) for v,r,p,s in itertools.product(values,(0,1,15,16,0xffffffff), (0,8),(0,1))]
def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-1024,1024)}
    value=double_bits(0.1757)
    put(m,CONST,value>>32);put(m,CONST+4,value&0xffffffff)
    return m
def args(c):
    return (1,7,bits(c.x),bits(c.y),bits(c.z),bits(c.px),bits(c.py),bits(c.pz),
        0x7fffffff,0x80000000,bits(14.0),0x12345678,bits(c.scale),0xabcdef01,0xff)
def reference(c):
    x,y,z,px,pz,scale=map(lambda v:floating(bits(v)),(c.x,c.y,c.z,c.px,c.pz,c.scale))
    sx=lambda v: math.trunc(v)&0xffff
    dx=floating(bits(floating(bits(x-px))*10.0));dz=floating(bits(floating(bits(z-pz))*10.0))
    a=sx(scale); b=sx(float(scale)*0.1757)
    return {0:(4,bits(x)),4:(4,bits(y)),8:(4,bits(z)),22:(2,a),24:(2,a),26:(2,b),28:(2,b),
        30:(2,sx(dx)),32:(2,sx(dz)),34:(2,150),36:(2,20),38:(2,600),
        40:(1,0x31),41:(1,0x72),42:(1,0xb3),43:(1,0x42),44:(1,0x83),45:(1,0xc4),
        46:(1,255),47:(1,255),48:(1,12+(c.random&15)),49:(1,1)}

class Oracle(FactoryOracle):
    def __init__(self,words,c):
        super().__init__(words,fixture(c),c,entry=ENTRY,arguments=args(c))
        self.before=self.r[:];self.before_f=self.f[:];self.packet=None
    def execute(self,w):
        op,fmt,ft,fs,fd,fn=w>>26,(w>>21)&31,(w>>16)&31,(w>>11)&31,(w>>6)&31,w&63
        if op==17 and ((fmt==16 and fn in (13,33)) or (fmt==17 and fn in (2,13))):
            if fmt==16 and fn==13:self.f[fd]=math.trunc(floating(self.f[fs]))&0xffffffff
            elif fmt==16 and fn==33:
                v=double_bits(floating(self.f[fs]));self.f[fd]=v&0xffffffff;self.f[fd+1]=v>>32
            elif fmt==17 and fn==2:
                left=double(self.f[fs+1]<<32|self.f[fs]);right=double(self.f[ft+1]<<32|self.f[ft]);v=double_bits(left*right)
                self.f[fd]=v&0xffffffff;self.f[fd+1]=v>>32
            else:self.f[fd]=math.trunc(double(self.f[fs+1]<<32|self.f[fs]))&0xffffffff
        else:super().execute(w)
    def record_call(self,t):
        assert t in (COLOR,RANDOM,EMIT),hex(t)
        a=tuple(self.arguments(4 if t==COLOR else 2 if t==EMIT else 0))
        if t==EMIT:
            assert a[1]==1 and STACK-1024<=a[0]<STACK
            self.packet={off:read(self.memory,a[0]+off,n) for off,(n,_) in reference(self.case).items()}
        if t==COLOR:
            assert a[0]==0 and a[2]==a[1]+1 and a[3]==a[1]+2
        self.calls.append((t,a))
    def hook(self,t):
        a=self.calls[-1][1]
        if t==COLOR:
            color=(0x31,0x72,0xb3) if sum(v[0]==COLOR for v in self.calls)==1 else (0x42,0x83,0xc4)
            for addr,value in zip(a[1:],color):self.put(addr,value,1)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
        if t==RANDOM:self.r[2]=self.case.random&0xffffffff

def main():
    data,fs,rs=parse_object(out/'independent-selected.o');a,n=fs['func_150C1E34']['value'],fs['func_150C1E34']['size']
    refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
    candidate=bound_blob(data[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es})
    retail=struct.unpack_from('>72I',(root/'conker/conker.us.bin').read_bytes(),0xEF2E4);seen=set()
    for c in cases():
        for ws in (retail,candidate):
            m=Oracle(ws,c);m.run();assert m.packet=={k:v for k,(_,v) in reference(c).items()},(c,m.packet,reference(c))
            assert [v[0] for v in m.calls]==[COLOR,COLOR,RANDOM,EMIT] and m.r[2]==1
            assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
            if ws is retail:seen.update(m.visits)
    report=dict(cases=len(cases()),retail_words_visited=sum(ENTRY+4*i in seen for i in range(72)),retail_body_words=72,
        helpers='modeled',initialized_packet_fields_only=True,source_installed=False)
    (out/'guest_150C1E34_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
