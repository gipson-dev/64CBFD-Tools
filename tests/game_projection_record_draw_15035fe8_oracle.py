"""Independent finite record-loop reference and mutable bounded draw provider."""
from pathlib import Path
import sys
from tools.experiments import game_projection_record_draw_15035fe8_recovery as source
ROOT=source.ROOT
from dataclasses import dataclass
import json,struct
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK,put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
OUT=source.OUT;ENTRY=0x15035FE8;DRAW=0x1502CCFC;BASE=0x800C3F08;COUNT=BASE-8
CURSOR,OTHER,ARENA,OTHER_ARENA=0x50000,0x60000,0x70000,0x74000
PACKET=0xF0010000;GFX_WORDS=1024

@dataclass(frozen=True)
class Case:
    seed:int;count:int;view:int;mode:int;pattern:int;phase:int;alias:int=0

def cases(native=False):
    views=(0,3,0xFFFFFFFF,0x7FFFFFFF,0x80000000,0x12345678)
    for i in range(1024):yield Case(i,(i//4)%16,views[i%6],i%4,(i//64)%4,8*(i&1))
    if native:return
    for i in range(48):yield Case(1100+i,1+i%15,views[i%6],i%4,i%4,8*(i&1),1+i%3)
    for count in(16,31,127,255):
        for phase in(0,8):yield Case(1200+count,count,0x80000000,0,1,phase)

def cursor(c):return(CURSOR,COUNT-4,COUNT-12,BASE+8)[c.alias]

def fixture(c):
    m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-512,128)}
    for base in(CURSOR,OTHER):
        for i in range(GFX_WORDS):put(m,base+4*i,0xA5A50000^c.seed^i)
    for base in(ARENA,OTHER_ARENA):
        for i in range(16*16):put(m,base+4*i,0xB6000000^c.seed^i)
    for i in range(-64,max(15,c.count)*12+32):m.setdefault(BASE+i,0xA5)
    m[COUNT]=c.count
    for i in range(max(15,c.count)):
        row=BASE+i*12;put(m,row,ARENA+(i%16)*64)
        values=((c.seed*13+i*19)&255,(c.seed+i*7)&255,(c.seed*5+i*11)&255,(255-i*17+c.seed)&255,
                (i*31+c.seed)&255,0xA5,0xA5,
                (0,255,(i+c.seed)&1,int((i+c.seed)%5==0))[c.pattern])
        for j,v in enumerate(values):m[row+4+j]=v
    return m

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+256}

def effect(m,c,args,ordinal,packet):
    command=args[0];put(m,command,0xCD000000|ordinal);put(m,command+4,args[1]^args[2])
    if c.mode==1:m[COUNT]=0
    if c.mode==2:
        m[COUNT]=15;i=(c.seed+ordinal*3)%15;row=BASE+i*12
        put(m,row,OTHER_ARENA+i*64);m[row+4]=(m[row+4]+7)&255;m[row+5]^=17
        m[row+8]=(m[row+8]+1)&255;m[row+11]^=255
    if c.mode==3:
        for i in range(4):put(m,packet+i*4,(c.seed^ordinal^0xB7000000)+i)
        return OTHER+ordinal*16
    return command+8*(1+(c.seed+ordinal)%3)

def reference(initial,c,stack_adjust=0):
    m=dict(initial);trace=[];command=cursor(c);packet=STACK+c.phase-20+stack_adjust
    if m[COUNT]:
        for i,(a,b)in enumerate(((0xD9FFFFFF,0x00200004),(0xD9EEFFFF,0),(0xE2001E01,0))):
            put(m,command+i*8,a);put(m,command+i*8+4,b)
        command+=24;limit=m[COUNT];index=0
        while index<limit:
            row=BASE+index*12
            if m[row+11]==0:
                values=tuple(m[row+5+i]for i in range(3))+(255,)
                for i,v in enumerate(values):put(m,packet+4*i,v)
                args=(command,m[row+8],c.view,read(m,row),m[row+4],PACKET,0,1)
                trace.append((args,values,m[COUNT]));command=effect(m,c,args,len(trace),packet);limit=m[COUNT]
            index+=1
    return m,trace,command

def hashseq(values):
    h=2166136261
    for v in values:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
    return h

def public_values(m):
    values=[m[COUNT]]
    for i in range(15):
        row=BASE+i*12;values.append(read(m,row));values.extend(m[row+j]for j in range(4,12))
    for base in(CURSOR,OTHER,ARENA,OTHER_ARENA):
        words=GFX_WORDS if base in(CURSOR,OTHER)else 256
        values.extend(read(m,base+i*4)for i in range(words))
    return values

class Oracle(TimingOracle):
    def __init__(self,words,memory,c):
        self.c=c;self.trace=[];self.boundaries=[];self.packet=STACK+c.phase-20
        super().__init__(words,memory,phase=c.phase,entry=ENTRY,arguments=(cursor(c),c.view))
    def record_call(self,target):
        assert target==DRAW;args=list(self.arguments(8));assert args[5]==self.packet
        args[5]=PACKET;values=tuple(read(self.memory,self.packet+i*4)for i in range(4))
        self.trace.append((tuple(args),values,self.memory[COUNT]));self.calls.append((target,tuple(args)))
        self.boundaries.append(tuple(self.memory[STACK+self.c.phase+i]for i in range(-104,8)))
    def hook(self,target):
        answer=effect(self.memory,self.c,self.trace[-1][0],len(self.trace),self.packet)
        for i in range(8):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xA5000010;self.r[2]=answer

def run():
    blob,refs=payload(OUT/'qualified-screen/candidate.o','func_15035FE8');raw=bind(blob,refs)
    retail=struct.unpack_from('>88I',(ROOT/'conker/conker.us.bin').read_bytes(),0x63498)
    seen=[set(),set()];count=calls=aliases=0
    for c in cases():
        initial=fixture(c);want,trace,result=reference(initial,c);models=[]
        for side,words in enumerate((raw,retail)):
            model=Oracle(words,initial,c).run();assert model.trace==trace,(c,side,'calls',model.trace,trace)
            assert public(model.memory)==public(want),(c,side,'public RAM')
            assert model.r[2]==result,(c,side,'returned cursor',model.r[2],result)
            models.append(model);seen[side].update(pc for pc in model.visits if ENTRY<=pc<ENTRY+4*len(words))
        assert models[0].boundaries==models[1].boundaries,(c,'all112 private call bytes')
        assert models[0].memory==models[1].memory,(c,'complete final guest RAM')
        count+=1;calls+=len(trace);aliases+=int(c.alias!=0)
    r=dict(cases=count,calls=calls,public_alias_cases=aliases,visited_words=[len(x)for x in seen],private_bytes=112,
           private_boundaries_equal=calls,complete_final_memory_equal_cases=count,returned_cursor_equal_cases=count,
           mutable_count_records_packet=True,helpers_are_bounded_providers=True,matching_credit=0)
    (OUT/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
