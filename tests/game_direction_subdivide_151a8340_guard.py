from pathlib import Path
import csv,io,json,struct,subprocess,os
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
r=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();c=r/'conker';o=c/'build/game-direction-subdivide-151a8340-screen';name='func_151A8340'
assembly=(c/'asm/1D4E00.s').read_text();a=assembly.index('glabel '+name+'\n');z=assembly.index('endlabel '+name,a)+len('endlabel '+name)
(o/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+assembly[a:z]+'\n.size '+name+',.-'+name+'\n')
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'retail.o'),str(o/'retail.s')],cwd=c,capture_output=True,check=True)
raw,refs=payload(o/'selected.o',name);assert len(raw)==540;words=list(struct.unpack('>135I',raw));assert words[0]==0x27bdff88 and words[56:58]==[0x0c000000,0x46128781]
assert refs[0xe0]==[('R_MIPS_26','func_150ADA68')] and not refs.get(0xe4)
p=words[:56]+[words[57],words[56],0]+words[58:]
# Only the two forward exits cross the inserted no-op; the back edge grows by one.
for at,old,new in ((0x78,0x54200057,0x54200058),(0x84,0x5b000054,0x5b000055),(0x1d0,0x1020ffac,0x1020ffab)):
 assert p[at//4]==old;p[at//4]=new
# Exchange only the operands of two finite commutative single multiplies.
for at,old,new in ((0x108,0x4600b402,0x46160402),(0x154,0x4600b482,0x46160482)):
 assert p[at//4]==old and (old&~0x1ff800)==(new&~0x1ff800);p[at//4]=new
start,stop=0x158//4,0x1a0//4;before=p[start:stop];order=(2,0,1,6,4,5,9,7,10,11,12,13,14,15,16,17,3,8);assert sorted(order)==list(range(18));p[start:stop]=[before[i] for i in order]
rows=[]
for i,expected in enumerate(words):
 replacement=p[i+(i>=58)];insert=0 if i==57 else None
 if expected==replacement and insert is None:continue
 oldref=refs.get(i*4,[]);newref=[('R_MIPS_26','func_150ADA68')] if i==57 else []
 assert oldref==([('R_MIPS_26','func_150ADA68')] if i==56 else [])
 ref=lambda v:'R_MIPS_26:func_150ADA68' if v else '-'
 rows.append(dict(filename='generated_1D4E00',function=name,offset='0x%X'%(i*4),expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations=ref(oldref),replacement_relocations=ref(newref),note='Restore midpoint subdivision independent schedule, commutative multiply operands and original call-delay no-op',insert_after='' if insert is None else '0x00000000',insert_after_relocations='',omit='false'))
assert len(rows)==22 and sum(bool(a['insert_after']) for a in rows)==1
original=(c/'retail_word_patches.us.csv').read_bytes();existing=[x for x in csv.DictReader(io.StringIO(original.decode())) if x['function']==name];assert not existing or existing==rows
stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=next(csv.reader(io.StringIO(original.decode()))),lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows([] if existing else rows)
(o/'proposed-guards.csv').write_bytes(original+stream.getvalue().encode());(o/'guarded.s').write_text(pg.emit_padded_assembly(o/'selected.o',c/'asm/1D4E00.s',filename='generated_1D4E00',word_patches_path=o/'proposed-guards.csv'))
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'guarded.o'),str(o/'guarded.s')],cwd=c,capture_output=True,check=True)
sy={a[1]:a[2][1] for a in symbol_rows((c/'build/conker.us.elf').read_bytes())};truth=struct.unpack_from('>136I',(c/'conker.us.bin').read_bytes(),0x1d57f0);assert tuple(bound_blob(*payload(o/'guarded.o',name),sy))==truth
assert normalized_pools(o/'baseline.o')==normalized_pools(o/'selected.o');assert same_functions(c/'build/src/game/generated_1D4E00.c.o',o/'guarded.o',(name,))==22
assert payload(o/'baseline.o','func_151A7A90')==payload(o/'selected.o','func_151A7A90')
print(json.dumps(dict(raw_words=135,padded_words=136,guards=22,inserted_noops=1,omissions=0,neighbors=22,parent_unchanged=True,installed=bool(existing))),flush=True)
