from pathlib import Path
import json,os,struct,subprocess
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
r=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();c=r/'conker';o=c/'build/game-radial-ground-emitter-151a9834-screen';name='func_151A9834'
s=(c/'asm/1D4E00.s').read_text();a=s.index('glabel '+name+'\n');z=s.index('endlabel '+name,a)+len('endlabel '+name);(o/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+s[a:z]+'\n.size '+name+',.-'+name+'\n')
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'retail.o'),str(o/'retail.s')],cwd=c,capture_output=True,check=True)
sy={v[1]:v[2][1] for v in symbol_rows((c/'build/conker.us.elf').read_bytes())};rom=(c/'conker.us.bin').read_bytes();truth=struct.unpack_from('>102I',rom,0x1d6ce4);assert tuple(bound_blob(*payload(o/'selected.o',name),sy))==truth
(o/'proposed-guards.csv').write_bytes((c/'retail_word_patches.us.csv').read_bytes());(o/'guarded.s').write_text(pg.emit_padded_assembly(o/'selected.o',c/'asm/1D4E00.s',filename='generated_1D4E00',word_patches_path=o/'proposed-guards.csv'))
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'guarded.o'),str(o/'guarded.s')],cwd=c,capture_output=True,check=True)
assert tuple(bound_blob(*payload(o/'guarded.o',name),sy))==truth and same_functions(c/'build/src/game/generated_1D4E00.c.o',o/'guarded.o',(name,))==22 and normalized_pools(o/'baseline.o')==normalized_pools(o/'selected.o')
text,functions,_=pg.parse_object(o/'guarded.o');end=functions[name]['value']+408;assert text[end:end+4]==rom[0x1d6e7c:0x1d6e80]==bytes(4)
scans={}
for label,word in (('direct_jal',0x0c000000|((0x151a9834>>2)&0x3ffffff)),('literal_pointer',0x151a9834)):
 needle=struct.pack('>I',word);hits=[];i=0
 while True:
  at=rom.find(needle,i)
  if at<0:break
  if at%4==0:hits.append(at)
  i=at+1
 scans[label]=hits
assert scans['direct_jal']==[0x10c94c,0x164394,0x1fd484]
(o/'caller-inventory.json').write_text(json.dumps(scans,indent=2)+'\n')
print(json.dumps(dict(raw_words=102,padded_words=102,alignment_words=1,guards=0,insertions=0,omissions=0,neighbors=22,direct_callers=3)),flush=True)
