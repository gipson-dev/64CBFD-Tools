"""Exercise the original callback-registry dispatch window."""
import itertools,struct
from tools.tests import game_owner_mode_1514ea1c_direct_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

def run():
    rom=(g.packet.ROOT/'conker/conker.us.bin').read_bytes();registry=0x8008ab64
    assert struct.unpack_from('>5I',rom,0x22f624)==(0x1514e89c,0x1514e920,0x1514e9dc,0x1514e9fc,g.ENTRY)
    start,end=0x1514d454,0x1514d47c
    window=struct.unpack_from('>10I',rom,start-0x15000000+0x2d4b0)
    assert window[:5]==(0x02eb6021,0x8d990000,0x8e040010,0x02802825,0x0320f809)
    node=0x50000
    class Connected(g.Machine):
        def __init__(self,words,c,m):
            self.c=c;code=dict(zip(range(g.ENTRY,g.ENTRY+4*len(words),4),words));code[end]=0
            FactoryOracle.__init__(self,window,m,c,entry=start,s=g.SYMS,arguments=(),connected=code)
            self.r[16]=node;self.r[20]=g.u32(c.mode);self.r[21]=g.u32(c.context);self.r[23]=registry;self.r[11]=16
            self.code=WindowCode(self.code,self);self.code.ends=(end,)
        def record_call(self,t):
            if t==g.ENTRY:self.calls.append((t,tuple(self.arguments(3))))
            else:super().record_call(t)
    streams=g.programs();count=0
    for mode,state,ret,mutation in itertools.product((-1,0,1,2,*range(3,13),13),(0,2,255),(0,0x12345678),(0,1)):
        c=g.Case(mode=mode,state=state,context=0x87654321,returned=ret,mutation=mutation);initial=g.fixture(c)
        g.put(initial,registry+16,g.ENTRY);g.put(initial,node+0x10,c.owner)
        want,calls,result=g.expected(c);g.put(want,registry+16,g.ENTRY);g.put(want,node+0x10,c.owner)
        for words in streams:
            machine=Connected(words,c,initial.copy())
            try:machine.run();raise AssertionError('caller boundary not reached')
            except WindowBoundary:pass
            assert (g.public(machine.memory,c),machine.calls,machine.r[17])==(want,[(g.ENTRY,(c.owner,g.u32(mode),g.u32(c.context)))]+calls,int(result!=0)),c
        count+=1
    print(count,'original indirect-dispatch window cases per stream')
