"""Mode dispatch, retail jump table, and bounded helper models."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_owner_mode_1514ea1c_direct as packet
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read

ENTRY=0x1514EA1C;SET=0x1518E37C;DEFAULT=0x1514E89C;STOP=0x1518E308;TABLE=0x800A5E20;OWNER=0x30000
SYMS={'func_1518E37C':SET,'func_1514E89C':DEFAULT,'jtbl_800A5E20':TABLE,'.rodata':TABLE}
u32=lambda v:v&0xffffffff
@dataclass(frozen=True)
class Case:
    phase:int=0;mode:int=0;state:int=0;context:int=0;returned:int=0;mutation:int=0;owner:int=OWNER

def fixture(c):
    home=STACK+c.phase;m={home+i:(i*17+0xa5)&255 for i in range(-512,512)}
    for i in range(0x100):m[c.owner+i]=(i*29+0x35)&255
    m[c.owner+0x22]=c.state;put(m,c.owner+0x10,0x87654320|(c.context&1))
    rom=(packet.ROOT/'conker/conker.us.bin').read_bytes()
    for i,value in enumerate(struct.unpack_from('>10I',rom,0x24a8e0)):put(m,TABLE+4*i,value)
    return m

def words(path):return bound_blob(*payload(path,'func_1514EA1C'),SYMS)
def programs():
    streams=[words(packet.OUT/(n+'.o')) for n in ('retail','after','generated','generic')]
    assert all(x==streams[0] for x in streams)
    return streams

def expected(c,connected=False):
    m=fixture(c);calls=[];mode=u32(c.mode)
    if 3<=mode<=12:
        code=(3,3,2,5,5,2,6,6,2,2)[mode-3]
        if mode in (3,6,9) and c.state!=2:code=2
        calls.append((SET,(c.owner,code)))
        if connected and c.state!=code:
            calls.append((STOP,(c.owner,)))
            if c.mutation:m[c.owner+0x22]^=0x55
            m[c.owner+0x22]=code
        elif not connected:
            if c.mutation:m[c.owner+0x22]=code
        result=1
    else:
        calls.append((DEFAULT,(c.owner,mode,u32(c.context))))
        if connected:
            flags=read(m,c.owner+0x10)
            if mode==0:put(m,c.owner+0x10,flags^1);result=1
            elif mode==1:put(m,c.owner+0x10,flags|1);result=1
            elif mode==2:put(m,c.owner+0x10,flags&~1);result=1
            else:result=0
        else:
            if c.mutation:m[c.owner+0x22]^=0x55
            result=u32(c.returned)
    return public(m,c),calls,result

def public(memory,c):
    home=STACK+c.phase
    return {a:b for a,b in memory.items() if not home-512<=a<home+512}

class Machine(FactoryOracle):
    def __init__(self,words,c,m,connected=None):
        self.c=c
        super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(c.owner,u32(c.mode),u32(c.context)),connected=connected)
    def record_call(self,t):
        counts={SET:2,DEFAULT:3,STOP:1}
        self.calls.append((t,tuple(self.arguments(counts[t]))))
    def hook(self,t):
        if t==SET:
            if self.c.mutation:self.memory[self.c.owner+0x22]=self.calls[-1][1][1]&255
            result=0x12345678
        elif t==DEFAULT:
            if self.c.mutation:self.memory[self.c.owner+0x22]^=0x55
            result=u32(self.c.returned)
        elif t==STOP:
            if self.c.mutation:self.memory[self.c.owner+0x22]^=0x55
            result=0x12345678
        else:raise AssertionError(hex(t))
        for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010;self.r[2]=result

def helper_code():
    rom=(packet.ROOT/'conker/conker.us.bin').read_bytes();result={}
    for entry,offset,count in ((DEFAULT,0x17bd4c,33),(SET,0x1bb82c,18)):
        result.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,rom,offset)))
    return result

def run():
    streams=programs();count=0
    modes=(-0x80000000,-1,0,1,2,*range(3,13),13,14,0x7fffffff)
    for mode,state,context,returned,mutation in itertools.product(modes,(0,1,2,3,255),(0,-1),(0,0x87654321),(0,1)):
        c=Case(mode=mode,state=state,context=context,returned=returned,mutation=mutation);initial=fixture(c);want,calls,result=expected(c)
        for stream in streams:
            m=Machine(stream,c,initial.copy()).run()
            assert (public(m.memory,c),m.calls,m.r[2])==(want,calls,result),c
        count+=1
    print(count,'independent guest model cases per stream')

def connected():
    streams=programs();code=helper_code();count=0
    for mode,state,mutation in itertools.product((-1,0,1,2,*range(3,13),13),(0,1,2,3,5,6,255),(0,1)):
        c=Case(mode=mode,state=state,context=0x12345678,mutation=mutation);initial=fixture(c);want,calls,result=expected(c,connected=True)
        for stream in streams:
            m=Machine(stream,c,initial.copy(),connected=code).run()
            assert (public(m.memory,c),m.calls,m.r[2])==(want,calls,result),(c,m.calls,calls)
        count+=1
    print(count,'cases per stream with original delegate and setter instructions; nested cleanup modeled')
