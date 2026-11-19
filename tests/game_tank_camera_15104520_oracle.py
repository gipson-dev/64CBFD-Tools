"""Independent Tank callback contract, original dispatcher and real child code."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_tank_camera_15104520_match as match
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_animation_timeline_oracle import bits,floating

CAMERA,ACTOR,OTHER,CHILD,TABLE,STATE,STATE_POINTER,FACTOR=(0x30000,0x70000,0x80000,0x15128774,0x80089670,0x90000,0x800B0DF0,0x800A35AC)
SYMS={'func_15128774':CHILD};u32=lambda n:n&0xFFFFFFFF
FIELDS=((0x190,4),(0x348,4),(0x34C,4),(0x370,4),(0x374,4),(0x3D0,4),(0x3E8,1),(0x6C8,4),(0x6FC,4))
@dataclass(frozen=True)
class Case:
    override:int=0
    mode:int=0
    speed:int=0x42440000
    current:int=0x442F0000
    desired:int=0x43B90000
    transition:int=0
    subject:int=ACTOR
    mutation:int=0
    phase:int=0

def cases():
    for override,mode,speed,current,transition in itertools.product((0,1,0x80000000),(0,1),(0x4247FFFF,0x42480000,0x42480001),(0x440ABFFF,0x440AC000,0x440AC001,0x442F0000),(0,1,128)):
        yield Case(override=override,mode=mode,speed=speed,current=current,transition=transition)
    for desired,current,speed in itertools.product((0,0x80000000,1,0x80000001,0xC0000000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345),
                                                  (0,0x80000000,1,0xC1200000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC54321),(0,0xFF800000,0x7F800000,0x7FC00001)):
        yield Case(mode=1,desired=desired,current=current,speed=speed)
    for subject,mutation,phase in itertools.product((ACTOR,OTHER,CAMERA+0x30C,CAMERA+0x310,CAMERA+0x338),range(8),(0,8)):
        yield Case(subject=subject,mutation=mutation,phase=phase)
    for override,mode in itertools.product((0,0xFFFFFFFF),(0,0xFFFFFFFF)):
        yield Case(override=override,mode=mode,transition=255)

def fixture(c):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
    for base,n in((CAMERA,0x9A0),(ACTOR,0x32C),(OTHER,0x32C),(STATE,32)):
        m.update({base+i:(i*29+0x5A)&255 for i in range(n)})
    for off,v in((0x190,0xC1A00000),(0x348,0x42820000),(0x34C,0x42A40000),(0x370,c.current),(0x374,c.desired),(0x3D0,c.subject),(0x3D4,OTHER),(0x6C8,c.mode),(0x6FC,c.override)):
        put(m,CAMERA+off,v)
    m[CAMERA+0x3E8]=c.transition;put(m,c.subject+0x3C,c.speed)
    for actor in(ACTOR,OTHER):
        for off,v in((0x14,0x418A0000),(0x18,0xC1A80000),(0x1C,0x41FA0000),(0x40,0x43D20000),(0x180,0x3F400000)):
            put(m,actor+off,v)
    put(m,FACTOR,0x3F6D4321);put(m,STATE_POINTER,STATE)
    return m
def fields(m):return tuple(read(m,CAMERA+off,n)for off,n in FIELDS)+(read(m,ACTOR+0x3C),read(m,OTHER+0x3C))
def effect(m,c):
    if c.mutation&1:put(m,CAMERA+0x374,bits(-31.25));put(m,CAMERA+0x370,bits(92.5))
    if c.mutation&2:put(m,CAMERA+0x6FC,0xFEDCBA98);put(m,CAMERA+0x6C8,0x87654321);m[CAMERA+0x3E8]=255
    if c.mutation&4:put(m,CAMERA+0x3D0,OTHER);put(m,ACTOR+0x3C,bits(27.25));put(m,OTHER+0x3C,bits(-6.5))
def child_reference(m,c):
    subject=c.subject;primary=read(m,CAMERA+0x3D0)
    put(m,CAMERA+0x35C,read(m,subject+0x180))
    x=read(m,subject+0x14);put(m,CAMERA+0x2F8,x);put(m,CAMERA+0x304,x)
    y=read(m,subject+0x18);other=read(m,CAMERA+0x3D4);put(m,CAMERA+0x2FC,y);put(m,CAMERA+0x308,y)
    z=read(m,subject+0x1C);put(m,CAMERA+0x300,z);put(m,CAMERA+0x30C,z)
    put(m,CAMERA+0x37C,bits(floating(read(m,primary+0x40))-180.0));put(m,other+0x18C,read(m,FACTOR));m[CAMERA+0x23C]=1
def reference(initial,c,connected=False):
    m=dict(initial);calls=[];snaps=[]
    if read(m,CAMERA+0x6FC)or not read(m,CAMERA+0x6C8):
        for off,v in((0x348,bits(117.0)),(0x34C,bits(117.0)),(0x374,bits(370.0)),(0x190,bits(77.0))):put(m,CAMERA+off,v)
    subject=read(m,CAMERA+0x3D0)
    if floating(read(m,subject+0x3C))<50.0 and not m[CAMERA+0x3E8]:
        desired=read(m,CAMERA+0x374);half=bits(0.5*floating(desired));difference=bits(floating(read(m,CAMERA+0x370))-floating(desired))
        if floating(half)<floating(difference):
            calls.append((CHILD,(CAMERA,subject)));snaps.append(fields(m))
            if connected:child_reference(m,c)
            else:effect(m,c)
    return m,calls,snaps

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=match.ENTRY,connected=None,args=None):
        super().__init__(words,memory,c,entry=entry,s=SYMS,connected=connected,arguments=(CAMERA,)if args is None else args)
        self.snapshots=[]
    def record_call(self,t):
        count=2 if t==CHILD else 1 if t==match.ENTRY else None;assert count is not None,hex(t)
        args=tuple(map(u32,self.arguments(count)));self.calls.append((t,args));self.events.append(('CALL',t,args))
        if t==CHILD:self.snapshots.append(fields(self.memory))
    def hook(self,t):
        assert t==CHILD;effect(self.memory,self.case)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def public(m):return{a:v for a,v in m.items()if not STACK-1024<=a<STACK+1024}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.snapshots,m.trace,m.current_pc,m.delay_of,m.dispatched_word)
def check(machine,initial,c,connected=False):
    memory,calls,snaps=reference(initial,c,connected)
    assert(public(machine.memory),machine.calls,machine.snapshots)==(public(memory),calls,snaps),c
    assert machine.r[29]==STACK+c.phase and machine.r[31]==machine.before[31]
    assert all(machine.r[i]==machine.before[i]for i in range(16,24))
def streams(p):
    truth=list(struct.unpack_from('>45I',(match.ROOT/'conker/conker.us.bin').read_bytes(),match.ROM));raw=bound_blob(p['raw'],p['refs'],SYMS);assert raw==truth
    return truth,raw
def guest_checks(p):
    pair=streams(p);visits=set();count=faults=0
    for c in cases():
        initial=fixture(c);machines=[]
        for words in pair:
            m=Oracle(words,initial,c).run();check(m,initial,c);machines.append(m)
        assert state(machines[0])==state(machines[1]);visits.update((pc-match.ENTRY)//4 for pc in machines[0].visits);count+=1
    for c in(Case(),Case(mode=1,current=bits(555.0)),Case(transition=1),Case(speed=bits(50.0)),Case(mutation=7),Case(subject=CAMERA+0x338)):
        initial=fixture(c);full=Oracle(pair[0],initial,c).run()
        for cut in range(full.all_accesses):
            machines=[]
            for words in pair:
                m=Oracle(words,initial,c);m.cut=cut
                try:m.run();raise AssertionError('Unfired Tank access boundary')
                except AccessBoundary:pass
                machines.append(m)
            assert state(machines[0])==state(machines[1]);faults+=1
    controls=0
    for at,xor in((0xC,1),(0x10,0x04000000),(0x4C,1),(0x70,0x04000000),(0x84,1),(0x9C,1)):
        wrong=pair[0][:];wrong[at//4]^=xor;rejected=False
        for c in(Case(),Case(current=bits(555.0)),Case(mode=1),Case(speed=bits(50.0)),Case(transition=1)):
            try:initial=fixture(c);check(Oracle(wrong,initial,c).run(),initial,c)
            except(AssertionError,KeyError,ValueError,OverflowError,ZeroDivisionError):rejected=True;break
        assert rejected,hex(at);controls+=1
    assert visits==set(range(45)),sorted(set(range(45))-visits)
    return dict(cases_per_stream=count,streams=2,visited_body_words=len(visits),alignment_words_checked=3,fault_prefix_pairs=faults,effective_instruction_controls=controls,
                guest_only_camera_subject_aliases=True,numerical_model='IEEE-single values and ordered predicates; FCSR not emulated',hardware_gameplay_claim=False)
def connected_checks(p):
    rom=(match.ROOT/'conker/conker.us.bin').read_bytes();dispatcher=list(struct.unpack_from('>17I',rom,0x15D6E0));helper=list(struct.unpack_from('>27I',rom,0x155C24));table=rom[0x22E130:0x22E1C0]
    selected=list(cases())[::19];count=0
    for c,enabled,real_child in itertools.product(selected,(0,11),(False,True)):
        initial=fixture(c);initial.update({TABLE+i:b for i,b in enumerate(table)});initial[STATE+15]=enabled
        expected,calls,snaps=reference(initial,c,real_child)if enabled else(dict(initial),[],[]);machines=[]
        for target in streams(p):
            code=dict(zip(range(match.ENTRY,match.ENTRY+180,4),target))
            if real_child:code.update(zip(range(CHILD,CHILD+108,4),helper))
            m=Oracle(dispatcher,initial,c,entry=0x15130230,connected=code,args=(CAMERA,0xFEDCBA98)).run()
            assert(m.calls,m.snapshots,public(m.memory))==(([(match.ENTRY,(CAMERA,))]if enabled else[])+calls,snaps,public(expected)),(c,enabled,real_child)
            assert m.r[29]==STACK+c.phase and m.r[31]==m.before[31]
            assert all(m.r[i]==m.before[i]for i in range(16,24));machines.append(m)
        assert state(machines[0])==state(machines[1]);count+=1
    return dict(complete_original_dispatcher_words=17,table_index=11,scenarios=count,streams=2,real_child_slot_words=27,
                child_connected_and_opaque_modes=True,table_zero_gate=True,other_callback_modes_not_claimed=True,hardware_gameplay_claim=False)
