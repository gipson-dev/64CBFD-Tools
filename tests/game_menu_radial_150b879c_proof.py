"""Complete normal-execution frame/FP/provider relation, independent of guard rows.

The C descriptor and one flag spill use distinct private homes. A closed byte
permutation relates their complete frames, including untouched descriptor bytes.
Opaque services invalidate public memory and may retain the passed direction
outputs or descriptor; they cannot inspect unpassed locals or implementation PCs.
This is not a claim of raw fault-state or unrestricted C stack-alias equivalence.
"""
import json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests import game_owner_record_151b09bc_proof as parent
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_menu_radial_150b879c_match as source
e=g.e;ENTRY=0x150B879C;RNG,REAL,DIRECTION,FACTORY,COPY=0x150ADA20,0x150ADA68,0x15143874,0x15130374,0x10022EC0
ROLES={14:15,15:24,24:25,25:8,8:9,9:10,10:11,11:12,12:13,13:14}

def canonical(off,raw):
 if raw:
  if -116<=off<-4:return off-4
  if -120<=off<-116:return off+112
  if -128<=off<-124:return off-4
  if -132<=off<-128:return off+4
 return off

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
 assert len(words)==142
 order=list(range(142));order[106:109]=[108,106,107];out=[words[i]for i in order]
 for i,w in enumerate(out):
  op,rs,rt=w>>26,w>>21&31,w>>16&31;off=w&65535
  if rs==29 and op in(9,35,40,41,43,49,57) and not(op==9 and rt==29):
   physical=off-168;new=canonical(physical,True)+168
   if new!=off:out[i]=(w&0xffff0000)|new
 assert out[106]==0x01A37025;out[106]=(out[106]&~(31<<11))|(15<<11)
 for i in range(109,127):out[i]=rename(out[i],ROLES)
 if refs is None:return out
 return out,{4*i:refs[4*old]for i,old in enumerate(order)if 4*old in refs}

def closure(words):
 assert set(ROLES)==set(ROLES.values()) and words[108]==0x01A37025
 assert words[106]>>26==15 and words[106]>>16&31==1
 assert words[107]>>26==49 and words[107]>>21&31==1
 # Move a pure integer OR across its independent constant-address/load pair.
 # The old t5 input is consumed before the new register-allocation epoch.
 defined={14};used={14}
 for i in range(109,125):
  reads,writes,_=fields(words[i]);assert reads&set(ROLES)<=defined,(i,reads,defined)
  defined|=writes&set(ROLES);used|=(reads|writes)&set(ROLES)
 assert not set(ROLES)&{0,4,5,6,7,16,29,31}
 assert {canonical(i,True)for i in range(-168,60)}==set(range(-168,60))
 return dict(permutation=[108,106,107],roles=ROLES,defined_before_use=True,frame_bijection_bytes=228,descriptor_bytes=112)

class State(g.State):
 def __init__(self,raw,remap=True):
  super().__init__('common');self.remap=raw and remap;self.exposed=set();self.mem={i:('PRIVATE_ENTRY',i)for i in range(-168,60)}
  self.r[4:8]=[('ARG',i)for i in range(4)]
  for i in range(4,15):self.store(('STACK',4*i),4,('ARG',i))
 def address(self,v):return('STACK',canonical(v[1],self.remap))if e.tagged(v,'STACK')else v
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -168<=off and off+size<=60
   return g.join([self.mem[canonical(off+i,self.remap)]for i in range(size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -168<=off and off+size<=60
   for i in range(size):self.mem[canonical(off+i,self.remap)]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def value(self,v):
  if e.tagged(v,'STACK'):return self.address(v)
  return tuple(self.value(item)for item in v)if isinstance(v,tuple)else v
 def frame(self):return tuple(self.value(self.mem[i])for i in range(-168,60))

class Program(parent.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  n={RNG:0,REAL:0,DIRECTION:4,FACTORY:5,COPY:3}[target];assert s.r[29]==('STACK',-168)
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-152+4*i),4)for i in range(max(0,n-4)))
  passed=tuple(s.address(v)for v in args);ordinal=sum(s.calls.values());s.calls[target]+=1;observed=()
  if target==DIRECTION:
   assert passed[2:]==(('STACK',-48),('STACK',-40))
   s.exposed.update(range(-48,-44));s.exposed.update(range(-40,-36))
  elif target==FACTORY:
   assert passed[:3]==(('STACK',-120),1,4)and passed[4]==1
   observed=tuple(s.mem[i]for i in range(-120,-8));s.exposed.update(range(-120,-8))
  elif target==COPY:
   assert passed[1:]==(('STACK',-4),4);e.plain(passed[0]);observed=tuple(s.mem[i]for i in range(-4,0))
  s.trace.append(('CALL',target,passed,observed,s.fcsr));s.trace.append(('FRAME',s.frame()));s.epoch+=1
  if target==COPY:
   for i,v in enumerate(observed):s.trace.append(('COPY_WRITE',e.add(passed[0],i),v))
  for off in s.exposed:s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for i in range(max(4,n)):s.store(('STACK',-168+4*i),4,('CALL_HOME',ordinal,i))
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  s.r[2]=passed[0]if target==COPY else('RESULT',target,ordinal)
  if target==REAL:s.f[0]=('FLOAT_RESULT',ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)

def compare(raw,retail,remap=True):
 terms=Terms();results=[];coverage=[]
 for side,words in enumerate((raw,retail)):
  program=Program(words,terms);answers={}
  for key,s in program.paths(State(side==0,remap)).items():
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)and s.r[2]==1
   assert(s.calls[RNG],s.calls[REAL],s.calls[DIRECTION],s.calls[FACTORY])==(4,2,1,1)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
   answers[key]=(s.trace,s.read_set,s.frame(),s.r[2],s.fcsr,s.divisors)
  assert program.seen==set(range(0,568,4)),('coverage',len(program.seen));results.append(answers);coverage.append(len(program.seen))
 assert results[0]==results[1],('complete relation mismatch',len(results[0]),len(results[1]))
 return len(results[0]),coverage

def main(raw=None,retail=None):
 if raw is None:
  lookup={v[1]:v[2][1]for v in symbol_rows((source.FROZEN/'conker/build/conker.us.elf').read_bytes())}
  raw=bound_blob(*payload(source.OUT/'owner.o',source.NAME),lookup);retail=list(struct.unpack('>142I',(source.OUT/'retail.bin').read_bytes()))
 assert derive(raw)==retail;normalization=closure(raw);count,coverage=compare(raw,retail);negatives=[]
 for label,index,mask in(('early-capture-address',7,4),('duration-mask',18,1),('color-divisor',38,1),('size-multiply',54,1<<11),('speed-addend',76,1),('late-literal-address',108,4),('signed-heading-home',79,4),('return-value',137,1)):
  bad=retail[:];bad[index]^=mask
  try:compare(raw,bad)
  except(AssertionError,ValueError,KeyError)as err:
   assert 'unsupported'not in str(err),(label,err);negatives.append(label)
  else:raise AssertionError(('ineffective semantic control',label,index))
 try:compare(raw,retail,False)
 except AssertionError:negatives.append('disabled-private-home-map')
 else:raise AssertionError('ineffective home-map control')
 report=dict(passes=True,paths=count,coverage=coverage,private_incoming_bytes=228,all112_descriptor_bytes=True,ordered_FP_FCSR=True,arbitrary_public_provider_epochs=True,normalization=normalization,effective_negatives=negatives,c_match_credit=0)
 (source.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
