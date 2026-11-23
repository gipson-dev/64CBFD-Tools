"""Independent packet/public model; original stack layout and caller window."""
from dataclasses import dataclass
import json,struct
from tools.experiments import game_linked_effect_151d1448_match as p
from tools.tests.game_owner_float_payload_oracle import FactoryOracle as Base,Case as BaseCase
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=p.ROOT,p.OUT;ENTRY=0x151D1448;OWNER=0x30000;ACTOR=0x80000;OTHER=0x88000;CHILD=0x50000;ROOT=0x60000;OUTA=0x70000;OUTB=0x71000
S={n:v[1]for _,n,v,_ in symbol_rows((o/'baseline/conker/build/conker.us.elf').read_bytes())if n}
u32=lambda x:x&0xffffffff
signed=lambda x:((x&0xffffffff)^0x80000000)-0x80000000
FLOATS=(0,0x80000000,0x3f800000,0xbf123456,0x7fc12345,0x7f800001,0x7f800000,0xff800000,0x00000001,0x7f7fffff)
@dataclass(frozen=True)
class Case:
 seed:int=0
 kind:int=37
 views:int=0
 channel:int=255
 context:int=128
 outcome:int=1
 mutation:int=0
 alias:int=0
 phase:int=0
 root:int=ROOT
 dest_alias:int=0
def cases():
 for seed in range(512):yield Case(seed,(37,0,255,1)[seed%4],(-2147483648,-1,0,1,4,2147483647)[seed%6],seed*31&255,(seed*17+128)&255,int(seed%5!=0),(seed//4)%8,int(seed%7==0),8*(seed&1))
 for seed in range(64):yield Case(seed+1024,37 if seed&1 else 1,(-1,0,1,2147483647)[seed%4],seed*7&255,255-seed,1,seed%8,seed&1,8*(seed&1))
 for root in(0x80000000,0x80008000,0x7fff8000,0xffffff00):
  for outcome in(0,1):yield Case(2048+outcome,1,-1,128,255,outcome,7,1,8*outcome,root)
def actor(c):return OWNER if c.alias else ACTOR
def positions(c):return tuple(FLOATS[(c.seed+i*3)%len(FLOATS)]for i in range(3))
def value(c):return FLOATS[(c.seed+7)%len(FLOATS)]
def fixture(c,s=None):
 s=S if s is None else s;m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2304)}
 for base,size in((OWNER,512),(ACTOR,512),(OTHER,512),(CHILD,160),(c.root,160),(OUTA,32),(OUTB,32)):
  assert base+size+16<=STACK-2048 or base-16>=STACK+2304,('Public fixture overlaps private stack',hex(base))
  m.update({u32(base+i):(i*29+c.seed*11+0x51)&255 for i in range(-16,size+16)})
 put(m,OWNER+0x28,actor(c));put(m,OWNER+0x30,CHILD);m[OWNER+1]=c.context&255;m[OWNER+0xc]=c.channel&255;m[actor(c)+4]=c.kind&255
 for at in(OWNER,ACTOR,OTHER):put(m,at+0x14c,value(c)if at==actor(c)else 0x3f400000)
 for i,v in enumerate(positions(c)):put(m,OWNER+0x40+4*i,v)
 put(m,c.root+0x98,OUTA);put(m,s['D_80082FA0'],c.views)
 for base in(OUTA,OUTB):
  put(m,base,0);put(m,base+4,0x3f000000+(c.seed&255));m[base+8]=0x5a
  for i in range(5):put(m,base+12+4*i,0x41000000+i*0x100+(c.seed&255))
 return m
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def config_words(m,at):return(read(m,at),read(m,at+4),m[at+8],*(read(m,at+12+4*i)for i in range(5)))
def request_words(m,at):return(*(read(m,at+4*i)for i in range(3)),read(m,at+12,2),read(m,at+14,2),read(m,at+16),m[at+20],m[at+21],read(m,at+24))
def service(m,c,a,s):
 original=actor(c)
 if c.mutation&1:
  m[OWNER+1]^=0x55;m[OWNER+0xc]^=0x5a;m[original+4]^=37;put(m,OWNER+0x28,OTHER);put(m,original+0x14c,0xc1200000);put(m,OTHER+0x14c,0x42c80000);put(m,s['D_80082FA0'],1)
  for i in range(3):put(m,OWNER+0x40+4*i,0x41200000+i*0x200000)
 if c.mutation&2:put(m,OWNER+0x30,0)
 if c.mutation&4:
  put(m,a[0]+14,read(m,a[0]+14,2)^1,2);put(m,a[0]+16,read(m,a[0]+16)^0x10);put(m,a[0]+4,read(m,a[0]+4)^0x80000000)
 if c.outcome:put(m,c.root+0x98,OWNER+c.dest_alias if c.dest_alias else OUTB if c.mutation&2 else OUTA)
 return c.root if c.outcome else 0
def reference(initial,c,s=None,home=None):
 s=S if s is None else s;m=initial.copy();home=STACK+c.phase if home is None else home;request=home-64;config=home-36;calls=[];observations=[]
 put(m,config,OWNER);put(m,config+4,0);m[config+8]=255
 if m[actor(c)+4]==37:values=(0x44480000,0x42100000,0x42480000,0x43480000)
 else:values=(0x43820000 if signed(read(m,s['D_80082FA0']))>0 else 0x43fa0000,0x42200000,0x42200000,0x43340000)
 for i,v in enumerate(values):put(m,config+12+4*i,v)
 put(m,config+28,read(m,read(m,OWNER+0x28)+0x14c))
 for i in range(3):put(m,request+4*i,read(m,OWNER+0x40+4*i))
 put(m,request+12,300,2);put(m,request+14,54,2);put(m,request+16,19);m[request+20]=6;m[request+21]=25;put(m,request+24,0)
 a=(request,32,40,0,17,18,0,0,0,m[OWNER+0xc],m[OWNER+1]);calls.append((s['func_15147A80'],a));observations.append(('request',data(m,request,28)));created=service(m,c,a,s)
 if created:
  dest=read(m,created+0x98);a=(dest,config,32);calls.append((s['memcpy'],a));copy=data(m,config,32);observations.append(('copy',dest,copy,read(m,OWNER+0x30)))
  for i,b in enumerate(copy):m[u32(dest+i)]=b
  put(m,OWNER+0x30,created)
 return m,calls,observations
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2304}
class Oracle(Base):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None):
  self.c=c;self.s=S if s is None else s;self.observed=[]
  super().__init__(words,initial.copy(),BaseCase(phase=c.phase),entry=entry,s={},connected=connected,arguments=(OWNER,));self.fp_before=list(self.f);self.entry_sp=self.r[29]
 def record_call(self,target):
  counts={self.s['func_15147A80']:11,self.s['memcpy']:3,ENTRY:1};assert target in counts,hex(target);a=tuple(map(u32,self.arguments(counts[target])));self.calls.append((target,a));self.events.append(('CALL',target,a))
  if target==self.s['func_15147A80']:self.observed.append(('request',data(self.memory,a[0],28)))
  elif target==self.s['memcpy']:self.observed.append(('copy',a[0],data(self.memory,a[1],a[2]),read(self.memory,OWNER+0x30)))
 def hook(self,target):
  a=self.calls[-1][1]
  if target==self.s['func_15147A80']:result=service(self.memory,self.c,a,self.s)
  else:
   assert target==self.s['memcpy']and a[2]<=64
   for i,b in enumerate(data(self.memory,a[1],a[2])):self.memory[u32(a[0]+i)]=b
   result=a[0]
  for i in range(11 if target==self.s['func_15147A80']else 4):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(result)
def streams():return{label:bound_blob(*payload(o/path,p.FUNCTION),S)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.events,m.calls,m.observed,m.dispatched_word)
def check(m,initial,c,s=None,caller=False):
 expected,calls,observed=reference(initial,c,s);prefix=[(ENTRY,(OWNER,))]if caller else[]
 assert public(m.memory)==public(expected),(c,'public');assert m.calls==prefix+calls,(c,'calls');assert m.observed==observed,(c,'packet observations');assert m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30:]==m.before[30:]and m.f[20:]==m.fp_before[20:],(c,'saved')
 assert m.r[29]==m.entry_sp+(0x38 if caller else 0)
def main():
 programs=streams();assert len({tuple(v)for v in programs.values()})==1;assert struct.pack('>98I',*programs['retail'])==(r/'conker/conker.us.bin').read_bytes()[0x1fe8f8:0x1fea80];visits=set();count=0
 for c in cases():
  initial=fixture(c);models=[]
  for ws in programs.values():m=Oracle(ws,initial,c);m.run();check(m,initial,c);models.append(m)
  assert all(state(m)==state(models[0])for m in models[1:]);visits.update(models[-1].visits);count+=1
 q=dict(cases_per_stream=count,streams=4,direct_instruction_and_binding_identity=True,independent_public_memory_calls_and_both_packets_equal=True,all_guest_private_bytes_and_saved_registers_equal=True,guest_padding_preserved=True,unexecuted_original_words=[i for i in range(98)if ENTRY+4*i not in visits],source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
def faults():
 programs=list(streams().values());count=0
 for c in(Case(),Case(kind=1,views=-1),Case(kind=1,views=1,mutation=7),Case(outcome=0),Case(alias=1,mutation=3)):
  initial=fixture(c);complete=Oracle(programs[-1],initial,c);complete.run()
  for cut in range(complete.all_accesses):
   states=[]
   for ws in programs:
    m=Oracle(ws,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    states.append(state(m))
   assert all(v==states[0]for v in states[1:]);count+=1
 q=dict(full_state_and_dispatched_word_access_prefix_quadruples=count,direct_raw_binary_fault_prefix_equal=True,portable_C_fault_claim=False);(o/'faults.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
def callers():
 rom=(r/'conker/conker.us.bin').read_bytes();words=struct.unpack('>6I',rom[0x1fe7c0:0x1fe7d8]);assert words==(0x0d474512,0x8fa40038,0x8fbf0014,0x27bd0038,0x03e00008,0);count=0
 for c in list(cases())[::12]:
  for ws in streams().values():
   initial=fixture(c);m=Oracle(words,initial,c,entry=0x151d1310,connected=dict(zip(range(ENTRY,ENTRY+392,4),ws)));put(m.memory,STACK+c.phase+0x38,OWNER);put(m.memory,STACK+c.phase+0x14,m.before[31]);m.before[29]=m.entry_sp+0x38;start=m.memory.copy();m.run();check(m,start,c,caller=True)
  count+=1
 q=dict(original_caller_window_words=6,entry='0x151D1310',actual_delay_load_from_caller_home=True,original_caller_epilogue_restores_return=True,cases_per_stream=count,unrecovered_full_caller_credit=0,scope='Literal call and common epilogue from func_151D1138; not full caller or factory implementation acceptance.');(o/'callers.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
def aliases():
 count=0
 for offset in(0x28,0x30,0x40):
  c=Case(kind=1,views=-1,mutation=1,alias=1,dest_alias=offset);initial=fixture(c)
  for ws in streams().values():m=Oracle(ws,initial,c);m.run();check(m,initial,c)
  count+=1
 q=dict(guest_only_public_payload_overlap_cases=count,native_alias_or_padding_bits_claimed=False);(o/'aliases.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());return q
if __name__=='__main__':main();print(json.dumps(faults()));print(json.dumps(callers()));print(json.dumps(aliases()))
