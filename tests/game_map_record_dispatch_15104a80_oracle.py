"""Independent actor selection, sequence payload, original wrapper and callback ABI."""
from dataclasses import dataclass,replace
import itertools,struct
from functools import lru_cache
from tools.experiments import game_map_record_dispatch_15104a80_recovery as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

ACTORS=0x800CC2D0;RECORDS=0x30000;BASE=RECORDS+4*160;MASKS=0x60000+5*4;MARK=0x70000
WRAPPER,CONSUMER,QUEUE=0x151494E0,0x15169260,0x800A5770
BASEPTR,MASKPTR=0x800DBEF4,0x800DBF94;TEMPLATES=(0x800A2380,0x800A238C,0x800A2398)
u32=lambda n:n&0xffffffff
@dataclass(frozen=True)
class Case:
    kind:int=0xF9
    mask:int=0xffffffff
    active:int=1
    delta:int=0
    phase:int=0
    seed:int=0
def cases():
    for kind,(mask,active)in itertools.product(range(256),((0,1),(0xffffffff,1),(1<<24,3))):yield Case(kind,mask,active,seed=kind)
    for kind,mask,active in itertools.product((0xF6,0xF7,0xF8,0xF9),(0,1,2,1<<24,1<<25,1<<31,0xffffffff,0x2000001),range(6)):yield Case(kind,mask,active,seed=kind+active)
    for kind,delta,active in itertools.product((0xF6,0xF7,0xF8,0xF9),(-164,-160,-156,-4,0,4,156,160,164),(1,3)):yield Case(kind,0xffffffff,active,delta,seed=delta&255)
def index(c):return(abs(c.delta)//160)*(-1 if c.delta<0 else 1)
def state(c,i):return 0 if c.active==0 else -1 if c.active==1 else 17 if(c.active==2 and i==0)or(c.active==3 and i==24)or(c.active==4 and i%3==0)or(c.active==5 and i==25)else 0
def selected(c):return next((ACTORS+i*812 for i in range(25)if state(c,i)and(c.mask>>i&1)),0)
def sequences(c):return tuple(bytes((j*19+k*37+c.seed)&255 for j in range(9))for k in range(3))
def fixture(c):
    m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-512,256)}
    for i in range(9*160):m[RECORDS+i]=(i*29+c.seed+0x5A)&255
    for i in range(11):put(m,MASKS+(i-5)*4,0xAAAA5555^i)
    put(m,BASEPTR,BASE);put(m,MASKPTR,MASKS);put(m,MASKS+index(c)*4,c.mask);put(m,MARK,0x11223344)
    for i in range(26):put(m,ACTORS+i*812,u32(state(c,i)))
    for address,data in zip(TEMPLATES,sequences(c)):
        for j,v in enumerate(data+b'\xA5\x5A\xCC'):m[address+j]=v
    m[BASE+c.delta+0x72]=c.kind;return m
def expected(c):
    actor=selected(c)
    return(0x38,(actor,))if c.kind==0xF6 else(0x35,(9,sequences(c)[0xF9-c.kind],actor))if c.kind in(0xF7,0xF8,0xF9)else None
def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+256}
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,s=source.SYMS,connected=connected,arguments=(BASE+c.delta,)if arguments is None else arguments)
        self.payloads=[]
    def record_call(self,t):
        if t==source.ENTRY:args=(self.r[4],)
        elif t==WRAPPER:args=(self.r[4],self.r[5])
        elif t==CONSUMER:args=tuple(self.r[4:8])
        else:raise AssertionError(('unexpected helper',hex(t)))
        self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        if t==WRAPPER:p,command=self.r[4:6]
        else:
            assert t==CONSUMER and self.r[4:6]==[QUEUE,2]
            p,command=self.r[6:8]
        if command==0x35:
            length=read(self.memory,p);sequence=read(self.memory,p+4);actor=read(self.memory,p+8)
            self.payloads.append((command,(length,bytes(self.memory[sequence+j]for j in range(length)),actor)))
        else:
            assert command==0x38
            self.payloads.append((command,(read(self.memory,p),)))
        put(self.memory,MARK,0xAABB0000|command)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def check(machine,initial,c):
    value=expected(c);want=dict(initial)
    if value:put(want,MARK,0xAABB0000|value[0])
    assert machine.payloads==([value]if value else[])and public(machine.memory)==public(want),c
    assert machine.r[29]==STACK+c.phase and machine.r[31]==machine.before[31]
    assert all(machine.r[i]==machine.before[i]for i in(*range(16,24),28,30))and machine.f[20:]==machine.saved_f
@lru_cache(maxsize=1)
def wrapper_words():
    rom=(source.ROOT/'conker/conker.us.bin').read_bytes();words=struct.unpack_from('>13I',rom,0x176990)
    return words
def wrapper_code():return dict(zip(range(WRAPPER,WRAPPER+52,4),wrapper_words()))
def guest_checks(prepared):
    count=0;visits=[set(),set()]
    for c in cases():
        initial=fixture(c)
        for i,words in enumerate((prepared['truth'],prepared['words'])):
            machine=Oracle(words,initial,c,connected=wrapper_code()).run();check(machine,initial,c)
            visits[i].update((pc-source.ENTRY)//4 for pc in machine.visits if source.ENTRY<=pc<source.ENTRY+len(words)*4)
        count+=1
    controls=[]
    for name,at,mask in(('scan-limit',0x8C,1),('sequence-source',0xCC,1<<16),('packet-length',0xE4,1),('pointer-command',0x1B0,1)):
        wrong=prepared['truth'][:];wrong[at//4]^=mask;rejected=False
        for c in(Case(),Case(kind=0xF6),Case(kind=0xF8),Case(kind=0xF7),Case(mask=1<<24,active=3)):
            try:initial=fixture(c);check(Oracle(wrong,initial,c,connected=wrapper_code()).run(),initial,c)
            except(AssertionError,KeyError,ValueError):rejected=True;break
        assert rejected,name;controls.append(name)
    return dict(cases_per_stream=count,streams=2,visited_words=[len(v)for v in visits],unvisited_words=[sorted(set(range(n))-v)for n,v in zip((113,110),visits)],
        original_wrapper_words=13,complete_seeded_public_memory_and_payloads=True,void_return_not_constrained=True,effective_instruction_controls=controls)
def prefix_checks(prepared):
    count=0
    for c in(Case(),Case(kind=0xF8,mask=1<<24,active=3),Case(kind=0xF7,mask=0),Case(kind=0xF6),Case(kind=0,mask=1<<31)):
        initial=fixture(c);runs=[Oracle(words,initial,c).run()for words in(prepared['truth'],prepared['words'])]
        assert runs[0].trace==runs[1].trace and runs[0].memory==runs[1].memory and runs[0].calls==runs[1].calls,c
        for cut in range(len(runs[0].trace)):
            pair=[]
            for words in(prepared['truth'],prepared['words']):
                m=Oracle(words,initial,c);m.cut=cut
                try:m.run();raise AssertionError(('unfired access cut',cut))
                except faults.AccessBoundary:pair.append((m.trace,m.memory,m.calls,m.payloads))
            assert pair[0]==pair[1],(c,cut);count+=1
    return dict(cases=5,paired_fault_prefixes=count,ordered_seeded_memory_equal=True,private_bytes_equal=True,full_GPR_PC_relation_not_qualified=True)
def caller_checks(prepared):
    rom=(source.ROOT/'conker/conker.us.bin').read_bytes();window=list(struct.unpack_from('>8I',rom,0x144DFC));count=0
    for c in list(cases())[::17]:
        initial=fixture(c)
        for words in(prepared['truth'],prepared['words']):
            code=wrapper_code();code.update(zip(range(source.ENTRY,source.ENTRY+len(words)*4,4),words))
            m=Oracle(window,initial,c,entry=0x1511794C,connected=code);m.r[8]=source.ENTRY
            wrapped=WindowCode(m.code,m);wrapped.ends={0x1511799C};m.code=wrapped
            try:m.run();raise AssertionError('Unfired callback window')
            except WindowBoundary:pass
            value=expected(c);want=dict(initial)
            if value:put(want,MARK,0xAABB0000|value[0])
            assert m.payloads==([value]if value else[])and public(m.memory)==public(want)
            assert m.calls[0]==(source.ENTRY,(BASE+c.delta,))and m.r[4]==BASE+c.delta and m.r[7]==3 and m.r[29]==STACK+c.phase
        count+=1
    return dict(original_window_words=8,scenarios=count,streams=2,registered_JALR_preserves_record_and_saved_mode=True,full_parent_or_queue_consumer_claim=False)
