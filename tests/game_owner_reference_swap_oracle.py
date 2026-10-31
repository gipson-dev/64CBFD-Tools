"""Reference-command callback: short-circuit identity, swap order and live dispatch.

Provider mutations and extra table slots are bounded guest contracts. Native
tests use disjoint typed objects and the three real callback-table slots.
"""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,re,struct,subprocess
from tools.experiments import game_owner_reference_swap_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD
RECORD,COMMAND,REMOVE,TABLE,FINAL,ALT=0x240000,0x220000,0x1516972C,0x8008B358,0x150F1684,0x15000040
SYMS=dict(func_1516972C=REMOVE,D_8008B358=TABLE)
@dataclass(frozen=True)
class Case:
 mode:int=0
 match:int=0
 id_match:bool=False
 callback:int=1
 mutation:int=0
 phase:int=0
 record:int=RECORD
 command:int=COMMAND

def fixture(c=Case(),s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
 for base in(c.record,c.command):m.update({base+i:(i*13+0x59)&255 for i in range(-16,112)})
 for i in range(256):put(m,s['D_8008B358']+4*i,FINAL if i==1 else 0)
 put(m,c.command,0x12345678);put(m,c.command+4,0x76543210)
 m[c.command+8]=0x51;m[c.command+9]=0xA2
 if c.mode&255==0:m[c.command+4]=0x37 if c.id_match else 0x38
 first,second=read(m,c.command),read(m,c.command+4)
 put(m,c.record+24,first if c.match in(1,3)else second if c.match==2 else 0xAABBCCDD)
 if c.match==3:put(m,c.command+4,first)
 m[c.record+28]=0x37;m[c.record+29]=c.callback
 put(m,c.record+32,0);put(m,c.record+36,0)
 return m

def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+1024}
def view(m,c):return public(m),bytes(m[c.record+i]for i in range(40)),bytes(m[c.command+i]for i in range(12))
def observation(m,c):return(read(m,c.record+24),m[c.record+28],m[c.record+29],bytes(m[c.command+i]for i in range(10)))
def release_effect(m,c,s):
 put(m,c.record+36,(read(m,c.record+36)+1)&0xFFFFFFFF)
 if c.mutation&1:put(m,c.record+24,0xF00D1234);m[c.record+28]=0xE1
 if c.mutation&2:m[c.record+29]=0 if m[c.record+29]else 1
 if c.mutation&4:put(m,c.command,0xFEDCBA98)
 if c.mutation&8:put(m,s['D_8008B358']+4*m[c.record+29],ALT)
def callback_effect(m,c):put(m,c.record+32,(read(m,c.record+32)+1)&0xFFFFFFFF)

def reference(initial,c,s=SYMS,connected_final=False):
 m=dict(initial);calls=[];observed=[];mode=c.mode&255
 def call(t,args):calls.append((t,args));observed.append(observation(m,c))
 if mode==0:
  if read(m,c.command)==read(m,c.record+24)or m[c.command+4]==m[c.record+28]:
   call(s['func_1516972C'],(c.record,));release_effect(m,c,s)
 elif mode==45:
  if read(m,c.record+24)==read(m,c.command):
   put(m,c.record+24,read(m,c.command+4));m[c.record+28]=m[c.command+9]
  elif read(m,c.record+24)==read(m,c.command+4):
   put(m,c.record+24,read(m,c.command));m[c.record+28]=m[c.command+8]
 target=read(m,s['D_8008B358']+4*m[c.record+29])
 if target:
  call(target,(c.record,c.command,mode))
  if connected_final and target==FINAL:
   if mode==67 and(read(m,c.command)==read(m,c.record+24)or m[c.command+4]==m[c.record+28]):
    call(s['func_1516972C'],(c.record,));release_effect(m,c,s)
  else:callback_effect(m,c)
 return m,calls,observed

class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=source.ENTRY,s=SYMS,connected_final=False):
  self.c,self.s,self.trace,self.observed=c,s,[],[]
  connected=None
  if connected_final:
   rom=(o/'before-conker_conker.us.bin').read_bytes();connected=dict(zip(range(FINAL,FINAL+88,4),struct.unpack_from('>22I',rom,0x11EB34)))
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.record,c.command,c.mode&0xFFFFFFFF),connected=connected)
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  assert t in(self.s['func_1516972C'],FINAL,ALT),hex(t)
  args=self.arguments(1 if t==self.s['func_1516972C']else 3)
  self.calls.append((t,args));self.events.append(('CALL',t,args));self.observed.append(observation(self.memory,self.c))
 def hook(self,t):
  if t==self.s['func_1516972C']:release_effect(self.memory,self.c,self.s)
  else:callback_effect(self.memory,self.c)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.r[2]=0xA5000010,0xA5000011,0xC0DEC0DE

def linked(obj,label,entry=source.ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[source.FUNCTION];asm,unknown=emit_function(text,f,rs,source.FUNCTION,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))

def guest_suite():
 cases=cuts=delaycuts=aliases=0;seen=set();raw_trace_cases=0
 for j,entry in enumerate((source.ENTRY,0x17007FFC,0x2500FFFC)):
  syms=SYMS if j==0 else dict(func_1516972C=entry+0x10000,D_8008B358=0x81007FFC+j*0x10000)
  images=[linked(o/n,'rebase-%d-%d'%(j,k),entry,syms)for k,n in enumerate(('original-func_15161F4C.o','qualified-padded.o','make-shadow/src/game_18D770.c.o','selected-final.o'))]
  assert images[0]==images[1]==images[2]and(len(images[0]),len(images[3]))==(58,57)
  for mode,match,id_match,index,mutation,phase in itertools.product((0,45,67,1,255,0xFFFFFF00,0x1234002D),range(4),(False,True),(0,1,2),(0,1,2,4,8,15),(0,8)):
   c=Case(mode,match,id_match,index,mutation,phase);m=fixture(c,syms);want,calls,observed=reference(m,c,syms)
   models=[Oracle(w,m,c,entry,syms).run()for w in(images[0],images[1],images[3])]
   for q in models:assert view(q.memory,c)==view(want,c)and q.calls==calls and q.observed==observed,(c,'semantic mismatch')
   assert complete(models[0])==complete(models[1])and models[0].trace==models[1].trace
   assert models[0].trace==models[2].trace,(c,'raw access ordering')
   seen.update(models[0].visits);cases+=1;raw_trace_cases+=1
  if j==0:
   for record,command,mode,mutation in itertools.product((RECORD,STACK+128),(COMMAND,RECORD,RECORD+16,RECORD+24,RECORD+28,STACK+256),(0,45,67),(0,15)):
    c=Case(mode=mode,match=1,id_match=True,record=record,command=command,mutation=mutation);m=fixture(c);want,calls,observed=reference(m,c)
    models=[Oracle(w,m,c).run()for w in(images[0],images[1],images[3])]
    for q in models:assert view(q.memory,c)==view(want,c)and q.calls==calls and q.observed==observed,(c,'alias')
    assert complete(models[0])==complete(models[1]);aliases+=1
   for c in(Case(mode=0,match=1,mutation=15),Case(mode=0,match=0,id_match=True),Case(mode=45,match=1),Case(mode=45,match=2),Case(mode=67,callback=0)):
    m=fixture(c);good=Oracle(images[0],m,c).run()
    for cut in range(good.root_accesses):
     pair=[]
     for words in images[:2]:
      q=Oracle(words,m,c);q.root_fault=cut
      try:q.run()
      except faults.AccessBoundary:pass
      else:raise AssertionError('unfired fault')
      assert q.root_accesses==cut;pair.append(q)
     assert complete(pair[0])==complete(pair[1])and pair[0].trace==pair[1].trace
     assert(pair[0].current_pc,pair[0].delay_of)==(pair[1].current_pc,pair[1].delay_of);cuts+=1;delaycuts+=pair[0].delay_of is not None
 missing=set(range(source.ENTRY,source.ENTRY+232,4))-seen
 assert missing=={0x15161FE8}
 # The duplicate second-pointer load has no internal incoming edge. Its
 # predecessor is the delay slot of an unconditional branch past it.
 original=struct.unpack_from('>58I',(o/'before-conker_conker.us.bin').read_bytes(),source.ROM)
 assert original[37]>>16==0x1000 and original[39]==0x8CAB0004
 targets={source.ENTRY+4*i+4+4*(((w&65535)^32768)-32768)for i,w in enumerate(original)if w>>26 in(1,4,5,6,7,20,21,22,23)}
 assert 0x15161FE8 not in targets
 return dict(cases=cases,executions=cases*3,raw_memory_trace_cases=raw_trace_cases,guest_alias_cases=aliases,rebases=3,visited_words=57,retained_unreachable_duplicate_load='0x15161FE8',fault_cuts=cuts,delay_fault_cuts=delaycuts,normalized_complete_state_equal=True,raw_public_state_calls_access_order_equal=True,raw_fault_context_equated=False,provider_mutations=True,portable_overlap_claim=False)

def connected_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();elf=(o/'before-conker_build_conker.us.elf').read_bytes()
 original=list(struct.unpack_from('>22I',rom,0x11EB34));assert original==list(struct.unpack_from('>22I',elf,source.elf_slot_offset(elf,FINAL,88)))
 images=[linked(o/n,'connected-%d'%i)for i,n in enumerate(('original-func_15161F4C.o','qualified-padded.o','selected-final.o'))];count=0;seen=set()
 for mode,match,id_match,index,mutation,phase in itertools.product((0,45,67),range(4),(False,True),(0,1,2),(0,15),(0,8)):
  c=Case(mode,match,id_match,index,mutation,phase);initial=fixture(c);want,calls,observed=reference(initial,c,connected_final=True)
  models=[Oracle(w,initial,c,connected_final=True).run()for w in images]
  for q in models:assert view(q.memory,c)==view(want,c)and q.calls==calls and q.observed==observed,(c,'connected callback')
  assert complete(models[0])==complete(models[1]);seen.update(models[0].visits);count+=1
 assert len(seen&set(range(FINAL,FINAL+88,4)))==22
 return dict(cases=count,executions=count*3,retained_final_callback_words=22,all_final_words_visited=True,mode67_identity_OR_and_removal_connected=True,release_provider_bounded=True)

class CallerOracle(TimingOracle):
 def __init__(self,words,memory,mode,returned,phase=0):
  self.mode,self.returned=mode,returned
  rom=(o/'before-conker_conker.us.bin').read_bytes();child=dict(zip(range(0x151604A0,0x15160600,4),struct.unpack_from('>88I',rom,0x18D950)))
  super().__init__(words,memory,phase=phase,entry=0x1516944C,arguments=(53,COMMAND,mode&0xFFFFFFFF),connected=child)
 def execute(self,w):
  if w>>26==32:
   offset=((w&65535)^32768)-32768;value=self.get((self.r[(w>>21)&31]+offset)&0xFFFFFFFF,1)
   self.r[(w>>16)&31]=((value^128)-128)&0xFFFFFFFF
  else:super().execute(w)
 def record_call(self,t):
  assert t in (0x1516968C,0x151604A0,source.ENTRY),hex(t)
  args=self.arguments(3);self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=self.returned

def caller_suite():
 rom=(o/'before-conker_conker.us.bin').read_bytes();elf=(o/'before-conker_build_conker.us.elf').read_bytes();ws=struct.unpack('>%dI'%(len(rom)//4),rom)
 assert [i*4 for i,w in enumerate(ws)if w==source.ENTRY]==[0x22FC64]
 assert not any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws)
 assert struct.unpack_from('>I',rom,0x22FC10+21*4)[0]==source.ENTRY
 assert struct.unpack_from('>I',rom,0x230A48)[0]==0x151604A0
 assert list(struct.unpack_from('>88I',elf,source.elf_slot_offset(elf,0x151604A0,352)))==list(struct.unpack_from('>88I',rom,0x18D950))
 asm=(o/'before-conker_asm_nonmatchings_game_1944C0_func_1516944C.s').read_text();n=len(re.findall(r'/\* [0-9A-F]+ [0-9A-F]+ [0-9A-F]{8} \*/',asm));words=list(struct.unpack_from('>%dI'%n,rom,0x1968FC));count=0;sites=set()
 for mode,ret,phase,nodes in itertools.product((0,45,67,1,255,0xFFFFFF00,0x1234002D),(0,1,0x80000000,0xFFFFFFFF),(0,8),(0,1,2)):
  memory=fixture(Case());memory.update({0x800DD190+i:0 for i in range(128)})
  memory[RECORD+0x12]=21;put(memory,RECORD+8,RECORD+80 if nodes==2 else 0);memory[RECORD+80+0x12]=21;put(memory,RECORD+80+8,0)
  put(memory,0x8008B4A8+53*52+28,0x151604A0);put(memory,0x8008B150+21*4,source.ENTRY)
  for row in range(2):put(memory,0x800DCE50+row*0x1A0+53*4,RECORD if nodes else 0)
  memory[0x800DD190]=0
  q=CallerOracle(words,memory,mode,ret,phase).run();roots=[args for t,args in q.calls if t==source.ENTRY]
  expected=[(RECORD,COMMAND,mode&255)]+([(RECORD+80,COMMAND,mode&255)]if nodes==2 else[])
  assert roots==(expected*2 if nodes else[]),(mode,nodes,roots)
  assert q.memory[0x800DD190]==0
  sites.update(pc for pc in q.visits if pc in(0x15169520,0x151605E4));count+=1
 assert sites=={0x15169520,0x151605E4}
 return dict(cases=count,original_outer_dispatcher_words=n,original_class_dispatcher_words=88,table_slot=21,record_class=53,one_literal_pointer_ROM='0x22FC64',callback_sites=[hex(x)for x in sorted(sites)],three_arguments_forwarded=True,callback_return_discarded=True,outer_production_placeholder_unchanged=True,no_direct_JAL=True)

def controls():
 b=source.SELECTED
 changes={'wrong_OR':(' || ',' && '),'wrong_remove_mode':('if (mode == 0) {','if (mode == 1) {'),'wrong_swap_mode':('mode == 0x2D','mode == 0x2C'),'first_id':('payload->unique_id = command->swap.second_id','payload->unique_id = command->swap.first_id'),'second_id':('payload->unique_id = command->swap.first_id','payload->unique_id = command->swap.second_id'),'wrong_first_pointer':('payload->reference = command->swap.second','payload->reference = command->swap.first'),'wrong_second_pointer':('payload->reference = command->swap.first','payload->reference = command->swap.second'),'missing_remove':('func_1516972C((void *)record);','(void)record;'),'wrong_index':('payload->callback','payload->unique_id'),'wrong_command_arg':('(record, command, mode)','(record, NULL, mode)'),'wrong_mode_arg':('(record, command, mode)','(record, command, 0)')}
 out={n:b.replace(a,z)for n,(a,z)in changes.items()};assert all(v!=b for v in out.values());return out

def native_harness():
 t=source.HEADERS+r'''
typedef char ABI[(sizeof(void*)==4&&sizeof(ReferencePayload)==8&&sizeof(ReferenceRecord)==32&&sizeof(ReferenceCommand)==12&&__builtin_offsetof(ReferenceRecord,payload)==24)?1:-1];
typedef struct {ReferenceRecord record;u32 calls,removals;u32 fence;} Storage;
static Storage actual,expected;static ReferenceCommand event;
static u32 rawmode,match,idmatch,index,mutation,phase,error;static void *wanted;static u8 wantedID;
static void bytes(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static void release(Storage*p){p->removals++;if(mutation&1){p->record.payload.reference=(void*)0xF00D1234u;p->record.payload.unique_id=0xE1;}if(mutation&2)p->record.payload.callback=p->record.payload.callback?0:1;}
static void callback(ReferenceRecord*p,const ReferenceCommand*c,u8 mode){
 if(p!=&actual.record||c!=&event||mode!=(u8)rawmode)error=1;actual.calls++;phase++;
}
void (*D_8008B358[256])(ReferenceRecord *,const ReferenceCommand *,u8);
void func_1516972C(void*p){if(p!=&actual.record||phase++!=0)error=1;release(&actual);if(mutation&4)event.single.reference=(void*)0xFEDCBA98u;if(mutation&8)D_8008B358[actual.record.payload.callback]=callback;}
'''
 for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace(source.FUNCTION,name)+'\n'
 t+=r'''
typedef void(*Callback)(ReferenceRecord*,const ReferenceCommand*,u8);
static int check(Callback fn){u32 i,k;u8 mode;
 for(rawmode=0;rawmode<256;rawmode++)for(match=0;match<4;match++)for(idmatch=0;idmatch<2;idmatch++)for(index=0;index<3;index++)for(mutation=0;mutation<16;mutation++){
  for(i=0;i<sizeof(actual);i++)((u8*)&actual)[i]=0xA5;actual.calls=actual.removals=0;actual.fence=0x12345678u;
  mode=(u8)rawmode;event.swap.first=(void*)0x12345678u;event.swap.second=(void*)0x76543210u;event.swap.first_id=0x51;event.swap.second_id=0xA2;
  if(!mode){event.single.reference=(void*)0x12345678u;event.single.unique_id=idmatch?0x37:0x38;}
  actual.record.payload.reference=match==1||match==3?event.single.reference:match==2?event.swap.second:(void*)0xAABBCCDDu;
  if(match==3&&mode)event.swap.second=event.swap.first;
  actual.record.payload.unique_id=0x37;actual.record.payload.callback=(u8)index;
  bytes(&expected,&actual,sizeof(actual));
  for(i=0;i<256;i++)D_8008B358[i]=i==1?callback:NULL;
  if(!mode){
   if(actual.record.payload.reference==event.single.reference||actual.record.payload.unique_id==event.single.unique_id)release(&expected);
  }else if(mode==45){
   wanted=actual.record.payload.reference;wantedID=actual.record.payload.unique_id;
   if(wanted==event.swap.first){wanted=event.swap.second;wantedID=event.swap.second_id;}
   else if(wanted==event.swap.second){wanted=event.swap.first;wantedID=event.swap.first_id;}
   expected.record.payload.reference=wanted;expected.record.payload.unique_id=wantedID;
  }
  k=expected.record.payload.callback;
  if(k==1||(expected.removals&&(mutation&8)))expected.calls++;
  error=phase=0;fn(&actual.record,&event,mode);
  if(error||phase!=expected.calls+expected.removals)return 1;
  for(i=0;i<sizeof(actual);i++)if(((u8*)&actual)[i]!=((u8*)&expected)[i])return 1;
 }return 0;
}
static int run(void){if(check(selected))return 10;
'''
 for i,name in enumerate(controls()):t+='if(!check(%s))return %d;\n'%(name,20+i)
 return t+'return 0;}\n'+START

def native_suite():
 unit=o/'native-reference.c';unit.write_text(native_harness())
 for opt in('O0','O2','O3'):
  exe=o/('native-reference-'+opt);q=subprocess.run([*native_command('-'+opt,True),'-mstackrealign','-fno-builtin',str(unit),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0,q.stderr
  q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert q.returncode==0,(opt,q.returncode,q.stderr)
 return dict(profiles=['O0','O2','O3'],positive_cases_each=98304,effective_controls=11,UBSan_trapping=True,all_256_modes=True,typed_disjoint_objects=True,whole_storage_fences=True,portable_alias_claim=False,live_selector_and_table_mutations=True)
