"""Instruction-driven complete normal-execution relation for the bone-hit C."""
from pathlib import Path
import json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_bone_hit_151aabc4_recovery as source
R,P,ENTRY=source.ROOT,source.OUT,source.ENTRY
e=g.e
SELECT,BONE,PREP,QUERY,EMIT,TRAIL=0x151D8E20,0x15142314,0x1504715C,0x1504697C,0x151DBCBC,0x15153F18
class State(g.State):
 def __init__(self,side):
  super().__init__(side);self.r[4]=('ACTOR',);self.r[5]=('BONE',);self.exposed=set();self.mem={off:('PRIVATE_BYTE',off)for off in range(-200,16)}
 def load(self,at,size,pool=b''):
  if e.tagged(at,'STACK'):
   off=at[1];assert size in(1,2,4)and off%size==0 and -200<=off and off+size<=16,('private load',at,size)
   return g.join([self.mem[off+i]for i in range(size)])
  return super().load(at,size,pool)
 def store(self,at,size,value):
  if e.tagged(at,'STACK'):
   off=at[1];assert size in(1,2,4)and off%size==0 and -200<=off and off+size<=16,('private store',at,size)
   for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
  else:super().store(at,size,value)
 def frame(self):return tuple(self.mem[i]for i in range(-200,16))
class Program(g.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  count={SELECT:0,BONE:3,PREP:2,QUERY:4,EMIT:7,TRAIL:5}[target]
  args=tuple(s.r[4:4+min(count,4)])+tuple(s.load(e.add(s.r[29],16+4*i),4)for i in range(max(0,count-4)))
  if target==BONE:assert args[2]==('STACK',-12);s.exposed.add((-12,0))
  elif target==PREP:assert args[0]==('STACK',-48);s.exposed.add((-48,-12))
  elif target==QUERY:
   assert args[0]==('STACK',-64)and args[1]==0 and args[3]==('STACK',-48);s.exposed.add((-64,-52))
  elif target==EMIT:
   assert args[1:]==(0x42200000,150,('STACK',-44),('STACK',-80),255,1),('first effect ABI',args);s.exposed.add((-80,-68))
  elif target==TRAIL:
   assert args==(('STACK',-156),('STACK',-148),('STACK',-48),255,1),('trail ABI',args);s.exposed.add((-156,-80))
  s.trace.append(('CALL',target,args,s.fcsr));s.trace.append(('PRIVATE_FRAME',s.frame()))
  ordinal=sum(s.calls.values());s.calls[target]+=1;s.epoch+=1
  for begin,end in sorted(s.exposed):
   for off in range(begin,end):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for i in range(4):s.store(e.add(s.r[29],4*i),4,('CALL_HOME',ordinal,i))
  s.r[2]=('RESULT',target,ordinal);s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_CONDITION',ordinal)
def prove(raw,retail):
 terms=Terms();values=[];coverage={}
 for side,words in(('raw',raw),('retail',retail)):
  p=Program(words,terms);paths=p.paths(0,{-4:'return'},State(side));result={}
  for key,s in paths.items():
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
   result[key]=(s.trace,s.read_set,s.frame(),tuple(s.r),tuple(s.f),s.hi,s.lo,s.fcsr)
  values.append(result);coverage[side]=p.seen
 a,b=values;assert a.keys()==b.keys(),('path keys',len(a),len(b))
 for key in a:
  if a[key]!=b[key]:
   part=next(i for i,(x,y)in enumerate(zip(a[key],b[key]))if x!=y)
   if part==0:
    x,y=a[key][0],b[key][0];i=next((i for i,(u,v)in enumerate(zip(x,y))if u!=v),min(len(x),len(y)))
    raise AssertionError(('trace',key,i,repr(x[i]if i<len(x)else'<end>')[:1400],repr(y[i]if i<len(y)else'<end>')[:1400]))
   raise AssertionError(('state',key,part,repr(a[key][part])[:1400],repr(b[key][part])[:1400]))
 for side,seen in coverage.items():assert seen==set(range(0,504,4)),('coverage',side,len(seen),sorted(set(range(0,504,4))-seen))
 return dict(paths=len(a),whole_function=True,reachable_words={k:len(v)for k,v in coverage.items()},ordered_FP_and_FCSR=True,all216_private_and_incoming_home_bytes=True,complete_registers_at_return=True,retained_bone_query_surface_and_hit_mutations=True,arbitrary_public_aliases=True)
def programs():
 raw,refs=payload(P/'v13.o','func_151AABC4');syms={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())}
 return bound_blob(raw,refs,syms),list(struct.unpack('>126I',(P/'retail.bin').read_bytes()))
def main():
 raw,retail=programs();report=prove(raw,retail);controls=[]
 for label,old,new in(('upper-bound',0x3C014248,0x3C014249),('fresh-matrix',0x8CE401D4,0x01C02025),('retained-hit',0x27A90078,0x27A900BC),('count-value',0x240E0003,0x240E0004),('selector-field',0xA3AE0068,0xA3AE0069)):
  bad=raw[:];assert bad.count(old)==1,(label,old);bad[bad.index(old)]=new
  try:prove(bad,retail)
  except(AssertionError,ValueError,KeyError):controls.append(label)
  else:raise AssertionError(('ineffective proof control',label))
 # A closed T8/T9 cycle in the private initialization block is ABI-neutral.
 renamed=raw[:]
 for i in range(0xE8//4,0x1E0//4):
  w=renamed[i];op=w>>26
  fields=(21,16,11)if op==0 else(21,)if op in(49,57)else(21,16)
  for shift in fields:
   reg=w>>shift&31
   if reg in(24,25):w=(w&~(31<<shift))|((49-reg)<<shift)
  renamed[i]=w
 positive=prove(renamed,retail)
 report.update(effective_controls=controls,positive_T8_T9_paths=positive['paths'],source_installed=source.installed(),c_match_credit=0)
 (P/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
