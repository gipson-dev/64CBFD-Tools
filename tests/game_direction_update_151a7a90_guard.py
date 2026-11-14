from pathlib import Path
import csv,io,json,re,struct,subprocess,os
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
r=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();c=r/'conker';o=c/'build/game-direction-update-151a7a90-screen';name='func_151A7A90'
assembly=(c/'asm/1D4E00.s').read_text();m=re.search(r'^glabel '+name+r'\n.*?^endlabel '+name+r'\s*$',assembly,re.M|re.S);assert m
(o/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+m.group()+'\n.size '+name+',.-'+name+'\n')
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'retail.o'),str(o/'retail.s')],cwd=c,capture_output=True,check=True)
raw,refs=payload(o/'selected.o',name);assert len(raw)==732
recipe=((0x70,0xafa80060,0xafa80064),(0x88,0x8fa80060,0x8fa80064),(0xb4,0xafa80060,0xafa80064),(0xcc,0x8fa80060,0x8fa80064),(0x114,0xa3a9005f,0xa3a90063),(0x124,0xafa80060,0xafa80064),(0x140,0x8fa80060,0x8fa80064),(0x148,0x93a9005f,0x93a90063),(0x158,0x27a50044,0x27a50048),(0x170,0x27a40038,0x27a4003c),(0x174,0x27a60050,0x27a60054),(0x17c,0xe7b20038,0xe7b2003c),(0x18c,0xe7a8003c,0xe7a80040),(0x19c,0xe7b20040,0xe7b20044),(0x1b8,0xa3a9005f,0xa3a90063),(0x1c0,0xafa80060,0xafa80064),(0x1c4,0xc7a40050,0x8fa80064),(0x1c8,0xc6060058,0x93a90063),(0x1cc,0xc7aa0054,0xc7a40054),(0x1d0,0x8fa80060,0xc6060058),(0x1d4,0x46062202,0xc7aa0058),(0x1d8,0xc7a40058,0x00001825),(0x1dc,0x93a9005f,0x46062202),(0x1e0,0x00001825,0xc7a4005c),(0x1e4,0xe7a80050,0xe7a80054),(0x1f0,0xe7b20054,0xe7b20058),(0x1fc,0xe7a80058,0xe7a8005c),(0x214,0xc7b00050,0xc7b00054),(0x224,0xc7a60044,0xc7a60048),(0x23c,0xc7aa0038,0xc7aa003c),(0x250,0xc7a80054,0xc7a80058),(0x254,0xc7b20048,0xc7b2004c),(0x268,0xc7a4003c,0xc7a40040),(0x27c,0xc7a60058,0xc7a6005c),(0x280,0xc7aa004c,0xc7aa0050),(0x294,0xc7b00040,0xc7b00044))
schedule=set(range(0x1c4,0x1e4,4))
assert len(recipe)==36 and len(schedule)==8
for at,a,b in recipe:
 if at not in schedule:assert b==a+4 and (a>>21&31)==29
before=[a+(4 if (a>>21&31)==29 else 0) for at,a,b in recipe if at in schedule]
after=[b for at,a,b in recipe if at in schedule]
assert after==[before[i] for i in (3,6,0,1,2,7,4,5)]
rows=[]
for at,expected,replacement in recipe:
 assert struct.unpack_from('>I',raw,at)[0]==expected and not refs.get(at)
 rows.append(dict(filename='generated_1D4E00',function=name,offset='0x%X'%at,expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Normalize direction updater closed local-home permutation and independent post-cross schedule',insert_after='',insert_after_relocations='',omit='false'))
original=(c/'retail_word_patches.us.csv').read_bytes();existing=[x for x in csv.DictReader(io.StringIO(original.decode())) if x['function']==name];assert not existing or existing==rows
stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=next(csv.reader(io.StringIO(original.decode()))),lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows([] if existing else rows)
(o/'proposed-guards.csv').write_bytes(original+stream.getvalue().encode());(o/'guarded.s').write_text(pg.emit_padded_assembly(o/'selected.o',c/'asm/1D4E00.s',filename='generated_1D4E00',word_patches_path=o/'proposed-guards.csv'))
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'guarded.o'),str(o/'guarded.s')],cwd=c,capture_output=True,check=True)
symbols={a[1]:a[2][1] for a in symbol_rows((c/'build/conker.us.elf').read_bytes())};words=bound_blob(*payload(o/'guarded.o',name),symbols);truth=struct.unpack_from('>183I',(c/'conker.us.bin').read_bytes(),0x1d4f40);assert tuple(words)==truth
assert normalized_pools(o/'baseline.o')==normalized_pools(o/'selected.o')
neighbors=same_functions(c/'build/src/game/generated_1D4E00.c.o',o/'guarded.o',(name,));assert neighbors==22
print(json.dumps(dict(raw_words=183,padded_words=183,guards=36,insertions=0,omissions=0,neighbors=neighbors,installed=bool(existing))),flush=True)
