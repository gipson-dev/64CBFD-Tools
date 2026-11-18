"""Independent record constructor reference, retained binding and real memcpy."""
from pathlib import Path
from dataclasses import dataclass,asdict
from functools import lru_cache
import itertools,json,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_owner_record_151b09bc_derive as normalizer
from tools.experiments import game_owner_record_151b09bc_match as recovery
p=recovery.OUT
ENTRY=0x151B09BC
A,S,ALT,O,MARK,TABLE=0x30000,0x90000,0x50000,0x60000,0x70000,0x800A3FE6
CLASSIFY,BIND,FACTORY,COPY=0x15134070,0x151494E0,0x151491F4,0x10022EC0
COUNTS={CLASSIFY:1,BIND:2,FACTORY:8,COPY:3}
HOLES=(5,6,7,149,150,151)
u32=lambda n:n&0xffffffff
short=lambda n:((n&65535)^32768)-32768
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
public=lambda m:{a:b for a,b in m.items()if not STACK-4096<=a<STACK+1024}

@dataclass(frozen=True)
class Case:
    seed:int=0;route:int=0;identity:int=0x87;kind:int=4;category:int=1
    duration:int=-1;channel:int=0xABCDEF80;context:int=0x87654321;outcome:int=1
    mutation:int=0;phase:int=0;source_null:int=0;alias:int=0;out_alias:int=0

def source_pointer(c):return A if c.alias else S
def output_pointer(c):return A if c.out_alias else O

def cases():
    durations=(-1,0,1,1000,32767,-32768,-2,0x1234FFFF)
    for seed,outcome in itertools.product(range(256),(0,1)):
        yield Case(seed=seed,identity=seed,kind=99 if seed%11==0 else seed%20,category=seed%4,
                   duration=durations[seed%8],channel=0xABCDEF00|seed,context=0x80000000^(seed*0x10203),
                   outcome=outcome,mutation=seed%32,phase=8*(seed&1),source_null=int(seed%7==0),
                   alias=int(seed%9==0),out_alias=int(seed%5==0))
    for identity,kind,category,duration,outcome,mutation in itertools.product((0,0x53,0xA5),(4,99),(0,1,2,255),(-1,0,32767,-32768),(0,1),(0,31)):
        yield Case(seed=197,identity=identity,kind=kind,category=category,duration=duration,
                   outcome=outcome,mutation=mutation,phase=8)
    for seed,outcome,mutation in itertools.product(range(8),(0,1),(0,31)):
        yield Case(seed=seed,route=1,outcome=outcome,mutation=mutation)

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-4096,1024)}
    for at,n in((A,512),(S,32),(ALT,512),(O,256),(MARK,4),(TABLE,320)):
        assert at+n<=STACK-4096 or at>=STACK+1024,('public/private overlap',at,n,STACK)
        m.update({at+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
    m[A+0x3B]=(c.seed*7)&255;m[ALT+0x3B]=(c.seed^0xA5)&255;m[source_pointer(c)+4]=c.identity
    for i in range(20):m[TABLE+16*i]=c.category
    return m

def masked_record(m,address):return bytes(0 if i in HOLES else m[address+i]for i in range(152))

def initialize(m,address,args):
    duration,_,kind,countdown,group,_,_,_=args
    put(m,address+14,duration,2)
    for off,value in((13,countdown),(16,255),(17,kind),(18,255),(19,group)):m[address+off]=value&255
    for i in range(16):m[address+20+i]=0

class Service:
    def __init__(self,m,c,home):self.m,self.c,self.home=m,c,home;self.calls=[];self.binding=None

    def copy(self,args,perform=True):
        destination,record,size=args
        assert destination==output_pointer(self.c)+40 and size==152
        self.calls.append((COPY,('output+40','payload',size),masked_record(self.m,record)))
        if perform:
            copied=data(self.m,record,size)
            for i,b in enumerate(copied):self.m[destination+i]=b
        return destination

    def invoke(self,target,args):
        m,c=self.m,self.c;ordinal=len(self.calls);normal=list(args);observed=b''
        if target==COPY:return self.copy(args)
        if target==CLASSIFY:
            assert args==(source_pointer(c),);normal[0]='source'
        elif target==BIND:
            self.binding=args[0];assert args[1]==19;normal[0]='binding'
            observed=data(m,args[0],5)+bytes(3)
        elif target==FACTORY:assert len(args)==8
        else:raise AssertionError(hex(target))
        self.calls.append((target,tuple(normal),observed))
        put(m,MARK,u32(0x13579BDF+ordinal*0x10203+target))
        if c.mutation&1 and target==CLASSIFY:m[A+0x3B]^=0x33
        if c.mutation&2 and self.binding is not None:
            put(m,self.binding,ALT);m[self.binding+4]=(c.seed+ordinal*7)&255
            for i in range(5,8):m[self.binding+i]=(0x50+ordinal+i)&255
        if c.mutation&4 and target==BIND:
            for i in range(20):m[TABLE+16*i]=(c.seed+1)%3
        if c.mutation&8 and target==BIND:m[A+0x3B]=(m[A+0x3B]+0x51)&255
        if c.mutation&16 and target==FACTORY:m[A+0x3B]^=0xA7
        if target==CLASSIFY:return c.kind
        if target==FACTORY:
            if c.outcome:initialize(m,output_pointer(c),args)
            return output_pointer(c)if c.outcome else 0
        return 0xE5000000+ordinal

def reference(initial,c):
    m=dict(initial);home=STACK+c.phase;binding,record=home-172,home-156
    service=Service(m,c,home)
    if c.route==1:return m,service.calls,0
    kind=4
    if not c.source_null and m[source_pointer(c)+4]not in(0x53,0xA5):kind=service.invoke(CLASSIFY,(source_pointer(c),))
    if kind==99:return m,service.calls,0
    category=m[TABLE+16*kind]
    if category==2:return m,service.calls,0
    m[record+148]=int(category==1)
    put(m,binding,A);m[binding+4]=m[A+0x3B];service.invoke(BIND,(binding,19))
    duration=short(c.duration);chosen,countdown=(300,0)if duration==-1 else(duration,1)
    put(m,record,A);m[record+4]=m[A+0x3B]
    for i in range(8,148):m[record+i]=0
    args=tuple(map(u32,(chosen,-1,19,countdown,15,152,c.channel&255,c.context)))
    created=service.invoke(FACTORY,args)
    if created:service.invoke(COPY,(created+40,record,152))
    return m,service.calls,created

def exchange(memory,home):
    m=dict(memory)
    for i in range(8):m[home-172+i],m[home-164+i]=memory[home-164+i],memory[home-172+i]
    return m

@lru_cache(maxsize=1)
def copy_code():
    rom=(recovery.FROZEN/'conker/conker.us.bin').read_bytes();truth=rom[0x22EC0:0x22EEC]
    elf=(recovery.FROZEN/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,COPY,44)
    assert elf[at:at+44]==truth
    return dict(zip(range(COPY,COPY+44,4),struct.unpack('>11I',truth)))

class Oracle(FactoryOracle):
    def __init__(self,words,initial,c):
        arguments=(0 if c.route==1 else A,0 if c.source_null else source_pointer(c),u32(c.duration),u32(c.channel),u32(c.context))
        super().__init__(words,initial,c,entry=ENTRY,s={},arguments=arguments,connected=dict(copy_code()))
        self.service=Service(self.memory,c,self.target_home);self.saved=tuple(self.r[16:24]);self.saved_fp=tuple(self.f[20:])
    def record_call(self,t):
        assert t in COUNTS,hex(t)
        args=tuple(self.arguments(COUNTS[t]));self.pending=t,args
        if t==COPY:self.service.copy(args,False)
    def hook(self,t):
        target,args=self.pending;assert t==target and t!=COPY
        answer=self.service.invoke(t,args)
        for i in range(max(4,COUNTS[t])):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=u32(answer)

def verify(words,c,remap=False):
    initial=fixture(c);expected,calls,answer=reference(initial,c)
    if remap:initial=exchange(initial,STACK+c.phase)
    m=Oracle(words,initial,c).run()
    assert public(m.memory)==public(expected),('public',asdict(c))
    assert m.service.calls==calls,('calls',asdict(c),next(((i,a,b)for i,(a,b)in enumerate(zip(m.service.calls,calls))if a!=b),None))
    assert m.r[2]==answer and tuple(m.r[16:24])==m.saved and tuple(m.f[20:])==m.saved_fp,('return/saved',c)
    return m

def main(retail,raw,derived):
    programs_=(retail,raw,derived);seen=[set(),set(),set()];copy_seen=[set(),set(),set()];count=0
    target=set(range(ENTRY,ENTRY+460,4));copy_range=set(range(COPY,COPY+44,4))
    for c in cases():
        a,b,d=verify(programs_[0],c),verify(programs_[1],c,True),verify(programs_[2],c)
        assert a.memory==exchange(b.memory,STACK+c.phase)==d.memory,('canonical RAM',c)
        for i,m in enumerate((a,b,d)):seen[i].update(m.visits&target);copy_seen[i].update(m.visits&copy_range)
        count+=1
    assert all(len(s)==114 for s in seen)and all(len(s)==11 for s in copy_seen)
    report=dict(cases_per_stream=count,target_coverage=[len(s)for s in seen],actual_memcpy_words=[len(s)for s in copy_seen],
                complete_canonical_RAM=True,return_and_all_arguments=True,payload_bytes=152,defined_payload_bytes=146,
                native_padding_uncredited_bytes=6,unreachable_word_preserved=38,c_match_credit=0)
    (p/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
