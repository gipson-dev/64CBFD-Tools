"""Every word/binding corruption and independent GNU carry/rebase checks."""
from pathlib import Path
from unittest.mock import patch
import csv,io,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_optional_emitter_150d728c_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_optional_emitter_150d728c_guest as g
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_local_vector_transform_15117da4_match import assembly
r=target_packet.ROOT;fn='func_150D728C';filename='generated_1045D0'
def assemble(s,path):
 f=path.with_suffix('.s');f.write_text(s);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def main():
 raw,refs=g.payload(o/'selected-owner.o',fn);truth=g.payload(o/'original-target.o',fn);assert len(raw)==392 and len(refs)==7;w=o/'boundaries';w.mkdir(exist_ok=True);obj=w/'raw.o';assemble(assembly(raw,refs,fn),obj)
 lines=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[line for line in lines if line.split(',')[1:3]==[filename,fn]];assert len(rows)==1;layout=w/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');full=o/'selected-guards.csv';parsed=csv.DictReader(io.StringIO(full.read_text()));patches=[row for row in parsed if row['function']==fn];assert len(patches)==0;guards=w/'guards.csv'
 with guards.open('w')as f:writer=csv.DictWriter(f,fieldnames=parsed.fieldnames);writer.writeheader();writer.writerows(patches)
 guarded={int(row['offset'],0)for row in patches};assert sorted(at for at in refs if at in guarded)==[];assert fn not in(o/'baseline/conker/retail_word_patches.us.csv').read_text()
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,filename,word_patches_path=guards),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename=filename,word_patches_path=guards)];outs=[]
 for i,emit in enumerate(emitters):
  f=w/f'padded-{i}.o';assemble(emit(obj),f);v,b=g.payload(f,fn);assert v[:392]==truth[0]and b==truth[1]and not any(v[392:]);outs.append(f)
 visible=rejected=bindings=0
 for at in range(0,392,4):
  bad=bytearray(raw);bad[at+3]^=4;changed=w/'changed.o';assemble(assembly(bad,refs,fn),changed)
  for i,emit in enumerate(emitters):
   if at in guarded:
    try:emit(changed)
    except ValueError as e:assert 'expected' in str(e);rejected+=1
    else:raise AssertionError(('masked guard corruption',at,i))
   else:
    result=w/f'visible-{i}.o';assemble(emit(changed),result);assert g.payload(result,fn)!=truth;visible+=1
 for at in refs:
  changed={k:list(v)for k,v in refs.items()};kind,name=changed[at][0];changed[at]=[(kind,name+'_wrong')];f=w/'wrong-binding.o';assemble(assembly(raw,changed,fn),f)
  for i,emit in enumerate(emitters):
   if at in guarded:
    try:emit(f)
    except ValueError as e:assert 'relocation' in str(e)
    else:raise AssertionError(('masked guard binding corruption',at,i))
   else:
    result=w/f'binding-visible-{i}.o';assemble(emit(f),result);assert g.payload(result,fn)!=truth;bindings+=1
 over=w/'oversize.o';assemble(assembly(raw+bytes(16),refs,fn),over);overflow=[]
 for emit in emitters:
  try:s=emit(over)
  except ValueError:overflow.append('rejected')
  else:assert'__retail_overflow_'+fn in s;overflow.append('visible overflow')
 links=runs=0
 for group,entry in enumerate((g.ENTRY,0x250D728C,0x350D728C,0x450D728C)):
  region=entry&0xF0000000;pre=tuple(region+v for v in(0x51C04F8,0x51C05A4,0x51C05F0));setup=region+0x51BFC40;emit=(region+0x514FB98,region+0x514FBFC);syms=dict(zip(('func_151C04F8','func_151C05A4','func_151C05F0','func_151BFC40','func_1514FB98','func_1514FBFC'),(*pre,setup,*emit)));programs=[]
  for i,f in enumerate((o/'normalized-target.o',*outs,o/'original-target.o',obj)):
   ld=w/f'{group}-{i}.ld';ld.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=ld.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(ld),'-e',fn,*[f'--defsym={n}=0x{v:X}'for n,v in syms.items()],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr;blob=sections(elf)['.text'][1];assert not any(blob[392:]);words=list(struct.unpack_from('>98I',blob));assert words==g.bound_blob(*g.payload(f,fn),syms)[:98];programs.append(words);links+=1
  assert all(ws==programs[0]for ws in programs)
  with patch.multiple(g,ENTRY=entry,PRE=pre,SETUP=setup,EMIT=emit):
   for c in(g.Case(matrix=0),g.Case(),g.Case(matrix=g.MATRIX+2,mutation=1),g.Case(matrix=0,mutation=7,phase=8),g.Case(mutation=7,phase=8)):
    models=[g.check(ws,c)for ws in programs];assert all(g.state(m)==g.state(models[0])for m in models[1:]);runs+=5

 q=dict(guards=0,guard_corruptions_rejected=rejected,unguarded_word_corruptions_visible=visible,all_binding_corruptions_visible=bindings,guard_binding_corruptions_rejected=0,raw_binding_positions_pinned=7,whole_guard_CSV_unchanged=True,body_words=98,retail_slot_words=101,retail_alignment_words=3,independent_jump_regions_only_no_HI16_LO16_target_bindings=True,GNU_links=links,guest_rebase_runs=runs,oversized=overflow,source_installed=target_packet.installed(),matching_credit=0);(o/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
