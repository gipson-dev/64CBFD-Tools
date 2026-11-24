"""Independent finite-path proof, effective corruptions and GNU rebases."""
import json,struct,subprocess,sys
from tools.experiments import game_effect_contact_1515a78c_match as p
from tools.tests import game_effect_contact_1515a78c_guest as g
from tools.tests import game_effect_contact_1515a78c_symbolic as symbolic
from tools.tests.game_effect_contact_1515a78c_normalizer import normalize
from tools.experiments.game_effect_contact_1515a78c_objects import assemble
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
def proof_controls(raw,truth):
 words=list(struct.unpack('>98I',raw[0]));rows=[]
 def negative(name,i,w):
  changed=words[:];assert changed[i]!=w;changed[i]=w
  try:symbolic.proof((struct.pack('>98I',*changed),raw[1]),truth,False)
  except AssertionError as e:
   assert isinstance(e.args[0],tuple)and e.args[0][0]in('branch predicates','Independent effect-placement relation differs'),(name,e)
   rows.append(dict(name=name,word=i,rejected_by_predicate_or_public_or_return_observation=True))
  else:raise AssertionError(('Ineffective proof control',name))
 negative('inclusive-vertical-gate',13,words[13]+2)
 negative('wrong-early-return',18,words[18]+1)
 negative('wrong-x-coordinate',16,words[16]+4)
 negative('wrong-position-axis',26,words[26]+4)
 negative('wrong-z-offset',28,words[28]-4)
 negative('wrong-rate',32,words[32]-4)
 negative('reverse-inside-result',39,words[39]^(1<<26))
 negative('wrong-query-threshold',44,words[44]+4)
 negative('wrong-query-output',46,words[46]+4)
 negative('reverse-query-result',47,words[47]^(1<<26))
 negative('lost-query-result-clear',50,words[50]-1)
 negative('strict-cached-height',54,words[54]-2)
 negative('inclusive-random',67,words[67]+2)
 negative('wrong-state-byte',71,words[71]-1)
 negative('wrong-state-code',72,words[72]+1)
 negative('wrong-center',79,words[79]+8)
 negative('narrow-selector',85,words[85]-0x80)
 negative('wrong-kind-byte',80,words[80]+1)
 negative('wrong-owner-byte',88,words[88]+1)
 def rename(w):
  op=w>>26;rs=w>>21&31
  fields=(21,16,11)if op==0 and w else(16,)if op==15 else(21,)if op in(49,57)else(16,)if op==17 and rs in(0,4)else(21,16)if op in(4,5,9,12,20,21,35,36,40,43)else()
  for shift in fields:
   v=w>>shift&31
   if v in(8,9):w=(w&~(31<<shift))|((17-v)<<shift)
  return w
 changed=struct.pack('>98I',*(rename(w)for w in words));assert changed!=raw[0];symbolic.proof((changed,raw[1]),truth,False)
 changed=words[:]
 for i,w in enumerate(words):
  if w>>26 in(35,43)and w>>21&31==29 and w&65535==48:changed[i]=(w&0xffff0000)|56
  if w>>26 in(36,40)and w>>21&31==29 and w&65535==79:changed[i]=(w&0xffff0000)|78
 assert changed!=words;symbolic.proof((struct.pack('>98I',*changed),raw[1]),truth,False)
 return dict(negative_controls=rows,complete_T0_T1_alpha_rename_accepted=True,independent_result_private_homes_move_accepted=True,unsupported_instruction_failures_counted=False)
def main():
 raw=payload(o/'selected-final/candidate.o',NAME);truth=payload(o/'original-target.o',NAME);assert normalize(*raw)==truth;proof=symbolic.proof(raw,truth);proof_control=proof_controls(raw,truth)
 where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(*raw),target);guard=where/'target-guards.csv';guard.write_bytes((o/'private-guards.csv').read_bytes().splitlines(keepends=True)[0]+(o/'guard-suffix.csv').read_bytes())
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[s for s in rows if s.split(',')[1:3]==['generated_185560',NAME]];assert len(selected)==1;layout=where/'layout.csv';layout.write_bytes((rows[0]+'\n'+selected[0]+'\n').encode())
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,'generated_185560',word_patches_path=guard),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename='generated_185560',word_patches_path=guard)];outputs=[];controls=0
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
 globals=[g.S[g.GLOBALS[0]],0x80a7fffc,0x80a88000,0x81018000]
 for number,(entry,base)in enumerate(((g.ENTRY,0x15001000),(g.ENTRY+0x10000,0x15008000),(g.ENTRY-0x10000,0x15f07000),(0x2515a78c,0x25001000))):
  symbols=g.S.copy();symbols.update({n:globals[number]+4*i for i,n in enumerate(g.GLOBALS)});symbols.update({n:base+0x1000*i for i,n in enumerate(callees)});blobs=[]
  for i,f in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_bytes((f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n').encode());elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{symbols[n]:X}'for n in sorted(names)],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr;text=sections(elf)['.text'][1];assert not any(text[404:]);words=list(struct.unpack('>101I',text[:404]));assert words==g.bound_blob(*payload(f,NAME),symbols);blobs.append(words);links+=1
  assert len({tuple(ws)for ws in blobs})==1
  for c in(g.Case(),g.Case(vertical=0xbf800000),g.Case(inside=0),g.Case(hit=0),g.Case(rate=0,random=0x7fc00001),g.Case(mutation=63,alias=1,phase=8)):
   initial=g.fixture(c,symbols);models=[]
   for ws in[g.bound_blob(*raw,symbols),*blobs]:
    m=g.Oracle(ws,initial,c,entry=entry,s=symbols);m.run();g.check(m,initial,c,symbols);models.append(m);runs+=1
   assert all(g.state(m)==g.state(models[1])for m in models[2:])
 report=dict(independent_symbolic_proof=proof,proof_controls=proof_control,both_padders_byte_exact=True,guards=98,insertions=3,omissions=0,effective_failclosed_word_or_binding_controls=controls,source_words_covered=98,source_binding_sites_covered=len(raw[1]),GNU_target_links=links,independent_code_callee_and_global_arrangements=4,guest_rebase_runs=runs,source_installed=p.installed(),matching_credit=0)
 (o/'qualification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in report.items()if k!='independent_symbolic_proof'}),flush=True);return report
if __name__=='__main__':main()
