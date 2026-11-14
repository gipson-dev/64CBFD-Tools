from pathlib import Path
import csv,io,re,struct,subprocess,json
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-pointer-list-validation-15114f44-screen';conker=root/'conker';name='func_15114F44';asm=(conker/'asm/13D350.s').read_text();m=re.search(r'^glabel '+name+r'\n.*?^endlabel '+name+r'\s*$',asm,re.M|re.S);assert m
retail=out/'retail.s';obj=out/'retail.o';retail.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+m.group()+'\n.size '+name+',.-'+name+'\n')
p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(conker)),str(retail.relative_to(conker))],cwd=conker,capture_output=True,text=True);assert p.returncode==0,p.stderr
raw,refs=payload(out/'selected.o',name);desired,drefs=payload(obj,name);assert len(raw)==len(desired)==356
before=struct.unpack('>89I',raw);after=struct.unpack('>89I',desired);changed=[i for i in range(89) if before[i]!=after[i] or refs.get(i*4)!=drefs.get(i*4)];assert len(changed)==7,changed
spec=lambda v:';'.join('%s:%s'%x for x in v) or '-'
rows=[dict(filename='generated_13D350',function=name,offset='0x%X'%(i*4),expected='0x%08X'%before[i],replacement='0x%08X'%after[i],expected_relocations=spec(refs.get(i*4,[])),replacement_relocations=spec(drefs.get(i*4,[])),note='Restore pointer list validation setup and empty-list schedule',insert_after='',insert_after_relocations='',omit='false') for i in changed]
original=(conker/'retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows);guards=out/'proposed-guards.csv';guards.write_bytes(original+stream.getvalue().encode());padded=out/'guarded.s';padded.write_text(pg.emit_padded_assembly(out/'selected.o',conker/'asm/13D350.s',filename='generated_13D350',word_patches_path=guards));paddedobj=out/'guarded.o'
p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(paddedobj.relative_to(conker)),str(padded.relative_to(conker))],cwd=conker,capture_output=True,text=True);assert p.returncode==0,p.stderr
symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};words=bound_blob(*payload(paddedobj,name),symbols);truth=struct.unpack_from('>89I',(conker/'conker.us.bin').read_bytes(),0x1423f4);assert tuple(words)==truth
base=conker/'build/src/game/generated_13D350.c.o';neighbors=same_functions(base,paddedobj,(name,));assert normalized_pools(out/'baseline.o')==normalized_pools(out/'selected.o');print(json.dumps(dict(guard_rows=len(rows),changed=changed,padded_neighbors=neighbors,words=len(words),uncredited=True)),flush=True)
