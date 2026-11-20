"""Finite valid lists, ordinary disjoint objects and o32 helper contracts."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_list_unlink_1517e134_match as s
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK,put,read

HEAD,FREE,NODES,ACTOR,COUNT=0x800DDD64,0x10004074,0x30000,0x40000,0x800DC9F0
TABLES=(0x80089F9C,0x80089FE4)
@dataclass(frozen=True)
class Case:
    length:int; index:int; mode:int; context:int; phase:int
    @property
    def target(self):return NODES+self.index*64
    @property
    def argument(self):return(0,self.target,NODES,ACTOR)[self.context]

def cases():
    for n in range(13):
        for index,mode,context,phase in itertools.product(range(n+1),range(3),range(4),(0,8)):
            yield Case(n,index,mode,context,phase)

def fixture(c):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-512,256)}
    for base,size in((NODES,14*64),(ACTOR,0x180),(HEAD,4),(COUNT,4),(TABLES[0],256*4),(TABLES[1],256*4)):
        memory.update({base+i:(i*19+0xB7)&255 for i in range(size)})
    for i in range(14):put(memory,NODES+i*64+36,NODES+(i+1)*64 if i+1<c.length else 0)
    put(memory,HEAD,NODES if c.length else 0);put(memory,COUNT,0xFFFFFFFF)
    put(memory,ACTOR+0x154,c.target);put(memory,ACTOR+0x168,7,1)
    for kind,table in enumerate(TABLES):
        for i in range(256):put(memory,table+i*4,0x15001000+kind*0x1000+i*4)
    return memory

def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+256}
def observation(m):return(read(m,HEAD),tuple(read(m,NODES+i*64+36)for i in range(14)),read(m,COUNT),read(m,ACTOR+0x168,1))
def effect(m,c):
    if c.mode==1:put(m,HEAD,NODES+13*64);put(m,c.target+36,0)
    if c.mode==2:
        put(m,HEAD,0);put(m,c.target+36,NODES+13*64);put(m,COUNT,0x12345678);put(m,ACTOR+0x168,255,1)

def reference(initial,c,caller=None):
    m=dict(initial);events=[]
    def unlink():
        head=read(m,HEAD);found=False
        if head==c.target:put(m,HEAD,read(m,c.target+36));found=True
        else:
            node=head
            while node and read(m,node+36)!=c.target:node=read(m,node+36)
            if node:put(m,node+36,read(m,c.target+36));found=True
        if found:events.append((FREE,(c.target,),observation(m)));effect(m,c)
    if caller is None:unlink()
    else:
        if read(m,ACTOR+0x154):unlink()
        put(m,COUNT,(read(m,COUNT)-1)&0xFFFFFFFF)
        callback=read(m,TABLES[caller]+read(m,ACTOR+0x168,1)*4)
        events.append((callback,(ACTOR,),observation(m)))
    return public(m),events

class UnlinkOracle(TimingOracle):
    def __init__(self,words,memory,c,entry=s.ENTRY,connected=None,caller=False):
        self.case=c;self.connected_caller=caller;self.boundaries=[]
        super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(ACTOR,)if caller else(c.target,c.argument),connected=connected)
    def record_call(self,target):
        if target==s.ENTRY:
            assert self.connected_caller and tuple(self.arguments(2))==(self.case.target,ACTOR)
            return
        args=tuple(self.arguments(1));self.boundaries.append((target,args,observation(self.memory)))
        self.calls.append((target,args))
    def hook(self,target):
        if target==FREE:
            assert self.calls[-1][1]==(self.case.target,)
            effect(self.memory,self.case)
        else:
            assert self.connected_caller and self.calls[-1][1]==(ACTOR,)
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]

def run(raw,normal,retail):
    seen=[set(),set(),set()];count=0;different_homes=0
    for c in cases():
        initial=fixture(c);wanted,events=reference(initial,c);models=[]
        for side,words in enumerate((raw,normal,retail)):
            model=UnlinkOracle(words,initial,c).run()
            assert public(model.memory)==wanted,(c,side,'public')
            assert model.boundaries==events,(c,side,'call boundary')
            models.append(model);seen[side].update(model.visits)
        assert models[1].memory==models[2].memory,(c,'normalized private')
        differences={a for a in initial if models[0].memory[a]!=models[2].memory[a]}
        dead={STACK+c.phase+4+i for i in range(4)}
        assert differences<=dead,(c,differences)
        assert read(models[0].memory,STACK+c.phase+4)==c.argument
        different_homes+=bool(differences);count+=1
    return dict(cases=count,visited_words=[len(v)for v in seen],normalized_entire_memory_equal=True,
        raw_only_unobserved_incoming_A1_home_differs=different_homes,helper_observes_unlink_before_free=True,
        saved_GPR_FPR_SP_RA_restored=True,arbitrary_null_target_or_fault_parity=False)

def callers(raw,normal,retail):
    rom=(s.ROOT/'conker/conker.us.bin').read_bytes();count=0
    for kind,(entry,offset)in enumerate(((0x151411E4,0x16E694),(0x15141250,0x16E700))):
        body=struct.unpack_from('>27I',rom,offset)
        for c in cases():
            if c.context:continue
            for attached in(0,1):
                initial=fixture(c)
                if not attached:put(initial,ACTOR+0x154,0)
                wanted,events=reference(initial,c,kind);models=[]
                for words in(raw,normal,retail):
                    connected={s.ENTRY+4*i:w for i,w in enumerate(words)}
                    model=UnlinkOracle(body,initial,c,entry,connected,True).run()
                    assert public(model.memory)==wanted,(kind,c,attached,'public')
                    assert model.boundaries==events,(kind,c,attached,'events')
                    models.append(model)
                assert models[1].memory==models[2].memory
                dead={STACK+c.phase-24+4+i for i in range(4)}
                assert{a for a in initial if models[0].memory[a]!=models[2].memory[a]}<=dead
                count+=1
    return dict(cases=count,original_callers=2,two_volatile_attachment_reads_preserved=True,
        post_free_counter_and_subtype_reloads=True,callback_actor_and_abi_preserved=True)
