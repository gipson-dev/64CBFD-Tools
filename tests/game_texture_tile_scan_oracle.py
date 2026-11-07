"""Bounded Gfx streams, sparse guest indices and authentic caller windows."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_texture_tile_scan_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import TrackedCode
from tools.tests.test_game_character_effect_pair import WindowBoundary
ENTRY,GLOBAL,LIST,COUNT=source.ENTRY,0x800B0E58,0x30000,0x50000
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
    asset:int=1
    occurrence:int=0
    mask:int=5
    blocks:int=4
    pairs:int=3
    gap:int=2
    prefix:int=0
    ending:int=0
    alias:int=0
    phase:int=0

def commands(c):
    rows=[(c.prefix,0x12345678)]
    for block in range(c.blocks):
        rows.append((0xFD,0x87654321 if c.mask>>block&1 else 0x12345678))
        rows.extend((0xE6,0x66778899)for _ in range(c.gap))
        rows.append((0xF2,0x00FC00FC))
        for _ in range(c.pairs-1):rows.extend(((0xF5,0x12345678),(0xF2,0x00FC00FC)))
        rows.extend(((0xF5 if c.ending&1 else 0xE7,0x55667788),(0xE7 if c.ending&2 else 0xF2,0x11223344)))
    rows.extend(((0xDF,0),(0,0)))
    return rows

def count_pointer(c):
    return (COUNT,LIST+4,LIST+8,GLOBAL+u32(c.asset*4),STACK+c.phase+8,LIST+8*(2+c.gap))[c.alias]

def fixture(c=Case(),global_address=GLOBAL):
    m={STACK+c.phase+i:(i*17+165)&255 for i in range(-256,512)}
    for base,n in((LIST,2048),(COUNT,16)):m.update({base+i:(i*29+89)&255 for i in range(n)})
    for i,(opcode,value)in enumerate(commands(c)):
        put(m,LIST+8*i,opcode<<24|0x123456);put(m,LIST+8*i+4,value)
    put(m,u32(global_address+c.asset*4),0x87654321)
    p=count_pointer(c)
    if c.alias==3:p=u32(global_address+c.asset*4)
    return m,p

def public(m,c):return{a:b for a,b in m.items()if not STACK+c.phase-256<=a<STACK+c.phase+512}

def reference(initial,c=Case(),pointer=None,global_address=GLOBAL):
    m=dict(initial);p=count_pointer(c)if pointer is None else pointer;put(m,p,0);remaining=signed(c.occurrence)
    for i in range(256):
        op=m[LIST+8*i]
        if op==0xDF:return m,0xFFFFFFFF
        if op!=0xFD:continue
        value=read(m,LIST+8*i+4);key=read(m,u32(global_address+c.asset*4))
        if value!=key and c.asset!=0:continue
        old=remaining;remaining=signed(remaining-1)
        if old>0:continue
        tile=next(j for j in range(i,256)if m[LIST+8*j]==0xF2)
        cursor=tile+1
        while True:
            put(m,p,u32(read(m,p)+1));first,second=m[LIST+8*cursor],m[LIST+8*(cursor+1)];cursor+=2
            if(first,second)!=(0xF5,0xF2):return m,tile
    raise AssertionError('Unbounded display-list fixture')

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),pointer=None,entry=ENTRY,connected=None,arguments=None):
        p=count_pointer(c)if pointer is None else pointer
        super().__init__(words,memory,c,entry=entry,arguments=tuple(map(u32,(LIST,c.asset,c.occurrence,p)))if arguments is None else arguments,connected=connected)
        self.target_contracts=[]
    def record_call(self,target):
        assert target==ENTRY,hex(target)
        a=tuple(map(u32,self.arguments(4)));self.calls.append((target,a));self.events.append(('CALL',target,a))
        self.target_contracts.append((a,tuple(self.r[16:24]),self.r[28],self.r[29],self.r[30],self.r[31]))

def cases():
    for asset,occurrence,mask,pairs,ending in itertools.product((0,1,7761),(0,1,2,4,-1),(0,5,15),(1,3),(0,1,2,3)):
        yield Case(asset=asset,occurrence=occurrence,mask=mask,pairs=pairs,ending=ending)
    for op in range(256):yield Case(prefix=op,gap=op%4,ending=op%4)
    for asset in(-1,0x7FFFFFFF,0x80000000,0xFFFFFFFF):yield Case(asset=asset)
    for occurrence in(0x80000000,0x80000001,0x7FFFFFFF,0xFFFFFFFF):yield Case(occurrence=occurrence)
    for alias,phase in itertools.product(range(6),(0,8)):yield Case(alias=alias,phase=phase)

def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.current_pc,m.delay_of,m.all_accesses,m.visits)

class CallerCode(TrackedCode):
    def __getitem__(self,pc):
        if pc==self.return_pc:
            m=self.owner;contract=m.target_contracts[-1];args,saved,gp,sp,fp,ra=contract
            assert(tuple(m.r[16:24]),m.r[28],m.r[29],m.r[30],m.r[31])==(saved,gp,sp,fp,ra)
            c=replace(m.case,alias=0);expected,result=reference(m.initial_contract,c,args[3])
            assert m.r[2]==result and read(m.memory,args[3])==read(expected,args[3])
            m.completed_contracts+=1
        if pc in self.ends:raise WindowBoundary
        return super().__getitem__(pc)

def caller_machine(rom,words,c=Case(),which=0):
    # Original five-word argument setup plus return branch, captured result,
    # missing-texture jump and its delay update. The rest stays unqualified.
    start=(0x15195B08,0x15195E4C)[which];offset=start-0x15000000+0x2D4B0
    body=struct.unpack_from('>9I',rom,offset);initial,p=fixture(c);code=dict(zip(range(ENTRY,ENTRY+284,4),words))
    success=start+36;failure=(0x15195CA8,0x15195F58)[which]
    code.update({success:0,failure:0})
    m=Oracle(body,initial,c,entry=start,connected=code,arguments=())
    for reg,value in({30:LIST,20:c.asset,21:c.occurrence,17:0xFFFFFFFF}if which==0 else{22:LIST,19:c.asset,21:c.occurrence,23:0xFFFFFFFF}).items():m.r[reg]=u32(value)
    m.initial_contract=dict(initial);m.completed_contracts=0;m.code=CallerCode(m.code,m);m.code.return_pc=start+20;m.code.ends={success,failure}
    return m
