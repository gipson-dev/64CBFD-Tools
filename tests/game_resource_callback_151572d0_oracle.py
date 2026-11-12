"""Bounded independent reference for the resource callback."""
from dataclasses import dataclass

from tools.tests.game_owner_float_payload_oracle import FactoryOracle

from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
ENTRY, OBJ, LINK, DELTA = 0x151572D0, 0x30000, 0x31000, 0x800BE9E4
FIRST, SECOND = 0x8008AD90, 0x8008ADA0
FIRST_FNS = (0x15157AA8, 0x151BECB8, 0x151B8C54, 0x150FB29C)
SECOND_FNS = (0x15157860, 0x15157918)
UPDATE, RELEASE = 0x1503F4B0, 0x1516972C

@dataclass(frozen=True)
class Case:
    flags:int; first:int; second:int; ret_first:int; ret_second:int
    timer:int; delta:int; mutation:int; phase:int

def s16(n):
    return ((n & 0xffff) ^ 0x8000) - 0x8000

def fixture(case):
    memory = {STACK+i:(i*17+0xa5)&255 for i in range(-2048,512)}
    for base,size in ((OBJ-16,0x90),(LINK-16,0x40),(DELTA,4),(FIRST,16),(SECOND,8)):
        memory.update({base+i:(i*13+0x5a)&255 for i in range(size)})
    for i,fn in enumerate(FIRST_FNS): put(memory,FIRST+i*4,fn)
    for i,fn in enumerate(SECOND_FNS): put(memory,SECOND+i*4,fn)
    memory[OBJ+0x10] = case.flags
    memory[OBJ+0x11] = case.first & 255
    memory[OBJ+0x12] = case.second & 255
    put(memory,OBJ+0x16,case.timer,2)
    memory[OBJ+0x43] = 130
    put(memory,OBJ+0x64,100,2)
    put(memory,OBJ+0x66,3,2)
    put(memory,OBJ+0x68,LINK)
    put(memory,DELTA,case.delta)
    return memory

def effect(memory, target, case):
    if case.mutation and target in FIRST_FNS:
        memory[OBJ+0x12] = 1
        memory[OBJ+0x10] = 0x20
        put(memory,OBJ+0x16,-3,2)
        memory[OBJ+0x43] = 100
    if case.mutation and target == UPDATE:
        memory[OBJ+0x10] |= 0x20
        put(memory,OBJ+0x16,4,2)
        put(memory,OBJ+0x64,8,2)
        put(memory,OBJ+0x66,7,2)
        memory[OBJ+0x43] = 50

def reference(case):
    m = fixture(case)
    calls = []
    def call(fn, arg):
        calls.append((fn,(arg,)))
        effect(m,fn,case)
        if fn in FIRST_FNS: return case.ret_first
        if fn in SECOND_FNS: return case.ret_second
        return 0
    expired = False
    if m[OBJ+0x10] & 1:
        timer = s16(read(m,OBJ+0x16,2) - read(m,DELTA))
        put(m,OBJ+0x16,timer,2)
        expired = timer < 0
    if not expired:
        i = (m[OBJ+0x11]^128)-128
        if i != -1 and not call(FIRST_FNS[i],OBJ): expired = True
        i = (m[OBJ+0x12]^128)-128
        if i != -1 and not call(SECOND_FNS[i],OBJ): expired = True
    if not expired: call(UPDATE,read(m,OBJ+0x68))
    if not expired and m[OBJ+0x10] & 0x20:
        remaining, limit = s16(read(m,OBJ+0x16,2)), s16(read(m,OBJ+0x64,2))
        if remaining < limit:
            alpha = remaining*s16(read(m,OBJ+0x66,2))
            if alpha < m[OBJ+0x43]: m[OBJ+0x43] = alpha & 255
    if expired: call(RELEASE,OBJ)
    return public(m), calls

def public(memory):
    return {a:b for a,b in memory.items() if not STACK-2048 <= a < STACK+512}

class Oracle(FactoryOracle):
    def __init__(self,words,case):
        super().__init__(words,fixture(case),case,entry=ENTRY,arguments=(OBJ,))
    def record_call(self,target):
        assert target in (*FIRST_FNS,*SECOND_FNS,UPDATE,RELEASE), hex(target)
        self.calls.append((target,(self.r[4],)))
    def hook(self,target):
        effect(self.memory,target,self.case)
        answer = (self.case.ret_first if target in FIRST_FNS else
                  self.case.ret_second if target in SECOND_FNS else 0)
        for i in range(4): self.put(self.r[29]+4*i,0xb5000000+i,4)
        for r in (1,2,3,*range(4,16),24,25): self.r[r]=0xa5000000+r
        self.f[:20]=[0xa5000000+i for i in range(20)]
        self.hi=self.lo=0xa5000000
        self.r[2]=answer
