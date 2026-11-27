"""Every classifier word/binding, all nine guards and independent table rebases."""
from tools.experiments import game_owner_action_classifier_1514ca80_match as target_packet
from pathlib import Path
from unittest.mock import patch
import csv,io,json,struct,subprocess,sys
sys.path.insert(0,str(target_packet.ROOT));o=target_packet.OUT;pass
from tools.tests import game_owner_action_classifier_1514ca80_guest as g
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_local_vector_transform_15117da4_match import assembly
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
r=target_packet.ROOT;fn='func_1514CA80';filename='generated_179F30'
def assemble(text,path):
 s=path.with_suffix('.s');s.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(s)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def main():
 raw,refs=payload(o/'selected-owner.o',fn);truth=payload(o/'original-target.o',fn);w=o/'boundaries';w.mkdir(exist_ok=True);obj=w/'raw.o';assemble(assembly(raw,refs,fn),obj)
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[row for row in rows if row.split(',')[1:3]==[filename,fn]];assert len(selected)==1;layout=w/'layout.csv';layout.write_text(rows[0]+'\n'+selected[0]+'\n')
 header=(o/'selected-guards.csv').read_text().splitlines()[0]+'\n';guards=w/'guards.csv';added=list(csv.reader(io.StringIO((o/'guard-additions.csv').read_text())));target=[row for row in added if row[1]==fn];assert len(target)==8 and len(added)==9
 def write_guards(path,values):
  s=io.StringIO(newline='');s.write(header);csv.writer(s,lineterminator='\n').writerows(values);path.write_text(s.getvalue())
 write_guards(guards,target)
 # Independently apply the checked compiler-input bindings for the fifth
 # rebase route; do not count a duplicate padded object as a separate route.
 normalized=bytearray(raw);normalized_refs={k:list(v)for k,v in refs.items()}
 for row in target:
  where=int(row[2],0);assert normalized[where:where+4]==int(row[3],0).to_bytes(4,'big') and normalized_refs[where]==pg.parse_relocation_spec(row[5]);normalized[where:where+4]=int(row[4],0).to_bytes(4,'big');normalized_refs[where]=pg.parse_relocation_spec(row[6])
 assert (bytes(normalized),normalized_refs)==truth
 raw_normalized=w/'raw-normalized.o';assemble(assembly(normalized,normalized_refs,fn),raw_normalized)
 emitters=[lambda p:pc.emit_padded_assembly(p,layout,filename,word_patches_path=guards),lambda p:pg.emit_padded_assembly(p,o/'original-target.s',filename=filename,word_patches_path=guards)]
 outs=[]
 for i,emit in enumerate(emitters):
  p=w/f'padded-{i}.o';assemble(emit(obj),p);assert payload(p,fn)==truth;outs.append(p)
 visible=word_rejected=bindings_visible=binding_rejected=0
 for where in range(0,len(raw),4):
  bad=bytearray(raw);bad[where+3]^=4;p=w/'changed.o';assemble(assembly(bad,refs,fn),p)
  for i,emit in enumerate(emitters):
   try:s=emit(p)
   except ValueError as e:assert 'stale 'in str(e);word_rejected+=1
   else:
    result=w/f'visible-{i}.o';assemble(s,result);assert payload(result,fn)!=truth;visible+=1
 for where in refs:
  bad={k:list(v)for k,v in refs.items()};kind,name=bad[where][0];bad[where]=[(kind,name+'_wrong')];p=w/'wrong-binding.o';assemble(assembly(raw,bad,fn),p)
  for i,emit in enumerate(emitters):
   try:s=emit(p)
   except ValueError as e:assert 'stale 'in str(e);binding_rejected+=1
   else:
    result=w/f'binding-visible-{i}.o';assemble(s,result);assert payload(result,fn)!=truth;bindings_visible+=1
 assert(visible,word_rejected,bindings_visible,binding_rejected)==(862,16,4,16)
 # Qualify the ninth guard on its complete 84-word neighbor in isolation.
 neighbor='func_1514EA1C';nraw,nrefs=payload(o/'selected-owner.o',neighbor);old,orefs=payload(o/'before-owner.o',neighbor);nguards=w/'neighbor-guards.csv';write_guards(nguards,[row for row in added if row[1]==neighbor]);nlayout=w/'neighbor-layout.csv';nrows=[row for row in rows if row.split(',')[1:3]==[filename,neighbor]];assert len(nrows)==1;nlayout.write_text(rows[0]+'\n'+nrows[0]+'\n')
 asm=(o/'baseline/conker/asm/179F30.s').read_text();body=asm.split('glabel '+neighbor+'\n',1)[1].split('endlabel '+neighbor,1)[0];nasm=w/'neighbor.s';nasm.write_text('glabel '+neighbor+'\n'+body+'endlabel '+neighbor+'\n')
 nemitters=[lambda p:pc.emit_padded_assembly(p,nlayout,filename,word_patches_path=nguards,rodata_symbol='jtbl_800A5E20'),lambda p:pg.emit_padded_assembly(p,nasm,filename=filename,word_patches_path=nguards,rodata_symbol='jtbl_800A5E20')];nobj=w/'neighbor-raw.o';assemble(assembly(nraw,nrefs,neighbor),nobj);expected=(old,{k:[(kind,'jtbl_800A5E20'if name=='.rodata'else name)for kind,name in vals]for k,vals in orefs.items()})
 for i,emit in enumerate(nemitters):
  p=w/f'neighbor-padded-{i}.o';assemble(emit(nobj),p);assert payload(p,neighbor)==expected
 neighbor_rejections=0
 for mode in ('word','binding'):
  bad=bytearray(nraw);br={k:list(v)for k,v in nrefs.items()}
  if mode=='word':bad[0x23]^=4
  else:br[0x20]=[('R_MIPS_LO16','.rodata_wrong')]
  p=w/'bad-neighbor.o';assemble(assembly(bad,br,neighbor),p)
  for emit in nemitters:
   try:emit(p)
   except ValueError as e:assert 'stale 'in str(e);neighbor_rejections+=1
   else:raise AssertionError('Ninth guard did not reject '+mode)
 p=w/'oversize.o';assemble(assembly(raw+bytes(16),refs,fn),p);overflow=[];overflow_details=[]
 for emit in emitters:
  try:s=emit(p)
  except ValueError as e:overflow.append('rejected');overflow_details.append(str(e))
  else:assert '__retail_overflow_'+fn in s;overflow.append('visible overflow')
 links=runs=0;tables=g.table_memory();canonical=(0x800A59AC,0x800A5C98,0x800A5D70,0x800A5DBC);sizes=(748,216,76,40)
 for group,entry in enumerate((0x1514CA80,0x2514CA80,0x3514CA80,0x4514CA80)):
  values=[0x800A7FFC+group*0x01000000,0x900A8000+group*0x01000000,0xA00AFFFC+group*0x01000000,0xB00A0000+group*0x01000000];level=0x800B7FFC+group*0x01000000;syms=dict(zip(('jtbl_800A59AC','jtbl_800A5C98','jtbl_800A5D70','jtbl_800A5DBC'),values));syms['D_800BE9F0']=level;memory={}
  for oldbase,newbase,size in zip(canonical,values,sizes):
   for i in range(0,size,4):
    value=g.g.read(tables,oldbase+i);g.g.put(memory,newbase+i,entry+value-0x1514CA80)
  programs=[]
  for i,p in enumerate((o/'normalized-target.o',*outs,o/'original-target.o',raw_normalized)):
   ld=w/f'{group}-{i}.ld';ld.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=ld.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(ld),'-e',fn,*[f'--defsym={n}=0x{v:X}'for n,v in syms.items()],'-o',str(elf),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr;blob=sections(elf)['.text'][1];assert not any(blob[1756:]);words=list(struct.unpack_from('>439I',blob));assert words==bound_blob(*payload(p,fn),syms);programs.append(words);links+=1
  assert all(words==programs[0]for words in programs)
  with patch.multiple(g,ENTRY=entry,LEVEL=level):
   for c in (g.Case(kind=94),g.Case(kind=255,level=-1),g.Case(level=2,who=25),g.Case(level=10,who=15),g.Case(kind=156,level=43),g.Case(level=14,who=1)):
    initial=g.fixture(c);initial.update(memory);args=(g.g.BASE,*g.ALIASES[0]);models=[g.check(words,c,initial,args)for words in programs];assert all(g.g.state(m)==g.g.state(models[0])for m in models[1:]);runs+=5
 q=dict(target_guards=8,neighbor_guards=1,all_word_mutations_visible_or_rejected=visible+word_rejected,word_mutations_visible=visible,guard_word_rejections=word_rejected,all_binding_mutations_visible_or_rejected=bindings_visible+binding_rejected,binding_mutations_visible=bindings_visible,guard_binding_rejections=binding_rejected,ninth_guard_word_and_binding_rejections=neighbor_rejections,GNU_links=links,guest_rebase_runs=runs,five_independent_construction_routes=True,four_tables_and_level_independently_rebased=True,all_original_generated_table_entry_targets_rebased=True,signed_HI16_LO16_carry_boundaries=True,oversized=overflow,oversized_rejection_reasons=overflow_details,source_installed=target_packet.installed(),matching_credit=0);(o/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
