"""Ordered resource-matrix contract; bounded IEEE model, not N64 hardware."""
import itertools,json,math,struct,sys
from dataclasses import dataclass,replace
from pathlib import Path
from tools.experiments.game_resource_matrix_15157dec_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
from tools.tests.test_game_record_matrix_update_match import rotation
ENTRY,ROTATE,OBJECT,INPUT,PAGE=0x15157DEC,0x150A8050,0x30000,0x60000,0x800BE9C0
COS,SIN,FACTOR=0x150AD780,0x150AD78C,0x8009F6C0
SYMS=dict(D_800BE9C0=PAGE,func_150A8050=ROTATE)
u32=lambda v:v&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 page:int=0
 pattern:int=0
 mutation:int=0
 parameters:int=INPUT
 phase:int=0
 object:int=OBJECT
 alias:int=0
 scaleX:int=0x40000000
 scaleY:int=0xBF000000

def symbols(c,s=None):
 s=dict(SYMS if s is None else s)
 if c.alias:s['D_800BE9C0']=u32(c.object+0xAC)
 return s
def seed(c):return tuple(bits(((i*3+c.pattern*5)%13-6)*.125)if i!=15 else bits(1.)for i in range(16))
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+2048}
def fixture(c,s=None):
 s=symbols(c,s);m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,2048)}
 for base,n in((c.object,0x1D8),(c.parameters,20)):
  m.update({u32(base+i):(i*29+0x5A)&255 for i in range(n)})
 for page in(range(256)if c.alias else {0,1,c.page}):
  base=u32(c.object+0x7C+page*64)
  for i,w in enumerate(seed(c)):put(m,u32(base+i*4),w)
 for j,v in enumerate((1.5,-2.75,3.125)):put(m,u32(c.object+0x54+4*j),bits(v))
 for j,w in enumerate((bits(10.+c.pattern),bits(-20.+c.pattern),bits(30.-c.pattern),c.scaleX,c.scaleY)):put(m,u32(c.parameters+4*j),w)
 m[s['D_800BE9C0']]=c.page;put(m,FACTOR,0x3C8EFA35)
 return m
def effect(m,c,s):
 if c.mutation&1:m[s['D_800BE9C0']]^=1
 if c.mutation&2:
  for i,v in enumerate((-4.25,5.5,-6.75)):put(m,u32(c.object+0x54+4*i),bits(v))
 if c.mutation&4:
  put(m,u32(c.parameters+12),bits(-.75));put(m,u32(c.parameters+16),bits(1.25))
 if c.mutation&8:
  for i,w in enumerate(reversed(seed(c))):put(m,u32(c.object+0x7C+(m[s['D_800BE9C0']]^1)*64+i*4),w)
 if c.mutation&16:
  for j in range(3):put(m,u32(c.parameters+4*j),bits(-11.-j))
def snapshot(m,c,s,args):return(args,m[s['D_800BE9C0']],data(m,c.object,0x1D8),data(m,c.parameters,20))
def reference(initial,c,s=None,connected=False):
 s=symbols(c,s);m=dict(initial);p=c.object
 args=(u32(p+0x7C+m[s['D_800BE9C0']]*64),*(read(m,u32(c.parameters+j*4))for j in range(3)))
 calls=[(s['func_150A8050'],args)];snaps=[snapshot(m,c,s,args)]
 if connected:
  factor=read(m,FACTOR)
  for angle in args[1:]:
   radians=fp(angle,factor,'mul');calls.extend(((COS,(radians,)),(SIN,(radians,))))
  values=rotation(args[1:],factor)
 else:values=seed(c)
 for i,w in enumerate(values):put(m,u32(args[0]+i*4),w)
 if not connected:effect(m,c,s)
 for offset,source in((0xAC,0x54),(0xB0,0x58),(0xB4,0x5C)):
  dest=u32(p+offset+m[s['D_800BE9C0']]*64);put(m,dest,read(m,u32(p+source)))
 for offset,scale in((0x7C,12),(0x80,12),(0x84,12),(0x8C,16),(0x90,16),(0x94,16),(0x9C,12),(0xA0,12),(0xA4,12)):
  dest=u32(p+offset+m[s['D_800BE9C0']]*64);v=read(m,u32(c.parameters+scale));put(m,dest,fp(read(m,dest),v,'mul'))
 return m,calls,snaps
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None,arguments=None):
  self.snapshots=[]
  super().__init__(words,memory,c,entry=entry,s=symbols(c,s),connected=connected,arguments=(u32(c.object),u32(c.parameters))if arguments is None else arguments)
  self.saved_f=self.f[20:].copy()
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==7:
   self.dispatched_word=w;self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
  else:super().execute(w)
 def record_call(self,t):
  if t in(SIN,COS):args=(self.f[12],)
  else:
   assert t==self.syms['func_150A8050'],hex(t);args=tuple(self.arguments(4));self.snapshots.append(snapshot(self.memory,self.case,self.syms,args))
  self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  if t in(SIN,COS):answer=bits((math.sin if t==SIN else math.cos)(floating(self.f[12])))
  else:
   args=self.calls[-1][1]
   for i,w in enumerate(seed(self.case)):put(self.memory,u32(args[0]+i*4),w)
   effect(self.memory,self.case,self.syms);answer=0xDEADBEEF
  # The actual leaf trig routes do not write their caller's argument homes.
  # The outer matrix provider may use its full outgoing argument area.
  if t not in(SIN,COS):
   for i in range(4):self.put(u32(self.r[29]+i*4),0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=answer;self.hi,self.lo=0xA5000010,0xA5000011
def cases():
 for page in range(256):yield Case(page=page,pattern=page%3,phase=(page&1)*8)
 for page,pattern,mutation,param,phase in itertools.product((0,1),range(3),range(32),(INPUT,OBJECT+0x120,OBJECT+0x70),(0,8)):
  yield Case(page=page,pattern=pattern,mutation=mutation,parameters=param,phase=phase)
 for scaleX,scaleY in itertools.product((0,0x80000000,bits(.125),bits(-2.),bits(1e20)),(0,bits(-.5),bits(1.25))):yield Case(scaleX=scaleX,scaleY=scaleY)
 for page,mutation in itertools.product((0,1),range(4)):yield Case(page=page,alias=1,mutation=mutation)
 for obj in(0,0xFFFFFE00):yield Case(object=obj)
def native_cases():
 seen=set()
 for c in cases():
  if c.page>1 or c.object!=OBJECT or c.alias:continue
  c=replace(c,phase=0)
  if c not in seen:seen.add(c);yield c
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,m.snapshots,m.trace,m.current_pc,m.delay_of,m.dispatched_word)
def check(m,initial,c,s=None,connected=False):
 expected,calls,snaps=reference(initial,c,s,connected)
 assert(public(m.memory),m.calls,m.snapshots)==(public(expected),calls,snaps),c
 assert m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[31]==m.before[31]and m.f[20:]==m.saved_f,c
def raw_words(s=SYMS):
 t,fs,rs=parse_object(out/'qualified-owner.o');f=fs['func_15157DEC'];refs={a-f['value']:v for a,v in rs.items()if f['value']<=a<f['value']+f['size']}
 return bound_blob(t[f['value']:f['value']+f['size']],refs,s)
def retail_words(s=SYMS):
 words=list(struct.unpack('>101I',(out/'retail-slot.bin').read_bytes()))
 for i,j in((3,4),(16,17)):
  v=s['D_800BE9C0'];assert words[i]&65535==0x800C and words[j]&65535==0xE9C0
  words[i]=(words[i]&0xFFFF0000)|(((v+32768)>>16)&65535);words[j]=(words[j]&0xFFFF0000)|(v&65535)
 assert words[14]>>26==3;words[14]=(words[14]&0xFC000000)|((s['func_150A8050']>>2)&0x3FFFFFF)
 return words
def main():
 n=accesses=0;visits=set();bodies={}
 for c in cases():
  s=symbols(c);initial=fixture(c);key=tuple(sorted(s.items()))
  if key not in bodies:bodies[key]=(raw_words(s),retail_words(s))
  raw,truth=bodies[key];assert raw==truth;pair=[]
  for words in(truth,raw):
   m=Oracle(words,initial,c).run();check(m,initial,c);pair.append(m);visits.update(m.visits)
  assert state(pair[0])==state(pair[1]);n+=1;accesses+=pair[0].all_accesses
  if n%512==0:print('guest cases',n,flush=True)
 assert len(visits)==101,len(visits)
 faults=delay=0
 for c in(Case(),Case(page=1,mutation=31,parameters=OBJECT+0x70),Case(alias=1),Case(object=0xFFFFFE00)):
  initial=fixture(c);raw=raw_words(symbols(c));full=Oracle(raw,initial,c).run()
  for cut in range(full.all_accesses):
   pair=[]
   for words in(retail_words(symbols(c)),raw):
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run();raise AssertionError('Missing fault')
    except AccessBoundary:pass
    pair.append(m)
   assert state(pair[0])==state(pair[1]);faults+=1;delay+=pair[0].delay_of is not None
 report=dict(cases_per_body=n,visited_body_words=101,accesses_per_body=accesses,fault_prefix_pairs=faults,delay_slot_faults=delay,native_cases=len(list(native_cases())),all_page_bytes_guest=True,guest_alias_and_wrapped_pointer_cases_separate=True,hardware_FCSR_claim=False)
 (out/'guest-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
