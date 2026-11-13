from pathlib import Path
import sys, struct, itertools
from dataclasses import dataclass
from tools.experiments import game_fade_update_151e4ee8_match as packet
root=packet.ROOT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
out=packet.OUT
ENTRY=0x151e4ee8
S={s:int(s[2:],16) for s in ('D_800E0B96','D_8008FDD0','D_8008FD74','D_800DDDC8','D_800DDDD8','D_800ABA2C','D_800ABA30','D_800ABA34','D_800BE9E4','D_800E0A88')}
ALPHA=S['D_800E0B96'];RATE=S['D_8008FD74'];OUTPUT=S['D_8008FDD0'];LEVEL=S['D_800DDDC8'];AUDIO=S['D_800DDDD8'];TICKS=S['D_800BE9E4'];CALLBACK=0x151e4e00
@dataclass(frozen=True)
class Case:
    phase:int;alpha:int;rate:int;ticks:int;level:int;threshold:int;mutate:int=0
def fixture(c):
    m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-128,64)}
    for a in S.values():
        for i in range(4):m[a+i]=0
    m[ALPHA]=c.alpha;m[RATE]=c.rate
    for addr,v in ((OUTPUT,0xdeadbeef),(LEVEL,c.level),(AUDIO,0xc1234567),(TICKS,c.ticks),(S['D_800ABA2C'],c.threshold),(S['D_800ABA30'],0x3eaaaaab),(S['D_800ABA34'],0x3f000001),(S['D_800E0A88'],CALLBACK)):put(m,addr,v)
    return m
def public(m):return {a:b for a,b in m.items() if not STACK-256<=a<STACK+256}
def reference(c):
    m=fixture(c);alpha=c.alpha
    put(m,OUTPUT,bits(1.0-floating(bits(float(alpha)/255.0))))
    cb=False
    if c.rate==255:
        if floating(c.level)>floating(c.threshold):
            alpha=(alpha+c.ticks)&255;m[ALPHA]=alpha
            put(m,AUDIO,read(m,S['D_800ABA30'] if alpha<85 else S['D_800ABA34']))
        if not (floating(c.level)<1.0) and alpha>=110:cb=True
    elif alpha==255:cb=True
    else:
        value=signed((alpha+c.ticks*c.rate)&0xffffffff)
        m[ALPHA]=(255 if value>=256 else value)&255
    if cb:
        m[ALPHA]=255;m[RATE]=8;put(m,OUTPUT,bits(1.0))
        observed=(m[ALPHA],m[RATE],read(m,OUTPUT),read(m,AUDIO))
        if c.mutate:m[ALPHA]=23;m[RATE]=7;put(m,OUTPUT,bits(0.5))
    else:observed=None
    return public(m),observed
class Machine(FactoryOracle):
    def __init__(self,words,c):
        super().__init__(words,fixture(c),c,entry=ENTRY,s=S,arguments=(0x12345678,))
        self.observed=None
    def record_call(self,t):
        assert t==CALLBACK,hex(t)
        self.observed=(self.memory[ALPHA],self.memory[RATE],read(self.memory,OUTPUT),read(self.memory,AUDIO))
        self.calls.append((t,tuple(self.r[4:8])))
    def hook(self,t):
        assert t==CALLBACK
        if self.case.mutate:self.memory[ALPHA]=23;self.memory[RATE]=7;put(self.memory,OUTPUT,bits(0.5))
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)]
def program(path):
    data,refs=payload(path,'func_151E4EE8')
    return bound_blob(data,refs,S)
def run():
    rom=(root/'conker/conker.us.bin').read_bytes()
    programs=[struct.unpack_from('>83I',rom,0x212398)]+[program(out/(n+'.o')) for n in ('after','generated','generic')]
    count=0
    for alpha,rate,ticks,level,threshold in itertools.product((0,1,84,85,109,110,254,255),(0,1,8,254,255),(0,1,0xff,0xffffffff,0x7fffffff,0x80000000),(0x00000000,0x3f000000,0x3f800000,0x7fc00000),(0x00000000,0x3f000000,0x3f800000,0x7fc00000)):
        c=Case(8 if count&1 else 0,alpha,rate,ticks,level,threshold,count&1)
        expected,obs=reference(c)
        for words in programs:
            m=Machine(words,c).run()
            assert (public(m.memory),m.observed)==(expected,obs),(c,m.observed,obs)
            if obs is not None:assert m.calls==[(CALLBACK,(0x12345678,ALPHA,255,OUTPUT))],m.calls
            else:assert not m.calls
        count+=1
    print('independent fade model',count,'cases, four instruction streams, callback mutations and NaN comparisons',flush=True)
