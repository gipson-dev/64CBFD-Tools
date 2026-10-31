"""Typed actor command callback: ordered copies, aliases and release routing.

Partial overlapping structure copies are guest-machine cases only. Native C
uses a separate typed payload; identity-only commands also exercise aliases.
"""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess,csv,io
from tools.experiments import game_actor_command_payload_match as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD;F=source.FUNCTION;ENTRY=source.ENTRY
ACTOR,EVENT,VECTOR,FREE,PARENT,TABLE=0x28000,0x30000,0x800A5480,0x1516972C,0x15149434,0x8008A8D8
PRE,FALLBACK,CALLBACK,DTABLE=0x151696DC,0x15169804,0x15200000,0x8008B4D0
SYMS=dict(D_800A5480=VECTOR,func_1516972C=FREE)
BITS=(0,0x80000000,1,0x007FFFFF,0x00800000,0x3F800000,0xBF800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7FA12345)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 command:int=0x32
 relation:bool=True
 alias:int=0
 flags:int=255
 pattern:int=0
 phase:int=0
 mode:int=0
 kind:int=2
 callback:bool=False
 connected:bool=False
def address(c,s=SYMS):return (EVENT,ACTOR+0x40,ACTOR+0x44,ACTOR+0x3C,ACTOR+0x64,s['D_800A5480'],ACTOR+0x68)[c.alias]
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)}
 for base,n in((ACTOR-16,256),(EVENT-16,80),(s['D_800A5480']-16,64)):
  m.update({base+i:(i*13+0xA5)&255 for i in range(n)})
 for i in range(3):put(m,s['D_800A5480']+4*i,BITS[(c.pattern+5+i)%12])
 p=address(c,s)
 for i in range(4):put(m,p+4*i,BITS[(c.pattern+i)%12])
 put(m,ACTOR+0x68,p if c.relation else p+4);m[ACTOR+0x6C]=c.flags;m[ACTOR]=c.kind
 for kind in(c.kind,2):put(m,DTABLE+52*kind,CALLBACK if c.callback else 0)
 return m
def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+512}
def free_effect(m,c):
 if c.mode&1:m[ACTOR+0x6C]^=0x55
def reference(initial,c,s=SYMS,connected=None):
 m=dict(initial);calls=[];command=c.command&255;p=address(c,s)
 if command==0x32:
  for i in range(3):put(m,ACTOR+0x40+4*i,read(m,p+4*i))
  put(m,ACTOR+0x64,read(m,p+12))
 elif command in(0x30,0x31):
  if p==read(m,ACTOR+0x68):m[ACTOR+0x6C]=(m[ACTOR+0x6C]|1)if command==0x30 else(m[ACTOR+0x6C]&254)
 elif command==0x4E:
  for i in range(3):put(m,ACTOR+0x40+4*i,read(m,s['D_800A5480']+4*i))
 elif command==0x4F:
  calls.append((s['func_1516972C'],(ACTOR,)))
  if c.connected if connected is None else connected:
   calls.append((PRE,(ACTOR,)))
   if c.mode&2:m[ACTOR]=2
   if m[ACTOR]>=2:
    calls.append((CALLBACK if read(m,DTABLE+52*m[ACTOR])else FALLBACK,(ACTOR,)));free_effect(m,c)
  else:free_effect(m,c)
 return m,calls
def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown
 p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
 subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
class Oracle(TimingOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=None,callbacks=()):
  self.c=c;self.syms=s;self.cut=None;self.accesses=0;self.trace=[];self.callback_set=set(callbacks)
  if c.connected and connected is None:
   rom=(r/'conker/conker.us.bin').read_bytes();connected=dict(zip(range(FREE,FREE+112,4),struct.unpack_from('>28I',rom,0x196BDC)))
  super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(ACTOR,address(c,s),c.command),connected=connected)
  self.before=self.r[:];self.saved_f=self.f[20:]
 def access(self):
  if self.own_instruction:
   if self.accesses==self.cut:raise faults.AccessBoundary
   self.accesses+=1
 def get(self,p,n):
  v=super().get(p,n)
  if self.own_instruction:self.trace.append(('R',p,n,v))
  return v
 def put(self,p,v,n):
  super().put(p,v,n)
  if self.recording and self.own_instruction:self.trace.append(('W',p,n,v&((1<<(8*n))-1)))
 def record_call(self,t):
  n=3 if t==ENTRY or t in self.callback_set else 1
  assert t in(ENTRY,self.syms['func_1516972C'],PRE,FALLBACK,CALLBACK)or t in self.callback_set,('unbounded-call',hex(t))
  a=tuple(map(u32,self.arguments(n)));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert t!=ENTRY
  if t==PRE:
   if self.c.mode&2:self.memory[ACTOR]=2
  elif t in(self.syms['func_1516972C'],FALLBACK,CALLBACK):free_effect(self.memory,self.c)
  else:assert t in self.callback_set
  for i in range(4):self.put(self.r[29]+i*4,0xB6000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA6000000+reg
  self.f[:20]=[0xA6000000+i for i in range(20)];self.hi,self.lo=0xA6000010,0xA6000011;self.r[2]=0x76543210
def state(m):return complete(m),m.trace,m.current_pc,m.delay_of,m.accesses
def check(m,c,s=SYMS):
 want,calls=reference(fixture(c,s),c,s)
 assert(public(m.memory),m.calls)==(public(want),calls),('public-state-or-calls',c)
 assert m.r[29]==STACK+c.phase and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.saved_f,('ABI-preservation',c)
def corpus():
 for command,relation,phase in itertools.product(range(256),(False,True),(0,8)):
  yield Case(command|0xA5B60000,relation,flags=(command*13)&255,pattern=command%12,phase=phase,mode=1)
 for flags,command in itertools.product(range(256),(0x30,0x31)):yield Case(command,flags=flags)
 for alias,command,relation,pattern in itertools.product(range(7),(0x30,0x31,0x32,0x4E,0x4F,0xFF),(False,True),range(12)):
  yield Case(command,relation,alias,0xA5,pattern,mode=1)
 for kind,callback,mode,phase in itertools.product((0,1,2,255),(False,True),(0,2),(0,8)):
  yield Case(0x4F,kind=kind,callback=callback,connected=True,mode=mode,phase=phase)
def guest_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ws=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];visits=set();hv=set();n=0
 for c in corpus():
  ms=[Oracle(w,fixture(c),c).run()for w in ws]
  for m in ms:check(m,c)
  assert state(ms[0])==state(ms[2]),c
  visits.update(ms[0].visits&set(range(ENTRY,ENTRY+232,4)));hv.update(ms[0].visits&set(range(FREE,FREE+112,4)));n+=1
 assert visits==set(range(ENTRY,ENTRY+232,4))-{ENTRY+132},sorted((p-ENTRY)//4 for p in set(range(ENTRY,ENTRY+232,4))-visits)
 cuts=delays=0
 for c in(Case(0x32,alias=2),Case(0x30),Case(0x31),Case(0x4E),Case(0x4F,mode=1),Case(0xFF),Case(0x30,False)):
  baseline=Oracle(ws[0],fixture(c),c).run()
  for cut in range(baseline.accesses):
   ms=[Oracle(w,fixture(c),c)for w in(ws[0],ws[2])]
   for m in ms:
    m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Ineffective fault cutoff')
   assert state(ms[0])==state(ms[1]);cuts+=1;delays+=ms[0].delay_of is not None
 rebased=0
 for i,entry in enumerate((0x17007FFC,0x2500FFFC,0x15008000)):
  s=dict(D_800A5480=0x60007FFC+i*0x10000,func_1516972C=entry+0x20000)
  bw=[linked(p,'rebased-%d-%d'%(i,j),entry,s)for j,p in enumerate(objects)]
  for c in(Case(0x32,alias=2),Case(0x4E),Case(0x4F,mode=1)):
   ms=[Oracle(w,fixture(c,s),c,entry,s).run()for w in bw]
   for m in ms:check(m,c,s)
   assert state(ms[0])==state(ms[2]);rebased+=1
 return dict(cases=n,executions=n*3,root_words_visited=len(visits),unreachable_duplicate_load_offset=132,original_release_words=28,helper_words_visited=len(hv),access_prefix_cases=cuts,branch_delay_cuts=delays,rebased_cases=rebased,original_normalized_complete_state_trace_fault_context_equal=True,raw_C_public_memory_calls_equal=True,raw_fault_schedule_equated=False,partial_overlap_is_guest_machine_only=True,all256_command_and_flag_bytes=True,high_command_home=True,lower_release_providers_bounded=True)
def controls(body):
 edits={'copy-command':('command == 0x32','command == 0x33'),'owner-gate':('payload == state->owner','payload != state->owner'),'set-bit':('state->flags |= 1','state->flags |= 2'),'clear-bit':('state->flags &= ~1','state->flags &= ~2'),'value-field':('((ActorCommandPayload *)payload)->value','((ActorCommandPayload *)payload)->position.z'),'copy-incomplete':('state->position = ((ActorCommandPayload *)payload)->position','state->position.x = ((ActorCommandPayload *)payload)->position.x'),'reset-command':('command == 0x4E','command == 0x4D'),'release-command':('command == 0x4F','command == 0x4D'),'missing-release':('func_1516972C((struct102 *)actor);','(void)actor;'),'missing-reset':('*(CommandVector *)((u8 *)actor + 0x40) = D_800A5480;','(void)actor;')}
 result={}
 for name,(a,b)in edits.items():assert body.count(a)==1,(name,a);result[name]=body.replace(a,b,1)
 return result
def compiled_controls():
 effective={};cases=[Case(command,relation,flags=0xA5,pattern=5,mode=1)for command,relation in itertools.product((0x30,0x31,0x32,0x4E,0x4F,0xFF),(False,True))]
 for name,body in controls(source.SELECTED).items():
  obj,diag=source.compile_owner(r,o,source.HEADERS+body,'IDO-control-'+name);assert not diag;words=linked(obj,'IDO-linked-'+name)
  for c in cases:
   m=Oracle(words,fixture(c),c).run()
   try:check(m,c)
   except AssertionError as e:
    assert e.args and isinstance(e.args[0],tuple)and e.args[0][0]=='public-state-or-calls',(name,e);effective[name]='semantic disagreement';break
  else:raise AssertionError('Ineffective compiled control '+name)
 return dict(successful_IDO_compiles=len(effective),effective_semantic_controls=effective,compiler_or_interpreter_failures_counted=False)
def guard_suite():
 raw,rs=source.payload(o/'selected-final.o');assert source.normalized_payload(raw,rs)==source.payload(o/('original-'+F+'.o'))
 before=(o/'before-conker_retail_word_patches.us.csv').read_bytes();reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rejected=0
 for i,row in enumerate(source.NEW_GUARDS):
  for kind in('expected','expected_relocations'):
   rows=[dict(x)for x in source.NEW_GUARDS]
   rows[i][kind]='0x%08X'%(int(row['expected'],0)^1)if kind=='expected'else'R_MIPS_26:foreign'
   buf=io.StringIO(newline='');csv.DictWriter(buf,fields,lineterminator='\n').writerows(rows);p=o/('guard-control-%d-%s.csv'%(i,kind));p.write_bytes(before+buf.getvalue().encode())
   try:source.emit_padded_assembly(o/'after-owner.o',r/source.ASM,filename=source.OWNER,word_patches_path=p)
   except ValueError:rejected+=1
   else:raise AssertionError('Ineffective actual padder guard control')
 return dict(guards=8,insertions=2,omissions=0,actual_padder_rejections=rejected,inserted_words=[0x8FBF0014]*2,insertions_restore_RA20_not_new_behavior=True,raw_words=56,normalized_words=58,bindings_shifted_without_change=True)
def caller_suite():
 rom=source.snapshot(o)['conker/conker.us.bin'];jal=(0x0C000000|((ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');assert not any(rom[i:i+4]==jal for i in range(0,len(rom)-3,4))
 pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==ENTRY.to_bytes(4,'big')];assert pointers==[0x22F43C]
 table=list(struct.unpack_from('>74I',rom,0x22F398));assert table[41]==ENTRY
 parent=list(struct.unpack_from('>23I',rom,0x1768E4));objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ws=[linked(p,'caller-'+str(i))for i,p in enumerate(objects)];seen=set();n=0
 for selector,command,relation,phase in itertools.product((0,41,74,255),(0x30,0x31,0x32,0x4E,0x4F,0xFF),(False,True),(0,8)):
  c=Case(command,relation,phase=phase,mode=1);initial=fixture(c);initial[ACTOR+19]=selector
  for i,value in enumerate(table):put(initial,TABLE+i*4,value)
  chosen=selector if selector<74 else 0;wanted=dict(initial);calls=[]
  if table[chosen]:
   calls=[(table[chosen],(ACTOR,address(c),command))]
   if chosen==41:wanted,more=reference(initial,c);calls+=more
  ms=[]
  for w in ws:
   conn=dict(zip(range(ENTRY,ENTRY+4*len(w),4),w));m=Oracle(parent,initial,c,PARENT,connected=conn,callbacks=table).run();assert(public(m.memory),m.calls)==(public(wanted),calls);ms.append(m)
  assert state(ms[0])==state(ms[2]);seen.update(ms[0].visits&set(range(PARENT,PARENT+92,4)));n+=1
 assert len(seen)==23
 return dict(registered_slot=41,table_entries=74,aligned_literal_pointers=pointers,direct_JALs=[],original_dispatcher_words=23,dispatcher_words_visited=len(seen),cases=n,typed_callback_arguments=['struct260 *','s32','u8'],return_value_ignored=True,out_of_range_and_null_slots=True,other_callbacks_bounded=True)

def native_harness(body):
 return source.HEADERS+r'''
typedef struct {u8 prefix[40];ActorCommandState state;u8 suffix[128];} Envelope;
typedef char StateOffset[__builtin_offsetof(Envelope,state)==40?1:-1];
typedef char FlagsOffset[__builtin_offsetof(ActorCommandState,flags)==68?1:-1];
typedef char ValueOffset[__builtin_offsetof(ActorCommandState,value)==60?1:-1];
typedef char PointerBytes[sizeof(void*)==4?1:-1];
static Envelope actual,expected;static ActorCommandPayload payload;CommandVector D_800A5480;
static int calls,wantCalls,mode,error;static u32 bits[12]={0,0x80000000u,1,0x007FFFFFu,0x00800000u,0x3F800000u,0xBF800000u,0x7F7FFFFFu,0x7F800000u,0xFF800000u,0x7FC12345u,0x7FA12345u};
static void putword(void *p,u32 v){u8 *d=(u8*)p;const u8 *s=(const u8*)&v;int i;for(i=0;i<4;i++)d[i]=s[i];}
static void copyword(u8 *d,const u8 *s){int i;u8 tmp[4];for(i=0;i<4;i++)tmp[i]=s[i];for(i=0;i<4;i++)d[i]=tmp[i];}
__attribute__((noinline)) void func_1516972C(struct102 *actor){calls++;if(actor!=(struct102*)&actual)error=1;if(mode)((u8*)actor)[0x6C]^=0x55;}
'''+body+r'''
static int one(u32 command,int flag,int relation,int pattern,int alias){int i;u8 *a=(u8*)&actual,*e=(u8*)&expected;void *p=alias?(void*)(a+0x40):(void*)&payload;u8 cmd=(u8)command;void (*callback)(struct260*,s32,u8)=func_150D1F6C;
for(i=0;i<(int)sizeof(actual);i++)a[i]=(u8)(i*13+flag);for(i=0;i<4;i++)putword((u8*)&payload+4*i,bits[(pattern+i)%12]);for(i=0;i<3;i++)putword((u8*)&D_800A5480+4*i,bits[(pattern+5+i)%12]);actual.state.owner=relation?p:(void*)((u8*)p+4);actual.state.flags=(u8)flag;expected=actual;wantCalls=0;
if(cmd==0x32){for(i=0;i<3;i++)copyword(e+0x40+4*i,(u8*)&payload+4*i);copyword(e+0x64,(u8*)&payload+12);}
else if(cmd==0x30||cmd==0x31){if(relation){if(cmd==0x30)expected.state.flags|=1;else expected.state.flags&=254;}}
else if(cmd==0x4E){for(i=0;i<3;i++)copyword(e+0x40+4*i,(u8*)&D_800A5480+4*i);}
else if(cmd==0x4F){wantCalls=1;if(mode)expected.state.flags^=0x55;}
calls=error=0;callback((struct260*)&actual,(s32)p,cmd);if(error||calls!=wantCalls)return 1;for(i=0;i<(int)sizeof(actual);i++)if(a[i]!=e[i])return 2;return 0;}
static int run(void){u32 command;int flag,relation,pattern,result,alias;for(command=0;command<256;command++)for(flag=0;flag<256;flag++)for(relation=0;relation<2;relation++){mode=flag&1;result=one(command,flag,relation,flag%12,0);if(result)return result;}
for(pattern=0;pattern<12;pattern++)for(alias=0;alias<2;alias++)for(relation=0;relation<2;relation++)for(command=0x30;command<=0x31;command++){mode=1;result=one(command,0xA5,relation,pattern,alias);if(result)return result;}return 0;}
'''+START
def native_suite():
 profiles={};effective={}
 def compile_run(body,label,opt):
  p=o/(label+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');q=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert not q.stdout and not q.stderr,(label,q.stdout,q.stderr);return q.returncode
 for opt in('-O0','-O2','-O3'):
  code=compile_run(source.SELECTED,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(exit=0,cases=131168,UBSan=True)
 for name,body in controls(source.SELECTED).items():
  code=compile_run(body,'native-control-'+name,'-O2');assert code in(1,2),(name,code);effective[name]=code
 return dict(cases_per_profile=131168,profiles=profiles,SDK32_layout=True,whole_envelope_canaries_checked=True,typed_three_argument_callback_invoked=True,native_aliases_only_for_identity_commands=True,partial_structure_overlap_not_claimed_portable=True,float_bit_patterns=12,negative_controls=len(effective),effective_native_controls=effective)
