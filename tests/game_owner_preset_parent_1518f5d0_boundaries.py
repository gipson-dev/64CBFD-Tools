"""Every direct word and binding remains visible across both scoped padders."""
from pathlib import Path
from unittest.mock import patch
import json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_owner_preset_parent_1518f5d0_match as target_packet
o=target_packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_owner_preset_parent_1518f5d0_guest as g
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_local_vector_transform_15117da4_match import assembly
r=target_packet.ROOT;fn='func_1518F5D0';filename='generated_1BA1D0'
def assemble(s,path):
 f=path.with_suffix('.s');f.write_text(s);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def main():
 raw,refs=g.payload(o/'selected-owner.o',fn);truth=g.payload(o/'original-target.o',fn);assert(raw,refs)==truth and len(refs)==7;w=o/'boundaries';w.mkdir(exist_ok=True);obj=w/'raw.o';assemble(assembly(raw,refs,fn),obj)
 childfn='func_1519021C';full=(o/'baseline/conker/asm/1BA1D0.s').read_text();childasm='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+childfn+'\n'+full.split('glabel '+childfn+'\n',1)[1].split('endlabel '+childfn,1)[0]+'endlabel '+childfn+'\n.size '+childfn+',.-'+childfn+'\n';assemble(childasm,w/'child-original.o')
 lines=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[line for line in lines if line.split(',')[1:3]==[filename,fn]];assert len(rows)==1;layout=w/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');full=o/'baseline/conker/retail_word_patches.us.csv';assert fn not in full.read_text();guards=w/'guards.csv';guards.write_text(full.read_text().splitlines()[0]+'\n');assert not pg.load_word_patches(guards,filename)
 emitters=[lambda p:pc.emit_padded_assembly(p,layout,filename,word_patches_path=guards),lambda p:pg.emit_padded_assembly(p,o/'original-target.s',filename=filename,word_patches_path=guards)];outs=[]
 for i,emit in enumerate(emitters):
  p=w/f'padded-{i}.o';assemble(emit(obj),p);assert g.payload(p,fn)==truth;outs.append(p)
 visible=bindings=0
 for at in range(0,500,4):
  changed=bytearray(raw);changed[at+3]^=4;p=w/'changed.o';assemble(assembly(changed,refs,fn),p)
  for i,emit in enumerate(emitters):
   result=w/f'visible-{i}.o';assemble(emit(p),result);assert g.payload(result,fn)!=truth;visible+=1
 for at in refs:
  changed={k:list(v)for k,v in refs.items()};kind,name=changed[at][0];changed[at]=[(kind,name+'_wrong')];p=w/'wrong-binding.o';assemble(assembly(raw,changed,fn),p)
  for i,emit in enumerate(emitters):
   result=w/f'binding-visible-{i}.o';assemble(emit(p),result);assert g.payload(result,fn)!=truth;bindings+=1
 p=w/'oversize.o';assemble(assembly(raw+bytes(16),refs,fn),p);overflow=[]
 for emit in emitters:
  try:s=emit(p)
  except ValueError:overflow.append('rejected')
  else:assert'__retail_overflow_'+fn in s;overflow.append('visible overflow')
 links=runs=0
 for group,(entry,low)in enumerate(((g.ENTRY,0),(0x2518F5D0,0x7FF8),(0x3518F5D0,0x8000),(0x4518F5D0,0xFFF8))):
  region=entry&0xF0000000;copy=region+0x22EC0;factory=region+0x51602C0;parentalloc=region+0x51D2F00;resource=region+0x51D2AB0;event=region+0xFA64;callback=region+0x5180000+low;childentry=region+0x519021C;tables=tuple(0x80210000+low+0x100*i for i in range(3));scalar=0x80320000+low;syms=dict(func_151D2F00=parentalloc,func_1519021C=childentry,func_151D2AB0=resource,func_1000FA64=event,func_1518E298=callback,memcpy=copy);programs=[]
  for i,p in enumerate((o/'normalized-target.o',*outs,o/'original-target.o',obj)):
   ld=w/f'{group}-{i}.ld';ld.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=ld.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(ld),'-e',fn,*[f'--defsym={n}=0x{v:X}'for n,v in syms.items()],'-o',str(elf),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr;blob=sections(elf)['.text'][1];assert not any(blob[500:]);words=list(struct.unpack_from('>125I',blob));assert words==g.bound_blob(*g.payload(p,fn),syms);programs.append(words);links+=1
  assert all(words==programs[0]for words in programs)
  with patch.multiple(g,ENTRY=entry,COPY=copy,ALLOC=parentalloc,RESOURCE=resource,EVENT=event,CALLBACK=callback),patch.multiple(g.child,ENTRY=childentry,COPY=copy,FACTORY=factory,TABLES=tables,SCALAR=scalar):
   childprogram=g.bound_blob(*g.payload(w/'child-original.o','func_1519021C'),g.child.symbols())
   with patch.object(g,'child_words',lambda:childprogram):
    for c in(g.Case(),g.Case(allocated=0),g.Case(main_alias=1,parent_mutation=1,mutation=1),g.Case(preset=255),g.Case(preset=24,rm=2)):
     models=[g.check(words,c)for words in programs];assert all(g.state(m)==g.state(models[0])for m in models[1:]);runs+=5
 q=dict(guards=0,all_word_corruptions_visible=visible,all_binding_corruptions_visible=bindings,raw_binding_positions_pinned=7,entire_guard_manifest_unchanged=True,GNU_links=links,guest_rebase_runs=runs,all_parent_child_services_callback_tables_scalar_rebased=True,no_alignment_tail=True,oversized=overflow,source_installed=target_packet.installed(),matching_credit=0);(o/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
