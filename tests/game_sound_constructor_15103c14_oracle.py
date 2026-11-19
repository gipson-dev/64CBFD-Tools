"""Independent constructor model, access prefixes, caller and callee ABI windows."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.experiments import game_sound_constructor_15103c14_match as match
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

ACTOR,OTHER,DATA,TIMERS=0x70000,0x80000,0xA0000,0x800D9AB0
LOOKUP,VALIDATE,RANDOM,REGISTER=0x1505EEF4,0x10010894,0x150ADA20,0x1000FA64
CALLBACK0,CALLBACK1=0x15103910,0x15103AA0
SYMS=dict(D_800D9AB0=TIMERS,func_1505EEF4=LOOKUP,func_10010894=VALIDATE,func_150ADA20=RANDOM,func_1000FA64=REGISTER,func_15103910=CALLBACK0,func_15103AA0=CALLBACK1)
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:((v&0xFFFFFFFF)^0x80000000)-0x80000000
half=lambda v:((v&65535)^32768)-32768
floating=lambda v:struct.unpack('>f',struct.pack('>I',v))[0]

@dataclass(frozen=True)
class Case:
    sound:int=0x1234
    key:int=0x89
    variants:int=3
    index:int=0
    paired:int=0
    cooldown:int=0
    actor:int=ACTOR
    reject:int=0
    random:int=0x89ABCDEF
    handle:int=0xFEDC
    camera:int=0
    coordinates:tuple=(0x418E0000,0xC2F70000,0x42C88000)
    mutation:int=0
    stages:int=15
    mutatedVariants:int=5
    mutatedPaired:int=0x80000000
    phase:int=0

def arguments(c):return tuple(map(u32,(c.sound,c.key,c.variants,c.index,c.paired)))
def timer(c):return u32(TIMERS+c.index*2)
def cases():
    for cooldown,sound,actor,reject,variants,paired,camera in itertools.product((0,1),(0x58D,0x1234),(0,ACTOR),(0,1),(0,3),(0,1),(0,1)):
        yield Case(cooldown=cooldown,sound=sound,actor=actor,reject=reject,variants=variants,paired=paired,camera=camera)
    for variants,random,paired,sound in itertools.product((1,2,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(0,1,0xFFFFFFFF),(0xFFFF,0xFFFFFFFF)):
        yield Case(variants=variants,random=random,paired=paired,sound=sound)
    for stage,mutation,camera in itertools.product((1,2,4,8,15),range(8),(0,1)):
        yield Case(stages=stage,mutation=mutation,camera=camera,actor=OTHER)
    for index in (-0x80000000,-1,0,1,2,3,4,0x7FFFFFFF):
        for phase in(0,8):yield Case(index=index,phase=phase)
    for coords in((0,0x80000000,1),(0xCF000000,0x4EFFFFFF,0x3F7FFFFF),(0xC7000000,0x46FFFE00,0x477FFF00),(0xBF400000,0x3F400000,0x3FC00000)):
        for camera in(0,1):yield Case(coordinates=coords,camera=camera)
    for stage,mutation,paired in itertools.product((1,2,4,15),(8,16,24,32,63),(0,1)):
        yield Case(stages=stage,mutation=mutation,paired=paired)
    for handle,camera,paired in itertools.product((0,0xFFFF),(0,1),(0,1)):yield Case(handle=handle,camera=camera,paired=paired)

def fixture(c):
    m={u32(STACK+i):(i*17+0xA5)&255 for i in range(-1024,1024)}
    for a,n in((ACTOR,0x32C),(OTHER,0x32C),(DATA,32),(TIMERS-8,32),(timer(c),2)):
        m.update({u32(a+i):(i*29+0x5A)&255 for i in range(n)})
    for a in(ACTOR,OTHER):
        for i,v in enumerate(c.coordinates):put(m,a+0x14+i*4,v)
        put(m,a+0x318,c.camera)
    put(m,timer(c),c.cooldown,2);put(m,STACK+c.phase+16,c.paired)
    return m

def effect(m,c,stage,home):
    bits=c.mutation if c.stages>>stage&1 else 0
    if bits&1:
        for a in(ACTOR,OTHER):
            for i,v in enumerate((0xC2F78000,0x43280000,0xBF400000)):put(m,a+0x14+i*4,v)
    if bits&2:
        for a in(ACTOR,OTHER):put(m,a+0x318,0 if read(m,a+0x318)else 1)
    if bits&4:put(m,timer(c),0x4321,2);put(m,TIMERS+6,0x8765,2)
    if bits&8:put(m,home+8,c.mutatedVariants)
    if bits&16:put(m,home+16,c.mutatedPaired)
    if bits&32:put(m,home+12,3)

class ZeroDivisorBoundary(Exception):pass
def reference(initial,c,snapshots=None):
    m=dict(initial);calls=[];home=STACK+c.phase;put(m,home+8,c.variants);cool=timer(c);sound=u32(c.sound)
    def call(target,args,stage):
        if snapshots is not None:snapshots.append(dict(memory=dict(m),target=target,args=tuple(map(u32,args))))
        calls.append((target,tuple(map(u32,args))));effect(m,c,stage,home)
    if read(m,cool,2)and sound!=0x58D:return m,calls
    call(LOOKUP,(c.key,),0)
    if not c.actor:return m,calls
    call(VALIDATE,(c.actor,),1)
    if c.reject:return m,calls
    variants=read(m,home+8)
    if variants:
        paired=read(m,home+16);call(RANDOM,(),2);variants=read(m,home+8)
        if not variants:raise ZeroDivisorBoundary
        sound=u32(sound+(c.random%variants)*(2 if paired else 1))
    primary=bool(read(m,c.actor+0x318));paired=read(m,home+16)
    if not primary and paired:sound=u32(sound+1)
    coords=tuple(u32(half(int(floating(read(m,c.actor+0x14+i*4)))))for i in range(3))
    args=(sound&65535,*coords,30000 if primary else 32700,32767,32766,
          CALLBACK0 if primary else CALLBACK1,20 if primary else u32(paired<<15)|20,c.actor,256,0)
    call(REGISTER,args,3);put(m,cool,600,2)
    return m,calls

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=match.ENTRY,connected=None,args=None):
        super().__init__(words,memory,c,entry=entry,s=SYMS,connected=connected,arguments=arguments(c)if args is None else args)
    def execute(self,word):
        if word>>26==0 and word&63==27 and self.r[word>>16&31]==0:raise ZeroDivisorBoundary
        return super().execute(word)
    def record_call(self,t):
        count={LOOKUP:1,VALIDATE:1,RANDOM:0,REGISTER:12,match.ENTRY:5}[t]
        args=tuple(map(u32,self.arguments(count)));self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        stage={LOOKUP:0,VALIDATE:1,RANDOM:2,REGISTER:3}[t];effect(self.memory,self.case,stage,self.target_home)
        for i in range(4):self.put(u32(self.r[29]+i*4),0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
        self.r[2]=u32({LOOKUP:self.case.actor,VALIDATE:self.case.reject,RANDOM:self.case.random,REGISTER:self.case.handle}[t])

def public(m):return{a:v for a,v in m.items()if not STACK-1024<=a<STACK+1024}
def check(machine,initial,c):
    memory,calls=reference(initial,c);assert(public(machine.memory),machine.calls)==(public(memory),calls),c
    assert machine.r[29]==STACK+c.phase and machine.r[31]==machine.before[31]
    assert all(machine.r[i]==machine.before[i]for i in range(16,24))
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.calls,m.trace,m.current_pc,m.delay_of,m.dispatched_word)
def streams(prepared):
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    rom=(match.ROOT/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>137I',rom,match.ROM))
    raw=bound_blob(prepared['raw'],prepared['refs'],SYMS)
    normalized=bound_blob(match.normalize(prepared['raw']),prepared['refs'],SYMS);assert normalized==truth
    return truth,raw,normalized

def guest_checks(prepared):
    allstreams=streams(prepared);truth=allstreams[0];count=0;visits=set()
    for c in cases():
        initial=fixture(c);pair=[]
        for words in allstreams:
            m=Oracle(words,initial,c).run();check(m,initial,c);pair.append(m)
            if words is truth:visits.update((pc-match.ENTRY)//4 for pc in m.visits)
        assert state(pair[0])==state(pair[1])==state(pair[2]);count+=1
    faults=0
    for c in(Case(),Case(paired=1),Case(camera=1),Case(cooldown=1),Case(actor=0),Case(reject=1),Case(variants=0),Case(mutation=63,stages=15)):
        initial=fixture(c);full=Oracle(truth,initial,c).run()
        for cut in range(full.all_accesses):
            pair=[]
            for words in allstreams:
                m=Oracle(words,initial,c);m.cut=cut
                try:m.run();raise AssertionError('Unfired constructor access boundary')
                except AccessBoundary:pass
                pair.append(m)
            assert state(pair[0])==state(pair[1])==state(pair[2]);faults+=1
    controls=0
    for at,xor in((0x30,1),(0x88,0x40),(0x10C,1),(0x178,4),(0x208,1)):
        wrong=truth[:];wrong[at//4]^=xor;rejected=False
        for c in(Case(),Case(paired=1),Case(camera=1),Case(cooldown=1,sound=0x58D),Case(variants=0),Case(random=0xFFFFFFFF)):
            try:initial=fixture(c);check(Oracle(wrong,initial,c).run(),initial,c)
            except(AssertionError,KeyError,ValueError,OverflowError):rejected=True;break
        assert rejected,hex(at);controls+=1
    # Zero can only appear here after a guest-only mutation of the incoming home.
    zero=0
    for paired in(0,1):
        c=Case(paired=paired,mutation=8,stages=4,mutatedVariants=0);initial=fixture(c);pair=[]
        for words in allstreams:
            m=Oracle(words,initial,c)
            try:m.run();raise AssertionError('Unfired zero divisor boundary')
            except ZeroDivisorBoundary:pass
            assert m.current_pc==match.ENTRY+(0x80 if paired else 0xB0)
            pair.append(m)
        assert state(pair[0])==state(pair[1])==state(pair[2]);zero+=1
    assert set(range(137))-visits=={37,49},sorted(set(range(137))-visits)
    assert truth[37]==truth[49]==0x0007000D
    return dict(cases_per_stream=count,streams=3,visited_words=len(visits),retained_break7_words=[37,49],all137_words_checked=True,
                fault_prefix_triples=faults,effective_instruction_controls=controls,zero_divisor_prefix_triples=zero,
                providers_opaque=True,finite_I32_float_domain=True,hardware_gameplay_or_full_parent_claim=False)

class WindowEnd(Exception):pass
class WindowCode(dict):
    def __init__(self,inner,end):super().__init__(inner);self.inner=inner;self.end=end;self[end]=0
    def __getitem__(self,pc):
        if pc==self.end:raise WindowEnd
        return self.inner[pc]

def caller_checks(prepared):
    rom=(match.ROOT/'conker/conker.us.bin').read_bytes();window=list(struct.unpack('>11I',rom[0xCC6A0:0xCC6CC]));prefix=list(struct.unpack('>7I',rom[0xFA64:0xFA80]))
    count=prefixes=0
    for cooldown,sound,variants,paired,camera,actor in itertools.product((0,1),(0x58D,0xFFFF),(0,3),(0,1),(0,1),(0,ACTOR)):
        c=Case(cooldown=cooldown,sound=sound,variants=variants,paired=paired,camera=camera,actor=actor);initial=fixture(c)
        for at,value in((8,c.variants),(12,c.key|0xABCD0000),(16,c.index),(20,c.paired)):put(initial,DATA+at,value)
        put(initial,STACK+0x30,c.sound);expected,calls=reference(initial,c);pair=[]
        for words in streams(prepared):
            connected=dict(zip(range(match.ENTRY,match.ENTRY+548,4),words));m=Oracle(window,initial,c,entry=0x1509F1F0,connected=connected)
            m.code=WindowCode(m.code,0x1509F234);m.r[16]=DATA
            try:m.run();raise AssertionError('Unfired caller continuation')
            except WindowEnd:pass
            assert m.calls==[(match.ENTRY,arguments(c)),*calls]and m.r[2]==0x7000 and public(m.memory)==public(expected)
            assert m.r[29]==STACK and m.r[16]==DATA;pair.append(m)
        assert state(pair[0])==state(pair[1])==state(pair[2]);count+=1
        for target,args in calls:
            if target!=REGISTER:continue
            memory=dict(initial)
            for i,v in enumerate(args[4:],4):put(memory,STACK+i*4,v)
            m=Oracle(prefix,memory,c,entry=REGISTER,args=args);m.code=WindowCode(m.code,0x1000FA80)
            try:m.run();raise AssertionError('Unfired callee home boundary')
            except WindowEnd:pass
            assert m.r[29]==STACK-40 and tuple(read(m.memory,STACK+i*4)for i in range(12))==args
            assert read(m.memory,STACK-12)==m.before[31]and read(m.memory,STACK-16)==m.before[16];prefixes+=1
    return dict(original_caller_words=11,caller_scenarios=count,streams=3,original_callee_words=7,callee_home_checks=prefixes,
                constructor_result_ignored=True,providers_opaque=True,full_parent_claim=False)
