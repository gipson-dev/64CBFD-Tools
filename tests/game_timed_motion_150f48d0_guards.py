"""Derive a private expected-word proposal from exact roles and scheduling."""
from pathlib import Path
import csv,io,json,re,struct,subprocess
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object as pg
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-timed-motion-150f48d0-durable';conker=root/'conker';name='func_150F48D0'
asm=(conker/'asm/121A20.s').read_text();match=re.search(r'^glabel '+name+r'\n.*?^endlabel '+name+r'\s*$',asm,re.M|re.S);assert match
retail=out/'retail.s';obj=out/'retail.o';retail.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+match.group()+'\n.size '+name+',.-'+name+'\n')
p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(conker)),str(retail.relative_to(conker))],cwd=conker,capture_output=True,text=True);assert p.returncode==0,p.stderr
raw,refs=payload(out/'formatted.o',name);desired,drefs=payload(obj,name);assert len(raw)==len(desired)==360
a=struct.unpack('>90I',raw);b=struct.unpack('>90I',desired);changed=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y or refs.get(i*4)!=drefs.get(i*4)]
roles=[1,2,5,7,16,19,20,23,25,26,27,35,41,47,76,82];schedule=[65,66,67,68,69,70];assert changed==sorted(roles+schedule),changed
assert all(refs.get(i*4)==drefs.get(i*4) for i in changed)
spec=lambda v:';'.join('%s:%s'%x for x in v) or '-'
rows=[]
for i in changed:
 rows.append(dict(filename='generated_121A20',function=name,offset='0x%X'%(4*i),expected='0x%08X'%a[i],replacement='0x%08X'%b[i],expected_relocations=spec(refs.get(i*4,[])),replacement_relocations=spec(drefs.get(i*4,[])),note='Normalize timed motion closed register roles' if i in roles else 'Restore timed motion independent load and float schedule',insert_after='',insert_after_relocations='',omit='false'))
original=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows)
guards=out/'proposed-guards.csv';guards.write_bytes(original+stream.getvalue().encode())
text=pg.emit_padded_assembly(out/'formatted.o',conker/'asm/121A20.s',filename='generated_121A20',word_patches_path=guards);padded=out/'guarded.s';padded.write_text(text);paddedobj=out/'guarded.o'
p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(paddedobj.relative_to(conker)),str(padded.relative_to(conker))],cwd=conker,capture_output=True,text=True);assert p.returncode==0,p.stderr
symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};words=bound_blob(*payload(paddedobj,name),symbols);truth=struct.unpack_from('>90I',(conker/'conker.us.bin').read_bytes(),0x121d80)
assert tuple(words)==truth and same_functions(conker/'build/src/game/generated_121A20.c.o',paddedobj,(name,))==5
report={'guard_rows':len(rows),'register_role_rows':len(roles),'schedule_rows':len(schedule),'retail_words':len(words),'owner_neighbors':5,'uncredited':True}
(out/'guard-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
