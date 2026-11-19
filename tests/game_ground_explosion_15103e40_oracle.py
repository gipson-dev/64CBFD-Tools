"""Independent explosion contract and bounded instruction/access-order checks.

The numerical model rounds each finite operation to IEEE single. It does not
model FCSR, interrupts, unbounded providers or physical gameplay acceptance.
"""
from dataclasses import dataclass, replace
import itertools
import struct
from tools.experiments import game_ground_explosion_15103e40_match as match
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.game_animation_timeline_oracle import bits, floating

POSITION,SOURCE,GROUND_CONTEXT,OTHER_SOURCE,OTHER_CONTEXT=0x30000,0x70000,0x60000,0x71000,0x61000
OPEN,INIT,QUERY,FLOAT_RANDOM,INT_RANDOM=0x151D3FF4,0x1504715C,0x15046C80,0x150ADA68,0x150ADA20
GROUND,SELECT,EFFECT1,EFFECT2,FINISH,ACTOR,AUDIO,FINAL=(
    0x150E7FEC,0x150E83AC,0x151D5404,0x151D5334,0x151D5514,0x151D40D4,0x15055A2C,0x151541B8)
COUNTS={OPEN:3,INIT:2,QUERY:4,FLOAT_RANDOM:0,INT_RANDOM:0,GROUND:12,SELECT:4,
        EFFECT1:8,EFFECT2:7,FINISH:3,ACTOR:8,AUDIO:5,FINAL:7,match.ENTRY:7}
SYMS={'func_%08X'%t:t for t in COUNTS if t!=match.ENTRY}
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:((n&0xFFFFFFFF)^0x80000000)-0x80000000
add=lambda a,b:bits(floating(a)+floating(b))
mul=lambda a,b:bits(floating(a)*floating(b))

@dataclass(frozen=True)
class Case:
    address:int=POSITION
    source:int=SOURCE
    ground_context:int=GROUND_CONTEXT
    mode:int=2
    detail:int=0x89ABCDEF
    slot:int=0xABCD00FF
    context:int=0x87654321
    position:tuple=(0x418C0000,0x42C88000,0xC2F78000)
    hit:int=1
    flags:int=1
    height:int=0x41180000
    move_probe:int=1
    integers:tuple=(0xFFFFFFFF,0x80000000,0x7FFFFFFF,0)
    floats:tuple=(0x3F7FFFFF,0x3E800000)
    mutation:int=0
    stages:int=(1<<17)-1
    phase:int=0

def arguments(c):return tuple(map(u32,(c.source,c.ground_context,c.address,c.mode,c.detail,c.slot,c.context)))
def frame(home):return home-152
def vector(m,p):return tuple(read(m,p+i*4)for i in range(3))
def vector_put(m,p,v):
    for i,w in enumerate(v):put(m,p+i*4,w)

def cases():
    for source,hit,flags,mode in itertools.product((0,SOURCE),(0,1),(0,1,3,128),(0,2)):
        yield Case(source=source,hit=hit,flags=flags,mode=mode)
    for value,mode,hit in itertools.product((0,1,100,101,301,302,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,2),(0,1)):
        yield Case(integers=(value,)*4,mode=mode,hit=hit)
    for ordinal,mutation in itertools.product(range(17),range(1,16)):
        yield Case(stages=1<<ordinal,mutation=mutation,mode=ordinal%3)
    for mutation,hit in itertools.product((1,2,4,8,15,16,17,31),(0,1)):
        yield Case(mutation=mutation,hit=hit)
    for ordinal,mode in itertools.product(range(17),(0,2)):
        yield Case(mutation=16,stages=1<<ordinal,mode=mode)
    for value in(0,0x80000000,1,0x3EFFFFFF,0x3F000000,0x3F7FFFFF,0x3F800000):
        yield Case(floats=(value,value))
    for position in((0,0x80000000,1),(0xCF000000,0x4EFFFFFF,0x3F7FFFFF),
                     (0xBF400000,0x3F400000,0x3FC00000)):
        for phase in(0,8):yield Case(position=position,phase=phase)
    for mode,slot,context in itertools.product((0xFFFFFF00,0x80000001,0xABCDEF02,255),(0,0xFFFFFF80),(0,0xFFFFFFFF)):
        yield Case(mode=mode,slot=slot,context=context)

def fixture(c):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
    for a,n in((POSITION,12),(SOURCE,16),(GROUND_CONTEXT,16),(OTHER_SOURCE,16),(OTHER_CONTEXT,16)):
        m.update({a+i:(i*29+0x5A)&255 for i in range(n)})
    vector_put(m,c.address,c.position)
    for i,v in enumerate(arguments(c)[4:],4):put(m,STACK+c.phase+i*4,v)
    return m

def initialize_ground(m,p,c):
    for i in range(36):m[p+i]=(i*13+0xA7)&255
    put(m,p,c.height);m[p+28]=c.flags
    for i in range(9):put(m,p+4+i*2,0x8000+i*0x1234,2)

def snapshot(m,home,exposed,address=POSITION):
    f=frame(home);values=list(vector(m,address))
    values.extend([read(m,f+0x58),m[f+0x74],*(read(m,f+0x5C+i*2,2)for i in range(9))]if exposed&1 else[0]*11)
    values.extend(vector(m,f+0x7C)if exposed&2 else(0,0,0))
    values.extend(vector(m,f+0x8C)if exposed&4 else(0,0,0))
    return exposed,tuple(values)

def effect(m,c,n,home,exposed):
    mutation=c.mutation if c.stages>>n&1 else 0;f=frame(home)
    if mutation&1:vector_put(m,c.address,(bits(-17.5+n),bits(80.25-n),bits(0.75+n)))
    if mutation&2 and exposed&1:
        put(m,f+0x58,bits(-3.25+n));m[f+0x74]^=1
        for i in range(9):put(m,f+0x5C+i*2,read(m,f+0x5C+i*2,2)^(n+i+1),2)
    if mutation&4 and exposed&2:vector_put(m,f+0x7C,(bits(30.5+n),bits(-1.25-n),bits(60.75+n)))
    if mutation&8 and exposed&4:vector_put(m,f+0x8C,(bits(-60.5-n),bits(4.25+n),bits(2.75-n)))
    if mutation&16:
        for off,v in((0,OTHER_SOURCE),(4,OTHER_CONTEXT),(12,n%3),(16,0xFEDC0000+n),(20,0xABCD0080+n),(24,0x13570000+n)):
            put(m,home+off,v)

def provider(m,c,t,n,home,exposed,ri,rf):
    f=frame(home);answer=0xC5000000+n
    if t==INIT:initialize_ground(m,f+0x58,c);exposed|=1
    if t==QUERY:
        put(m,f+0x58,c.height);m[f+0x74]=c.flags
        if c.move_probe:vector_put(m,f+0x7C,(bits(17.25),bits(25.5),bits(-31.75)))
        answer=u32(c.hit)
    if t==INT_RANDOM:answer=c.integers[ri];ri+=1
    if t==FLOAT_RANDOM:answer=c.floats[rf];rf+=1
    effect(m,c,n,home,exposed)
    return answer,exposed,ri,rf

def reference(initial,c,home=None):
    m=dict(initial);home=STACK+c.phase if home is None else home;f=frame(home);calls=[];snaps=[];returns=[];exposed=ri=rf=0
    for i in(0,1,3):put(m,home+i*4,arguments(c)[i])
    def call(t,*args):
        nonlocal exposed,ri,rf
        if t==QUERY:exposed|=2
        if t==GROUND:exposed|=4
        args=tuple(map(u32,args));calls.append((t,args));snaps.append(snapshot(m,home,exposed,c.address))
        answer,exposed,ri,rf=provider(m,c,t,len(calls)-1,home,exposed,ri,rf);returns.append(answer)
        return answer
    slot=lambda:m[home+23]
    context=lambda:read(m,home+24)
    if c.source:
        m[f+0x8B]=0;call(OPEN,c.address,slot(),context())
        v=vector(m,c.address);vector_put(m,f+0x7C,(v[0],add(v[1],bits(100.0)),v[2]))
        call(INIT,f+0x58,read(m,home+4))
        if call(QUERY,f+0x7C,0,add(read(m,c.address+4),bits(-100.0)),f+0x58)and m[f+0x74]&1:
            vector_put(m,f+0x8C,(read(m,f+0x7C),read(m,f+0x58),read(m,f+0x84)));m[f+0x8B]=1
            sample=call(FLOAT_RANDOM);a=call(INT_RANDOM);b=call(INT_RANDOM)
            call(GROUND,add(mul(sample,bits(125.0)),bits(204.0)),a%101+155,f+0x5C,f+0x8C,b%302+500,0,1,0,0,0,slot(),0)
        selected=f+0x8C if m[f+0x8B]else c.address
        a=call(INT_RANDOM);call(SELECT,selected,a%62+120,slot(),context())
        call(EFFECT1,c.address,0x43FD0000,0x447D4000,0x3A8163D3,15,20,slot(),context())
        call(EFFECT2,c.address,0x43FD0000,0x447D4000,0x3A8163D3,5,slot(),context())
        call(FINISH,c.address,slot(),context())
        mode=m[home+15]
        if mode:call(ACTOR,c.address,0,read(m,home),read(m,home+4),0,0x42 if mode==2 else 0x2B,0x41 if mode==2 else 0x2A,read(m,home+16))
        call(AUDIO,0,*vector(m,c.address),1)
        sample=call(FLOAT_RANDOM);a=call(INT_RANDOM)
        call(FINAL,c.address,add(mul(sample,bits(4.0)),bits(12.0)),0x3FD20C49,bits(float(a%56+200)),0,slot(),context())
    return m,calls,snaps,returns

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=match.ENTRY,connected=None,args=None):
        super().__init__(words,memory,c,entry=entry,s=SYMS,connected=connected,arguments=arguments(c)if args is None else args)
        self.exposed=self.ri=self.rf=0;self.snapshots=[]
    def record_call(self,t):
        if t==match.ENTRY:self.target_home=self.r[29]
        if t==QUERY:self.exposed|=2
        if t==GROUND:self.exposed|=4
        a=list(map(u32,self.arguments(COUNTS[t])))
        if t==GROUND:a[0]=self.f[12]
        self.calls.append((t,tuple(a)));self.events.append(('CALL',t,tuple(a)))
        if t!=match.ENTRY:self.snapshots.append(snapshot(self.memory,self.target_home,self.exposed,self.case.address))
    def hook(self,t):
        n=len(self.snapshots)-1
        value,self.exposed,self.ri,self.rf=provider(self.memory,self.case,t,n,self.target_home,self.exposed,self.ri,self.rf)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
        self.r[2]=u32(value)
        if t==FLOAT_RANDOM:self.f[0]=value

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
def check(machine,initial,c,home=None):
    m,calls,snaps,_=reference(initial,c,home)
    assert(public(machine.memory),machine.calls,machine.snapshots)==(public(m),calls,snaps),c
    assert machine.r[29]==STACK+c.phase and machine.r[31]==machine.before[31]
    assert all(machine.r[i]==machine.before[i]for i in range(16,24))

def rename_address(p,home):
    f=frame(home)
    if f+0x44<=p<f+0x48:return p+16
    if f+0x54<=p<f+0x58:return p-16
    return p
def rename_memory(m,home):return{rename_address(p,home):v for p,v in m.items()}
def state(m,raw=False):
    memory=m.memory;trace=m.trace;word=m.dispatched_word
    if raw:
        memory=rename_memory(memory,m.target_home)
        trace=[(kind,rename_address(p,m.target_home),n,v)for kind,p,n,v in trace]
        if m.current_pc-match.ENTRY in match.SPEC['frame_cell']['access_offsets']:word-=16
    return(memory,m.r,m.f,m.hi,m.lo,m.calls,trace,m.current_pc,m.delay_of,word)

def streams(prepared):
    truth=list(struct.unpack_from('>202I',(match.ROOT/'conker/conker.us.bin').read_bytes(),match.ROM))
    raw=bound_blob(prepared['raw'],prepared['refs'],SYMS)
    guarded=bound_blob(match.normalize(prepared['raw']),prepared['refs'],SYMS);assert guarded==truth
    return truth,raw,guarded

def cell_initialization(words):
    """Explore both branch outcomes, honoring delay slots and likely annuls."""
    todo=[(0,None,False)];seen=set();loads=set();stores=set()
    while todo:
        pc,continuation,initialized=todo.pop()
        if pc is None:continue
        key=(pc,continuation,initialized)
        if key in seen:continue
        seen.add(key);assert 0<=pc<len(words)
        w=words[pc];op,rs,rt=w>>26,w>>21&31,w>>16&31;offset=((w&65535)^32768)-32768
        if rs==29 and offset==0x54 and op in(0x31,0x39):
            if op==0x31:assert initialized,hex(pc*4);loads.add(pc*4)
            else:initialized=True;stores.add(pc*4)
        if continuation is not None:
            if continuation!=-1:todo.append((continuation,None,initialized))
            continue
        if op==3:todo.append((pc+1,pc+2,initialized))
        elif op==0 and w&63==8:todo.append((pc+1,-1,initialized))
        elif op in(1,4,5,6,7,20,21,22,23):
            target=pc+1+offset;todo.append((pc+1,target,initialized))
            if not(op==4 and rs==rt):
                todo.append((pc+2,None,initialized)if op>=20 else(pc+1,pc+2,initialized))
        else:todo.append((pc+1,None,initialized))
    assert stores=={0xD4,0x298}and loads=={0x104,0x29C}
    return dict(CFG_states=len(seen),initialized_on_all_load_paths=True,stores=sorted(stores),loads=sorted(loads))

def guest_checks(prepared):
    allstreams=streams(prepared);truth=allstreams[0];count=faults=0;visits=set()
    for c in cases():
        initial=fixture(c);pair=[]
        for i,words in enumerate(allstreams):
            m=Oracle(words,rename_memory(initial,STACK+c.phase)if i==1 else initial,c).run();check(m,initial,c);pair.append(state(m,i==1))
            if i==0:visits.update((pc-match.ENTRY)//4 for pc in m.visits)
        assert pair[0]==pair[1]==pair[2],c;count+=1
    for c in(Case(),Case(source=0),Case(hit=0,mode=0),Case(flags=128),Case(mutation=31),Case(mutation=15,phase=8)):
        initial=fixture(c);full=Oracle(truth,initial,c).run()
        for cut in range(full.all_accesses):
            pair=[]
            for i,words in enumerate(allstreams):
                m=Oracle(words,rename_memory(initial,STACK+c.phase)if i==1 else initial,c);m.cut=cut
                try:m.run();raise AssertionError('Unfired explosion access boundary')
                except AccessBoundary:pass
                pair.append(state(m,i==1))
            assert pair[0]==pair[1]==pair[2],(c,cut);faults+=1
    controls=0
    for at,xor in((0x24,1),(0xA8,1),(0xE0,0x10000),(0x1B8,1),(0x240,1),(0x284,1)):
        wrong=truth[:];wrong[at//4]^=xor;rejected=False
        for c in(Case(),Case(source=0),Case(hit=0),Case(flags=128),Case(mode=1),Case(mode=0)):
            try:initial=fixture(c);check(Oracle(wrong,initial,c).run(),initial,c)
            except(AssertionError,KeyError,ValueError,OverflowError,ZeroDivisionError):rejected=True;break
        assert rejected,hex(at);controls+=1
    missing=set(range(202))-visits;assert missing=={92,185,186,187,188},sorted(missing)
    return dict(cases_per_stream=count,streams=3,visited_words=len(visits),retained_unreachable_words=sorted(missing),
                fault_prefix_triples=faults,effective_instruction_controls=controls,
                raw_state_relation='bijection swapping only the two unexposed four-byte sample cells',
                cell_initialization=cell_initialization(allstreams[1]),providers_opaque=True,FCSR_or_hardware_claim=False)

def caller_checks(prepared):
    import re
    rom=(match.ROOT/'conker/conker.us.bin').read_bytes();scenarios=[];counts={}
    for entry,mode in((0x1506AB7C,1),(0x1506ABC4,2)):
        words=list(struct.unpack_from('>18I',rom,entry-0x15000000+0x2D4B0));counts[hex(entry)]=18
        for source,hit,flags in itertools.product((0,SOURCE),(0,1),(0,1)):
            c=Case(source=source,mode=mode,slot=255,context=1,hit=hit,flags=flags);initial=fixture(c);record=POSITION-4
            put(initial,record,c.ground_context);put(initial,record+16,c.detail)
            scenarios.append((entry,words,c,initial,(source,record),STACK-40))
    assembly=(match.ROOT/'conker/asm/nonmatchings/game_981E0/func_15070C40.s').read_text()
    words=[int(w,16)for w in re.findall(r'/\*\s*[0-9A-Fa-f]+\s+[0-9A-Fa-f]+\s+([0-9A-Fa-f]{8})\s*\*/',assembly)]
    counts['0x15070c40']=len(words)
    for mode,index,hit,flags in itertools.product((0,1,2,255),(0,2),(0,1),(0,1)):
        source=GROUND_CONTEXT if not index else 0x800CC2D0+(index-1)*0x32C
        c=Case(address=STACK-12,source=source,mode=mode,slot=255,context=0,detail=0,hit=hit,flags=flags)
        initial=fixture(c);initial.update({GROUND_CONTEXT+i:0xA5 for i in range(0x32C)})
        put(initial,0x800D154C,GROUND_CONTEXT);initial[GROUND_CONTEXT+0x124]=index
        vector_put(initial,GROUND_CONTEXT+0x14,c.position)
        scenarios.append((0x15070C40,words,c,initial,(mode,),STACK-64))
    for entry,words,c,initial,args,home in scenarios:
        model=dict(initial)
        for i,v in enumerate(arguments(c)[4:],4):put(model,home+i*4,v)
        expected,calls,snaps,_=reference(model,c,home);pair=[]
        for i,target in enumerate(streams(prepared)):
            connected=dict(zip(range(match.ENTRY,match.ENTRY+808,4),target))
            m=Oracle(words,rename_memory(initial,home)if i==1 else initial,c,entry=entry,connected=connected,args=args).run()
            assert(m.calls,m.snapshots,public(m.memory))==([(match.ENTRY,arguments(c)),*calls],snaps,public(expected)),(hex(entry),c)
            assert m.r[29]==STACK and m.r[31]==m.before[31]
            assert all(m.r[r]==m.before[r]for r in range(16,24))
            pair.append(state(m,i==1))
        assert pair[0]==pair[1]==pair[2]
    return dict(complete_original_callers=counts,scenarios=len(scenarios),streams=3,void_result_ignored=True,providers_opaque=True,hardware_or_gameplay_claim=False)
