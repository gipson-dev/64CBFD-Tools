"""Bounded view state, original spatial walkers and caller-loop qualification."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.experiments import game_view_leaf_category_match as source
from tools.tests import game_actor_phase_motion_oracle as phase
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
r=Path.cwd();o=r/source.BUILD
STACK=phase.STACK
VIEWS,NODES,LEAF=0x220000,0x260000,0x270000
LOOKUP,CATEGORY,NOTIFY,REFRESH=0x1510FD20,0x1510FE30,0x150A6760,0x150F33F8
SYMS={n:int(n[2:],16) for n in ('D_800DBFF0','D_800DBDC0','D_800DBDC4','D_800DBDC8','D_800DBDCC','D_800DBDD0','D_800DBE30','D_800BE9F0','D_800DBE48','D_80082FA0')}
SYMS.update(func_1510FD20=LOOKUP,func_1510FE30=CATEGORY,func_150A6760=NOTIFY,func_150F33F8=REFRESH)
@dataclass(frozen=True)
class Case:
 view:int=0
 x:float=12.75
 z:float=-17.5
 category:int=1
 previous:int=0
 flag:int=60
 mode:int=0
 phase:int=0
 tree:int=0

def half(v):return ((v&65535)^32768)-32768
def fixture(c=Case(),s=SYMS,connected=False):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,128)}
 m.update({VIEWS+i:(i*13+0x59)&255 for i in range(-16,4*0x9A0+32)})
 m.update({NODES+i:0 for i in range(-16,112)})
 for n in ('D_800DBFF0','D_800DBDC0','D_800DBDC4','D_800DBDC8','D_800DBDCC','D_800DBDD0','D_800DBE30','D_800BE9F0','D_800DBE48','D_80082FA0'):
  for i in range(-8,24):m.setdefault(s[n]+i,0xA5)
 for i in range(4):
  put(m,VIEWS+i*0x9A0+0x2F8,bits(c.x));put(m,VIEWS+i*0x9A0+0x300,bits(c.z));put(m,s['D_800DBE30']+i*2,c.previous&65535,2)
 put(m,s['D_800DBFF0'],VIEWS);put(m,s['D_800BE9F0'],c.flag);put(m,s['D_80082FA0'],3)
 if connected:
  if c.tree==0:root=0
  elif c.tree==1:
   root=NODES;put(m,root+6,8,2)
  elif c.tree==2:
   root=NODES
   for at,x,z,rad,child,sibling in ((0,0,0,8,16,48),(16,-4,-4,3,0,16),(32,4,4,3,0,16),(48,20,20,8,0,0)):
    for off,value in ((4,sibling),(6,rad),(8,x),(10,z),(12,child)):put(m,NODES+at+off,value&65535,2)
  else:
   root=NODES+48
   for at,x,z,rad,child,sibling in ((48,0,0,8,-32,-16),(16,-4,-4,3,0,16),(32,20,20,8,0,0)):
    for off,value in ((4,sibling),(6,rad),(8,x),(10,z),(12,child)):put(m,NODES+at+off,value&65535,2)
  put(m,s['D_800DBE48'],root)
 return m

def lookup(m,x,z,s=SYMS):
 p=read(m,s['D_800DBE48'])
 for _ in range(32):
  if not p:return 0
  inside=abs(signed((x-half(read(m,p+8,2)))&0xFFFFFFFF))<=read(m,p+6,2) and abs(signed((z-half(read(m,p+10,2)))&0xFFFFFFFF))<=read(m,p+6,2)
  child=half(read(m,p+12,2));sibling=half(read(m,p+4,2))
  if inside and not child:return p
  delta=child if inside else sibling
  p=(p+delta)&0xFFFFFFFF if delta else 0
 raise AssertionError('Unbounded reference tree')
def category(m,target,s=SYMS):
 p=read(m,s['D_800DBE48']);result=0
 for _ in range(32):
  if not p:return 0
  if p==target:return result
  delta=half(read(m,p+12,2))
  if not delta:
   delta=half(read(m,p+4,2))
   if not delta:return 0
   result+=1
  p=(p+delta)&0xFFFFFFFF
 raise AssertionError('Unbounded reference category chain')

def effect(m,c,s,target):
 if target==LOOKUP:
  if c.mode&1:put(m,s['D_800DBFF0'],VIEWS+0x9A0)
  if c.mode&2:put(m,s['D_800DBDC0'],0xDEADBEEF)
  if c.mode&4:put(m,s['D_800DBDCC'],0x7FC12345)
 elif target==CATEGORY:
  if c.mode&8:put(m,s['D_800DBE30']+2*c.view,c.category&65535,2)
  if c.mode&16:put(m,s['D_800BE9F0'],60)
 elif target==NOTIFY:
  if c.mode&32:put(m,s['D_800BE9F0'],59)
  if c.mode&64:put(m,s['D_800DBDC4'],0x80000000)
 elif target==REFRESH:
  if c.mode&128:put(m,s['D_800DBDC8'],0x89ABCDEF)

def reference(initial,c,s=SYMS,connected=False,view=None):
 m=dict(initial);calls=[];v=c.view if view is None else view
 # The emitted routine captures the base before publishing the view index.
 base=read(m,s['D_800DBFF0']);put(m,s['D_800DBDC0'],v)
 p=base+v*0x9A0
 x=math.trunc(floating(read(m,p+0x2F8)));z=math.trunc(floating(read(m,p+0x300)))
 put(m,s['D_800DBDCC'],bits(float(x)));put(m,s['D_800DBDD0'],bits(float(z)))
 calls.append((s['func_1510FD20'],(x&0xFFFFFFFF,z&0xFFFFFFFF)))
 leaf=lookup(m,x,z,s)if connected else LEAF
 if not connected:effect(m,c,s,LOOKUP)
 put(m,s['D_800DBDC8'],leaf)
 calls.append((s['func_1510FE30'],(leaf,)))
 value=category(m,leaf,s)if connected else c.category&0xFFFFFFFF
 if not connected:effect(m,c,s,CATEGORY)
 put(m,s['D_800DBDC4'],value)
 address=s['D_800DBE30']+2*v
 if signed(value)!=half(read(m,address,2)):
  put(m,address,value&65535,2);calls.append((s['func_150A6760'],(v,)));effect(m,c,s,NOTIFY)
 if read(m,s['D_800BE9F0'])==60:
  calls.append((s['func_150F33F8'],(v,)));effect(m,c,s,REFRESH)
 return m,calls

class Oracle(phase.Oracle):
 def __init__(self,w,m,c=Case(),entry=source.ENTRY,s=SYMS,connected=None,fault=None):
  super().__init__(w,m,c,entry,s,connected,fault)
  self.r[4]=c.view
 def record_call(self,t):
  signatures={self.s['func_1510FD20']:2,self.s['func_1510FE30']:1,self.s['func_150A6760']:1,self.s['func_150F33F8']:1,source.ENTRY:1}
  assert t in signatures,hex(t)
  args=self.arguments(signatures[t]);self.calls.append((t,args))
  self.observations.append((t,tuple(read(self.memory,self.s[n])for n in ('D_800DBDC0','D_800DBDC4','D_800DBDC8','D_800DBDCC','D_800DBDD0','D_800BE9F0')),read(self.memory,self.s['D_800DBE30']+2*self.c.view,2)))
 def hook(self,t):
  actual=next(k for k,n in ((LOOKUP,'func_1510FD20'),(CATEGORY,'func_1510FE30'),(NOTIFY,'func_150A6760'),(REFRESH,'func_150F33F8'))if self.s[n]==t)
  value=LEAF if actual==LOOKUP else self.c.category&0xFFFFFFFF if actual==CATEGORY else 0xA55A1234
  effect(self.memory,self.c,self.s,actual)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)]
  self.r[2]=value;self.hi,self.lo=0xA5000010,0xA5000011

def public(m):return {a:v for a,v in m.items()if not STACK-512<=a<STACK+128}
def linked(obj,label,entry=source.ENTRY,s=SYMS,function=source.FUNCTION):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[function],rs,function,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 n=fs[function]['size']//4
 return list(struct.unpack('>%dI'%n,sections(p.with_suffix('.elf'))['.text'][1][:n*4]))
def images(label,entry=source.ENTRY,s=SYMS):
 result=[linked(o/n,label+'-'+str(i),entry,s)for i,n in enumerate(('original-func_1510FC34.o','selected-final.o','qualified-padded.o','make-shadow/src/game/generated_13BB20.c.o'))]
 assert all(w==result[0]for w in result)
 return result
def compare(words,c,s=SYMS,entry=source.ENTRY,initial=None,connected=None):
 initial=fixture(c,s,bool(connected))if initial is None else initial;want,calls=reference(initial,c,s,bool(connected))
 models=[Oracle(w,initial,c,entry,s,connected).run()for w in words]
 for m in models:assert public(m.memory)==public(want)and m.calls==calls,(c,'public state/calls',m.calls,calls)
 for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and m.observations==models[0].observations
 return models[0]
def guest_suite():
 count=aliases=cuts=delays=0;seen=set()
 for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
  s=SYMS if j==0 else {n:(0x81007FFC+j*0x10000+i*0x10000)for i,n in enumerate(SYMS)}
  if j:
   s.update({n:entry+0x10000+0x100*i for i,n in enumerate(('func_1510FD20','func_1510FE30','func_150A6760','func_150F33F8'))})
  words=images('view-rebase-'+str(j),entry,s)
  for view,xy,value,previous,flag,mode,sp in itertools.product((0,3),((0.,-0.75),(32767.75,-32768.75),(2147483520.,-2147483520.)),(0,0xFFFFFFFF,0x80008000,32767),(0,-1),(0,60),(0,255),(0,8)):
   c=Case(view,*xy,value,previous,flag,mode,sp);m=compare(words,c,s,entry);seen.update(p-entry for p in m.visits if entry<=p<entry+236);count+=1
  if j==0:
   for index,a in enumerate((dict(s,D_800DBDCC=VIEWS+0x300),dict(s,D_800DBDC4=s['D_800DBE30']),dict(s,D_800DBDC0=s['D_800DBFF0']))):
    aw=images('view-alias-'+str(index),entry,a)
    for sp in(0,8):compare(aw,Case(phase=sp),a,entry);aliases+=1
   for c in(Case(),Case(category=0,flag=0),Case(mode=255),Case(phase=8,mode=255)):
    initial=fixture(c);good=Oracle(words[0],initial,c).run()
    for cut in range(good.root_accesses):
     models=[]
     for w in words:
      m=Oracle(w,initial,c,fault=cut)
      try:m.run()
      except phase.faults.AccessBoundary:pass
      else:raise AssertionError('Ineffective access cut')
      models.append(m)
     for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace and(m.current_pc,m.delay_of,m.root_accesses)==(models[0].current_pc,models[0].delay_of,models[0].root_accesses)
     cuts+=1;delays+=models[0].delay_of is not None
 assert seen==set(range(0,236,4)),sorted(set(range(0,236,4))-seen)
 return dict(cases=count,executions=4*count,reachable_words=len(seen),independent_rebases=3,aliases=aliases,access_prefix_cases=cuts,branch_delay_cuts=delays,full_state_and_access_trace_equal=True,finite_valid_f32_to_s32=True,FCSR_or_portable_alias_claim=False)

def connected_suite():
 asm=(o/'before-conker_asm_13BB20.s').read_text();code={};sizes={}
 for name,address in (('func_1510FD20',LOOKUP),('func_1510FE30',CATEGORY)):
  a=asm.index('glabel '+name);b=asm.index('endlabel '+name,a)
  # Retain named relocations when assembling each complete original helper.
  p=o/('helper-'+name+'.s');p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.section .text\n.type '+name+', @function\n'+asm[a:b]+'.size '+name+', . - '+name+'\n')
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(r/'conker/include'),'-o',str(p.with_suffix('.o')),str(p)],capture_output=True,check=True)
  w=linked(p.with_suffix('.o'),'connected-'+name,address,SYMS,name);sizes[name]=len(w);code.update({address+4*i:v for i,v in enumerate(w)})
 roots=images('view-connected');seen=set();count=0
 for tree,x,z,previous,flag,sp in itertools.product(range(4),(-20.,-7.,-4.,0.,4.,8.,20.,28.),(-20.,-4.,0.,4.,20.,28.),(0,2),(0,60),(0,8)):
  c=Case(0,x,z,previous=previous,flag=flag,phase=sp,tree=tree);m=compare(roots,c,connected=code);seen.update(m.visits);count+=1
 return dict(cases=count,executions=4*count,original_helper_words=sizes,lookup_words_visited=sum(LOOKUP+4*i in seen for i in range(sizes['func_1510FD20'])),category_words_visited=sum(CATEGORY+4*i in seen for i in range(sizes['func_1510FE30'])),null_and_leaf_and_branch_trees=True,signed_relative_offsets=True,complete_spatial_tree_or_gameplay_claim=False)

def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();target=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
 sites=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==target]
 pointers=[i for i in range(0,len(rom)-3,4)if struct.unpack_from('>I',rom,i)[0]==source.ENTRY]
 assert sites==[0x466F0]and pointers==[],(sites,pointers)
 start,stop,after=0x15019228,0x15019260,0x15019248
 window=list(struct.unpack_from('>14I',rom,0x466D8));roots=images('view-callers');count=0
 for maximum,mode,flag,sp,poison in itertools.product((-1,0,1,3),(0,1,2),(0,60),(0,8),(0,1,0x80000000,0xFFFFFFFF)):
  c=Case(flag=flag,phase=sp);initial=fixture(c);put(initial,SYMS['D_80082FA0'],maximum&0xFFFFFFFF)
  expected=dict(initial);calls=[];v=0
  while v<=signed(read(expected,SYMS['D_80082FA0'])):
   expected,seq=reference(expected,c,view=v);calls.extend([(source.ENTRY,(v,)),*seq])
   if mode==1:put(expected,SYMS['D_80082FA0'],0)
   elif mode==2 and v==0:put(expected,SYMS['D_80082FA0'],3)
   v+=1;assert v<=4
  # Apply loop-bound mutation at the real post-call boundary, independent of
  # which notification callbacks run within this call.
  class Code(phase.WindowCode):
   def __getitem__(self,pc):
    if pc==after:
     view=read(self.owner.memory,self.owner.r[29]+0x24)
     if mode==1:put(self.owner.memory,SYMS['D_80082FA0'],0)
     elif mode==2 and view==0:put(self.owner.memory,SYMS['D_80082FA0'],3)
    return super().__getitem__(pc)
  models=[]
  for w in roots:
   m=Oracle(window,initial,c,start,connected=dict(zip(range(source.ENTRY,source.ENTRY+236,4),w)))
   m.stop_pc,m.poison_pc,m.poison_value=stop,after,poison;m.code=Code(dict(m.code),m)
   try:m.run()
   except phase.WindowStop:pass
   else:raise AssertionError('Caller loop did not stop')
   assert public(m.memory)==public(expected)and m.calls==calls,(maximum,mode,flag,sp,'caller',m.calls,calls)
   assert m.r[4]==v and m.r[29]==STACK+sp
   models.append(m)
  for m in models[1:]:assert complete(m)==complete(models[0])and m.trace==models[0].trace
  count+=1
 return dict(cases=count,executions=4*count,original_window_words=14,aligned_JAL_sites=sites,aligned_literal_pointers=pointers,ignored_return_poisons=4,inclusive_live_bound_reload=True,negative_skip_and_growing_and_shrinking_bounds=True,full_parent_or_gameplay_claim=False)

def native_harness(headers,body):
 return headers+r'''
typedef union {u32 u; f32 f;} FloatBits;
static f32 number(u32 x){FloatBits v;v.u=x;return v.f;}
static u32 word(f32 x){FloatBits v;v.f=x;return v.u;}
typedef char pointer_is_four[sizeof(void *)==4?1:-1];
typedef char view_stride_is_2464[sizeof(ViewRecord)==0x9A0?1:-1];
u8 *D_800DBFF0,*D_800DBDC8;
s32 D_800DBDC0,D_800DBDC4,D_800BE9F0;
f32 D_800DBDCC,D_800DBDD0;
s16 D_800DBE30[6];
static union {u32 align;u8 bytes[4*0x9A0+64];} views;
static u8 leaves[8];
typedef struct {u32 base,view,category,leaf,x,z; s16 previous[4]; s32 flag;} State;
typedef struct {u32 target,a,b;} Event;
static Event observed[4],expectedEvents[4];
static unsigned calls,expectedCalls,mode,view,seed;
static s32 suppliedCategory;
static State expected;
static State capture(void){
 State s;unsigned i;
 s.base=(u32)D_800DBFF0;s.view=(u32)D_800DBDC0;s.category=(u32)D_800DBDC4;
 s.leaf=(u32)D_800DBDC8;s.x=word(D_800DBDCC);s.z=word(D_800DBDD0);s.flag=D_800BE9F0;
 for(i=0;i<4;i++)s.previous[i]=D_800DBE30[i];
 return s;
}
static void restore(State *s){
 unsigned i;
 D_800DBFF0=(u8 *)s->base;D_800DBDC0=(s32)s->view;D_800DBDC4=(s32)s->category;
 D_800DBDC8=(u8 *)s->leaf;D_800DBDCC=number(s->x);D_800DBDD0=number(s->z);D_800BE9F0=s->flag;
 for(i=0;i<4;i++)D_800DBE30[i]=s->previous[i];
}
static void change(State *s,unsigned target){
 if(target==0){
  if(mode&1)s->base=(u32)(views.bytes+0x9A0);
  if(mode&2)s->view=0xDEADBEEFu;
  if(mode&4)s->x=0x7FC12345u;
 }else if(target==1){
  if(mode&8)s->previous[view]=(s16)suppliedCategory;
  if(mode&16)s->flag=60;
 }else if(target==2){
  if(mode&32)s->flag=59;
  if(mode&64)s->category=0x80000000u;
 }else if(mode&128)s->leaf=0x89ABCDEFu;
}
static void observe(unsigned target,u32 a,u32 b){
 State s=capture();
 if(calls>=4)__builtin_trap();
 observed[calls].target=target;observed[calls].a=a;observed[calls].b=b;calls++;
 change(&s,target);restore(&s);
}
u8 *func_1510FD20(s32 x,s32 z){observe(0,(u32)x,(u32)z);return leaves+(seed&7);}
s32 func_1510FE30(u8 *leaf){observe(1,(u32)leaf,0);return suppliedCategory;}
void func_150A6760(s32 v){observe(2,(u32)v,0);}
void func_150F33F8(s32 v){observe(3,(u32)v,0);}
''' + body+r'''
static void expect(unsigned target,u32 a,u32 b){
 expectedEvents[expectedCalls].target=target;expectedEvents[expectedCalls].a=a;expectedEvents[expectedCalls].b=b;expectedCalls++;
 change(&expected,target);
}
static void reference(f32 x,f32 z){
 s32 ix=(s32)x,iz=(s32)z;
 expected.view=view;expected.x=word((f32)ix);expected.z=word((f32)iz);
 expect(0,(u32)ix,(u32)iz);
 expected.leaf=(u32)(leaves+(seed&7));expect(1,expected.leaf,0);
 expected.category=(u32)suppliedCategory;
 if(suppliedCategory!=(s32)expected.previous[view]){
  expected.previous[view]=(s16)suppliedCategory;expect(2,view,0);
 }
 if(expected.flag==60)expect(3,view,0);
}
static int run_cases(void){
 static const s32 categories[8]={0,1,-1,32767,-32768,65536,0x7FFFFFFF,(s32)0x80008000u};
 static const s16 previous[4]={0,-1,32767,-32768};
 static const f32 coords[8]={0.0f,-0.75f,12.75f,-17.5f,32767.75f,-32768.75f,2147483520.0f,-2147483520.0f};
 unsigned n,i,j;
 for(i=0;i<sizeof(views.bytes);i++)views.bytes[i]=(u8)(i*13+0x59);
 for(n=0;n<65536;n++){
  f32 x=coords[(n>>5)&7],z=coords[((n>>5)+3)&7];State actual;
  view=n&3;mode=(n>>8)&255;seed=n*1664525u+1013904223u;suppliedCategory=categories[(n>>2)&7];
  for(i=0;i<4;i++){
   *(f32 *)(views.bytes+i*0x9A0+0x2F8)=x;
   *(f32 *)(views.bytes+i*0x9A0+0x300)=z;
   D_800DBE30[i]=previous[(n>>3)&3];
  }
  D_800DBE30[4]=(s16)0xA55A;D_800DBE30[5]=(s16)0x5AA5;
  D_800DBFF0=views.bytes;D_800DBDC0=123;D_800DBDC4=456;D_800DBDC8=leaves+7;
  D_800DBDCC=-1.0f;D_800DBDD0=-2.0f;D_800BE9F0=((n>>10)%3==0)?60:((n>>10)%3==1)?0:59;
  expected=capture();calls=expectedCalls=0;reference(x,z);func_1510FC34((s32)view);actual=capture();
  if(actual.base!=expected.base||actual.view!=expected.view||actual.category!=expected.category||actual.leaf!=expected.leaf||actual.x!=expected.x||actual.z!=expected.z||actual.flag!=expected.flag)return 74;
  for(i=0;i<4;i++)if(actual.previous[i]!=expected.previous[i])return 74;
  if(calls!=expectedCalls)return 74;
  for(i=0;i<calls;i++)if(observed[i].target!=expectedEvents[i].target||observed[i].a!=expectedEvents[i].a||observed[i].b!=expectedEvents[i].b)return 74;
  if((u16)D_800DBE30[4]!=0xA55A||(u16)D_800DBE30[5]!=0x5AA5)return 75;
  if(!(n&255))for(i=0;i<sizeof(views.bytes);i++){
   unsigned cell=i/0x9A0,offset=i%0x9A0;int coordinate=cell<4&&((offset>=0x2F8&&offset<0x2FC)||(offset>=0x300&&offset<0x304));
   if(!coordinate&&views.bytes[i]!=(u8)(i*13+0x59))return 76;
  }
  for(j=0;j<8;j++)if(leaves[j])return 77;
 }
 return 0;
}
void _start(void){int result=run_cases();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
def native_suite():
 body=source.SELECTED;headers=source.HEADERS
 controls={
 'wrong-X-offset':body.replace('record + 0x2F8','record + 0x300'),
 'wrong-Z-offset':body.replace('record + 0x300','record + 0x2F8'),
 'untruncated-X-publication':body.replace('D_800DBDCC = (f32)x;','D_800DBDCC = *(f32 *)(record + 0x2F8);'),
 'narrowed-category':body.replace('category = func_1510FE30(leaf);','category = (s16)func_1510FE30(leaf);'),
 'reversed-cache-gate':body.replace('category != *previous','category == *previous'),
 'wrong-cache-index':body.replace('&D_800DBE30[view]','&D_800DBE30[(view + 1) & 3]'),
 'missing-leaf-publication':body.replace('D_800DBDC8 = leaf;','D_800DBDC8 = NULL;'),
 'wrong-refresh-gate':body.replace('D_800BE9F0 == 60','D_800BE9F0 != 60'),
 'wrong-notification-view':body.replace('func_150A6760(view);','func_150A6760(view ^ 1);'),
 'stale-refresh-flag':body.replace('s16 *previous;','s16 *previous;\n    s32 flag = D_800BE9F0;').replace('D_800BE9F0 == 60','flag == 60'),
 }
 results=[]
 for label,opt,text,control in [('positive-'+opt,opt,body,False)for opt in('-O0','-O2','-O3')]+[(n,'-O2',v,True)for n,v in controls.items()]:
  assert not control or text!=body,label
  p=o/('native-'+label+'.c');p.write_text(native_harness(headers,text));exe=p.with_suffix('')
  command=native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)]
  q=subprocess.run(command,capture_output=True,text=True);assert q.returncode==0,(label,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True);assert q.returncode==(74 if control else 0),(label,q.returncode,q.stdout,q.stderr)
  results.append(dict(name=label,optimization=opt,control=control,exit=q.returncode))
 return dict(positive_cases_each=65536,profiles=['O0','O2','O3'],effective_controls=len(controls),controls_exit_by_semantic_mismatch=True,UBSan_trapping=True,all_four_view_slots_and_all256_callback_modes=True,complete_public_state_and_provider_log=True,cache_canaries_and_periodic_view_bytes=True,finite_f32_to_s32_only=True,FCSR_or_portable_alias_claim=False,results=results)
