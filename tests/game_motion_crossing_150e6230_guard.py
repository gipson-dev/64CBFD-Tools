"""Derive a private two-insertion retail schedule proposal."""
from pathlib import Path
import csv,io,json,re,struct,subprocess
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object as pg
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-motion-crossing-150e6230-durable';conker=root/'conker';name='func_150E6230'
asm=(conker/'asm/113480.s').read_text();match=re.search(r'^glabel '+name+r'\n.*?^endlabel '+name+r'\s*$',asm,re.M|re.S);assert match
retail=out/'retail.s';obj=out/'retail.o';retail.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+match.group()+'\n.size '+name+',.-'+name+'\n')
p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(conker)),str(retail.relative_to(conker))],cwd=conker,capture_output=True,text=True);assert p.returncode==0,p.stderr
raw,refs=payload(out/'formatted.o',name);desired,drefs=payload(obj,name);assert len(raw)==360 and len(desired)==368
a=struct.unpack('>90I',raw);b=struct.unpack('>92I',desired)
def index(i):return i+(i>60)+(i>74)
inserts={60:61,74:76};changed=[i for i in range(90) if a[i]!=b[index(i)] or refs.get(i*4)!=drefs.get(index(i)*4) or i in inserts]
assert changed==[3,4,7,8,11,14,18,21,24,26,28,31,44,45,49,60,62,63,64,65,66,67,68,69,70,71,72,73,74],changed
spec=lambda v:';'.join('%s:%s'%x for x in v) or '-'
rows=[]
for i in changed:
 j=index(i);insert=inserts.get(i)
 rows.append(dict(filename='generated_113480',function=name,offset='0x%X'%(4*i),expected='0x%08X'%a[i],replacement='0x%08X'%b[j],expected_relocations=spec(refs.get(i*4,[])),replacement_relocations=spec(drefs.get(j*4,[])),note='Restore motion crossing stack roles and closed branch schedule',insert_after=('0x%08X'%b[insert] if insert is not None else ''),insert_after_relocations=(spec(drefs.get(insert*4,[])) if insert is not None else ''),omit='false'))
original=(conker/'retail_word_patches.us.csv').read_bytes();assert __import__('hashlib').sha256(original.replace(b'\r\n',b'\n')).hexdigest()=='2978eb42b9ec8cf0c8977e6ec2ed01225a081e7ef32c011642db65dc856d6f09';fields=next(csv.reader(io.StringIO(original.decode())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows)
guards=out/'proposed-guards.csv';guards.write_bytes(original+stream.getvalue().encode());text=pg.emit_padded_assembly(out/'formatted.o',conker/'asm/113480.s',filename='generated_113480',word_patches_path=guards);padded=out/'guarded.s';padded.write_text(text);paddedobj=out/'guarded.o'
p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(paddedobj.relative_to(conker)),str(padded.relative_to(conker))],cwd=conker,capture_output=True,text=True);assert p.returncode==0,p.stderr
symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};words=bound_blob(*payload(paddedobj,name),symbols);truth=struct.unpack_from('>92I',(conker/'conker.us.bin').read_bytes(),0x1136e0)
assert tuple(words)==truth
neighbors=same_functions(conker/'build/src/game/generated_113480.c.o',paddedobj,(name,))
report={'guard_rows':len(rows),'insertions':2,'retail_words':len(words),'owner_neighbors':neighbors,'uncredited':True}
(out/'guard-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
