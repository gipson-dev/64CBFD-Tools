"""Actor point resolution and vertical interval: ordered aliases and literal helpers."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests import game_actor_height_position_oracle as legacy
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-position-action-150EAF50-match';F='func_150EAF50';ENTRY=0x150EAF50
STACK,ACTOR,POSITION,RESULT=legacy.STACK,legacy.ACTOR,legacy.POSITION,legacy.RESULT
put,read,bits,floating=legacy.put,legacy.read,legacy.bits,legacy.floating
OTHER,ALT_RESULT=0x40000,0x44000
SYMS=dict(func_15142314=0x15142314,func_1504715C=0x1504715C,func_15046C80=0x15046C80)
RESOLVE,INITIALIZE,QUERY=SYMS.values()
@dataclass(frozen=True)
class Case(legacy.Case):
 private:int=0
def position(c):return legacy.position(c)
def result(c):return legacy.result(c)
def home(c):return STACK+c.phase if c.child_home is None else c.child_home
def fixture(c):
 m=legacy.fixture(c)
 for base in(OTHER,ALT_RESULT):m.update({base+i:(i*19+0x69)&255 for i in range(0x340)})
 put(m,ACTOR+0x1D4,0x50000000);put(m,OTHER+0x1D4,0x60000000);return m
def resolved_values(c,index):return tuple(legacy.VALUES[(c.pattern+i+(0 if index==33 else 3))%12]for i in range(3))
def resolver_effect(m,c,p,index):
 for i,v in enumerate(resolved_values(c,index)):put(m,p+4*i,v)
 if c.private&1:put(m,home(c)+4,OTHER);put(m,home(c)+8,ALT_RESULT)
 if c.private&4:put(m,home(c)+12,0xABCD00FF)
def initialize_effect(m,c,d,p):
 legacy.initializer_effect(m,c,d,p)
 if c.private&2:put(m,home(c)+8,ALT_RESULT)
def public(m):return legacy.public(m)
def visible(m,c):
 out=public(m)
 for p,n in((position(c),12),(result(c),36)):
  if p:out.update({p+i:m[p+i]for i in range(n)})
 return out
def reference(initial,c,s=SYMS):
 m=dict(initial);p=position(c);calls=[];packets=[];mode=c.fourth&255
 if mode not in(1,2):return m,calls,packets,0
 index=33 if mode==1 else 29;matrix=read(m,ACTOR+0x1D4);calls.append((s['func_15142314'],(matrix,index,p)));resolver_effect(m,c,p,index)
 d=read(m,home(c)+8)if c.private&1 else result(c)
 if not d:return m,calls,packets,1
 start=home(c)-12;put(m,start,read(m,p));put(m,start+4,bits(floating(read(m,p+4))+10.0));put(m,start+8,read(m,p+8))
 actor=read(m,home(c)+4)if c.private&1 else ACTOR;calls.append((s['func_1504715C'],(d,actor)));initialize_effect(m,c,d,p)
 d=read(m,home(c)+8)if c.private&3 else d;lower=bits(floating(read(m,p+4))-50.0);calls.append((s['func_15046C80'],(start,0,lower,d)));packets.append(tuple(read(m,start+4*i)for i in range(3)));legacy.query_effect(m,c,d,p)
 return m,calls,packets,c.returned&0xFFFFFFFF
class Oracle(legacy.HeightOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None,arguments=None):
  self.syms=s;super().__init__(words,memory,c,entry=entry,initialize=s['func_1504715C'],query=s['func_15046C80'],connected=connected,arguments=(position(c),ACTOR,result(c),c.fourth)if arguments is None else arguments)
 def record_call(self,t):
  if t in(self.syms['func_15142314'],ENTRY):
   n=3 if t==self.syms['func_15142314']else 4;a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
  else:super().record_call(t)
 def hook(self,t):
  c=self.case;a=self.calls[-1][1];p=position(c)
  if t==self.syms['func_15142314']:resolver_effect(self.memory,c,a[2],a[1]);value=0x12345678
  elif t==self.initialize:initialize_effect(self.memory,c,a[0],p);value=0x76543210
  else:assert t==self.query;legacy.query_effect(self.memory,c,a[3],p);value=c.returned&0xFFFFFFFF
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=value;self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
def cases():
 for pattern,query,layout,mutation,action,phase in itertools.product(range(12),(False,True),range(6),range(4),(1,2),(0,8)):
  yield Case(pattern=pattern,query=query,position_layout=layout,mode=mutation,returned=(0,1,0xFFFFFFFF,0x80000000)[mutation],fourth=action,phase=phase)
 for pattern,layout,result_layout,mutation,action in itertools.product((0,3,9),range(6),range(4),range(4),(1,2)):
  yield Case(pattern=pattern,position_layout=layout,result_layout=result_layout,mode=mutation,fourth=action)
 for action in range(256):yield Case(pattern=action%12,fourth=0xAB000000|action,query=bool(action&1),mode=action&3)
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.packets)
def verify(m,initial,c,s=SYMS):
 want,calls,packets,value=reference(initial,c,s);assert(visible(m.memory,c),m.calls,m.packets,m.r[2])==(visible(want,c),calls,packets,value),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.saved_f
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');programs=[linked(p,'semantic-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];count=0;visited=set()
 for c in cases():
  initial=fixture(c);ms=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);visited.update(ms[0].visits);count+=1
 assert set(range(ENTRY,ENTRY+224,4))-visited=={ENTRY+0x78};prefixes=delaycuts=0
 for c in(Case(fourth=0),Case(fourth=1,query=False),Case(fourth=1),Case(pattern=9,fourth=2,mode=3),Case(fourth=1,position_layout=1,result_layout=1),Case(fourth=2,phase=8)):
  initial=fixture(c);full=Oracle(programs[0],initial,c).run()
  for cut in range(full.root_accesses):
   ms=[]
   for words in programs:
    m=Oracle(words,initial,c);m.root_fault=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing prefix',cut))
    assert m.root_accesses==cut;ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2])and(ms[0].current_pc,ms[0].delay_of)==(ms[1].current_pc,ms[1].delay_of);prefixes+=1;delaycuts+=ms[0].delay_of is not None
 private=0
 for mu,action,phase in itertools.product(range(1,8),(1,2),(0,8)):
  c=Case(fourth=0xABCDEF00|action,private=mu,phase=phase,mode=3);initial=fixture(c);ms=[]
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);private+=1
 for action,p in itertools.product((0,1,2),(0,STACK-12,ACTOR+0x1D4)):
  c=Case(fourth=action,position_override=p,query=False if p==0 else True);initial=fixture(c);ms=[]
  if p==0 and action:continue
  for words in programs:m=Oracle(words,initial,c).run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);private+=1
 rebased=0
 for k,(entry,resolve,initialize,query)in enumerate(((0x15001000,0x10007FF0,0x10008000,0x1000FFF0),(0x1F008000,0x1F108000,0x1000FFF0,0x10008000),(0x1000FFF0,0x10008000,0x10007FF0,0x10007FF4))):
  s=dict(func_15142314=resolve,func_1504715C=initialize,func_15046C80=query);ps=[linked(p,'rebase'+str(k)+'-'+str(i),entry,s)for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2]
  for action,enabled,mutation,phase in itertools.product((0,1,2,255),(False,True),range(4),(0,8)):
   c=Case(fourth=action,query=enabled,mode=mutation,phase=phase,pattern=mutation*3);initial=fixture(c);ms=[]
   for words in ps:m=Oracle(words,initial,c,s,entry).run();verify(m,initial,c,s);ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebased+=1
 caller=caller_suite(programs);helpers=helper_suite(programs)
 return dict(private_only=True,installed=False,matching_credit=0,cases=count,executions=count*3,body_words=56,covered_reachable_words=55,unreachable_duplicate_word=hex(ENTRY+0x78),frame=56,guards=0,full_original_raw_padded_state_equal=True,independent_public_and_visible_output_reference=True,all_four_argument_ABI_and_three_helpers_checked=True,access_prefix_pairs=prefixes,delay_slot_cuts=delaycuts,rebase_layouts=3,rebase_cases=rebased,private_home_and_alias_cases=private,caller=caller,helpers=helpers,portable_C_fault_private_home_or_FCSR_claimed=False)
def caller_suite(programs):
 rom=(r/'conker/conker.us.bin').read_bytes();jal=struct.pack('>I',0x0C000000|((ENTRY>>2)&0x3FFFFFF));assert[at for at in range(0,len(rom),4)if rom[at:at+4]==jal]==[0x118570];assert not any(rom[at:at+4]==struct.pack('>I',ENTRY)for at in range(0,len(rom),4))
 parent=0x150EB090;end=0x150EB0D0;skip=0x150EB1A4;window=list(struct.unpack_from('>16I',rom,0x118540));assert window[12]==struct.unpack('>I',jal)[0];count=0;seen=set()
 for enabled,action,mutation,answer,phase in itertools.product((False,True),(0,1,2,255),range(4),(0,1,0xFFFFFFFF),(0,8)):
  h=STACK+phase;c=Case(fourth=action,position_override=h-12,result_override=h-48,child_home=h-88,mode=mutation,returned=answer,phase=phase);initial=fixture(c)
  if not enabled:put(initial,ACTOR+0x1D4,0)
  wanted,calls,packets,value=reference(initial,c)if enabled else(initial,[],[],None);ms=[]
  for words in programs:
   code=dict(zip(range(ENTRY,ENTRY+224,4),words));code[end]=code[skip]=0;m=Oracle(window,initial,c,entry=parent,connected=code,arguments=(ACTOR,0xAB000000|action,0x87654321));m.code=CallerCode(m.code,m);m.code.ends=(end,skip)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing original caller boundary')
   expected=([(ENTRY,(h-12,ACTOR,h-48,action))]+calls)if enabled else[]
   assert(visible(m.memory,c),m.calls,m.packets)==(visible(wanted,c),expected,packets),(enabled,c)
   assert m.reached_boundary==(end if enabled and value else skip)
   if enabled:assert m.r[2]==value
   seen.update(m.visits);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 assert set(range(parent,end,4))<=seen
 return dict(entry=hex(parent),ROM='0x118540',words=16,cases=count,disabled_and_enabled_routes=True,return_boolean_consumed=True,position_and_result_are_parent_stack_objects=True,complete_parent_claimed=False)
class CallerCode(WindowCode):
 def __getitem__(self,pc):
  if pc in self.ends:self.owner.reached_boundary=pc;raise WindowBoundary
  return super().__getitem__(pc)
class Helpers(Oracle):
 def __init__(self,words,memory,c,index,answer,status,mutation,connected):
  super().__init__(words,memory,c,connected=connected);self.index,self.answer,self.status,self.mutation=index,answer,status,mutation
 def record_call(self,t):
  if t in(legacy.CHECK,legacy.CLASSIFY,legacy.FALLBACK):
   a=tuple(self.arguments({legacy.CHECK:1,legacy.CLASSIFY:3,legacy.FALLBACK:4}[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  else:super().record_call(t)
 def hook(self,t):
  if t==RESOLVE:return super().hook(t)
  assert t not in(INITIALIZE,QUERY);d=result(self.case)
  if t==legacy.CHECK:
   assert self.calls[-1][1]==(self.index-1,)
   if self.mutation:self.memory[d+28]=0xA0;put(self.memory,ACTOR+0x1A0,0,2);put(self.memory,legacy.ENTITIES,0)
   value=self.answer
  elif t==legacy.CLASSIFY:self.memory[d+28]^=0x10;value=self.status
  else:assert t==legacy.FALLBACK;self.memory[d+28]^=0x20;value=self.case.returned
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=value&0xFFFFFFFF;self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def helper_reference(initial,c,flag,index,answer,status,mutation):
 m=dict(initial);p,d=position(c),result(c);start=home(c)-12;selected=33 if(c.fourth&255)==1 else 29;calls=[(RESOLVE,(read(m,ACTOR+0x1D4),selected,p))];resolver_effect(m,c,p,selected);ray=(read(m,p),bits(floating(read(m,p+4))+10.0),read(m,p+8))
 for i,v in enumerate(ray):put(m,start+4*i,v)
 calls.append((INITIALIZE,(d,ACTOR)));put(m,d,read(m,ACTOR+0x180))
 if flag:
  for i,v in enumerate((988,19,1034,-1012,19,34,988,19,-966)):put(m,d+4+2*i,v&65535,2)
 else:
  for i in range(18):m[d+4+i]=m[ACTOR+0x18C+i]
 put(m,d+24,read(m,ACTOR+0x184));m[d+28]=6;m[d+29]=2 if index else 1;put(m,d+32,0x38000+(index-1)*160 if index else 0)
 if index:
  calls.append((legacy.CHECK,(index-1,)))
  if mutation:m[d+28]=0xA0;put(m,ACTOR+0x1A0,0,2);put(m,legacy.ENTITIES,0)
 m[d+28]|=int(not index or bool(answer));lower=bits(floating(read(m,p+4))-50.0);calls.extend(((QUERY,(start,0,lower,d)),(legacy.CLASSIFY,(start,lower,d))));m[d+28]^=0x10
 if status==0:calls.append((legacy.FALLBACK,(start,0,lower,d)));m[d+28]^=0x20;value=c.returned&0xFFFFFFFF
 else:value=0 if status==1 else 1
 return m,calls,[ray],value
def helper_suite(programs):
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(r/'conker/build/conker.us.elf').read_bytes();from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
 descriptions=((INITIALIZE,0x7460C,89),(QUERY,0x74130,32));connected={};fixed=[];seen={entry:set()for entry,_,_ in descriptions}
 for entry,at,n in descriptions:
  raw=rom[at:at+n*4];connected.update(zip(range(entry,entry+n*4,4),struct.unpack('>%dI'%n,raw)));p=elf_slot_offset(elf,entry,n*4);fixed.append(elf[p:p+n*4]==raw)
 count=0
 for flag,index,answer,status,returned,mutation,phase,action in itertools.product((0,0x200000),(0,1,7),(0,1,0xFFFFFFFF),(0,1,2),(0,0xFFFFFFFF),(False,True),(0,8),(1,2)):
  c=Case(fourth=action,returned=returned,phase=phase);initial=fixture(c)
  for at,v in((0x14,bits(-12.5)),(0x18,bits(88.0)),(0x1C,bits(34.5)),(0x180,bits(19.75)),(0xF8,flag),(0x184,0x12345678)):put(initial,ACTOR+at,v)
  put(initial,ACTOR+0x1A0,index,2);put(initial,legacy.ENTITIES,0x38000);want,calls,packets,value=helper_reference(initial,c,flag,index,answer,status,mutation);ms=[]
  for words in programs:
   m=Helpers(words,initial,c,index,answer,status,mutation,connected).run();assert(visible(m.memory,c),m.calls,m.packets,m.r[2])==(visible(want,c),calls,packets,value),(flag,index,answer,status,returned,mutation,phase,action)
   for entry,_,n in descriptions:seen[entry].update(set(range(entry,entry+n*4,4))&m.visits)
   ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 return dict(original_helpers_executed=True,literal_words=121,cases=count,coverage=[len(seen[e])for e,_,_ in descriptions],current_ELF_exact=fixed,resolver_entity_check_and_lower_queries_bounded=True,query_status_domain=[0,1,2])
def native_harness(selected):
 head,body=selected.split('/* Resolve',1);body='/* Resolve'+body
 mutants=dict(gate=body.replace('mode != 1 && mode != 2','mode != 1 && mode != 3'),point1=body.replace('index = 0x21','index = 0x20'),point2=body.replace('index = 0x1D','index = 0x1C'),matrix=body.replace('actor + 0x1D4','actor + 0x1D0'),null_result=body.replace('return 1;','return 0;'),upper=body.replace('position[1] + 10.0f','position[1] + 9.0f'),lower=body.replace('position[1] - 50.0f','position[1] - 49.0f'),skip_initializer=body.replace('    func_1504715C(result, (HeightActor71820 *)actor);\n',''),selector=body.replace('func_15046C80(start, 0,','func_15046C80(start, 1,'),return_value=body.replace('return func_15046C80(start, 0, position[1] - 50.0f, result);','func_15046C80(start, 0, position[1] - 50.0f, result);\n    return 1;'),stale_height=body.replace('    f32 start[3];','    f32 start[3];\n    f32 lower;').replace('    func_1504715C(result, (HeightActor71820 *)actor);','    lower = position[1] - 50.0f;\n    func_1504715C(result, (HeightActor71820 *)actor);').replace('return func_15046C80(start, 0, position[1] - 50.0f, result);','return func_15046C80(start, 0, lower, result);'))
 assert all(v!=body for v in mutants.values())
 text=head+r'''
 typedef char Pointer32[sizeof(void*)==4?1:-1];
 static u8 *actor,*out,*result;static u8 expected[0x800];
 static u32 pattern,queryEnabled,layout,resultLayout,mutation,returned,action,ncalls,error,cases;
 static u32 expectedRay[3],expectedLower,expectedMatrix;
 static const u32 values[]={0,0x80000000u,0x3F800000u,0xBF800000u,0x42C80000u,0xC2C80000u,1,0x4B800000u};
 static const s32 returns[]={0,1,-1,(-2147483647-1)};
 static const u8 actions[]={0,1,2,3,255};
 static f32 fp(u32 v){union{u32 w;f32 f;}x;x.w=v;return x.f;}
 static u32 bits(f32 v){union{u32 w;f32 f;}x;x.f=v;return x.w;}
 static void putword(u8*p,u32 v){u8*q=(u8*)&v;u32 i;for(i=0;i<4;i++)p[i]=q[i];}
 static u32 word(const u8*p){u32 v;u8*q=(u8*)&v;u32 i;for(i=0;i<4;i++)q[i]=p[i];return v;}
 __attribute__((noinline,noclone)) void func_15142314(u8*m,s32 index,f32*p){u32 i,shift=action==1?0:3;
  if((u32)m!=expectedMatrix||index!=(action==1?33:29)||(u8*)p!=out||ncalls++!=0)error=1;
  for(i=0;i<3;i++)putword((u8*)p+4*i,values[(pattern+i+shift)%8]);}
 __attribute__((noinline,noclone)) void func_1504715C(HeightResult71820*d,HeightActor71820*a){u32 i;
  if((u8*)d!=result||(u8*)a!=actor||ncalls++!=1)error=1;
  for(i=0;i<36;i++)((u8*)d)[i]=(u8)(i*7+mutation);putword((u8*)d,0x43960000u);
  if(mutation&1)putword(out+4,0x442F0000u);}
 __attribute__((noinline,noclone)) s32 func_15046C80(f32*p,u16 selector,f32 lower,HeightResult71820*d){u32 i;
  if(selector||(u8*)d!=result||bits(lower)!=expectedLower||ncalls++!=2)error=1;
  for(i=0;i<3;i++)if(word((u8*)p+4*i)!=expectedRay[i])error=1;
  ((u8*)d)[28]=0xD7;if(mutation&2)putword(out,0xC3480000u);return returns[returned];}
 '''
 text+='\n'.join(v.replace(F,'test_'+name)for name,v in dict(selected=body,**mutants).items())
 text+=r'''
 typedef s32(*Fn)(f32*,u8*,HeightResult71820*,u8);
 static int one(Fn fn){u32 i,p,d,shift,answer,enabled=action==1||action==2;
  for(i=0;i<0x800;i++)actor[i]=(u8)(i*13+pattern);
  putword(actor+0x1D4,0x50000000u);putword(actor+0x1D0,0x60000000u);
  out=layout==0?actor+0x380:layout==1?actor+0x14:layout==2?actor+0x18:actor+0x1D4;
  result=!queryEnabled?0:resultLayout==0?actor+0x400:resultLayout==1?out:actor+0x14;
  for(i=0;i<0x800;i++)expected[i]=actor[i];p=(u32)(out-actor);d=result?(u32)(result-actor):0;expectedMatrix=word(expected+0x1D4);
  if(enabled){shift=action==1?0:3;for(i=0;i<3;i++)putword(expected+p+4*i,values[(pattern+i+shift)%8]);
   if(queryEnabled){expectedRay[0]=word(expected+p);expectedRay[1]=bits(fp(word(expected+p+4))+10.0f);expectedRay[2]=word(expected+p+8);
    for(i=0;i<36;i++)expected[d+i]=(u8)(i*7+mutation);putword(expected+d,0x43960000u);if(mutation&1)putword(expected+p+4,0x442F0000u);
    expectedLower=bits(fp(word(expected+p+4))-50.0f);expected[d+28]=0xD7;if(mutation&2)putword(expected+p,0xC3480000u);
   }}
  ncalls=error=0;answer=(u32)fn((f32*)out,actor,(HeightResult71820*)result,(u8)action);cases++;
  if(answer!=(enabled?(queryEnabled?(u32)returns[returned]:1u):0u)||error||ncalls!=(enabled?(queryEnabled?3u:1u):0u))return 1;
  for(i=0;i<0x800;i++)if(actor[i]!=expected[i])return 2;
  return 0;}
 static int corpus(Fn fn){u32 a;int code;
  for(pattern=0;pattern<8;pattern++)for(queryEnabled=0;queryEnabled<2;queryEnabled++)for(layout=0;layout<4;layout++)for(resultLayout=0;resultLayout<3;resultLayout++)for(mutation=0;mutation<4;mutation++)for(a=0;a<5;a++)for(returned=0;returned<4;returned++){
   action=actions[a];code=one(fn);if(code)return code;
  }return 0;}
 static int run(void){u32 address,requested,i;Fn bad[]={'''+','.join('test_'+n for n in mutants)+r'''};
  __asm__ volatile("int $0x80":"=a"(address):"a"(45),"b"(0):"memory");requested=(address+15u)&~15u;
  __asm__ volatile("int $0x80":"=a"(address):"a"(45),"b"(requested+0x800):"memory");if(address<requested+0x800)return 90;actor=(u8*)requested;
  if(corpus(test_selected))return 91;if(cases!=15360)return 92;
  for(i=0;i<sizeof(bad)/sizeof(bad[0]);i++)if(!corpus(bad[i]))return 93;
  return 0;}
 '''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text,len(mutants)
def run_native(selected):
 text,controls=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,cases=15360,negative_controls=controls,UBSan=True)
 return dict(profiles=reports,cases=15360,negative_controls=controls,signature='s32(f32*,u8*,HeightResult71820*,u8)',position_layouts=4,result_layouts=3,finite_float_payloads_and_aliases_checked=True,initializer_mutation_and_late_lower_read_checked=True,untyped_backing=True,private_home_fault_or_FCSR_claimed=False)
