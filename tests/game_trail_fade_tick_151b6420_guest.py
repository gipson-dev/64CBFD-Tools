"""Ordered trail-ring reference, emitted instruction execution and fault cuts."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_trail_fade_tick_151b6420_match as target_packet
o=target_packet.OUT;ENTRY=0x151b6420;TIMER=0x800be9e4;DT=0x800be9a4;FACTOR=0x800aa470;OBJECT=0x30000;RECORDS=0x50000
bits,floating=fp.bits,fp.floating;s8=lambda v:((v&255)^128)-128
@dataclass(frozen=True)
class Case:
 capacity:int=4
 head:int=3
 tail:int=0
 count:int=3
 flags:int=0
 dt:int=bits(.25)
 factor:int=0x3efced92
 life:int=bits(.5)
 distance:int=bits(100.)
 alias:int=0
 rm:int=0
 phase:int=0
 object:int=OBJECT
 delta:int=1
def records(c):return c.object+0x54 if c.alias==1 else RECORDS
def symbols(c):return dict(D_800BE9A4=records(c)+12 if c.alias==2 else DT,D_800AA470=records(c)+16 if c.alias==3 else FACTOR)
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-128,192)}
 for p,n in ((c.object-32,224),(records(c)-32,28*max(c.capacity,1)+96)):m.update({p+i:(i*29+0x5a)&255 for i in range(n)})
 for index in range(max(c.capacity,1)):
  p=records(c)+28*index
  for i,v in enumerate((1.5,-2.75,3.125)):put(m,p+4*i,bits(v+index*.0625))
  put(m,p+12,c.life if index&1 else bits(-floating(c.life)));m[p+16]=83;put(m,p+24,bits(floating(c.distance)*index))
 m[c.object+0x25]=c.capacity;m[c.object+0x2c]=c.count&255;m[c.object+0x2d]=c.tail&255;m[c.object+0x2e]=c.head&255;put(m,c.object+0x1e,c.flags,2);put(m,c.object+0x94,records(c));put(m,TIMER,c.delta&0xffffffff)
 syms=symbols(c);put(m,syms['D_800BE9A4'],c.dt);put(m,syms['D_800AA470'],c.factor);return m
def trunc(a):
 x=floating(a);v=math.trunc(x)if math.isfinite(x)else 0;valid=math.isfinite(x)and -(1<<31)<=v<(1<<31)
 return (v&0xffffffff if valid else 0x80000000),0x10040 if not valid else 0x1004 if v!=x else 0
def reference(initial,c,initial_fcsr=None):
 m=dict(initial);owner=c.object;base=read(m,owner+0x94);ops=[];fcsr=c.rm if initial_fcsr is None else initial_fcsr;outer=drains=fades=0
 def calc(a,b,fn):
  nonlocal fcsr
  ops.append((fn,a,b,fcsr));v,flags=arithmetic(a,b,fn,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;return v
 def comparison(a,b):
  nonlocal fcsr
  flag=floating(a)<floating(b);ops.append((60,a,b,fcsr));fcsr=(fcsr&~(0x800000|0x3f000))|(0x800000 if flag else 0);return flag
 if s8(m[owner+0x2c])<2 and read(m,owner+0x1e,2)&8:return m,ops,fcsr,0,outer,drains,fades
 index=s8(m[owner+0x2e])
 while index!=s8(m[owner+0x2d]):
  outer+=1;assert outer<=256,('unqualified outer termination',c);index-=1
  if index<0:index=m[owner+0x25]-1
  p=(base+28*index)&0xffffffff;put(m,p+12,calc(read(m,p+12),read(m,symbols(c)['D_800BE9A4']),1))
  if comparison(read(m,p+12),0):
   while index!=s8(m[owner+0x2d]):
    drains+=1;assert drains<=512,('unqualified drain termination',c);m[owner+0x2d]=(m[owner+0x2d]+1)&255
    if s8(m[owner+0x2d])==m[owner+0x25]:m[owner+0x2d]=0
    m[owner+0x2c]=(m[owner+0x2c]-1)&255
 if s8(m[owner+0x2c])>0:
  index=s8(m[owner+0x2d]);coefficient=read(m,symbols(c)['D_800AA470']);oldest=read(m,(base+28*index+24)&0xffffffff)
  while True:
   fades+=1;assert fades<=256,('unqualified fade termination',c);p=(base+28*index)&0xffffffff;difference=calc(read(m,p+24),oldest,1);product=calc(difference,coefficient,2);ops.append((13,product,0,fcsr));value,flags=trunc(product);fcsr=(fcsr&~0x3f000)|flags;signed=((value^0x80000000)-0x80000000);m[p+16]=min(signed,155)&255
   index+=1
   if index>=m[owner+0x25]:index=0
   if index==s8(m[owner+0x2e]):break
 if s8(m[owner+0x2c])>0:
  p=(base+28*s8(m[owner+0x2d]))&0xffffffff
  for i in range(3):put(m,owner+0x54+4*i,read(m,p+4*i))
 else:
  for i in range(3):put(m,owner+0x54+4*i,0)
 return m,ops,fcsr,1,outer,drains,fades
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(c.object,)if arguments is None else arguments,s=symbols(c),connected=connected);self.initial=dict(self.memory);self.fcsr=c.rm;self.before_f=self.f[:];self.fp_operations=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63 in (1,2,13,60):
   rt,fs,fd,fn=w>>16&31,w>>11&31,w>>6&31,w&63;a,b=self.f[fs],self.f[rt];self.fp_operations.append((fn,a,b if fn!=13 else 0,self.fcsr))
   if fn==60:
    self.condition=floating(a)<floating(b);self.fcsr=(self.fcsr&~(0x800000|0x3f000))|(0x800000 if self.condition else 0)
   else:
    value,flags=trunc(a)if fn==13 else arithmetic(a,b,fn,self.fcsr&3);self.f[fd]=value;self.fcsr=(self.fcsr&~0x3f000)|flags
  else:super().execute(w)
 def record_call(self,t):raise AssertionError(('leaf call',hex(t)))
 def hook(self,t):raise AssertionError(('leaf call',hex(t)))
def observable(m):return m.memory,m.fp_operations,m.fcsr,m.r[2]
def state(m,raw=False):return m.memory,m.r,m.f[20:]if raw else m.f,m.fcsr,m.hi,m.lo,m.calls,m.fp_operations,m.trace,m.current_pc,m.delay_of,m.condition
def check(words,c):
 m=Machine(words,c).run();want=reference(m.initial,c);assert observable(m)==want[:4],dict(case=str(c),components=[a==b for a,b in zip(observable(m),want[:4])],FP=m.fp_operations[:6],wantFP=want[1][:6]);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[]
 for cap in range(1,7):rows.extend(Case(capacity=cap,head=h,tail=t,count=n,life=life,rm=(h+t)&3)for h,t,n,life in itertools.product(range(cap),range(cap),(0,1,2,255),(bits(0.),bits(.5),bits(-.5))))
 rows.extend(Case(count=n,flags=f,life=l,dt=d,distance=dist,rm=rm,phase=8*(rm&1))for n,f,l,d,dist,rm in itertools.product((128,255,0,1,2,127),(0,8),(bits(-1),bits(1)),(bits(-.5),bits(.5)),(bits(-100),bits(1000)),range(4)))
 rows.extend(Case(alias=a,rm=rm,head=2,capacity=3,tail=0,life=bits(1.),object=STACK+32 if obj else OBJECT)for a,rm,obj in itertools.product(range(4),range(4),(0,1)))
 rows.extend(Case(head=h,tail=t,capacity=4,count=2,dt=0,life=0,rm=rm,factor=f,distance=d)for h,t,rm,f,d in itertools.product((0,3),(0,2),range(4),(1,bits(-.25),bits(1.)),(bits(0),bits(.0001),bits(1e10))))
 return rows
def main():
 files=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o'];cache={};seen=set();rows=cases()
 for c in rows:
  key=tuple(sorted(symbols(c).items()))
  if key not in cache:cache[key]=[bound_blob(*payload(o/f,'func_151B6420'),symbols(c))for f in files]
  models=[check(w,c)for w in cache[key]];assert all(state(m)==state(models[0])for m in models[2:]);assert state(models[1],raw=True)==state(models[0],raw=True);seen.update(models[0].visits)
 prefixes=0
 for c in (Case(),Case(count=0,flags=8),Case(capacity=3,head=2,tail=0,alias=2),Case(capacity=3,head=2,tail=0,alias=3)):
  streams=[bound_blob(*payload(o/f,'func_151B6420'),symbols(c))for f in files];full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing fault cut')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[2:]);assert state(models[1],raw=True)==state(models[0],raw=True);prefixes+=1
 controls=[];c=Case(head=3,tail=1,dt=bits(-.25),life=0,distance=bits(1000.));words=bound_blob(*payload(o/'original-target.o','func_151B6420'),symbols(c))
 for name,old,new in [('return',0x24020001,0x24020000),('maximum',0x2408009b,0x2408009a),('lifetime',0x46062201,0x46062200),('distance',0x46008081,0x46008080),('multiply',0x460e1482,0x460e1480)]:
  assert words.count(old)>=1;wrong=[new if w==old else w for w in words];m=Machine(wrong,c).run();assert observable(m)!=reference(m.initial,c)[:4],name;controls.append(dict(name=name,complete_supported_execution=True,rejected=True))
 missing=set(range(ENTRY,ENTRY+436,4))-seen;assert missing=={ENTRY+0x2c,ENTRY+0x13c,ENTRY+0x19c},[hex(x)for x in missing]
 q=dict(cases_per_stream=len(rows),streams=5,executed_words=len(seen),unreachable_retail_duplicate_load_store_words=[hex(x)for x in sorted(missing)],fault_prefix_quintuples=prefixes,normalized_full_private_state_and_fault_order_equal=True,raw_public_memory_GPR_HILO_ABI_FCSR_FP_operand_order_and_fault_access_equal=True,raw_dead_volatile_FPR_literal_identity_not_claimed=True,finite_capacity1_to6_all_head_tail_pairs=True,all_four_rounding_modes=True,finite_FP_model_not_hardware=True,guest_aliases_owner_records_DT_and_captured_coefficient=True,signed_byte_count_and_clamp_truncation_boundaries=True,arbitrary_invalid_ring_termination_not_claimed=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0)
 (o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
