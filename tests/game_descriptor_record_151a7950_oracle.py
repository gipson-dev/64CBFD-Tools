"""Compare original, compiler and normalized constructor against an independent model."""
import itertools, json, struct
from dataclasses import dataclass
from tools.experiments import game_descriptor_record_151a7950_match as p
from tools.experiments import game_descriptor_record_151a7950_match as n
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read

SOURCE, RECORD = 0x30000, 0x50000
ALLOC, COPY, ZERO = 0x15167A68, 0x10022EC0, 0x100226F0
u32 = lambda x: x & 0xffffffff
signed16 = lambda x: ((x & 0xffff) ^ 0x8000) - 0x8000

@dataclass(frozen=True)
class Case:
    alloc: int
    count: int
    mutation: int
    mode: int
    phase: int = 0
    seed: int = 0
    bytes: int = 0x40
    parameter: int = 0x87654321
    data: int = SOURCE

def args(c): return (c.data, c.bytes, c.mode, c.parameter)
def fixture(c):
    m = {STACK+i: (i*17+c.seed*13+165)&255 for i in range(-1024,1024)}
    for base, size in ((SOURCE,256),(RECORD,0x200)):
        m.update({base+i:(i*29+c.seed*11+0x5a)&255 for i in range(size)})
    put(m,c.data+2,c.count&0xffff,2)
    return m
def public(m): return {a:v for a,v in m.items() if not STACK-1024 <= a < STACK+1024}
def effects(m,c,t):
    if t == ALLOC and c.mutation == 1: put(m,c.data+2,1,2)
    if t == COPY and c.mutation == 2: put(m,c.data+2,2,2)
def count(m,c): return signed16(read(m,c.data+2,2))

def reference(c,initial):
    m = dict(initial)
    calls = [(ALLOC,(0x2d,u32(c.parameter),u32(c.bytes+count(m,c)*24+0x80),1,c.mode&255,1))]
    effects(m,c,ALLOC)
    if not c.alloc: return m,calls,0
    calls.append((COPY,(RECORD+0x10,c.data,0x50)))
    chunk = bytes(m[c.data+i] for i in range(0x50))
    for i,v in enumerate(chunk): m[RECORD+0x10+i] = v
    effects(m,c,COPY)
    put(m,RECORD+0x64,RECORD+0x80)
    put(m,RECORD+0x68,0)
    put(m,RECORD+0x60,u32(RECORD+0x80+count(m,c)*24))
    for off in (0,4,8): put(m,RECORD+0x80+off,0)
    for off,value in ((-24,0),(-20,0),(-16,0x3f800000)):
        put(m,RECORD+0x80+count(m,c)*24+off,value)
    calls.append((ZERO,(RECORD+0x6c,0x10)))
    for i in range(0x10): m[RECORD+0x6c+i] = 0
    put(m,RECORD+0x7c,u32(signed16(read(m,RECORD+0x12,2))*64+0x140))
    return m,calls,RECORD

class Oracle(FactoryOracle):
    def __init__(self,words,c,connected=None,memory=None):
        self.c=c
        super().__init__(words, fixture(c) if memory is None else memory, c, entry=p.ENTRY, arguments=args(c), connected=connected)
        self.initial=dict(self.memory); self.before=self.r[:]; self.before_f=self.f[:]
    def record_call(self,t):
        counts={ALLOC:6,COPY:3,ZERO:2}
        assert t in counts,hex(t)
        self.calls.append((t,tuple(self.arguments(counts[t]))))
    def hook(self,t):
        c=self.c; a=self.calls[-1][1]
        if t==COPY:
            assert a==(RECORD+0x10,c.data,0x50)
            chunk=bytes(self.memory[c.data+i] for i in range(0x50))
            for i,v in enumerate(chunk): self.memory[RECORD+0x10+i]=v
        if t==ZERO:
            assert a==(RECORD+0x6c,0x10)
            for i in range(a[1]): self.memory[a[0]+i]=0
        effects(self.memory,c,t)
        value=RECORD if t==ALLOC and c.alloc else (RECORD+0x10 if t==COPY else 0)
        for i in range(4): self.put(self.r[29]+4*i,0xb5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25): self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)]; self.hi,self.lo=0xa5000010,0xa5000011; self.r[2]=u32(value)

def programs():
    raw,refs=p.payload(p.out/'independent-selected.o')
    lookup={v[1]:v[2][1] for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())}
    syms={name:lookup[name] for es in refs.values() for _,name in es}
    normal,nrefs=n.normalize(raw,refs)
    rom=(p.root/'conker/conker.us.bin').read_bytes()
    return struct.unpack_from('>80I',rom,p.ROM),p.bound_blob(raw,refs,syms),p.bound_blob(normal,nrefs,syms)

def main():
    cases=[Case(a,c,m,mode,phase,i%3) for i,(a,c,m,mode,phase) in enumerate(itertools.product((0,1),(-1,0,1,2,3),(0,1,2),(0,0x1ff),(0,8)))]
    visits=[set(),set(),set()]; variants=programs()
    for c in cases:
        machines=[]
        for index,ws in enumerate(variants):
            machine=Oracle(ws,c); machine.run()
            want,calls,value=reference(c,machine.initial)
            assert public(machine.memory)==public(want),(c,'public memory')
            assert machine.calls==calls,(c,machine.calls,calls)
            assert machine.r[2]==value,(c,machine.r[2],value)
            assert machine.r[16:24]==machine.before[16:24] and machine.r[28:]==machine.before[28:] and machine.f[20:]==machine.before_f[20:]
            visits[index].update(machine.visits); machines.append(machine)
        a,b,d=machines
        assert (a.memory,a.r,a.f,a.calls,a.trace)==(d.memory,d.r,d.f,d.calls,d.trace),(c,'normalized state')
    report=dict(cases=len(cases),executions=3*len(cases),retail_words_visited=sum(p.ENTRY+4*i in visits[0] for i in range(80)), normalized_complete_state=True, count_after_helpers=True, counts=[-1,0,1,2,3], helpers_modeled=True, bounded_nonoverlapping_buffers=True, source_installed=False,byte_exact=False)
    (p.out/'guest.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report),flush=True);return report
if __name__=='__main__': main()
