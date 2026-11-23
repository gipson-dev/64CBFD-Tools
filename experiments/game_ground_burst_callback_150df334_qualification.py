"""Independent semantic proof, effective corruptions and GNU symbol rebases."""
import json,struct,subprocess,sys
from tools.experiments import game_ground_burst_callback_150df334_match as p
from tools.tests import game_ground_burst_callback_150df334_guest as g
from tools.tests import game_ground_burst_callback_150df334_symbolic as symbolic
from tools.tests.game_ground_burst_callback_150df334_normalizer import normalize
from tools.experiments.game_ground_burst_callback_150df334_objects import assemble
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
 words=list(struct.unpack('>98I',raw[0]));rejected=[]
 def mutate(name,i,w):
  copy=words[:];assert w!=copy[i];copy[i]=w
  try:symbolic.proof((struct.pack('>98I',*copy),raw[1]),truth,False)
  except AssertionError as e:assert isinstance(e.args[0],tuple)and e.args[0][0]=='Independent ground-burst relation differs',(name,e);rejected.append(name)
  else:raise AssertionError(('Ineffective semantic control',name))
 first=lambda predicate:next(i for i,w in enumerate(words)if predicate(w))
 mutate('probe-height',6,words[6]-1);i=first(lambda w:w>>26==17 and w>>21&31==16 and w&63==0);mutate('float-add-to-sub',i,words[i]|1)
 i=first(lambda w:w>>26==0 and w&63==27);mutate('signed-lifetime-remainder',i,words[i]^1)
 i=first(lambda w:w==0x9206000c);mutate('channel-byte',i,words[i]+1);i=first(lambda w:w==0x92070001);mutate('context-byte',i,words[i]+1)
 i=first(lambda w:w==0x3c06437a);mutate('radius',i,0x3c0643fa);mutate('owner-coordinate-cache',25,words[25]+4)
 i=max(i for i,w in enumerate(words)if w>>26==0 and w&63==27);mutate('signed-count-remainder',i,words[i]^1)
 def rename(w):
  op=w>>26;fields=(21,16,11)if op==0 else(16,)if op==15 else(16,)if op==17 and w>>21&31 in(0,4)else()if op in(2,3,17)else(21,)if op in(49,57)else(21,16)
  for shift in fields:
   v=w>>shift&31
   if v in(14,15):w=(w&~(31<<shift))|((29-v)<<shift)
  return w
 changed=struct.pack('>98I',*(rename(w)for w in words));assert changed!=raw[0];symbolic.proof((changed,raw[1]),truth,False)
 return dict(negative_controls=rejected,all_rejected_by_observation_mismatch=True,harmless_temporary_register_rename_accepted=True,unsupported_opcode_failures_counted=False)
def main():
 raw=payload(o/'selected-final/candidate.o',NAME);truth=payload(o/'original-target.o',NAME);assert normalize(*raw)==truth;proof=symbolic.proof(raw,truth);proof_control=proof_controls(raw,truth)
 where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(*raw),target);guard=o/'private-guards.csv'
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[s for s in rows if s.split(',')[1:3]==['generated_10C170',NAME]];assert len(selected)==1;layout=where/'layout.csv';layout.write_bytes((rows[0]+'\n'+selected[0]+'\n').encode())
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,'generated_10C170',word_patches_path=guard),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename='generated_10C170',word_patches_path=guard)];outputs=[];controls=0
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
 names={n for v in truth[1].values()for _,n in v};links=runs=0
 for number,(entry,base)in enumerate(((g.ENTRY,0x15001000),(g.ENTRY+0x10000,0x15008000),(g.ENTRY-0x10000,0x15f07000),(0x250df334,0x25001000))):
  symbols=g.S.copy();symbols.update({n:base+0x1000*i for i,n in enumerate(sorted(names))});blobs=[]
  for i,f in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_bytes((f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n').encode());elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{symbols[n]:X}'for n in sorted(names)],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr;text=sections(elf)['.text'][1];assert not any(text[388:]);words=list(struct.unpack('>97I',text[:388]));assert words==g.bound_blob(*payload(f,NAME),symbols);blobs.append(words);links+=1
  assert len({tuple(ws)for ws in blobs})==1
  for c in(g.Case(hit=0),g.Case(),g.Case(hit=-1,mutation=63,ground_mode=0),g.Case(mutation=63,phase=8)):
   initial=g.fixture(c);models=[]
   for label,ws in [('raw',g.bound_blob(*raw,symbols)),*[(str(i),b)for i,b in enumerate(blobs)]]:
    m=g.Oracle(ws,g.fixture(c,label=='raw'),c,entry=entry,s=symbols,raw=label=='raw');m.run();g.check(m,initial,c,symbols);models.append(m);runs+=1
   assert all(g.state(m)==g.state(models[1])for m in models[2:])
 report=dict(independent_symbolic_proof=proof,proof_controls=proof_control,both_padders_byte_exact=True,guards=98,insertions=2,omissions=3,effective_failclosed_word_or_binding_controls=controls,source_words_covered=98,source_binding_sites_covered=5,GNU_target_links=links,independent_code_and_callee_arrangements=4,guest_rebase_runs=runs,source_installed=p.installed(),matching_credit=0)
 (o/'qualification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in report.items()if k!='independent_symbolic_proof'}),flush=True);return report
if __name__=='__main__':main()
