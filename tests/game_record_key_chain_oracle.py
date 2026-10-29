from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/'conker/build/game-record-key-chain-match';F='func_15195D00';ENTRY=0x15195D00;OWNER,OTHER,NODES,NEW,OLD=0x30000,0x34000,0x50000,0x70000,0x90000
SYMS=dict(D_800E08E0=0x800E08E0,D_800E08E4=0x800E08E4,func_151957B0=0x151957B0)
@dataclass(frozen=True)
class Case:
 length:int=0
 match:int=-2
 key:int=0x12345678
 index:int=1234
 mode:int=255
 pool:int=0
 mutation:int=0
 phase:int=0
def fixture(c,s=None):
 s=SYMS if s is None else s;m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for base,n in((OWNER,64),(OTHER,64),(NODES,0x200),(NEW,32),(OLD,32)):m.update({base+i:(i*29+0x59)&255 for i in range(n)})
 put(m,OWNER+0x18,NODES if c.length else 0)
 for i in range(c.length):
  p=NODES+32*i;put(m,p+8,c.key if i==c.match or(c.match==-1 and i==0)else c.key^0x01000000^i);put(m,p+12,(c.index^(1 if c.match==-1 else 0))&65535,2);put(m,p+16,p+32 if i+1<c.length else 0)
 put(m,OLD,0);put(m,OLD+4,0);put(m,s['D_800E08E0'],OLD if c.pool else 0);put(m,s['D_800E08E4'],OLD if c.pool else 0);return m
def provider(m,c,s,home):
 head=s['D_800E08E0'];tail=s['D_800E08E4'];prior=read(m,tail);put(m,NEW+4,0);put(m,NEW,prior)
 if prior:put(m,prior+4,NEW)
 else:put(m,head,NEW)
 put(m,tail,NEW)
 if c.mutation&1:put(m,home,OTHER)
 if c.mutation&2:put(m,home+12,0xABCD0080)
 if c.mutation&4:put(m,OWNER+0x18,OLD)
def reference(initial,c,s=None):
 s=SYMS if s is None else s;m=dict(initial);home=STACK+c.phase;put(m,home,OWNER);put(m,home+12,c.mode);cursor=read(m,OWNER+0x18);record=cursor
 if cursor:
  while True:
   if read(m,record+8)==c.key and read(m,record+12,2)==c.index:return m,[],cursor
   cursor=read(m,record+16)
   if cursor:record=cursor;cursor=read(m,cursor+16)
   if not cursor:break
 calls=[(s['func_151957B0'],(20,s['D_800E08E0'],s['D_800E08E4']))];provider(m,c,s,home)
 if record:put(m,record+16,NEW)
 else:put(m,read(m,home)+0x18,NEW)
 put(m,NEW+8,c.key);put(m,NEW+12,c.index&65535,2);mode=read(m,home+12);put(m,NEW+16,0);m[NEW+14]=mode&255;return m,calls,NEW
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY,s=None,connected=None):super().__init__(words,memory,c,entry=entry,s=SYMS if s is None else s,connected=connected,arguments=(OWNER,c.key,c.index,c.mode))
 def record_call(self,t):
  assert t==self.syms['func_151957B0'];args=tuple(self.arguments(3));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  provider(self.memory,self.case,self.syms,STACK+self.case.phase)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=NEW
def linked(obj,label,entry=ENTRY,s=None):
 s=SYMS if s is None else s;text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
public=lambda m:{a:b for a,b in m.items()if not STACK-256<=a<STACK+256}

import sys
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
def run_suite(stage_output):
 global o,frame_checks
 q=sys.modules[__name__]
 o=stage_output;r=Path.cwd();objects=(o/('original-'+q.F+'.o'),o/'qualified-padded.o',o/'selected.o');programs=[q.linked(obj,'qualified-'+str(i))for i,obj in enumerate(objects)];assert programs[0]==programs[1]
 state=lambda m:(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo)
 count=0;visited=set();frame_checks=0
 class Probe(q.Oracle):
  def record_call(self,t):
   global frame_checks
   super().record_call(t)
   assert self.r[29]==q.STACK+self.case.phase-40
   if self.case.length:
    assert q.read(self.memory,self.r[29]+36)==q.NODES+32*(self.case.length-1);frame_checks+=1
 for length in range(8):
  for match,key,index,mode,pool,mutation,phase in itertools.product(range(-2,length),(0,1,0x80000000,0xFFFFFFFF),(0,65535,65536,0xFFFFFFFF),(0,255,0x12340080),(0,1),(0,3,7),(0,8)):
   c=q.Case(length,match,key,index,mode,pool,mutation,phase);initial=q.fixture(c);want,calls,value=q.reference(initial,c);pair=[]
   for j,words in enumerate(programs):
    m=(Probe if j<2 else q.Oracle)(words,initial,c).run();assert(q.public(m.memory),m.calls,m.r[2])==(q.public(want),calls,value),(c,j);pair.append(m)
   assert state(pair[0])==state(pair[1]);visited.update(pair[0].visits);count+=1
 print('qualified guest cases',count,flush=True)
 prefixes=0
 for c in(q.Case(0),q.Case(1,-2,mutation=3,phase=8),q.Case(3,0),q.Case(3,1),q.Case(3,2,pool=1,mutation=7),q.Case(7,-1,index=0xFFFFFFFF,pool=1,phase=8)):
  initial=q.fixture(c);full=q.Oracle(programs[0],initial,c).run()
  for cut in range(full.all_accesses):
   pair=[]
   for words in programs[:2]:
    m=q.Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Missing dispatched access boundary')
    pair.append(m)
   assert state(pair[0])==state(pair[1])and(pair[0].current_pc,pair[0].delay_of)==(pair[1].current_pc,pair[1].delay_of);prefixes+=1
 c=q.Case(3,0);sparse=q.fixture(c)
 for base,n in((q.SYMS['D_800E08E0'],8),(q.NEW,32),(q.OLD,32),(q.NODES+32,0x200-32),(q.NODES+16,4)):
  for i in range(n):sparse.pop(base+i,None)
 for words in programs:
  m=q.Oracle(words,sparse,c).run();assert not m.calls and q.public(m.memory)==q.public(sparse)
 rebases=0
 for k,(entry,base)in enumerate(((0x15001000,0x80007FF0),(0x1F008000,0x80008000),(0x1000FFF0,0x8000FFF0))):
  s=dict(D_800E08E0=base,D_800E08E4=base+4,func_151957B0=0x151957B0);triple=[q.linked(obj,'rebase-%d-%d'%(k,j),entry,s)for j,obj in enumerate(objects)];assert triple[0]==triple[1]
  for length,match,index,mutation,phase in itertools.product((0,1,3,7),(-2,0,1,6),(0,65535,65536,0xFFFFFFFF),(0,3,7),(0,8)):
   if match>=length:continue
   c=q.Case(length,match,0xFFFFFFFF,index,0x12340080,1,mutation,phase);initial=q.fixture(c,s);want,calls,value=q.reference(initial,c,s)
   for words in triple:
    m=q.Oracle(words,initial,c,entry,s).run();assert(q.public(m.memory),m.calls,m.r[2])==(q.public(want),calls,value)
   rebases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();window=list(struct.unpack_from('>11I',rom,0x1C33DC));END=0x15195F58;caller_cases=0
 class Caller(q.Oracle):
  def record_call(self,t):
   if t==q.ENTRY:
    args=tuple(self.arguments(4));self.calls.append((t,args));self.events.append(('CALL',t,args))
   else:super().record_call(t)
 for length in(0,1,3):
  for match,key,index,mode,mutation,phase in itertools.product(range(-2,length),(0,0xFFFFFFFF),(0,65535,65536,0xFFFFFFFF),(0,255,0x12340080,0xFFFFFFFF),(0,3),(0,8)):
   c=q.Case(length,match,key,index,mode,1,mutation,phase);initial=q.fixture(c);q.put(initial,q.STACK+phase+0x50,mode);before=dict(initial);signed_mode=mode if mode<0x80000000 else mode-0x100000000
   if before[q.OWNER+0x14]<signed_mode:before[q.OWNER+0x14]=mode&255
   want,calls,_=q.reference(before,c);calls=[(q.ENTRY,(q.OWNER,key,index,mode))]+calls;pair=[]
   for words in programs:
    code=dict(zip(range(q.ENTRY,q.ENTRY+212,4),words));code[END]=0;m=Caller(window,initial,c,entry=0x15195F2C,connected=code);m.r[16]=q.OWNER;m.r[18]=index;m.r[22]=key;m.r[21]=11;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing original caller boundary')
    assert(q.public(m.memory),m.calls,m.r[21],m.r[16],m.r[18],m.r[22],m.r[29])==(q.public(want),calls,12,q.OWNER,index,key,q.STACK+phase),(c,m.calls,calls);pair.append(m)
   assert state(pair[0])==state(pair[1]);caller_cases+=1
 receipt=dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,words=53,covered_words=len(visited),unvisited=[hex(pc)for pc in range(q.ENTRY,q.ENTRY+212,4)if pc not in visited],frame=40,record_spill_home=36,spill_value_checks=frame_checks,raw_public_memory_calls_equal=True,normalized_full_state_equal=True,return_register_diagnostic_only=True,void_interface_inferred_from_only_retained_caller=True,access_prefix_pairs=prefixes,sparse_head_match_skip=True,rebase_layouts=3,rebase_cases=rebases,caller_words=11,caller_cases=caller_cases,parent_result_register_unused=True,complete_parent_claimed=False,provider_bounded=True,guest_only_incoming_home_mutations=True,allocation_failure_C_domain_claimed=False)

 receipt['connected_constructor']=run_connected_constructor(stage_output)
 return receipt

from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 body=selected[selected.index('/* Preserve'):];F='func_15195D00'
 mutants=dict(signed_index=body.replace('*(u16 *)(record + 0xC) == index','*(s16 *)(record + 0xC) == index'),truncated_index=body.replace('== index)','== (u16)index)'),key_width=body.replace('*(s32 *)(record + 8)','*(u16 *)(record + 8)'),wrong_mode=body.replace('cursor[0xE] = mode','cursor[0xE] = 0'),wrong_clear=body.replace('*(u8 **)(cursor + 0x10) = NULL','*(u8 **)(cursor + 0xC) = NULL'),wrong_append=body.replace('*(u8 **)(record + 0x10) = cursor','*(u8 **)(owner + 0x18) = cursor'),wrong_owner=body.replace('*(u8 **)(owner + 0x18) = cursor','*(u8 **)(owner + 0x1C) = cursor'))
 normal=body;start=normal.index('    if (cursor != NULL) {');end=normal.index('        cursor = (u8 *)func_151957B0',start)
 normal=normal[:start]+'''    if (cursor != NULL) {
        record = cursor;
        for (;;) {
            if (*(s32 *)(record + 8) == key && *(u16 *)(record + 0xC) == index) return;
            cursor = *(u8 **)(record + 0x10);
            if (cursor == NULL) break;
            record = cursor;
        }
'''+normal[end:];mutants['full_tail_search']=normal;assert all(x!=body for x in mutants.values())
 text='''#include <ultra64.h>
s32 D_800E08E0,D_800E08E4;
static union {u32 align;u8 b[64];} owner;
static union {u32 align;u8 b[256];} nodes;
static union {u32 align;u8 b[32];} created,oldPool;
static s32 calls,mutation;static u32 observed[3];
s32 func_151957B0(s32 size,u8 *head,u8 *tail){u8 *prior=*(u8**)tail;
 calls++;observed[0]=size;observed[1]=(u32)head;observed[2]=(u32)tail;
 *(u8**)(created.b+4)=NULL;*(u8**)created.b=prior;
 if(prior)*(u8**)(prior+4)=created.b;else *(u8**)head=created.b;
 *(u8**)tail=created.b;if(mutation)*(u8**)(owner.b+0x18)=oldPool.b;
 return (s32)created.b;
}
'''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items())
 text+='''
static const u32 keys[4]={0,1,0x80000000,0xFFFFFFFF},indices[4]={0,65535,65536,0xFFFFFFFF},modes[3]={0,255,0x12340080};
static void fill(void*p,u32 n,u8 seed){u8*b=p;u32 i;for(i=0;i<n;i++)b[i]=(u8)(i*29+seed);}
static void setup(s32 length,s32 match,u32 key,u32 index,s32 pool,s32 effect){s32 i;u8*p;
 fill(&owner,sizeof(owner),0x59);fill(&nodes,sizeof(nodes),0xA5);fill(&created,sizeof(created),0x37);fill(&oldPool,sizeof(oldPool),0x23);
 *(u8**)(owner.b+0x18)=length?nodes.b:NULL;
 for(i=0;i<length;i++){p=nodes.b+32*i;*(u32*)(p+8)=i==match||(match==-1&&i==0)?key:key^0x01000000u^(u32)i;*(u16*)(p+12)=(u16)(index^(match==-1?1:0));*(u8**)(p+16)=i+1<length?p+32:NULL;}
 *(u32*)oldPool.b=0;*(u32*)(oldPool.b+4)=0;D_800E08E0=pool?(s32)oldPool.b:0;D_800E08E4=pool?(s32)oldPool.b:0;calls=0;mutation=effect;observed[0]=observed[1]=observed[2]=0;
}
static void reference(u8*own,s32 key,s32 index,s32 mode){u8*cursor=*(u8**)(own+0x18),*record=cursor;
 if(cursor){for(;;){if(*(u32*)(record+8)==(u32)key&&(u32)*(u16*)(record+12)==(u32)index)return;cursor=*(u8**)(record+16);if(cursor){record=cursor;cursor=*(u8**)(cursor+16);}if(!cursor)break;}
 cursor=(u8*)func_151957B0(20,(u8*)&D_800E08E0,(u8*)&D_800E08E4);*(u8**)(record+16)=cursor;
 }else{cursor=(u8*)func_151957B0(20,(u8*)&D_800E08E0,(u8*)&D_800E08E4);*(u8**)(own+0x18)=cursor;}
 *(u32*)(cursor+8)=(u32)key;*(u16*)(cursor+12)=(u16)index;*(u8**)(cursor+16)=NULL;cursor[14]=(u8)mode;
}
static u8 snapshot[512];static u32 used;
static s32 transfer(void*p,u32 n,s32 save){u8*b=p;u32 i;for(i=0;i<n;i++){if(save)snapshot[used+i]=b[i];else if(snapshot[used+i]!=b[i])return 1;}used+=n;return 0;}
static s32 state(s32 save){used=0;return transfer(&owner,sizeof(owner),save)||transfer(&nodes,sizeof(nodes),save)||transfer(&created,sizeof(created),save)||transfer(&oldPool,sizeof(oldPool),save)||transfer(&D_800E08E0,4,save)||transfer(&D_800E08E4,4,save)||transfer(&calls,4,save)||transfer(observed,sizeof(observed),save);}
typedef void(*Fn)(u8*,s32,s32,s32);
static s32 check(Fn fn){s32 n,match,k,i,t,p,e,count=0;
 for(n=0;n<8;n++)for(match=-2;match<n;match++)for(k=0;k<4;k++)for(i=0;i<4;i++)for(t=0;t<3;t++)for(p=0;p<2;p++)for(e=0;e<2;e++){
 setup(n,match,keys[k],indices[i],p,e);reference(owner.b,(s32)keys[k],(s32)indices[i],(s32)modes[t]);state(1);
 setup(n,match,keys[k],indices[i],p,e);fn(owner.b,(s32)keys[k],(s32)indices[i],(s32)modes[t]);if(state(0))return 1;count++;
 }return count==8448?0:2;
}
static s32 run(void){if(sizeof(void*)!=4)return 90;if(check(test_selected))return 10;
'''
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 return text+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

def run_connected_constructor(stage_output):
 global o
 o=stage_output;ALLOC=0x10003C40;CTOR=0x151957B0;FIRST=0xB0000
 rom=(Path.cwd()/'conker/conker.us.bin').read_bytes();constructor=struct.unpack_from('>29I',rom,0x1C2C60)
 assert constructor[0]==0x27BDFFE8 and constructor[6]==0x0C000F10
 programs=[linked(obj,'connected-'+str(j))for j,obj in enumerate((o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected.o'))];assert programs[0]==programs[1]
 class Connected(Oracle):
  def record_call(self,t):
   assert t in(CTOR,ALLOC);args=tuple(self.arguments(3 if t==CTOR else 4));self.calls.append((t,args));self.events.append(('CALL',t,args))
  def hook(self,t):
   assert t==ALLOC and self.calls[-1][1]==(20,1,0,0)
   home=STACK+self.case.phase
   if self.case.mutation&1:put(self.memory,home,OTHER)
   if self.case.mutation&2:put(self.memory,home+12,0xABCD0080)
   if self.case.mutation&4:put(self.memory,OWNER+0x18,OLD)
   for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
   self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=NEW
 count=0;nonempty_pool_proofs=0
 for length,match,index,mutation,phase,pool_shape in itertools.product((0,1,3,7),(-2,0,1,6),(0,65535,65536,0xFFFFFFFF),(0,3,7),(0,8),(0,1,2)):
  if match>=length:continue
  c=Case(length,match,0xFFFFFFFF,index,0x12340080,int(pool_shape!=0),mutation,phase);initial=fixture(c)
  if pool_shape==2:
   initial.update({FIRST+i:(i*13+0x5A)&255 for i in range(32)});put(initial,FIRST,0);put(initial,FIRST+4,OLD);put(initial,OLD,FIRST);put(initial,SYMS['D_800E08E0'],FIRST)
  want,calls,value=reference(initial,c);calls=[item for call in calls for item in(call,(ALLOC,(20,1,0,0)))];pair=[]
  for words in programs:
   code=dict(zip(range(CTOR,CTOR+116,4),constructor));m=Connected(words,initial,c,connected=code).run();assert(public(m.memory),m.calls,m.r[2])==(public(want),calls,value),(c,pool_shape,m.calls,calls);pair.append(m)
   if calls and pool_shape==2:
    assert read(m.memory,SYMS['D_800E08E0'])==FIRST and read(m.memory,SYMS['D_800E08E4'])==NEW and read(m.memory,NEW)==OLD and read(m.memory,OLD+4)==NEW;nonempty_pool_proofs+=1
  assert(pair[0].r,pair[0].f,pair[0].memory,pair[0].calls,pair[0].events,pair[0].trace,pair[0].hi,pair[0].lo)==(pair[1].r,pair[1].f,pair[1].memory,pair[1].calls,pair[1].events,pair[1].trace,pair[1].hi,pair[1].lo);count+=1
 return dict(cases=count,executions=count*3,constructor_words=29,constructor_frame=24,allocator_arguments=[20,1,0,0],two_element_pool_head_tail_checks=nonempty_pool_proofs,actual_retail_constructor_connected=True,successful_allocations_only=True,allocator_bounded=True,extra_conversion_credit=0)
