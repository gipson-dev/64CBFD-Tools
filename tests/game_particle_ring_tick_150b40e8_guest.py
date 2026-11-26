"""Ordered particle-ring model, complete literal execution, and finite domains."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_particle_ring_tick_150b40e8_match as target_packet
o=target_packet.OUT;ENTRY=0x150b40e8;TIMER=0x800be9e4;DT=0x800be9a4;OBJECT=0x30000;AUX=0x80000;RECORDS=0x50000
bits,floating=fp.bits,fp.floating;s8=lambda v:((v&255)^128)-128;s16=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 capacity:int=4
 head:int=3
 tail:int=0
 count:int=3
 flags:int=0
 delta:int=1
 lifetime:int=10
 dt:int=bits(.25)
 alias:int=0
 rm:int=0
 phase:int=0
 object:int=OBJECT
def records(c):return c.object+0x54 if c.alias==1 else RECORDS
def aux(c):return records(c)if c.alias==2 else AUX
def symbols(c):return dict(D_800BE9E4=TIMER,D_800BE9A4=records(c)if c.alias==3 else DT)
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-128,192)}
 for p,n in((c.object-32,208),(AUX-16,80),(records(c)-16,36*max(c.capacity,1)+64)):
  m.update({p+i:(i*29+0x5a)&255 for i in range(n)})
 for index in range(max(c.capacity,1)):
  p=records(c)+36*index
  for i,v in enumerate((1.5,-2.75,3.125,.125,-.25,.5,2.25)):put(m,p+4*i,bits(v+index*.0625))
  put(m,p+28,83,2);put(m,p+30,(c.lifetime if index&1 else -c.lifetime)&65535,2)
 put(m,aux(c)+12,bits(-.375));m[aux(c)+28]=c.flags;put(m,aux(c)+40,bits(.125))
 m[c.object+0x25]=c.capacity;m[c.object+0x2c]=c.count&255;m[c.object+0x2d]=c.tail&255;m[c.object+0x2e]=c.head&255
 put(m,c.object+0x94,records(c));put(m,c.object+0x98,aux(c));put(m,TIMER,c.delta&0xffffffff);put(m,symbols(c)['D_800BE9A4'],c.dt);return m
def reference(initial,c,s0=None,ra=None,initial_fcsr=None):
 m=dict(initial);owner=c.object;count=s8(m[owner+0x2c]);params=read(m,owner+0x98);base=read(m,owner+0x94);ops=[];fcsr=c.rm if initial_fcsr is None else initial_fcsr;iterations=0;drains=0
 def calc(a,b,fn):
  nonlocal fcsr
  ops.append((fn,a,b,fcsr));v,flags=arithmetic(a,b,fn,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return v
 if count<2 and m[params+28]&1:return m,ops,fcsr,0,iterations,drains
 index=s8(m[owner+0x2e]);tail=s8(m[owner+0x2d]);dt=symbols(c)['D_800BE9A4']
 while index!=tail:
  iterations+=1;assert iterations<=256,('outside finite outer domain',c)
  index-=1
  if index<0:index=m[owner+0x25]-1
  p=(base+36*index)&0xffffffff;put(m,p+28,255,2);put(m,p+30,(s16(read(m,p+30,2))-read(m,TIMER))&65535,2);expired=s16(read(m,p+30,2))<0
  product=calc(read(m,params+12),read(m,dt),2);put(m,p+16,calc(read(m,p+16),product,0))
  for dst,src in((0,12),(4,16),(8,20)):
   product=calc(read(m,p+src),read(m,dt),2);put(m,p+dst,calc(read(m,p+dst),product,0))
  product=calc(read(m,params+40),read(m,dt),2);put(m,p+24,calc(read(m,p+24),product,0))
  tail=s8(m[owner+0x2d])
  if expired and index!=tail:
   while True:
    drains+=1;assert drains<=512,('outside finite drain domain',c)
    m[owner+0x2d]=(m[owner+0x2d]+1)&255
    if s8(m[owner+0x2d])==m[owner+0x25]:m[owner+0x2d]=0
    m[owner+0x2c]=(m[owner+0x2c]-1)&255;tail=s8(m[owner+0x2d])
    if index==tail:break
  tail=s8(m[owner+0x2d])
 if s8(m[owner+0x2c])>0:
  for i in range(3):put(m,owner+0x54+4*i,read(m,(base+36*tail+4*i)&0xffffffff))
 else:
  for i in range(3):put(m,owner+0x54+4*i,0)
 return m,ops,fcsr,1,iterations,drains
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(c.object,)if arguments is None else arguments,s=symbols(c),connected=connected);self.initial=dict(self.memory);self.fcsr=c.rm;self.before_f=self.f[:];self.fp_operations=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in(0,2):
   rt,fs,fd,fn=w>>16&31,w>>11&31,w>>6&31,w&63;self.fp_operations.append((fn,self.f[fs],self.f[rt],self.fcsr));value,flags=arithmetic(self.f[fs],self.f[rt],fn,self.fcsr&3);self.f[fd]=value;self.fcsr=(self.fcsr&~0x3f000)|flags
  else:super().execute(w)
 def record_call(self,t):raise AssertionError(('leaf made a call',hex(t)))
 def hook(self,t):raise AssertionError(('leaf made a call',hex(t)))
def observable(m):return m.memory,m.fp_operations,m.fcsr,m.r[2]
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.fp_operations,m.trace
def check(words,c):
 m=Machine(words,c).run();wanted=reference(m.initial,c);expected=wanted[:4];actual=observable(m);assert actual==expected,dict(case=str(c),components=[a==b for a,b in zip(actual,expected)],diff=[hex(a)for a in m.memory if m.memory[a]!=wanted[0].get(a)][:8]);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[]
 for cap in range(1,7):
  rows +=[Case(capacity=cap,head=h,tail=t,count=n,lifetime=life,rm=(h+t)&3)for h,t,n,life in itertools.product(range(cap),range(cap),(0,1,2,255),(0,1,32767))]
 rows +=[Case(capacity=4,head=3,tail=0,count=count,flags=flag,delta=delta,lifetime=life,rm=rm,phase=8*(rm&1))for count,flag,delta,life,rm in itertools.product((128,255,0,1,2,127),(0,1),(-65536,-1,0,1,65536),(-32768,-1,0,1,32767),range(4))]
 rows +=[Case(capacity=3,head=2,tail=0,alias=alias,rm=rm,lifetime=life,object=STACK+32 if obj else OBJECT)for alias,rm,life,obj in itertools.product(range(4),range(4),(0,1),(0,1))]
 # Finite high-capacity domain: nonnegative tail and no expiration drain.
 rows +=[Case(capacity=cap,head=head,tail=0,count=2,delta=0,lifetime=0,rm=rm)for cap,head,rm in itertools.product((127,128,255),(0,1,127,128,255),range(4))]
 return rows
def main():
 files=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o'];cache={};seen=set();rows=cases()
 for c in rows:
  key=tuple(sorted(symbols(c).items()))
  if key not in cache:cache[key]=[bound_blob(*payload(o/f,'func_150B40E8'),symbols(c))for f in files]
  models=[check(ws,c)for ws in cache[key]];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(models[0].visits)
 prefixes=0
 for c in(Case(capacity=2,head=1,tail=0),Case(count=0,flags=1),Case(capacity=2,head=1,tail=0,alias=3)):
  streams=[bound_blob(*payload(o/f,'func_150B40E8'),symbols(c))for f in files];full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in streams:
    m=Machine(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing access boundary')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 controls=[];c=Case();words=bound_blob(*payload(o/'original-target.o','func_150B40E8'),symbols(c))
 for name,old,new in [('return',0x24020001,0x24020000),('opacity',0x240900ff,0x240900fe),('record-stride',0x24080024,0x24080020),('gravity-product',0x46062202,0x46062200)]:
  wrong=list(words);assert wrong.count(old)>=1;wrong=[new if w==old else w for w in wrong];m=Machine(wrong,c).run();assert observable(m)!=reference(m.initial,c)[:4];controls.append(dict(name=name,complete_supported_execution=True,rejected=True))
 missing=set(range(ENTRY,ENTRY+428,4))-seen;assert missing=={ENTRY+0x30},[hex(a)for a in missing]
 q=dict(cases_per_stream=len(rows),streams=5,executed_words=len(seen),unreachable_retail_load_words=[hex(a)for a in missing],per_instruction_raw_normalized_state_and_fault_order_equal=True,fault_prefix_quintuples=prefixes,complete_memory_no_frame_ABI_HILO_return_and_ordered_FP_comparison=True,finite_capacity1_to6_all_head_tail_pairs=True,signed_count_and_lifetime_boundaries=True,global_delta_low16_narrowing_and_repeated_float_reads=True,finite_high_capacity_no_drain_domain=True,arbitrary_invalid_ring_termination_not_claimed=True,record_owner_aux_coefficient_overlaps_guest_only=True,all_four_rounding_modes=True,finite_FP_model_not_hardware=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
