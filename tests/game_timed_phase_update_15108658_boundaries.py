"""Exercise every word guard, exact binding pin, slot limit and GNU rebases."""
from pathlib import Path
from unittest.mock import patch
import csv,io,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_timed_phase_update_15108658_match as packet
from tools.tests import game_timed_phase_update_15108658_guest as g
o=packet.OUT
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_classifier_candidates import sections
r=packet.ROOT;fn='func_15108658';filename='generated_135780'
def assembly(raw,refs):
 text='.set noat\n.set noreorder\n.text\n.globl '+fn+'\n.type '+fn+',@function\n'+fn+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):text+=f'.reloc ., {kind}, {name}\n'
  text+=f'.word 0x{word:08X}\n'
 return text+'.size '+fn+',.-'+fn+'\n'
def assemble(text,path):
 src=path.with_suffix('.s');src.write_text(text);p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(src)],text=True,capture_output=True);assert p.returncode==0,p.stderr
def main():
 raw,refs=g.payload(o/'selected-final/owner-candidate.o',fn);truth=g.payload(o/'original-target.o',fn);w=o/'boundaries';w.mkdir(exist_ok=True);f=w/'raw.o';assemble(assembly(raw,refs),f)
 lines=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[s for s in lines if s.split(',')[1:3]==[filename,fn]];assert len(rows)==1;layout=w/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');guard=w/'guards.csv';guard.write_text((o/'selected-guards.csv').read_text().splitlines()[0]+'\n'+(o/'guard-additions.csv').read_text());pins={int(row[2],0)for row in csv.reader(io.StringIO((o/'guard-additions.csv').read_text()))};assert len(pins)==46
 full=pg.load_word_patches(o/'selected-guards.csv',filename);scoped=pg.load_word_patches(guard,filename);assert{k:v for k,v in full.items()if k[0]==fn}==scoped
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,filename,word_patches_path=guard),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename=filename,word_patches_path=guard)];outputs=[]
 for i,emit in enumerate(emitters):
  out=w/f'padded-{i}.o';assemble(emit(f),out);assert g.payload(out,fn)==truth;outputs.append(out)
 rejected=visible=0
 for at in range(0,420,4):
  bad=bytearray(raw);bad[at+3]^=4;obj=w/'changed.o';assemble(assembly(bad,refs),obj)
  for i,emit in enumerate(emitters):
   if at in pins:
    try:emit(obj)
    except ValueError as e:assert'expected'in str(e).lower()or'patch'in str(e).lower();rejected+=1
    else:raise AssertionError('Guard bypass')
   else:
    out=w/f'visible-{i}.o';assemble(emit(obj),out);assert g.payload(out,fn)!=truth;visible+=1
 bindings=guarded_bindings=0
 for at in refs:
  changed={k:list(v)for k,v in refs.items()};kind,name=changed[at][0];changed[at]=[(kind,name+'_wrong')];obj=w/'wrong-binding.o';assemble(assembly(raw,changed),obj)
  for i,emit in enumerate(emitters):
   if at in pins:
    try:emit(obj)
    except ValueError:guarded_bindings+=1
    else:raise AssertionError('Guard binding bypass')
   else:
    out=w/f'wrong-binding-{i}.o';assemble(emit(obj),out);assert g.payload(out,fn)!=truth
  assert changed!=refs;bindings+=1
 over=w/'oversize.o';assemble(assembly(raw+bytes(16),refs),over);overflow=[]
 for emit in emitters:
  try:text=emit(over)
  except ValueError:overflow.append('rejected')
  else:assert'__retail_overflow_'+fn in text;overflow.append('visible overflow')
 links=runs=0;calls={'func_150ADA68'};names={n for rows in refs.values()for _,n in rows}
 for group,(entry,low)in enumerate(((g.ENTRY,0),(0x25108658,0x7ff8),(0x35108658,0x8000),(0x45108658,0xfff8))):
  symbols={n:(entry&0xf0000000)+0x210000+0x20000*i+low for i,n in enumerate(sorted(calls))};symbols.update({n:0x80100000+0x20000*i+low for i,n in enumerate(sorted(names-calls))});programs=[]
  for i,obj in enumerate([o/'normalized-target.o',*outputs,o/'original-target.o',f]):
   script=w/f'{group}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');p=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',fn,*[f'--defsym={n}=0x{a:X}'for n,a in symbols.items()],'-o',str(elf),str(obj)],text=True,capture_output=True);assert p.returncode==0,p.stderr;blob=sections(elf)['.text'][1];assert not any(blob[420:]);words=list(struct.unpack_from('>105I',blob));assert words==g.bound_blob(*g.payload(obj,fn),symbols);programs.append(words);links+=1
  assert all(ws==programs[0]for ws in programs[:4])
  with patch.multiple(g,ENTRY=entry,RNG=symbols['func_150ADA68'],DELTA=symbols['D_800BE9A4'],EDGE=symbols['D_800A2460'],RATE=symbols['D_800A2464']):
   for c in(g.Case(),g.Case(mutation=1),g.Case(cooldown=2**-30),g.Case(cooldown=11.),g.Case(remaining=-1.)):
    models=[g.Machine(ws,c).run()for ws in programs];a=models[0]
    assert all((m.memory,m.r,m.f,m.fcsr,m.calls)==(a.memory,a.r,a.f,a.fcsr,a.calls)for m in models[1:4]);rawm=models[-1]
    assert(rawm.memory,rawm.r[2],rawm.fcsr,rawm.calls,rawm.observations)==(a.memory,a.r[2],a.fcsr,a.calls,a.observations)
    assert[x for x in rawm.fp_operations if x[0]==1]==[x for x in a.fp_operations if x[0]==1];runs+=5
 q=dict(guarded_word_corruptions_rejected=rejected,unguarded_word_corruptions_visible=visible,raw_binding_positions_pinned=bindings,guarded_binding_corruptions_rejected=guarded_bindings,unguarded_bindings_remain_visible=True,full_and_scoped_guard_rows_equal=True,GNU_links=links,guest_rebase_runs=runs,oversized=overflow,raw_caller_scratch_register_and_fault_prefix_equality_not_claimed=True,source_installed=packet.installed(),matching_credit=0)
 (o/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
