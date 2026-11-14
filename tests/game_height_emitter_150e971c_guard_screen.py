"""Build an uncredited, expected-word proposal with the real rodata binding."""
from pathlib import Path
import csv,hashlib,io,json,os,re,struct,subprocess
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools import pad_generated_object as pg
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-height-emitter-150e971c-durable';conker=root/'conker';name='func_150E971C'
original=(conker/'retail_word_patches.us.csv').read_bytes()
assert hashlib.sha256(original.replace(b'\r\n',b'\n')).hexdigest()=='1c334a7683340d6d28a8df2557fcbc4c6c3e7ba438e0a523b9929e4f580b2f4c'
assert 'generated_113D60.c.o: RETAIL_RODATA_SYMBOL := D_800A1350' in (conker/'Makefile').read_text()
asm=(conker/'asm/113D60.s').read_text();match=re.search(r'^glabel '+name+r'\n.*?^endlabel '+name+r'\s*$',asm,re.M|re.S);assert match
retail=out/'retail.s';obj=out/'retail.o';retail.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+match.group()+'\n.size '+name+',.-'+name+'\n')
p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(conker)),str(retail.relative_to(conker))],cwd=conker,capture_output=True,text=True);assert p.returncode==0,p.stderr
raw,refs=payload(out/'snapshot.o',name);desired,drefs=payload(obj,name);assert len(raw)==len(desired)==364
a=struct.unpack('>91I',raw);b=struct.unpack('>91I',desired);changed=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y or refs.get(i*4)!=drefs.get(i*4)]
report={'raw_relocations':refs,'retail_relocations':drefs,'changed':changed}
(out/'guard-diffs.json').write_text(json.dumps(report,indent=2)+'\n')
assert changed==[0,20,27,28,29,*range(42,56),57,59,64,67,88]
assert all(refs.get(i*4)==drefs.get(i*4) for i in changed)
spec=lambda v:';'.join('%s:%s'%x for x in v) or '-'
rows=[dict(filename='generated_113D60',function=name,offset='0x%X'%(4*i),expected='0x%08X'%a[i],replacement='0x%08X'%b[i],expected_relocations=spec(refs.get(i*4,[])),replacement_relocations=spec(drefs.get(i*4,[])),note='Normalize height emitter frame and descriptor store schedule',insert_after='',insert_after_relocations='',omit='false') for i in changed]
fields=next(csv.reader(io.StringIO(original.decode())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows)
guards=out/'proposed-guards.csv';guards.write_bytes(original+stream.getvalue().encode())
text=pg.emit_padded_assembly(out/'snapshot.o',conker/'asm/113D60.s',filename='generated_113D60',word_patches_path=guards,rodata_symbol='D_800A1350');padded=out/'guarded.s';padded.write_text(text);paddedobj=out/'guarded.o'
p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(paddedobj.relative_to(conker)),str(padded.relative_to(conker))],cwd=conker,capture_output=True,text=True);assert p.returncode==0,p.stderr
symbols={r[1]:r[2][1] for r in symbol_rows((conker/'build/conker.us.elf').read_bytes())};words=bound_blob(*payload(paddedobj,name),symbols);truth=struct.unpack_from('>91I',(conker/'conker.us.bin').read_bytes(),0x116bcc)
assert tuple(words)==truth
baseline=out/'baseline-padded.s';baseline.write_text(pg.emit_padded_assembly(out/'baseline.o',conker/'asm/113D60.s',filename='generated_113D60',word_patches_path=conker/'retail_word_patches.us.csv',rodata_symbol='D_800A1350'))
baselineobj=out/'baseline-padded.o';p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(baselineobj.relative_to(conker)),str(baseline.relative_to(conker))],cwd=conker,capture_output=True,text=True);assert p.returncode==0,p.stderr
neighbors=same_functions(baselineobj,paddedobj,(name,))
assert same_functions(conker/'build/src/game/generated_113D60.c.o',paddedobj,(name,))==neighbors==28
report={'guard_rows':len(rows),'retail_words':len(words),'unchanged_padded_owner_functions':neighbors,'rodata_symbol':'D_800A1350','uncredited':True}
(out/'guard-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
