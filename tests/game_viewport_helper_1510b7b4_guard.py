from pathlib import Path
import csv,io,json,re,struct,subprocess,hashlib
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object as pg
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-viewport-helper-shape-screen';conker=root/'conker';name='func_1510B7B4';asm=(conker/'asm/138520.s').read_text();m=re.search(r'^glabel '+name+r'\n.*?^endlabel '+name+r'\s*$',asm,re.M|re.S);assert m
retail=out/'retail.s';obj=out/'retail.o';retail.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+m.group()+'\n.size '+name+',.-'+name+'\n')
p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(conker)),str(retail.relative_to(conker))],cwd=conker,capture_output=True,text=True);assert p.returncode==0,p.stderr
raw,refs=payload(out/'owner-candidate.o',name);desired,drefs=payload(obj,name);assert len(raw)==len(desired)==420
before=struct.unpack('>105I',raw);after=struct.unpack('>105I',desired);changed=[i for i in range(105) if before[i]!=after[i] or refs.get(i*4)!=drefs.get(i*4)];print('changed',changed,flush=True);assert changed==[70,71,72,74,75,76,77,78,79,81,82,84,85,87,88,89,93,94,95,96,97,98,99,100]
spec=lambda v:';'.join('%s:%s'%x for x in v) or '-'
rows=[dict(filename='generated_138520',function=name,offset='0x%X'%(i*4),expected='0x%08X'%before[i],replacement='0x%08X'%after[i],expected_relocations=spec(refs.get(i*4,[])),replacement_relocations=spec(drefs.get(i*4,[])),note='Restore viewport command register roles and independent read schedule',insert_after='',insert_after_relocations='',omit='false') for i in changed]
original=(conker/'retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows);guards=out/'proposed-guards.csv';guards.write_bytes(original+stream.getvalue().encode());padded=out/'guarded.s';padded.write_text(pg.emit_padded_assembly(out/'owner-candidate.o',conker/'asm/138520.s',filename='generated_138520',word_patches_path=guards));paddedobj=out/'guarded.o'
p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(paddedobj.relative_to(conker)),str(padded.relative_to(conker))],cwd=conker,capture_output=True,text=True);assert p.returncode==0,p.stderr
symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};words=bound_blob(*payload(paddedobj,name),symbols);truth=struct.unpack_from('>105I',(conker/'conker.us.bin').read_bytes(),0x138c64);assert tuple(words)==truth
neighbors=same_functions(conker/'build/src/game/generated_138520.c.o',paddedobj,(name,));report={'guard_rows':len(rows),'retail_words':len(words),'neighbors':neighbors,'guard_sha256':hashlib.sha256(original).hexdigest(),'uncredited':True};(out/'guard-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
