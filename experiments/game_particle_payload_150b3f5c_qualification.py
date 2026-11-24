"""Private-word instruction relation, strict corruptions and independent rebases."""
import json,struct,subprocess,sys
from tools.experiments import game_particle_payload_150b3f5c_match as p
from tools.tests import game_particle_payload_150b3f5c_guest as g
from tools.tests import game_particle_payload_150b3f5c_symbolic as symbolic
from tools.tests.game_particle_payload_150b3f5c_normalizer import normalize
from tools.experiments.game_particle_payload_150b3f5c_objects import assemble
from tools.experiments.game_paired_ground_constructor_match import payload
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
def relation(raw,truth):
 proof=symbolic.proof(raw,truth);words=list(struct.unpack('>99I',raw[0]));controls=[]
 for label,i,delta in [('overlap-store',17,-41),('wrong-FP-source',18,1<<16),('wrong-source-float-field',9,4),('wrong-final-copy-size',94,-4)]:
  bad=words[:];bad[i]+=delta
  try:symbolic.proof((struct.pack('>99I',*bad),raw[1]),truth)
  except AssertionError:controls.append(label)
  else:raise AssertionError(('Ineffective structural control',label))
 proof.update(structural_controls=controls,structural_controls_not_counted_as_semantic_source_controls=True,source_installed=p.installed(),matching_credit=0);(o/'symbolic.json').write_bytes((json.dumps(proof,indent=2)+'\n').encode());return proof


def main():
 raw=payload(o/'selected-final/candidate.o',NAME);truth=payload(o/'original-target.o',NAME);assert normalize(*raw)==truth;p.guards(raw,normalize(*raw));proof=relation(raw,truth)
 where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(*raw),target);guard=where/'target-guards.csv';guard.write_bytes((o/'private-guards.csv').read_bytes().splitlines(keepends=True)[0]+(o/'guard-suffix.csv').read_bytes())
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[s for s in rows if s.split(',')[1:3]==['generated_E1280',NAME]];assert len(selected)==1;layout=where/'layout.csv';layout.write_bytes((rows[0]+'\n'+selected[0]+'\n').encode())
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,'generated_E1280',word_patches_path=guard),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename='generated_E1280',word_patches_path=guard)];outputs=[];controls=0
 for i,emit in enumerate(emitters):
  f=where/f'padded-{i}.o';assemble(emit(target),f);assert payload(f,NAME)==truth;outputs.append(f)
 def reject(data,refs):
  nonlocal controls
  f=where/'corrupt.o';assemble(assembly(data,refs),f)
  for emit in emitters:
   try:emit(f)
   except ValueError as error:assert NAME in str(error);controls+=1
   else:raise AssertionError('Strict guard accepted changed source or binding')
 for at in range(0,len(raw[0]),4):
  data=bytearray(raw[0]);data[at+3]^=4;reject(data,raw[1])
 for at in raw[1]:
  refs={i:list(v)for i,v in raw[1].items()};kind,name=refs[at][0];refs[at]=[(kind,name+'_wrong')]+refs[at][1:];reject(raw[0],refs)
 names={n for v in truth[1].values()for _,n in v};callees=sorted(n for v in truth[1].values()for kind,n in v if kind=='R_MIPS_26');links=runs=0
 for number,(entry,callee_base,shift)in enumerate(((g.ENTRY,0x15001000,0),(g.ENTRY+0x10000,0x15008000,0x18000),(g.ENTRY-0x10000,0x15f07000,0x28000),(0x250b3f5c,0x25001000,0x1000000))):
  symbols=g.S.copy();symbols.update({n:(g.S[n]+shift)&0xffffffff for n in names if n not in callees});symbols.update({n:callee_base+0x1000*i for i,n in enumerate(callees)});blobs=[]
  for i,f in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_bytes((f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n').encode());elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{symbols[n]:X}'for n in sorted(names)],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr;text=sections(elf)['.text'][1];assert not any(text[396:]);words=list(struct.unpack('>99I',text[:396]));assert words==g.bound_blob(*payload(f,NAME),symbols);blobs.append(words);links+=1
  assert len({tuple(ws)for ws in blobs})==1
  for c in(g.Case(),g.Case(success=0),g.Case(mode=1),g.Case(mode=3),g.Case(mode=4),g.Case(alias=1,shape=3)):
   initial=g.fixture(c,symbols);models=[]
   for ws in[g.bound_blob(*raw,symbols),*blobs]:
    m=g.Oracle(ws,initial,c,entry=entry,s=symbols);m.run();g.check(m,initial,c,symbols);models.append(m);runs+=1
   assert all(g.state(m,i==0)==g.state(models[-1])for i,m in enumerate(models))
 report=dict(independent_instruction_relation=proof,both_padders_byte_exact=True,guards=99,identity_guards=97,insertions=0,omissions=0,effective_failclosed_word_or_binding_controls=controls,source_words_covered=99,source_binding_sites_covered=len(raw[1]),GNU_target_links=links,independent_code_callee_and_global_arrangements=4,guest_rebase_runs=runs,source_installed=p.installed(),matching_credit=0)
 (o/'qualification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in report.items()if k!='independent_instruction_relation'}),flush=True);return report
if __name__=='__main__':main()
