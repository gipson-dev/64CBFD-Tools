"""Texture segment pairs: captured metadata, guest cache paths and cursor callers."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.experiments import game_texture_segment_pair_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD;F=source.FUNCTION;ENTRY=source.ENTRY
TABLE,LOADER,OUTPUT,IDS,ACTOR=0x80090B60,0x1510D0EC,0x20000,0x80000,0x60000
SYMS=dict(D_80090B60=TABLE,func_1510D0EC=LOADER)
u32=lambda v:v&0xFFFFFFFF
signed=lambda v:(v^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
 index:int=0xABCDFFFF
 segment:int=0xDEAD00FF
 priority:int=0xFEDCBA98
 segments:int=2
 layout:int=1
 address:int=0xFFFFFFF0
 extent:int=0x80000000
 resource:int=0xAABBCCDD
 effect:int=1
 phase:int=0
 alias:int=0
 seed:int=0
 cursor:int=OUTPUT
def record(c,s=SYMS):return s['D_80090B60']+12*(c.index&65535)
def destination(c,s=SYMS):return (c.cursor,record(c,s),IDS)[c.alias]
def arguments(c,s=SYMS):return tuple(map(u32,(destination(c,s),c.index,c.segment,c.priority)))
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-2048,4096)}
 for base,n in ((OUTPUT-32,8192),(IDS-32,256),(ACTOR-32,4096)):
  m.update({base+i:(i*29+c.seed+0x5A)&255 for i in range(n)})
 for i in range(-32,64):m[record(c,s)+i]=(i*13+c.seed)&255
 put(m,record(c,s),IDS);put(m,IDS,c.resource);put(m,record(c,s)+10,c.segments,1);put(m,record(c,s)+11,c.layout,1)
 return m
def effects(m,c,s,home):
 if c.effect&1:
  put(m,record(c,s)+10,1 if c.segments==2 else 2,1);put(m,record(c,s)+11,c.layout^1,1);put(m,IDS,c.resource^0x55)
 if c.effect&2:put(m,home+8,0x13570000|((c.segment+1)&255))
def public(m):return{p:v for p,v in m.items()if not STACK-2048<=p<STACK+4096}
def reference(initial,c,s=SYMS,home=None):
 home=STACK+c.phase if home is None else home;m=dict(initial);p=record(c,s);resource=read(m,read(m,p));count=read(m,p+10,1);layout=read(m,p+11,1)
 calls=[(s['func_1510D0EC'],(resource,home-16,u32(c.priority),0))];effects(m,c,s,home);put(m,home-16,c.extent)
 segment=(c.segment+1)&255 if c.effect&2 else c.segment&255;cursor=destination(c,s)
 put(m,cursor+4,c.address);put(m,cursor,0xDB060000|segment*4);cursor+=8
 if count==2:
  put(m,cursor,0xDB060000|((segment+1)*4&65535));put(m,cursor+4,u32(c.address+c.extent-(512 if layout==1 else 32)));cursor+=8
 return m,calls,cursor
def linked(obj,label,entry=ENTRY,s=SYMS,function=F):
 text,fs,rs=parse_object(obj);f=fs[function];asm,unknown=emit_function(text,f,rs,function,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',function,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None,args=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=arguments(c,s)if args is None else args)
 def record_call(self,t):
  assert t in(self.syms['func_1510D0EC'],ENTRY),hex(t);a=tuple(map(u32,self.arguments(4)));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert t==self.syms['func_1510D0EC'];c=self.case;a=self.calls[-1][1];effects(self.memory,c,self.syms,self.target_home);self.put(a[1],c.extent,4)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(c.address)
def state(m):return(complete(m),m.trace,m.current_pc,m.delay_of,m.all_accesses)
def check(m,initial,c,s=SYMS):
 want,calls,result=reference(initial,c,s);assert(public(m.memory),m.calls,m.r[2])==(public(want),calls,result),c
def cases():
 for i in range(256):yield Case(index=0xABCD0000|i,segment=0xDEAD0000|i,segments=(0,1,2,3,255)[i%5],layout=i,extent=(0,1,32,512,0x7FFFFFFF,0x80000000,0xFFFFFFFF)[i%7],address=(0,0x80000000,0xFFFFFFF0)[i%3],seed=i)
 for index,count,layout,effect,phase in itertools.product((0,1,0x7FFF,0x8000,0xFFFF),(0,1,2,3,255),(0,1,2,255),(0,1,3),(0,8)):
  yield Case(index=0x12340000|index,segments=count,layout=layout,effect=effect,phase=phase)
 for alias,count,effect in itertools.product((1,2),(1,2),(0,3)):yield Case(alias=alias,segments=count,effect=effect)
def guest_suite():
 objects=('original-'+F+'.o','selected-final.o','qualified-padded.o');ws=[linked(o/n,'guest-'+str(i))for i,n in enumerate(objects)];assert ws[0]==ws[1]==ws[2];visited=set();corpus=list(cases())
 for c in corpus:
  initial=fixture(c);ms=[]
  for w in ws:m=Oracle(w,initial,c).run();check(m,initial,c);ms.append(m);visited.update(m.visits)
  assert state(ms[0])==state(ms[1])==state(ms[2]),c
 assert set(range(ENTRY,ENTRY+236,4))<=visited;cuts=delays=0
 for c in (Case(segments=1),Case(segments=2,layout=0),Case(segments=2,layout=1,effect=3,alias=1,phase=8)):
  initial=fixture(c);normal=Oracle(ws[0],initial,c).run()
  for cut in range(normal.all_accesses):
   ms=[]
   for w in ws:
    m=Oracle(w,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Access cut did not fire')
    ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);cuts+=1;delays+=ms[0].delay_of is not None
 rebase=0
 for entry,table,loader in ((0x17007FFC,0x80217FFC,0x1710FFFC),(0x2500FFFC,0x80318000,0x25100000)):
  s=dict(D_80090B60=table,func_1510D0EC=loader);programs=[linked(o/n,'rebase-'+str(entry)+'-'+str(i),entry,s)for i,n in enumerate(objects)];assert programs[0]==programs[1]==programs[2]
  for c in (Case(),Case(segments=1),Case(layout=0,effect=3),Case(index=0,alias=1)):
   initial=fixture(c,s);ms=[Oracle(w,initial,c,entry,s).run()for w in programs]
   for m in ms:check(m,initial,c,s)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebase+=1
 return dict(cases=len(corpus),executions=len(corpus)*3,body_words=59,guards=0,bindings=3,all_target_words_exercised=True,access_cuts=cuts,delay_cuts=delays,rebase_cases=rebase,captured_metadata_and_resource=True,guest_incoming_home_mutation=True,guest_output_aliases=True,complete_RAM_registers_trace_and_fault_context=True,portable_guest_alias_or_hardware_claimed=False)
def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();ws=[linked(o/n,'caller-'+str(i))for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];count=0
 for parent,offset,member in ((0x15133E84,0x161334,0x170),(0x15133EB8,0x161368,0x174)):
  words=list(struct.unpack_from('>13I',rom,offset))
  for index,segment,segments,layout,phase in itertools.product((0,0xFFFF),(0,255),(1,2),(0,1),(0,8)):
   c=Case(index=index,segment=segment,segments=segments,layout=layout,phase=phase,effect=1);initial=fixture(c);put(initial,ACTOR+member,index,2);put(initial,ACTOR+member+2,segment,1);put(initial,ACTOR+member+4,c.priority);ms=[]
   for w in ws:
    code=dict(zip(range(ENTRY,ENTRY+236,4),w));m=Oracle(words,initial,c,entry=parent,connected=code,args=(OUTPUT,ACTOR,0xA5));m.target_home=STACK+phase-24;m.run();want,calls,result=reference(initial,c,home=m.target_home)
    assert(public(m.memory),m.calls,m.r[2])==(public(want),[(ENTRY,(OUTPUT,index,segment,c.priority)),*calls],result);ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 # Complete original list caller, including its eight-bit index and cursor chain.
 loop=struct.unpack_from('>35I',rom,0x161488);loop_cases=0
 for n,segments,layout,phase in itertools.product((0,1,2,7,255),(1,2),(0,1),(0,8)):
  c=Case(index=0,segment=7,segments=segments,layout=layout,effect=0,phase=phase);initial=fixture(c);put(initial,ACTOR+0x170,n,1)
  for i in range(n):put(initial,ACTOR+0x174+8*i,0,2);put(initial,ACTOR+0x176+8*i,7,1);put(initial,ACTOR+0x178+8*i,c.priority)
  ms=[];want=dict(initial);cursor=OUTPUT;calls=[]
  for i in range(n):
   a=(cursor,0,7,c.priority);cc=replace(c,alias=0);local=STACK+phase-40
   # Each original invocation receives the previous cursor as a0.
   resource=read(want,IDS);calls.extend([(ENTRY,a),(LOADER,(resource,local-16,c.priority,0))]);put(want,cursor+4,c.address);put(want,cursor,0xDB06001C);cursor+=8
   if segments==2:put(want,cursor,0xDB060020);put(want,cursor+4,u32(c.address+c.extent-(512 if layout==1 else 32)));cursor+=8
  for w in ws:
   m=Oracle(loop,initial,c,entry=0x15133FD8,connected=dict(zip(range(ENTRY,ENTRY+236,4),w)),args=(OUTPUT,ACTOR,0xA5));m.target_home=STACK+phase-40;m.run();assert(public(m.memory),m.calls,m.r[2])==(public(want),calls,cursor),(n,segments,phase);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);loop_cases+=1
 # The remaining original parent contributes a two-call cursor chain window.
 class WindowExit(Exception):pass
 class WindowCode(faults.TrackedCode):
  def __getitem__(self,pc):
   if pc==0x151D7194:self.owner.current_pc=pc;raise WindowExit
   return super().__getitem__(pc)
 window=struct.unpack_from('>7I',rom,0x204628);window_cases=0
 for segments,layout,phase in itertools.product((0,1,2,3,255),(0,1,2,255),(0,8)):
  c=Case(index=195,segment=6,priority=3,segments=segments,layout=layout,effect=1,phase=phase);initial=fixture(c);want=dict(initial);calls=[];cursor=OUTPUT
  for segment in (6,7):
   cc=replace(c,segment=segment,cursor=cursor);a=(cursor,195,segment,3);want,subcalls,cursor=reference(want,cc);calls.extend([(ENTRY,a),*subcalls])
  ms=[]
  for w in ws:
   m=Oracle(window,initial,c,entry=0x151D7178,connected=dict(zip(range(ENTRY,ENTRY+236,4),w)),args=(OUTPUT,195,6,0xA5));m.code[0x151D7194]=0;m.code=WindowCode(m.code,m)
   try:m.run()
   except WindowExit:pass
   else:raise AssertionError('Original two-call window exit did not fire')
   assert(public(m.memory),m.calls,m.r[2])==(public(want),calls,cursor),(segments,layout,phase);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);window_cases+=1
 return dict(wrapper_cases=count,original_wrappers=2,wrapper_words=13,list_cases=loop_cases,original_list_words=35,list_index255_and_empty=True,two_call_window_cases=window_cases,two_call_window_words=7,cursor_chaining_verified=True,retail_JAL_ROM=['0x161350','0x161384','0x1614D0','0x204628','0x20463C'],all_five_JAL_sites_executed=True,full_gameplay_claimed=False)

def connected_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();helper=dict(zip(range(LOADER,LOADER+648,4),struct.unpack_from('>162I',rom,0x13A59C)));ws=[linked(o/n,'connected-'+str(i))for i,n in enumerate(('original-'+F+'.o','selected-final.o','qualified-padded.o'))];count=0;visited=set()
 for resource,zero,segments,layout,priority in itertools.product((-1,0,1,0x1E51,0x1E52),(False,True),(1,2),(0,1),(0xFFFFFFFF,0,127,255)):
  c=Case(index=0,resource=u32(resource),segments=segments,layout=layout,priority=priority,effect=0);initial=fixture(c)
  put(initial,0x800D9F58,3);put(initial,0x800D9F5C,u32(-3));size=0xFFFF
  if 0<=resource<0x1E52:
   put(initial,0x80091D20+2*resource,0 if zero else 1,2);put(initial,0x800B0E58+4*resource,c.address);put(initial,0x800B87A0+2*resource,size,2);put(initial,0x800BC448+resource,0x80,1);put(initial,0x800D9F68+resource,255,1)
  want=dict(initial);put(want,0x800D9F58,u32(min(3,resource)));put(want,0x800D9F5C,u32(max(-3,resource)))
  address=0x80000000;extent=read(initial,STACK-16)
  if 0<=resource<0x1E52:
   if zero:put(want,0x800B0E58+4*resource,address)
   else:address=c.address
   extent=size
   if signed(priority)>-128:put(want,0x800BC448+resource,priority,1)
  put(want,OUTPUT,0xDB0603FC);put(want,OUTPUT+4,address);cursor=OUTPUT+8
  if segments==2:put(want,cursor,0xDB060400);put(want,cursor+4,u32(address+extent-(512 if layout==1 else 32)));cursor+=8
  ms=[]
  for w in ws:m=Oracle(w,initial,c,connected=helper).run();assert(public(m.memory),m.calls,m.r[2])==(public(want),[(LOADER,(u32(resource),STACK-16,priority,0))],cursor),c;ms.append(m);visited.update(m.visits)
  assert state(ms[0])==state(ms[1])==state(ms[2]);count+=1
 return dict(cases=count,executions=count*3,original_loader_words=162,loader_words_visited=sum(p in visited for p in helper),cache_hit_zero_size_and_invalid_ID_paths=True,min_max_extent_priority_and_retain_checked=True,early_return_extent_is_guest_stack_only=True,allocation_decompression_paths_claimed=False)
def controls(body):
 return dict(wrong_resource=body.replace('*D_80090B60[index].resource','(s32)D_80090B60[index].resource'),wrong_index=body.replace('D_80090B60[index]','D_80090B60[(u16)(index + 1)]'),wrong_count=body.replace('segments == 2','segments == 1'),wrong_layout=body.replace('layout == 1','layout == 0'),wrong_large_tail=body.replace('0x200','0x201'),wrong_small_tail=body.replace('0x20)','0x21)'),wrong_segment=body.replace('segment, address','segment + 1, address'),wrong_next_segment=body.replace('segment + 1,','segment + 2,'),wrong_priority=body.replace('&extent, priority, 0','&extent, 0, 0'),wrong_retain=body.replace('&extent, priority, 0','&extent, priority, 1'),wrong_return=body.replace('return cursor;','return cursor - 1;'),reload_count=body.replace('    gSPSegment(cursor++, segment, address);','    segments = D_80090B60[index].segments;\n    gSPSegment(cursor++, segment, address);'),reload_layout=body.replace('    gSPSegment(cursor++, segment, address);','    layout = D_80090B60[index].layout;\n    gSPSegment(cursor++, segment, address);'))
def compiled_controls():
 receipt={};corpus=[Case(index=0,segments=2,layout=1),Case(index=0,segments=2,layout=0),Case(index=0,segments=1)]
 for n,body in controls(source.SELECTED).items():
  assert body!=source.SELECTED;obj,diag=source.compile_owner(r,o,source.HEADERS+body,'control-'+n);assert not diag;w=linked(obj,'control-linked-'+n)
  for i,c in enumerate(corpus):
   initial=fixture(c);p=record(c)+12;put(initial,p,IDS+4);put(initial,IDS+4,c.resource^1);put(initial,p+10,2,1);put(initial,p+11,0,1);m=Oracle(w,initial,c).run()
   try:check(m,initial,c)
   except AssertionError:receipt[n]=i;break
  assert n in receipt,('Ineffective control',n)
 return dict(count=len(receipt),effective_IDO_controls=receipt,compiler_or_oracle_errors_accepted=False)
def native_harness(body):
 return source.HEADERS+body+r'''
typedef char record_size_is_12[sizeof(TextureSegmentRecord15F680)==12?1:-1];
typedef char count_offset_is_10[__builtin_offsetof(TextureSegmentRecord15F680,segments)==10?1:-1];
TextureSegmentRecord15F680 D_80090B60[65536];
static s32 ids[65536];static Gfx output[6];static u32 address,extent,index,segment,priority,count,layout,effect,requests,error;
__attribute__((noinline)) u32 func_1510D0EC(s32 id,s32 *size,s32 prio,s32 retain) {
 requests++;if((u32)id!=(index^0xAABBCCDDu)||(u32)prio!=priority||retain||!size)error=1;
 if(size)*size=(s32)extent;
 if(effect){D_80090B60[index].segments=count==2?1:2;D_80090B60[index].layout=layout^1;ids[index]^=0x55;}
 return address;
}
static int run(void) {
 static const u32 sizes[]={0,1,32,512,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};
 static const u32 addresses[]={0,0x80000000u,0xFFFFFFF0u};static const u8 counts[]={0,1,2,3,255};
 u32 n,i,needed,w0,w1;Gfx *result;
 for(n=0;n<65536;n++){D_80090B60[n].resource=&ids[n];ids[n]=(s32)(n^0xAABBCCDDu);D_80090B60[n].segments=2;D_80090B60[n].layout=1;}
 for(n=0;n<65536;n++)for(effect=0;effect<2;effect++) {
  index=n;segment=n&255;priority=n^0x87654321u;count=counts[n%5];layout=(n>>8)&255;address=addresses[n%3];extent=sizes[n%7];requests=error=0;
  D_80090B60[n].resource=&ids[n];ids[n]=(s32)(n^0xAABBCCDDu);D_80090B60[n].segments=count;D_80090B60[n].layout=layout;
  for(i=0;i<6;i++){output[i].words.w0=0x13570000u+i;output[i].words.w1=0x24680000u+i;}
  result=func_15133EEC(output+1,(u16)n,(u8)segment,(s32)priority);needed=count==2?2:1;
  if(error||requests!=1)return 1;if(result!=output+1+needed)return 2;
  for(i=0;i<6;i++) {
   w0=0x13570000u+i;w1=0x24680000u+i;
   if(i==1){w0=0xDB060000u|segment*4;w1=address;}
   if(i==2&&needed==2){w0=0xDB060000u|((segment+1)*4&65535);w1=address+extent-(layout==1?512u:32u);}
   if(output[i].words.w0!=w0||output[i].words.w1!=w1)return 3;
  }
 }
 return 0;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
def native_suite():
 profiles={};controls_receipt={}
 for opt in ('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]+'.c');p.write_text(native_harness(source.SELECTED));exe=p.with_suffix('');q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr;q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stderr);profiles[opt]=dict(exit=0,cases=131072,UBSan=True)
 for n,body in controls(source.SELECTED).items():
  p=o/('native-control-'+n+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');q=subprocess.run(native_command('-O2')+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr;q=subprocess.run([str(exe)],capture_output=True);assert q.returncode in (1,2,3)and not q.stdout and not q.stderr,(n,q.returncode,q.stderr);controls_receipt[n]=q.returncode
 return dict(cases_per_profile=131072,all65536_indices=True,all256_segments_and_layouts=True,profiles=profiles,negative_controls=len(controls_receipt),effective_native_controls=controls_receipt,SDK32_layout=True,output_canaries=True,metadata_capture_before_helper=True,unsigned_address_wrap=True,loader_output_always_written_contract=True,uninitialized_early_return_extent_or_native_alias_claimed=False)
