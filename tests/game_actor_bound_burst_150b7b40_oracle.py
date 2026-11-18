"""Complete parent instruction screen with opaque provider contracts, not hardware."""
from pathlib import Path
from dataclasses import dataclass
import hashlib,itertools,json,math,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_actor_bound_burst_150b7b40_screen as source
p=source.OUT;f=source.FROZEN;ENTRY,ACTOR,MODEL=0x150B7B40,0x60000,0x68000
RNG,REAL,SINE,POSITION,TRANSFORM,BOUNDS=0x150ADA20,0x150ADA68,0x151423D8,0x15142314,0x15143134,0x1515C244
BURST,RADIAL,INIT,QUERY,FLOOR,CHILD,SPRAY=0x150B82D0,0x150B85C0,0x1504715C,0x15046C80,0x1514C678,0x15132A4C,0x15151A38
SIGNATURES={RNG:0,REAL:0,SINE:1,POSITION:3,TRANSFORM:3,BOUNDS:4,BURST:6,RADIAL:5,INIT:2,QUERY:4,FLOOR:12,CHILD:6,SPRAY:3}
SPANS={1:12,2:12,3:12,4:12,5:12,6:12,7:4,8:4,9:4,10:36,11:12,12:124,13:136}
data=lambda m,a,n:bytes(m[a+i]for i in range(n))
public=lambda m:{a:b for a,b in m.items()if not STACK-4096<=a<STACK+1024}
@dataclass(frozen=True)
class Case:
 model:int=0;zero:int=0;floor:int=0;profile:int=0;mutation:int=0;phase:int=0;seed:int=0;null:int=0
def cases():
 for model,zero,floor,profile,mutation in itertools.product((0,1),(0,1),(0,1),range(4),range(4)):
  seed=(11*model+17*zero+19*floor+23*profile+29*mutation)&255
  yield Case(model,zero,floor,profile,mutation,8*(seed&1),seed)
 yield Case(null=1)
def fixture(c):
 m={STACK+i:0xA5 for i in range(-4096,1024)}
 for a,n in((ACTOR,0x200),(MODEL,0x100)):m.update({a+i:(i*17+c.seed)&255 for i in range(n)})
 for off,v in((0x14,1.25),(0x18,2.5),(0x1c,3.75),(0x3c,1.5),(0x40,4.),(0xb8,5.),(0xc4,6.),(0x14c,(-.5,.75,2.,.5)[c.profile]),(0x150,(2.,.5,-1.,.75)[c.profile])):put(m,ACTOR+off,bits(v))
 put(m,ACTOR+0x1d4,MODEL if c.model else 0);put(m,ACTOR+0x184,0x12345678);put(m,ACTOR+0x76,0x4567,2)
 elf=(f/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,0x8009FD30,0x38);m.update({0x8009FD30+i:b for i,b in enumerate(elf[at:at+0x38])});return m
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry=ENTRY,initial=None,arguments=None,connected=None):
  super().__init__(words,fixture(c)if initial is None else initial,c,entry=entry,s={},arguments=(0 if c.null else ACTOR,0xABCD0000|c.seed,0x80000000|c.seed)if arguments is None else arguments,connected=connected)
  self.roles={};self.calls=[];self.integers=self.reals=0;self.saved=tuple(self.r[16:24])+tuple(self.r[28:]);self.saved_fp=tuple(self.f[20:])
 def execute(self,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==16 and fn in(4,5,7):
   v=self.f[w>>11&31];self.f[w>>6&31]=bits(math.sqrt(floating(v)))if fn==4 else v&0x7fffffff if fn==5 else v^0x80000000;return
  return super().execute(w)
 def role(self,k,address):
  assert STACK-4096<=address<STACK+1024 and address%4==0,(k,hex(address))
  if k in self.roles:assert self.roles[k]==address,(k,self.roles[k],address)
  else:
   assert not any(max(address,v)<min(address+SPANS[k],v+SPANS[i])for i,v in self.roles.items()),('overlapping roles',k)
   self.roles[k]=address
 def record_call(self,t):
  assert t in SIGNATURES,hex(t);a=tuple(self.arguments(SIGNATURES[t]));observed=()
  if t==POSITION:self.role({4:1,5:2,0:3}[a[1]],a[2])
  elif t==TRANSFORM:
   self.role({0x8009FD30:4,0x8009FD3C:5,0x8009FD48:6}[a[0]],a[1]);observed=data(self.memory,a[0],12)
  elif t==BOUNDS:
   for k,v in zip((4,8,7),a[1:]):self.role(k,v)
  elif t==BURST:
   for k,v in zip((4,7,8,9),a[:4]):self.role(k,v)
   observed=b''.join(data(self.memory,v,n)for v,n in zip(a[:4],(12,4,4,4)))
  elif t==RADIAL:
   for k,v in zip((4,7,8),a[:3]):self.role(k,v)
   observed=b''.join(data(self.memory,v,n)for v,n in zip(a[:3],(12,4,4)))
  elif t==INIT:self.role(10,a[0])
  elif t==QUERY:self.role(11,a[0]);self.role(10,a[3]);observed=data(self.memory,a[0],12)+data(self.memory,a[3],36)
  elif t==FLOOR:a=(self.f[12],self.f[14],*a[2:])
  elif t in(CHILD,SPRAY):
   k=12 if t==CHILD else 13;self.role(k,a[0]);observed=data(self.memory,a[0],SPANS[k])
  normalized=tuple(0xffffff00+next(k for k,v in self.roles.items()if v==n)if n in self.roles.values()else n for n in a)
  self.pending=t,a;self.calls.append((t,normalized,observed))
 def mutate(self):
  c=self.case;ordinal=len(self.calls)
  if c.mutation&1:
   for i,off in enumerate((0x14,0x18,0x1c,0x3c,0x40,0xb8,0xc4,0x14c,0x150)):put(self.memory,ACTOR+off,bits((ordinal%5+i+1)/4.))
   put(self.memory,ACTOR+0x76,(0x4567+ordinal*0x1100)&65535,2);put(self.memory,ACTOR+0x184,0x12340000|ordinal)
  if c.mutation&2:
   for k,a in self.roles.items():
    for i in range(1 if k in(7,8,9,10)else 3):put(self.memory,a+4*i,bits(((ordinal+k+i)%13+1)/4.))
 def hook(self,t):
  c=self.case;a=self.pending[1];answer=0;fvalue=None
  def vector(at,values):
   for i,v in enumerate(values):put(self.memory,at+4*i,bits(v))
  if t==POSITION:vector(a[2],(1.+a[1],2.+a[1],3.+a[1]))
  elif t==TRANSFORM:
   v=(a[0]-0x8009FD30)//12;vector(a[1],(0.,0.,0.)if c.zero else(1.+v*3,2.+v*3,3.+v*3))
  elif t==BOUNDS:vector(a[1],(1.25,2.5,3.75));put(self.memory,a[2],bits(0. if c.zero else 4.));put(self.memory,a[3],bits(0. if c.zero else 6.))
  elif t==SINE:fvalue=bits(((a[0]&255)-128)/128.)
  elif t==INIT:
   for i in range(36):self.memory[a[0]+i]=0
   put(self.memory,a[0],bits(7.5))
  elif t==QUERY:put(self.memory,a[3],bits(7.5));answer=c.floor
  elif t==RNG:answer=((0,25,0xffffffff,0x80000000)[c.profile]+self.integers*0x13579bdf)&0xffffffff;self.integers+=1
  elif t==REAL:fvalue=bits(.125+.0625*(self.reals%5));self.reals+=1
  elif t not in(BURST,RADIAL,FLOOR,CHILD,SPRAY):raise AssertionError(hex(t))
  self.mutate()
  for i in range(max(4,SIGNATURES[t])):put(self.memory,self.r[29]+4*i,0xb5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
  self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xDEADBEEF;self.r[2]=answer&0xffffffff
  if fvalue is not None:self.f[0]=fvalue
def streams():
 syms={v[1]:v[2][1]for v in symbol_rows((f/'conker/build/conker.us.elf').read_bytes())}
 answer=[('retail',list(struct.unpack('>484I',(p/'retail.bin').read_bytes())))]
 for label in('portable-11','captured-model'):answer.append((label,bound_blob(*payload(p/(label+'.o'),'func_150B7B40'),syms)))
 return answer
def main(programs=None):
 programs=streams()if programs is None else programs;results={};reports=[]
 for stream_index,(label,words)in enumerate(programs):
  base=ENTRY if stream_index==0 else 0x15200000
  seen=set();count=0;calls=0
  for i,c in enumerate(cases()):
   m=Oracle(words,c,base).run();result=(m.calls,public(m.memory),m.r[2])
   assert tuple(m.r[16:24])+tuple(m.r[28:])==m.saved and tuple(m.f[20:])==m.saved_fp
   if stream_index==0:results[i]=result
   else:
    if result!=results[i]:
     old=results[i][0];at=next((n for n,(a,b)in enumerate(zip(old,m.calls))if a!=b),None)
     raise AssertionError((label,c,'first unequal provider',at,old[at]if at is not None else None,m.calls[at]if at is not None else None))
   seen.update(m.visits&set(range(base,base+4*len(words),4)));count+=1;calls+=len(m.calls)
  if stream_index==0:assert seen==set(range(ENTRY,ENTRY+1936,4))-{0x150B7D60}
  row=dict(stream=label,cases=count,words=len(words),visited_words=len(seen),provider_calls=calls,full124_and136_byte_descriptors=True,hardware_runtime_unclaimed=True);reports.append(row);print(json.dumps(row),flush=True)
 report=dict(passes=True,streams=reports,private_padding_seed_coupling='uniform 0xA5 for finite guest screen only',complete_private_inductive_relation_pending=True,providers_and_both_children_modeled=True,native_qualification_separate=True,c_match_credit=0)
 (p/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
