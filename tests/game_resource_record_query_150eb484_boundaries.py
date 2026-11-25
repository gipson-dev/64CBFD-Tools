"""Exercise every word guard, exact binding pin, slot limit and GNU rebases."""
from pathlib import Path
from unittest.mock import patch
import csv,io,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()));from tools.experiments import game_resource_record_query_150eb484_match as packet
o=packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_resource_record_query_150eb484_guest as g
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_classifier_candidates import sections
r=packet.ROOT;fn='func_150EB484';filename='generated_1188E0'
def assembly(raw,refs):
 text='.set noat\n.set noreorder\n.text\n.globl '+fn+'\n.type '+fn+',@function\n'+fn+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):text+=f'.reloc ., {kind}, {name}\n'
  text+=f'.word 0x{word:08X}\n'
 return text+'.size '+fn+',.-'+fn+'\n'
def assemble(text,path):
 src=path.with_suffix('.s');src.write_text(text);p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(src)],text=True,capture_output=True);assert p.returncode==0,p.stderr
def main():
 raw,refs=g.payload(o/'selected-1188E0.o',fn);truth=g.payload(o/'original-target.o',fn);w=o/'boundaries';w.mkdir(exist_ok=True);f=w/'raw.o';assemble(assembly(raw,refs),f)
 lines=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[s for s in lines if s.split(',')[1:3]==[filename,fn]];assert len(rows)==1;layout=w/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');guard=w/'guards.csv';guard.write_text((o/'selected-guards.csv').read_text().splitlines()[0]+'\n'+(o/'guard-additions.csv').read_text());pins={int(row[2],0)for row in csv.reader(io.StringIO((o/'guard-additions.csv').read_text()))};assert len(pins)==23
 full=pg.load_word_patches(o/'selected-guards.csv',filename);scoped=pg.load_word_patches(guard,filename);assert{k:v for k,v in full.items()if k[0]==fn}==scoped
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,filename,word_patches_path=guard),lambda f:pg.emit_padded_assembly(f,o/'func_150EB484-original.s',filename=filename,word_patches_path=guard)];outputs=[]
 for i,emit in enumerate(emitters):
  out=w/f'padded-{i}.o';assemble(emit(f),out);assert g.payload(out,fn)==truth;outputs.append(out)
 rejected=visible=0
 for at in range(0,400,4):
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
 links=runs=0;calls={'func_15083E90','func_150A34B0','func_150A2864','func_150EBC80'};names={n for rows in refs.values()for _,n in rows}
 for group,(entry,low)in enumerate(((g.ENTRY,0),(0x250eb484,0x7ff8),(0x350eb484,0x8000),(0x450eb484,0xfff8))):
  symbols={n:(entry&0xf0000000)+0x210000+0x20000*i+low for i,n in enumerate(sorted(calls))};symbols.update({n:0x80100000+0x20000*i+low for i,n in enumerate(sorted(names-calls))});symbols['D_80088AA0']=0x80180000+low;symbols['D_80088AB0']=symbols['D_80088AA0']+16;symbols['D_80088AD0']=symbols['D_80088AB0']+32;programs=[]
  for i,obj in enumerate([o/'normalized-target.o',*outputs,o/'original-target.o',f]):
   script=w/f'{group}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');p=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',fn,*[f'--defsym={n}=0x{a:X}'for n,a in symbols.items()],'-o',str(elf),str(obj)],text=True,capture_output=True);assert p.returncode==0,p.stderr;blob=sections(elf)['.text'][1];assert not any(blob[400:]);words=list(struct.unpack_from('>100I',blob));assert words==g.bound_blob(*g.payload(obj,fn),symbols);programs.append(words);links+=1
  assert all(ws==programs[0]for ws in programs[:4])
  with patch.multiple(g,ENTRY=entry,symbols=symbols):
   for c in(g.Case(),g.Case(hit=3,mutation=7),g.Case(hit=11,mutation=1),g.Case(context=0,hit=0,mutation=3),g.Case(context=0,hit=-1)):
    models=[g.Machine(ws,c).run()for ws in programs];a=models[0]
    assert all((m.memory,m.r,m.f,m.calls)==(a.memory,a.r,a.f,a.calls)for m in models[1:4]);rawm=models[-1]
    assert(g.public(rawm.memory,c),rawm.r[2],rawm.calls,rawm.observations)==(g.public(a.memory,c),a.r[2],a.calls,a.observations);runs+=5
 q=dict(guarded_word_corruptions_rejected=rejected,unguarded_word_corruptions_visible=visible,raw_binding_positions_pinned=bindings,guarded_binding_corruptions_rejected=guarded_bindings,unguarded_bindings_remain_visible=True,full_and_scoped_guard_rows_equal=True,GNU_links=links,guest_rebase_runs=runs,oversized=overflow,raw_private_frame_scratch_register_and_fault_prefix_equality_not_claimed=True,source_installed=packet.installed(),matching_credit=0)
 (o/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
