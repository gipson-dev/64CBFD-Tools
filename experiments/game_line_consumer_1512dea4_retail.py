"""Private bounded retail screen for the line consumer's kind/stack behavior."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read

root=Path.cwd();out=root/'conker/build/game-line-consumer-1512dea4-screen'
out.mkdir(parents=True,exist_ok=True)
rom=(root/'conker/conker.us.bin').read_bytes();ENTRY=0x1512dea4;OWNER=0x320000
words=list(struct.unpack_from('>166I',rom,0x15b354))
@dataclass(frozen=True)
class Case:
    kind:int; stack_x:float; stack_z:float; phase:int=0
def fixture(c):
    m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
    m.update({OWNER+i:(i*29+0x35)&255 for i in range(-16,0xa00)})
    for offset,value in ((0x874,4.),(0x878,5.),(0x87c,6.),(0x2bc,1.),(0x2c0,1.),(0x2c4,2.),
                         (0x880,.5),(0x884,.25),(0x888,-.5),(0x890,2.),(0x894,3.)):
        put(m,OWNER+offset,bits(value))
    m[OWNER+0x870]=c.kind;m[OWNER+0x23c]=1
    put(m,STACK+c.phase-0x14,bits(c.stack_x));put(m,STACK+c.phase-0x0c,bits(c.stack_z))
    return m
class Machine(FactoryOracle):
    def __init__(self,m,c):super().__init__(words,m,c,entry=ENTRY,s={},arguments=(OWNER,))
    def execute(self,word):
        op,rs,rt,rd,fd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
        if op==17 and rs==16 and fn==7:self.f[fd]=self.f[rd]^0x80000000;return
        if op==17 and rs==16 and fn==4:self.f[fd]=bits(math.sqrt(floating(self.f[rd])));return
        return super().execute(word)
    def hook(self,t):raise AssertionError(('unexpected helper in immediate branch',hex(t)))

def f32(v):return floating(bits(v))
def expected(c):
    distance=f32(math.sqrt(f32(f32(f32(3.*3.)+f32(4.*4.))+f32(4.*4.))))
    base=[f32(4.+f32(.5*distance)),f32(5.+f32(.25*distance)),f32(6.+f32(-.5*distance))]
    offsets={0:(-1.,-1.),1:(1.,1.),2:(1.,-1.),3:(-1.,1.)}.get(c.kind,(c.stack_x,c.stack_z))
    return tuple(bits(f32(v+d)) for v,d in zip(base,(offsets[0],3.,offsets[1])))

cases=0;invalid={}
for kind,sx,sz,phase in itertools.product((0,1,2,3,4,255),(-7.,2.),(-3.,5.),(0,8)):
    c=Case(kind,sx,sz,phase);machine=Machine(fixture(c),c).run()
    values=tuple(read(machine.memory,OWNER+off) for off in (0x8a8,0x8ac,0x8b0))
    assert values==expected(c),(c,values,expected(c))
    assert values==tuple(read(machine.memory,OWNER+off) for off in (0x2f8,0x2fc,0x300))
    assert read(machine.memory,OWNER+0x898)==bits(40.) and read(machine.memory,OWNER+0x89c)==bits(40.)
    if kind>=4:invalid.setdefault(kind,set()).add(values)
    cases+=1
assert all(len(values)==4 for values in invalid.values()),invalid
report={'cases':cases,'retail_kinds':[0,1,2,3,4,255],'phase_values':[0,8],
        'invalid_kind_output_variants':{str(k):len(v) for k,v in invalid.items()},
        'immediate_branch_only':True,'helper_calls_exercised':False,'uncredited':True}
(out/'retail-kind-screen.json').write_text(json.dumps(report,indent=2)+'\n')
print(report,flush=True)
