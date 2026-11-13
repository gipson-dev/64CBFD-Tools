from dataclasses import dataclass
import itertools,math
from tools.experiments import game_camera_state_15125924_direct as packet
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
root,out=packet.ROOT,packet.OUT
NAME='func_15125924';ENTRY=0x15125924
SYMS={'func_15125490':0x15125490,'func_15123934':0x15123934,'func_15124B18':0x15124B18,'func_151239CC':0x151239CC}
CAMERA=0x30000;STATE=0x50000;ACTOR=0x60000
@dataclass(frozen=True)
class Case:
    phase:int=0;present:int=1;flags:int=0;flags84:int=0;enabled:int=1;status:int=0;value:float=0.;first:int=1;second:int=1;busy:int=0;mutate:int=0
def fixture(c):
    m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
    for base,n in ((CAMERA,0x800),(STATE,0x200),(ACTOR,0x200)):m.update({base+i:(i*29+0x35)&255 for i in range(n)})
    for at,v in ((0x3d4,STATE if c.present else 0),(0x3d0,ACTOR),(0x2c,c.flags),(0x84,c.flags84),(0x6c8,c.busy),(0x5f0,0x1000),(0x2fc,bits(5.5)),(0x354,bits(2.25)),(0x344,bits(-1.)),(0x348,bits(-2.)),(0x190,bits(3.0))):put(m,CAMERA+at,v)
    put(m,STATE+0x1c,bits(c.value));m[STATE+0x4e]=c.status;m[ACTOR+0x102]=c.enabled
    return m
def words(path):return bound_blob(*payload(path,NAME),SYMS)
class Machine(FactoryOracle):
    def __init__(self,words,c,m):
        self.c=c
        super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(CAMERA,))
    def execute(self,w):
        op,fmt,src,dst,fn=w>>26,w>>21&31,w>>11&31,w>>6&31,w&63
        if op==17 and fmt==16 and fn==13:
            v=floating(self.f[src]);self.f[dst]=(math.trunc(v)&0xffffffff) if math.isfinite(v) and -(2**31)<=v<2**31 else 0x80000000
        else:super().execute(w)
    def record_call(self,t):
        counts={SYMS['func_15125490']:1,SYMS['func_15123934']:5,SYMS['func_15124B18']:1,SYMS['func_151239CC']:2}
        self.calls.append((t,tuple(self.arguments(counts[t]))))
    def hook(self,t):
        c=self.c
        if c.mutate:
            if t==SYMS['func_15125490']:put(self.memory,CAMERA+0x2c,0x80)
            elif t==SYMS['func_15123934']:put(self.memory,CAMERA+0x6c8,c.busy)
            elif t==SYMS['func_15124B18']:put(self.memory,CAMERA+0x5f0,0x55)
            elif t==SYMS['func_151239CC']:put(self.memory,CAMERA+0x5f0,0x1100)
        for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010
        self.r[2]=c.first if t==SYMS['func_15125490'] else c.second if t==SYMS['func_15123934'] else 0xfeedface
def public(m,c):return {a:b for a,b in m.items() if not STACK+c.phase-512<=a<STACK+c.phase+512}
def reference(initial,c):
    m=initial.copy();calls=[]
    status=m[STATE+0x4e] if c.present else 0
    value=math.trunc(floating(read(m,STATE+0x1c))) if c.present else 0
    if read(m,CAMERA+0x2c)&0x40:return public(m,c),calls
    if not(read(m,CAMERA+0x84)&0x4000) and not m[ACTOR+0x102]:return public(m,c),calls
    calls.append((SYMS['func_15125490'],(CAMERA,)))
    if c.mutate:put(m,CAMERA+0x2c,0x80)
    if c.first and not status and not value:
        calls.append((SYMS['func_15123934'],(CAMERA,0x80,1,1,13)))
        if c.mutate:put(m,CAMERA+0x6c8,c.busy)
        if c.second and not read(m,CAMERA+0x6c8):
            calls.append((SYMS['func_15124B18'],(CAMERA,)))
            if c.mutate:put(m,CAMERA+0x5f0,0x55)
            put(m,CAMERA+0x5f0,read(m,CAMERA+0x5f0)|0x1000)
        return public(m,c),calls
    if read(m,CAMERA+0x2c)&0x80:
        calls.append((SYMS['func_151239CC'],(CAMERA,13)))
        if c.mutate:put(m,CAMERA+0x5f0,0x1100)
        put(m,CAMERA+0x190,bits(0.0))
    flags=read(m,CAMERA+0x5f0)
    if flags&0x1000:
        offset=bits(floating(read(m,CAMERA+0x2fc))-floating(read(m,CAMERA+0x354)))
        put(m,CAMERA+0x5f0,flags&~0x1000);put(m,CAMERA+0x344,offset);put(m,CAMERA+0x348,offset)
    return public(m,c),calls
def run():
    programs=[words(out/f) for f in ('retail.o','after.o','padded.o')];assert programs[0]==programs[1]==programs[2]
    count=0
    for present,flags,flags84,enabled,status,value,first,second,busy,mutate in itertools.product((0,1),(0,0x40,0x80),(0,0x4000),(0,1),(0,1),(0.,0.9,1.25),(0,1),(0,1),(0,1),(0,1)):
        c=Case(0,present,flags,flags84,enabled,status,value,first,second,busy,mutate);initial=fixture(c);states=[]
        for program in programs:
            m=Machine(program,c,initial.copy()).run();states.append((public(m.memory,c),m.calls))
        assert states[0]==states[1]==states[2]==reference(initial,c),c
        count+=1
    print(count,'non-overlap guest cases per stream; retail, raw candidate and padded body agree with independent public-state and call model')
if __name__=='__main__':run()
