"""Fail-closed instruction/binding guards, symbolic controls and GNU rebases."""
import copy,json,struct,subprocess,sys
from tools.experiments import game_group_record_pairs_15022024_match as p
from tools.tests import game_group_record_pairs_15022024_guest as g
from tools.tests.game_group_record_pairs_15022024_symbolic import proof
from tools.tests.game_group_record_pairs_15022024_normalizer import normalize
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
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[s for s in rows if s.split(',')[1:3]==['generated_49D30',NAME]];assert len(selected)==1;layout=where/'layout.csv';layout.write_text(rows[0]+'\n'+selected[0]+'\n');guard=where/'guards.csv';guard.write_bytes((o/'private-guards.csv').read_bytes().splitlines(keepends=True)[0]+(o/'guard-suffix.csv').read_bytes())
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,'generated_49D30',word_patches_path=guard),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename='generated_49D30',word_patches_path=guard)];outputs=[];controls=0
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
 except ValueError as e:assert NAME in str(e)and'cannot insert'in str(e)
 else:raise AssertionError('Generic padder accepted oversized guarded insertion body')
 try:emitters[1](oversized)
 except ValueError as e:assert NAME in str(e)
 else:raise AssertionError('Generated padder accepted oversized normalized body')
 names={n for v in refs.values()for _,n in v};links=0
 for number,(entry,shift)in enumerate(((g.ENTRY,0),(g.ENTRY+0x10000,0x8000),(g.ENTRY-0x10000,-0x1000),(0x25022024,0x10000000))):
  symbols={n:(g.S[n]+shift)&0xffffffff for n in names};blobs=[]
  for i,f in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{v:X}'for n,v in symbols.items()],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   text=sections(elf)['.text'][1];assert not any(text[364:]);words=list(struct.unpack('>91I',text[:364]));assert words==g.bound_blob(*payload(f,NAME),symbols);blobs.append(words);links+=1
  assert len({tuple(ws)for ws in blobs})==1
 # Effective semantic controls also exercise the symbolic proof's rejection.
 raw=g.bound_blob(data,refs,g.S);retail=g.bound_blob(*truth,g.S);symbolic_controls=0
 for index in(2,5,13,27,34,41,47,53,64,74,80,82):
  bad=raw[:];bad[index]^=1<<21
  try:proof(bad,retail,False)
  except(AssertionError,IndexError,KeyError):symbolic_controls+=1
  else:raise AssertionError(('Symbolic comparator accepted semantic mutation',index))
 source=p.MANIFEST['selected_source'];a,b=function_span(source,NAME);body=source[a:b];changed=body.replace(' != missing',' != D_80096A14');assert changed!=body;obj,_=p.compile_owner(r,where,source[:a]+changed+source[b:],'uncached-sentinel');bad=g.bound_blob(*payload(obj,NAME),g.S)
 for c in g.cases():
  initial=g.fixture(c);expected,answer=g.reference(initial,c);m=g.Oracle(bad,initial,c);m.run()
  if g.public(m.memory,c)!=g.public(expected,c)or m.r[2]!=answer:break
 else:raise AssertionError('Uncached-sentinel control ineffective')
 report=dict(guards=87,insertions=6,omissions=2,effective_word_and_binding_guard_rejections=controls,source_words_covered=87,source_binding_sites_covered=len(refs),generated_oversized_rejection=1,generic_oversized_insertion_rejection=1,GNU_target_links=links,independent_global_arrangements=4,effective_symbolic_controls=symbolic_controls,effective_uncached_sentinel_guest_control=True,source_installed=p.installed(),matching_credit=0);(o/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
