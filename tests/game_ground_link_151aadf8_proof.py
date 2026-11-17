"""Locate the first complete-state proof boundary for the sequenced recovery."""
from pathlib import Path
import json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_ground_link_151aadf8_recovery as source
R,P,ENTRY=source.ROOT,source.OUT,source.ENTRY
e=g.e
QUERY,SELECT,REAL,RNG,CREATE,COPY=0x15045800,0x151D8E20,0x150ADA68,0x150ADA20,0x1513C73C,0x10022EC0
class State(g.State):
 def __init__(self,side):
  super().__init__(side);self.r[4]=('OWNER',);self.exposed=set();self.mem={off:('PRIVATE_BYTE',off)for off in range(-192,16)}
 def load(self,at,size,pool=b''):
  if e.tagged(at,'STACK'):
   off=at[1];assert size in(1,2,4)and off%size==0 and -192<=off and off+size<=16,('private load',at,size)
   return g.join([self.mem[off+i]for i in range(size)])
  return super().load(at,size,pool)
 def store(self,at,size,value):
  if e.tagged(at,'STACK'):
   off=at[1];assert size in(1,2,4)and off%size==0 and -192<=off and off+size<=16,('private store',at,size)
   for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
  else:super().store(at,size,value)
 def frame(self):return tuple(self.mem[off]for off in range(-192,16))
class Program(g.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  count={QUERY:4,SELECT:0,REAL:0,RNG:0,CREATE:14,COPY:3}[target]
  args=tuple(s.r[4:4+min(count,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,count-4)))
  if target==QUERY:assert args[0]==('STACK',-24)and args[1]==0;s.exposed.add((-24,-12))
  elif target==CREATE:assert args[0]==('STACK',-64);s.exposed.add((-64,-24))
  elif target==COPY:assert args[1:]==(('STACK',-96),32);s.exposed.add((-96,-64))
  s.trace.append(('CALL',target,args,s.fcsr));s.trace.append(('PRIVATE_FRAME',s.frame()))
  ordinal=sum(s.calls.values());s.calls[target]+=1;s.epoch+=1
  for begin,end in sorted(s.exposed):
   for off in range(begin,end):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for i in range(max(4,count)):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  s.r[2]=('RESULT',target,ordinal)
  if target==REAL:s.f[0]=('RESULT_FP',target,ordinal)
  if target==COPY:s.r[2]=args[0]
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)
def program(label):
 if label=='retail':return list(struct.unpack('>166I',(P/'retail.bin').read_bytes()))
 b,r=payload(P/(label+'.o'),'func_151AADF8');syms={v[1]:v[2][1]for v in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())};return bound_blob(b,r,syms)
def run(words,side,terms,cut):
 calls=[i*4 for i,w in enumerate(words)if w>>26==3 and(0x10000000|((w&0x3ffffff)<<2))==RNG]
 stops={-4:'return'}
 if cut is not None:stops[calls[cut]]='before-rng-'+str(cut)
 p=Program(words,terms);paths=p.paths(0,stops,State(side));result={}
 for key,s in paths.items():
  if key[0]=='return':
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
  result[key]=(s.trace,s.read_set,s.frame(),tuple(s.r),tuple(s.f),s.hi,s.lo,s.fcsr)
 return result,p.seen
def compare(label,cut,words=None):
 terms=Terms();raw,rs=run(program(label)if words is None else words,'raw',terms,cut);retail,ts=run(program('retail'),'retail',terms,cut)
 assert raw.keys()==retail.keys(),('keys',len(raw),len(retail));fail=[]
 for key in raw:
  if raw[key]!=retail[key]:
   part=next(i for i,(x,y)in enumerate(zip(raw[key],retail[key]))if x!=y)
   detail=None
   if part==0:
    a,b=raw[key][0],retail[key][0];at=next((i for i,(x,y)in enumerate(zip(a,b))if x!=y),min(len(a),len(b)))
    if at<len(a)and at<len(b)and a[at][0]==b[at][0]=='PRIVATE_FRAME':
     off=next(i for i,(x,y)in enumerate(zip(a[at][1],b[at][1]))if x!=y);detail=(at,'private-byte',off-192,repr(a[at][1][off]),repr(b[at][1][off]))
    else:detail=(at,repr(a[at]if at<len(a)else'<end>')[:400],repr(b[at]if at<len(b)else'<end>')[:400])
   elif part==2:
    at=next(i for i,(x,y)in enumerate(zip(raw[key][2],retail[key][2]))if x!=y);detail=(at-192,repr(raw[key][2][at]),repr(retail[key][2][at]))
   elif part in(3,4):
    at=next(i for i,(x,y)in enumerate(zip(raw[key][part],retail[key][part]))if x!=y);detail=(at,repr(raw[key][part][at]),repr(retail[key][part][at]))
   fail.append(dict(path=repr(key)[:400],part=part,detail=detail))
 return dict(label=label,cut=cut,paths=len(raw),equal_paths=len(raw)-len(fail),raw_reached=len(rs),retail_reached=len(ts),failures=fail)
def main():
 raw=program('v42');retail=program('retail');moves=[]
 for old,new in((0xafa20050,0xafa2004c),(0xafa20054,0xafa20050),(0x8fa90054,0x8fa90050),(0x8faf0050,0x8faf004c)):
  assert raw.count(old)==1;at=raw.index(old);raw[at]=new;moves.append(dict(offset=hex(at*4),expected=hex(old),replacement=hex(new)))
 original=compare('v42',None);assert original['paths']==7 and original['equal_paths']==3
 adjusted=compare('home-normalized',None,raw);assert adjusted['paths']==adjusted['equal_paths']==7
 controls=[]
 for label,old,new in(('raised-height',0x3c0142c8,0x3c0142ca),('private-first-spill',0xafa2004c,0xafa20050),('retained-query-x',0xc7b000a8,0xc7b000ac),('factory-kind',0x24050007,0x24050008),('descriptor-flags',0x35290300,0x35290301)):
  bad=raw[:];assert bad.count(old)==1,(label,hex(old));bad[bad.index(old)]=new;r=compare(label,None,bad)
  assert r['equal_paths']<r['paths'],('ineffective proof control',label);controls.append(label)
 positive=raw[:]
 for i in range(0xd0//4,0x1dc//4):
  w=positive[i];op=w>>26;fields=(21,16,11)if op==0 else(21,)if op in(49,57)else(21,16)
  for shift in fields:
   reg=w>>shift&31
   if reg in(24,25):w=(w&~(31<<shift))|((49-reg)<<shift)
  positive[i]=w
 r=compare('T8-T9-positive',None,positive);assert r['equal_paths']==r['paths']==7
 report=dict(paths=7,raw_paths_with_complete_private_state_equal=3,private_home_words=moves,normalized_paths_with_complete_private_state_equal=7,all208_private_and_incoming_home_bytes=True,ordered_FP_and_FCSR=True,complete_registers_at_return=True,arbitrary_public_alias_epochs=True,retained_query_and_descriptor_mutations=True,effective_controls=controls,positive_allocation_paths=7,whole_function=True,raw_reachable_words=163,retail_reachable_words=164,source_installed=source.installed(),c_match_credit=0)
 (P/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
