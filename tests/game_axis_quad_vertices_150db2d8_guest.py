"""Ordered finite quad arithmetic, opaque mutations and actual buffer/copy code."""
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
import itertools,json,math,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_interpolated_particle_emitter_150d1204_guest import arithmetic,fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_axis_quad_vertices_150db2d8_match as target_packet
o=target_packet.OUT;r=target_packet.ROOT;ENTRY=0x150DB2D8;ACTOR=0x30000;BUFFER=0x60000;ALT=0x70000;PAGE=0x800BE9C0;BACKEND=0x151D5D60;COPY=0x10022EC0;ALLOC=0x10003C40
bits,floating=fp.bits,fp.floating;u32=lambda v:v&0xFFFFFFFF;half=lambda v:((v&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
 view:int=0
 width:int=bits(1.25)
 height:int=bits(2.5)
 axisX:int=bits(.25)
 axisZ:int=bits(1.)
 fresh:int=1
 success:int=1
 mutation:int=0
 redirect:int=0
 private:int=0
 alias:int=0
 connected:int=0
 page:int=0
 rm:int=0
 phase:int=0
 seed:int=0
def symbols():return dict(func_151D5D60=BACKEND,memcpy=COPY)
def slot(c,view=None):return u32(ACTOR+0x100+4*half(c.view if view is None else view))
def output(c):return ACTOR+0x40 if c.alias==2 else BUFFER+(0 if c.page else 64)
def public(m,c):return{a:v for a,v in m.items()if not STACK+c.phase-2048<=a<STACK+c.phase+512}
def fixture(c):
 m={}
 for p,n in((ACTOR,512),(BUFFER,320),(ALT,320),(STACK+c.phase-2048,2560),(PAGE,1)):
  for i in range(n):assert p+i not in m;m[p+i]=(i*29+c.seed*11+90)&255
 for off,v in((0x2C,c.width),(0x30,c.height),(0x34,bits(10.5)),(0x38,bits(-12.25)),(0x3C,bits(3.75)),(0x40,c.axisX),(0x48,c.axisZ)):put(m,ACTOR+off,v)
 for i in range(4):m.setdefault(slot(c)+i,0)
 pointer=0 if c.connected&4 and(c.fresh or not c.success)else ACTOR+0xC0 if c.alias==1 else BUFFER
 put(m,slot(c),pointer);m[PAGE]=c.page
 if c.private==1:
  for i in range(4):m.setdefault(slot(c,1)+i,0)
  put(m,slot(c,1),ALT)
 return m
def effect(m,c,stage,number,home):
 frame=home-72
 if stage==BACKEND and c.private==1:put(m,home+4,0xABCD0001)
 if stage==COPY and number==1:
  if c.mutation:put(m,slot(c,half(read(m,home+4))),ALT);put(m,ACTOR+0x2C,bits(-4.75))
  if c.redirect:put(m,frame+0x44,ALT+64)
  if c.private==2:put(m,home+4,0xABCD0001)
  if c.private==3:put(m,frame+0x40,ALT+128)
def trunc(a):
 x=floating(a);v=math.trunc(x)if math.isfinite(x)else 0;valid=math.isfinite(x)and -(1<<31)<=v<(1<<31)
 return (v&0xFFFFFFFF if valid else 0x80000000),0x10040 if not valid else 0x1004 if v!=x else 0
def reference(initial,c,home=None,initial_fcsr=None):
 m=dict(initial);home=STACK+c.phase if home is None else home;frame=home-72;cur,first,fresh=frame+0x44,frame+0x40,frame+0x37;csr=c.rm if initial_fcsr is None else initial_fcsr;ops=[];calls=[]
 def calc(a,b,fn):
  nonlocal csr
  ops.append((fn,a,b,csr));v,flags=arithmetic(a,b,fn,csr&3);csr=(csr&~0x3F000)|flags;return v
 def convert(a):
  nonlocal csr
  ops.append((13,a,0,csr));v,flags=trunc(a);csr=(csr&~0x3F000)|flags;return v
 put(m,home+4,u32(c.view));calls.append((BACKEND,(ACTOR+0x100,u32(half(c.view)),64,cur,fresh)))
 if c.connected&4:
  p=read(m,slot(c));m[fresh]=0
  if not p:
   calls.append((ALLOC,(128,1,2,1)));p=BUFFER if c.success else 0;put(m,slot(c),p)
   if p:m[fresh]=1
  answer=u32(p+(0 if c.page else 64))if p else 0
 else:m[fresh]=c.fresh;answer=output(c)if c.success else 0
 put(m,cur,answer);effect(m,c,BACKEND,0,home);put(m,first,read(m,cur))
 if not read(m,cur):return public(m,c),calls,ops,csr,0
 if m[fresh]:
  address=slot(c,half(read(m,home+4)));template=ACTOR+0xC0
  for i in range(2):
   dest=u32(read(m,address)+i*64);calls.append((COPY,(dest,template,64)))
   for j in range(64):m[u32(dest+j)]=m[u32(template+j)]
   effect(m,c,COPY,i+1,home)
 width=read(m,ACTOR+0x2C);horizontal=calc(width,read(m,ACTOR+0x40),2);depth=calc(width^0x80000000,read(m,ACTOR+0x48),2)
 for i,(sx,sy,sz)in enumerate(((1,1,1),(1,-1,1),(-1,-1,-1),(-1,1,-1))):
  for j,(off,delta,sign)in enumerate(((0x34,horizontal,sx),(0x38,None,sy),(0x3C,depth,sz))):
   if delta is None:delta=read(m,ACTOR+0x30)
   value=calc(read(m,ACTOR+off),delta,0 if sign==1 else 1);put(m,read(m,cur)+16*i+2*j,convert(value)&65535,2)
  put(m,read(m,cur)+16*i+6,0,2)
 return public(m,c),calls,ops,csr,read(m,first)
@lru_cache(maxsize=1)
def rom():return(r/'conker/conker.us.bin').read_bytes()
def helpers(c):
 code={}
 for bit,entry,at,n in((1,COPY,0x22EC0,11),(4,BACKEND,0x203210,52)):
  if c.connected&bit:code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom(),at)))
 return code
class Machine(FactoryOracle):
 def __init__(self,words,c,memory=None,entry=None,arguments=None,connected=None):
  self.c=c;self.home=STACK+c.phase;self.copies=0;code=helpers(c);code.update(connected or{});super().__init__(words,fixture(c)if memory is None else memory,c,entry=ENTRY if entry is None else entry,arguments=(ACTOR,u32(c.view))if arguments is None else arguments,s=symbols(),connected=code);self.initial=dict(self.memory);self.fcsr=c.rm;self.before_f=self.f[:];self.fp_operations=[]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
  elif w>>26==17 and w>>21&31==16 and w&63 in(0,1,2,13):
   rt,fs,fd,fn=w>>16&31,w>>11&31,w>>6&31,w&63;a,b=self.f[fs],self.f[rt];self.fp_operations.append((fn,a,b if fn!=13 else 0,self.fcsr));self.f[fd],flags=trunc(a)if fn==13 else arithmetic(a,b,fn,self.fcsr&3);self.fcsr=(self.fcsr&~0x3F000)|flags
  else:super().execute(w)
 def record_call(self,t):
  counts={BACKEND:5,COPY:3,ALLOC:4};assert t in counts,hex(t);args=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,args));self.events.append(('CALL',t,args))
  if t==BACKEND:self.cursor_slot,self.fresh_slot=args[3:]
 def hook(self,t):
  c=self.c;a=self.calls[-1][1];value=0
  if t==BACKEND:self.put(a[3],output(c)if c.success else 0,4);self.put(a[4],c.fresh,1);effect(self.memory,c,t,0,self.home)
  elif t==COPY:
   for i in range(a[2]):self.memory[u32(a[0]+i)]=self.memory[u32(a[1]+i)]
   self.copies+=1;effect(self.memory,c,t,self.copies,self.home);value=a[0]
  else:assert t==ALLOC;value=BUFFER if c.success else 0
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(value)
def observable(m):return public(m.memory,m.c),m.calls,m.fp_operations,m.fcsr,m.r[2]
def state(m):return m.memory,m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.fp_operations,m.trace,m.current_pc,m.delay_of,m.condition
def check(words,c):
 m=Machine(words,c).run();want=reference(m.initial,c);assert observable(m)==want,dict(case=str(c),components=[a==b for a,b in zip(observable(m),want)],actual_calls=m.calls,want_calls=want[1],actual_FP=m.fp_operations,want_FP=want[2]);assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:];return m
def cases():
 rows=[Case(view=v,fresh=f,success=s,width=w,rm=rm,mutation=mutation,redirect=redirect)for v,f,s,w,rm,mutation,redirect in itertools.product((0,3,0xFFFF,0x12340002),(0,1),(0,1),(bits(0.),bits(-2.75),bits(65536.5)),range(4),(0,1),(0,1))]
 rows.extend(Case(view=v,fresh=1,private=p,alias=alias,phase=8,rm=rm)for v,p,alias,rm in itertools.product((0,0x8000,0x7FFF),range(4),range(3),range(4)))
 rows.extend(Case(connected=mode,fresh=f,success=s,page=page,view=3,rm=rm)for mode,f,s,page,rm in itertools.product((1,4,5),(0,1),(0,1),(0,1),range(4)))
 return rows
def main():
 files=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/generic.o','qualified-owner/generated.o'];streams=[bound_blob(*payload(o/f,'func_150DB2D8'),symbols())for f in files];assert all(w==streams[0]for w in streams);seen=set();rows=cases()
 for c in rows:
  models=[check(w,c)for w in streams];assert all(state(m)==state(models[0])for m in models[1:]);seen.update(x for x in models[0].visits if ENTRY<=x<ENTRY+576)
 prefixes=0
 for c in(Case(success=0),Case(),Case(fresh=0),Case(mutation=1,redirect=1),Case(connected=5,fresh=1)):
  full=Machine(streams[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for words in streams:
    m=Machine(words,c);m.cut=cut
    try:m.run();raise AssertionError('missing access fault')
    except AccessBoundary:models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);prefixes+=1
 missing=sorted(set(range(ENTRY,ENTRY+576,4))-seen);q=dict(cases_per_stream=len(rows),streams=5,executed_words=len(seen),unreachable_words=[hex(x)for x in missing],fault_prefix_quintuples=prefixes,all_raw_and_padded_full_private_states_equal=True,independent_reference_public_memory_calls_FP_FCSR_return_equal=True,reference_private_stack_not_claimed=True,all_four_rounding_modes=True,finite_FP_model_not_hardware=True,actual52word_backend_and11word_memcpy_connected=True,allocator_opaque=True,guest_aliases_and_private_home_redirects_not_portable_C=True,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
