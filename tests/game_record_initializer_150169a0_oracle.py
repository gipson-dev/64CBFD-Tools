"""Compare complete private initializer to retail under opaque helper effects."""
from dataclasses import dataclass,replace
import hashlib,itertools,json,math,struct
from tools.experiments import game_record_initializer_150169a0_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case as MachineCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read

LIST,ALT,BYTES,HALVES,MARK=0x30000,0x60000,0x50000,0x51000,0x70000
TABLE,COUNT,ORIGINAL,FLAGS,HALFPTR=0x800D20FC,0x800D2100,0x800D2101,0x800D210C,0x800D2110
PLAYERS,SPLIT,MASK,SCENE,STATE,ACTORS=0x8008FD8C,0x8008FD90,0x800D2340,0x800BE9F0,0x800D1548,0x800CC2D0
RESET,MEASURE,ALLOC,DMA,APPEND,PREPARE,ZERO,SELECT,CACHE,IDENTITY,SUBMIT,FINAL=(
    0x15004F30,0x1502B9B4,0x10003C40,0x10004514,0x1502B8E0,0x15017114,
    0x100226F0,0x150859AC,0x15016850,0x15083DA0,0x1508295C,0x15172CA8)
COUNTS={RESET:0,MEASURE:2,ALLOC:4,DMA:4,APPEND:5,PREPARE:1,ZERO:2,SELECT:2,CACHE:0,IDENTITY:0,SUBMIT:3,FINAL:1}
BANK_CATEGORIES={26,36,43,45,48,51,52,63}
u32=lambda n:n&0xffffffff
signed8=lambda n:((n&255)^128)-128
data=lambda m,p,n:bytes(m[p+i]for i in range(n))
public=lambda m:{p:b for p,b in m.items()if not STACK-2048<=p<STACK+2304 and not source.POOL<=p<source.POOL+336}

@dataclass(frozen=True)
class Case:
    category:int=0
    selected:int=0
    players:int=1
    mask:int=0xffff
    split:int=1
    scene:int=0
    added:int=1
    mode:int=0
    phase:int=0
    seed:int=0

def fixture(c):
    assert all(not(STACK-2048<=p<STACK+2304 or STACK-2048<p+n<=STACK+2304)
               for p,n in((LIST,64*48),(ALT,64*48),(BYTES,256),(HALVES,512),(MARK,32)))
    m={STACK+i:(i*17+0xa5)&255 for i in range(-2048,2304)}
    for p,n in((LIST,64*48),(ALT,64*48),(BYTES,256),(HALVES,512),(MARK,32),(ACTORS,max(26,c.players)*812),(0x1a33f0,0x3f0)):
        m.update({p+i:(i*29+c.seed*11+0x5a)&255 for i in range(n)})
    for p,n,v in((TABLE,4,LIST),(COUNT,1,0xa5),(ORIGINAL,1,0xa6),(FLAGS,4,0xdeadbeef),(HALFPTR,4,0xa5a5a5a5),
                (PLAYERS,1,c.players),(SPLIT,1,c.split),(MASK,2,c.mask),(SCENE,4,c.scene),(STATE,4,0x87654321)):
        put(m,p,v&((1<<(8*n))-1),n)
    for bank,n in((0x1a33f0,5),(0x1a34e0,16)):
        for i in range(n):m[bank+i*48+40]=(i+1 if c.seed&1 and i&1 else 0)
    for i in range(64):
        m[LIST+i*48+40]=0;m[ALT+i*48+40]=0
    for i in range(max(26,c.players)):
        for k,value in enumerate((i*1.25-32769.75,-i*3.5+100.75,65537.75-i)):
            put(m,ACTORS+i*812+20+k*4,struct.unpack('>I',struct.pack('>f',value))[0])
        put(m,ACTORS+i*812+118,0x8000+i*0x321,2)
    return m

def snapshot(m,addresses):
    # Hash all mapped public bytes in address order, including unused bytes.
    return hashlib.sha256(bytes(m[p]for p in addresses)).hexdigest()

def effect(m,c,target,args,ordinal):
    value=0x98760000+ordinal
    if target==MEASURE:value=c.added*48
    elif target==ALLOC:
        value=(LIST,BYTES,HALVES)[ordinal-1]
        if c.mode&16 and ordinal==2:put(m,COUNT,2,1)
    elif target==DMA:
        packet=data(m,args[0],args[2])
        for i,b in enumerate(packet):m[args[1]+i]=b
    elif target==APPEND:
        for i in range(c.added*48):m[args[0]+i]=(i*7+0x31)&255
        for i in range(c.added):m[args[0]+i*48+40]=0
        value=c.added*48
    elif target==PREPARE:
        if c.mode&1:put(m,COUNT,3,1)
        if c.mode&32:put(m,COUNT,0,1)
    elif target==ZERO:
        for i in range(args[1]):m[args[0]+i]=0
    elif target==SELECT:
        value=u32(c.selected)
        if c.mode&2:
            put(m,TABLE,ALT if ordinal&1 else LIST)
            # The recovered code must use provider-updated positions as well.
            put(m,ACTORS+(args[0]&65535)*812+20,0xc1200000)
    elif target==CACHE:
        if c.mode&4:put(m,TABLE,ALT);put(m,COUNT,3,1)
        if c.mode&64:put(m,COUNT,0,1)
    elif target==IDENTITY:
        value=(ordinal*17+3)&255
        if c.mode&8:
            put(m,TABLE,ALT if ordinal&1 else LIST)
            put(m,COUNT,2,1)
    put(m,MARK,target);put(m,MARK+4,ordinal)
    return u32(value)

def reference(initial,c):
    m=dict(initial);calls=[];observations=[];counts={};addresses=tuple(sorted(public(m)))
    def call(target,*args):
        args=tuple(map(u32,args));calls.append((target,args));observations.append(snapshot(m,addresses))
        counts[target]=counts.get(target,0)+1
        return effect(m,c,target,args,counts[target])
    def rec(offset):return read(m,TABLE)+offset
    def byte(offset,field,value):put(m,rec(offset)+field,value&255,1)
    def flag(offset,value):p=rec(offset)+24;put(m,p,read(m,p)|value)
    call(RESET)
    bank,end=(0x1a34e0,0x1a37e0)if c.category in BANK_CATEGORIES else(0x1a33f0,0x1a34e0)
    extra=call(MEASURE,2,14);size=end-bank
    put(m,TABLE,call(ALLOC,extra+size,1,2,0));call(DMA,bank,read(m,TABLE),size,1)
    put(m,COUNT,size//48,1);put(m,ORIGINAL,read(m,COUNT,1),1)
    added=call(APPEND,read(m,TABLE)+read(m,COUNT,1)*48,0,2,14,c.category)
    put(m,COUNT,(read(m,COUNT,1)+added//48)&255,1);call(PREPARE,c.category)
    count=read(m,COUNT,1);put(m,FLAGS,call(ALLOC,count,1,0,0));doubled=count*2
    put(m,HALFPTR,call(ALLOC,doubled,1,0,0));call(ZERO,read(m,FLAGS),count);call(ZERO,read(m,HALFPTR),doubled)
    put(m,STATE,0);slot=offset=0
    while slot<signed8(read(m,PLAYERS,1)):
        if (1<<(slot&31))&read(m,MASK,2):
            selected=call(SELECT,slot,1);byte(offset,2,0)
            if selected==0:byte(offset,4,150 if read(m,SCENE)in(54,58,64)else 0)
            elif selected in(1,2,3,4,11,16,33,34,39,40):
                byte(offset,4,{1:59,2:152,3:117,4:128,11:136,16:150,33:159,34:160,39:178,40:180}[selected])
            elif selected in(8,9,10):
                byte(offset,4,83 if selected==9 else 119);byte(offset,3,{8:30,9:31,10:37}[selected]);byte(offset,16,170 if selected==8 else 168)
                byte(offset,13,(3 if slot>=signed8(read(m,SPLIT,1))else 1)if selected==8 else(2 if selected==9 else 3))
                if selected==9:
                    put(m,rec(offset)+32,0x3f333333);put(m,rec(offset)+36,0x3f333333)
                flag(offset,{8:0x180000,9:1,10:0x100000}[selected])
                if selected==8:byte(offset,14,read(m,rec(offset)+14,1)|128)
            elif 12<=selected<=15:
                byte(offset,4,144);byte(offset,3,1 if slot<signed8(read(m,SPLIT,1))else 12);flag(offset,4);byte(offset,13,13)
            elif 17<=selected<=28:byte(offset,4,156)
            elif 29<=selected<=32:byte(offset,4,157)
            elif selected in(35,36):byte(offset,4,155 if selected==35 else 154);byte(offset,3,21)
            elif selected in(37,38):
                byte(offset,4,176 if selected==37 else 177);put(m,rec(offset)+36,0x3f19999a);put(m,rec(offset)+32,read(m,rec(offset)+36))
            if read(m,SCENE)in(50,51):flag(offset,0x4000000)
            for k in range(3):
                f=struct.unpack('>f',data(m,ACTORS+slot*812+20+k*4,4))[0]
                put(m,rec(offset)+6+k*2,math.trunc(f)&65535,2)
            byte(offset,12,read(m,ACTORS+slot*812+118,2)>>8)
        else:byte(offset,2,1)
        slot+=1;offset+=48
    call(CACHE);slot=offset=0;limit=read(m,COUNT,1)
    while slot<limit:
        if read(m,rec(offset)+40,1)==0:
            identity=call(IDENTITY);byte(offset,40,identity);limit=read(m,COUNT,1)
        slot+=1;offset+=48
    call(SUBMIT,c.category,1,1);call(FINAL,0);call(SUBMIT,c.category,1,0)
    return m,calls,observations

class Oracle(FactoryOracle):
    def __init__(self,words,m,c,entry=None,connected=None):
        self.init_case=c;self.init_observations=[];self.ordinals={};self.init_addresses=tuple(sorted(public(m)))
        super().__init__(words,m,MachineCase(phase=c.phase),entry=source.ENTRY if entry is None else entry,connected=connected,arguments=(u32(c.category),))
    def record_call(self,t):
        if t==source.ENTRY:return
        assert t in COUNTS,hex(t);args=tuple(map(u32,self.arguments(COUNTS[t])))
        self.calls.append((t,args));self.events.append(('CALL',t,args));self.init_observations.append(snapshot(self.memory,self.init_addresses))
    def hook(self,t):
        self.ordinals[t]=self.ordinals.get(t,0)+1;value=effect(self.memory,self.init_case,t,self.calls[-1][1],self.ordinals[t])
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value

def corpus():
    for category in range(256):yield Case(category=category,players=0,added=category%3,seed=category&1)
    for selected,scene in itertools.product((*range(41),41,0x7fffffff,-1),(0,50,51,54,58,64)):
        yield Case(selected=selected,scene=scene,seed=selected&1)
    for mode,phase in itertools.product(range(32),(0,8)):
        yield Case(category=26,selected=(8,9,10,12,35,37)[mode%6],players=4,split=2,mode=mode,phase=phase)
    for players,mask,split in itertools.product((-128,-1,0,1,2,16,26,33),(0,1,0x8000,0xffff),(-1,0,127)):
        yield Case(players=players,mask=mask,split=split,selected=12,added=0)
    for mode,phase in itertools.product((32,64,96),(0,8)):
        yield Case(category=26,players=0,added=0,mode=mode,phase=phase)

def unreachable_proof(words,pool):
    word=lambda pc:words[(pc-source.ENTRY)//4]
    target=lambda pc,w:pc+4+4*(((w&65535)^32768)-32768)
    branches={target(source.ENTRY+i*4,w)for i,w in enumerate(words)if w>>26 in(4,5,6,7,20,21,22,23)}
    table=set(struct.unpack_from('>38I',pool,0))|set(struct.unpack_from('>41I',pool,0xa8))
    dead=(0x15016c34,0x15016e00,0x15016e84)
    for pc in dead:
        branch=word(pc-8)
        assert branch>>16==0x1000 and target(pc-8,branch)!=pc
        assert pc not in branches|table
        assert word(pc)>>26==35
    # The only break is bypassed by an ordinary BNE with V1 still literal48.
    assert word(0x15016a5c)==0x24030030 and word(0x15016a88)==0x14600002
    assert word(0x15016a90)==0x0007000d
    for pc in range(0x15016a60,0x15016a88,4):
        w=word(pc);op=w>>26
        if op==0:assert not(w&63 in(0,33,35,37,42,18)and w>>11&31==3)
        elif op in(9,12,13,15,32,33,35,36,37):assert w>>16&31!=3
    return [hex(p)for p in(0x15016a90,*dead)]

def run_case(program,c):
    words,pool=program;m=fixture(c);want,calls,obs=reference(m,c)
    m.update({source.POOL+i:b for i,b in enumerate(pool)})
    machine=Oracle(words,m,c);saved=(machine.r[16:24],machine.r[29],machine.f[20:])
    machine.run();assert (machine.r[16:24],machine.r[29],machine.f[20:])==saved
    assert public(machine.memory)==public(want),('public memory',c)
    assert machine.calls==calls,('calls',c,machine.calls,calls)
    assert machine.init_observations==obs,('entry snapshots',c)
    assert data(machine.memory,source.POOL,336)==pool
    return machine

def main():
    programs=source.programs();seen=set();count=0
    for c in corpus():
        for i,p in enumerate(programs):
            machine=run_case(p,c)
            if not i:seen.update(machine.visits)
        count+=1
        if count%128==0:print('qualified guest cases',count,flush=True)
    controls=[]
    # Effective public controls: category dispatch, active/disabled marker,
    # and the signed position result. Changes retain supported instructions.
    for at,old,new,c in((0x1c,0x24ceffe6,0x24ceffe5,Case(category=26)),
                         (0x248,0xa1c00002,0xa1c70002,Case()),
                         (0x650,0xa72f0006,0xa72f0008,Case(selected=1))):
        words,pool=programs[0];changed=words[:];assert changed[at//4]==old
        changed[at//4]=new
        try:run_case((changed,pool),c)
        except AssertionError:controls.append(hex(at))
        else:raise AssertionError('Ineffective emitted negative control')
    missing={hex(source.ENTRY+i*4):hex(w)for i,w in enumerate(programs[0][0])if source.ENTRY+i*4 not in seen}
    proved=unreachable_proof(*programs[0]);assert set(missing)==set(proved)
    report=dict(cases=count,streams=2,retail_words_visited=len(seen),retail_words=477,unvisited_words=missing,unreachable_retail_words_proved=proved,public_bytes_and_entry_snapshots=True,saved_gprs_fprs_and_sp=True,opaque_helpers=True,effective_controls=controls,raw_fault_or_native_claimed=False,uncredited=True)
    (source.OUT/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
