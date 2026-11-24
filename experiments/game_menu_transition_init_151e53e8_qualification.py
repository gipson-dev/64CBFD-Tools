"""Direct identity, effective corruption controls and independent GNU relocation."""
import json,struct,subprocess,sys
from tools.experiments import game_menu_transition_init_151e53e8_match as p
from tools.tests import game_menu_transition_init_151e53e8_guest as g
from tools.experiments.game_texture_registration_15195dd4_objects import assemble
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
r,o=p.ROOT,p.OUT;NAME=p.FUNCTION

def assembly(data,refs):
 text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,n in refs.get(i*4,[]):text+=f'.reloc ., {kind}, {n}\n'
  text+=f'.word 0x{word:08X}\n'
 return text+'.size '+NAME+',.-'+NAME+'\n'

def main():
 from tools.tests.game_menu_transition_init_151e53e8_normalizer import normalize
 data,refs=payload(o/'selected-final/candidate.o',NAME);truth=payload(o/'original-target.o',NAME)
 assert len(data)==404 and (data,refs)==truth and len(refs)==37
 assert normalize(data,refs)==truth
 assert p.MANIFEST['guard_count']==0 and (o/'private-guards.csv').read_bytes()==(o/'baseline/conker/retail_word_patches.us.csv').read_bytes()
 where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(data,refs),target)
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[s for s in rows if s.split(',')[1:3]==['generated_20AE20',NAME]];assert len(selected)==1
 layout=where/'layout.csv';layout.write_text(rows[0]+'\n'+selected[0]+'\n')
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,'generated_20AE20'),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename='generated_20AE20')];outputs=[];controls=0
 for i,emit in enumerate(emitters):
  f=where/f'padded-{i}.o';assemble(emit(target),f);assert payload(f,NAME)==truth;outputs.append(f)
 # Direct code has no normalizing guards. Corruption must stay visible rather
 # than being silently repaired; it is not a fail-closed padder rejection.
 for at in range(0,len(data),4):
  bad=bytearray(data);bad[at+3]^=4
  try:normalize(bytes(bad),refs)
  except AssertionError:pass
  else:raise AssertionError('Identity pin accepted a changed word')
  f=where/'corrupt-word.o';assemble(assembly(bad,refs),f)
  for i,emit in enumerate(emitters):
   out=where/f'corrupt-word-{i}.o';assemble(emit(f),out);assert payload(out,NAME)!=truth;controls+=1
 for at in refs:
  br={i:list(v)for i,v in refs.items()};kind,n=br[at][0];br[at]=[(kind,n+'_wrong')]+br[at][1:]
  try:normalize(data,br)
  except AssertionError:pass
  else:raise AssertionError('Identity pin accepted a changed binding')
  f=where/'corrupt-binding.o';assemble(assembly(data,br),f)
  for i,emit in enumerate(emitters):
   out=where/f'corrupt-binding-{i}.o';assemble(emit(f),out);assert payload(out,NAME)!=truth;controls+=1
 oversized=where/'oversized.o';assemble(assembly(data+struct.pack('>I',0x24420001),refs),oversized);text=emitters[0](oversized);assert '__retail_overflow_'+NAME in text
 out=where/'generic-overflow.o';assemble(text,out);assert payload(out,NAME)!=truth
 try:emitters[1](oversized)
 except ValueError as error:assert NAME in str(error)
 else:raise AssertionError('Generated padder accepted an oversized body')
 names={n for v in refs.values()for _,n in v};callees=sorted({n for v in refs.values()for kind,n in v if kind=='R_MIPS_26'});links=runs=0
 for number,(entry,base,shift)in enumerate(((g.ENTRY,0x15001000,0),(g.ENTRY+0x10000,0x15008000,0x8000),(g.ENTRY-0x10000,0x15f07000,-0x1000),(0x251e53e8,0x25001000,0x10000000))):
  symbols=g.S.copy();symbols.update({n:(g.S[n]+shift)&0xffffffff for n in names if n not in callees});symbols.update({n:base+0x1000*i for i,n in enumerate(sorted(set(callees)|{'func_151DDBA0'}))});blobs=[]
  for i,f in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf')
   q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{symbols[n]:X}'for n in sorted(names)],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   text=sections(elf)['.text'][1];assert not any(text[404:]);words=list(struct.unpack('>101I',text[:404]));assert words==g.bound_blob(*payload(f,NAME),symbols);blobs.append(words);links+=1
  assert len({tuple(ws)for ws in blobs})==1
  for c in(g.Case(),g.Case(gate=0),g.Case(count=-128),g.Case(defer=256),g.Case(alias=1),g.Case(alias=2)):
   initial=g.fixture(c,symbols);models=[]
   for ws in[g.bound_blob(data,refs,symbols),*blobs]:
    m=g.Oracle(ws,initial,c,entry=entry,s=symbols);m.run();g.check(m,initial,c,symbols);models.append(m);runs+=1
   assert all(g.state(m)==g.state(models[0])for m in models[1:])
 report=dict(raw_is_exact_retail_words_and_bindings=True,both_padders_byte_exact=True,guards=0,insertions=0,omissions=0,effective_wrong_word_or_binding_controls=controls,source_words_covered=101,source_binding_sites_covered=37,generated_oversized_rejection=1,generic_overflow_preserved_but_unmatched=1,GNU_target_links=links,independent_code_callee_and_global_arrangements=4,guest_rebase_runs=runs,additional_helper_implementation_claim=False,source_installed=p.installed(),matching_credit=0)
 (o/'qualification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
