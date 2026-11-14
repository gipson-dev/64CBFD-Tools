from pathlib import Path
import csv,io,json,re,struct,subprocess,os
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
r=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();c=r/'conker';o=c/'build/game-spawn-allocator-151a8b20-screen';name='func_151A8B20'
assembly=(c/'asm/1D4E00.s').read_text();m=re.search(r'^glabel '+name+r'\n.*?^endlabel '+name+r'\s*$',assembly,re.M|re.S);assert m
(o/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+m.group()+'\n.size '+name+',.-'+name+'\n')
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'retail.o'),str(o/'retail.s')],cwd=c,capture_output=True,check=True)
raw,refs=payload(o/'selected.o',name);assert len(raw)==456
recipe=((0xb8,0x1040003e,0x1040003f,None),(0xe4,0x1140001f,0x11400020,None),(0x12c,0xe7a00048,0xe7a00040,None),(0x138,0xc7a00048,0xc7a00040,None),(0x15c,0x10000002,0xace20050,None),(0x160,0xace20050,0x10000003,0x90f80000))
rows=[]
for at,expected,replacement,insert in recipe:
 assert struct.unpack_from('>I',raw,at)[0]==expected and not refs.get(at)
 rows.append(dict(filename='generated_1D4E00',function=name,offset='0x%X'%at,expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Restore spawn allocator spatial-store schedule and independent float temporary',insert_after='' if insert is None else '0x%08X'%insert,insert_after_relocations='',omit='false'))
original=(c/'retail_word_patches.us.csv').read_bytes();existing=[x for x in csv.DictReader(io.StringIO(original.decode())) if x['function']==name];assert not existing or existing==rows
stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=next(csv.reader(io.StringIO(original.decode()))),lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows([] if existing else rows)
(o/'proposed-guards.csv').write_bytes(original+stream.getvalue().encode());(o/'guarded.s').write_text(pg.emit_padded_assembly(o/'selected.o',c/'asm/1D4E00.s',filename='generated_1D4E00',word_patches_path=o/'proposed-guards.csv'))
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'guarded.o'),str(o/'guarded.s')],cwd=c,capture_output=True,check=True)
symbols={a[1]:a[2][1] for a in symbol_rows((c/'build/conker.us.elf').read_bytes())};words=bound_blob(*payload(o/'guarded.o',name),symbols);truth=struct.unpack_from('>115I',(c/'conker.us.bin').read_bytes(),0x1d5fd0);assert tuple(words)==truth
assert normalized_pools(o/'baseline.o')==normalized_pools(o/'selected.o')
neighbors=same_functions(c/'build/src/game/generated_1D4E00.c.o',o/'guarded.o',(name,));assert neighbors==22
print(json.dumps(dict(raw_words=114,padded_words=115,guards=6,insertions=1,neighbors=neighbors,installed=bool(existing))),flush=True)
