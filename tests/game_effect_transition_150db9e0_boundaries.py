"""Every word/binding corruption and independent GNU carry/rebase checks."""
from pathlib import Path
from unittest.mock import patch
import csv,io,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_effect_transition_150db9e0_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_effect_transition_150db9e0_guest as g
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_local_vector_transform_15117da4_match import assembly
r=target_packet.ROOT;fn='func_150DB9E0';filename='generated_108E90'
def assemble(s,path):
 f=path.with_suffix('.s');f.write_text(s);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def main():
 raw,refs=g.payload(o/'selected-owner.o',fn);truth=g.payload(o/'original-target.o',fn);assert len(raw)==640 and len(refs)==25;w=o/'boundaries';w.mkdir(exist_ok=True);obj=w/'raw.o';assemble(assembly(raw,refs,fn),obj)
 lines=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[line for line in lines if line.split(',')[1:3]==[filename,fn]];assert len(rows)==1;layout=w/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');full=o/'selected-guards.csv';parsed=csv.DictReader(io.StringIO(full.read_text()));patches=[row for row in parsed if row['function']==fn];assert len(patches)==7;guards=w/'guards.csv'
 with guards.open('w')as f:writer=csv.DictWriter(f,fieldnames=parsed.fieldnames);writer.writeheader();writer.writerows(patches)
 guarded={int(row['offset'],0)for row in patches};assert sorted(at for at in refs if at in guarded)==[0x74];assert fn not in(o/'baseline/conker/retail_word_patches.us.csv').read_text()
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,filename,word_patches_path=guards),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename=filename,word_patches_path=guards)];outs=[]
 for i,emit in enumerate(emitters):
  f=w/f'padded-{i}.o';assemble(emit(obj),f);assert g.payload(f,fn)==truth;outs.append(f)
 visible=rejected=bindings=0
 for at in range(0,640,4):
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
 for group,(entry,low)in enumerate(((g.ENTRY,0),(0x250DB9E0,0x7FF8),(0x350DB9E0,0x8000),(0x450DB9E0,0xFFF8))):
  region=entry&0xF0000000;preset=region+0x5196438;oriented=region+0x5152F70;spawn=region+0x51491F4;short=region+0x5153298;constants=tuple(0x80210000+low+4*i for i in range(9));data=0x80320000+low;syms=dict(func_15196438=preset,func_15152F70=oriented,func_151491F4=spawn,func_15153298=short,D_80090514=data,**dict(zip(g.CONSTANT_NAMES,constants)));programs=[]
  for i,f in enumerate((o/'normalized-target.o',*outs,o/'original-target.o',obj)):
   ld=w/f'{group}-{i}.ld';ld.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=ld.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(ld),'-e',fn,*[f'--defsym={n}=0x{v:X}'for n,v in syms.items()],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr;blob=sections(elf)['.text'][1];assert not any(blob[640:]);words=list(struct.unpack_from('>160I',blob));assert words==g.bound_blob(*g.payload(f,fn),syms);programs.append(words);links+=1
  assert all(ws==programs[0]for ws in programs[:4])
  with patch.multiple(g,ENTRY=entry,PRESET=preset,ORIENTED=oriented,SPAWN=spawn,SHORT=short,CONSTANTS=constants,DATA=data):
   for c in(g.Case(),g.Case(actor=0),g.Case(transition=1),g.Case(transition=2),g.Case(mutation=1,private=1,phase=8)):
    models=[g.check(ws,c)for ws in programs];assert all(g.state(m)==g.state(models[0])for m in models[1:]);runs+=5
 q=dict(guards=7,guard_corruptions_rejected=rejected,unguarded_word_corruptions_visible=visible,all_binding_corruptions_visible=bindings,guard_binding_corruptions_rejected=2,raw_binding_positions_pinned=25,old_guard_prefix_unchanged=True,GNU_links=links,guest_rebase_runs=runs,oversized=overflow,source_installed=target_packet.installed(),matching_credit=0);(o/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
