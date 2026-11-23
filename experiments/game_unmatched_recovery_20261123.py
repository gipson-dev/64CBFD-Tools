"""Reproduce two uncredited C recoveries without changing production sources."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_suffix('.json').read_text());OUT=ROOT/MANIFEST['build']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
 assert sha(ROOT/'conker/build/conker.us.elf')==MANIFEST['production_ELF_sha256']
 assert sha(ROOT/'conker/conker.us.bin')==MANIFEST['ROM_sha256']and sha(ROOT/'conker/retail_word_patches.us.csv')==MANIFEST['guards_sha256']
 for row in MANIFEST['targets']:
  assert sha(ROOT/row['source'])==row['before_source_sha256']and sha(ROOT/row['asm'])==row['original_asm_sha256']
 assert MANIFEST['source_installed']is False and MANIFEST['matching_credit']==0
 OUT.mkdir(exist_ok=True)
def screen():
 from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 from tools.experiments.game_paired_ground_constructor_match import payload
 prepare();reports=[];rom=(ROOT/'conker/conker.us.bin').read_bytes()
 for row in MANIFEST['targets']:
  where=OUT/row['function'];where.mkdir(exist_ok=True);selected=where/'selected-final';selected.mkdir(exist_ok=True);old=(ROOT/row['source']).read_text();a,b=function_span(old,row['function']);source=old[:a]+row['declarations']+'\n'+row['body']+old[b:];before,bd=compile_owner(ROOT,selected,old,'before');after,ad=compile_owner(ROOT,selected,source,'candidate');text,functions=link_owner(ROOT,selected,after,row['source'].removeprefix('conker/src/').removesuffix('.c'));f=functions[row['function']];words=struct.unpack('>'+str(f['size']//4)+'I',text[f['value']:f['value']+f['size']]);start,end=row['ROM'];truth=struct.unpack('>'+str(row['original_words'])+'I',rom[start:end]);q=dict(words=len(words),frame=(-words[0])&65535, differences=sum(x!=y for x,y in zip(words,truth))+abs(len(words)-len(truth)),neighbors=same_functions(before,after,(row['function'],)),pools_equal=normalized_pools(before)==normalized_pools(after),diagnostics_before=diagnostic_rows(bd),diagnostics_after=diagnostic_rows(ad));assert q==row['expected_screen'],(row['function'],q,row['expected_screen'])
  for n,s in(('selected-owner.c',source),('body.c',row['body']),('declarations.c',row['declarations'])):(selected/n).write_text(s)
  raw,bindings=payload(after,row['function']);assert hashlib.sha256(raw).hexdigest()==row['expected_raw_payload_sha256'];assert hashlib.sha256(json.dumps(bindings,sort_keys=True).encode()).hexdigest()==row['expected_raw_bindings_sha256']
  asm=(ROOT/row['asm']).read_text();a=asm.index('glabel '+row['function']+'\n');b=asm.index('endlabel '+row['function'],a)+len('endlabel '+row['function']);(where/'original-target-fragment.s').write_text(asm[a:b]);q.update(function=row['function'],retail_words=row['original_words'],source_installed=False,matching_credit=0);(where/'screen.json').write_text(json.dumps(q,indent=2)+'\n');reports.append(q)
 q=dict(targets=reports,production_image_unchanged=True,production_sources_unchanged=True,source_installed=False,matching_credit=0);prepare();(OUT/'screen.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def controls():
 from tools.tests import game_unmatched_pair_lookup_20261123_guest as g
 from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
 row=MANIFEST['targets'][1];assert row['function']=='func_15022024';where=OUT/row['function']/'controls';where.mkdir(exist_ok=True);source=(OUT/row['function']/'selected-final/selected-owner.c').read_text();a,b=function_span(source,row['function']);body=source[a:b]
 changes={'wrong-gate':body.replace('PAIR_GATE_49D30[group] != 1','PAIR_GATE_49D30[group] == 0'),'wrong-tag-type':body.replace('*(u16 *)tag == 2','*(u16 *)tag == 1'),'wrong-record-field':body.replace('record + 0x3C','record + 0x40'),'uncached-sentinel':body.replace('missing = D_80096A14;','missing = D_80096A14;').replace(' != missing',' != D_80096A14'),'discarded-true-result':body.replace('return 1;','return 0;')};effective={}
 for label,changed in changes.items():
  assert changed!=body;obj,_=compile_owner(ROOT,where,source[:a]+changed+source[b:],label);words=g.bound_blob(*g.payload(obj,row['function']),g.S)
  for c in g.cases():
   initial=g.fixture(c);expected,answer=g.reference(initial,c);m=g.Oracle(words,initial,c);m.run()
   if g.public(m.memory,c)!=g.public(expected,c)or m.r[2]!=answer:effective[label]=dict(seed=c.seed,alias=c.alias);break
  else:raise AssertionError('Ineffective semantic comparison control: '+label)
 q=dict(effective_output_comparison_controls=effective,source_installed=False,matching_credit=0);(OUT/'controls.json').write_text(json.dumps(q,indent=2)+'\n');prepare();print(json.dumps(q),flush=True);return q
def normalization_outline():
 """Inventory evidence for a future normalizer, not an exact-match gate."""
 from collections import Counter
 from tools.experiments.game_paired_ground_constructor_match import payload
 where=OUT/'func_15022024';data,rr=payload(where/'selected-final/candidate.o','func_15022024');truth,tr=payload(where/'original-target.o','func_15022024');raw=list(struct.unpack('>87I',data));retail=list(struct.unpack('>91I',truth));assert raw[:3]==[0x27BDFFF8,0xAFB00004,0x00C08025]and raw[-3:]==[0x8FB00004,0x03E00008,0x27BD0008];assert raw[15]>>26==7 and raw[17]>>16==0x1000 and raw[18]==0x00001025
 omit_raw={0,1,2,17,18,84,85,86};omit_retail={*range(7),*range(86,91)}
 def token(w,refs):
  op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fn=w&63;imm=w&65535
  if w==0:return('nop',)
  if op==0:return('R',fn,(w>>6&31)if fn in(0,2,3)else None,rs==0,rt==0,rd==0)
  if op==17:
   if rs==8:return('Fbranch',rt)
   if rs in(0,4):return('Fmove',rs,rt==0)
   return('Fop',rs,fn)
  if op in(4,5,6,7,20,21,22,23):return('branch',op,rs==0,rt==0)
  return('I',op,imm,tuple(sorted(refs)))
 left=[token((w&0x03FFFFFF)|(6<<26)if i==15 else w,rr.get(4*i,()))for i,w in enumerate(raw)if i not in omit_raw];right=[token(w,tr.get(4*i,()))for i,w in enumerate(retail)if i not in omit_retail];assert len(left)==len(right)==79 and Counter(left)==Counter(right)
 q=dict(raw_core_words=79,retail_core_words=79,opcode_immediate_zero_role_and_binding_multisets_equal=True,scope='Outline only: removes actual frame/register-save blocks and a redundant count early-return pair, classifies the inverse count guard. Register names, scheduling, branch targets and full private-state proof remain open.',source_installed=False,matching_credit=0);(OUT/'normalization-outline.json').write_text(json.dumps(q,indent=2)+'\n');return q
if __name__=='__main__':screen();controls();print(json.dumps(normalization_outline()))
