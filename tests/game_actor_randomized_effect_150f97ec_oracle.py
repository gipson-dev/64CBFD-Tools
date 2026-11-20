"""Finite independent effect reference with mutable bounded helper contracts."""
from dataclasses import dataclass
from pathlib import Path
import json,random,struct
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK,put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
from tools.experiments import game_actor_randomized_effect_150f97ec_recovery as source
ROOT=source.ROOT;OUT=source.OUT;ENTRY=0x150F97EC
TRANSFORM,REAL,INTEGER,SUBMIT=0x15145EA4,0x150ADA68,0x150ADA20,0x15102B38
ACTOR,BANK,OTHER,INDEX,SRC,SECOND=0x30000,0x50000,0x60000,0x80088B50,0x800A1C48,0x800A1C54
VECS=(0xC2F80000,0xC1000000,0x41E00000,0xC32A0000,0xC1000000,0x41E00000)
fmul=lambda a,b:bits(floating(a)*floating(b));fadd=lambda a,b:bits(floating(a)+floating(b))
@dataclass(frozen=True)
class Case:
    seed:int;enabled:int;selector:int;priority:int;parameter:int;mode:int;phase:int;reals:tuple;integers:tuple
def cases():
    rng=random.Random(0x150F97EC);values=(0,0x80000000,1,0x00800000,bits(0.25),bits(0.5),0x3F7FFFFF)
    for i in range(768):
        yield Case(i,int(i%5!=0),i%256,(i*37)&255,(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF,rng.getrandbits(32))[i%6],
            i%4,(i&1)*8,tuple(rng.choice(values)for _ in range(3)),tuple(rng.getrandbits(32)for _ in range(2)))
def fixture(c):
    m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
    for base,length in((ACTOR,0x32C),(BANK,256*64),(OTHER,256*64),(INDEX,4),(SRC,24)):
        m.update({base+i:0xA5 for i in range(length)})
    put(m,ACTOR+0x1D4,BANK if c.enabled else 0);m[INDEX]=c.selector
    for i,w in enumerate(VECS):put(m,SRC+4*i,w)
    return m
def public(m):return{a:b for a,b in m.items()if not STACK-0x400<=a<STACK+0x200}
def effect(m,c,target,ordinal,counts,position,homes,scale):
    if target==TRANSFORM:
        for i,value in enumerate((c.seed%17-8,(c.seed%13-6)*0.5,c.seed%7-3)):put(m,position+i*4,bits(float(value)))
    elif target in(REAL,INTEGER):
        if c.mode==1 and target==REAL:m[INDEX]=(m[INDEX]+17)&255;put(m,ACTOR+0x1D4,OTHER)
        if c.mode==2 and target==INTEGER:m[INDEX]=255;put(m,ACTOR+0x1D4,0)
        if c.mode==3:
            for i in range(3):put(m,position+i*4,fadd(read(m,position+i*4),bits((i+1)*0.25)))
            put(m,homes[0],SECOND);put(m,homes[1],OTHER)
    elif target==SUBMIT:
        put(m,ACTOR,c.seed^0x12345678)
        if c.mode==3:
            for i in range(2):put(m,scale+i*4,bits(float(i+ordinal)))
            put(m,position,bits(-17.0))
    if target==REAL:return c.reals[counts[REAL]-1]
    if target==INTEGER:return c.integers[counts[INTEGER]-1]
    return(OTHER+ordinal*16)&0xFFFFFFFF
def snapshot(m):return(read(m,ACTOR),read(m,ACTOR+0x1D4),m[INDEX])
def reference(initial,c):
    m=dict(initial);trace=[];counts={t:0 for t in(TRANSFORM,REAL,INTEGER,SUBMIT)}
    point=STACK+c.phase-12;homes=(STACK+c.phase-28,STACK+c.phase-32);scale=STACK+c.phase-24
    def call(target,args):
        counts[target]+=1;ordinal=sum(counts.values())
        arrays=tuple(read(m,scale+4*i)for i in range(2))+tuple(read(m,point+4*i)for i in range(3))if target==SUBMIT else()
        trace.append((target,tuple(args),snapshot(m),arrays));return effect(m,c,target,ordinal,counts,point,homes,scale)
    if read(m,ACTOR+0x1D4):
        call(TRANSFORM,(0xF0010010,0xF0010014,read(m,ACTOR+0x1D4)+m[INDEX]*64,1))
        put(m,scale+4,fadd(fmul(call(REAL,()),bits(1.0)),bits(2.0)))
        put(m,scale,fadd(fmul(call(REAL,()),bits(14.0)),bits(28.0)))
        first=call(INTEGER,());second=call(INTEGER,());angle=fadd(fmul(call(REAL,()),bits(300.0)),bits(400.0))
        call(SUBMIT,(ACTOR,m[INDEX],SRC,SECOND,0xF0010020,first%3+4,second%156+100,angle,0xF0010000,255,0,0xFFFFFFFF,c.priority,c.parameter))
    return m,trace
class Oracle(TimingOracle):
    def __init__(self,words,memory,c):
        self.c=c;self.trace=[];self.boundaries=[];self.provider_counts={t:0 for t in(TRANSFORM,REAL,INTEGER,SUBMIT)}
        self.position=STACK+c.phase-12;self.homes=(STACK+c.phase-28,STACK+c.phase-32);self.scale=STACK+c.phase-24
        super().__init__(words,memory,phase=c.phase,entry=ENTRY,arguments=(ACTOR,c.priority,c.parameter))
    def record_call(self,target):
        assert target in self.provider_counts;self.provider_counts[target]+=1
        n={TRANSFORM:4,REAL:0,INTEGER:0,SUBMIT:14}[target];args=list(self.arguments(n));arrays=()
        if target==TRANSFORM:
            assert tuple(args[:2])==self.homes and read(self.memory,args[0])==SRC and read(self.memory,args[1])==self.position
            args[0:2]=[0xF0010010,0xF0010014]
        if target==SUBMIT:
            assert(args[4],args[8])==(self.scale,self.position);args[4]=0xF0010020;args[8]=0xF0010000
            arrays=tuple(read(self.memory,self.scale+4*i)for i in range(2))+tuple(read(self.memory,self.position+4*i)for i in range(3))
        self.trace.append((target,tuple(args),snapshot(self.memory),arrays));self.calls.append((target,tuple(args)))
        self.boundaries.append(tuple(self.memory[STACK+self.c.phase+i]for i in range(-112,12)))
    def hook(self,target):
        answer=effect(self.memory,self.c,target,len(self.calls),self.provider_counts,self.position,self.homes,self.scale)
        n={TRANSFORM:4,REAL:0,INTEGER:0,SUBMIT:14}[target]
        for i in range(max(4,n)):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xA5000010;self.r[2]=answer
        if target==REAL:self.f[0]=answer
def run(words=None):
    if words is None:
        blob,refs=payload(OUT/'qualified-screen/candidate.o','func_150F97EC');words=bind(blob,refs)
    truth=struct.unpack_from('>89I',(ROOT/'conker/conker.us.bin').read_bytes(),0x126C9C);seen=[set(),set()];count=calls=boundaries=0
    assert tuple(struct.unpack_from('>6I',(ROOT/'conker/conker.us.bin').read_bytes(),0x246708))==VECS
    for c in cases():
        initial=fixture(c);want,trace=reference(initial,c);models=[]
        for side,code in enumerate((words,truth)):
            model=Oracle(code,initial,c).run();assert model.trace==trace,(c,side,'trace',model.trace,trace)
            assert public(model.memory)==public(want),(c,side,'public')
            models.append(model);seen[side].update(pc for pc in model.visits if ENTRY<=pc<ENTRY+4*len(code))
        assert models[0].boundaries==models[1].boundaries,(c,'private call bytes')
        assert models[0].memory==models[1].memory,(c,'whole guest memory')
        count+=1;calls+=len(trace);boundaries+=len(models[0].boundaries)
    report=dict(cases=count,calls=calls,visited_words=[len(x)for x in seen],private_bytes=124,private_boundaries_equal=boundaries,
        complete_final_memory_equal_cases=count,late_global_reload_and_unsigned_modulo=True,bounded_providers=True,matching_credit=0)
    (OUT/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
