"""Fail-closed instruction/binding guards, symbolic controls and GNU rebases."""
import copy,json,struct,subprocess,sys
from tools.experiments import game_resource_cache_sweep_15114a1c_match as p
from tools.tests import game_resource_cache_sweep_15114a1c_guest as g
from tools.tests.game_resource_cache_sweep_15114a1c_symbolic import proof
from tools.tests.game_resource_cache_sweep_15114a1c_normalizer import normalize
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
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[s for s in rows if s.split(',')[1:3]==['generated_13D350',NAME]];assert len(selected)==1;layout=where/'layout.csv';layout.write_text(rows[0]+'\n'+selected[0]+'\n');guard=where/'guards.csv';guard.write_bytes((o/'private-guards.csv').read_bytes().splitlines(keepends=True)[0]+(o/'guard-suffix.csv').read_bytes())
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,'generated_13D350',word_patches_path=guard),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename='generated_13D350',word_patches_path=guard)];outputs=[];controls=0
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
 except ValueError as e:assert NAME in str(e)and('cannot insert'in str(e)or'stale overflow word patch'in str(e))
 else:raise AssertionError('Generic padder accepted oversized guarded insertion body')
 try:emitters[1](oversized)
 except ValueError as e:assert NAME in str(e)
 else:raise AssertionError('Generated padder accepted oversized normalized body')
 names={n for v in refs.values()for _,n in v};links=0;guest_runs=0
 for number,(entry,shift)in enumerate(((g.ENTRY,0),(g.ENTRY+0x10000,0x8000),(g.ENTRY-0x10000,-0x1000),(0x25114A1C,0x10000000))):
  symbols={n:(g.S[n]+shift)&0xffffffff for n in names};blobs=[]
  for i,f in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{v:X}'for n,v in symbols.items()],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   text=sections(elf)['.text'][1];assert not any(text[376:]);words=list(struct.unpack('>94I',text[:376]));assert words==g.bound_blob(*payload(f,NAME),symbols);blobs.append(words);links+=1
  assert len({tuple(ws)for ws in blobs})==1
  for c in(g.Case(1024,8,0),g.Case(1031,8,7),g.Case(1042,8,15),g.Case(4,-1,3)):
   initial=g.fixture(c,symbols);models=[]
   for ws in[g.bound_blob(data,refs,symbols),*blobs]:
    m=g.Oracle(ws,initial,c,entry=entry,s=symbols);m.run();g.check(m,initial,c,symbols);models.append(m);guest_runs+=1
   assert g.state(models[1])==g.state(models[2])==g.state(models[3])

 # Independent symbolic checks reject changed public fields, masks, calls,
 # writes and loop progress, while accepting an independent temporary allocation.
 raw=g.bound_blob(data,refs,g.S);retail=g.bound_blob(*truth,g.S);mutations=[]
 for i,w in enumerate(raw):
  op=w>>26;rs=w>>21&31;rt=w>>16&31;imm=w&65535
  if op==36 and imm in(0x70,0x4e):mutations.append((i,w^1))
  if op==12 and imm in(1,128):mutations.append((i,(w&0xffff0000)|(2 if imm==1 else 64)))
  if op==40:mutations.append((i,w^1))
  if op==43 and rs!=29 and rt==0:mutations.append((i,w|(3<<16)))
  if op==9 and rs==rt and imm in(1,160):mutations.append((i,(w&0xffff0000)|(2 if imm==1 else 144)))
  if op==3:mutations.append((i,w^1))
 rejected=[]
 for index,word in mutations:
  bad=raw[:];bad[index]=word
  try:proof(bad,retail,False)
  except(AssertionError,IndexError,KeyError):rejected.append(index)
  else:raise AssertionError(('Symbolic comparator accepted semantic mutation',index))
 assert len(rejected)>=10
 alt=[]
 for word in raw:
  op=word>>26;fields=('rt',)if op==15 else('rs','rt','rd')if op==0 and word else('rs','rt')if op!=3 and word else()
  for field in fields:
   shift={'rs':21,'rt':16,'rd':11}[field];v=word>>shift&31;word=(word&~(31<<shift))|({14:15,15:14}.get(v,v)<<shift)
  alt.append(word)
 proof(alt,retail,False)
 report=dict(guards=92,insertions=2,omissions=0,effective_word_and_binding_guard_rejections=controls,source_words_covered=92,source_binding_sites_covered=len(refs),generated_oversized_rejection=1,generic_oversized_guard_rejection=1,GNU_target_links=links,independent_global_arrangements=4,guest_rebase_runs=guest_runs,effective_symbolic_controls=rejected,independent_temporary_reallocation_accepted=True,source_installed=p.installed(),matching_credit=0);(o/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
