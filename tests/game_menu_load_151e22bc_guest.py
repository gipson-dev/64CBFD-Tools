"""Bounded differential screen for original and branch-based menu loaders."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_sequence_direction_1501fe68_match import elf_slot_offset
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_classifier_candidates import sections

root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-menu-load-151e22bc-durable'
rom=(root/'conker/conker.us.bin').read_bytes();elf=(root/'conker/build/conker.us.elf').read_bytes()
ENTRY=0x151e22bc;CALLEE=0x151dd9e4;STATUS=0x320000;RECORDS=0x330800
SOURCE=0x800ab690;DEST=0x800e0be0;STATUS_PTR=0x8008fdd4;RECORD_PTR=0x80082bbc;TABLE=0x800ab994
table=elf[elf_slot_offset(elf,TABLE,40):][:40]
assert list(struct.unpack('>10I',table))==[0x151e2384,0x151e2390,0x151e2390,0x151e23e0,0x151e23e0,0x151e23b0,0x151e23e0,0x151e23a4,0x151e23c0,0x151e23c0]
@dataclass(frozen=True)
class Case:
    index:int;value:int;clamp:int;alias:int;phase:int=0
def fixture(c):
    m={STACK+i:(i*17+0xa5)&255 for i in range(-512,512)}
    for start,size in ((STATUS-16,128),(RECORDS-1400,2800),(SOURCE-16,128),(DEST-32,96),(TABLE,40)):
        m.update({start+i:(i*29+0x35)&255 for i in range(size)})
    m.update({TABLE+i:v for i,v in enumerate(table)})
    put(m,STATUS_PTR,STATUS);m[STATUS+0x42]=0;m[SOURCE]=c.index&255
    rec=(DEST+c.alias-1 if c.alias else RECORDS+c.index*10)
    put(m,RECORD_PTR,(rec-c.index*10)&0xffffffff)
    for i in range(10):m[rec+i]=(i*37+11)&255
    m[rec+1]=c.value&255;m[rec+3]=c.clamp&255
    return m,rec
def reference(initial,c,rec):
    m=dict(initial);v=m[rec+3]
    if v>=5:m[rec+3]=4
    v=m[rec+1];v=v if v<128 else v-256
    if v<=0:m[rec+1]=1;v=1
    m[DEST+2]=v&255
    v=m[rec+2];m[DEST+0xb]=0;m[DEST+3]=v
    m[DEST+0x10]=m[rec+3];m[DEST+0x11]=m[rec+4]
    if c.index==0:m[DEST+4]=m[rec+5]
    elif c.index in (1,2):m[DEST+0xd]=m[rec+5];m[DEST+0xe]=m[rec+6]
    elif c.index==5:m[DEST+0x11]=0;m[DEST+0x12]=m[rec+5]
    elif c.index==7:m[DEST+0x12]=m[rec+5]
    elif c.index in (8,9):
        m[DEST+7]=m[rec+5];v=m[rec+6]
        m[DEST+0x11]=1;m[DEST+3]=2;m[DEST+0x13]=v
    m[DEST+0x16]=m[rec+8];m[DEST+6]=m[rec+9]
    return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
class Machine(FactoryOracle):
    def __init__(self,w,m,c):super().__init__(w,m,c,entry=ENTRY,s={},arguments=())
    def record_call(self,t):assert t==CALLEE;self.calls.append(t)
    def hook(self,t):
        assert t==CALLEE
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
        self.r[2]=0x12345678

programs=[(list(struct.unpack_from('>82I',rom,0x20f76c)),table)]
symbols={'D_8008FDD4':STATUS_PTR,'D_800AB690':SOURCE,'D_80082BBC':RECORD_PTR,'D_800E0BE0':DEST,'func_151DD9E4':CALLEE,'.rodata':TABLE,'jtbl_800AB994':TABLE}
for name in ('broken.o','alias-00.o','guarded-private.o'):
    obj=out/name;raw,refs=payload(obj,'func_151E22BC');words=bound_blob(raw,refs,symbols)
    mapped=table
    if name in ('broken.o','alias-00.o'):
        _,fs,_=parse_object(obj);offset=fs['func_151E22BC']['value'];pool=sections(obj)['.rodata'][1]
        mapped=struct.pack('>10I',*(ENTRY+n-offset for n in struct.unpack_from('>10I',pool)))
    programs.append((words,mapped))
cases=[]
for index,value,clamp,alias in itertools.product((-1,0,1,2,3,4,5,6,7,8,9,10),(-128,0,1),(0,4,5,255),(0,1,3,11)):
    c=Case(index,value,clamp,alias);initial,rec=fixture(c);expected=reference(initial,c,rec);models=[]
    for p,mapped in programs:
        try:
            memory=initial.copy();memory.update({TABLE+i:v for i,v in enumerate(mapped)})
            m=Machine(p,memory,c).run();public={a:v for a,v in m.memory.items() if not STACK-512<=a<STACK+512 and not TABLE<=a<TABLE+40}
            wanted={a:v for a,v in expected.items() if not TABLE<=a<TABLE+40}
            models.append({'matches_reference':public==wanted,'calls':m.calls,'error':''})
        except (AssertionError,KeyError,ValueError,OverflowError,ZeroDivisionError) as e:models.append({'matches_reference':False,'calls':[],'error':str(e)[:120]})
    cases.append({'case':repr(c),'index':index,'alias':alias,'models':models})
report={'cases':len(cases),'streams':len(programs),'reference_mismatches':[sum(not r['models'][i]['matches_reference'] for r in cases) for i in range(len(programs))],
        'errors':[sum(bool(r['models'][i]['error']) for r in cases) for i in range(len(programs))],
        'wrong_calls':[sum(r['models'][i]['calls']!=[CALLEE] for r in cases) for i in range(len(programs))],
        'disjoint_mismatches':[sum(not r['models'][i]['matches_reference'] for r in cases if r['alias']==0) for i in range(len(programs))],
        'modeled_callee':True,'uncredited':True,'details':cases}
(out/'guest-screen.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items() if k!='details'},flush=True)
