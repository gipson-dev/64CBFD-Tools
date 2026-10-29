"""Resource list memory model, bounded helper effects and native32 harness."""
from pathlib import Path
from dataclasses import dataclass
import itertools,struct,subprocess
from tools.experiments import game_resource_byte_list_match as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ROOT=Path(__file__).resolve().parents[2];o=ROOT/source.BUILD
F,ENTRY,ROM=source.FUNCTION,source.ENTRY,source.ROM
FIRST,SECOND=0x1503D774,0x1503D660
RECORD,RESOURCE_A,RESOURCE_B,LIST_A,LIST_B,ACTOR=0x30000,0x70000,0x71000,0x50000,0x51000,0x60000
syms=dict(D_800D1C90=0x800D1C90,D_80086CAC=0x80086CAC,func_1503D774=FIRST,func_1503D660=SECOND)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 identity:int=17
 primary:int=2
 extra:int=1
 selector:int=0
 context:int=0x87654321
 unused:int=0xABCDEF87
 mutation:int=0
 phase:int=0
 seed:int=0
def args(c):return (RECORD,u32(c.unused),u32(c.context))
def fixture(c,s=None):
 s=syms if s is None else s;m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-512,512)}
 for p,n in ((RECORD-16,352),(RESOURCE_A-16,96),(RESOURCE_B-16,96),(LIST_A-16,560),(LIST_B-16,560),(ACTOR-16,352)):
  assert not(p<STACK+512 and p+n>STACK-512),'Fixture overlaps guest stack'
  for i in range(n):m[p+i]=(i*13+c.seed+0x59)&255
 for i in range(256):put(m,s['D_800D1C90']+4*i,RESOURCE_A);put(m,s['D_80086CAC']+4*i,LIST_A if i%2==0 else LIST_B)
 for p,selector in ((RESOURCE_A,c.selector),(RESOURCE_B,c.selector^1)):
  m[p+4]=c.primary;m[p+5]=selector;m[p+0x38]=c.extra
 m[RECORD+4]=c.identity;return m
def root_effect(m,c,s):
 if c.mutation&1:put(m,s['D_800D1C90']+c.identity*4,RESOURCE_B)
 if c.mutation&2:m[RECORD+4]=0x21
def selection(m,c,s):
 resource=read(m,s['D_800D1C90']+c.identity*4);count=m[resource+4]
 cursor=RECORD+4 if count==0 else read(m,s['D_80086CAC']+4*m[resource+5]);return resource,cursor,(count or 1)+m[resource+0x38]
def loop_effect(m,c,s,resource,cursor,first):
 if first:
  if c.mutation&4:m[cursor]^=0x5A
  if c.mutation&16:
   m[resource+4]=m[resource+0x38]=255;put(m,s['D_80086CAC']+4*m[resource+5],LIST_B)
 elif c.mutation&8:m[cursor+1]=0xE1
def reference(initial,c,s=None):
 s=syms if s is None else s;m=dict(initial);calls=[]
 if c.identity==255:return m,calls
 calls.append((s['func_1503D774'],(c.identity,u32(c.context))));root_effect(m,c,s);resource,cursor,count=selection(m,c,s)
 for i in range(count):
  calls.append((s['func_1503D774'],(m[cursor],u32(c.context))));loop_effect(m,c,s,resource,cursor,True)
  calls.append((s['func_1503D660'],(m[cursor],u32(c.context))));loop_effect(m,c,s,resource,cursor,False);cursor+=1
 return m,calls
class ListOracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None):
  super().__init__(words,memory,c,entry=entry,s=syms if s is None else s,connected=connected,arguments=args(c));self.stage=0;self.cursor=None;self.resource=None
 def record_call(self,t):
  assert t in (self.syms['func_1503D774'],self.syms['func_1503D660']);a=tuple(self.arguments(2));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  if self.stage==0:
   assert t==self.syms['func_1503D774'];root_effect(self.memory,self.case,self.syms);self.resource,self.cursor,_=selection(self.memory,self.case,self.syms)
  else:
   first=self.stage%2==1;assert t==self.syms['func_1503D774'if first else'func_1503D660'];loop_effect(self.memory,self.case,self.syms,self.resource,self.cursor,first)
   if not first:self.cursor+=1
  self.stage+=1
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0x87654321
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def state(m):return(m.r,m.f,m.hi,m.lo,m.condition,m.memory,m.events,m.calls,m.trace)
def cases():
 for identity,primary,extra,mode,phase in itertools.product((0,186,255),(0,1,4),(0,2),(0,1,2,4,8,16,31),(0,8)):
  yield Case(identity=identity,primary=primary,extra=extra,selector=5 if mode&1 else 0,mutation=mode,phase=phase,context=0x87654321 if mode&2 else 0,unused=0xFFFFFFFF if phase else 0)
 for primary,extra,mode in itertools.product((0,255),(0,255),(0,31)):
  yield Case(identity=17,primary=primary,extra=extra,selector=5,mutation=mode)
def linked(obj,entry,label,s=None):
 s=syms if s is None else s;text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def native_harness():
 body=source.SELECTED;header=source.HEADERS;F=source.FUNCTION
 controls=dict(sentinel=body.replace('identity != 255','identity < 186'),extra=body.replace('count += resource[0x38]','count += 0'),default_count=body.replace('count = 1;','count = 0;'),signed_byte=body.replace('func_1503D774(*cursor, context)','func_1503D774(*(s8 *)cursor, context)'),context=body.replace('func_1503D660(*cursor, context)','func_1503D660(*cursor, 0)'),cached_byte=body.replace('            func_1503D774(*cursor, context);','            s32 captured = *cursor;\n            func_1503D774(captured, context);').replace('func_1503D660(*cursor, context)','func_1503D660(captured, context)'))
 assert all(t!=body for t in controls.values());t=header+'\n'.join(b.replace(F,'test_'+n)for n,b in dict(selected=body,**controls).items())
 t+=r'''
static u8 record[336],resourceA[64],resourceB[64],listA[544],listB[544];
static u8 wantedRecord[336],wantedA[64],wantedB[64],wantedListA[544],wantedListB[544];
u8 *D_800D1C90[187];u32 D_80086CAC[6];
static s32 mode,bad,calls,expectedCalls,wantedContext;static u8 wantedIdentity;static u8 *activeCursor,*activeResource;
static s32 expectedIds[1024],expectedTags[1024];
static s32 helper(s32 tag,s32 identity,s32 context){
 if(calls>=expectedCalls||tag!=expectedTags[calls]||identity!=expectedIds[calls]||context!=wantedContext)bad=1;
 if(calls++==0){
  if(mode&1)D_800D1C90[wantedIdentity]=resourceB;
  if(mode&2)record[4]=0x21;
  activeResource=D_800D1C90[wantedIdentity];activeCursor=activeResource[4]?(u8*)D_80086CAC[activeResource[5]]:record+4;
 }else if(tag==1){
  if(mode&4)*activeCursor^=0x5A;
  if(mode&16){activeResource[4]=activeResource[0x38]=255;D_80086CAC[activeResource[5]]=(u32)listB;}
 }else{if(mode&8)activeCursor[1]=0xE1;activeCursor++;}
 return -123456789;
}
s32 func_1503D774(s32 identity,s32 context){return helper(1,identity,context);}
s32 func_1503D660(s32 identity,s32 context){return helper(2,identity,context);}
typedef void(*Fn)(u8*,s32,s32);
static s32 modes[]={0,1,2,4,8,16,31},identities[]={0,17,186,255},primaries[]={0,1,4,255},extras[]={0,2,255};
static int check(Fn fn){s32 id,p,e,sel,m,i,n,selector;u8 *res,*cursor;
 for(id=0;id<4;id++)for(p=0;p<4;p++)for(e=0;e<3;e++)for(sel=0;sel<2;sel++)for(m=0;m<7;m++){
  wantedIdentity=(u8)identities[id];mode=modes[m];wantedContext=(mode&2)?-123456789:0;selector=sel?5:0;
  for(i=0;i<336;i++)record[i]=wantedRecord[i]=(u8)(i*13+0x59);
  for(i=0;i<64;i++){resourceA[i]=wantedA[i]=(u8)(i*13+0x69);resourceB[i]=wantedB[i]=(u8)(i*13+0x79);}
  for(i=0;i<544;i++){listA[i]=wantedListA[i]=(u8)(i*13+0x89);listB[i]=wantedListB[i]=(u8)(i*13+0x99);}
  for(i=0;i<187;i++)D_800D1C90[i]=resourceA;for(i=0;i<6;i++)D_80086CAC[i]=(u32)(i%2?listB:listA);
  record[4]=wantedRecord[4]=wantedIdentity;resourceA[4]=resourceB[4]=wantedA[4]=wantedB[4]=(u8)primaries[p];resourceA[0x38]=resourceB[0x38]=wantedA[0x38]=wantedB[0x38]=(u8)extras[e];
  resourceA[5]=wantedA[5]=(u8)selector;resourceB[5]=wantedB[5]=(u8)(selector^1);expectedCalls=0;
  if(wantedIdentity!=255){
   expectedTags[expectedCalls]=1;expectedIds[expectedCalls++]=wantedIdentity;if(mode&2)wantedRecord[4]=0x21;
   res=(mode&1)?wantedB:wantedA;n=(res[4]?res[4]:1)+res[0x38];cursor=res[4]?(res[5]%2?wantedListB:wantedListA):wantedRecord+4;
   for(i=0;i<n;i++){
    expectedTags[expectedCalls]=1;expectedIds[expectedCalls++]=*cursor;if(mode&4)*cursor^=0x5A;
    if(mode&16)res[4]=res[0x38]=255;
    expectedTags[expectedCalls]=2;expectedIds[expectedCalls++]=*cursor;if(mode&8)cursor[1]=0xE1;cursor++;
   }
  }
  bad=calls=0;fn(record,(s32)0xABCDEF87u,wantedContext);if(bad||calls!=expectedCalls)return 1;
  for(i=0;i<336;i++)if(record[i]!=wantedRecord[i])return 2;
  for(i=0;i<64;i++)if(resourceA[i]!=wantedA[i]||resourceB[i]!=wantedB[i])return 3;
  for(i=0;i<544;i++)if(listA[i]!=wantedListA[i]||listB[i]!=wantedListB[i])return 4;
  if(wantedIdentity!=255&&D_800D1C90[wantedIdentity]!=((mode&1)?resourceB:resourceA))return 5;
 }return 0;
}
static int run(void){if(sizeof(void*)!=4)return 90;if(check(test_selected))return 10;
'''
 for i,n in enumerate(controls):t+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
 return t+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
