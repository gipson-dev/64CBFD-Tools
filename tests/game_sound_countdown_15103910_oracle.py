"""Independent signed-countdown contract and original o32 callback window."""
from dataclasses import dataclass, replace
import itertools
import struct
from tools.experiments import game_sound_countdown_15103910_match as match
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

STATE,ACTOR,PENDING,OTHER,VALUE,VOLUME=0x30000,0x70000,0x50000,0x80000,0x51000,0x52000
assert all(not STACK-1024<=a<STACK+1024 for a in (STATE,ACTOR,PENDING,OTHER,VALUE,VOLUME))
EMIT,STOP,TICKS=0x10010344,0x100111C8,0x800BE9E4
SYMS=dict(func_10010344=EMIT,func_100111C8=STOP,D_800BE9E4=TICKS)
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
    actorHandle:int=1
    parameterA:int=-1
    parameter8:int=0x8001
    volumeValue:int=0xFEDCBA98
    flags:int=0x812345FF
    coordinates:tuple=(0x418E0000,0xC2F70000,0x42C88000)
    mutation:int=0
    phase:int=0
    address:int=STATE
    pending:int=PENDING
    callbackValue:int=VALUE
    volume:int=VOLUME
    unused:tuple=(0x7FA12345,0x80000000,0xFFFFFFFF)

def cases():
    for low,high,pending,handle,ticks in itertools.product((0,1,0x7FFF,0x8000,0xFFFF),(0,0x1234,0x8000,0xFFFF),(0,0xFFFF),(0,1,0xFFFF),(0,1,0x80000000)):
        yield Case(packed=high<<16|low,pendingValue=pending,handle=handle,ticks=ticks)
    for low in (1,2,0x7FFE,0x7FFF,0x8000,0x8001,0xFFFF):
        for ticks in (0,1,2,low,low+1,0x7FFF,0x8000,0xFFFF,0x80000000,0xFFFFFFFF):yield Case(packed=0xFFFF0000|low,ticks=ticks)
    for coords in ((0,0x80000000,1),(0xCF000000,0x4EFFFFFF,0x3F7FFFFF),(0xC7000000,0x46FFFE00,0x477FFF00),(0xBF400000,0x3F400000,0x3FC00000)):
        for packed in (0,1,0x12340001,0xFFFF0000):yield Case(packed=packed,coordinates=coords)
    for packed,handle in ((0,0),(0,2),(0,1),(0x12340001,2)):
        for mutation in range(128):yield Case(packed=packed,handle=handle,pendingValue=1 if packed&65535 else 0,mutation=mutation)
    for a,b in itertools.product((-32768,-1,0,32767),(0,1,0x8000,65535)):
        yield Case(parameterA=a,parameter8=b,packed=0,handle=0)
    for at in (0,2,4,6,8,10,12,14,16,18,24,26,28,30,36,38):
        for packed in (0x12340001,0xFFFF8000):yield Case(packed=packed,ticks=0xFFFFFFFF,pending=STATE+at,pendingValue=ACTOR>>16 if at==28 else 0)
    for value,volume in ((VALUE,VALUE),(STATE+12,VOLUME),(VALUE,STATE+12),(STATE+24,STATE+16),(STATE+36,STATE+24),(STATE+16,STATE+16)):
        for packed in (0,0x12340001):yield Case(packed=packed,callbackValue=value,volume=volume)
    for pending in (0,STACK+12,STACK+24):
        for packed in ((0,0x12340000)if pending==0 else(1,0x12340001)):yield Case(pending=pending,packed=packed)
    for phase in (0,8):
        for packed in (0,1,0x12340000,0x80000000):yield Case(packed=packed,phase=phase,address=0xFFFFFFF0)

def arguments(c):return tuple(map(u32,(c.address,c.callbackValue,c.volume,*c.unused,c.pending)))

def fixture(c):
    m={u32(STACK+i):(i*17+0xA5)&255 for i in range(-1024,1024)}
    for a,n in ((c.address,40),(ACTOR,0x330),(OTHER,0x330),(PENDING,4),(VALUE,4),(VOLUME,4)):
        m.update({u32(a+i):(i*29+0x5A)&255 for i in range(n)})
    for at,v,n in ((0,0x4567,2),(8,c.parameter8,2),(10,c.parameterA,2),(12,c.volumeValue,4),(16,c.flags,4),(20,match.ENTRY,4),(24,c.packed,4),(28,ACTOR,4),(36,c.handle,2)):
        put(m,u32(c.address+at),v,n)
    for i,v in enumerate(c.coordinates):put(m,ACTOR+0x14+i*4,v)
    put(m,ACTOR+0x8C,c.actorHandle,2)
    if c.pending:put(m,c.pending,c.pendingValue,2)
    put(m,TICKS,c.ticks)
    for i,v in enumerate(arguments(c)[4:],4):put(m,STACK+c.phase+i*4,v)
    return m

def effect(m,c,target,args,home):
    a=c.address
    if c.mutation&1:put(m,u32(a+16),read(m,u32(a+16))^0xFFFFFFFF)
    if c.mutation&2:put(m,u32(a+24),0xDEADBEEF);put(m,TICKS,0xFFFFFFFF)
    if c.mutation&4:
        for at,v,n in ((0,0x1357,2),(8,0x9876,2),(10,-12345,2),(12,0x89ABCDEF,4)):put(m,u32(a+at),v,n)
    if c.mutation&8:put(m,home+24,0x8000FFFF)
    if c.mutation&16:put(m,u32(a+28),OTHER)
    if c.mutation&32:put(m,u32(a+36),0xCAFE,2)
    if c.mutation&64:put(m,ACTOR+0x8C,0xDEAD,2)

def reference(initial,c,snapshots=None):
    m=dict(initial);a=c.address;home=STACK+c.phase;calls=[]
    put(m,home+12,c.unused[0])
    def get(at,n=4):return read(m,u32(a+at),n)
    def store(at,v,n=4):put(m,u32(a+at),v,n)
    actor=get(28);packed=get(24);remaining=half(packed)
    for i in range(3):store(2+i*2,int(floating(read(m,u32(actor+0x14+i*4)))),2)
    def call(target,args):
        if snapshots is not None:snapshots.append(dict(memory=dict(m),target=target,args=tuple(map(u32,args))))
        calls.append((target,tuple(map(u32,args))));effect(m,c,target,args,home)
    if remaining:
        pending=read(m,c.pending,2)
        if pending:
            store(24,pending<<16|(packed&65535));store(0,0,2);put(m,c.pending,0,2)
            call(EMIT,(0x5B0,actor,25000,100,120));return m,calls,0
        remaining=half(remaining-read(m,TICKS))
        if remaining<=0:
            token=signed(packed)>>16;put(m,c.pending,token,2);volume=get(12);store(0,token,2)
            put(m,c.volume,volume);put(m,c.callbackValue,1);store(24,0);return m,calls,0
    else:
        put(m,c.volume,get(12));put(m,c.callbackValue,1)
        handle=get(36,2)
        if not handle:
            call(EMIT,(0x5B1,actor,get(12),u32(half(get(10,2))),get(8,2)));return m,calls,1
        actorHandle=read(m,u32(actor+0x8C),2)
        if handle!=actorHandle:
            call(STOP,(actorHandle,));put(m,u32(actor+0x8C),get(36,2),2)
        flags=get(16);packed=get(24);store(16,flags&0xFFFFFF7F)
    store(24,(packed&0xFFFF0000)|u32(remaining))
    return m,calls,0

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=match.ENTRY,connected=None,args=None):
        super().__init__(words,memory,c,entry=entry,s=SYMS,connected=connected,arguments=arguments(c)if args is None else args)
    def record_call(self,t):
        count={EMIT:5,STOP:1,match.ENTRY:7}[t]
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
    rom=(match.ROOT/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>100I',rom,match.ROM))
    raw,refs=payload(prepared['after'],match.FUNCTION);candidate=bound_blob(raw,refs,SYMS);assert candidate==truth
    visits=set();count=0
    for c in cases():
        initial=fixture(c);pair=[]
        for words in (truth,candidate):
            m=Oracle(words,initial,c).run();check(m,initial,c);pair.append(m)
            if words is truth:visits.update((pc-match.ENTRY)//4 for pc in m.visits)
        assert state(pair[0])==state(pair[1]);count+=1
    faults=0
    for c in (Case(),Case(pendingValue=0xFFFF),Case(packed=0),Case(packed=0,handle=0),Case(packed=0,handle=2,mutation=127),Case(packed=0xFFFF8000),Case(pending=0,packed=0),Case(packed=0xFFFF0001,ticks=0xFFFFFFFF)):
        initial=fixture(c);full=Oracle(truth,initial,c).run()
        for cut in range(full.all_accesses):
            pair=[]
            for words in (truth,candidate):
                m=Oracle(words,initial,c);m.cut=cut
                try:m.run();raise AssertionError('Unfired countdown access cut')
                except AccessBoundary:pass
                pair.append(m)
            assert state(pair[0])==state(pair[1]);faults+=1
    controls=0
    for offset,xor in ((0x24,0x40),(0x78,1),(0xD4,1),(0xE8,1),(0x158,1)):
        wrong=truth[:];wrong[offset//4]^=xor;rejected=False
        for c in (Case(),Case(packed=0x12340001),Case(packed=0,handle=0),Case(packed=0,handle=2),Case(packed=0xFFFF8000),Case(pendingValue=0xFFFF),Case(ticks=0xFFFFFFFF)):
            try:initial=fixture(c);check(Oracle(wrong,initial,c).run(),initial,c)
            except (AssertionError,KeyError,OverflowError,ValueError):rejected=True;break
        assert rejected,hex(offset);controls+=1
    prefixes=0
    for c in (Case(),Case(unused=(1,2,3)),Case(phase=8)):
        initial=fixture(c);m=Oracle(truth,initial,c);m.cut=4
        try:m.run();raise AssertionError('Unfired actor-load boundary')
        except AccessBoundary:pass
        assert m.current_pc==match.ENTRY+0x18 and m.dispatched_word==0x8E11001C
        assert read(m.memory,STACK+c.phase+12)==c.unused[0];prefixes+=1
    # Retail retains one dead actor-handle load after an unconditional return branch.
    assert set(range(100))-visits=={77},sorted(set(range(100))-visits)
    assert truth[75]==0x10000013 and truth[76]==0x24020001 and truth[77]==0x9624008C
    targets={i+1+half(w)for i,w in enumerate(truth)if w>>26 in(1,4,5,6,7,20,21,22,23)}
    assert 77 not in targets
    return dict(cases_per_stream=count,visited_words=len(visits),retained_dead_words=[77],all100_words_checked=True,
                fault_prefix_pairs=faults,effective_instruction_controls=controls,fired_argument_home_prefixes=prefixes,
                providers_opaque=True,finite_I32_float_domain=True,hardware_gameplay_or_full_parent_claim=False)

class WindowEnd(Exception):pass
class WindowCode(dict):
    def __init__(self,inner):super().__init__(inner);self.inner=inner;self[0x10011884]=0
    def __getitem__(self,pc):
        if pc==0x10011884:raise WindowEnd
        return self.inner[pc]

def caller_checks(prepared):
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    rom=(match.ROOT/'conker/conker.us.bin').read_bytes();start,end=0x10011848,0x10011884
    window=list(struct.unpack('>15I',rom[0x11848:0x11884]));truth=list(struct.unpack_from('>100I',rom,match.ROM))
    candidate=bound_blob(prepared['raw'],prepared['refs'],SYMS);count=0
    for packed,handle,pending,mutation in itertools.product((0,1,0x12340002,0xFFFF8000),(0,2),(0,0xFFFF),(0,119)):
        c=Case(packed=packed,handle=handle,pendingValue=pending,mutation=mutation,
               callbackValue=STACK+0xB0,volume=STACK+0xB4,pending=STACK+0xA6,unused=(STACK+0xBC,STACK+0xA8,STACK+0xA0))
        initial=fixture(c);put(initial,STACK+0xC8,0);expected,calls,result=reference(initial,c);pair=[]
        for words in (truth,candidate):
            connected=dict(zip(range(match.ENTRY,match.ENTRY+400,4),words));m=Oracle(window,initial,c,entry=start,connected=connected)
            m.code=WindowCode(m.code);m.r[16]=c.address;m.r[17]=c.flags;m.r[30]=c.address
            try:m.run();raise AssertionError('Unfired original callback continuation')
            except WindowEnd:pass
            assert m.calls==[(match.ENTRY,arguments(c)),*calls] and m.r[2]==result
            assert public(m.memory)==public(expected)
            for at,n in ((c.callbackValue,4),(c.volume,4),(c.pending,2)):assert read(m.memory,at,n)==read(expected,at,n)
            assert m.r[29]==STACK and m.r[16]==c.address and m.r[30]==c.address
            pair.append(m)
        assert state(pair[0])==state(pair[1]);count+=1
    return dict(original_window_words=15,callback_variants=count,return_boundary=end,providers_opaque=True,full_parent_claim=False)
