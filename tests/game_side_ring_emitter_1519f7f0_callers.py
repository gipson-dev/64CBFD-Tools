"""Original helper/dispatcher evidence; transition fault is guest-only."""
from pathlib import Path
from functools import lru_cache
import itertools,json,struct
from tools.tests import game_side_ring_emitter_1519f7f0_oracle as g
from tools.tests import game_perpendicular_offset_1519ef90_oracle as offset
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
DISPATCH,RETIRE,HEADING,SAMPLE=0x15147740,0x1516972C,0x15143E08,0x151423D8
@lru_cache(None)
def original(entry,n):
 rom=(g.R/'conker/conker.us.bin').read_bytes();blob=rom[entry-0x15000000+0x2D4B0:entry-0x15000000+0x2D4B0+4*n]
 elf=(g.R/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,entry,len(blob));assert elf[at:at+len(blob)]==blob
 return list(struct.unpack('>'+str(n)+'I',blob))
def code(entry,n):return dict(zip(range(entry,entry+n*4,4),original(entry,n)))
def data(m):
 _,words,_=offset.helper_data()
 for p,v in words.items():g.put(m,p,v)
 g.put(m,g.S+0x68,g.bits(2.))
 g.put(m,g.P+0x20,g.bits(3.));g.put(m,g.P+0x24,g.bits(4.))
def actual_side(m,c,args,ordinal):
 p,mode,out=args;state=g.read(m,p);actor=g.read(m,state+0x18)
 if not g.read(m,actor+0x1D4):return 0
 op=lambda a,b,k:g.fp(a,b,k,c.rule)
 dx=op(g.read(m,actor+20),g.read(m,p+32),'sub');dz=op(g.read(m,actor+28),g.read(m,p+36),'sub')
 limit=g.floating(g.read(m,g.symbols()['D_800A8CE0']))
 if limit<abs(g.floating(dx)) or limit<abs(g.floating(dz)):
  inv=op(g.bits(1.),g.sqrt_word(op(op(dx,dx,'mul'),op(dz,dz,'mul'),'add')),'div')
  tx,tz=op(dz,inv,'mul'),op(dx,inv,'mul')
 else:
  heading=((g.read(m,actor+0x7A,2)>>8)+64)&255
  tx,tz=offset.sample(m,heading),offset.sample(m,(heading-64)&255)
 distance=g.read(m,state+0x68)
 if mode!=6:distance^=0x80000000
 g.put(m,out,op(g.read(m,actor+20),op(distance,tx,'mul'),'add'))
 g.put(m,out+8,op(g.read(m,actor+28),op(distance,tz,'mul'),'sub'))
 height=g.read(m,actor+0x118)
 g.put(m,out+4,g.read(m,actor+24) if g.floating(height)<g.floating(g.read(m,g.symbols()['D_800A8CE4'])) else height)
 return 1
class Connected(g.Machine):
 def __init__(self,w,m,c,entry=g.ENTRY,more=None):
  connected={**code(g.SIDE,94),**code(HEADING,7),**code(SAMPLE,27),**(more or {})}
  super().__init__(w,m,c,connected=connected)
  if entry!=g.ENTRY:
   # FactoryOracle's constructor takes the entry explicitly; initialize the
   # original parent rather than changing a running machine's program counter.
   g.FactoryOracle.__init__(self,w,m,g.BaseCase(phase=c.phase),entry=entry,s={},arguments=(g.E,),connected=connected)
 def record_call(self,t):
  if t in (HEADING,SAMPLE,RETIRE,g.ENTRY):
   a=tuple(self.arguments(1));self.raw_calls.append((t,a));self.calls.append((t,a));return
  return super().record_call(t)
 def hook(self,t):
  if t==RETIRE:self.r[2]=0;return
  return super().hook(t)
def side_queries(streams):
 count=0;helper_visits=set()
 for heading,mode,flags,move in itertools.product(range(256),(6,7),(0,4),(False,True)):
  c=g.Case(mode=mode,flags=flags,scale=g.bits(.125),height=g.bits(-9600.));m=g.fixture(c);data(m)
  g.put(m,g.T+0x7A,((heading-64)&255)<<8,2)
  if move:g.put(m,g.P+0x20,0);g.put(m,g.P+0x24,0)
  expected,result,calls,_=g.reference(m,c,side_provider=actual_side)
  for label,w in streams.items():
   q=Connected(w,m,c).run();root_calls=[x for x in q.calls if x[0] not in (HEADING,SAMPLE)]
   assert (g.public(q.memory,c),q.r[2],root_calls)==(g.public(expected,c),result,calls),(label,c,heading,move,root_calls,calls)
   assert not any(x[0] in (g.CLEAN,g.FACTORY,g.COPY) for x in q.calls)
   helper_visits|={pc for pc in q.visits if g.SIDE<=pc<g.SIDE+376}
  count+=1
 return count,len(helper_visits)
def dispatcher(streams):
 table=g.symbols()['D_8008A23C'];rom=(g.R/'conker/conker.us.bin').read_bytes();blob=rom[0x22ECFC:0x22ED44]
 elf=(g.R/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,table,len(blob));assert elf[at:at+len(blob)]==blob
 assert struct.unpack_from('>I',blob,20)[0]==g.ENTRY
 count=0
 for gate,mode,flags,phase in itertools.product(range(4),(6,7),(0,4),(0,8)):
  c=g.Case(gate=gate,mode=mode,flags=flags,phase=phase,scale=g.bits(.125),height=g.bits(-9600.));m=g.fixture(c);data(m)
  g.put(m,g.E+0x1E,c.flags&~2,2);m[g.E+0x2F]=0;m[g.E+0x30]=5
  for i,v in enumerate(blob):m[table+i]=v
  expected,result,calls,_=g.reference(m,g.replace(c,phase=phase-32),side_provider=actual_side)
  want=[(g.ENTRY,(g.E,))]+calls
  if not result:want.append((RETIRE,(g.E,)))
  for label,w in streams.items():
   q=Connected(original(DISPATCH,100),m,c,entry=DISPATCH,more=dict(zip(range(g.ENTRY,g.ENTRY+4*len(w),4),w))).run()
   actual=[x for x in q.calls if x[0] not in (HEADING,SAMPLE)]
   assert (g.public(q.memory,c),actual)==(g.public(expected,c),want),(label,c,actual,want)
  count+=1
 return count
def cleanup_fault(streams):
 # Inject an opaque query miss to reach the transition, then connect the
 # complete actual cleanup. This branch is outside the ordinary real-helper
 # invariant. Observe the exact low-address store; do not call it portable C.
 result=[]
 for mode,outcome in itertools.product((6,7),(0,1)):
  c=g.Case(mode=mode,hit=0,factory=outcome);m=g.fixture(c)
  for label,w in streams.items():
   q=g.Machine(w,m,c,connected=code(g.CLEAN,32));low=0x5C if mode==6 else 0x64
   try:q.run()
   except AssertionError as failure:assert failure.args==(('unmapped store',low,4),),failure
   else:raise AssertionError('Actual cleanup did not reach the retail unmapped output store')
   assert g.read(q.memory,g.P)==0
   assert all(low+i not in q.memory for i in range(4))
   assert g.read(q.memory,g.S+0x58+(0 if mode==6 else 8))==0
   if outcome:assert q.calls[-1][0]==g.COPY and q.calls[-1][2][:4]==b'\0'*4
   result.append(dict(stream=label,mode=mode,factory=outcome,unmapped_store=hex(low),store_not_performed=True))
 return result
def main():
 streams=g.programs();n,visits=side_queries(streams);parent=dispatcher(streams);faults=cleanup_fault(streams)
 report=dict(connected_side_cases_per_stream=n,original_side_words=94,original_heading_words=7,original_sample_words=27,side_visited_words=visits,
 parent_cases_per_stream=parent,original_dispatcher_words=100,callback_table='D_8008A23C',slot=5,cleanup_words=32,guest_low_address_observations=faults,
 opaque_query_miss_excluded_from_ordinary_real_helper_domain=True,hardware_faults_emulated=False,c_match_credit=0)
 (g.O/'connected-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
