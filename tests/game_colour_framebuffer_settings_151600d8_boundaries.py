"""All direct words/bindings remain exposed; independent GNU carry rebases."""
from pathlib import Path
from unittest.mock import patch
import json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_colour_framebuffer_settings_151600d8_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_colour_framebuffer_settings_151600d8_guest as g
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_local_vector_transform_15117da4_match import assembly
r=target_packet.ROOT;fn='func_151600D8';filename='generated_18D250'
def assemble(text,path):
 f=path.with_suffix('.s');f.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def main():
 raw,refs=g.payload(o/'selected-owner.o',fn);truth=g.payload(o/'original-target.o',fn);assert(raw,refs)==truth and len(refs)==33;w=o/'boundaries';w.mkdir(exist_ok=True);obj=w/'raw.o';assemble(assembly(raw,refs,fn),obj)
 lines=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[line for line in lines if line.split(',')[1:3]==[filename,fn]];assert len(rows)==1;layout=w/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');full=o/'baseline/conker/retail_word_patches.us.csv';assert fn not in full.read_text();guards=w/'guards.csv';guards.write_text(full.read_text().splitlines()[0]+'\n');assert not pg.load_word_patches(guards,filename)
 emitters=[lambda p:pc.emit_padded_assembly(p,layout,filename,word_patches_path=guards),lambda p:pg.emit_padded_assembly(p,o/'original-target.s',filename=filename,word_patches_path=guards)];outs=[]
 for i,emit in enumerate(emitters):
  p=w/f'padded-{i}.o';assemble(emit(obj),p);assert g.payload(p,fn)==truth;outs.append(p)
 visible=bindings=0
 for at in range(0,412,4):
  changed=bytearray(raw);changed[at+3]^=4;p=w/'changed.o';assemble(assembly(changed,refs,fn),p)
  for i,emit in enumerate(emitters):
   result=w/f'visible-{i}.o';assemble(emit(p),result);assert g.payload(result,fn)!=truth;visible+=1
 for at in refs:
  changed={k:list(v)for k,v in refs.items()};kind,name=changed[at][0];changed[at]=[(kind,name+'_wrong')];p=w/'wrong-binding.o';assemble(assembly(raw,changed,fn),p)
  for i,emit in enumerate(emitters):
   result=w/f'binding-visible-{i}.o';assemble(emit(p),result);assert g.payload(result,fn)!=truth;bindings+=1
 p=w/'oversize.o';assemble(assembly(raw+bytes(16),refs,fn),p);overflow=[]
 for emit in emitters:
  try:text=emit(p)
  except ValueError:overflow.append('rejected')
  else:assert'__retail_overflow_'+fn in text;overflow.append('visible overflow')
 links=runs=0
 for group,(entry,low)in enumerate(((g.ENTRY,0),(0x251600d8,0x7ff8),(0x351600d8,0x8000),(0x451600d8,0xfff8))):
  meta=0x80100000+low;coefficients=tuple(0x80210000+low+4*i for i in range(4));provider=(entry&0xf0000000)+0x21422dc;syms={'func_151422DC':provider}
  for offset in(*g.LABELS,*g.FILES):syms[f'D_{0x800a6540+offset:08X}']=meta+offset
  for i,name in enumerate(('D_800A6674','D_800A6678','D_800A667C','D_800A6680')):syms[name]=coefficients[i]
  programs=[]
  for i,p in enumerate((o/'normalized-target.o',*outs,o/'original-target.o',obj)):
   ld=w/f'{group}-{i}.ld';ld.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=ld.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(ld),'-e',fn,*[f'--defsym={n}=0x{v:X}'for n,v in syms.items()],'-o',str(elf),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr;blob=sections(elf)['.text'][1];assert not any(blob[412:]);words=list(struct.unpack_from('>103I',blob));assert words==g.bound_blob(*g.payload(p,fn),syms);programs.append(words);links+=1
  assert all(words==programs[0]for words in programs)
  with patch.multiple(g,ENTRY=entry,PROVIDER=provider,META=meta,COEFFS=coefficients):
   for c in(g.Case(),g.Case(actual=False,mode=15,values=(0xffffffff,0x7fffffff,0x80000000,0x01000001,17)),g.Case(pattern=7),g.Case(object=g.STACK+32),g.Case(actual=False,mode=8,phase=8,rm=3)):
    models=[g.check(words,c)for words in programs];assert all(g.state(m)==g.state(models[0])for m in models[1:]);runs+=5
 q=dict(guards=0,all_word_corruptions_visible=visible,all_binding_corruptions_visible=bindings,raw_binding_positions_pinned=33,entire_guard_manifest_unchanged=True,GNU_links=links,guest_rebase_runs=runs,actual7word_provider_rebased_with_leaf=True,all_distinct_metadata_and_coefficient_bindings_retained=True,oversized=overflow,source_installed=target_packet.installed(),matching_credit=0);(o/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
