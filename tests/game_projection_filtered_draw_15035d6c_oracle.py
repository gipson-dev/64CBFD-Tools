"""Finite independent command reference; public aliases are guest-only cases."""
from pathlib import Path
import sys
from tools.experiments import game_projection_filtered_draw_15035d6c_recovery as source
ROOT=source.ROOT
from dataclasses import dataclass,replace
import json,struct
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK,put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
OUT=source.OUT;ENTRY=0x15035D6C;BASE=0x800C3F08;COUNT=0x800C3F00
CURSOR,DESC,LISTS,BANK,TARGETS=0x50000,0x60000,0x70000,0x80000,0x90000
GFX_WORDS=4096;RECORDS=255

@dataclass(frozen=True)
class Case:
    seed:int;count:int;lists:int;mask:int;pattern:int;alpha:int;red:int;green:int;blue:int;phase:int=0;alias:int=0

def cases(native=False):
    sizes=(0,1,2,3,7,8,9,31,32,33,127,255);colors=(0,1,255,256,0xffffffff,0x80000000,0x12345678)
    for i in range(512):
        yield Case(i,(i//4)%5,sizes[(i//5)%12],(0,1,255,0xaa)[i%4],(i//12)%5,
            (0,1,127,254,255)[i%5],colors[i%7],colors[(i+2)%7],colors[(i+4)%7],8*(i&1))
    for count in(16,31,127,255):
        for phase in(0,8):yield Case(600+count,count,0,0,0,255,0xffffffff,0x80000000,0x12345678,phase)
    if native:return
    for i in range(72):
        yield Case(1000+i,1+i%4,(0,1,8,33)[i%4],(0,255)[i%2],0,255,255,127,63,8*(i&1),1+i%6)

def cursor(c):return(CURSOR,COUNT-4,COUNT-12,BASE+8,DESC+16,DESC-8,LISTS)[c.alias]

def fixture(c):
    m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-512,512)}
    regions=((CURSOR,GFX_WORDS*4),(DESC-16,GFX_WORDS*4+32),(LISTS,GFX_WORDS*4),
             (BASE-32,GFX_WORDS*4+32),(BANK,RECORDS*64),(TARGETS,256*8))
    for address,size in regions:
        for i in range(size):m.setdefault(address+i,0xa5)
    for i in range(GFX_WORDS):put(m,CURSOR+i*4,0xa5a50000^c.seed^i)
    m[COUNT]=c.count;m[DESC]=c.seed&255;m[DESC+3]=c.alpha;m[DESC+6]=(c.seed*3)&255
    m[DESC+19]=c.mask;m[DESC+20]=c.lists;put(m,DESC+36,LISTS)
    for i in range(256):put(m,LISTS+i*4,TARGETS+i*8)
    for i in range(RECORDS):
        row=BASE+i*12;put(m,row,BANK+i*64);m[row+4]=(c.seed*13+i*19)&255
        for j in range(5,9):m[row+j]=(c.seed+i+j)&255
        m[row+9]=m[DESC];m[row+10]=m[DESC+6];m[row+11]=1
        if c.pattern==1:m[row+11]=0
        elif c.pattern==2:m[row+9]^=1
        elif c.pattern==3:m[row+10]^=1
        elif c.pattern==4:
            if i%4==1:m[row+11]=255
            elif i%4==2:m[row+9]^=1
            elif i%4==3:m[row+10]^=1
    return m

def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+1024}

def reference(initial,c):
    m=dict(initial);trace=[];command=cursor(c)
    def store(address,value):put(m,address,value&0xffffffff);trace.append(('W',address,4,value&0xffffffff))
    if m[COUNT]:
        store(command+4,0x200);store(command,0xd9ffffff);command+=8
        limit=m[COUNT];index=0
        if limit:
            while True:
                row=BASE+index*12
                if m[row+11]==1 and m[DESC]==m[row+9]and m[DESC+6]==m[row+10]:
                    alpha=m[row+4]*m[DESC+3]>>8
                    store(command,0xe7000000);store(command+4,0);command+=8
                    store(command,0xdb06000c);store(command+4,read(m,row));command+=8
                    value=((c.red&255)<<24)|((c.green&255)<<16)|((c.blue&255)<<8)|(alpha&255)
                    store(command+4,value);store(command,0xfb000000);command+=8
                    store(command,0xdb060020);store(command+4,0x80082fc0 if alpha<255 else 0x80083140);command+=8
                    count=m[DESC+20];j=0
                    while j<count:
                        if not(m[DESC+19]&(1<<(j&31))):
                            store(command,0xde000000)
                            value=read(m,read(m,DESC+36)+j*4);store(command+4,value);command+=8
                            count=m[DESC+20]
                        j+=1
                    limit=m[COUNT]
                index+=1
                if index>=limit:break
                assert index<256,('reference outer bound',c)
        store(command,0xd9fffdff);store(command+4,0);command+=8
    return m,trace,command

def hashseq(values):
    h=2166136261
    for v in values:h=((h^(v&0xffffffff))*16777619)&0xffffffff
    return h

class Oracle(TimingOracle):
    def __init__(self,words,memory,c):
        self.c=c
        super().__init__(words,memory,phase=c.phase,entry=ENTRY,
            arguments=(cursor(c),DESC,c.red,c.green,c.blue))
    def record_call(self,target):raise AssertionError(('unexpected helper',target))

def run():
    blob,refs=payload(OUT/'qualified-screen/candidate.o','func_15035D6C');raw=bind(blob,refs)
    retail=struct.unpack_from('>159I',(ROOT/'conker/conker.us.bin').read_bytes(),0x6321C)
    seen=[set(),set()];count=aliases=stores=0;missing=[]
    for c in cases():
        initial=fixture(c);want,trace,result=reference(initial,c);models=[]
        for side,words in enumerate((raw,retail)):
            model=Oracle(words,initial,c).run()
            writes=[v for v in model.events if v[0]=='W'and not STACK-512<=v[1]<STACK+1024]
            assert writes==trace,(c,side,'ordered public stores',writes[:8],trace[:8])
            assert public(model.memory)==public(want),(c,side,'public memory')
            assert model.r[2]==result,(c,side,'returned cursor',model.r[2],result)
            models.append(model);seen[side].update(pc for pc in model.visits if ENTRY<=pc<ENTRY+4*len(words))
        assert models[0].memory==models[1].memory,(c,'complete final guest RAM')
        count+=1;aliases+=int(c.alias!=0);stores+=len(trace)
    for side,words in enumerate((raw,retail)):missing.append([i for i in range(len(words))if ENTRY+4*i not in seen[side]])
    r=dict(cases=count,ordered_public_stores=stores,public_alias_cases=aliases,visited_words=[len(x)for x in seen],
        normal_unvisited_words=missing,private_bytes=52,complete_final_memory_equal_cases=count,
        returned_cursor_equal_cases=count,alpha_opaque_branch_unreachable=True,matching_credit=0)
    (OUT/'guest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
