"""Independent full-frame/FP/provider proof and closed temporary-role normalization."""
from pathlib import Path
import hashlib,json,struct
from tools.tests import game_menu_layers_150b77a8_proof as parent
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
e=parent.e;g=parent.g;ENTRY=0x150B791C
from tools.experiments import game_menu_four_records_150b791c_match as source
p=source.OUT;f=source.FROZEN
ROLES=((21,57,{9:10,10:8,8:9}),(69,77,{10:12,12:11,11:10}),(88,96,{24:8,8:25,25:24}))
class Program(parent.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
def operands(w):
 op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
 if op==15:return set(),{rt},(16,)
 if op==9:return{rs},{rt},(21,16)
 if op in(35,36,33,37):return{rs},{rt},(21,16)
 if op in(40,41,43):return{rs,rt},set(),(21,16)
 if op in(49,57):return{rs},set(),(21,)
 if op in(4,5,20,21):return{rs,rt},set(),(21,16)
 if op==17:
  if rs==0:return set(),{rt},(16,)
  if rs==4:return{rt},set(),(16,)
  assert rs==16;return set(),set(),()
 if w==0:return set(),set(),()
 if op==0 and fn in(33,37):return{rs,rt},{rd},(21,16,11)
 raise AssertionError(('unexpected role instruction',hex(w)))
def rename(w,mapping):
 for shift in operands(w)[2]:
  register=w>>shift&31;w=(w&~(31<<shift))|(mapping.get(register,register)<<shift)
 return w
def derive(words,refs=None):
 assert len(words)==137
 order=list(range(137));order[14:20]=[19,15,14,16,17,18]
 result=[words[i]for i in order]
 for lo,hi,mapping in ROLES:
  for i in range(lo,hi+1):result[i]=rename(result[i],mapping)
 if refs is None:return result
 return result,{4*i:refs[4*old]for i,old in enumerate(order)if 4*old in refs}
def closure(words):
 assert words[19]>>26==15 and words[19]>>16&31==1
 for i in(14,16,17,18):assert words[i]>>26==9 and words[i]>>21&31==0 and words[i]>>16&31!=1
 assert words[15]>>26==17 and words[15]&63==13
 # Moving a GPR-only LUI across the unchanged conversion neither reads nor
 # writes its FP operand/result/FCSR. No FP operation is reordered or added.
 assert operands(words[15])==(set(),set(),())
 reports=[]
 for lo,hi,mapping in ROLES:
  assert set(mapping)==set(mapping.values())and not set(mapping)&{0,4,5,6,7,16,29,31}
  defined=set();used=set()
  for w in words[lo:hi+1]:
   reads,writes,_=operands(w);assert reads&set(mapping)<=defined,('role read before definition',lo,hex(w),reads,defined)
   defined|=writes&set(mapping);used|=(reads|writes)&set(mapping)
  reports.append(dict(first_word=lo,last_word=hi,mapping=mapping,defined_before_use=True,used_registers=sorted(used)))
 return reports
def programs():
 symbols={v[1]:v[2][1]for v in symbol_rows((f/'conker/build/conker.us.elf').read_bytes())}
 return bound_blob(*payload(p/'owner.o','func_150B791C'),symbols),list(struct.unpack('>137I',(p/'retail.bin').read_bytes()))
def compare(raw,retail):
 terms=Terms();answers=[];coverage=[]
 for words in(raw,retail):
  program=Program(words,terms);paths=program.paths(parent.State());result={}
  for key,s in paths.items():
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
   result[key]=(s.trace,s.read_set,s.frame(),s.fcsr)
  answers.append(result);coverage.append(len(program.seen))
 assert answers[0]==answers[1],('complete transfer mismatch',len(answers[0]),len(answers[1]))
 return len(answers[0]),coverage
def main(raw=None,retail=None):
 if raw is None:raw,retail=programs()
 assert derive(raw)==retail;roles=closure(raw);count,coverage=compare(raw,retail)
 negatives=0
 for index,mask in((10,4),(40,4),(46,1),(57,0x04000000),(74,1),(77,0x04000000),(96,0x04000000),(127,1)):
  wrong=retail[:];wrong[index]^=mask
  try:compare(raw,wrong)
  except(AssertionError,ValueError,KeyError):negatives+=1
  else:raise AssertionError(('ineffective transfer negative',index))
 report=dict(passes=True,paths=count,coverage=coverage,words=137,frame_bytes_compared=112,ordered_FP_conversions=3,FP_FCSR_order_preserved=True,arbitrary_retained_descriptor_and_public_provider_mutations=True,roles=roles,transfer_negatives=negatives,c_match_credit=0)
 (p/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
