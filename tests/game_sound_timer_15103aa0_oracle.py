"""Independent token/timer model and exact emitted memory-prefix checks."""
from dataclasses import dataclass, replace
import itertools
import struct
from tools.experiments import game_sound_timer_15103aa0_match as match
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

STATE,ACTOR,PENDING,OTHER=0x30000,0x70000,0x50000,0x80000
assert not STACK-1024<=ACTOR<STACK+1024 and not STACK-1024<=OTHER<STACK+1024
EMIT,CONTROL,TICKS=0x10010344,0x1000F85C,0x800BE9E4
SYMS=dict(func_10010344=EMIT,func_1000F85C=CONTROL,D_800BE9E4=TICKS)
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
half=lambda v:((v&65535)^32768)-32768
floating=lambda v:struct.unpack('>f',struct.pack('>I',v))[0]
FIELDS=((0,2),(2,2),(4,2),(6,2),(8,2),(10,2),(12,4),(16,4),(20,4),(24,4),(28,4),(32,4),(36,2),(38,2))

@dataclass(frozen=True)
class Case:
    packed:int=0x12340002
    ticks:int=1
    pendingValue:int=0
    handle:int=1
    parameterA:int=-1
    parameter8:int=0x8001
    flags:int=0x812345FF
    coordinates:tuple=(0x418E0000,0xC2F70000,0x42C88000)
    mutation:int=0
    phase:int=0
    address:int=STATE
    pending:int=PENDING
    unused:tuple=(0x7FA12345,0x80000000,0xFFFFFFFF,0x13579BDF,0x2468ACE0)


def cases():
    for low,high,flag,pending,handle,ticks in itertools.product((0,1,0x7FFF),(0,0x1234,0x8000,0xFFFF),(0,0x8000),(0,0xFFFF),(0,0xFFFF),(0,1,0x80000000)):
        yield Case(packed=high<<16|flag|low,pendingValue=pending,handle=handle,ticks=ticks)
    for low in (1,2,0x7FFE,0x7FFF):
        for ticks in (0,1,2,low,low+1,0x7FFF,0x80000000,0xFFFFFFFF):yield Case(packed=0xFFFF0000|low,ticks=ticks)
    for coords in ((0,0x80000000,1),(0xCF000000,0x4EFFFFFF,0x3F7FFFFF),(0xC7000000,0x46FFFE00,0x477FFF00),(0xBF400000,0x3F400000,0x3FC00000)):
        for packed in (0,1,0x12340001,0xFFFF0000):yield Case(packed=packed,coordinates=coords,ticks=1)
    for packed in (0,0x12340000,0x12340001):
        for mutation in range(32):yield Case(packed=packed,pendingValue=1 if packed&0x7FFF else 0,mutation=mutation)
    for a,b in itertools.product((-32768,-1,0,32767),(0,1,0x8000,65535)):
        yield Case(parameterA=a,parameter8=b,pendingValue=0x8001)
    for at in (0,2,4,6,8,10,16,18,24,26,28,30,36,38):
        for packed in (0x12340001,0xFFFF0001):yield Case(packed=packed,ticks=0xFFFFFFFF,pending=STATE+at,pendingValue=ACTOR>>16 if at==28 else 0)
    for pending in (0,STACK+4,STACK+24):
        for packed in ((0,0x12340000)if pending==0 else(1,0x12340001)):
            yield Case(pending=pending,packed=packed)
    for phase in (0,8):
        for packed in (0,1,0x12340000,0x80000000):yield Case(packed=packed,phase=phase,address=0xFFFFFFF0)


def arguments(c):return tuple(map(u32,(c.address,*c.unused,c.pending)))


def fixture(c):
    m={u32(STACK+i):(i*17+0xA5)&255 for i in range(-1024,1024)}
    for a,n in ((c.address,40),(ACTOR,0x330),(OTHER,0x330),(PENDING,4)):
        m.update({u32(a+i):(i*29+0x5A)&255 for i in range(n)})
    for at,v,n in ((0,0x4567,2),(8,c.parameter8,2),(10,c.parameterA,2),(16,c.flags,4),(24,c.packed,4),(28,ACTOR,4),(36,c.handle,2)):
        put(m,u32(c.address+at),v,n)
    for i,v in enumerate(c.coordinates):put(m,ACTOR+0x14+i*4,v)
    if c.pending:put(m,c.pending,c.pendingValue,2)
    put(m,TICKS,c.ticks)
    for i,v in enumerate(arguments(c)[4:],4):put(m,STACK+c.phase+i*4,v)
    return m


def effect(m,c,target,args,home):
    a=c.address
    if c.mutation&1:put(m,u32(a+16),read(m,u32(a+16))^0xFFFFFFFF)
    if c.mutation&2:put(m,u32(a+24),0xDEADBEEF);put(m,TICKS,0xFFFFFFFF)
    if c.mutation&4:
        for at,v,n in ((0,0x1357,2),(8,0x9876,2),(10,-12345,2)):put(m,u32(a+at),v,n)
    if c.mutation&8:put(m,home+24,0x8000FFFF)
    if c.mutation&16:put(m,u32(a+28),OTHER)


def reference(initial,c,snapshots=None):
    m=dict(initial);a=c.address;home=STACK+c.phase;calls=[]
    for i,v in enumerate(c.unused[:3],1):put(m,home+i*4,v)
    def get(at,n=4):return read(m,u32(a+at),n)
    def store(at,v,n=4):put(m,u32(a+at),v,n)
    actor=get(28);packed=get(24);remaining=packed&0x7FFF
    for i in range(3):store(2+i*2,int(floating(read(m,u32(actor+0x14+i*4)))),2)
    def call(target,args):
        if snapshots is not None:snapshots.append(dict(memory=dict(m),target=target,args=tuple(map(u32,args))))
        calls.append((target,tuple(map(u32,args))));effect(m,c,target,args,home)
    def emit(command):call(EMIT,(command,actor,0xFFFF9E58,u32(half(get(10,2))),get(8,2)))
    if remaining:
        pending=read(m,c.pending,2)
        if pending:
            store(24,pending<<16|(packed&65535));store(0,0,2);put(m,c.pending,0,2);emit(0x5B0)
            return m,calls,0
        ticks=read(m,TICKS)
        if ticks>=remaining:
            token=signed(packed)>>16;put(m,c.pending,token,2);fresh=get(24);store(0,token,2);store(24,fresh&0xFFFF8000)
            return m,calls,0
        remaining-=ticks
    else:
        handle=get(36,2)
        if not handle:emit(0x5B1);return m,calls,1
        if packed:
            if not packed&0x8000:call(CONTROL,(handle,0xFFFF8000,2))
            store(24,0)
        flags=get(16);packed=get(24);store(16,flags&0xFFFFFF7F)
    store(24,(packed&0xFFFF8000)|remaining)
    return m,calls,0


class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=match.ENTRY,connected=None,args=None):
        super().__init__(words,memory,c,entry=entry,s=SYMS,connected=connected,arguments=arguments(c)if args is None else args)
    def record_call(self,t):
        count={EMIT:5,CONTROL:3,match.ENTRY:7}[t]
        args=tuple(map(u32,self.arguments(count)));self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        effect(self.memory,self.case,t,self.calls[-1][1],self.target_home)
        for i in range(4):self.put(u32(self.r[29]+i*4),0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011


def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+1024}

def check(machine,initial,c):
    memory,calls,value=reference(initial,c)
    assert (public(machine.memory),machine.calls,machine.r[2])==(public(memory),calls,value),c
    assert machine.r[29]==STACK+c.phase and machine.r[31]==machine.before[31]
    assert all(machine.r[i]==machine.before[i]for i in range(16,24))

def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.trace,m.current_pc,m.delay_of,m.dispatched_word)


def guest_checks(prepared):
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    rom=(match.ROOT/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>93I',rom,match.ROM))
    raw,refs=payload(prepared['after'],match.FUNCTION);candidate=bound_blob(raw,refs,SYMS);assert candidate==truth
    visits=set();count=0
    for c in cases():
        initial=fixture(c);pair=[]
        for words in (truth,candidate):
            m=Oracle(words,initial,c).run();check(m,initial,c);pair.append(m)
            if words is truth:visits.update((pc-match.ENTRY)//4 for pc in m.visits)
        assert state(pair[0])==state(pair[1]);count+=1
    faults=0
    for c in (Case(),Case(pendingValue=0xFFFF),Case(packed=0),Case(packed=0,handle=0),Case(packed=0xFFFF0000,mutation=31),Case(packed=0x12348000),Case(pending=0,packed=0),Case(packed=0xFFFF0001,ticks=0xFFFFFFFF)):
        initial=fixture(c);full=Oracle(truth,initial,c).run()
        for cut in range(full.all_accesses):
            pair=[]
            for words in (truth,candidate):
                m=Oracle(words,initial,c);m.cut=cut
                try:m.run();raise AssertionError('Unfired sound timer access cut')
                except AccessBoundary:pass
                pair.append(m)
            assert state(pair[0])==state(pair[1]);faults+=1
    controls=0
    for offset,xor in ((0x28,0x8000),(0x80,1),(0xFC,1),(0x104,1),(0x13C,1)):
        wrong=truth[:];wrong[offset//4]^=xor;rejected=False
        for c in (Case(),Case(packed=0,handle=0),Case(packed=0xFFFF0000),Case(packed=0x12348000),Case(pendingValue=0xFFFF),Case(ticks=0xFFFFFFFF)):
            try:initial=fixture(c);check(Oracle(wrong,initial,c).run(),initial,c)
            except (AssertionError,KeyError,OverflowError,ValueError):rejected=True;break
        assert rejected,hex(offset);controls+=1
    # A named fired boundary proves the three incoming homes, independently of public outputs.
    prefixes=0
    for c in (Case(),Case(unused=(1,2,3,4,5)),Case(phase=8)):
        initial=fixture(c);m=Oracle(truth,initial,c);m.cut=5
        try:m.run();raise AssertionError('Unfired actor-load boundary')
        except AccessBoundary:pass
        assert m.current_pc==match.ENTRY+0x1C and m.dispatched_word==0x8E05001C
        assert [read(m.memory,STACK+c.phase+4*i)for i in(1,2,3)]==list(c.unused[:3]);prefixes+=1
    assert len(visits)==93,sorted(set(range(93))-visits)
    return dict(cases_per_stream=count,visited_words=len(visits),fault_prefix_pairs=faults,effective_instruction_controls=controls,
                fired_argument_home_prefixes=prefixes,original_literal_callers=0,providers_opaque=True,finite_I32_float_domain=True,
                hardware_gameplay_or_full_parent_claim=False)
