"""Effect-slot list cleanup: nested live iterators, signed depth and callback ABI."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-effect-slot-release-150E35DC-match';F='func_150E35DC';ENTRY=0x150E35DC;ROM=0x110A8C
POOL,DEPTH,SAVED,RELEASE=0x800DCE50,0x800DD190,0x800DD198,0x150E3514
NODES=tuple(0x30000+i*0x200 for i in range(8));ARG=0x58000;HOOK=0x15601000
SYMS=dict(D_800DCE50=POOL,D_800DD190=DEPTH,D_800DD198=SAVED,func_150E3514=RELEASE)
u32=lambda n:n&0xFFFFFFFF;s8=lambda n:((n&255)^128)-128
@dataclass(frozen=True)
class Case:
 handle:int=0
 depth:int=-1
 pattern:int=0
 mode:int=0
 empty:int=0
 phase:int=0
def slot(m,s=SYMS):return u32(s['D_800DD198']+4*s8(m[s['D_800DD190']]))
def ids(c):
 return[(0,1,2,127,128,255,1,255)[i]if c.pattern==0 else(0 if c.pattern==1 else 255 if c.pattern==2 else(i*37+c.pattern)&255)for i in range(8)]
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,1024)}
 for i in range(-128,128):put(m,u32(s['D_800DD198']+4*i),0)
 for i in range(0x340):m.setdefault(u32(s['D_800DCE50']+i),0xA5)
 for i,node in enumerate(NODES):
  for j in range(0x100):m[node+j]=(i*31+j*13+7)&255
  put(m,node+8,0 if i in(2,5,7)else NODES[i+1]);m[node+0x48]=ids(c)[i];put(m,node+0x4A,0,2)
 for row in range(2):put(m,s['D_800DCE50']+row*0x1A0+0x98,0);put(m,s['D_800DCE50']+row*0x1A0+0x9C,0 if c.empty&(1<<row)else NODES[row*3])
 m[s['D_800DD190']]=c.depth&255;put(m,ARG,u32(c.handle));return m
def effects(m,c,node,state,s=SYMS):
 if state['fired']:return False
 state['fired']=True;saved=read(m,slot(m,s))
 if c.mode&1:put(m,node+8,NODES[6])
 if c.mode&2 and saved:m[saved+0x48]=(m[saved+0x48]+1)&255
 if c.mode&4:put(m,slot(m,s),read(m,saved+8)if saved else 0)
 if c.mode&8:
  value=read(m,slot(m,s));m[s['D_800DD190']]=(m[s['D_800DD190']]+1)&255;put(m,slot(m,s),value)
 if c.mode&16:
  put(m,s['D_800DCE50']+0x9C,NODES[6]);put(m,s['D_800DCE50']+0x1A0+0x9C,0);return True
 return False
def observation(m,node,s=SYMS):return(node,m[s['D_800DD190']],read(m,slot(m,s)),m[node+0x48])
def reference(initial,c,s=SYMS,entry=ENTRY):
 m=dict(initial);calls=[];obs=[];state=dict(fired=False);wanted=u32(c.handle-1)
 def walk():
  for row in range(2):
   depth=m[s['D_800DD190']];node=read(m,s['D_800DCE50']+row*0x1A0+0x9C);m[s['D_800DD190']]=(depth+1)&255;cursor=slot(m,s);steps=0
   while node:
    steps+=1;assert steps<=24,('unbounded fixture',c)
    put(m,cursor,read(m,node+8))
    if wanted==0xFFFFFFFF or wanted==m[node+0x48]:
     calls.append((s['func_150E3514'],(node,)));obs.append(observation(m,node,s))
     if effects(m,c,node,state,s):calls.append((entry,(u32(c.handle),)));walk()
     cursor=slot(m,s)
    node=read(m,cursor)
   m[s['D_800DD190']]=(m[s['D_800DD190']]-1)&255
 walk();return m,calls,obs
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}
def bridge(entry=ENTRY,helper=RELEASE,hook=HOOK):
 # Only the explicit provider hook is synthetic. Its bridge owns its frame,
 # saves RA, and can re-enter the actual target body with the same handle.
 jal=lambda at:0x0C000000|((at>>2)&0x3FFFFFF)
 return{helper+4*i:w for i,w in enumerate((0x27BDFFE8,0xAFBF0014,jal(hook),0,0x10400005,0,0x3C040006,0x8C848000,jal(entry),0,0x8FBF0014,0x03E00008,0x27BD0018))}
class Oracle(RayOracle):
 def __init__(self,ws,m,c=Case(),entry=ENTRY,s=SYMS,connected=None,arguments=None):
  self.c,self.s,self.target_entry=c,s,entry;self.trace=[];self.observations=[];self.provider_state=dict(fired=False);self.cut=None;self.root_accesses=0;self.target_bytes=len(ws)*4;self.hook_at=entry+0x701A24
  joined=bridge(entry,s['func_150E3514'],self.hook_at);joined.update(connected or{})
  TimingOracle.__init__(self,ws,m,phase=c.phase,entry=entry,arguments=arguments or(u32(c.handle),),connected=joined)
 def access(self):
  if self.own_instruction and self.target_entry<=self.current_pc<self.target_entry+self.target_bytes:
   if self.root_accesses==self.cut:raise faults.AccessBoundary
   self.root_accesses+=1
 def get(self,a,n):
  value=super().get(a,n)
  if self.own_instruction:self.trace.append(('R',a,n,value))
  return value
 def put(self,a,v,n):
  super().put(a,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',a,n,v&((1<<(n*8))-1)))
 def record_call(self,target):
  if target==self.hook_at:return
  assert target in(self.s['func_150E3514'],self.target_entry),hex(target);args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))
  if target==self.s['func_150E3514']:self.observations.append(observation(self.memory,args[0],self.s))
 def hook(self,target):
  assert target==self.hook_at,hex(target);node=self.calls[-1][1][0];recurse=effects(self.memory,self.c,node,self.provider_state,self.s)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678;self.r[2]=int(recurse)
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def images(label='guest',entry=ENTRY,s=SYMS):return[linked(o/n,label+'-'+str(i),entry,s)for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))]
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.observations,m.hi,m.lo,m.condition)
def compare(c,ims,entry=ENTRY,s=SYMS):
 initial=fixture(c,s);want,calls,obs=reference(initial,c,s,entry);ms=[]
 for ws in ims:
  m=Oracle(ws,initial,c,entry,s).run();assert(public(m.memory),m.calls,m.observations)==(public(want),calls,obs),(c,m.calls,calls,m.observations,obs);ms.append(m)
 assert state(ms[0])==state(ms[2])and state(ms[0])==state(ms[1]),c;return ms[0]
def guest_suite():
 ims=images();assert ims[0]==ims[2]and len(ims[1])==55;count=0;visits=set()
 for handle,depth,pattern,mode,empty,phase in itertools.product((0,1,2,129,256,257,0x80000000,0xFFFFFFFF),(-1,0,2),range(4),range(32),range(4),(0,8)):
  c=Case(handle,depth,pattern,mode,empty,phase);visits.update(compare(c,ims).visits);count+=1
  if count%4096==0:print('GUEST_CASES',count,flush=True)
 assert set(range(ENTRY,ENTRY+224,4))<=visits
 extras=0
 for depth,handle,mode in itertools.product((-128,-68,-3,-2,126,127,128,255),(0,1,256),(0,7,15,31)):
  compare(Case(handle,depth,0,mode),ims);extras+=1
 cuts=delays=0
 for c in(Case(),Case(2,0,0,15),Case(0,2,0,31),Case(257,-1,2,0,3)):
  full=compare(c,ims)
  for cut in range(full.root_accesses):
   ms=[]
   for ws in(ims[0],ims[2]):
    m=Oracle(ws,fixture(c),c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('access cut absent')
    ms.append(m)
   assert state(ms[0])==state(ms[1])and(ms[0].current_pc,ms[0].delay_of)==(ms[1].current_pc,ms[1].delay_of);cuts+=1;delays+=ms[0].delay_of is not None
 rebases=0
 for j,(entry,pool,saved)in enumerate(((0x17007FFC,0x90007FFC,0x90108000),(0x2500FFFC,0x90008000,0x9010FFFC),(0x15008000,0x9020FFFC,0x90218000))):
  s=dict(D_800DCE50=pool,D_800DD190=pool+0x340,D_800DD198=saved,func_150E3514=entry+0x20000);ims2=images('rebase-'+str(j),entry,s)
  for handle,depth,mode,empty in itertools.product((0,2,256),(-1,2),(0,15,31),(0,3)):compare(Case(handle,depth,0,mode,empty),ims2,entry,s);rebases+=1
 return dict(cases=count,executions=count*3,covered_words=56,raw_words=55,guest_only_invalid_depth_cases=extras,access_prefix_cases=cuts,delay_slot_cuts=delays,rebased_cases=rebases,GNU_layouts=3,raw_final_full_state_and_trace_equal=True,normalized_full_prefix_equal=True,actual_target_reentry=True,two_row_end_alias_preserved_in_rebases=True,invalid_indices_not_claimed_as_portable_C=True)

def controls(body):
 changes={
 'no_decrement':('(u32)handle - 1u','(u32)handle'),
 'wrong_decrement':('(u32)handle - 1u','(u32)handle + 1u'),
 'signed_slot':('handle == node[0x48]','handle == (s8)node[0x48]'),
 'wrong_slot':('handle == node[0x48]','handle == node[0x49]'),
 'always_release':('handle == -1 || handle == node[0x48]','1'),
 'missing_all':('handle == -1 || handle == node[0x48]','handle == node[0x48]'),
 'late_next':('node = D_800DD198[D_800DD190];','node = *(u8 **)(node + 8);'),
 'one_row':('row += 0x1A0;','row += 0x340;'),
 'wrong_head':('row + 0x9C','row + 0x98'),
 'missing_unwind':('        D_800DD190--;',''),
 }
 out={}
 for name,(a,b) in changes.items():
  assert a in body,(name,a);out[name]=body.replace(a,b)
 out['cached_next']=body.replace('    u8 *node;','    u8 *node;\n    u8 *savedNext;').replace('D_800DD198[D_800DD190] = *(void **)(node + 8);','savedNext = *(u8 **)(node + 8);\n            D_800DD198[D_800DD190] = savedNext;').replace('node = D_800DD198[D_800DD190];','node = savedNext;')
 out['cached_depth']=body.replace('    u8 *node;','    u8 *node;\n    s32 index;').replace('        D_800DD190++;','        D_800DD190++;\n        index = D_800DD190;').replace('D_800DD198[D_800DD190]','D_800DD198[index]')
 assert len(set(out.values()))==len(out)and body not in out.values()
 return out

def _native_suite(m):
 o=m.o;body=(o/'selected-semantic-input.c').read_text();cases=[m.Case(h,d,p,mode,e)for h,d,p,mode,e in itertools.product((0,1,2,129,256,257),(-1,0,2),range(4),range(32),range(4))]
 nid=lambda x:-1 if not x else m.NODES.index(x)
 rows=[]
 for c in cases:
  want,calls,obs=m.reference(m.fixture(c),c)
  heads=[nid(m.read(want,m.POOL+row*0x1A0+0x9C))for row in range(2)]
  nexts=[nid(m.read(want,n+8))for n in m.NODES];saved=[nid(m.read(want,m.SAVED+4*i))for i in range(6)]
  slots=[want[n+0x48]for n in m.NODES];trace=[(nid(n),d,nid(s),v)for n,d,s,v in obs];assert len(trace)<=16
  trace +=[(0,0,0,0)]*(16-len(trace))
  array=lambda xs:'{'+','.join(map(str,xs))+'}'
  rows.append('{'+','.join([str(m.u32(c.handle))+'u',str(c.depth),str(c.pattern),str(c.mode),str(c.empty),str(len(obs)),str(want[m.DEPTH]),array(heads),array(nexts),array(saved),array(slots),'{'+','.join(array(x)for x in trace)+'}'])+'}')
 variants={'selected':body,**controls(body)};parts=[];names=[]
 for name,text in variants.items():
  n='candidate_'+name;names.append(n);parts.append(text.replace(m.F,n))
 t='\n'.join(parts)+r'''
u8 iteratorStorage[896] __attribute__((aligned(4)));
__asm__(".globl D_800DCE50\n.set D_800DCE50, iteratorStorage+16\n.globl D_800DD190\n.set D_800DD190, iteratorStorage+848\n.globl D_800DD198\n.set D_800DD198, iteratorStorage+856\n");
typedef union {u32 align;u8 b[256];} Node;
static struct{u32 left[4];Node nodes[8];u32 right[4];} storage;
struct Trace{s32 node;u32 depth;s32 saved;u32 slot;};
struct Case{s32 handle,depth;u32 pattern,mode,empty,count,finalDepth;s32 heads[2],next[8],saved[6];u8 slots[8];struct Trace trace[16];};
static const struct Case cases[]={ROWS};
typedef void(*Fn)(s32);static Fn active;static const struct Case *c;static u32 calls,error,fired;
typedef char ABI[(sizeof(void*)==4&&sizeof(Node)==256)?1:-1];
static u8*node(s32 id){return id<0?(u8*)0:storage.nodes[id].b;}
static s32 id(void*p){u32 i;if(!p)return -1;for(i=0;i<8;i++)if(p==node((s32)i))return (s32)i;return -99;}
static void*next(u8*p){return *(void**)(p+8);}
__attribute__((noinline,noclone)) void func_150E3514(u8*p){
 u32 level=(u8)D_800DD190;void*saved;const struct Trace *e;
 if(level>=6){error=1;return;}saved=D_800DD198[level];
 if(calls>=c->count)error=1;else{e=&c->trace[calls];if(id(p)!=e->node||level!=e->depth||id(saved)!=e->saved||p[0x48]!=e->slot)error=1;}calls++;
 if(fired)return;fired=1;
 if(c->mode&1)*(void**)(p+8)=node(6);
 if((c->mode&2)&&saved)((u8*)saved)[0x48]++;
 if(c->mode&4)D_800DD198[level]=saved?next(saved):(void*)0;
 if(c->mode&8){D_800DD190++;D_800DD198[(u8)D_800DD190]=D_800DD198[level];}
 if(c->mode&16){*(void**)(D_800DCE50+0x9C)=node(6);*(void**)(D_800DCE50+0x1A0+0x9C)=0;active(c->handle);}
}
static u8 initial_slot(u32 i){static const u8 v[]={0,1,2,127,128,255,1,255};if(!c->pattern)return v[i];if(c->pattern==1)return 0;if(c->pattern==2)return 255;return (u8)(i*37+c->pattern);}
static int one(Fn fn,const struct Case*input){
 u32 i,j;u8*p;active=fn;c=input;calls=error=fired=0;
 for(i=0;i<896;i++)iteratorStorage[i]=0xA5;
 for(i=0;i<4;i++)storage.left[i]=storage.right[i]=0xA5A5A5A5u;
 for(i=0;i<8;i++){p=node((s32)i);for(j=0;j<256;j++)p[j]=(u8)(i*31+j*13+7);*(void**)(p+8)=node(i==2||i==5||i==7?-1:(s32)i+1);p[0x48]=initial_slot(i);*(u16*)(p+0x4A)=0;}
 for(i=0;i<6;i++)D_800DD198[i]=0;
 for(i=0;i<2;i++){*(void**)(D_800DCE50+i*0x1A0+0x98)=0;*(void**)(D_800DCE50+i*0x1A0+0x9C)=node(c->empty&(1u<<i)?-1:(s32)i*3);}
 D_800DD190=(s8)c->depth;fn(c->handle);
 if(error||calls!=c->count||(u8)D_800DD190!=c->finalDepth)return 1;
 for(i=0;i<2;i++)if(id(*(void**)(D_800DCE50+i*0x1A0+0x9C))!=c->heads[i])return 2;
 for(i=0;i<6;i++)if(id(D_800DD198[i])!=c->saved[i])return 3;
 for(i=0;i<8;i++){p=node((s32)i);if(id(next(p))!=c->next[i]||p[0x48]!=c->slots[i])return 4;for(j=0;j<256;j++)if(!(j>=8&&j<12)&&j!=0x48&&j!=0x4A&&j!=0x4B&&p[j]!=(u8)(i*31+j*13+7))return 5;}
 for(i=0;i<4;i++)if(storage.left[i]!=0xA5A5A5A5u||storage.right[i]!=0xA5A5A5A5u)return 6;
 for(i=0;i<896;i++)if(!(i>=16+0x98&&i<16+0xA0)&&!(i>=16+0x1A0+0x98&&i<16+0x1A0+0xA0)&&i!=848&&!(i>=856&&i<880)&&iteratorStorage[i]!=0xA5)return 7;
 return 0;
}
static int run(void){Fn fns[]={FUNCTIONS};u32 n,i;int failed;
 if((u32)&D_800DD190!=(u32)D_800DCE50+832||(u32)D_800DD198!=(u32)D_800DCE50+840)return 99;
 for(n=0;n<sizeof(fns)/sizeof(fns[0]);n++){failed=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
 /* Defective unwind/row controls are tested with no recursive callback to keep every fixture defined. */
 if(n&&((cases[i].mode&16)||cases[i].depth<0))continue;
 {int e=one(fns[n],&cases[i]);if(!n&&e)return e;if(e){failed=1;break;}}}
 if(n&&!failed)return 50+n;}return 0;}
'''
 t=t.replace('ROWS',',\n'.join(rows)).replace('FUNCTIONS',','.join(names))+m.START
 path=o/'native-slot-release.c';path.write_text(t);profiles={}
 for opt in('-O0','-O2','-O3'):
  binary=o/('native-slot-release'+opt);q=subprocess.run(m.native_command(opt)+['-mstackrealign',str(path),'-o',str(binary)],capture_output=True,text=True);binary.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stderr,(opt,q.stdout,q.stderr)
  q=subprocess.run([str(binary)],capture_output=True,timeout=60);assert q.returncode==0,(opt,q.returncode);profiles[opt]=dict(exit=0,UBSan=True)
 return dict(cases_per_profile=len(cases),profiles=profiles,compiled_controls=len(names)-1,effective_controls=True,physical_row_end_depth_alias=True,real_saved_pointer_slots=6,native_invalid_indices_not_claimed=True,whole_nodes_and_canaries=True,actual_C_target_reentry=True)

def _caller_suite(m):
 rom=(m.r/'conker/conker.us.bin').read_bytes();entry,end=0x1509D844,0x1509D84C
 pointer=struct.pack('>I',m.ENTRY);jal=struct.pack('>I',0x0C000000|((m.ENTRY>>2)&0x3FFFFFF))
 assert[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal]==[0xCACF4]
 assert not[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==pointer]
 ws=list(struct.unpack_from('>2I',rom,0xCACF4));assert ws[1]==0x00062183
 class Boundary(Exception):pass
 class Window(m.faults.TrackedCode):
  def __contains__(self,pc):return pc==end or super().__contains__(pc)
  def __getitem__(self,pc):
   if pc==end:raise Boundary
   return super().__getitem__(pc)
 ims=m.images('caller');count=0
 class Caller(m.Oracle):
  def __init__(self,body,initial,c):
   super().__init__(ws,initial,c,entry,connected={m.ENTRY+4*i:w for i,w in enumerate(body)})
   self.target_entry=m.ENTRY;self.code=Window(dict(self.code),self)
  def record_call(self,target):
   if target==m.ENTRY:
    args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))
   else:super().record_call(target)
 for encoded,depth,mode,empty,phase in itertools.product((0,64,128,129*64,255*64,256*64,0x7FFFFFFF,0x80000000,0xFFFFFFFF),(-1,2),(0,15),(0,3),(0,8)):
  handle=m.u32((encoded if encoded<0x80000000 else encoded-0x100000000)>>6);c=m.Case(handle,depth,0,mode,empty,phase);initial=m.fixture(c);want,calls,obs=m.reference(initial,c);ms=[]
  for body in ims:
   q=Caller(body,initial,c);q.r[6]=encoded;q.before=q.r[:]
   try:q.run()
   except Boundary:pass
   else:raise AssertionError('caller window not exited')
   assert(m.public(q.memory),q.calls,q.observations)==(m.public(want),[(m.ENTRY,(handle,)),*calls],obs),(c,q.calls,calls)
   ms.append(q)
  assert m.state(ms[0])==m.state(ms[1])==m.state(ms[2]);count+=1
 return dict(cases=count,parent='func_1509D780',original_window_words=2,call=hex(entry),delay_slot='sra a0,a2,6',return_ignored=True,complete_parent_execution_claimed=False)

def _compiled_controls(m,n):
 result={};body=(m.o/'selected-semantic-input.c').read_text()
 for name,text in n.controls(body).items():
  obj,diag=m.compile_owner(m.r,m.o,text,'negative-'+name);assert not diag;ws=m.linked(obj,'negative-linked-'+name);witness=None
  for handle,pattern,mode in itertools.product((0,1,2,129,256,257),range(4),(0,7,15)):
   c=m.Case(handle,0,pattern,mode);initial=m.fixture(c);want,calls,obs=m.reference(initial,c);q=m.Oracle(ws,initial,c).run()
   if(m.public(q.memory),q.calls,q.observations)!=(m.public(want),calls,obs):witness=[handle,pattern,mode];break
  assert witness is not None,('ineffective semantic control',name);result[name]=witness
 return dict(count=len(result),effective_IDO_controls=result,compile_or_oracle_errors_not_accepted=True)

def _provider_suite(m):
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 TABLE,FINAL,UNLINK,FALLBACK,DESTRUCTORS,OTHER=0x800D99D0,0x1516972C,0x151696DC,0x15169804,0x8008B4D0,0x48000
 rom=(m.r/'conker/conker.us.bin').read_bytes();elf=(m.o/'before-conker_build_conker.us.elf').read_bytes();code={};identities={}
 for at,offset,count in((m.RELEASE,0x1109C4,50),(FINAL,0x196BDC,28)):
  raw=rom[offset:offset+count*4];pos=elf_slot_offset(elf,at,count*4);assert raw==elf[pos:pos+count*4]
  code.update({at+4*i:w for i,w in enumerate(struct.unpack('>%dI'%count,raw))});identities[hex(at)]=dict(words=count,current_byte_exact=True)
 class Provider(m.Oracle):
  def record_call(self,target):
   assert target in(m.RELEASE,FINAL,UNLINK,FALLBACK);args=self.arguments(1);self.calls.append((target,args));self.events.append(('CALL',target,args))
   if target==m.RELEASE:self.observations.append(m.observation(self.memory,args[0]))
  def hook(self,target):
   assert target in(UNLINK,FALLBACK)
   if target==UNLINK:m.effects(self.memory,self.c,self.calls[-1][1][0],self.provider_state)
   for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
   self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678;self.r[2]=0xA5000002
 def reference(initial,c):
  memory=dict(initial);calls=[];obs=[];state=dict(fired=False);wanted=m.u32(c.handle-1)
  for row in range(2):
   depth=memory[m.DEPTH];node=m.read(memory,m.POOL+row*0x1A0+0x9C);memory[m.DEPTH]=(depth+1)&255;cursor=m.slot(memory)
   while node:
    m.put(memory,cursor,m.read(memory,node+8))
    if wanted==0xFFFFFFFF or wanted==memory[node+0x48]:
     calls.append((m.RELEASE,(node,)));obs.append(m.observation(memory,node));p=TABLE+memory[node+0x48]*4
     if m.read(memory,p)==node:m.put(memory,p,0)
     calls.extend(((FINAL,(node,)),(UNLINK,(node,))));assert not m.effects(memory,c,node,state)
     if memory[node]>=2:calls.append((FALLBACK,(node,)))
     cursor=m.slot(memory)
    node=m.read(memory,cursor)
   memory[m.DEPTH]=(memory[m.DEPTH]-1)&255
  return memory,calls,obs
 ims=m.images('original-providers');count=0;visits=set()
 for handle,depth,kind,matching,mode,empty,phase in itertools.product((0,1,2,8,9),(-1,2),(0,1,2),(False,True),(0,7,15),(0,3),(0,8)):
  c=m.Case(handle,depth,0,mode,empty,phase);initial=m.fixture(c)
  for i,node in enumerate(m.NODES):initial[node+0x48]=i;initial[node]=kind;m.put(initial,TABLE+4*i,node if matching else OTHER)
  m.put(initial,DESTRUCTORS+kind*52,0);want,calls,obs=reference(initial,c);ms=[]
  for body in ims:
   q=Provider(body,initial,c,connected=code).run();assert(m.public(q.memory),q.calls,q.observations)==(m.public(want),calls,obs),(c,kind,q.calls,calls);ms.append(q);visits.update(q.visits)
  assert m.state(ms[0])==m.state(ms[1])==m.state(ms[2]);count+=1
 seen=set(code)&visits;assert m.RELEASE in seen and FINAL in seen
 return dict(cases=count,provider_identities=identities,loaded_original_helper_words=len(code),visited_original_helper_words=len(seen),sound_handle_zero=True,unlink_and_fallback_are_bounded_hooks=True,full_release_chain_or_hardware_claimed=False)

def native_suite():
 import sys
 return _native_suite(sys.modules[__name__])
def caller_suite():
 import sys
 return _caller_suite(sys.modules[__name__])
def compiled_controls():
 import sys
 return _compiled_controls(sys.modules[__name__],sys.modules[__name__])
def provider_suite():
 import sys
 return _provider_suite(sys.modules[__name__])
