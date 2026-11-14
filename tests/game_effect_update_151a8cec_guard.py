from pathlib import Path
import csv,io,json,re,struct,subprocess,os
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
r=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();c=r/'conker';o=c/'build/game-effect-update-151a8cec-screen';name='func_151A8CEC'
assembly=(c/'asm/1D4E00.s').read_text();m=re.search(r'^glabel '+name+r'\n.*?^endlabel '+name+r'\s*$',assembly,re.M|re.S);assert m
(o/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+m.group()+'\n.size '+name+',.-'+name+'\n')
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'retail.o'),str(o/'retail.s')],cwd=c,capture_output=True,check=True)
raw,refs=payload(o/'selected.o',name);desired,drefs=payload(o/'retail.o',name);assert raw==desired and refs==drefs and len(raw)==560
original=(c/'retail_word_patches.us.csv').read_bytes();assert not any(x['function']==name for x in csv.DictReader(io.StringIO(original.decode())))
(o/'proposed-guards.csv').write_bytes(original);(o/'guarded.s').write_text(pg.emit_padded_assembly(o/'selected.o',c/'asm/1D4E00.s',filename='generated_1D4E00',word_patches_path=o/'proposed-guards.csv'))
subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o/'guarded.o'),str(o/'guarded.s')],cwd=c,capture_output=True,check=True)
symbols={a[1]:a[2][1] for a in symbol_rows((c/'build/conker.us.elf').read_bytes())};words=bound_blob(*payload(o/'guarded.o',name),symbols);truth=struct.unpack_from('>140I',(c/'conker.us.bin').read_bytes(),0x1d619c);assert tuple(words)==truth
assert normalized_pools(o/'baseline.o')==normalized_pools(o/'selected.o')
neighbors=same_functions(c/'build/src/game/generated_1D4E00.c.o',o/'guarded.o',(name,));assert neighbors==22
print(json.dumps(dict(raw_words=140,padded_words=140,guards=0,neighbors=neighbors,installed='void func_151A8CEC(struct260 *owner)' in (c/'src/game/generated_1D4E00.c').read_text())),flush=True)
