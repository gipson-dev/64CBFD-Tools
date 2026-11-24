"""Independent semantic proof, effective corruptions and GNU symbol rebases."""
import json,struct,subprocess,sys
from tools.experiments import game_actor_state_motion_150b12fc_match as p
from tools.tests import game_actor_state_motion_150b12fc_guest as g
from tools.tests import game_actor_state_motion_150b12fc_symbolic as symbolic
from tools.tests.game_actor_state_motion_150b12fc_normalizer import normalize
from tools.experiments.game_actor_state_motion_150b12fc_objects import assemble
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
 m=symbolic
 words=list(struct.unpack('>98I',raw[0]));rows=[]
 def negative(name,i,w):
  changed=words[:];assert w!=changed[i];changed[i]=w
  try:m.proof((struct.pack('>98I',*changed),raw[1]),truth,False)
  except AssertionError as e:assert isinstance(e.args[0],tuple)and e.args[0][0]=='Independent state-motion relation differs',(name,e);rows.append(dict(name=name,word=i,rejected_by_public_or_call_or_FP_observation=True))
  else:raise AssertionError(('Ineffective proof control',name))
 negative('counter-value',5,words[5]+1);negative('signed-row-height',17,words[17]|(4<<26));negative('current-angle-field',35,words[35]+2);negative('wrapped-angle-scale',41,words[41]-(1<<6));negative('upper-clamp-bound',36,words[36]-0x20);negative('lower-clamp-bound',48,words[48]-0x20);negative('smooth-product-to-add',71,words[71]&~3);negative('facing-offset',72,words[72]-0x2000);negative('final-predicate-polarity',88,words[88]^(1<<26))
 changed=words[:];assert changed[4]>>26==37;changed[4]=(changed[4]&0x03ffffff)|(33<<26);m.proof((struct.pack('>98I',*changed),raw[1]),truth,False)
 def rename(w):
  op=w>>26;rs=w>>21&31;fn=w&63;fields=(16,)if op in(49,57)else(11,)if op==17 and rs in(0,4)else(11,6)if op==17 and rs==20 else(16,11)if op==17 and rs==16 and fn==60 else(11,6)if op==17 and rs==16 and fn==6 else(16,11,6)if op==17 and rs==16 else()
  for shift in fields:
   v=w>>shift&31
   if v in(12,14):w=(w&~(31<<shift))|((26-v)<<shift)
  return w
 changed=struct.pack('>98I',*(rename(w)for w in words));assert changed!=raw[0];m.proof((changed,raw[1]),truth,False)
 return dict(negative_controls=rows,first_LHU_to_LH_equivalence_accepted=True,FP12_FP14_alpha_rename_accepted=True,unsupported_instruction_failures_counted=False)

def main():
 raw=payload(o/'selected-final/candidate.o',NAME);truth=payload(o/'original-target.o',NAME);assert normalize(*raw)==truth;proof=symbolic.proof(raw,truth);proof_control=proof_controls(raw,truth)
 where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(*raw),target);guard=o/'private-guards.csv'
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[s for s in rows if s.split(',')[1:3]==['generated_DE5A0',NAME]];assert len(selected)==1;layout=where/'layout.csv';layout.write_bytes((rows[0]+'\n'+selected[0]+'\n').encode())
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,'generated_DE5A0',word_patches_path=guard),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename='generated_DE5A0',word_patches_path=guard)];outputs=[];controls=0
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
 globals=[{n:g.S[n]for n in('D_8009F8BC','D_8009F8C0','D_800D2104')},dict(D_8009F8BC=g.S['D_8009F8BC']+0x8000,D_8009F8C0=g.S['D_8009F8C0']+0x8000,D_800D2104=g.S['D_800D2104']+0x7000),dict(D_8009F8BC=0x80a7fffc,D_8009F8C0=0x80a80000,D_800D2104=0x80108004),dict(D_8009F8BC=0x81008000,D_8009F8C0=0x81008004,D_800D2104=0x81018000)]
 for number,(entry,base)in enumerate(((g.ENTRY,0x15001000),(g.ENTRY+0x10000,0x15008000),(g.ENTRY-0x10000,0x15f07000),(0x250b12fc,0x25001000))):
  symbols=g.S.copy();symbols.update(globals[number]);symbols.update({n:base+0x1000*i for i,n in enumerate(callees)});blobs=[]
  for i,f in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_bytes((f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n').encode());elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{symbols[n]:X}'for n in sorted(names)],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr;text=sections(elf)['.text'][1];assert not any(text[392:]);words=list(struct.unpack('>98I',text[:392]));assert words==g.bound_blob(*payload(f,NAME),symbols);blobs.append(words);links+=1
  assert len({tuple(ws)for ws in blobs})==1
  for c in(g.Case(),g.Case(velocity=0x41200000),g.Case(velocity=0xc1200000),g.Case(velocity=0x7fc12345,mutation=63,alias=2),g.Case(result=-1,alias=3),g.Case(old_angle=0x8000,current_angle=0x7fff,velocity=0,mutation=2,phase=8)):
   initial=g.fixture(c,symbols);models=[]
   for ws in[g.bound_blob(*raw,symbols),*blobs]:
    m=g.Oracle(ws,initial,c,entry=entry,s=symbols);m.run();g.check(m,initial,c,symbols);models.append(m);runs+=1
   assert all(g.state(m)==g.state(models[1])for m in models[2:])

 report=dict(independent_symbolic_proof=proof,proof_controls=proof_control,both_padders_byte_exact=True,guards=98,insertions=0,omissions=0,effective_failclosed_word_or_binding_controls=controls,source_words_covered=98,source_binding_sites_covered=11,GNU_target_links=links,independent_code_callee_and_global_arrangements=4,guest_rebase_runs=runs,source_installed=p.installed(),matching_credit=0)
 (o/'qualification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in report.items()if k!='independent_symbolic_proof'}),flush=True);return report
if __name__=='__main__':main()
