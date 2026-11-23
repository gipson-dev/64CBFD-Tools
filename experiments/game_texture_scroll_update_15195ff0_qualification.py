"""Fail-closed instruction/binding guards, symbolic controls and GNU rebases."""
import copy,json,struct,subprocess,sys
from tools.experiments import game_texture_scroll_update_15195ff0_match as p
from tools.tests import game_texture_scroll_update_15195ff0_guest as g
from tools.tests.game_texture_scroll_update_15195ff0_symbolic import proof
from tools.tests.game_texture_scroll_update_15195ff0_normalizer import normalize
from tools.experiments.game_texture_registration_15195dd4_objects import assemble
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_remaining_donor_candidates import function_span
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
r,o=p.ROOT,p.OUT;NAME=p.FUNCTION
def assembly(data,refs):
 text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,n in refs.get(i*4,[]):text+=f'.reloc ., {kind}, {n}\n'
  text+=f'.word 0x{w:08X}\n'
 return text+'.size '+NAME+',.-'+NAME+'\n'
def main():
 data,refs=payload(o/'selected-final/candidate.o',NAME);truth=payload(o/'original-target.o',NAME);assert normalize(data,refs)==truth
 where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(data,refs),target)
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[s for s in rows if s.split(',')[1:3]==['generated_1C2C60',NAME]];assert len(selected)==1;layout=where/'layout.csv';layout.write_text(rows[0]+'\n'+selected[0]+'\n');guard=where/'guards.csv';guard.write_bytes((o/'private-guards.csv').read_bytes().splitlines(keepends=True)[0]+(o/'guard-suffix.csv').read_bytes())
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,'generated_1C2C60',word_patches_path=guard),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename='generated_1C2C60',word_patches_path=guard)];outputs=[];controls=0
 for i,emit in enumerate(emitters):
  f=where/f'padded-{i}.o';assemble(emit(target),f);assert payload(f,NAME)==truth;outputs.append(f)
 # Exercise every expected source word and every source relocation site.
 for at in range(0,len(data),4):
  bad=bytearray(data);bad[at+3]^=4;f=where/'corrupt-word.o';assemble(assembly(bad,refs),f)
  try:normalize(bad,refs)
  except ValueError:pass
  else:raise AssertionError('Normalizer accepted changed source word')
  for emit in emitters:
   try:emit(f)
   except ValueError:controls+=1
   else:raise AssertionError(('Padder accepted changed source word',at))
 for at in refs:
  br=copy.deepcopy(refs);kind,n=br[at][0];br[at]=[(kind,n+'_wrong')]+br[at][1:];f=where/'corrupt-binding.o';assemble(assembly(data,br),f)
  try:normalize(data,br)
  except ValueError:pass
  else:raise AssertionError('Normalizer accepted changed source binding')
  for emit in emitters:
   try:emit(f)
   except ValueError:controls+=1
   else:raise AssertionError(('Padder accepted changed binding',at))
 oversized=where/'oversized.o';assemble(assembly(data+bytes.fromhex('24420001')*8,refs),oversized)
 try:emitters[0](oversized)
 except ValueError as e:assert NAME in str(e)and'stale overflow word patch'in str(e)
 else:raise AssertionError('Generic padder accepted oversized guarded insertion body')
 try:emitters[1](oversized)
 except ValueError as e:assert NAME in str(e)
 else:raise AssertionError('Generated padder accepted oversized normalized body')
 names={n for v in refs.values()for _,n in v};links=0
 for number,(entry,shift)in enumerate(((g.ENTRY,0),(g.ENTRY+0x10000,0x8000),(g.ENTRY-0x10000,-0x1000),(0x25195AA8,0x10000000))):
  symbols={n:(g.S[n]+shift*(index+1))&0xffffffff for index,n in enumerate(sorted(names))};blobs=[]
  for i,f in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{v:X}'for n,v in symbols.items()],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   text=sections(elf)['.text'][1];assert not any(text[808:]);words=list(struct.unpack('>202I',text[:808]));assert words==g.bound_blob(*payload(f,NAME),symbols);blobs.append(words);links+=1
  assert len({tuple(ws)for ws in blobs})==1
 # Effective semantic controls also exercise the symbolic proof's rejection.
 raw=g.bound_blob(data,refs,g.S);retail=g.bound_blob(*truth,g.S);symbolic_controls=0
 for index in(7,17,19,37,48,51,76,77,79,81,90,93,102,107,108,112,114,117,123,128,136,137,146,163,164,169,173,174,180,188,189):
  bad=raw[:];bad[index]=0
  try:proof(False,[bad,retail])
  except(AssertionError,IndexError,KeyError,StopIteration):symbolic_controls+=1
  else:raise AssertionError(('Symbolic comparator accepted semantic mutation',index))
 for index in(105,106,112,142):
  bad=retail[:];bad[index]=0
  try:proof(False,[raw,bad])
  except(AssertionError,IndexError,KeyError,StopIteration):symbolic_controls+=1
  else:raise AssertionError(('Role comparator accepted missing address operation',index))
 report=dict(guards=197,insertions=5,omissions=0,effective_word_and_binding_guard_rejections=controls,source_words_covered=197,source_binding_sites_covered=len(refs),generated_oversized_rejection=1,generic_oversized_trampoline_guard_rejection=1,GNU_target_links=links,independent_global_arrangements=4,effective_symbolic_controls=symbolic_controls,source_installed=p.installed(),matching_credit=0);(o/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
