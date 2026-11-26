"""Unmasked instructions, fail-closed literal pool and contiguous rebases."""
from pathlib import Path
from unittest.mock import patch
import json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_bouncing_effect_150db114_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_bouncing_effect_150db114_guest as g
from tools import check_bouncing_effect_150db114_pool as check_pool
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_local_vector_transform_15117da4_match import assembly
r=target_packet.ROOT;fn='func_150DB114';filename='generated_108320'
def assemble(s,path):
 f=path.with_suffix('.s');f.write_text(s);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def main():
 raw,refs=g.payload(o/'bound-owner.o',fn);truth=g.payload(o/'original-target.o',fn);assert len(refs)==8;w=o/'boundaries';w.mkdir(exist_ok=True);obj=w/'raw.o';assemble(assembly(raw,refs,fn),obj)
 lines=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[x for x in lines if x.split(',')[1:3]==[filename,fn]];assert len(rows)==1;layout=w/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');full=o/'baseline/conker/retail_word_patches.us.csv';assert fn not in full.read_text();guards=w/'guards.csv';guards.write_text(full.read_text().splitlines()[0]+'\n')
 emitters=[lambda p:pc.emit_padded_assembly(p,layout,filename,word_patches_path=guards,rodata_symbol='D_800A0BE4'),lambda p:pg.emit_padded_assembly(p,o/'original-target.s',filename=filename,word_patches_path=guards,rodata_symbol='D_800A0BE4')];outs=[]
 for i,emit in enumerate(emitters):
  p=w/f'padded-{i}.o';assemble(emit(obj),p);assert g.bound_blob(*g.payload(p,fn),g.symbols(g.Case()))==g.bound_blob(*truth,g.symbols(g.Case()));outs.append(p)
 visible=bindings=0
 for at in range(0,452,4):
  changed=bytearray(raw);changed[at]^=4;p=w/'changed.o';assemble(assembly(changed,refs,fn),p)
  for i,emit in enumerate(emitters):
   result=w/f'visible-{i}.o';assemble(emit(p),result);assert g.payload(result,fn)!=g.payload(outs[i],fn);visible+=1
 for at in refs:
  changed={k:list(v)for k,v in refs.items()};kind,name=changed[at][0];changed[at]=[(kind,name+'_wrong')];p=w/'wrong-binding.o';assemble(assembly(raw,changed,fn),p)
  for i,emit in enumerate(emitters):
   result=w/f'binding-visible-{i}.o';assemble(emit(p),result);assert g.payload(result,fn)!=g.payload(outs[i],fn);bindings+=1
 original=(o/'selected-owner.o').read_bytes();header=pg.ELF_HEADER.unpack_from(original);hs=[pg.SECTION_HEADER.unpack_from(original,header[6]+i*header[11])for i in range(header[12])];n=hs[header[13]];names=original[n[4]:n[4]+n[5]];index,sec=next((i,s)for i,s in enumerate(hs)if pg.read_c_string(names,s[0])=='.rodata');check_pool.verify(o/'selected-owner.o');pool_rejects=[]
 for offset in range(16):
  bad=bytearray(original);bad[sec[4]+offset]^=1;p=w/'wrong-pool.o';p.write_bytes(bad)
  try:check_pool.verify(p);raise AssertionError('accepted wrong literal/padding')
  except ValueError:pool_rejects.append(offset)
 for field,value in((2,3),(5,12)):
  bad=bytearray(original);struct.pack_into('>I',bad,header[6]+index*header[11]+4*field,value);p=w/'wrong-section.o';p.write_bytes(bad)
  try:check_pool.verify(p);raise AssertionError('accepted wrong pool section')
  except ValueError:pool_rejects.append('field'+str(field))
 p=w/'oversize.o';assemble(assembly(raw+bytes(16),refs,fn),p);overflow=[]
 for emit in emitters:
  try:s=emit(p)
  except ValueError:overflow.append('rejected')
  else:assert'__retail_overflow_'+fn in s;overflow.append('visible overflow')
 links=runs=0
 for group,(entry,low)in enumerate(((g.ENTRY,0x0BE4),(0x250DB114,0x7FF8),(0x350DB114,0x8000),(0x450DB114,0xFFF8))):
  pool=0x80100000+low;dt=0x80200000+low;syms=dict(D_800BE9A4=dt,D_800A0BE4=pool,D_800A0BE8=pool+4,D_800A0BEC=pool+8,**{'.rodata':pool});programs=[]
  for i,p in enumerate((o/'normalized-target.o',*outs,o/'original-target.o',obj)):
   ld=w/f'{group}-{i}.ld';ld.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=ld.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(ld),'-e',fn,*[f'--defsym={n}=0x{v:X}'for n,v in syms.items()],'-o',str(elf),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr;blob=sections(elf)['.text'][1];assert not any(blob[452:]);words=list(struct.unpack_from('>113I',blob));assert words==g.bound_blob(*g.payload(p,fn),syms);programs.append(words);links+=1
  assert all(words==programs[0]for words in programs)
  with patch.multiple(g,ENTRY=entry,DT=dt,POOL=pool):
   for c in(g.Case(),g.Case(y=g.bits(2),z=g.bits(.5)),g.Case(alpha=0),g.Case(dt=g.bits(-.5)),g.Case(rm=3,object=g.STACK+64)):
    models=[g.check(words,c)for words in programs];assert all(g.state(m)==g.state(models[0])for m in models[1:]);runs+=5
 q=dict(guards=0,independent_literal_symbols_across_signed_low_carry=True,all_word_corruptions_visible=visible,all_binding_corruptions_visible=bindings,pool_rejections=len(pool_rejects),entire_guard_manifest_unchanged=True,GNU_links=links,guest_rebase_runs=runs,three_literal_aliases_rebased_as_contiguous_unit=True,compiler_alignment_never_overwrites_next_original_nonzero_word=True,oversized=overflow,source_installed=target_packet.installed(),matching_credit=0);(o/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
