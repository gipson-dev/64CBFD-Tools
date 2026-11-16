"""Instruction-driven normal-execution emitter relation, independent of fitting.

Nonfaulting ordinary public memory is stable within each quiet epoch; public
stores and opaque calls invalidate the entire epoch, allowing public aliases.
FP instructions and their FCSR transitions remain ordered. Private frame bytes
are observed at every call. Providers can mutate the previously exposed packet
and curve ranges, but cannot inspect implementation PCs or unpassed locals.
DIV zero and signed-overflow inputs are excluded explicitly, not silently
interpreted as portable defined C behavior. No runtime or fault-state claim.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import json,struct,sys
from tools.experiments import game_spawn_curve_151a1998_recovery as m
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests.game_scaled_argument_packet_151a1010_proof import short as modular_short

O=m.OUT;ENTRY=m.ENTRY
RNG,REAL,TRIG,SUBMIT,COPY=0x150ADA20,0x150ADA68,0x151423D8,0x15167D84,m.symbols()['memcpy']

TABLE=0x80090b60

def narrow_difference(value):
 """Recognize x-(x>>k), whose signed16 range follows from that of x."""
 if not e.tagged(value,'LINEAR')or value[1]!=0 or len(value[2])!=2:return False
 positive=[v for v,k in value[2]if k==1];negative=[v for v,k in value[2]if k==e.U32]
 return len(positive)==len(negative)==1 and bounded16(positive[0])and e.tagged(negative[0],'ASR')and negative[0][1]==positive[0]and type(negative[0][2])is int and 0<=negative[0][2]<32

def bounded16(value):
 if isinstance(value,int):return -32768<=((value&0xffffffff)^0x80000000)-0x80000000<=32767
 if e.tagged(value,'SIGN16'):return True
 if e.tagged(value,'ASR'):return type(value[2])is int and 0<=value[2]<32 and bounded16(value[1])
 return narrow_difference(value)

def short(value):
 # These rules are exact bit-vector identities. They neither bound arbitrary
 # provider values nor assume that two independent shorts can be subtracted
 # without overflow. The paired difference must have precisely one origin.
 if e.tagged(value,'SIGN16'):return short(value[1])
 if e.tagged(value,'AND')and value[2]==65535:return short(value[1])
 if bounded16(value):return value&e.U32 if isinstance(value,int)else value
 return modular_short(value)

def byte(v,shift):
 if e.tagged(v,'SIGN16')and shift<16:v=v[1]
 if e.tagged(v,'AND')and isinstance(v[2],int)and v[2]>>(shift)&255==255:v=v[1]
 if isinstance(v,int):return(v>>shift)&255
 return('BYTE',v,shift)

def join(values):
 n=len(values)
 if n==1:return values[0]
 if all(isinstance(v,int)for v in values):return sum(v<<(8*(n-i-1))for i,v in enumerate(values))
 if all(e.tagged(v,'BYTE')for v in values)and [v[2]for v in values]==list(range(8*(n-1),-1,-8))and all(v[1]==values[0][1]for v in values):
  return values[0][1]if n==4 else e.bitop('AND',values[0][1],65535)
 return('JOIN',tuple(values))

def predicate(op,a,b):
 if op=='EQ':
  for x,y in((a,b),(b,a)):
   if y==0x80000000 and (e.tagged(x,'SIGN16')or e.tagged(x,'ASR')and e.tagged(x[1],'SIGN16')):return False
 return e.pred(op,a,b)

class State(e.State):
 def __init__(self,side):
  super().__init__('common','emitter');self.side=side;self.state_reg=18 if side=='raw'else 16;self.mem={};self.epoch=0;self.read_set=Counter();self.divisors=set();self.exposed_packet=False;self.exposed_curve=False
  self.r=[('INITIAL_GPR',i)for i in range(32)];self.r[0]=0;self.r[4]=('RECORD',);self.r[29]=('STACK',0);self.r[31]=('RETURN',)
  for i in(*range(16,24),28,30):self.r[i]=('ENTRY',i)
  self.f=[('INITIAL_FP',i)for i in range(32)]
  for i in range(20,32):self.f[i]=('ENTRY_FP',i)
  self.fcsr=('ENTRY_FCSR',);self.condition=None
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0
   assert -240<=off and off+size<=0,('private read escape',off,size)
   return join([self.mem.get(off+i,('PRIVATE_BYTE',off+i))for i in range(size)])
  e.plain(address);self.read_set[self.epoch,address,size]+=1
  return ('LOAD',address,size,self.epoch)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0
   assert -240<=off and off+size<=0,('private write escape',off,size)
   for i in range(size):self.mem[off+i]=byte(value,8*(size-i-1))
  else:
   e.plain(address);e.plain(value);self.trace.append(('WRITE',address,size,e.bitop('AND',value,(1<<(8*size))-1)));self.epoch+=1
 def frame(self):return tuple(self.load(('STACK',off),1)for off in range(-240,0))

class Program(e.Program):
 def __init__(self,words,terms):super().__init__(words,b'',ENTRY);self.terms=terms;self.seen=set()
 def instruction(self,pc):self.seen.add(pc);return super().instruction(pc)
 def step(self,s,w):
  op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if w==0:return
  if op==0 and fn==37 and (rs==0 or rt==0):s.r[rd]=s.r[rt if rs==0 else rs]
  elif op==0 and fn==0 and sa==16:s.r[rd]=('LEFT16',short(s.r[rt]))
  elif op==0 and fn==3 and sa==16:
   assert e.tagged(s.r[rt],'LEFT16');s.r[rd]=s.r[rt][1]
  elif op==0 and fn in(25,26,27):
   a,b=s.r[rs],s.r[rt]
   if fn in(26,27):
    # Normal execution excludes the later BREAK checks. Keep the obligations
    # as symbolic predicates so both streams must require the same domain.
    p=predicate('EQ',b,0);assert p is not True;e.assume(s,p,False);s.divisors.add((fn,a,b))
    if fn==26 and a==0x80000000:
     p=predicate('EQ',b,0xffffffff);assert p is not True;e.assume(s,p,False)
    s.lo=self.terms.term('SDIV'if fn==26 else'UDIV',a,b)
    s.hi=self.terms.term('SREM'if fn==26 else'UREM',a,b)
   else:
    if isinstance(a,int)and isinstance(b,int):s.lo=a*b&e.U32;s.hi=a*b>>32
    else:s.lo=e.scale(a,b)if isinstance(b,int)else e.scale(b,a)if isinstance(a,int)else self.terms.term('MULT',*sorted((a,b),key=repr));s.hi=self.terms.term('MULT_HI',*sorted((a,b),key=repr))
  elif op in(32,33,36,37):
   size=1 if op in(32,36)else 2;imm=((w&65535)^32768)-32768;v=s.load(e.add(s.r[rs],imm),size)
   if op==33:v=short(v)
   elif op==32:v=('SIGN8',v)
   else:v=e.bitop('AND',v,(1<<(8*size))-1)
   s.r[rt]=v
  elif op in(53,61):
   address=e.add(s.r[rs],((w&65535)^32768)-32768);assert e.tagged(address,'STACK')and address[1]%8==0
   if op==61:s.store(address,4,s.f[rt]);s.store(e.add(address,4),4,s.f[rt+1])
   else:s.f[rt]=s.load(address,4);s.f[rt+1]=s.load(e.add(address,4),4)
  elif op==17 and rs==4:s.f[rd]=s.r[rt]
  elif op==17 and rs in(16,20):
   if rs==16 and fn==6:s.f[sa]=s.f[rd]
   else:
    assert (rs==16 and fn in(0,1,2,3,13,60))or(rs==20 and fn==32),('unsupported FP',hex(w))
    args=(s.f[rd],s.f[rt])if rs==16 and fn in(0,1,2,3,60)else(s.f[rd],)
    observation=(rs,fn,args,s.fcsr);s.trace.append(('FP',observation));value=self.terms.term('FP_VALUE',*observation);s.fcsr=self.terms.term('FP_STATUS',*observation)
    if fn==60:s.condition=value
    else:s.f[sa]=value
  else:super().step(s,w)
  s.r[0]=0
 def call(self,s,target):
  assert target in(RNG,REAL,TRIG,SUBMIT,COPY)
  n={RNG:0,REAL:0,TRIG:1,SUBMIT:6,COPY:3}[target]
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,n-4)))
  ordinal=sum(s.calls.values());s.calls[target]+=1
  exposed=()
  if target==SUBMIT:
   assert args[0]==('STACK',-60)and args[1:4]==(0,20,0xffffffff),('packet call shape',args)
   exposed=tuple(s.load(('STACK',off),1)for off in range(-60,-4));s.exposed_packet=True
  if target==COPY:
   assert args[1:]==(('STACK',-80),20),('curve call shape',args)
   e.plain(args[0]);exposed=tuple(s.load(('STACK',off),1)for off in range(-80,-60));s.exposed_curve=True
  s.trace.append(('CALL',target,args,exposed,s.fcsr))
  s.trace.append(('PRIVATE_FRAME',s.frame()))
  s.epoch+=1
  # Retained passed ranges may be changed by this or a later provider.
  for begin,end,active in((-60,-4,s.exposed_packet),(-80,-60,s.exposed_curve)):
   if active:
    for off in range(begin,end):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
  for i in range(max(4,n)):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  s.r[2]=('RESULT',target,ordinal)
  if target in(REAL,TRIG):s.f[0]=('RESULT_FP',target,ordinal)
  if target==COPY:s.r[2]=args[0]
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal)
  s.condition=('CALL_CONDITION',ordinal)
 def paths(self,start,stops,initial):
  states=[(start,initial)];answers={};work=0
  while states:
   pc,s=states.pop();work+=1;s.steps+=1;assert work<100000 and s.steps<1500,('unbounded proof',start,work,hex(pc))
   if s.steps>1 and pc in stops:
    key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)));assert key not in answers,('duplicate path',key);answers[key]=s;continue
   w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31;delay=lambda n:self.step(n,self.instruction(pc+4))
   if op in(4,5,6,7,20,21,22,23)or op==17 and rs==8:
    if op==17:p=s.condition;assert p is not None;likely=bool(rt&2);p=p if rt&1 else e.negate(p)
    else:
     p=predicate('EQ',s.r[rs],s.r[rt])if op in(4,5,20,21)else predicate('SLT',0,s.r[rs]);likely=op>=20
     if op in(5,21,6,22):p=e.negate(p)
    for take in e.choices(s,p):
     n=deepcopy(s);e.assume(n,p,take)
     if take or not likely:delay(n)
     dest=pc+4+4*(((w&65535)^32768)-32768)if take else pc+8;states.append((dest,n))
   elif op==3:
    s.r[31]=self.entry+pc+8;delay(s);self.call(s,((self.entry+pc+4)&0xf0000000)|((w&0x3ffffff)<<2));states.append((pc+8,s))
   elif op==0 and w&63==8:
    assert s.r[rs]==('RETURN',);delay(s);states.append((-4,s))
   elif op==0 and w&63==13:raise AssertionError(('normal-domain BREAK reached',hex(pc),s.facts))
   else:self.step(s,w);states.append((pc+4,s))
  return answers

def initial(side,phase,program):
 s=State(side);s.state_reg=program.state_reg
 if phase=='prefix':return s
 for w in program.words[:17]:program.step(s,w)
 # Only the explicitly related live roles may be assumed equal at an
 # arbitrary loop head. Side-specific dead values expose accidental reads.
 for i in(1,2,3,*range(4,19),24,25,31):s.r[i]=('DEAD_ITERATION_GPR',side,i)
 for i in range(32):s.f[i]=('DEAD_ITERATION_FP',side,i)
 assert s.state_reg in(16,17,18)
 s.r[s.state_reg]=e.add(('RECORD',),40);s.r[19]=('RECORD',);s.r[20]=255;s.r[21]=TABLE;s.r[22]=('STACK',-60);s.r[23]=('STACK',-80)
 s.exposed_packet=s.exposed_curve=True
 s.trace=[];s.facts={};return s

def relation(s,end):
 if end=='return':
  assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
  assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
 else:
  assert s.r[29]==('STACK',-240)
  assert(s.r[s.state_reg],s.r[19],s.r[20],s.r[21],s.r[22],s.r[23])==(e.add(('RECORD',),40),('RECORD',),255,TABLE,('STACK',-60),('STACK',-80)),('loop roles',s.side,[(i,s.r[i])for i in(16,17,19,20,21,22,23)])
  assert s.r[28]==('ENTRY',28)and s.r[30]==('ENTRY',30)
  for reg,offset in ((16,0x4c),(17,0x50),(18,0x54),(19,0x58),(20,0x5c),(21,0x60),(22,0x64),(23,0x68)):
   assert s.load(('STACK',offset-240),4)==('ENTRY',reg),('inductive saved GPR',reg)
  assert s.load(('STACK',0x6c-240),4)==('RETURN',)
  for reg in range(20,32):assert s.load(('STACK',0x18+4*(reg-20)-240),4)==('ENTRY_FP',reg),('inductive saved FPR',reg)
 return(s.trace,s.read_set,s.divisors,s.fcsr,s.frame(),tuple(s.r[2:4])if end=='return'else())

def prove(raw,retail,phases=('prefix','loop'),raw_state_register=18,raw_loop_start=0x108):
 terms=Terms();programs={side:Program(words,terms)for side,words in(('raw',raw),('retail',retail))};report={}
 for side,program in programs.items():program.state_reg=raw_state_register if side=='raw'else 16;program.loop_start=raw_loop_start if side=='raw'else 0x104
 for phase in phases:
  values={}
  for side,p in programs.items():
   cut=p.loop_start
   paths=p.paths(0 if phase=='prefix'else cut,{cut:'loop',-4:'return'},initial(side,phase,p));values[side]={key:relation(s,key[0])for key,s in paths.items()}
  assert values['raw'].keys()==values['retail'].keys(),('path predicates',phase,len(values['raw']),len(values['retail']),next(iter(values['raw'].keys()-values['retail'].keys()),None),next(iter(values['retail'].keys()-values['raw'].keys()),None))
  for key,a in values['raw'].items():
   b=values['retail'][key]
   if a!=b:
    part=next(i for i,(x,y)in enumerate(zip(a,b))if x!=y)
    if part==0:
     at=next((i for i,(x,y)in enumerate(zip(a[0],b[0]))if x!=y),None)
     raise AssertionError(('transfer trace',phase,key,'event',at,repr(a[0][at]if at is not None else a[0])[:3500],repr(b[0][at]if at is not None else b[0])[:3500]))
    raise AssertionError(('transfer part',phase,key,part,repr(a[part])[:2500],repr(b[part])[:2500]))
  report[phase]=len(values['raw']);print(json.dumps(dict(phase=phase,paths=report[phase])),flush=True)
 coverage={}
 for side,p in programs.items():
  unseen=[pc for pc in range(0,len(p.words)*4,4)if pc not in p.seen]
  if set(phases)=={'prefix','loop'}:
   assert all(p.words[pc//4]>>26==0 and p.words[pc//4]&63==13 for pc in unseen),('unproved non-BREAK instruction',side,[hex(pc)for pc in unseen])
  coverage[side]=dict(visited_words=len(p.seen),unvisited_BREAK_offsets=[hex(pc)for pc in unseen])
 return dict(paths=report,coverage=coverage,ordered_FP_and_FCSR=True,private_frame_at_every_provider=True,full_private_frame_at_return=True,arbitrary_public_aliases=True,exposed_ranges_mutable_by_providers=True,normal_nonzero_DIV_domain=True,whole_function=set(phases)=={'prefix','loop'},c_match_credit=0)


def check_short_identities():
 import random
 U32=0xffffffff
 sign32=lambda x:((x&U32)^0x80000000)-0x80000000
 sign16=lambda x:(((x&65535)^32768)-32768)&U32
 count=0
 for n in range(-32768,32768):
  assert short(n)==sign16(n)and short(n&U32)==sign16(n)
  for k in range(32):
   q=(n>>k)&U32;difference=(n-(n>>k))&U32
   assert sign16(q)==q and sign16(difference)==difference
   count+=1
 rng=random.Random(0x151a1998)
 for _ in range(100000):
  v=rng.getrandbits(32);assert sign16(v&65535)==sign16(v)and short(v)==sign16(v)
 x=('SIGN16',('X',));y=('SIGN16',('Y',));assert bounded16(x)
 for k in range(32):
  shift=('ASR',x,k);difference=e.add(x,e.scale(shift,-1))
  assert short(shift)==shift and short(difference)==difference
  assert short(('AND',shift,65535))==shift
  assert not bounded16(('ASR',('X',),k))
 independent=e.add(x,e.scale(y,-1));assert not bounded16(independent)
 assert sign16(32767-(-32768))!=((32767-(-32768))&U32)
 for k in(-1,32,33):assert not bounded16(('ASR',x,k))
 assert not bounded16(('LINEAR',1,((x,1),(('ASR',x,1),U32))))
 report=dict(exhaustive_single_origin_shift_pairs=count,random_32bit_mask_cases=100000,independent_origin_overflow_control=True,unbounded_and_invalid_shift_controls=True,shared_tools_changed=False,c_match_credit=0)
 return report

def main():
 import hashlib,time
 from tools.experiments.game_spawn_curve_151a1998_match import fields
 m.check_inputs();raw,refs=payload(O/'qualified.o',m.NAME);words=bound_blob(raw,refs,m.symbols());truth=m.retail()
 report=prove(words,truth);report['integer_identity_controls']=check_short_identities();controls=[]
 def run(label,candidate,good):
  start=time.monotonic()
  try:detail=prove(candidate,truth)
  except AssertionError as error:
   assert not good,(label,error);reason=str(error)
   assert reason and not any(x in reason for x in('unsupported','unbounded proof','escaped code','normal-domain BREAK')),('invalid control',label,reason)
   row=dict(label=label,rejected=True,reason=reason[:800],seconds=round(time.monotonic()-start,3))
  else:assert good,('ineffective control',label);row=dict(label=label,passes=True,seconds=round(time.monotonic()-start,3))
  controls.append(row)
 alternative=[]
 for w in words:
  for shift,kind in fields(w):
   if kind=='g'and w>>shift&31 in(8,9):w=(w&~(31<<shift))|((17-(w>>shift&31))<<shift)
  alternative.append(w)
 assert alternative!=words;run('independent-T0-T1-allocation',alternative,True)
 bad=words[:];assert bad[0x10c//4]==0;bad[0x10c//4]=0xAFA0009C;run('unwritten-private-gap',bad,False)
 for label,find,change in(
  ('mode-byte-offset',lambda w:w>>26==36 and w>>21&31==19 and w&65535==12,lambda w:w+1),
  ('curve-quarter-threshold',lambda w:w>>26==41 and w>>21&31==29 and w&65535==0xAC,lambda w:w+2),
  ('FP-operand-order',lambda w:w>>26==17 and w>>21&31==16 and w&63==2 and w>>11&31!=w>>16&31,lambda w:(w&~((31<<11)|(31<<16)))|((w>>11&31)<<16)|((w>>16&31)<<11))):
  at=next(i for i,w in enumerate(words)if i>=0x108//4 and find(w));bad=words[:];bad[at]=change(bad[at]);assert bad!=words;run(label,bad,False)
 m.check_inputs();report.update(controls=controls,raw_sha256=hashlib.sha256(raw).hexdigest(),source_installed=m.installed())
 (O/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':print(json.dumps(main()),flush=True)
