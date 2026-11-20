"""Private behavioral screen; a pass is not a byte-match or fault-prefix claim."""
from dataclasses import dataclass
from pathlib import Path
import json,struct
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,signed

ENTRY,POINT,DEPTH,DRAW=0x1517E28C,0x1517EAAC,0x1517EC1C,0x1517E4A8
HEAD,TOUCHED,GATE,INTENSITY=0x800DDD64,0x800DDD60,0x800DCDD0,0x800DD2D0
CONTEXT,POINTS,TABLES=0x800B0DF0,0x8008CFFC,0x8008D004
NODES,COMMANDS,VIEW,POSITION=0x30000,0x50000,0x60000,0x70000

@dataclass(frozen=True)
class Case:
    seed:int
    mode:int
    phase:int

def cases():
    for i in range(256):
        for mode in range(4):yield Case(i,mode,8*(i&1))

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,256)}
    for base,size in ((NODES-16,4*0x40+32),(COMMANDS-16,256),(VIEW-16,64),(POSITION-16,64)):
        m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(size)})
    for base,size in ((HEAD-4,16),(TOUCHED-4,12),(GATE-4,12),(INTENSITY-4,12),(CONTEXT-4,12),(POINTS-4,32)):
        for i in range(size):m[base+i]=0xA5
    put(m,HEAD,0 if c.seed==0 else NODES);put(m,TOUCHED,0xA5,1)
    put(m,GATE,int((c.seed+c.mode)%4!=0),1);put(m,INTENSITY,c.seed,1)
    put(m,CONTEXT,VIEW);put(m,VIEW+16,1,1);put(m,POINTS,0);put(m,POINTS+4,POSITION)
    for i in range(3):put(m,POSITION+4*i,bits((i-1)*1.25+c.seed*0.125))
    for i,pair in enumerate(((0,1),(7,3),(1,30))):
        put(m,TABLES+4*i,pair[0]<<8|pair[1],2);put(m,TABLES+4*i+2,0,2)
    for i in range(4):
        node=NODES+i*0x40
        put(m,node+0x24,node+0x40 if i<3 else 0)
        put(m,node+0x2A,0xFFFC if (c.seed+i)&1 else c.seed*257,2)
        put(m,node+0x2C,(0,29,30,65535)[(c.seed//4+i)%4],2)
        put(m,node+0x2E,(c.seed+i*53)&255,1);put(m,node+0x2F,(c.seed+i)&1,1)
        put(m,node+0x30,(0,1,128,255)[(c.seed+i+c.mode)%4],1)
    return m

def result(c,target,ordinal):
    return (1,0,2,0xFFFFFFFF)[(c.seed+c.mode+ordinal+(target==POINT))%4]

def effect(m,c,target,args,ordinal):
    if target==DRAW:
        commands,node,group,count,falloff,strength,intensity=args
        put(m,commands,0xC0000000|group<<16|count<<8|falloff);put(m,commands+4,strength)
        put(m,node+0x28,(read(m,node+0x28,2)+count)&65535,2);put(m,TOUCHED,1,1)
        if intensity:put(m,intensity,(c.seed+ordinal*31)&255,1)
        if c.mode==3:put(m,node+0x24,0)
        return (commands+8)&0xFFFFFFFF
    node=args[3]-12 if target==POINT else args[0]
    put(m,node+12,bits(c.seed*0.5+ordinal));put(m,node+16,bits(-c.mode*1.25))
    if target==DEPTH:
        # Some providers intentionally leave the caller's previous word intact.
        if (c.seed+ordinal)%3:put(m,args[1],(4000,1,0,0xFFFFFFFF)[(c.seed//4+ordinal)%4])
        put(m,node+0x2C,(read(m,node+0x2C,2)+(c.mode&1)*31)&65535,2)
    if c.mode==1:put(m,node+0x2E,read(m,node+0x2E,1)^3,1)
    if c.mode==2:
        put(m,HEAD,NODES+3*0x40);put(m,GATE,int(ordinal&1),1)
        link=read(m,node+0x24)
        if link:put(m,node+0x24,read(m,link+0x24))
        put(m,node+0x2A,0xFFFC if ordinal&1 else 0,2)
    return result(c,target,ordinal)

def public(m):return{a:v for a,v in m.items()if not STACK-512<=a<STACK+256}

def reference(initial,c):
    m=dict(initial);calls=[];node=read(m,HEAD);commands=COMMANDS
    sp=STACK+c.phase-120
    # These private words are observed by the original guest even before a write.
    sampled=read(m,sp+0x6C)
    put(m,TOUCHED,0,1)
    while node:
        if read(m,node+0x30,1):
            flags=read(m,node+0x2E,1);skip=False
            if flags&1:
                if not read(m,GATE,1):skip=True
                else:
                    position=read(m,POINTS+read(m,read(m,CONTEXT)+16,1)*4)
                    args=tuple(read(m,position+i*4)for i in range(3))+(node+12,node+16)
                    calls.append((POINT,args));answer=effect(m,c,POINT,args,len(calls))
                    skip=answer!=1;strength=255 if read(m,node+0x2A,2)==0xFFFC else 0xFFFFFFFF
                    flags=read(m,node+0x2E,1)
            else:
                args=(node,sp+0x6C);calls.append((DEPTH,args));answer=effect(m,c,DEPTH,args,len(calls))
                sampled=read(m,sp+0x6C);skip=answer!=1
                difference=(read(m,node+0x2C,2)-sampled)&0xFFFFFFFF
                strength=256 if signed(difference)<30 else 0xFFFFFFFF
                flags=read(m,node+0x2E,1)
            intensity=INTENSITY if flags&2 else 0
            if not skip:
                index=read(m,node+0x2F,1)
                args=(commands,node,read(m,TABLES+index,1),read(m,TABLES+4+index,1),read(m,TABLES+8+index,1),strength,intensity)
                calls.append((DRAW,args));commands=effect(m,c,DRAW,args,len(calls))
            elif intensity:put(m,intensity,0,1)
        node=read(m,node+0x24)
    return m,calls,commands

class ListOracle(TimingOracle):
    def __init__(self,words,memory,c):
        self.case=c
        super().__init__(words,memory,phase=c.phase,entry=ENTRY,arguments=(COMMANDS,0x87654321))
    def record_call(self,target):
        if target==POINT:args=(self.f[12],self.f[14],self.r[6],self.r[7],read(self.memory,self.r[29]+16))
        else:
            assert target in (DEPTH,DRAW),hex(target)
            args=tuple(self.arguments(2 if target==DEPTH else 7))
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        answer=effect(self.memory,self.case,target,self.calls[-1][1],len(self.calls))
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=answer

def run(candidate,retail,selected=None):
    seen=[set(),set()];count=0;private=0;first_difference=None;visited_calls=set()
    for c in selected or cases():
        initial=fixture(c);want,calls,value=reference(initial,c);models=[]
        for side,words in enumerate((candidate,retail)):
            model=ListOracle(words,initial,c).run()
            assert model.calls==calls,(c,side,'helper calls',model.calls,calls)
            assert model.r[2]==value,(c,side,'return')
            assert public(model.memory)==public(want),(c,side,'public memory')
            seen[side].update(model.visits);visited_calls.update(t for t,a in model.calls);models.append(model)
        same=models[0].memory==models[1].memory
        private+=same
        if not same and first_difference is None:
            first_difference=dict(case=c.__dict__,addresses=[hex(a)for a in initial if models[0].memory[a]!=models[1].memory[a]][:32])
        count+=1
    return dict(cases=count,visited_words=[len(v)for v in seen],public_memory_and_helper_calls_equal=True,
        complete_private_equal_cases=private,first_private_difference=first_difference,
        helper_targets=[hex(t)for t in sorted(visited_calls)],fault_prefix_or_hardware_parity=False,
        candidate_reachable_word_indices=sorted((pc-ENTRY)//4 for pc in seen[0]),
        retail_unreachable_word_indices=[i for i in range(len(retail))if ENTRY+4*i not in seen[1]])
