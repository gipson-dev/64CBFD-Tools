from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/'conker/build/game-path-node-gate-match';F='func_1507B974';ENTRY=0x1507B974;CURRENT,OTHER,TABLE,ROW,OTHER_ROW=0x30000,0x34000,0x50000,0x70000,0x90000
SYMS=dict(D_800D154C=0x800D154C,D_800CC2D0=0x800CC2D0,D_800D2104=0x800D2104,D_800D1890=0x800D1890,D_800D1891=0x800D1891,D_800D1892=0x800D1892,D_800D1893=0x800D1893,func_15075400=0x15075400)
@dataclass(frozen=True)
class Case:
 selector:int=0
 table_index:int=0
 record_index:int=0
 offset:int=0
 key:int=0
 compare:int=0
 flag:int=0
 mode:int=0
 alias:int=0
 phase:int=0
 command:int=247

def fixture(c,s=None):
 s=SYMS if s is None else s;p=s['D_800D1890'];params=[c.command,c.compare,c.flag,c.offset]
 if c.alias==1:params[0],params[1]=c.key>>8,c.key&255
 elif c.alias==2:params[2],params[3]=c.key>>8,c.key&255
 row=ROW if not c.alias else p+(0 if c.alias==1 else 2)-6-8*(c.record_index+params[3]);m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base,n in ((row,4096),(OTHER_ROW,4096),(CURRENT,0x32C),(OTHER,0x32C)):
  assert not(base<STACK+1024 and base+n>STACK-1024);m.update({base+i:(i*13+0x59)&255 for i in range(n)})
 actor=CURRENT
 if c.selector:
  assert 1<=c.selector<=26;actor=s['D_800CC2D0']+(c.selector-1)*0x32C;m.update({actor+i:(i*29+0xA5)&255 for i in range(0x32C)})
 m[CURRENT+0x65]=c.selector;m[CURRENT+0x13F]=125;m[CURRENT+0x21E]=106;m[actor+0x13F]=c.table_index;m[actor+0x21E]=c.record_index
 for i in range(256):put(m,TABLE+i*4,OTHER_ROW)
 put(m,TABLE+c.table_index*4,row);put(m,s['D_800D154C'],CURRENT);put(m,s['D_800D2104'],TABLE)
 for i,v in enumerate(params):m[p+i]=v
 put(m,row+8*(c.record_index+params[3])+6,c.key,2);return m

def effect(m,c,s,actor):
 p=s['D_800D1890']
 if c.mode&1:m[p]^=255;m[p+2]^=0xAA
 if c.mode&2:put(m,s['D_800D154C'],OTHER);put(m,s['D_800D2104'],TABLE+0x2000)
 if c.mode&4:m[actor+0x13F]^=7;m[actor+0x21E]^=9

def reference(initial,c,s=None):
 s=SYMS if s is None else s;m=dict(initial);actor=read(m,s['D_800D154C']);selector=m[actor+0x65]
 if selector:actor=s['D_800CC2D0']+(selector-1)*0x32C
 table=read(m,s['D_800D2104']);row=read(m,table+4*m[actor+0x13F]);node=row+8*m[actor+0x21E]+8*m[s['D_800D1893']];key=read(m,node+6,2)
 if m[s['D_800D1891']]==key:m[s['D_800D1892']]^=1
 calls=[]
 if m[s['D_800D1892']]:calls.append((s['func_15075400'],(m[s['D_800D1890']],)));effect(m,c,s,actor)
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY,s=None,connected=None):super().__init__(words,memory,c,entry=entry,s=SYMS if s is None else s,connected=connected,arguments=())
 def record_call(self,t):
  assert t==self.syms['func_15075400'];args=tuple(self.arguments(1));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  s=self.syms;actor=read(self.memory,s['D_800D154C']);selector=self.memory[actor+0x65]
  if selector:actor=s['D_800CC2D0']+(selector-1)*0x32C
  effect(self.memory,self.case,s,actor)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def linked(obj,label,entry=ENTRY,s=None):
 s=SYMS if s is None else s;text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
public=lambda m:{a:b for a,b in m.items()if not STACK-1024<=a<STACK+1024}
def cases():
 for vals in itertools.product((0,1,26),(0,255),(0,255),(0,255),(0,1,255,256,32768,65535),(0,1,255),(0,1,2,255),(0,7),(0,8)):
  selector,table_index,record_index,offset,key,compare,flag,mode,phase=vals;yield Case(selector,table_index,record_index,offset,key,compare,flag,mode,0,phase)
 for vals in itertools.product((0,1,26),(0,255,256,65535),(0,255),(0,1,255),(0,7),(1,2),(0,8)):
  selector,key,compare,flag,mode,alias,phase=vals;yield Case(selector,255,255,255,key,compare,flag,mode,alias,phase)

def run_guest(output):
 global o
 o=output
 original=linked(o/('original-'+F+'.o'),'guest-original');normalized=linked(o/'qualified-padded.o','guest-qualified');raw=linked(o/'selected.o','guest-raw');assert original==normalized;count=0;visited=set()
 for c in cases():
  initial=fixture(c);want,calls=reference(initial,c);pair=[]
  for words in(original,normalized,raw):
   m=Oracle(words,initial,c).run();assert(public(m.memory),m.calls)==(public(want),calls),(c,m.calls,calls);pair.append(m)
  assert(pair[0].r,pair[0].f,pair[0].memory,pair[0].events,pair[0].trace)==(pair[1].r,pair[1].f,pair[1].memory,pair[1].events,pair[1].trace);visited.update(pair[0].visits);count+=1

 return dict(cases=count,executions=count*3,covered_words=len(visited),raw_public_memory_calls_equal=True,normalized_full_state_equal=True)

def run_boundaries(output):
 global o
 import sys
 q=sys.modules[__name__]
 o=output;r=Path.cwd();F=q.F;rom=(r/'conker/conker.us.bin').read_bytes()
 a=q.linked(o/('original-'+F+'.o'),'bounds-original');n=q.linked(o/'qualified-padded.o','bounds-normalized');raw=q.linked(o/'selected.o','bounds-raw');assert a==n
 assert struct.unpack_from('>I',rom,0x22B300)[0]==q.ENTRY
 WINDOW,END,SCRIPT,CHANGED=0x1507BD00,0x1507BD74,0xB0000,0xB1000
 window=list(struct.unpack_from('>29I',rom,0xA91B0));assert window[0]==0x8E020218
 # ROM conversion is relative to the retained parent, not a guessed segment base.
 assert window==list(struct.unpack_from('>29I',rom,0xA90C4+WINDOW-0x1507BC14))
 class Caller(q.Oracle):
  def __init__(self,m,c,words,mutate):
   code=dict(zip(range(q.ENTRY,q.ENTRY+212,4),words));code[END]=0
   super().__init__(window,m,c,entry=WINDOW,connected=code);self.mutate=mutate
   self.r[16]=q.CURRENT
   for reg,name in zip(range(17,21),('D_800D1890','D_800D1891','D_800D1892','D_800D1893')):self.r[reg]=q.SYMS[name]
   self.r[21]=0x80086730;self.before=self.r[:];self.code=WindowCode(self.code,self);self.code.ends=(END,)
  def record_call(self,t):
   if t==q.ENTRY:self.calls.append((t,()));self.events.append(('CALL',t,()))
   else:super().record_call(t)
  def hook(self,t):
   assert t==q.SYMS['func_15075400'];super().hook(t)
   if self.mutate:q.put(self.memory,q.CURRENT+0x218,CHANGED)
 count=0
 for selector,key,compare,flag,mode,phase,mutate,opcode in itertools.product((0,1,26),(0,255,256,65535),(0,255),(0,1,255),(0,7),(0,8),(False,True),(0x44,0xF7,0xFF)):
  c=q.Case(selector,255,255,255,key,compare,flag,mode,0,phase);initial=q.fixture(c);q.put(initial,q.CURRENT+0x218,SCRIPT);q.put(initial,0x80086840,q.ENTRY)
  params=bytes((247,compare,flag,255))
  for i,b in enumerate(bytes((opcode,))+params):initial[SCRIPT+i]=b
  want=dict(initial);calls=[]
  if opcode<247:
   for i,b in enumerate(params):want[q.SYMS['D_800D1890']+i]=b
   want,calls=q.reference(want,c);calls=[(q.ENTRY,())]+calls
   base=CHANGED if mutate and len(calls)>1 else SCRIPT
   q.put(want,q.CURRENT+0x218,base+5)
  else:q.put(want,q.CURRENT+0x218,SCRIPT+1)
  pair=[]
  for words in(a,n,raw):
   m=Caller(initial,c,words,mutate)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing dispatcher boundary')
   assert(q.public(m.memory),m.calls)==(q.public(want),calls),(c,opcode,mutate,m.calls,calls)
   pair.append(m)
  assert(pair[0].r,pair[0].f,pair[0].memory,pair[0].trace)==(pair[1].r,pair[1].f,pair[1].memory,pair[1].trace)
  count+=1
 print('caller cases',count,flush=True)
 prefixes=0
 for c in(q.Case(),q.Case(selector=26,key=255,compare=255,flag=1,mode=7,phase=8),q.Case(selector=1,key=65535,flag=255,alias=2)):
  initial=q.fixture(c);full=q.Oracle(a,initial,c).run()
  for cut in range(full.all_accesses):
   pair=[]
   for words in(a,n):
    m=q.Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Missing actual access cut')
    pair.append(m)
   assert(pair[0].r,pair[0].f,pair[0].memory,pair[0].trace,pair[0].events,pair[0].current_pc,pair[0].delay_of)==(pair[1].r,pair[1].f,pair[1].memory,pair[1].trace,pair[1].events,pair[1].current_pc,pair[1].delay_of)
   prefixes+=1
 # No command byte is required on a mismatch whose flag stays clear.
 c=q.Case(key=256,compare=0,flag=0);sparse=q.fixture(c);del sparse[q.SYMS['D_800D1890']]
 for words in(a,n,raw):
  m=q.Oracle(words,sparse,c).run();assert not m.calls
  assert not any(e[1]>=q.SYMS['D_800CC2D0'] and e[1]<q.SYMS['D_800CC2D0']+26*0x32C for e in m.trace)
 rebases=0
 for k,(entry,base)in enumerate(((0x15001000,0x80007FF0),(0x1F008000,0x80008000),(0x1000FFF0,0x8000FFF0))):
  s=dict(q.SYMS,D_800CC2D0=base,D_800D154C=base+0x527C,D_800D2104=base+0x5E34,func_15075400=(entry&0xF0000000)|0x0075400)
  for i in range(4):s['D_800D189'+str(i)]=base+0x55C0+i
  triple=[q.linked(obj,'rebased-%d-%d'%(k,j),entry,s)for j,obj in enumerate((o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected.o'))];assert triple[0]==triple[1]
  for selector,key,compare,flag,mode,alias in itertools.product((0,1,26),(0,255,256,65535),(0,255),(0,255),(0,7),(0,1,2)):
   c=q.Case(selector,255,255,255,key,compare,flag,mode,alias,8);initial=q.fixture(c,s);want,calls=q.reference(initial,c,s)
   for words in triple:
    m=q.Oracle(words,initial,c,entry,s).run();assert(q.public(m.memory),m.calls)==(q.public(want),calls),(k,c)
   rebases+=1
 print('rebases',rebases,flush=True)
 body,rs=payload(o/'selected.o',F);controls=0
 def checked(b,bindings):
  if b!=body or bindings!=rs:raise ValueError('Changed raw source ABI payload')
 for i in range(len(body)):
  bad=bytearray(body);bad[i]^=1
  try:checked(bytes(bad),rs)
  except ValueError:controls+=1
  else:raise AssertionError('Ineffective body control')
 for at in rs:
  try:checked(body,{**rs,at:[('R_MIPS_26','wrong_symbol')]})
  except ValueError:controls+=1
  else:raise AssertionError('Ineffective binding control')
 rows=list(csv.DictReader(io.StringIO((o/'proposed-guards.csv').read_text())));mine=[x for x in rows if x['filename']=='game_A28B0' and x['function']==F];assert len(mine)==31
 for i,g in enumerate(mine):
  modified=[dict(x,expected=hex(int(x['expected'],0)^1))if x is g else x for x in rows];stream=io.StringIO();w=csv.DictWriter(stream,list(rows[0]));w.writeheader();w.writerows(modified);p=o/('rejected-guard-%d.csv'%i);p.write_text(stream.getvalue())
  try:emit_padded_assembly(o/'after-owner.o',r/'conker/retail_layout.us.txt','game_A28B0',word_patches_path=p)
  except ValueError:pass
  else:raise AssertionError('Ineffective preimage control')
 receipt=dict(private_only=True,installed=False,matching_credit=0,caller_cases=count,caller_words=29,opcode=68,command_F7_skip=True,post_provider_script_reload=True,complete_parent_claimed=False,access_prefix_pairs=prefixes,sparse_skips=1,rebase_layouts=3,rebase_cases=rebases,raw_controls=controls,guard_controls=len(mine))

 return receipt

from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import test_game_actor_burst_consumer_match as faults
import csv,io,sys
sys.path.insert(0,str(Path.cwd()/"tools"))
from tools.pad_c_object import emit_padded_assembly

from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 body=selected[selected.index("/* Toggle"):];F="func_1507B974"
 mutants={
  'wrong_row':body.replace('[actor->unk13F]','[actor->unk21E]'),
  'wrong_record':body.replace('node += actor->unk21E * 8;','node += actor->unk13F * 8;'),
  'wrong_key':body.replace('node + 6','node + 4'),
  'truncate_key':body.replace('*(u16 *)(node + 6)','(u8)*(u16 *)(node + 6)'),
  'no_selector':body.replace('if (actor->unk65 != 0)','if (0)'),
  'or_toggle':body.replace('D_800D1892 ^= 1','D_800D1892 |= 1'),
  'old_gate':body.replace('    u8 *node;','    u8 *node;\n    u8 previous = D_800D1892;').replace('if (D_800D1892 != 0)','if (previous != 0)'),
  'wrong_command':body.replace('func_15075400(D_800D1890)','func_15075400(D_800D1891)')}
 assert all(v!=body for v in mutants.values())
 text='''#include <ultra64.h>
 #include "variables.h"
 #define OFFSETOF(T,f) ((u32)&((T*)0)->f)
 typedef char actor_size[sizeof(struct127)==0x32C?1:-1];
 typedef char selector_offset[__builtin_offsetof(struct127,unk65)==0x65?1:-1];
 typedef char row_offset[__builtin_offsetof(struct127,unk13F)==0x13F?1:-1];
 typedef char record_offset[__builtin_offsetof(struct127,unk21E)==0x21E?1:-1];
 struct127 D_800CC2D0[26],*D_800D154C;
 s32 *D_800D2104;
 static union {u32 align;u8 b[8192];} backing,otherRow;
 static struct127 current,other;
 static u8 *table[256],*parameters,*activeRow;
 static s32 mode,calls,last;
 #define D_800D1890 parameters[0]
 #define D_800D1891 parameters[1]
 #define D_800D1892 parameters[2]
 #define D_800D1893 parameters[3]
 void func_15075400(s32 command) {
  struct127 *a=D_800D154C;
  if(a->unk65)a=D_800CC2D0+a->unk65-1;
  calls++;last=command;
  if(mode&1){parameters[0]^=255;parameters[2]^=0xAA;}
  if(mode&2){D_800D154C=&other;D_800D2104=(s32*)(table+1);}
  if(mode&4){a->unk13F^=7;a->unk21E^=9;}
 }
 '''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items())
 text+='''
 static void reference(void) {
  struct127 *a=D_800D154C;u8 *row;u16 key;
  if(a->unk65)a=D_800CC2D0+(unsigned)a->unk65-1;
  row=table[(unsigned)a->unk13F];
  key=*(u16*)(row+8*((unsigned)a->unk21E+(unsigned)parameters[3])+6);
  if(key==(unsigned)parameters[1])parameters[2]=(u8)(parameters[2]^1);
  if(parameters[2])func_15075400((unsigned)parameters[0]);
 }
 static const u16 keys[]={0,1,255,256,32768,65535};
 static const u8 selectors[]={0,1,26},bytes[]={0,1,255},flags[]={0,1,2,255};
 static void fill(void*p,u32 n,u8 value){u8*b=p;u32 i;for(i=0;i<n;i++)b[i]=(u8)(value+i*13);}
 static void setup(s32 sel,s32 ti,s32 ri,s32 off,s32 key,s32 cmp,s32 flag,s32 md,s32 alias){
  struct127 *a;u32 i;u16 *k;
  fill(&backing,sizeof(backing),0x59);fill(&otherRow,sizeof(otherRow),0xA3);
  fill(&current,sizeof(current),0x37);fill(&other,sizeof(other),0x2B);fill(D_800CC2D0,sizeof(D_800CC2D0),0x47);
  D_800D154C=&current;D_800D2104=(s32*)table;mode=md;calls=0;last=-1;
  current.unk65=sel;current.unk13F=125;current.unk21E=106;
  a=sel?D_800CC2D0+sel-1:&current;a->unk13F=ti;a->unk21E=ri;
  parameters=backing.b+4096;
  parameters[0]=247;parameters[1]=cmp;parameters[2]=flag;parameters[3]=off;
  if(alias){k=(u16*)(parameters+(alias==1?0:2));*k=(u16)key;}
  activeRow=alias?parameters+(alias==1?0:2)-6-8*((unsigned)ri+parameters[3]):backing.b;
  for(i=0;i<256;i++)table[i]=otherRow.b;
  table[ti]=activeRow;
  *(u16*)(activeRow+8*((unsigned)ri+parameters[3])+6)=(u16)key;
 }
 static u8 snapshot[40000];static u32 used;
 static s32 transfer(void*p,u32 n,s32 save){u8*b=p;u32 i;for(i=0;i<n;i++){if(save)snapshot[used+i]=b[i];else if(snapshot[used+i]!=b[i])return 1;}used+=n;return 0;}
 static s32 state(s32 save){used=0;
  if(transfer(&backing,sizeof(backing),save)||transfer(&otherRow,sizeof(otherRow),save)||transfer(&current,sizeof(current),save)||transfer(&other,sizeof(other),save)||transfer(D_800CC2D0,sizeof(D_800CC2D0),save))return 1;
  return 0;
 }
 typedef void(*Fn)(void);
 static s32 check(Fn fn){s32 si,ti,ri,oi,ki,ci,fi,mi,al,wcalls,wlast,wcurrent,wtable,count=0;
  for(si=0;si<3;si++)for(ti=0;ti<2;ti++)for(ri=0;ri<2;ri++)for(oi=0;oi<2;oi++)
  for(ki=0;ki<6;ki++)for(ci=0;ci<3;ci++)for(fi=0;fi<4;fi++)for(mi=0;mi<2;mi++)for(al=0;al<3;al++){
  #define SETUP setup(selectors[si],ti*255,ri*255,oi*255,keys[ki],bytes[ci],flags[fi],mi*7,al)
  SETUP;reference();state(1);wcalls=calls;wlast=last;wcurrent=D_800D154C==&current;wtable=D_800D2104==(s32*)table;
  SETUP;fn();if(state(0)||calls!=wcalls||last!=wlast||(D_800D154C==&current)!=wcurrent||(D_800D2104==(s32*)table)!=wtable)return 1;count++;
  }
  return count==10368?0:2;
 }
 static s32 run(void){if(sizeof(void*)!=4)return 90;if(check(test_selected))return 10;
 '''
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

 return text
from tools.experiments.game_four_head_lookup_match import payload
