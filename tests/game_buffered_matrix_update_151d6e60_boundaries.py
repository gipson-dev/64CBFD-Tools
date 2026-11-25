"""No guard masks: expose every changed word/binding and verify GNU rebases."""
from pathlib import Path
from unittest.mock import patch
import json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_buffered_matrix_update_151d6e60_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_buffered_matrix_update_151d6e60_guest as g
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_local_vector_transform_15117da4_match import assembly
r=target_packet.ROOT;fn='func_151D6E60';filename='generated_203E20'
def assemble(s,path):
 f=path.with_suffix('.s');f.write_text(s);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def main():
 raw,refs=g.payload(o/'selected-owner.o',fn);truth=g.payload(o/'original-target.o',fn);assert(raw,refs)==truth and len(refs)==8;w=o/'boundaries';w.mkdir(exist_ok=True);obj=w/'raw.o';assemble(assembly(raw,refs,fn),obj)
 lines=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[line for line in lines if line.split(',')[1:3]==[filename,fn]];assert len(rows)==1;layout=w/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');full_guards=o/'baseline/conker/retail_word_patches.us.csv';assert fn not in full_guards.read_text();guards=w/'guards.csv';guards.write_text(full_guards.read_text().splitlines()[0]+'\n');assert not{k:v for k,v in pg.load_word_patches(full_guards,filename).items()if k[0]==fn}and not pg.load_word_patches(guards,filename)
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,filename,word_patches_path=guards),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename=filename,word_patches_path=guards)];outs=[]
 for i,emit in enumerate(emitters):
  f=w/f'padded-{i}.o';assemble(emit(obj),f);assert g.payload(f,fn)==truth;outs.append(f)
 visible=bindings=0
 for at in range(0,416,4):
  bad=bytearray(raw);bad[at+3]^=4;changed=w/'changed.o';assemble(assembly(bad,refs,fn),changed)
  for i,emit in enumerate(emitters):
   result=w/f'visible-{i}.o';assemble(emit(changed),result);assert g.payload(result,fn)!=truth;visible+=1
 for at in refs:
  changed={k:list(v)for k,v in refs.items()};kind,name=changed[at][0];changed[at]=[(kind,name+'_wrong')];f=w/'wrong-binding.o';assemble(assembly(raw,changed,fn),f)
  for i,emit in enumerate(emitters):
   result=w/f'binding-visible-{i}.o';assemble(emit(f),result);assert g.payload(result,fn)!=truth;bindings+=1
 over=w/'oversize.o';assemble(assembly(raw+bytes(16),refs,fn),over);overflow=[]
 for emit in emitters:
  try:s=emit(over)
  except ValueError:overflow.append('rejected')
  else:assert'__retail_overflow_'+fn in s;overflow.append('visible overflow')
 links=runs=0
 for group,(entry,low)in enumerate(((g.ENTRY,0),(0x251d6e60,0x7ff8),(0x351d6e60,0x8000),(0x451d6e60,0xfff8))):
  syms=dict(func_15144AA8=(entry&0xf0000000)+0x2144aa8,func_150A8050=(entry&0xf0000000)+0x20a8050,D_800BE9C0=0x80100000+low,D_800AB278=0x80210000+low);programs=[]
  for i,f in enumerate((o/'normalized-target.o',*outs,o/'original-target.o',obj)):
   ld=w/f'{group}-{i}.ld';ld.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=ld.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(ld),'-e',fn,*[f'--defsym={n}=0x{v:X}'for n,v in syms.items()],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr;blob=sections(elf)['.text'][1];assert not any(blob[416:]);words=list(struct.unpack_from('>104I',blob));assert words==g.bound_blob(*g.payload(f,fn),syms);programs.append(words);links+=1
  assert all(ws==programs[0]for ws in programs)
  with patch.multiple(g,ENTRY=entry,ANGLE=syms['func_15144AA8'],ROTATE=syms['func_150A8050'],PAGE=syms['D_800BE9C0'],SCALE=syms['D_800AB278']):
   for c in(g.Case(),g.Case(mode=15),g.Case(page=255),g.Case(position_alias=1),g.Case(object=g.STACK+32,mode=15)):
    models=[g.Machine(ws,c,entry=entry).run()for ws in programs];assert all(g.state(m)==g.state(models[0])for m in models[1:])
    for m in models:assert(m.memory,m.calls,m.observations,m.fp_operations,m.fcsr,m.r[2])==g.reference(m.initial,c,m.before[16],m.before[31])
    runs+=5

 q=dict(guards=0,all_word_corruptions_visible=visible,all_binding_corruptions_visible=bindings,raw_binding_positions_pinned=8,guard_manifest_unchanged=True,GNU_links=links,guest_rebase_runs=runs,oversized=overflow,source_installed=target_packet.installed(),matching_credit=0);(o/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
