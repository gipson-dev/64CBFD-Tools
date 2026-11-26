"""Literal direct-C emitter streams, complete seeded packets and helper footprint."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_actor_direction_point_oracle import DirectionOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_optional_emitter_150d728c_match as target_packet
r=target_packet.ROOT;o=target_packet.OUT;ENTRY=0x150D728C;PRE=(0x151C04F8,0x151C05A4,0x151C05F0);SETUP=0x151BFC40;EMIT=(0x1514FB98,0x1514FBFC);POSITION=0x300000;DIRECTION=0x301000;MATRIX=0x302000;ALTERNATE=0x303000;MARK=0x304000;PLAYERS=0x80082FA0;MODE=0x8008FD8C;DEFAULTS=0x800AA97C;u32=lambda x:x&0xFFFFFFFF;signed=lambda x:((x&0xFFFFFFFF)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 matrix:int=MATRIX
 slot:int=255
 context:int=1
 position:int=POSITION
 direction:int=DIRECTION
 values:tuple=(0,0x80000000,0x3F800001)
 mutation:int=0
 connected:int=0
 players:int=1
 mode:int=0
 phase:int=0
 seed:int=0
 csr:int=0x2004
def symbols():return dict(zip(('func_151C04F8','func_151C05A4','func_151C05F0','func_151BFC40','func_1514FB98','func_1514FBFC'),(*PRE,SETUP,*EMIT)))
def arguments(c):return(c.matrix,c.position,c.direction,c.slot,c.context)
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+2048}
def fixture(c):
 m={STACK+c.phase+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2048)}
 for base,n in((POSITION-32,128),(DIRECTION-32,128),(MATRIX-32,128),(ALTERNATE-32,128),(MARK,32),(PLAYERS-8,20),(MODE-8,20),(DEFAULTS-8,40)):m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for p in(c.position,c.direction):
  for i,v in enumerate(c.values):put(m,p+4*i,v)
 put(m,PLAYERS,c.players);m[MODE]=c.mode&255
 for i,v in enumerate((0x3DCCCCCD,0x3E4CCCCD,0xBF800001,0x00000001,0x80000000)):put(m,DEFAULTS+4*i,v)
 return m
def effect(m,c,t,args):
 put(m,MARK,read(m,MARK)+1);home=STACK+c.phase
 if t in PRE and c.mutation&1:
  i=PRE.index(t)
  for j,v in enumerate((0x3F000001+i,0xBF400000+i,0x40000001+i)):put(m,c.position+4*j,v);put(m,c.direction+4*j,v^0x80000000)
  if c.matrix:put(m,c.matrix+i*2,0x1234+i,2)
 if t==PRE[0]and c.mutation&2:
  for i,v in enumerate((0 if c.matrix else ALTERNATE,ALTERNATE,ALTERNATE,0x12340080,0xFEDCBA98)):put(m,home+4*i,v)
 if t==SETUP and c.mutation&4:
  for i,v in enumerate((0x41100000,0xC1200000,0x41300000)):put(m,c.position+4*i,v);put(m,c.direction+4*i,v^0x80000000)
def setup(m,p,radius):
 players=signed(read(m,PLAYERS));mode=((m[MODE]^128)-128);half=players>=2;reduced=half or mode>=8
 for off,v in((0,3),(4,4>>half),(0x14,read(m,DEFAULTS)),(0x18,read(m,DEFAULTS+4)),(0x1C,0x42340000),(0x20,0x42540000),(0x24,0x434B0000),(0x28,0x43CF0000),(0x2C,7),(0x30,3>>reduced),(0x34,0x41700000),(0x38,read(m,DEFAULTS+8)),(0x3C,read(m,DEFAULTS+12)),(0x40,read(m,DEFAULTS+16))):put(m,p+off,v)
 for off,v in((0x44,25),(0x46,15),(0x48,100),(0x4A,100),(0x4C,12),(0x4E,20)):put(m,p+off,v,2)
 m[p+0x50]=255 if reduced else 0;put(m,radius,0x43F70000)
def reference(initial,c,initial_csr=None):
 m=dict(initial);home=STACK+c.phase
 for i,v in enumerate(arguments(c)):
  if i in(0,3,4):put(m,home+4*i,v)
 calls=[];ops=[];observations=[];csr=c.csr if initial_csr is None else initial_csr
 def call(t,args):
  calls.append((t,tuple(map(u32,args))))
  if t==SETUP:
   setup(m,*args)
   if c.connected:return
  effect(m,c,t,args)
 def negate(v):
  nonlocal csr
  assert v&0x7F800000!=0x7F800000;ops.append((7,v,csr));csr&=~0x3F000;return v^0x80000000
 for t in PRE:call(t,(c.position,c.slot&255,read(m,home+16)))
 rotation=read(m,home);oriented=rotation!=0;p=home-264+(144 if oriented else 44);body=p+(36 if oriented else 16);radius=p+(32 if oriented else 12)
 for i in range(3):put(m,p+4*i,negate(read(m,c.direction+4*i)))
 if oriented:
  # Retail copies four unaligned words then its final aligned halfword.
  for off,n in((0,4),(4,4),(8,4),(12,4),(16,2)):
   value=read(m,rotation+off,n);put(m,p+12+off,value,n)
  for i in range(3):put(m,body+8+4*i,read(m,c.position+4*i))
 call(SETUP,(body,radius))
 if not oriented:
  for i in range(3):put(m,body+8+4*i,read(m,c.position+4*i))
 t=EMIT[oriented];observations.append((t,data(m,p,120 if oriented else 100)));call(t,(p,c.slot&255,read(m,home+16)));return m,calls,ops,observations,csr
@lru_cache(None)
def helper_words():
 blob=(r/'conker/conker.us.bin').read_bytes()[0x1ED0F0:0x1ED250];old=(o/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(old,SETUP,len(blob));assert old[at:at+len(blob)]==blob;return list(struct.unpack('>88I',blob))
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,connected=None):
  code={}if connected is None else dict(connected)
  if c.connected:code.update(zip(range(SETUP,SETUP+352,4),helper_words()))
  self.c=c;self.observed=[];self.ops=[];super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,s=symbols(),connected=code,arguments=arguments(c));self.initial=dict(self.memory);self.fcsr=c.csr;self.before_f=self.f[:]
 def execute(self,w):
  if w>>26 in(34,38,42,46):return DirectionOracle.execute(self,w)
  if w>>26==0 and w&63==7:
   rs,rt,rd=w>>21&31,w>>16&31,w>>11&31;self.r[rd]=u32(signed(self.r[rt])>>(self.r[rs]&31));self.r[0]=0
  elif w>>26==17 and w>>21&31==16 and w&63==7:
   fs,fd=w>>11&31,w>>6&31;v=self.f[fs];assert v&0x7F800000!=0x7F800000;self.ops.append((7,v,self.fcsr));self.f[fd]=v^0x80000000;self.fcsr&=~0x3F000
  else:super().execute(w)
 def record_call(self,t):
  counts={**dict.fromkeys(PRE,3),SETUP:2,EMIT[0]:3,EMIT[1]:3};assert t in counts,hex(t);args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t in EMIT:self.observed.append((t,data(self.memory,args[0],120 if t==EMIT[1]else 100)))
 def hook(self,t):
  args=self.calls[-1][1]
  if t==SETUP:setup(self.memory,*args)
  effect(self.memory,self.c,t,args)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xDEADBEEF
def state(m):return(m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.ops,m.observed,m.trace,m.current_pc,m.delay_of,m.condition)
def check(words,c):
 m=Machine(words,c).run();memory,calls,ops,obs,csr=reference(m.initial,c);got=(public(m.memory,c),m.calls,m.ops,m.observed,m.fcsr);want=(public(memory,c),calls,ops,obs,csr);assert got==want,dict(case=str(c),parts=[a==b for a,b in zip(got,want)]);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[]
 for i,(matrix,slot,mutation,connected,phase)in enumerate(itertools.product((0,MATRIX,MATRIX+2),(0,255,0x87654380),range(8),(0,1),(0,8))):
  values=((0,0x80000000,0x3F800001),(1,0x807FFFFF,0x7F7FFFFF),(0xC1200000,0x3EAAAAAB,0x80000001))[i%3];rows.append(Case(matrix=matrix,slot=slot,context=(1,0x80000000,0xFFFFFFFF)[i%3],values=values,mutation=mutation,connected=connected,players=(-1,1,2,7)[i%4],mode=(0,7,8,255)[(i//4)%4],phase=phase,seed=i,csr=(i%4)|0x23004))
 return rows
def main():
 files=('original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o');streams=[bound_blob(*payload(o/f,'func_150D728C'),symbols())for f in files];assert all(w[:98]==streams[0]for w in streams);seen=set();count=0
 for c in cases():
  models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for m in models);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+392);count+=1
 cuts=0
 for c in(Case(),Case(matrix=0),Case(matrix=MATRIX+2,mutation=3,phase=8),Case(matrix=0,connected=1,players=2,mode=8)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for w in streams:
    m=Machine(w,c);m.cut=cut
    try:m.run();raise AssertionError('Missing fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models);cuts+=1
 dead=[hex(x)for x in sorted(set(range(ENTRY,ENTRY+392,4))-seen)];assert dead==['0x150d73a0'],dead
 q=dict(cases_per_stream=count,streams=5,retail_body_words=98,retail_padding_words=3,executed_body_words=len(seen),unreachable_original_words=dead,full_private_states_equal=True,fault_prefix_quintuples=cuts,ordered_finite_NEG_and_FCSR_equal=True,complete100_or120byte_seeded_packets_compared=True,unknown_packet_padding_only_guest_observed=True,actual88word_setup_helper_connected=True,two_aligned_matrix_offsets_qualified=True,captured_position_direction_and_slot_with_live_optional_pointer_and_fifth_home=True,point_position_reloaded_after_setup_oriented_position_captured_before_setup=True,guest_only_incoming_home_mutations=True,precursors_and_factories_opaque=True,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
