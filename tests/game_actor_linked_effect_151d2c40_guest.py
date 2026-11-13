"""Bounded guest/reference comparison for the linked-effect update."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read

root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-linked-effect-151d2c40-durable'
rom=(root/'conker/conker.us.bin').read_bytes();elf=(root/'conker/build/conker.us.elf').read_bytes()
symbols={r[1]:r[2][1] for r in symbol_rows(elf)}
ENTRY=0x151d2c40;TRANSFORM=0x15143134;DESTROY=0x1516972c
EFFECT=0x320000;ACTOR=0x330000;MATRIX=0x340000;TICKS=0x800be9e4;TABLE=0x8008fc40
CBBASE=0x16040000;VALUES=(0x3f123456,0xbf456789,0x7fc12345)
u32=lambda x:x&0xffffffff
signed8=lambda x:(x&127)-(x&128)
signed16=lambda x:((x&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
    gate:int;flags:int;timer:int;ticks:int;update:int;release:int;answer:int;mutation:int;phase:int=0
def fixture(c):
    m={STACK+i:(i*17+0xa5)&255 for i in range(-1024,1024)}
    for base,size in ((EFFECT-16,0x100),(ACTOR-16,0x400),(MATRIX-16,0x420),(TABLE-520,1060)):
        m.update({base+i:(i*29+0x35)&255 for i in range(size)})
    put(m,EFFECT+0x10,ACTOR);m[EFFECT+0x14]=0x43;m[EFFECT+0x24]=3
    put(m,EFFECT+0x26,c.timer,2);m[EFFECT+0x28]=c.flags&255;m[EFFECT+0x29]=c.update&255;m[EFFECT+0x2a]=c.release&255
    put(m,EFFECT+0x2c,0x12345678);put(m,ACTOR,1);m[ACTOR+4]=2;m[ACTOR+0x3b]=0x43;m[ACTOR+0x74]=0x12
    put(m,ACTOR+0x1d4,MATRIX);put(m,TICKS,c.ticks)
    for n in range(-130,132):put(m,TABLE+4*n,CBBASE+4*(n+130))
    if c.gate==1:put(m,ACTOR,0)
    if c.gate==2:m[ACTOR+4]=255
    if c.gate==3:m[ACTOR+0x3b]=0x44
    if c.gate==4:put(m,ACTOR+0x1d4,0)
    if c.gate==5:m[ACTOR+0x74]=0xff
    return m
def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+1024}
def helper_effect(m,c,point):
    for i,v in enumerate(VALUES):put(m,point+4*i,v)
    if c.mutation==1:
        m[EFFECT+0x28]^=1;put(m,EFFECT+0x26,0xfffd,2);m[EFFECT+0x2a]=0;m[EFFECT+0x29]=1
    elif c.mutation==2:
        m[EFFECT+0x28]=0;m[EFFECT+0x29]=0xff
def callback_effect(m,c,point):
    put(m,point,read(m,point)^0x11223344);put(m,EFFECT+0x2c,0xcafebabe)
def reference(initial,c):
    m=dict(initial);calls=[];point=STACK+c.phase-0x10
    actor=read(m,EFFECT+0x10)
    invalid=(read(m,actor)==0 or m[actor+4]==255 or m[EFFECT+0x14]!=m[actor+0x3b] or
             read(m,actor+0x1d4)==0 or (m[actor+0x74]&15)==15)
    if invalid:calls.append((DESTROY,(EFFECT,)));return public(m),calls
    matrix=u32(read(m,actor+0x1d4)+(m[EFFECT+0x24]<<6))
    calls.append((TRANSFORM,(EFFECT+0x18,point,matrix)));helper_effect(m,c,point)
    if m[EFFECT+0x28]&1:
        timer=(signed16(read(m,EFFECT+0x26,2))-read(m,TICKS))&65535;put(m,EFFECT+0x26,timer,2)
        if signed16(timer)<0:
            kind=signed8(m[EFFECT+0x2a])
            if kind!=-1:
                target=read(m,TABLE+8+4*kind);calls.append((target,(EFFECT,point)));callback_effect(m,c,point)
            put(m,EFFECT+0x2c,0);calls.append((DESTROY,(EFFECT,)));return public(m),calls
    kind=signed8(m[EFFECT+0x29])
    if kind!=-1:
        target=read(m,TABLE+4*kind);calls.append((target,(EFFECT,point)));callback_effect(m,c,point)
        if not c.answer:calls.append((DESTROY,(EFFECT,)));return public(m),calls
    for i in range(3):put(m,EFFECT+0x34+4*i,read(m,point+4*i))
    return public(m),calls
class Machine(FactoryOracle):
    def __init__(self,w,m,c):super().__init__(w,m,c,entry=ENTRY,s={},arguments=(EFFECT,))
    def record_call(self,t):
        n=3 if t==TRANSFORM else 1 if t==DESTROY else 2
        self.calls.append((t,tuple(self.arguments(n))))
    def hook(self,t):
        if t==TRANSFORM:helper_effect(self.memory,self.case,self.r[5])
        elif t!=DESTROY:callback_effect(self.memory,self.case,self.r[5])
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
        self.r[2]=self.case.answer if t not in (TRANSFORM,DESTROY) else 0x87654321
        self.f[:20]=[0xa5000000+i for i in range(20)]
def main():
    programs=[list(struct.unpack_from('>91I',rom,0x2000f0))]
    for file in ('portable-03.o','guarded.o'):
        programs.append(bound_blob(*payload(out/file,'func_151D2C40'),symbols))
    assert programs[0]==programs[2]
    cases=0
    for gate,flags,timer,ticks,answer,mutation,phase in itertools.product(range(6),(0,1),(-32768,-1,0,1,32767),(0,1,0x7fffffff,0x80000000),(0,1),range(3),(0,8)):
        kinds=(-128,-2,-1,0,1,3,127);u=kinds[(cases*5+gate)%len(kinds)];r=kinds[(cases*3+flags)%len(kinds)]
        c=Case(gate,flags,timer,ticks,u,r,answer,mutation,phase);initial=fixture(c);expected,calls=reference(initial,c)
        for program in programs:
            m=Machine(program,initial.copy(),c).run()
            assert public(m.memory)==expected and m.calls==calls,(c,m.calls,calls)
        cases+=1
    report={'cases':cases,'streams':len(programs),'callee_and_callbacks_modeled':True,
            'stack_overlap_tested':False,'independent_memory_call_model':True,'uncredited':True}
    (out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
if __name__=='__main__':main()
