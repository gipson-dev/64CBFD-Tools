"""Independent private guest model for the complete resource-allocation routine."""
from pathlib import Path
from dataclasses import dataclass
import hashlib,itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-actor-resource-allocation-match';F='func_150832AC';ENTRY=0x150832AC
SYMS=dict(D_80082FA0=0x80082FA0,func_1515D480=0x1515D480,func_1515D440=0x1515D440)
signed=lambda x:(x^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 descriptor:int=1
 requested:int=0
 flag:int=0
 last:int=0
 outcome:int=1
 mutation:int=0
 alias:int=-1
 phase:int=0
def actor(c,s):return 0x30000 if c.alias<0 else s['D_80082FA0']-c.alias
def descriptor(c,s):return actor(c,s)if c.descriptor==2 else 0x50000 if c.descriptor else 0
def fixture(c,s=SYMS):
 a=actor(c,s);d=descriptor(c,s);m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for base,n in((a,1024),(0x50000,64)):m.update({base+i:(i*29+0x59)&255 for i in range(n)})
 put(m,a+0x144,d);m[a+0x127]=c.flag
 if d:m[d+0x2F]=c.requested
 put(m,a+0x300,0 if c.outcome==2 else 0x12345678);put(m,s['D_80082FA0'],c.last&0xFFFFFFFF);return m
def returned(c,n,trailing=False):
 if c.outcome==0:return 0
 return ((0x80010000 if c.outcome==2 else 0x80070000)+(0x1000 if trailing else n*0x100))&0xFFFFFFFF
def provider(m,c,s,n,trailing=False):
 a=actor(c,s);d=descriptor(c,s)
 if c.mutation==1:put(m,s['D_80082FA0'],0xFFFFFFFF)
 elif c.mutation==2:put(m,s['D_80082FA0'],2 if n<2 and not trailing else 0xFFFFFFFF)
 elif c.mutation==3:
  m[a+0x127]^=0xFF
  if d:m[d+0x2F]^=0x7F
  put(m,a+0x144,0)
 return returned(c,n,trailing)
def reference(initial,c,s=SYMS):
 m=dict(initial);a=actor(c,s);d=read(m,a+0x144);calls=[]
 if not d:return m,calls
 requested=m[d+0x2F];count=requested or(3 if m[a+0x127]else 5);index=0
 while index<=signed(read(m,s['D_80082FA0'])):
  assert index<8,('Unbounded test allocation',c,index)
  calls.append((s['func_1515D480'],(count,)));value=provider(m,c,s,index);put(m,a+0x304+4*index,value);index+=1
 if read(m,a+0x300+4*index):m[a+0x301]=count&255
 calls.append((s['func_1515D440'],()));value=provider(m,c,s,index,True);put(m,a+0x314,value);return m,calls
public=lambda m:{a:b for a,b in m.items()if not STACK-256<=a<STACK+256}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  self.allocations=0;super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(actor(c,s),))
 def record_call(self,t):
  assert t in(self.syms['func_1515D480'],self.syms['func_1515D440'],ENTRY),hex(t)
  n=1 if t in(self.syms['func_1515D480'],ENTRY)else 0;args=tuple(self.arguments(n));self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  trailing=t==self.syms['func_1515D440'];assert trailing or t==self.syms['func_1515D480']
  assert self.r[29]==STACK+self.case.phase-48
  for offset,reg in((24,16),(28,17),(32,18),(36,19),(40,20),(44,31)):assert read(self.memory,self.r[29]+offset)==(self.expected_target_ra if reg==31 and hasattr(self,'expected_target_ra')else self.before[reg]),(offset,reg)
  value=provider(self.memory,self.case,self.syms,self.allocations,trailing)
  if not trailing:self.allocations+=1
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def cases():
 for args in itertools.product((0,1,2),(0,1,128,255),(0,255),(-2147483648,-1,0,1,3,5),(0,1,2),(0,1,2,3),(-1,0x300,0x304),(0,8)):yield Case(*args)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo)
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1];count=0;visited=set();allocation_calls=0
 for c in cases():
  initial=fixture(c);want,calls_expected=reference(initial,c);machines=[]
  for i,words in enumerate(programs):
   m=Oracle(words,initial,c).run();assert(public(m.memory),m.calls)==(public(want),calls_expected),(c,i);machines.append(m)
  assert state(machines[0])==state(machines[1]),c;visited.update(machines[0].visits);count+=1;allocation_calls+=machines[0].allocations
 assert len(visited)==54,(len(visited),sorted(visited));print(dict(guest_cases=count,covered_words=len(visited)),flush=True)
 prefixes=0
 for c in(Case(descriptor=0),Case(),Case(requested=128,last=5),Case(last=-1),Case(mutation=2,phase=8),Case(mutation=3,descriptor=2),Case(alias=0x304,outcome=2)):
  initial=fixture(c);full=Oracle(programs[0],initial,c).run()
  for cut in range(full.all_accesses):
   pair=[]
   for words in programs[:2]:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missed access boundary',c,cut))
    pair.append(m)
   assert state(pair[0])==state(pair[1]);prefixes+=1
 # A null descriptor does not require the global, flags, unused actor data or providers.
 c=Case(descriptor=0);m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)};put(m,actor(c,SYMS)+0x144,0)
 for words in programs:machine=Oracle(words,m,c).run();assert public(machine.memory)==public(m)and machine.calls==[]
 rebased=0
 for k,(entry,g)in enumerate(((0x15001000,0x80007FF0),(0x1F008000,0x80008000),(0x1000FFF0,0x8000FFF0))):
  s=dict(SYMS,D_80082FA0=g);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)];assert ps[0]==ps[1]
  for args in itertools.product((0,1,2),(0,255),(-1,0,5),(0,1,2),(-1,0x300,0x304)):
   c=Case(descriptor=args[0],requested=args[1],last=args[2],mutation=args[3],alias=args[4]);initial=fixture(c,s);want,calls_expected=reference(initial,c,s)
   for words in ps:machine=Oracle(words,initial,c,s,entry).run();assert(public(machine.memory),machine.calls)==(public(want),calls_expected)
   rebased+=1
 callers=caller_suite(programs)
 q=dict(original_caller_windows=callers,private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,covered_words=54,raw_compiler_words=53,normalized_words=54,frame=48,allocation_calls=allocation_calls,zero_return_word_probes=True,real_allocator_failure_completion_claimed=False,live_signed_count_mutations=True,descriptor_and_flag_mutations=True,global_record_aliases=True,normalized_literal_full_state_equal=True,raw_public_effects_equal=True,void_result_register_ignored=True,access_prefix_pairs=prefixes,sparse_null_descriptor=True,rebase_layouts=3,rebase_cases=rebased,providers_bounded=True,hardware_or_complete_parent_claimed=False)
 return q

def caller_suite(programs):
 rom=(r/'conker/conker.us.bin').read_bytes();rows=[]
 for entry,offset,length,end in((0x15083088,0xB0538,4,0x1508309C),(0x150314AC,0x5E95C,7,0x150314C8)):
  window=list(struct.unpack_from('>%dI'%length,rom,offset));assert window[0]==0x0D420CAB;count=0
  for requested,desc,flag,last,outcome,phase in itertools.product((0,128),(0,1),(0,255),(-1,0,3),(0,1),(0,8)):
   c=Case(requested=requested,descriptor=desc,flag=flag,last=last,outcome=outcome,phase=phase);initial=fixture(c);a=actor(c,SYMS);index=0 if not flag else 2;slot=a+index*4
   if entry==0x150314AC:put(initial,slot+0x304,0)
   want,expected=reference(initial,c)
   for words in programs:
    connected=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));connected[end]=0
    m=Oracle(window,initial,c,entry=entry,connected=connected);m.expected_target_ra=entry+8
    if entry==0x15083088:m.r[16]=a
    else:m.r[18]=a;m.r[2]=slot
    m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing original caller-window boundary')
    assert(public(m.memory),m.calls)==(public(want),[(ENTRY,(a,))]+expected),(hex(entry),c)
    if entry==0x150314AC:
     assert m.r[2]==slot and m.r[3]==1 and read(m.memory,STACK+phase+0x54)==slot
     assert read(m.memory,STACK+phase+0x50)==read(want,slot+0x304)
   count+=1
  rows.append(dict(entry=hex(entry),ROM=hex(offset),words=length,cases=count,arguments=1,result_register_ignored=True,earlier_parent_gates_preconditions=True,complete_parent_claimed=False))
 return rows



from tools.tests.test_game_row_destination_fill import START
def native_harness(selected):
 global F
 body=selected[selected.index('/* Allocate'):]
 mutants=dict(cached_count=body.replace('    s32 rawCount;','    s32 rawCount;\n    s32 cachedCount = D_80082FA0;').replace('index <= D_80082FA0','index <= cachedCount'),exclusive_bound=body.replace('index <= D_80082FA0','index < D_80082FA0'),wrong_final_test=body.replace('actor + index * 4 + 0x300','actor + index * 4 + 0x304'),unconditional_byte=body.replace('if (*(u32 *)(actor + index * 4 + 0x300) != 0)','if (1)'),wrong_fallback=body.replace('? 5 : 3','? 7 : 3'),omit_trailing=body.replace('*(u8 **)(actor + 0x314) = func_1515D440();','*(u8 **)(actor + 0x314) = 0;'))
 assert all(v!=body for v in mutants.values())
 text=r'''#include <ultra64.h>
 typedef struct {s32 descriptor,requested,flag,last,outcome,mutation,alias;} Case;
 typedef struct {u32 kind,argument;} Event;
 static u8 actorData[1024] __attribute__((aligned(8)));
 static u8 descriptorData[64] __attribute__((aligned(8)));
 static s32 separateCount,*countPointer;
 static const Case *currentCase;
 static Event events[16];static s32 eventCount,allocationCount,badBound;
 #define D_80082FA0 (*countPointer)
 static u32 provider(s32 trailing){
  const Case *c=currentCase;u8*d=c->descriptor==2?actorData:c->descriptor?descriptorData:0;u32 value;
  if(c->mutation==1)*countPointer=-1;
  else if(c->mutation==2)*countPointer=allocationCount<2&&!trailing?2:-1;
  else if(c->mutation==3){actorData[0x127]^=255;if(d)d[0x2F]^=0x7F;*(u8**)(actorData+0x144)=0;}
  value=c->outcome==0?0:(c->outcome==2?0x80010000u:0x80070000u)+(trailing?0x1000u:(u32)allocationCount*0x100u);
  if(!trailing)allocationCount++;return value;
 }
 u8 *func_1515D480(s32 count){if(eventCount>=15){badBound=1;*countPointer=-1;return 0;}events[eventCount].kind=1;events[eventCount++].argument=(u32)count;return (u8 *)provider(0);}
 u8 *func_1515D440(void){if(eventCount>=15){badBound=1;return 0;}events[eventCount].kind=2;events[eventCount++].argument=0;return (u8 *)provider(1);}
 static void reference(u8 *a){
  u8*d=*(u8**)(a+0x144);s32 quantity,i;
  if(!d)return;quantity=d[0x2F];if(!quantity)quantity=a[0x127]?3:5;
  for(i=0;i<=*countPointer;i++){if(i>=8){badBound=1;return;}*(u8**)(a+0x304+i*4)=func_1515D480(quantity);}
  if(*(u32*)(a+0x300+i*4))a[0x301]=(u8)quantity;
  *(u8**)(a+0x314)=func_1515D440();
 }
 '''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items())
 cases=list(itertools.product((0,1,2),(0,1,128,255),(0,255),(-2147483648,-1,0,1,3,5),(0,1,2),(0,1,2,3),(-1,0x300,0x304)));assert len(cases)==5184
 text+='\nstatic const Case cases[]={\n'+',\n'.join('{'+','.join(str(x)if x!=-2147483648 else'(-2147483647-1)'for x in c)+'}'for c in cases)+'\n};\n'
 text+=r'''
 static void setup(const Case*c){s32 i;currentCase=c;for(i=0;i<1024;i++)actorData[i]=(u8)(i*29+0x59);for(i=0;i<64;i++)descriptorData[i]=(u8)(i*29+0x59);
  *(u8**)(actorData+0x144)=c->descriptor==2?actorData:c->descriptor?descriptorData:0;actorData[0x127]=(u8)c->flag;
  if(c->descriptor==2)actorData[0x2F]=(u8)c->requested;else if(c->descriptor)descriptorData[0x2F]=(u8)c->requested;
  *(u32*)(actorData+0x300)=c->outcome==2?0:0x12345678u;countPointer=c->alias<0?&separateCount:(s32*)(actorData+c->alias);*countPointer=c->last;eventCount=0;allocationCount=0;badBound=0;
 }
 typedef void(*Fn)(u8*);
 static u8 expectedActor[1024],expectedDescriptor[64];static Event expectedEvents[16];
 static s32 check(Fn fn){s32 n,i,ne,na,nc;for(n=0;n<5184;n++){
  setup(cases+n);reference(actorData);if(badBound)return 99;for(i=0;i<1024;i++)expectedActor[i]=actorData[i];for(i=0;i<64;i++)expectedDescriptor[i]=descriptorData[i];for(i=0;i<eventCount;i++)expectedEvents[i]=events[i];ne=eventCount;na=allocationCount;nc=separateCount;
  setup(cases+n);fn(actorData);if(badBound||eventCount!=ne||allocationCount!=na)return 1;
  for(i=0;i<1024;i++)if(actorData[i]!=expectedActor[i])return 2;for(i=0;i<64;i++)if(descriptorData[i]!=expectedDescriptor[i])return 3;
  for(i=0;i<eventCount;i++)if(events[i].kind!=expectedEvents[i].kind||events[i].argument!=expectedEvents[i].argument)return 4;
  if(cases[n].alias<0&&separateCount!=nc)return 5;
  }return 0;}
 static int run(void){if(sizeof(void*)!=4)return 90;if(check(test_selected))return 10;
 '''
 for i,name in enumerate(mutants):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

 return text
