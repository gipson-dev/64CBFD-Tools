"""Literal MIPS execution against a separate ordered trail-ring reference."""
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
from tools.experiments import game_trail_record_update_151b77f4_match as target_packet
o=target_packet.OUT
ENTRY=0x151b77f4;LENGTH=0x15143e64;TABLE=0x8008fb90;TIMER=0x800be9e4
CALLBACKS=(0x151b7678,0x151b76cc);OBJECT=0x30000;AUX=0x80000;OTHER_AUX=0x81000;RECORDS=0x50000;OTHER_RECORDS=0x60000;ATTACHED=0x70000
bits,floating=fp.bits,fp.floating
signed=lambda v:((v&255)^128)-128
@dataclass(frozen=True)
class Case:
 head:int=0
 tail:int=2
 count:int=1
 capacity:int=4
 delta:int=1
 selector:int=0
 outcome:int=1
 attached:int=1
 mode:int=0
 alias:int=0
 pattern:int=0
 rm:int=0
 phase:int=0
 object:int=OBJECT
 distance:int=bits(3.25)
def symbols(c):return dict(func_15143E64=LENGTH,D_8008FB90=TABLE,D_800BE9E4=TIMER)
def records(c):return(RECORDS,c.object+0x10-20*signed(c.head),c.object+0x14-20*signed(c.head),c.object+0x94-20*signed(c.head))[min(c.alias,3)]
def attached(c):return 0 if not c.attached else c.object-0x30 if c.alias==4 else ATTACHED
def fixture(c):
 m={STACK+c.phase+i:(i*17+0xa5)&255 for i in range(-192,160)}
 for p,n in((c.object-32,220),(AUX-16,48),(OTHER_AUX-16,48),(ATTACHED-16,112)):
  m.update({p+i:(i*29+0x5a)&255 for i in range(n)})
 for base in(RECORDS,OTHER_RECORDS,records(c)):
  for index in{signed(c.head),-2,3}:
   for i in range(-16,48):m.setdefault((base+20*index+i)&0xffffffff,(i*13+c.pattern)&255)
 for i,v in enumerate((1.5,-2.75,3.125)):put(m,c.object+0x10+4*i,bits(v+c.pattern*.25))
 m[c.object+0x25]=c.capacity;m[c.object+0x2c]=c.count&255;m[c.object+0x2d]=c.tail&255;m[c.object+0x2e]=c.head&255
 put(m,c.object+0x94,records(c));put(m,c.object+0x98,AUX)
 put(m,AUX,attached(c));put(m,AUX+4,0x12340000);m[AUX+8]=c.selector
 put(m,OTHER_AUX,0);put(m,OTHER_AUX+4,0x87650000);m[OTHER_AUX+8]=1
 for i,t in enumerate(CALLBACKS):put(m,TABLE+4*i,t)
 put(m,TIMER,c.delta&0xffffffff);return m
def public(m,c):return {a:v for a,v in m.items()if not STACK+c.phase-192<=a<STACK+c.phase+160}
def effect(m,c,t,args):
 if t in CALLBACKS:
  for i,v in enumerate((4.25,-5.5,6.75)):put(m,args[1]+4*i,bits(v+c.pattern*.25))
  if c.mode&1:put(m,AUX,ATTACHED if not attached(c)else 0)
  if c.mode&2:put(m,c.object+0x94,OTHER_RECORDS);put(m,c.object+0x98,OTHER_AUX)
  if c.mode&4:m[c.object+0x2e]=254;m[c.object+0x2d]=255;m[c.object+0x2c]=127
 else:
  assert t==LENGTH
  if c.mode&8:
   for i,v in enumerate((-7.125,8.25,-9.5)):put(m,c.object+0x10+4*i,bits(v))
  if c.mode&16:put(m,c.object+0x94,OTHER_RECORDS);put(m,c.object+0x98,OTHER_AUX)
  if c.mode&32:m[c.object+0x2e]=3;m[c.object+0x2d]=0;m[c.object+0x2c]=255
def provider_fcsr(c,t):return c.rm|(0x10 if t in CALLBACKS else 0x20)
def reference(initial,c,s0,ra,initial_fcsr=None):
 m=dict(initial);home=STACK+c.phase;sp=home-72;put(m,sp+0x14,ra);calls=[];obs=[];ops=[];fcsr=c.rm if initial_fcsr is None else initial_fcsr
 owner=c.object;table=read(m,owner+0x94);aux=read(m,owner+0x98);put(m,sp+0x40,table)
 def call(t,args):
  nonlocal fcsr
  calls.append((t,args));obs.append((public(m,c),fcsr));effect(m,c,t,args)
  for i in range(4):put(m,sp+4*i,0xb5000000+i)
  fcsr=provider_fcsr(c,t)
 def copy(dst,src):
  for i in range(3):put(m,dst+4*i,read(m,src+4*i))
 if read(m,TIMER)&0x80000000 or read(m,TIMER)==0:return m,calls,obs,ops,fcsr,1
 copy(sp+0x34,owner+0x10);put(m,home,owner);put(m,sp+0x1c,owner+0x10);put(m,sp+0x44,aux)
 callback=read(m,TABLE+4*m[aux+8]);call(callback,(owner,owner+0x10))
 if not c.outcome:return m,calls,obs,ops,fcsr,0
 dest=read(m,aux)
 if dest:copy(dest+0x40,owner+0x10)
 for i in range(3):
  a,b=read(m,owner+0x10+4*i),read(m,sp+0x34+4*i);ops.append((1,a,b,fcsr));value,flags=arithmetic(a,b,1,fcsr&3);fcsr=(fcsr&~0x3f000)|flags;put(m,sp+0x28+4*i,value)
 call(LENGTH,(sp+0x28,));dest=(table+20*signed(m[owner+0x2e]))&0xffffffff
 # Ordered three-word copy also covers overlapping destination/source words.
 copy(dest,owner+0x10);put(m,dest+12,c.distance);m[dest+16]=255
 m[owner+0x2e]=(m[owner+0x2e]+1)&255
 if signed(m[owner+0x2e])==m[owner+0x25]:m[owner+0x2e]=0
 m[owner+0x2c]=(m[owner+0x2c]+1)&255
 if signed(m[owner+0x2d])==signed(m[owner+0x2e]):
  m[owner+0x2d]=(m[owner+0x2d]+1)&255
  if signed(m[owner+0x2d])==m[owner+0x25]:m[owner+0x2d]=0
  m[owner+0x2c]=(m[owner+0x2c]-1)&255
 return m,calls,obs,ops,fcsr,1
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(c.object,)if arguments is None else arguments,s=symbols(c),connected=connected);self.initial=dict(self.memory);self.fcsr=c.rm;self.before_f=self.f[:];self.observations=[];self.fp_operations=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==1:
   rt,fs,fd=w>>16&31,w>>11&31,w>>6&31;self.fp_operations.append((1,self.f[fs],self.f[rt],self.fcsr));value,flags=arithmetic(self.f[fs],self.f[rt],1,self.fcsr&3);self.f[fd]=value;self.fcsr=(self.fcsr&~0x3f000)|flags
  else:super().execute(w)
 def record_call(self,t):
  assert t in(*CALLBACKS,LENGTH),hex(t);args=tuple(self.arguments(1 if t==LENGTH else 2));self.calls.append((t,args));self.observations.append((public(self.memory,self.c),self.fcsr))
 def hook(self,t):
  effect(self.memory,self.c,t,self.calls[-1][1])
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.f[:20]=[0xa5000000+i for i in range(20)];self.f[0]=self.c.distance if t==LENGTH else 0xa5000000;self.r[2]=0xa5000000 if t==LENGTH else self.c.outcome;self.hi,self.lo=0xa5000010,0xa5000011;self.fcsr=provider_fcsr(self.c,t)
def observable(m):return m.memory,m.calls,m.observations,m.fp_operations,m.fcsr,m.r[2]
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations,m.fp_operations
def check(ws,c):
 m=Machine(ws,c).run();expected=reference(m.initial,c,m.before[16],m.before[31]);actual=observable(m)
 assert actual==expected,dict(case=str(c),components=[a==b for a,b in zip(actual,expected)],memory_differences=[hex(a)for a in m.memory if m.memory[a]!=expected[0].get(a)][:10])
 assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(head=h,tail=(h+1)&255,count=h,capacity=cap,selector=h&1,rm=h&3)for h,cap in itertools.product(range(256),(0,1,127,128,255))]
 rows +=[Case(mode=mode,selector=sel,attached=att,outcome=out,rm=mode&3,phase=8*(mode&1))for mode,sel,att,out in itertools.product(range(64),range(2),range(2),range(2))]
 rows +=[Case(alias=a,mode=mode,rm=rm,pattern=rm)for a,mode,rm in itertools.product(range(5),(0,3,8,15,32,63),range(4))]
 rows +=[Case(delta=delta,object=STACK+32 if obj else OBJECT,selector=selector)for delta,obj,selector in itertools.product((0,0xffffffff,0x80000000,0x7fffffff),(0,1),(0,1))]
 return rows
def main():
 files=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o'];streams=[bound_blob(*payload(o/f,'func_151B77F4'),symbols(Case()))for f in files];assert all(ws==streams[0]for ws in streams[2:]);seen=set();rows=cases()
 for c in rows:
  models=[check(ws,c)for ws in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(models[0].visits)
 prefixes=0
 for c in(Case(),Case(outcome=0),Case(alias=2),Case(mode=63)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in(streams[0],*streams[2:]):
    m=Machine(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing boundary')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])and m.trace==models[0].trace for m in models[1:]);prefixes+=1
 controls=[];c=Case(head=3,tail=0,capacity=4,mode=0);words=streams[0]
 for name,old,new in [('return',0x24020001,0x24020000),('opacity',0x240a00ff,0x240a00fe),('record-distance',0xe440000c,0xe4400014),('head-wrap',0xa0c0002e,0xa0c0002d)]:
  wrong=list(words);assert wrong.count(old)==1;wrong[wrong.index(old)]=new;m=Machine(wrong,c).run();assert observable(m)!=reference(m.initial,c,m.before[16],m.before[31]);controls.append(dict(name=name,complete_supported_execution=True,rejected=True))
 assert seen==set(range(ENTRY,ENTRY+420,4)),[hex(p)for p in set(range(ENTRY,ENTRY+420,4))-seen]
 q=dict(cases_per_stream=len(rows),streams=5,raw_and_normalized_final_machine_states_equal=True,executed_words=len(seen),literal_fault_prefix_quadruples=prefixes,raw_fault_prefix_equivalence_not_claimed=True,complete_memory_frame72_ABI_return_and_ordered_FP_reference=True,all_signed_head_count_bytes=True,unsigned_capacity_and_selector=True,captured_old_table_aux_and_post_provider_reloads=True,provider_mutations_and_overlapping_guest_objects=True,all_four_rounding_modes=True,opaque_callback_and_length_contracts_not_full_implementations=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
