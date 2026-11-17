"""Complete original slot-six dispatcher, callback, cleanup and release paths."""
from tools.experiments import game_region_emitter_151a5660_recovery as source
from pathlib import Path
import importlib.util,itertools,json,struct,sys
from tools.tests import game_region_emitter_151a5660_oracle as g
O=source.OUT
PARENT,TABLE,CLEAN_TABLE,CLEAN,RELEASE,TICKS=0x15149264,0x8008A4E8,0x8008A4C0,0x150AE790,0x1516972C,0x800BE9E4
rom=(g.R/'conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>45I',rom,0x176714))
class Machine(g.Oracle):
 def __init__(self,w,m,c,revive):
  connected=g.trig_source.helper_code();connected.update(dict(zip(range(g.ENTRY,g.ENTRY+len(w)*4,4),w)))
  g.FactoryOracle.__init__(self,parent,m,c,entry=PARENT,arguments=(g.E,),s={},connected=connected)
  self.service=g.Service(self.memory,c,self.target_home-24);self.fcsr=0;self.conversions=g.Counter();self.before_f=self.f[:];self.callbacks=[];self.revive=revive
 def record_call(self,t):
  if t==g.ENTRY:self.callbacks.append(tuple(self.arguments(1)));return
  if t in(CLEAN,RELEASE):self.pending=(t,tuple(self.arguments(1)));self.service.calls.append((t,self.pending[1],b''));return
  super().record_call(t)
 def hook(self,t):
  if t not in(CLEAN,RELEASE):return super().hook(t)
  assert self.pending==(t,(g.E,))
  if t==CLEAN:g.put(self.memory,g.E+14,0 if self.revive else -1,2);self.memory[g.E+13]^=0x20
  else:g.put(self.memory,g.MARK,0x87654321);self.memory[g.E+13]^=0x80
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=0xCAFEBABE
def check(words,c,flag,lifetime,selector,cleanup,revive,wrong_slot=False):
 initial=g.fixture(c);initial[g.E+13]=flag;initial[g.E+16]=cleanup;initial[g.E+17]=selector;g.put(initial,g.E+14,lifetime,2);g.put(initial,TICKS,3)
 for table,at in((CLEAN_TABLE,0x22EF80),(TABLE,0x22EFA8)):
  for i in range(10):g.put(initial,table+4*i,struct.unpack_from('>I',rom,at+4*i)[0])
 assert g.read(initial,TABLE+24)==g.ENTRY and g.read(initial,CLEAN_TABLE)==CLEAN
 if wrong_slot:g.put(initial,TABLE+24,g.ENTRY+4)
 expected=dict(initial);calls=[];callbacks=[]
 if flag:g.put(expected,g.E+14,g.half(lifetime-3),2)
 if selector==6:callbacks=[(g.E,)];expected,calls=g.reference(expected,c,home=g.STACK+c.phase-24)
 if g.half(g.read(expected,g.E+14,2))<0 and cleanup==0:
  calls.append((CLEAN,(g.E,),b''));g.put(expected,g.E+14,0 if revive else -1,2);expected[g.E+13]^=0x20
 if g.half(g.read(expected,g.E+14,2))<0:calls.append((RELEASE,(g.E,),b''));g.put(expected,g.MARK,0x87654321);expected[g.E+13]^=0x80
 q=Machine(words,initial,c,revive).run()
 assert(g.public(q.memory),q.service.calls,q.callbacks)==(g.public(expected),calls,callbacks),('parent relation',c,flag,lifetime,selector,cleanup,revive)
 return q
def main():
 dest=O/'connected-parent.json';assert not dest.exists();streams=g.programs();seen=set();n=0
 for route,flag,lifetime,selector,cleanup,revive,phase in itertools.product((0,1,2,4),(0,1),(-1,2,32767),(6,255),(0,255),(0,1),(0,8)):
  c=g.Case(seed=255 if revive else 17,mode=2,route=route,query=1,hit=revive,pattern=4,mutation=31,phase=phase)
  for label,words in streams.items():seen.update(check(words,c,flag,lifetime,selector,cleanup,revive).visits)
  n+=1
 assert len(seen&set(range(PARENT,PARENT+180,4)))==45
 controls=[]
 for name,wrong,words in [('wrong-table-target',True,streams['retail']),('wrong-expiry',False,[v if i!=0x44//4 else 0xA640000E for i,v in enumerate(streams['retail'])])]:
  try:check(words,g.Case(route=1),0,2,6,0,0,wrong)
  except(AssertionError,KeyError):controls.append(name)
  else:raise AssertionError(('ineffective connected control',name))
 report=dict(cases_per_stream=n,streams=list(streams),parent_words=45,parent_words_visited=45,slot='D_8008A4E8[6]',original_tables=True,indirect_A0_owner=True,result_ignored=True,cleanup_and_release_bounded_providers=True,post_cleanup_lifetime_recheck=True,controls=controls,source_installed=source.installed(),c_match_credit=0)
 dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
