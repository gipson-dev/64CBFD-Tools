"""Private instruction-driven opening proof, not whole-function qualification."""
from tools.experiments import game_region_emitter_151a5660_recovery as source
from pathlib import Path
from collections import Counter
import hashlib,json,struct,sys
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
O=source.OUT;R=source.ROOT;ENTRY=source.ENTRY;VIEW=0x151464B8
class State(g.State):
 def __init__(self,side):
  super().__init__(side);self.r[4]=('OWNER',);self.epoch=0
 def load(self,at,size,pool=b''):
  if e.tagged(at,'STACK'):
   off=at[1];assert size in(1,2,4)and off%size==0 and -512<=off and off+size<=0
   return g.join([self.mem.get(off+i,('PRIVATE_BYTE',off+i))for i in range(size)])
  e.plain(at);self.read_set[self.epoch,at,size]+=1
  return ('LOAD',at,size,self.epoch)
 def store(self,at,size,value):
  if e.tagged(at,'STACK'):
   off=at[1];assert size in(1,2,4)and off%size==0 and -512<=off and off+size<=0
   for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
  else:super().store(at,size,value)
 def frame(self):return tuple(self.load(('STACK',off),1)for off in range(-264,0))
class Program(g.Program):
 def __init__(self,words,terms):
  e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  assert target==VIEW,('opening escaped into another provider',hex(target))
  assert s.r[29]==('STACK',-264)
  ordinal=sum(s.calls.values());s.calls[target]+=1
  e.plain(s.r[4]);s.trace.append(('CALL',target,(s.r[4],),s.fcsr));s.trace.append(('PRIVATE_FRAME',s.frame()))
  s.epoch+=1
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  for i in range(4):s.store(e.add(s.r[29],i*4),4,('CALL_HOME',ordinal,i))
  s.r[2]=e.bitop('AND',('RESULT',target,ordinal),255)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal)
  s.condition=('CALL_CONDITION',ordinal)
def relation(s,end):
 if end=='return':
  assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
  assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))
  assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
 else:
  assert s.r[29]==('STACK',-264)and s.r[16]==e.add(('OWNER',),40)and s.r[18]==('OWNER',)and s.f[28]==0x3F800000
  for reg,at in ((16,-192),(17,-188),(18,-184)):
   assert s.load(('STACK',at),4)==('ENTRY',reg)
  assert s.load(('STACK',-180),4)==('RETURN',)
 return s.trace,s.read_set,s.fcsr,s.frame()
def prove(raw,retail):
 terms=Terms();programs={side:Program(words,terms)for side,words in [('raw',raw),('retail',retail)]};values={}
 for side,p in programs.items():
  states=p.paths(0,{0x10C:'loop',-4:'return'},State(side))
  values[side]={key:relation(s,key[0])for key,s in states.items()}
 assert values['raw'].keys()==values['retail'].keys(),('opening paths',values['raw'].keys(),values['retail'].keys())
 for key,v in values['raw'].items():assert v==values['retail'][key],('opening transfer',key)
 return dict(paths=len(values['raw']),terminal_kinds=dict(Counter(k[0]for k in values['raw'])),ordered_FP_and_FCSR=True,arbitrary_public_aliases=True,opaque_viewmask_provider=True,private_frame_compared=True,callee_saved_restoration=True,whole_function=False)
def main():
 label='qualified';dest=O/('prefix-proof-'+label+'.json');assert not dest.exists()
 raw,refs=payload(O/(label+'.o'),'func_151A5660')
 symbols={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())}
 actual=bound_blob(raw,refs,symbols);retail=list(struct.unpack('>403I',(O/'retail.bin').read_bytes()))
 report=prove(actual,retail);controls=[]
 for name,old,new in [('expiry-width',0xA64F000E,0xAE4F000E),('disabled-byte',0x93190014,0x93190015),('accumulator-order',0x46062202,0x46062102)]:
  bad=actual[:];assert bad.count(old)==1;bad[bad.index(old)]=new
  try:prove(bad,retail)
  except(AssertionError,ValueError):controls.append(name)
  else:raise AssertionError(('ineffective opening control',name))
 report.update(label=label,controls=controls,raw_sha256=hashlib.sha256(raw).hexdigest(),source_installed=source.installed(),c_match_credit=0)
 dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
