"""Independent resource-motion semantics and literal access/fault checks."""
import itertools,json,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_resource_motion_151563b8_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
ENTRY,REMOVE,OBJECT,MARK=0x151563B8,0x1516972C,0x30000,0x70000
SYMS=dict(D_800BE9E4=0x800BE9E4,D_800BE9A4=0x800BE9A4,func_1516972C=REMOVE)
u32=lambda v:v&0xFFFFFFFF
half=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 flags:int=9
 remaining:int=10
 ticks:int=1
 step:int=0x3F000000
 threshold:int=20
 rate:int=3
 alpha:int=255
 seed:int=0
 phase:int=0
 object:int=OBJECT
 alias:int=0
 mutation:int=0

def symbols(c,s=None):
 s=dict(SYMS if s is None else s)
 if c.alias:s['D_800BE9A4']=u32(c.object+(0x10,0x14,0x28,0x30)[c.alias-1])
 return s

def fixture(c,s=None):
 s=symbols(c,s);m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,2048)}
 for base,size in((c.object-16,0x1F8),(MARK,16)):
  m.update({u32(base+i):(i*29+c.seed*11+0x5A)&255 for i in range(size)})
 for j,off in enumerate((0x10,0x14,0x18,0x1C,0x20,0x24,0x28,0x2C,0x30,0x34,0x38,0x3C)):
  value=((j-5)*.25,(j+1)*-1.5,0.,(j-3)*1024.125)[c.seed%4]
  put(m,u32(c.object+off),bits(value))
 m[u32(c.object+0x40)]=c.flags;put(m,u32(c.object+0x42),c.remaining,2)
 m[u32(c.object+0x4C)]=c.alpha;put(m,u32(c.object+0x4E),c.threshold,2);put(m,u32(c.object+0x50),c.rate,2)
 put(m,s['D_800BE9E4'],c.ticks);put(m,s['D_800BE9A4'],c.step)
 return m

def data(m,p,n=0x1D8):return bytes(m[u32(p+i)]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def effect(m,c,s):
 put(m,MARK,0x13579BDF)
 if c.mutation:
  for i in range(0x54):m[u32(c.object+i)]=(i*7+0xC3)&255
  put(m,s['D_800BE9A4'],bits(7.25));put(m,s['D_800BE9E4'],0xDEADBEEF)

def reference(initial,c,s=None):
 s=symbols(c,s);m=dict(initial);p=c.object;expired=False;calls=[];snapshots=[]
 if m[u32(p+0x40)]&1:
  timer=half(read(m,u32(p+0x42),2)-read(m,s['D_800BE9E4']))
  put(m,u32(p+0x42),timer,2);expired=timer<0
 if not expired:
  fade=m[u32(p+0x40)]&8
  for destination,velocity in((0x10,0x1C),(0x14,0x20),(0x18,0x24),(0x28,0x34),(0x2C,0x38),(0x30,0x3C)):
   product=fp(read(m,u32(p+velocity)),read(m,s['D_800BE9A4']),'mul')
   put(m,u32(p+destination),fp(read(m,u32(p+destination)),product,'add'))
  remaining=half(read(m,u32(p+0x42),2))
  if fade and remaining<half(read(m,u32(p+0x4E),2)):
   alpha=half(remaining*half(read(m,u32(p+0x50),2)))
   if alpha<m[u32(p+0x4C)]:m[u32(p+0x4C)]=alpha&255
 else:
  calls.append((s['func_1516972C'],(u32(p),)))
  snapshots.append((u32(p),data(m,p),read(m,s['D_800BE9E4']),read(m,s['D_800BE9A4'])))
  effect(m,c,s)
 return m,calls,snapshots

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None,arguments=None):
  self.snapshots=[]
  super().__init__(words,memory,c,entry=entry,s=symbols(c,s),connected=connected,arguments=(u32(c.object),)if arguments is None else arguments)
  self.saved_f=self.f[20:].copy()
 def record_call(self,t):
  assert t==self.syms['func_1516972C'],hex(t)
  a=(u32(self.r[4]),);self.calls.append((t,a));self.events.append(('CALL',t,a))
  self.snapshots.append((a[0],data(self.memory,a[0]),read(self.memory,self.syms['D_800BE9E4']),read(self.memory,self.syms['D_800BE9A4'])))
 def hook(self,t):
  effect(self.memory,self.case,self.syms)
  for i in range(4):self.put(u32(self.r[29]+i*4),0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def cases():
 for flags in range(256):yield Case(flags=flags,remaining=(0,1,32767,32768,65535)[flags%5],ticks=(0,1,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[flags%5],seed=flags%4,phase=(flags&1)*8)
 for timer,ticks in itertools.product((0,1,2,32767,32768,32769,65535),(0,1,2,32767,32768,0x7FFFFFFF,0x80000000,0x80000001,0xFFFFFFFF)):
  for flags in(0,1,8,9):yield Case(flags=flags,remaining=timer,ticks=ticks,seed=timer%4,mutation=1,phase=(timer&1)*8)
 for timer,threshold,rate,alpha in itertools.product((0,1,2,32767,32768,65535),(0,1,2,32767,32768,65535),(0,1,32767,32768,65535),(0,1,127,255)):
  yield Case(flags=8,remaining=timer,threshold=threshold,rate=rate,alpha=alpha,seed=(timer+rate)%4)
 for step,seed in itertools.product((0,0x80000000,bits(.125),bits(-.5),bits(1024.25),bits(1e20),0x7F800000,0x7FC01234),range(4)):
  yield Case(flags=8,step=step,seed=seed)
 for alias,flags in itertools.product(range(1,5),(0,1,8,9)):
  yield Case(flags=flags,alias=alias,seed=alias%4)
 for p in(0,0xFFFFFFC0):yield Case(object=p,flags=8,step=bits(-.5))

def native_cases():
 seen=set()
 for c in cases():
  if c.alias or c.object!=OBJECT or c.step in(0x7F800000,0x7FC01234):continue
  c=replace(c,phase=0)
  if c not in seen:seen.add(c);yield c

def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.snapshots,m.trace,m.current_pc,m.delay_of,m.dispatched_word)
def check(m,initial,c,s=None):
 expected,calls,snaps=reference(initial,c,s)
 assert(public(m.memory),m.calls,m.snapshots)==(public(expected),calls,snaps),c
 assert m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[31]==m.before[31]and m.f[20:]==m.saved_f,c

def raw_words(s=SYMS):
 text,fs,rs=parse_object(out/'qualified-owner.o');f=fs['func_151563B8'];refs={a-f['value']:v for a,v in rs.items()if f['value']<=a<f['value']+f['size']}
 return bound_blob(text[f['value']:f['value']+f['size']],refs,s)

def retail_words(s=SYMS):
 words=list(struct.unpack('>80I',(out/'retail-slot.bin').read_bytes()))
 for hi,lo,name in((16,36,'D_800BE9E4'),(28,68,'D_800BE9A4')):
  i,j=hi//4,lo//4;v=s[name]
  assert words[i]&65535==((SYMS[name]+32768)>>16)&65535
  assert words[j]&65535==SYMS[name]&65535
  words[i]=(words[i]&0xFFFF0000)|(((v+32768)>>16)&65535)
  words[j]=(words[j]&0xFFFF0000)|(v&65535)
 assert words[74]>>26==3
 words[74]=(words[74]&0xFC000000)|((s['func_1516972C']>>2)&0x3FFFFFF)
 return words

def main():
 truth=list(struct.unpack('>80I',(out/'retail-slot.bin').read_bytes()));visits=set();n=accesses=0
 for c in cases():
  s=symbols(c);raw=raw_words(s);initial=fixture(c);pair=[]
  baseline=retail_words(s);assert baseline==raw
  for words in(baseline,raw):
   m=Oracle(words,initial,c).run();check(m,initial,c);pair.append(m);visits.update(m.visits)
  assert state(pair[0])==state(pair[1]);n+=1;accesses+=pair[0].all_accesses
  if n%512==0:print('guest cases',n,flush=True)
 assert len(visits)==80,len(visits)
 faults=delay=0
 for c in(Case(),Case(remaining=0,mutation=1),Case(flags=8,remaining=0x8000,rate=0x8000),Case(flags=8,alias=1),Case(object=0xFFFFFFC0)):
  initial=fixture(c);raw=raw_words(symbols(c));full=Oracle(raw,initial,c).run()
  for cut in range(full.all_accesses):
   pair=[]
   for words in(retail_words(symbols(c)),raw):
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run();raise AssertionError('Missing fault')
    except AccessBoundary:pass
    pair.append(m)
   assert state(pair[0])==state(pair[1]);faults+=1;delay+=pair[0].delay_of is not None
 report=dict(cases_per_body=n,visited_body_words=80,accesses_per_body=accesses,fault_prefix_pairs=faults,delay_slot_faults=delay,
             all_flags=True,fullword_ticks_and_halfword_wrap=True,guest_only_global_alias_and_wrapped_pointer_cases=True,native_cases=len(list(native_cases())),hardware_FCSR_claim=False)
 (out/'guest-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
