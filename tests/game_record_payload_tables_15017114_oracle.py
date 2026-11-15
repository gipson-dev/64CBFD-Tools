"""Payload pointers/status model with captured counts and exposed loader output."""
from dataclasses import dataclass
import hashlib,itertools,json
from tools.experiments import game_record_payload_tables_15017114_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case as FactoryCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
COUNT,ORIGINAL,PTRS,STATUS,PLAYERS=0x800d2100,0x800d2101,0x800d2104,0x800d2108,0x8008fd8c
PTR_A,PTR_B,FLAG_A,FLAG_B,ARENA_A,ARENA_B,BUFFERS,MARK=0x30000,0x32000,0x34000,0x35000,0x38000,0x44000,0x50000,0x70000
META_A,META_B=ARENA_A+4096,ARENA_B+4096
REGIONS=((PTR_A,1024),(PTR_B,1024),(FLAG_A,256),(FLAG_B,256),(ARENA_A,8192),(ARENA_B,8192),(BUFFERS,2048),(MARK,16),(COUNT,16),(PLAYERS,1))
ALLOC,ZERO,LOAD=0x10003c40,0x100226f0,0x1502b7f0
COUNTS={ALLOC:4,ZERO:2,LOAD:4}
u32=lambda n:n&0xffffffff
s8=lambda n:((n&255)^128)-128
public=lambda m:{p:b for p,b in m.items()if not STACK-1024<=p<STACK+1024}
data=lambda m,p,n:bytes(m[p+i]for i in range(n))

@dataclass(frozen=True)
class Case:
    n:int=6
    original:int=2
    players:int=2
    success:int=1
    write_output:bool=True
    mode:int=0
    alias:int=0
    phase:int=0
    category:int=26
    seed:int=0

def fixture(c):
    assert 0<=c.n<=255 and 0<=c.original<=255
    assert all(base+size<=STACK-1024 or base>=STACK+1024 for base,size in REGIONS),('public region overlaps private stack',hex(STACK))
    m={STACK+i:(i*17+0x51)&255 for i in range(-512,512)}
    for base,size in REGIONS:
        for i in range(size):m[base+i]=(i*29+c.seed*11+0x5a)&255
    for base in(META_A,META_B):
        for j in range(-256,256):
            put(m,base+j*8,0 if j%3==0 else 32+(j%5)*16)
            put(m,base+j*8+4,3 if c.alias==1 else (j*7+0x102)&0xffffffff)
    for p,n,v in((COUNT,1,c.n),(ORIGINAL,1,c.original),(PTRS,4,0xdeadbeef),(STATUS,4,0xa5a5a5a5),(PLAYERS,1,c.players)):
        put(m,p,u32(v)&((1<<(n*8))-1),n)
    return m

def snapshot(m,addresses):return hashlib.sha256(bytes(m[p]for p in addresses)).hexdigest()
def effect(m,c,target,args,ordinal):
    result=0x98760000+ordinal
    if target==ALLOC:
        result=PTR_A if ordinal==1 else COUNT if ordinal==2 and c.alias==1 else FLAG_A if ordinal==2 else BUFFERS+(ordinal-3)*16
        if c.mode&1 and ordinal==1:put(m,COUNT,3,1)
        if c.mode&4 and ordinal>=2:put(m,PTRS,PTR_B if ordinal&1 else PTR_A)
    elif target==ZERO:
        for i in range(args[1]):assert args[0]+i in m;m[args[0]+i]=0
        if c.mode&2:
            if ordinal==2:put(m,PLAYERS,3,1)
            elif ordinal==3:put(m,PLAYERS,2,1)
        if c.mode&4 and ordinal>=3:
            put(m,PTRS,PTR_B if ordinal&1 else PTR_A);put(m,STATUS,FLAG_B if ordinal&1 else FLAG_A)
    else:
        assert target==LOAD and read(m,args[0])==0
        base=META_B if c.seed&1 else META_A
        if c.write_output:put(m,args[0],base)
        if c.mode&8:put(m,COUNT,6,1);put(m,ORIGINAL,1,1)
        if c.alias==1:
            put(m,COUNT,2,1);put(m,ORIGINAL,0,1);put(m,STATUS,COUNT)
            for j in range(-4,4):put(m,base+j*8,32+(j%5)*16);put(m,base+j*8+4,3)
        elif c.alias in(2,3):
            assert c.n==1 and c.original==0
            put(m,base,32);put(m,base+4,2 if c.alias==2 else 8)
            put(m,STATUS,base+3 if c.alias==2 else args[0]+3)
        result=c.success
    put(m,MARK,target);put(m,MARK+4,ordinal)
    return u32(result)

def reference(initial,c):
    m=dict(initial);calls=[];observations=[];ordinals={};addresses=tuple(sorted(public(m)))
    output=STACK+c.phase-8;put(m,output,0)
    def call(target,*args):
        args=tuple(map(u32,args));calls.append((target,args));observations.append(snapshot(m,addresses))
        ordinals[target]=ordinals.get(target,0)+1
        return effect(m,c,target,args,ordinals[target])
    count=read(m,COUNT,1)
    put(m,PTRS,call(ALLOC,count*4,1,0,0));put(m,STATUS,call(ALLOC,count,1,0,0))
    call(ZERO,read(m,PTRS),count*4);call(ZERO,read(m,STATUS),count)
    index=0
    while index<s8(read(m,PLAYERS,1)):
        value=call(ALLOC,16,1,2,0);put(m,read(m,PTRS)+index*4,value)
        call(ZERO,read(m,read(m,PTRS)+index*4),16)
        put(m,read(m,STATUS)+index,2,1);index+=1
    if call(LOAD,output,2,16,c.category):
        index=read(m,ORIGINAL,1);limit=read(m,COUNT,1)
        while index<limit:
            address=read(m,output)+(index-read(m,ORIGINAL,1))*8
            if read(m,address)!=0:
                put(m,read(m,STATUS)+index,read(m,address+4)&255,1)
                address=read(m,output)+(index-read(m,ORIGINAL,1))*8
                put(m,read(m,PTRS)+index*4,u32(read(m,output)+read(m,address)))
                limit=read(m,COUNT,1)
            index+=1
    return m,calls,observations

class Oracle(FactoryOracle):
    def __init__(self,words,m,c,entry=None,connected=None):
        self.payload_case=c;self.payload_observations=[];self.ordinals={};self.addresses=tuple(sorted(public(m)))
        super().__init__(words,m,FactoryCase(phase=c.phase),entry=source.ENTRY if entry is None else entry,connected=connected,arguments=(u32(c.category),))
    def record_call(self,target):
        if target in(source.ENTRY,source.RAW_ENTRY):return
        assert target in COUNTS,hex(target);args=tuple(map(u32,self.arguments(COUNTS[target])))
        if target==LOAD:assert args[0]==self.target_home-8 and read(self.memory,args[0])==0
        self.calls.append((target,args));self.events.append(('CALL',target,args));self.payload_observations.append(snapshot(self.memory,self.addresses))
    def hook(self,target):
        self.ordinals[target]=self.ordinals.get(target,0)+1
        value=effect(self.memory,self.payload_case,target,self.calls[-1][1],self.ordinals[target])
        for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value

def run_case(program,c):
    words,entry=program;initial=fixture(c);want,calls,observations=reference(initial,c)
    m=Oracle(words,initial,c,entry=entry);saved=(m.r[16:24],m.r[29],m.f[20:]);m.run()
    assert(m.r[16:24],m.r[29],m.f[20:])==saved
    assert public(m.memory)==public(want),('memory',c)
    assert m.calls==calls,('calls',c,m.calls,calls)
    assert m.payload_observations==observations,('snapshots',c)
    return m

def corpus():
    for n in range(256):yield Case(n=n,original=n//2,players=0,seed=n&1)
    for mode,phase,success in itertools.product(range(16),(0,8),(0,1)):
        yield Case(mode=mode,phase=phase,success=success,players=3,seed=mode&1)
    for players,original,category in itertools.product((-128,-1,0,1,2,26,127),(0,6,255),(-1,0,0x100,0x7fffffff)):
        yield Case(players=players,original=original,category=category)
    for n,success,write_output in itertools.product((0,6),(0,1),(False,True)):
        yield Case(n=n,original=n,players=0,success=success,write_output=write_output)
    for alias,phase,seed in itertools.product((1,2,3),(0,8),(0,1)):
        yield Case(n=2 if alias==1 else 1,original=0,players=1 if alias==1 else 0,alias=alias,phase=phase,seed=seed)

def main():
    programs=source.programs();seen=set();count=0
    for c in corpus():
        for i,program in enumerate(programs):
            m=run_case(program,c)
            if i==0:seen.update(m.visits)
        count+=1
        if count%128==0:print('payload guest cases',count,flush=True)
    assert len(seen)==121,('unvisited retail words',[hex(source.ENTRY+i*4)for i in range(121)if source.ENTRY+i*4 not in seen])
    controls=[]
    for pc,old,new in((0x2c,0xafa00040,0xafa10040),(0x8c,0x02602825,0x00002825),(0x1a8,0xaf090000,0xaf090004)):
        words,entry=programs[0];changed=words[:];assert changed[pc//4]==old;changed[pc//4]=new
        try:run_case((changed,entry),Case())
        except AssertionError:controls.append(hex(pc))
        else:raise AssertionError(('ineffective control',hex(pc)))
    report=dict(cases=count,streams=2,retail_words_visited=len(seen),all_count_bytes=256,aliases=3,exposed_private_output_alias=True,helper_entry_snapshots=True,saved_gprs_fprs_and_sp=True,effective_controls=controls,uninstalled=True,uncredited=True,full_fault_or_native_claimed=False)
    (source.OUT/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
