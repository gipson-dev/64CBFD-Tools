from pathlib import Path
import csv,io,json,re,struct,subprocess,os
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
r=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();c=r/'conker';o=c/'build/game-attached-direction-151a87f8-screen';name='func_151A87F8'
assembly=(c/'asm/1D4E00.s').read_text();m=re.search(r'^glabel '+name+r'\n.*?^endlabel '+name+r'\s*$',assembly,re.M|re.S);assert m
(o/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+m.group()+'\n.size '+name+',.-'+name+'\n')
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'retail.o'),str(o/'retail.s')],cwd=c,capture_output=True,check=True)
raw,refs=payload(o/'selected.o',name);assert len(raw)==552
recipe=((0x74,0x01273021,0x00e93021),(0x98,0x27af005c,0x27af0078),(0x120,0x8fa4005c,0x8fa40078),(0x174,0x27a40078,0x27a4007c),(0x17c,0xe7a40078,0xe7a4007c),(0x18c,0xe7aa007c,0xe7aa0080),(0x1a0,0xe7a80080,0xe7a80084),(0x1c4,0x27a40078,0x27a4007c),(0x1c8,0x27a5006c,0x27a50060),(0x1e0,0x24020001,0x358d0002),(0x1e4,0x358d0002,0xa20d001c),(0x1ec,0xa20d001c,0x24020001),(0x1f4,0x24020001,0x31cffffd),(0x1f8,0x31cffffd,0xa20f001c),(0x200,0xa20f001c,0x24020001),(0x208,0x24020001,0x3319fffd),(0x20c,0x3319fffd,0xa219001c),(0x210,0xa219001c,0x24020001))
rows=[]
for at,expected,replacement in recipe:
 assert struct.unpack_from('>I',raw,at)[0]==expected and not refs.get(at)
 note='Normalize attached-direction local homes, return-constant schedule and commutative matrix address'
 rows.append(dict(filename='generated_1D4E00',function=name,offset='0x%X'%at,expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note=note,insert_after='',insert_after_relocations='',omit='false'))
original=(c/'retail_word_patches.us.csv').read_bytes();existing=[x for x in csv.DictReader(io.StringIO(original.decode())) if x['function']==name];assert not existing or existing==rows
stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=next(csv.reader(io.StringIO(original.decode()))),lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows([] if existing else rows)
(o/'proposed-guards.csv').write_bytes(original+stream.getvalue().encode());(o/'guarded.s').write_text(pg.emit_padded_assembly(o/'selected.o',c/'asm/1D4E00.s',filename='generated_1D4E00',word_patches_path=o/'proposed-guards.csv'))
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'guarded.o'),str(o/'guarded.s')],cwd=c,capture_output=True,check=True)
symbols={a[1]:a[2][1] for a in symbol_rows((c/'build/conker.us.elf').read_bytes())};words=bound_blob(*payload(o/'guarded.o',name),symbols);truth=struct.unpack_from('>138I',(c/'conker.us.bin').read_bytes(),0x1d5ca8);assert tuple(words)==truth
assert normalized_pools(o/'baseline.o')==normalized_pools(o/'selected.o')
neighbors=same_functions(c/'build/src/game/generated_1D4E00.c.o',o/'guarded.o',(name,));assert neighbors==22
print(json.dumps(dict(raw_words=138,padded_words=138,guards=18,insertions=0,omissions=0,neighbors=neighbors,installed=bool(existing))),flush=True)
