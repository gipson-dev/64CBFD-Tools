"""Complete instruction-driven frame/FP/provider relation, independent of the fit."""
from pathlib import Path
import hashlib,json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests import game_owner_record_151b09bc_proof as parent
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_scaled_radial_150b85c0_match as source
e=g.e;p=source.OUT;f=source.FROZEN;ENTRY=0x150B85C0;RNG,FACTORY=0x150ADA20,0x15130374
ROLES={9:10,10:11,11:12,12:24,24:15,15:13,13:14,14:25,25:8,8:9}
class State(g.State):
 def __init__(self):
  super().__init__('common');self.r[4:8]=[('ARG',i)for i in range(4)];self.mem={i:('PRIVATE_ENTRY',i)for i in range(-152,20)}
  self.store(('STACK',16),4,('ARG',4))
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -152<=off and off+size<=20
   return g.join([self.mem[off+i]for i in range(size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -152<=off and off+size<=20
   for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def frame(self):return tuple(self.mem[i]for i in range(-152,20))
class Program(parent.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  assert target in(RNG,FACTORY)and s.r[29]==('STACK',-152)
  ordinal=sum(s.calls.values());s.calls[target]+=1;observed=()
  args=()if target==RNG else tuple(s.r[4:8])+(s.load(('STACK',-136),4),)
  if target==FACTORY:
   assert args[:3]==(('STACK',-112),1,0)
   observed=tuple(s.mem[i]for i in range(-112,0))
  s.trace.append(('CALL',target,args,observed,s.fcsr));s.trace.append(('FRAME',s.frame()));s.epoch+=1
  if target==FACTORY:
   for off in range(-112,0):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for i in range(4 if target==RNG else 5):s.store(('STACK',-152+4*i),4,('CALL_HOME',ordinal,i))
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  s.r[2]=('RESULT',target,ordinal);s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal)
def fields(w):
 op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
 if op==15:return set(),{rt},(16,)
 if op in(9,13):return{rs},{rt},(21,16)
 if op in(35,36):return{rs},{rt},(21,16)
 if op in(40,41,43):return{rs,rt},set(),(21,16)
 if op in(49,57):return{rs},set(),(21,)
 if op==3:return set(),{31},()
 assert op==0 and fn==37,hex(w);return{rs,rt},{rd},(21,16,11)
def rename(w,mapping):
 for shift in fields(w)[2]:
  reg=w>>shift&31;w=(w&~(31<<shift))|(mapping.get(reg,reg)<<shift)
 return w
def derive(words,refs=None):
 assert len(words)==119
 order=list(range(119));order[89:93]=[92,89,90,91];result=[words[i]for i in order]
 # The flags input t2 is consumed before the new temporary epoch. Only OR's
 # newly defined output changes at this boundary; subsequent roles are closed.
 assert result[89]==0x01435825;result[89]=rename(result[89],{11:12})
 for i in range(90,115):result[i]=rename(result[i],ROLES)
 if refs is None:return result
 return result,{4*i:refs[4*old]for i,old in enumerate(order)if 4*old in refs}
def closure(words):
 assert set(ROLES)==set(ROLES.values())and words[92]==0x01435825
 assert words[89]>>26==15 and words[89]>>16&31==1
 assert words[90]>>26==49 and words[90]>>21&31==1
 assert words[91]>>26==35 and words[91]>>21&31==29
 # OR has only integer-register effects and is independent of the intervening
 # literal/address loads. Both load order and the two ordered FP multiplies stay.
 defined={11};used={11}
 ordered=words[:89]+[words[92],words[89],words[90],words[91]]+words[93:]
 for i in range(90,113):
  reads,writes,_=fields(ordered[i]);assert reads&set(ROLES)<=defined,('role before definition',i,reads,defined)
  defined|=writes&set(ROLES);used|=(reads|writes)&set(ROLES)
 reads,_,_=fields(ordered[114]);assert reads&set(ROLES)<=defined
 assert words[113]>>26==3 and not set(ROLES)&{0,4,5,6,7,16,29,31}
 return dict(permutation=[92,89,90,91],range=[89,114],mapping=ROLES,defined_before_use=True,used_roles=sorted(used))
def programs():
 lookup={v[1]:v[2][1]for v in symbol_rows((f/'conker/build/conker.us.elf').read_bytes())}
 return bound_blob(*payload(p/'owner.o','func_150B85C0'),lookup),list(struct.unpack('>119I',(p/'retail.bin').read_bytes()))
def compare(raw,retail):
 terms=Terms();results=[];coverage=[]
 for words in(raw,retail):
  program=Program(words,terms);paths=program.paths(State());answers={}
  for key,s in paths.items():
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)and s.calls[RNG]==4 and s.calls[FACTORY]==1
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
   answers[key]=(s.trace,s.read_set,s.frame(),s.r[2],s.fcsr,s.divisors)
  assert program.seen==set(range(0,476,4)),('coverage',len(program.seen));results.append(answers);coverage.append(len(program.seen))
 assert results[0]==results[1],('complete relation mismatch',len(results[0]),len(results[1]))
 return len(results[0]),coverage
def main(raw=None,retail=None):
 if raw is None:raw,retail=programs()
 assert derive(raw)==retail;relation=closure(raw);count,coverage=compare(raw,retail)
 negatives=[]
 for label,index,mask in(('descriptor-kind',7,1),('duration-divisor',15,1),('color-divisor',39,1),('multiply-source',54,1<<11),('literal-address',91,4),('tail-byte',99,1),('context-home',114,4),('return-custody',1,4)):
  bad=retail[:];bad[index]^=mask
  try:compare(raw,bad)
  except(AssertionError,ValueError,KeyError)as err:
   assert 'unsupported'not in str(err),(label,err);negatives.append(label)
  else:raise AssertionError(('ineffective transfer control',label))
 report=dict(passes=True,paths=count,coverage=coverage,words=119,private_incoming_bytes=172,all112_descriptor_bytes=True,ordered_FP_FCSR=True,arbitrary_public_provider_epochs=True,full_return_and_saved_ABI=True,normalization=relation,effective_negatives=negatives,c_match_credit=0)
 (p/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
