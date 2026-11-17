"""Private provider, UV induction and return relations for the 464-word stream."""
from pathlib import Path
from collections import Counter
import json,struct
from tools.tests import game_strip_draw_151ad92c_entry_proof as opening
from tools.tests import game_strip_draw_151ad92c_geometry_proof as geometry
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms

e,g=opening.e,opening.g
FRAME=304
COUNT=e.bitop('AND',('CAPTURED_COUNT',),255)
WIDTH=e.bitop('AND',('CAPTURED_WIDTH',),65535)
HEIGHT=e.add(e.bitop('AND',('CAPTURED_HEIGHT',),65535),-1)
SHIFT=('CAPTURED_SHIFT',);INDEX=('SEGMENT_INDEX',);T=('FIRST_T',)
OUTPUT=('UV_OUTPUT',);RETURN_OUTPUT=('PROVIDER_OUTPUT',)
U=e.scale(e.add(WIDTH,256),1<<21)
CONSTANTS_RETAIL={17:0x01008010,18:0x05000208,19:0x05020A08,20:0x0502040A,21:0x05040C0A,22:0x0504060E,23:0x05040E0C,30:0x02140000}
CONSTANTS_RAW={12:0x01008010,13:0x05000208,31:0x05020A08,17:0x0502040A,18:0x05040C0A,19:0x0504060E,20:0x05040E0C,21:0x02140000,23:0x0506000E,30:0x0500080E}

def home(offset):return ('STACK',offset-FRAME)

def word_roundtrip(value):
 # Recover a word only when its four actual bytes exactly equal the byte
 # function applied to one recorded 32-bit origin. This handles a mask whose
 # low bytes were already simplified without dropping mismatched origins.
 if e.tagged(value,'JOIN')and len(value[1])==4:
  values=value[1]
  for byte in values:
   if e.tagged(byte,'BYTE'):
    original=byte[1]
    if tuple(g.byte(original,shift)for shift in(24,16,8,0))==values:return original
 return value

class State(opening.State):
 def __init__(self,side,phase):
  super().__init__();self.side=side;self.phase=phase
  self.r=[0]+[('DEAD_GPR',side,i)for i in range(1,32)]
  self.r[16],self.r[29],self.r[28]=opening.RECORD,('STACK',-FRAME),('ENTRY_GPR',28)
  self.f=[('CURRENT_FP',i)for i in range(32)]
  self.fcsr,self.condition=('STAGE_CSR',phase),('STAGE_CONDITION',phase)
  for reg,offset in [(reg,0x68+(reg-16)*4)for reg in range(16,24)]+[(30,0x88)]:
   self.store(home(offset),4,('ENTRY_GPR',reg))
  self.store(home(0x8C),4,('RETURN',))
  for reg in range(20,32,2):
   off=0x38+(reg-20)*4
   self.store(home(off),4,('ENTRY_FP',reg+1));self.store(home(off+4),4,('ENTRY_FP',reg))
  for off,val in ((0x118,SHIFT),(0x11C,HEIGHT),(0x130,opening.OUTPUT),(0x134,opening.RECORD),(0x138,('VIEWPORT',))):self.store(home(off),4,val)
  if phase=='provider':
   self.r[4],self.r[17],self.r[7]=opening.OUTPUT,WIDTH,0
   self.r[10 if side=='retail'else 8]=COUNT
   self.r[13 if side=='retail'else 12]=opening.oracle.TABLE
   self.r[31 if side=='retail'else 13]=12
   if side=='retail':self.r[6],self.r[8]=0,0
   else:self.r[6],self.r[3]=COUNT,COUNT
  elif phase=='uv':
   self.r[4]=OUTPUT;self.r[9]=opening.oracle.BANK
   for reg,value in (CONSTANTS_RETAIL if side=='retail'else CONSTANTS_RAW).items():self.r[reg]=value
   self.r[10 if side=='retail'else 8]=COUNT
   self.r[8 if side=='retail'else 3]=INDEX
   self.r[31 if side=='retail'else 22]=U
   self.r[12 if side=='retail'else 11]=T
   if side=='retail':self.r[11],self.r[13]=e.add(INDEX,1),e.add(T,HEIGHT)
   else:self.r[2]=OUTPUT
   for off,value in ((0x94,e.add(COUNT,-1)),(0x124,COUNT),(0x128,0)):self.store(home(off),4,value)
   for condition,taken in ((e.pred('SLT',INDEX,0),False),(e.pred('SLT',1,COUNT),True),(e.pred('SLT',INDEX,e.add(COUNT,-1)),True)):
    e.assume(self,condition,taken)
  else:self.r[4]=OUTPUT
  if phase!='return':e.assume(self,e.pred('SLT',COUNT,21),True)
  self.trace=[];self.read_set=Counter()
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):return word_roundtrip(super().load(address,size,pool))
  value=g.join([self.public.get(e.add(address,i),('MEMORY_BYTE',self.epoch,e.add(address,i)))for i in range(size)])
  self.read_set[address,size,value]+=1;return value

class Program(opening.Program):
 def call(self,s,target):
  assert target==opening.oracle.SUBMIT,hex(target)
  args=tuple(s.r[4:8])+tuple(s.load(e.add(s.r[29],off),4)for off in range(16,44,4))
  ordinal=s.calls[target];s.calls[target]+=1
  s.trace.extend((('CALL',target,args,s.fcsr),('CALL_PRIVATE',s.frame()),('CALL_PUBLIC',tuple(sorted(s.public.items(),key=repr)))))
  s.epoch+=1
  for address in s.public:s.public[address]=('PROVIDER_BYTE',ordinal,address)
  for reg in (1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for i in range(11):s.store(home(4*i),4,('CALL_HOME',ordinal,i))
  s.r[2],s.r[31]=RETURN_OUTPUT,('CALL_RETURN',ordinal)
  s.hi,s.lo=('CALL_HI',ordinal),('CALL_LO',ordinal)
  s.fcsr,s.condition=('CALL_CSR',ordinal),('CALL_CONDITION',ordinal)

def locations(side,record):
 if side=='retail':return {'provider':0x151ADD68-0x151AD92C,'uv':0x151ADED4-0x151AD92C,'return':0x151AE020-0x151AD92C}
 origin={int(k):v for k,v in record['origin_map'].items()}
 at=lambda address:origin[(address-0x1ADC)//4]*4
 return {'provider':at(0x1F28),'uv':at(0x20AC),'return':at(0x21E4)}

def uv_roles(s,side,advance=False):
 idx=s.r[8 if side=='retail'else 3];first=s.r[12 if side=='retail'else 11]
 assert s.r[10 if side=='retail'else 8]==COUNT,('captured count',side,s.r[10 if side=='retail'else 8],COUNT)
 assert s.r[31 if side=='retail'else 22]==U,('packed U',side,s.r[31 if side=='retail'else 22],U)
 assert all(s.load(home(off),4)==v for off,v in((0x94,e.add(COUNT,-1)),(0x124,COUNT),(0x128,0),(0x118,SHIFT),(0x11C,HEIGHT))),('UV private invariant',side)
 if advance:
  assert idx==e.add(INDEX,1),('UV index',side,idx)
  assert first==e.add(T,HEIGHT),('first T',side,first)
 elif s.phase=='provider':
  assert idx==0 and first==256,('UV seed',side,idx,first)
  assert s.r[4]==e.add(RETURN_OUTPUT,16),('provider result cursor',side,s.r[4])
 if side=='retail':
  assert s.r[11]==e.add(idx,1),('next UV index',s.r[11],idx)
  assert s.r[13]==e.add(first,HEIGHT),('second T',s.r[13],first)
 else:assert s.r[2]==s.r[4],('raw vertex-command cursor',s.r[2],s.r[4])
 constants=CONSTANTS_RETAIL if side=='retail'else CONSTANTS_RAW
 assert all(s.r[reg]==v for reg,v in constants.items()),('UV constants',side,{reg:s.r[reg]for reg in constants})
 return (s.r[4],s.r[16],s.r[29],s.r[28],s.r[9],s.r[10 if side=='retail'else 8],idx,first,s.r[31 if side=='retail'else 22],tuple(s.f[20:]))

def relation(a,b,phase,end):
 for label,x,y in (('private',a.frame(),b.frame()),('combined ordered effects and FP status',a.trace,b.trace),('public',a.public,b.public),('reads',a.read_set,b.read_set),('FP status',a.fcsr,b.fcsr),('FP condition',a.condition,b.condition)):
  if x!=y:
   at=next((i for i,(u,v)in enumerate(zip(x,y))if u!=v),None)if isinstance(x,(list,tuple))else None
   raise AssertionError((phase,end,label,at,repr(x[at]if at is not None else x)[:850],repr(y[at]if at is not None else y)[:850]))
 if end=='uv':assert uv_roles(a,'retail',phase=='uv')==uv_roles(b,'raw',phase=='uv'),('UV roles',phase)
 elif end=='return':
  assert (a.r[4],a.r[29],a.r[28])==(b.r[4],b.r[29],b.r[28]),('return-head roles',phase)
 else:
  for s in(a,b):
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',),('restored stack and return',s.side,s.r[29],s.r[31])
   assert all(s.r[i]==('ENTRY_GPR',i)for i in(*range(16,24),28,30)),('restored GPR',s.side)
   assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)],('restored FPR',s.side,s.f[20:])
  assert a.r[2]==b.r[2],('returned output',a.r[2],b.r[2])

def prove(truth,candidate,record,phase):
 terms=Terms();answers=[]
 for side,words in(('retail',truth),('raw',candidate)):
  loc=locations(side,record);stops={-4:'done'}if phase=='return'else {loc['uv']:'uv',loc['return']:'return'}
  s=State(side,phase);answers.append(Program(words,terms).paths(loc[phase],stops,s))
 left,right=answers
 assert left.keys()==right.keys(),('path predicates',phase,len(left),len(right),next(iter(left.keys()-right.keys()),None),next(iter(right.keys()-left.keys()),None))
 for key,a in left.items():relation(a,right[key],phase,key[0])
 return dict(phase=phase,paths=len(left),ends=dict(Counter(key[0]for key in left)),all_320_private_bytes=True,combined_ordered_public_effects_and_FP_status=True,stable_public_reads=True,opaque_public_mutations=phase=='provider',live_roles=True,terms=len(terms.values))

def controls(truth,candidate,record):
 from tools.tests.game_strip_update_151ad174_proof import alternate
 alt=[alternate(w)for w in candidate];assert alt!=candidate
 positive={phase:prove(truth,alt,record,phase)for phase in('provider','uv','return')}
 changes=(('provider','wrong-count-home',0xAFA80124,0xAFA80120),
  ('provider','missing-zero-cursor-home',0xAFA00128,0),
  ('provider','wrong-eleventh-argument',0x240E003E,0x240E003F),
  ('provider','reloaded-mutated-count',0x8FA80124,0x92080042),
  ('provider','wrong-zero-cursor-reload',0x8FA30128,0x8FA30124),
  ('provider','private-width-spill',0x01E0B025,0xAFAF012C),
  ('uv','wrong-modify-vertex-index',0x37390008,0x3739000A),
  ('uv','wrong-UV-limit-home',0x8FAF0094,0x8FAF0090),
  ('return','wrong-return-frame',0x27BD0130,0x27BD0128),
  ('return','wrong-saved-FPR-pair',0xD7B40038,0xD7B40040))
 rejected=[]
 for phase,name,before,after in changes:
  assert candidate.count(before)==1,(name,candidate.count(before))
  bad=candidate[:];at=bad.index(before);bad[at]=after
  try:prove(truth,bad,record,phase)
  except AssertionError as error:
   reason=str(error);assert reason and not any(s in reason for s in('unsupported','unbounded','escaped code')),reason
   rejected.append(dict(name=name,phase=phase,index=at,rejected=reason[:240]))
  else:raise AssertionError(('ineffective provider/UV control',name))
 return dict(independent_GPR_allocation_positive=positive,effective_controls=rejected)
