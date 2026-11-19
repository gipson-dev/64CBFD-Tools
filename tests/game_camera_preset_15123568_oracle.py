"""Independent camera selector model, literal guest traces and caller windows."""
from dataclasses import dataclass, replace
import struct
from tools.experiments import game_camera_preset_15123568_match as match
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary

ENTRY=match.ENTRY
SYMS=dict(D_800A34D8=0x800A34D8,D_800BE9E4=0x800BE9E4,func_15124B18=0x15124B18,func_15125608=0x15125608)
SETUP,UPDATE=SYMS['func_15124B18'],SYMS['func_15125608']
u32=lambda v:v&0xFFFFFFFF
s32=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
s16=lambda v:((v&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
    kind:int=0
    state:int=0
    disabled:int=0
    flags:int=4
    buttons:int=8
    mode:int=0
    active:int=0
    activeState:int=4
    actorMode:int=0
    preset:int=3
    enabled:int=14
    cooldown:int=0
    ticks:int=1
    distance:int=0x4479C000
    mutation:int=0
    phase:int=0
    address:int=0x30000


def cases():
    base=Case()
    axes=dict(kind=(0,3,4,255),state=(0,0x40,0x41,0xFFFFFFFF),disabled=(0,1,255),flags=(0,1,4,0xFFFFFFFF),
              buttons=(0,8,0x8008,65535),mode=(0,4,0xFFFFFFFF),active=(0,1,0x80000000),activeState=(0,4,0xFFFFFFFF),
              actorMode=(0,1,255),preset=(-3,0,1,2,3,4,15,31,32,33),enabled=(2,4,8,6,10,12,14,0x800E,65535),
              cooldown=(0,1,2,20,0x7FFFFFFF,0x80000000,0xFFFFFFFF),ticks=(0,1,2,20,0x7FFFFFFF,0x80000000,0xFFFFFFFF))
    for name,values in axes.items():
        for value in values:
            for phase in (0,8): yield replace(base,**{name:value},phase=phase)
    for c in (Case(kind=4,state=0x40),Case(kind=4,disabled=1),Case(active=1,activeState=0),Case(actorMode=1,preset=1)):
        yield c
    for preset in (-3,0,1,2,3,4,15,31,32,33):
        for mask in (2,4,8,14,0x800E,65535): yield replace(base,preset=preset,enabled=mask)
    for cooldown in (1,20,0x7FFFFFFF):
        for ticks in (0,1,20,0x7FFFFFFF,0x80000000,0xFFFFFFFF): yield replace(base,cooldown=cooldown,ticks=ticks)
    for kind in (0,4):
        for mutation in range(8):
            for distance in (0x4479C000,0x80000000,0x7FA12345): yield replace(base,kind=kind,mutation=mutation,distance=distance)
    for kind in (0,4):
        for address in (0xFFFFFF00,SYMS['D_800A34D8']-0x1B4,SYMS['D_800BE9E4']-0x7B8):
            yield replace(base,address=address,kind=kind)
    # Degenerate masks only enter paths that do not run the selection loop.
    for preset in (-32768,32767):
        for mask in (0,1): yield replace(base,preset=preset,enabled=mask,flags=0)


def fixture(c):
    m={u32(STACK+i):(i*17+0xA5)&255 for i in range(-1024,1024)}
    for address,n in ((c.address,0x9A0),(0x40000,0x9A0),(0x50000,0x400),(0x60000,0x400)):
        m.update({u32(address+i):(i*29+0x5A)&255 for i in range(n)})
    a=c.address
    for at,v,n in ((0x2C,c.state,4),(0x84,c.flags,4),(0xDC,c.mode,4),(0x36A,c.buttons,2),
                   (0x3D0,0x50000,4),(0x3D4,0x60000,4),(0x6C8,c.active,4),(0x6FC,c.activeState,4),
                   (0x1B4,c.preset,2),(0x1E0,c.enabled,2),(0x7B8,c.cooldown,4),(0x92C,c.disabled,1)):
        put(m,u32(a+at),v,n)
    put(m,0x500AD,c.actorMode,1);put(m,0x60120,c.kind,1)
    put(m,SYMS['D_800A34D8'],c.distance);put(m,SYMS['D_800BE9E4'],c.ticks)
    return m


def effect(m,c,target,a,home):
    if c.mutation&1: put(m,u32(a+0x1B4),2,2)
    if c.mutation&2: put(m,u32(a+0x190),0x7FA12345)
    put(m,u32(a+0x7CC),target)
    if c.mutation&4: put(m,home,0x40000)


def reference(initial,c):
    m=dict(initial);calls=[];a=c.address;home=STACK+c.phase
    def get(at,n=4): return read(m,u32(a+at),n)
    def store(at,v,n=4): put(m,u32(a+at),v,n)
    def call(target):
        nonlocal a
        calls.append((target,(a,)));effect(m,c,target,a,home)
        if c.mutation&4:a=0x40000
    attached=get(0x3D4)
    if read(m,u32(attached+0x120),1)==4 and get(0x2C)!=0x40 and get(0x92C,1)==0:
        value=read(m,SYMS['D_800A34D8']);store(0x1B4,1,2);store(0x7C0,value)
        call(SETUP);store(0x198,0);store(0x190,0)
        return m,calls
    cooldown=s32(get(0x7B8))
    if cooldown>0:
        value=s32(cooldown-read(m,SYMS['D_800BE9E4']));store(0x7B8,max(value,0));return m,calls
    if not get(0x84)&4 or not get(0x36A,2)&8 or get(0xDC)==4:return m,calls
    if get(0x6C8) and get(0x6FC)!=4:return m,calls
    actor=get(0x3D0)
    if read(m,u32(actor+0xAD),1)==1 and s16(get(0x1B4,2))==1:return m,calls
    if s16(get(0x1B4,2))==1:return m,calls
    while True:
        preset=s16(get(0x1B4,2)-1);store(0x1B4,preset,2)
        if preset<=0:preset=3;store(0x1B4,preset,2)
        if (1<<(preset&31))&s16(get(0x1E0,2)):break
    call(SETUP);call(UPDATE);store(0x7B8,20)
    return m,calls


class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None):
        self.snapshots=[]
        super().__init__(words,memory,c,entry=entry,s=SYMS,connected=connected,arguments=(c.address,))
    def record_call(self,t):
        if t not in (SETUP,UPDATE,ENTRY):raise AssertionError(('Unmodeled camera helper',hex(t)))
        a=tuple(map(u32,self.arguments(1)));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        effect(self.memory,self.case,t,self.calls[-1][1][0],self.target_home)
        for i in range(4):self.put(u32(self.r[29]+4*i),0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011


def public(m):return {a:v for a,v in m.items() if not STACK-1024<=a<STACK+1024}

def check(m,initial,c):
    expected,calls=reference(initial,c)
    assert (public(m.memory),m.calls)==(public(expected),calls),c
    assert m.r[29]==STACK+c.phase and m.r[31]==m.before[31]
    assert all(m.r[i]==m.before[i] for i in range(16,24))


def state(m):return (m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.trace,m.current_pc,m.delay_of,m.dispatched_word)


def guest_checks(prepared):
    rom=(match.ROOT/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>90I',rom,match.ROM))
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    raw,refs=payload(prepared['out']/'after.o',match.FUNCTION);natural=bound_blob(raw,refs,SYMS)
    raw,refs=payload(prepared['after'],match.FUNCTION);guarded=bound_blob(raw,refs,SYMS);assert guarded==truth
    visits=set();count=0
    for c in cases():
        initial=fixture(c)
        for words in (truth,natural,guarded):
            m=Oracle(words,initial,c).run();check(m,initial,c)
            if words is truth:visits.update((v-ENTRY)//4 for v in m.visits)
        count+=1
    faults=0
    for c in (Case(),Case(kind=4),Case(cooldown=20),Case(cooldown=1,ticks=20),Case(flags=0),Case(kind=4,mutation=7),Case(preset=1),
              Case(kind=4,state=0x40),Case(kind=4,disabled=1),Case(active=1,activeState=0),Case(actorMode=1,preset=1)):
        initial=fixture(c);full=Oracle(truth,initial,c).run()
        for cut in range(full.all_accesses):
            pair=[]
            for words in (truth,guarded):
                m=Oracle(words,initial,c);m.cut=cut
                try:m.run();raise AssertionError('Unfired camera access cut')
                except AccessBoundary:pass
                pair.append(m)
            assert state(pair[0])==state(pair[1]);faults+=1
    controls=0
    for offset in (0x44,0x84,0x11C,0x154):
        wrong=truth[:];wrong[offset//4]^=0x10000 if offset==0x84 else 1;rejected=False
        for c in (Case(),Case(kind=4),Case(cooldown=1,ticks=20),Case(preset=0,enabled=8)):
            try:
                initial=fixture(c);check(Oracle(wrong,initial,c).run(),initial,c)
            except (AssertionError,KeyError):rejected=True;break
        assert rejected,hex(offset);controls+=1
    windows=[]
    for offset in (0x1503F0,0x15564C):
        entry=offset-0x2D4B0+0x15000000;literal=struct.unpack_from('>2I',rom,offset)
        assert literal[0]>>26==3 and ((literal[0]&0x3FFFFFF)<<2|0x10000000)==ENTRY
        for c in (Case(),Case(kind=4),Case(cooldown=20),Case(preset=1)):
            initial=fixture(c);connected=dict(zip(range(ENTRY,ENTRY+360,4),truth));connected[entry+8]=0
            machine=Oracle(literal,initial,c,entry=entry,connected=connected)
            machine.r[16]=c.address;machine.before[16]=c.address
            machine.code=WindowCode(machine.code,machine);machine.code.ends={entry+8}
            try:machine.run();raise AssertionError('Caller window did not stop')
            except WindowBoundary:pass
            expected,calls=reference(initial,c)
            assert public(machine.memory)==public(expected) and machine.calls==[(ENTRY,(c.address,))]+calls
        windows.append(dict(rom=hex(offset),entry=hex(entry),words=2,cases=4,full_caller=False))
    assert sorted(set(range(90))-visits)==[27,37]
    return dict(cases_per_stream=count,streams=3,visited_retail_words=len(visits),unvisited=sorted(set(range(90))-visits),
                fault_prefix_pairs=faults,effective_instruction_controls=controls,caller_windows=windows,
                original_helpers_opaque=True,hardware_or_gameplay_claim=False)
