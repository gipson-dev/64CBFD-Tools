"""Whole public behavior under bounded o32 providers; not private/frame proof."""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
ROOT=recovery.ROOT
from dataclasses import dataclass
import json,math,struct
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK,put,read
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
OUT=recovery.OUT;ENTRY=0x15035808;ACTORS=0x800CC2D0
COUNT,RECORDS,CURSOR,BASE,CAP,USED,HEAD,BUFFER,WIDE,STATE=(
    0x800C3F00,0x800C3F08,0x800C3E88,0x800C3E8C,0x800C3E7C,0x800C3E7A,
    0x800C3EE0,0x800BE9C0,0x800C35EA,0x800DBFF0)
VIEW,NODES,BANK,CACHE,ATTACH,PRIMARY,OTHER=0x30000,0x100000,0x50000,0x60000,0x70000,0x80000,0x90000
QUERY,DISTANCE,QUEUE,COLOR,MATRIX,CULL,RESOLVE,ALLOC=(
    0x1502DB20,0x150AD9A0,0x150356C8,0x1502D54C,0x15034F30,0x15035714,0x15031070,0x10003C40)
COUNTS={QUERY:1,DISTANCE:3,QUEUE:0,COLOR:2,MATRIX:19,CULL:4,RESOLVE:4,ALLOC:4}
COLORS_TOKEN='COLOR_HOME';PRIMARY_TOKEN='PRIMARY_HOME';SECONDARY_TOKEN='SECONDARY_HOME'
def real(v):return floating(bits(v))
def value(m,a,size=4):return int.from_bytes(bytes(m[a+i]for i in range(size)),'big')
def write(m,a,v,size=4):put(m,a,v&((1<<(8*size))-1),size)
def fp(m,a):return floating(read(m,a))

@dataclass(frozen=True)
class Case:
    seed:int;mode:int;index:int;count:int;gate:int;pattern:int;effect:int;phase:int
    distance_override:int|None=None
    argument_words:tuple|None=None

def cases():
    for i in range(768):
        yield Case(i,i%3,(i//3)%3,(0,1,12,14,15)[(i//9)%5],(i//5)%9,(i//7)%8,(i//11)%8,8*(i&1))
    for effect in range(8):
        for pattern in range(8):
            for opacity in range(4):
                seed=2000+(effect*8+pattern)*4+opacity
                yield Case(seed,(effect+pattern)%3,(effect+opacity)%3,0,0,pattern,effect,8*((pattern+opacity)&1),0)
    for mode in range(3):
        for phase in(0,8):yield Case(4000+mode,mode,0,0,0,0,8,phase,0)
    for gate in range(9):
        for mode in range(3):
            for phase in(0,8):yield Case(5000+gate*12+mode*2+phase//8,mode,1,0,gate,0,0,phase)

def inputs(c):
    if c.argument_words is not None:
        assert len(c.argument_words)==8
        return c.argument_words
    return tuple(bits(v)for v in(13.25,-7.5,31.0,0.0,0.25,100.0,150.0,(0.0,1.0,127.5,255.0)[c.seed%4]))
def wanted_distance(c):
    if c.distance_override is not None:return c.distance_override
    return 1401 if c.gate==6 else(9999 if c.gate==8 else(0,1199,1200,1201,1399,1400)[c.seed%6])
def fixture(c):
    assert NODES+0x300<=STACK-1024 or NODES>=STACK+512
    m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-1024,256)}
    for base,length in((ACTORS,3*0x32c),(VIEW,0x600),(NODES,0x300),(BANK,0x4000),
        (CACHE,0x4000),(ATTACH,0x3000),(PRIMARY,0x1000),(OTHER,0x1000),(RECORDS,255*12)):
        m.update({base+i:0xa5 for i in range(length)})
    actor=ACTORS+c.index*0x32c
    write(m,actor,0 if c.gate==1 else 1);m[actor+4]=59;m[actor+7]=(255,1,127,254)[c.seed%4]
    if c.gate==4:m[actor+7]=0
    m[actor+0x3b]=(7+c.seed)&255;m[actor+0x74]=15 if c.gate==3 else 0
    write(m,actor+0x1d4,0 if c.gate==2 else PRIMARY)
    for off,v in zip((0x14,0x18,0x1c),(17.25,-13.5,0.125)):write(m,actor+off,bits(v))
    for off,v in zip((0x2f8,0x2fc,0x300),(23.75,-1.25,71.875)):write(m,VIEW+off,bits(v))
    write(m,STATE,VIEW);m[COUNT]=c.count;m[BUFFER]=c.seed&1;m[WIDE]=int(c.gate==8)
    write(m,CURSOR,BANK);write(m,BASE,BANK);write(m,CAP,0 if c.gate==5 else 64,2);write(m,USED,0xfffe,2)
    write(m,HEAD,NODES)
    for i in range(3):
        node=NODES+i*0x100;m[node]=m[actor+0x3b];m[node+3]=(255,127,1)[i];m[node+6]=i+3
        if c.pattern==1 and i==0:m[node]^=1
        if c.pattern==2 and i==1:m[node+3]=0
        write(m,node+0x34,PRIMARY+0x400 if c.pattern==5 else 0)
        write(m,node+0x48,ATTACH+i*0x1000 if c.pattern in(4,7)else 0)
        m[ATTACH+i*0x1000+0x3f4]=i+1
        for index in range(2):write(m,node+0x4c+index*4,CACHE+0x2000+i*0x200 if c.pattern==3 else 0)
        write(m,node+0x54,NODES+(i+1)*0x100 if i<2 else 0);write(m,node+0x58,NODES+(i-1)*0x100 if i else 0)
    return m

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}

class Providers:
    def initialize(self,c,m):
        self.c=c;self.memory=dict(m);self.trace=[];self.ordinal=0;self.descriptor=0
        self.color_home=None;self.primary_home=None;self.secondary_home=None;self.allocations=0
    def effect(self,target,args):
        m,c=self.memory,self.c;actor=ACTORS+c.index*0x32c;self.ordinal+=1;ordinal=self.ordinal
        answer=0xa5100000|ordinal
        if target==QUERY:
            answer=1+c.seed%3
            if c.effect==6:
                m[actor+7]=17;write(m,CURSOR,BANK+64);write(m,actor+0x14,bits(-17.25))
            if c.effect==8:m[COUNT]=15
        elif target==DISTANCE:answer=wanted_distance(c)
        elif target==QUEUE:
            if m[COUNT]==15:answer=0
            else:answer=RECORDS+m[COUNT]*12;m[COUNT]=(m[COUNT]+1)&255
        elif target==COLOR:
            self.set_colors(tuple((c.seed*3+i*71)&255 for i in range(3)))
            if c.effect==7:m[COUNT]=15
        elif target==MATRIX:
            m[args[1]+4]=(c.seed*7+ordinal*29)&255
            if args[4]:write(m,args[4],0xbc000000|ordinal)
            if c.effect==1:self.set_colors(tuple((v+11)&255 for v in self.get_colors()))
            if c.effect==5:write(m,actor+0x18,bits(33.5+ordinal))
        elif target==CULL:answer=int(c.gate==7)
        elif target==RESOLVE:
            self.descriptor=args[0];index=(args[0]-NODES)//0x100
            self.set_primary(PRIMARY+index*0x200);self.set_secondary(OTHER+index*0x200)
            answer=int(not(c.pattern==6 and index==1))
            if c.effect==4:write(m,args[0]+0x54,0)
        elif target==ALLOC:
            self.allocations+=1;answer=CACHE+self.allocations*0x400
            if c.effect==2:m[BUFFER]^=1
            if c.effect==3:self.set_primary(OTHER+(self.descriptor-NODES));self.set_secondary(PRIMARY)
            if c.effect==5:
                m[self.descriptor+3]=31;write(m,self.descriptor+0x34,0);write(m,self.descriptor+0x48,0)
        else:raise AssertionError(('unknown provider',target))
        return answer&0xffffffff

class Reference(Providers):
    def __init__(self,m,c):self.initialize(c,m);self.colors=[0,0,0];self.primary=0;self.secondary=0
    def set_colors(self,values):self.colors=list(values)
    def get_colors(self):return tuple(self.colors)
    def set_primary(self,v):self.primary=v
    def set_secondary(self,v):self.secondary=v
    def call(self,target,args=()):
        args=tuple(v&0xffffffff if isinstance(v,int)else v for v in args);self.trace.append((target,args))
        return self.effect(target,args)
    def run(self):
        m,c=self.memory,self.c;actor=ACTORS+c.index*0x32c;params=inputs(c)
        if m[COUNT]==15:return self
        if c.mode==0 and read(m,actor)!=1:return self
        if not read(m,actor+0x1d4)or m[actor+0x74]&15==15:return self
        opacity=m[actor+7]
        if not opacity:return self
        count=self.call(QUERY,(m[actor+4],))
        if (read(m,CURSOR)+(count<<6)-read(m,BASE))&0xffffffff>value(m,CAP,2)<<6:return self
        limit=10000 if m[WIDE]==1 else 1400;view=read(m,STATE)
        coords=tuple(math.trunc(real(fp(m,view+v)-fp(m,actor+a)))for v,a in((0x2f8,0x14),(0x2fc,0x18),(0x300,0x1c)))
        distance=real(float(signed(self.call(DISTANCE,coords))))
        if float(limit)<distance:return self
        factor=256
        if float(limit-200)<distance:factor=math.trunc(real(real(real(float(limit)-distance)*256.0)/float(limit-200)))
        if opacity!=255:factor=factor*opacity>>8
        record=self.call(QUEUE)
        if not record:return self
        write(m,record,read(m,CURSOR));self.call(COLOR,(c.index,COLORS_TOKEN))
        for i,color in enumerate(self.colors):m[record+5+i]=color&255
        m[record+11]=0;m[record+8]=c.index;m[record+9]=m[actor+0x3b]
        self.primary=read(m,actor+0x1d4)
        self.transform(actor,record,count,params,params[-1],0,0)
        m[record+4]=m[record+4]*factor>>8&255
        if self.call(CULL,(c.mode,actor,self.primary,params[1])):
            m[COUNT]=(m[COUNT]-1)&255;return self
        write(m,CURSOR,read(m,CURSOR)+(count<<6));write(m,USED,value(m,USED,2)+count,2)
        descriptor=read(m,HEAD);iterations=0
        while descriptor:
            iterations+=1;assert iterations<=8
            next_descriptor=read(m,descriptor+0x54)
            if m[descriptor]==m[actor+0x3b]and m[descriptor+3]:
                record=self.call(QUEUE)
                if not record:return self
                for i,color in enumerate(self.colors):m[record+5+i]=color&255
                m[record+11]=1;m[record+8]=c.index;m[record+9]=m[actor+0x3b];m[record+10]=m[descriptor+6]
                if self.call(RESOLVE,(descriptor,actor,PRIMARY_TOKEN,SECONDARY_TOKEN)):
                    alpha=math.trunc(floating(params[-1]));attachment=read(m,descriptor+0x48)
                    count=m[attachment+0x3f4]if attachment else 1
                    if not read(m,descriptor+0x4c+m[BUFFER]*4):
                        allocation=self.call(ALLOC,(count<<6,1,2,0))
                        write(m,descriptor+0x4c+m[BUFFER]*4,allocation)
                    write(m,record,read(m,descriptor+0x4c+m[BUFFER]*4))
                    alpha=alpha*m[descriptor+3]>>8
                    fixed=int(bool(read(m,descriptor+0x34)or read(m,descriptor+0x48)))
                    self.transform(0,record,count,params,bits(float(alpha)),fixed,1)
                    m[record+4]=m[record+4]*factor>>8&255
            descriptor=next_descriptor
        return self
    def transform(self,first,record,count,params,alpha,input_fixed,output_fixed):
        actor=ACTORS+self.c.index*0x32c
        args=(first,record,self.c.mode,self.primary,read(self.memory,record),count,*params[:5],
            *(read(self.memory,actor+off)for off in(0x14,0x18,0x1c)),params[5],params[6],alpha,input_fixed,output_fixed)
        assert len(args)==19;self.call(MATRIX,args)

class Oracle(TimingOracle,Providers):
    def __init__(self,words,m,c):
        Providers.initialize(self,c,m)
        TimingOracle.__init__(self,words,m,phase=c.phase,entry=ENTRY,arguments=(c.mode,c.index,*inputs(c)))
        self.boundaries=[]
    def set_colors(self,values):
        assert self.color_home is not None
        for i,v in enumerate(values):write(self.memory,self.color_home+4*i,v)
    def get_colors(self):return tuple(read(self.memory,self.color_home+4*i)for i in range(3))
    def set_primary(self,v):
        assert self.primary_home is not None;write(self.memory,self.primary_home,v)
    def set_secondary(self,v):
        assert self.secondary_home is not None;write(self.memory,self.secondary_home,v)
    def record_call(self,target):
        assert target in COUNTS,hex(target);args=list(self.arguments(COUNTS[target]));self.actual_args=tuple(args)
        self.boundaries.append((target,tuple(self.r[16:24]),read(self.memory,HEAD),tuple(self.memory[NODES+i*0x100]for i in range(3))))
        if target==COLOR:
            self.color_home=args[1];args[1]=COLORS_TOKEN
        if target==RESOLVE:
            self.primary_home,self.secondary_home=args[2:4];args[2:4]=[PRIMARY_TOKEN,SECONDARY_TOKEN]
        self.trace.append((target,tuple(args)));self.calls.append((target,tuple(args)))
    def hook(self,target):
        answer=self.effect(target,self.trace[-1][1]);n=COUNTS[target]
        for i in range(max(4,n)):write(self.memory,self.r[29]+i*4,0xb5000000+self.ordinal*32+i)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000010;self.r[2]=answer

def bind(raw,refs):
    anchors={n:ALLOC if n=='allocate_memory'else 0x80097d74 if n=='.rodata'else int(n.split('_')[1],16)for rs in refs.values()for _,n in rs}
    return tuple(bound_blob(raw,refs,anchors))

def run():
    raw,refs=payload(recovery.WHERE/'candidate.o','func_15035808');words=bind(raw,refs)
    retail=struct.unpack_from('>345I',(ROOT/'conker/conker.us.bin').read_bytes(),0x62cb8)
    seen=[set(),set()];count=calls=allocations=0;effects=set();gates=set()
    for c in cases():
        m=fixture(c);reference=Reference(m,c).run()
        for side,stream in enumerate((words,retail)):
            model=Oracle(stream,m,c).run()
            if model.trace!=reference.trace:
                at=next((i for i,(a,b)in enumerate(zip(model.trace,reference.trace))if a!=b),min(len(model.trace),len(reference.trace)))
                (OUT/'guest-mismatch.txt').write_text(repr((c,side,at,model.trace[max(0,at-1):at+2],reference.trace[max(0,at-1):at+2])))
                raise AssertionError(('provider trace',c,side,at))
            if public(model.memory)!=public(reference.memory):
                wanted=public(reference.memory);actual=public(model.memory)
                differences=[(hex(a),actual.get(a),wanted.get(a))for a in sorted(actual.keys()|wanted.keys())if actual.get(a)!=wanted.get(a)]
                (OUT/'guest-mismatch.txt').write_text(repr((c,side,differences[:30])))
                raise AssertionError(('public memory',c,side,len(differences)))
            seen[side].update(pc for pc in model.visits if ENTRY<=pc<ENTRY+4*len(stream))
        count+=1;calls+=len(reference.trace);allocations+=reference.allocations;effects.add(c.effect);gates.add(c.gate)
    report=dict(cases=count,logical_calls=calls,allocations=allocations,provider_modes=sorted(effects),early_gate_modes=sorted(gates),
        visited_words=[len(v)for v in seen],full_public_memory=True,all_19_matrix_arguments=True,
        unvisited_words=[[i for i in range(len(stream))if ENTRY+4*i not in seen[side]]for side,stream in enumerate((words,retail))],
        retained_color_and_resolver_homes=True,allocator_frame_index_changes=True,preloaded_next_link_changes=True,
        private_pointer_arguments_canonicalized=True,exact_private_frame_claim=False,FCSR_emulation=False,matching_credit=0)
    (OUT/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
