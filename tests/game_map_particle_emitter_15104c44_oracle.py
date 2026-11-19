"""Independent sampled map-particle contract; hardware FCSR is not modeled."""
from dataclasses import dataclass
from collections import Counter
from pathlib import Path
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY=0x15104C44;RECORD=0x30000;TAIL=RECORD+0x28;GATEPTR=0x40000;MARK=0x70000
REMOVE,GATE,REAL,RNG,DIRECTION,PROBE,SPAWN=0x1000FD38,0x151464B8,0x150ADA68,0x150ADA20,0x15143874,0x15046C80,0x15105CE0
TICKS,TIME,RATE,RANGE=0x800BE9E4,0x800BE9A4,0x800A23AC,0x800A23B0
ONE,HALF=bits(1.),bits(.5)
u32=lambda n:n&0xffffffff
short=lambda n:((n&65535)^32768)-32768
f32=lambda n:bits(float(n))
@dataclass(frozen=True)
class Case:
    timer:int=3
    ticks:int=1
    blocked:int=0
    accumulator:int=bits(2.25)
    time:int=bits(1.)
    hits:int=15
    mutation:int=0
    seed:int=0
    phase:int=0
    rule:str='left'
def cases():
    for timer,ticks,blocked,accumulator,time in itertools.product((-1,0,1,32767),(0,1,-1,0x7fffffff,0x80000000),(0,1),(bits(0.),bits(1.),0x3f800001,bits(3.25),0x7fc12345),(bits(0.),bits(1.))):
        yield Case(timer,ticks,blocked,accumulator,time,seed=(timer+ticks)&15)
    for mutation,hits,phase,seed in itertools.product(range(16),(0,5,15),(0,8),(0,5)):
        yield Case(mutation=mutation,hits=hits,phase=phase,seed=seed)
    for accumulator,time,rule in itertools.product((0x80000000,0x7fc01234,0xffc05678,0x7f800001),(bits(0.),0x7fc000AB),('left','right')):
        yield Case(accumulator=accumulator,time=time,rule=rule)
def fixture(c):
    m={STACK+i:(i*17+c.seed+0xa5)&255 for i in range(-768,256)}
    m.update({RECORD+i:(i*29+c.seed+0x5a)&255 for i in range(0x90)})
    m[RECORD+1]=0x18+c.seed;m[RECORD+0xC]=0xE1-c.seed;m[RECORD+0xD]=0
    put(m,RECORD+0xE,100,2);m[RECORD+0x10]=255;m[RECORD+0x11]=60
    put(m,TAIL,0x12345678);put(m,TAIL+4,c.accumulator);put(m,TAIL+8,c.timer,2)
    for offset,value in((0xC,1.25),(0x10,20.5),(0x14,-3.75),(0x18,4.5),(0x1C,60.25),(0x20,-7.5)):
        put(m,TAIL+offset,bits(value))
    put(m,TAIL+0x44,GATEPTR);put(m,GATEPTR,0);put(m,GATEPTR+2,0 if c.blocked else 1,2);put(m,0x80082FA0,2)
    for address,value in((TICKS,c.ticks),(TIME,c.time),(RATE,0x3E49BA5F),(RANGE,0x3E99999A),(MARK,0x11223344)):put(m,address,u32(value))
    return m
def public(m):return{a:v for a,v in m.items()if not STACK-768<=a<STACK+256}
def random(c,index):return(0,0xffffffff,0x80000000,0x7fffffff,255,256,13,156,3,0x12345678)[(index+c.seed)%10]
def real(c,index):return bits((0.,.125,.5,1.,-.0)[(index+c.seed)%5])
def direction(angle,radius,c):
    a=angle&255
    return fp(radius,bits((a-128)/128.),'mul',c.rule),fp(radius,bits((127-a)/128.),'mul',c.rule)
def packet(data):return tuple(data[i]for i in range(80)if i not in(3,0x35,0x36,0x37,0x4D,0x4E,0x4F))
def effects(m,c,target,index,pointer=0):
    put(m,MARK,0xaabb0000|((target>>2)&65535))
    if c.mutation&1 and target==REAL and index==0:
        for a,v in((RATE,bits(.25)),(RANGE,bits(.5)),(TIME,bits(.5)),(TAIL+4,bits(2.5))):put(m,a,v)
    if target==PROBE:
        for i in range(36):m[TAIL+0x20+i]=(i*13+c.seed+index)&255
        put(m,TAIL+0x20,bits(-7.5+index*.25));put(m,TAIL+0x44,GATEPTR)
        if c.mutation&2:
            put(m,TAIL+0xC,bits(10.5));put(m,TAIL+0x14,bits(31.25));put(m,TAIL+0x18,bits(2.75))
        if c.mutation&8 and pointer:
            put(m,pointer,fp(read(m,pointer),bits(.25),'add',c.rule));put(m,pointer+8,fp(read(m,pointer+8),bits(-.5),'add',c.rule))
    if c.mutation&4 and target==SPAWN:
        put(m,TAIL+4,bits(1.5));m[RECORD+1]^=0x17;m[RECORD+0xC]^=0x21
def reference(initial,c):
    m=dict(initial);calls=[];packets=[];counts=Counter();sample=[0,0,0]
    def invoke(t,args=(),payload=None):
        i=counts[t];counts[t]+=1;calls.append((t,args))
        if payload is not None:packets.append(payload)
        # The independent model keeps local coordinates in logical slots.
        if t==PROBE:
            effects(m,c,t,i)
            if c.mutation&8:
                sample[0]=fp(sample[0],bits(.25),'add',c.rule);sample[2]=fp(sample[2],bits(-.5),'add',c.rule)
        else:effects(m,c,t,i)
        return real(c,i)if t==REAL else random(c,i)if t==RNG else c.blocked if t==GATE else bool(c.hits&(1<<(i%4)))if t==PROBE else 0
    def add(a,b):return fp(a,b,'add',c.rule)
    def mul(a,b):return fp(a,b,'mul',c.rule)
    def field(at):return read(m,TAIL+at)
    if short(read(m,TAIL+8,2))<0:return public(m),calls,packets
    timer=short(u32(short(read(m,TAIL+8,2))-read(m,TICKS)));put(m,TAIL+8,timer,2)
    if timer<0:invoke(REMOVE,(0x1000EF40,field(0),0))
    if invoke(GATE,(field(0x44),)):return public(m),calls,packets
    v=invoke(REAL);increment=mul(add(read(m,RATE),mul(v,read(m,RANGE))),read(m,TIME))
    put(m,TAIL+4,add(field(4),increment))
    if not floating(field(4))>1.:return public(m),calls,packets
    sample[1]=add(field(0x10),field(0x1C))
    descriptor={};base={}
    def word(at,v):put(descriptor,at,v)
    descriptor[2]=1;descriptor[0x34]=255;put(descriptor,0x44,3,2);put(descriptor,0x46,4,2);descriptor[0x4C]=0
    word(0x40,bits(45.));word(0x3C,bits(25.));word(4,field(0xC));word(8,add(field(0x10),field(0x1C)));word(12,field(0x14))
    descriptor[0x48]=0x61;descriptor[0x49]=0xF2;descriptor[0x4A]=255
    word(0x14,fp(add(field(0x10),field(0x1C)),bits(180.),'sub',c.rule))
    iterations=0
    while True:
        iterations+=1;assert iterations<16,'fixture must terminate'
        angle=invoke(RNG)&255;v=invoke(REAL);radius=mul(add(mul(v,HALF),HALF),field(0x18))
        invoke(DIRECTION,(angle,radius,0,1));sample[0],sample[2]=direction(angle,radius,c)
        sample[0]=add(sample[0],field(0xC));sample[2]=add(sample[2],field(0x14))
        hit=invoke(PROBE,(tuple(sample),0,field(0x10),TAIL+0x20))
        if hit:
            angle=invoke(RNG)&255;v=invoke(REAL);radius=mul(v,bits(220.));invoke(DIRECTION,(angle,radius,2,3));sx,sz=direction(angle,radius,c)
            angle=invoke(RNG)&255;v=invoke(REAL);radius=mul(v,bits(220.));invoke(DIRECTION,(angle,radius,4,5));ex,ez=direction(angle,radius,c)
            word(0x10,add(field(0xC),sx));word(0x18,add(field(0x14),sz))
            word(0x28,sample[0]);word(0x2C,field(0x20));word(0x30,sample[2])
            word(0x1C,add(sample[0],ex));word(0x24,add(sample[2],ez));word(0x20,add(field(0x20),bits(180.)))
            put(descriptor,0,invoke(RNG)%13+8,2);descriptor[0x4B]=(invoke(RNG)%156+100)&255;word(0x38,invoke(RNG)%3+5)
            invoke(SPAWN,(0,0,m[RECORD+0xC],m[RECORD+1]),tuple(descriptor[i]for i in range(80)if i not in(3,0x35,0x36,0x37,0x4D,0x4E,0x4F)))
        put(m,TAIL+4,fp(field(4),ONE,'sub',c.rule))
        if not floating(field(4))>1.:break
    return public(m),calls,packets
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None):
        super().__init__(words,memory,c,entry=entry,connected=connected,arguments=(RECORD,));self.c=c;self.counts=Counter();self.packets=[];self.raw_packets=[];self.roles={}
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63 in(0,1,2):
            self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],{0:'add',1:'sub',2:'mul'}[w&63],self.c.rule)
        else:super().execute(w)
    def record_call(self,t):
        if t==REMOVE:args=tuple(self.r[4:7])
        elif t==GATE:args=(self.r[4],)
        elif t in(RNG,REAL):args=()
        elif t==DIRECTION:
            args=(self.r[4],self.r[5],None,None)
            positions=sorted({self.r[6],self.r[7],*self.roles})
            self.roles[self.r[6]]=self.roles.get(self.r[6],len(self.roles));self.roles[self.r[7]]=self.roles.get(self.r[7],len(self.roles))
            args=(self.r[4],self.r[5],self.roles[self.r[6]],self.roles[self.r[7]])
        elif t==PROBE:args=(tuple(read(self.memory,self.r[4]+i*4)for i in range(3)),self.r[5],self.r[6],self.r[7])
        elif t==SPAWN:
            args=(0,*self.r[5:8]);captured={i:self.memory[self.r[4]+i]for i in range(80)}
            self.packets.append(packet(captured));self.raw_packets.append(bytes(captured.values()))
        elif t==ENTRY:args=(self.r[4],)
        else:raise AssertionError(('helper',hex(t)))
        self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        i=self.counts[t];self.counts[t]+=1;c=self.c;arguments=self.r[4:8]
        value=real(c,i)if t==REAL else random(c,i)if t==RNG else c.blocked if t==GATE else int(bool(c.hits&(1<<(i%4))))if t==PROBE else 0
        if t==DIRECTION:
            x,z=direction(arguments[0],arguments[1],c);put(self.memory,arguments[2],x);put(self.memory,arguments[3],z)
        effects(self.memory,c,t,i,arguments[0]if t==PROBE else 0)
        for j in range(4):self.put(self.r[29]+j*4,0xb5000000+j,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+j for j in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
        if t==REAL:self.f[0]=value
        else:self.r[2]=value
def guest_checks(truth,raw):
    visited=[set(),set()];count=0
    for c in cases():
        initial=fixture(c);expected=reference(initial,c);raw_payloads=[]
        for i,words in enumerate((truth,raw)):
            machine=Oracle(words,initial,c).run();actual=(public(machine.memory),machine.calls,machine.packets)
            assert actual==expected,(c,i,'public/calls/packets',next(((j,a,b)for j,(a,b)in enumerate(zip(actual[1],expected[1]))if a!=b),None))
            assert machine.r[29]==STACK+c.phase and all(machine.r[reg]==machine.before[reg]for reg in(*range(16,24),28,30,31))and machine.f[20:]==machine.saved_f
            raw_payloads.append(machine.raw_packets)
            visited[i].update((pc-ENTRY)//4 for pc in machine.visits if ENTRY<=pc<ENTRY+len(words)*4)
        assert raw_payloads[0]==raw_payloads[1],('full80byte copied payload',c)
        count+=1
    return dict(cases=count,streams=2,visited_words=[len(v)for v in visited],unvisited_words=[sorted(set(range(len(w)))-v)for w,v in zip((truth,raw),visited)],all_80_copied_guest_bytes_equal=True,source_installed=False,matching_credit=0,hardware_NaN_FCSR_not_claimed=True)
def caller_checks(truth,raw,root):
    rom=(root/'conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>45I',rom,0x176714));count=0;parent_visits=set()
    assert struct.unpack_from('>I',rom,0x22F098)[0]==ENTRY
    for c in list(cases())[::10]:
        initial=fixture(c);put(initial,0x8008A5D8,ENTRY);expected=reference(initial,c)
        for words in(truth,raw):
            connected=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));machine=Oracle(parent,initial,c,entry=0x15149264,connected=connected).run()
            assert(public(machine.memory),machine.calls,machine.packets)==(expected[0],[(ENTRY,(RECORD,)),*expected[1]],expected[2]),c
            assert machine.r[29]==STACK+c.phase and machine.r[31]==machine.before[31]
            assert all(machine.r[j]==machine.before[j]for j in(*range(16,24),28,30))and machine.f[20:]==machine.saved_f
            parent_visits.update((v-0x15149264)//4 for v in machine.visits if 0x15149264<=v<0x15149318)
        count+=1
    return dict(scenarios=count,streams=2,original_parent_words=45,parent_words_visited=len(parent_visits),registry=0x8008A4E8,slot=60,literal_ROM=0x22F098,void_return_not_consumed=True,full_parent_or_cleanup_qualification_not_claimed=True)
def instruction_controls(truth):
    controls=[('initial-timer-field',0x40,2),('gate-branch',0x8C,1<<16),('integer-remainder-sign',0x300,1),('particle-duration',0x308,1),
        ('channel-byte',0x344,1),('saved-F26',0x384,1<<16),('descriptor-pointer',0x348,4),('packet-copy-consumer',0x34C,1)]
    effective=[]
    for name,at,mask in controls:
        wrong=truth[:];wrong[at//4]^=mask;rejected=False
        for c in [Case(seed=j)for j in range(6)]+[Case(timer=-1),Case(timer=0),Case(blocked=1)]:
            try:
                m=fixture(c);model=Oracle(wrong,m,c).run();assert(public(model.memory),model.calls,model.packets)==reference(m,c)
                assert model.f[20:]==model.saved_f
            except(AssertionError,KeyError,ValueError):rejected=True;break
        assert rejected,('ineffective instruction control',name);effective.append(name)
    return dict(effective_instruction_controls=effective)
