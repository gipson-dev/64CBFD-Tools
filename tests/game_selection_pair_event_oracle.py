"""Selection events: original dispatch windows, late byte reads and native32 ABI."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-selection-pair-event-match';F='func_15158FA4';ENTRY=0x15158FA4;BODY=224;ACTOR=0x30000;EVENT=0x50000;MARK=0x70000;SYMS=dict(func_1516972C=0x1516972C,func_1519F400=0x1519F400)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 opcode:int=0
 relation:int=0
 tag_match:int=0
 mutation:int=0
 phase:int=0
def fixture(c,event=EVENT):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-128,128)}
 for base,n in((ACTOR,128),(event,16),(MARK,8)):m.update({base+i:(i*29+0x59)&255 for i in range(n)})
 first=0x89ABCDEF;second=first if c.relation==3 else 0xFEDCBA98;current=(first,second,0x76543210,first)[c.relation]
 put(m,ACTOR+0x18,current);m[ACTOR+0x1C]=(second>>24)^(0 if c.tag_match else 255);put(m,event,first);put(m,event+4,second);m[event+8]=0xD3;m[event+9]=0x27;return m
def effect(m,c,kind,event=EVENT):
 put(m,MARK,kind)
 if c.mutation&1:put(m,ACTOR+0x18,0xA9123456);m[ACTOR+0x1C]=0x5A
 if c.mutation&2:put(m,event,0xCAFEBABE);put(m,event+4,0xFA123456);m[event+8]=0xA7;m[event+9]=0xE2
 if c.mutation&4:put(m,MARK+4,0xABCD1234)
def reference(initial,c,event=EVENT,home=None,ra=0xDEAD0000):
 m=dict(initial);home=STACK+c.phase if home is None else home;put(m,home+8,c.opcode);put(m,home-4,ra);command=c.opcode&255;calls=[]
 if command in(0,4):
  if read(m,ACTOR+0x18)==read(m,event)or m[ACTOR+0x1C]==m[event+4]:
   kind=1 if command==0 else 2;calls.append((kind,(ACTOR,)));effect(m,c,kind,event)
 elif command==45:
  first,current=read(m,event),read(m,ACTOR+0x18)
  if first==current:put(m,ACTOR+0x18,read(m,event+4));m[ACTOR+0x1C]=m[event+9]
  elif read(m,event+4)==current:put(m,ACTOR+0x18,first);m[ACTOR+0x1C]=m[event+8]
 return m,calls
def cases():
 rows=[Case(op,rel,tag,mu,phase)for op in range(256)for rel,tag,phase in itertools.product(range(4),(0,1),(0,8))for mu in((0,7)if op in(0,4)else(0,))]
 rows.extend(Case(0xABCD0000|op,rel,tag,7,phase)for op,rel,tag,phase in itertools.product((0,4,45,255),range(4),(0,1),(0,8)))
 return tuple(rows)
def public(m):return{a:b for a,b in m.items()if not STACK-128<=a<STACK+128}
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None,event=EVENT):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(ACTOR,event,u32(c.opcode)));self.before=self.r[:];self.before_f=self.f[:];self.event=event
 def record_call(self,t):
  assert t in(*self.syms.values(),ENTRY);n=3 if t==ENTRY else 1;a=tuple(self.arguments(n));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  kind=1 if t==self.syms['func_1516972C']else 2;assert t in self.syms.values()and self.calls[-1][1]==(ACTOR,);effect(self.memory,self.case,kind,self.event)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def linked(obj,label,s=SYMS,entry=ENTRY):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>56I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.condition)
def calls_for(calls,s=SYMS):return[(s['func_1516972C'if kind==1 else'func_1519F400'],args)for kind,args in calls]
def verify(m,initial,c,s=SYMS,event=EVENT):
 want,calls=reference(initial,c,event);assert(m.memory,m.calls)==(want,calls_for(calls,s)),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');programs=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[2];count=0;visited=set()
 for c in cases():
  initial=fixture(c);ms=[]
  for program in programs:m=Oracle(program,initial,c);m.run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[2]);assert(ms[0].calls,ms[0].trace,ms[0].memory)==(ms[1].calls,ms[1].trace,ms[1].memory);visited.update(ms[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+BODY,4))-{ENTRY+0x7C,ENTRY+0x9C};prefixes=0
 for c in(Case(0,2,0),Case(0,0,0,7),Case(45,0),Case(45,1),Case(45,2),Case(4,2,1,7),Case(255)):
  initial=fixture(c);full=Oracle(programs[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   ms=[]
   for program in programs:
    m=Oracle(program,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing prefix',cut))
    ms.append(m)
   assert state(ms[0])==state(ms[2]);assert(ms[0].trace,ms[0].memory,ms[0].calls)==(ms[1].trace,ms[1].memory,ms[1].calls);prefixes+=1
 aliases=0
 for event,c in itertools.product((ACTOR+0x10,ACTOR+0x14,ACTOR+0x18,ACTOR+0x1C),tuple(Case(op,rel,tag,7)for op,rel,tag in itertools.product((0,4,45,255),range(4),(0,1)))):
  initial=fixture(c,event);ms=[]
  for program in programs:m=Oracle(program,initial,c,event=event);m.run();verify(m,initial,c,event=event);ms.append(m)
  assert state(ms[0])==state(ms[2]);assert ms[0].trace==ms[1].trace;aliases+=1
 c=Case(255);initial={STACK+i:0 for i in range(-128,128)}
 for program in programs:m=Oracle(program,initial,c);m.r[4]=m.r[5]=0;m.run();assert not m.calls
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s={n:0x10008000+i*0x10000+k*0x100000 for i,n in enumerate(SYMS)};ps=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for c in(Case(op,rel,tag,7)for op,rel,tag in itertools.product((0,4,45,255),range(4),(0,1))):
   initial=fixture(c);ms=[]
   for program in ps:m=Oracle(program,initial,c,s,entry);m.run();verify(m,initial,c,s);ms.append(m)
   assert state(ms[0])==state(ms[2]);assert ms[0].trace==ms[1].trace;rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x2308DC)[0]==ENTRY and 0x8008B4A8+46*0x34+0x1C==0x8008BE1C;windows=((0x15169160,5),(0x15169340,10),(0x15169514,5));cc=0
 for entry,nwords in windows:
  off=entry-0x15000000+0x2D4B0;window=struct.unpack_from('>%dI'%nwords,rom,off);end=entry+nwords*4;call=next(entry+i*4 for i,w in enumerate(window)if w&0xFC1FFFFF==0x0000F809)
  for c in(Case(op,rel,tag,7,phase)for op,rel,tag,phase in itertools.product((0,4,45,255),range(4),(0,1),(0,8))):
   initial=fixture(c);put(initial,ACTOR,46);put(initial,0x8008BE1C,ENTRY);want,calls=reference(initial,c,ra=call+8);ms=[]
   for program in programs:
    code=dict(zip(range(ENTRY,ENTRY+BODY,4),program));code[end]=0;m=Oracle(window,initial,c,entry=entry,connected=code);m.r[16]=ACTOR;m.r[18]=EVENT;m.r[19]=u32(c.opcode);m.r[22]=ACTOR if nwords==10 else 0x8008BE00;m.r[23]=0x8008B4A8;m.r[30]=0x34
    if entry==0x15169514:m.r[19]=EVENT;m.r[20]=u32(c.opcode)
    m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing callback boundary')
    # Caller masks A2 before dispatch, so the incoming home holds its low byte.
    expected=dict(want);put(expected,STACK+c.phase+8,c.opcode&255);assert(m.memory,m.calls)==(expected,[(ENTRY,(ACTOR,EVENT,c.opcode&255))]+calls_for(calls));ms.append(m)
   assert state(ms[0])==state(ms[2]);assert ms[0].trace==ms[1].trace;cc+=1
 return dict(cases=count,executions=count*3,covered_words=54,compiler_words=56,slot_words=56,alignment_words=0,unreachable_offsets=[124,156],frame=24,guards=15,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,guest_alias_cases=aliases,sparse_unhandled_NULL_pointers=True,caller_windows=3,caller_window_words=[5,10,5],caller_window_cases=cc,registration_table='D_8008B4A8',registration_index=46,registration_stride=52,registration_field=28,registration_ROM='0x2308DC',result_ignored=True,original_and_normalized_full_state_equal=True,raw_C_access_call_memory_and_ABI_equal=True,bounded_helpers=True,complete_helpers_or_parents_claimed=False,private_only=True,installed=False,matching_credit=0)
def controls(body):return dict(wrong_zero_helper=body.replace('func_1516972C(selection)','func_1519F400(selection)'),wrong_four_helper=body.replace('func_1519F400(selection)','func_1516972C(selection)'),wrong_command=body.replace('opcode == 0x2D','opcode == 0x2C'),wrong_first_tag=body.replace('event[9]','event[8]'),wrong_second_tag=body.replace('event[8]','event[9]'),wrong_swap=body.replace('= first;','= current;'),wrong_output=body.replace('selection[0x1C] =','selection[0x1D] ='),wrong_helper_pointer=body.replace('(selection);','(selection + 4);'),wrong_byte_gate=body.replace('(selection[0x1C] == event[4])','(*(u32 *)(selection + 0x1C) == *(u32 *)(event + 4))'))
def native_harness(selected):
 head,body=selected.split('/* Apply',1);body='/* Apply'+body;bad=controls(body);assert all(v!=body for v in bad.values());cs=[c for c in cases()if not c.phase and c.opcode<256];rows=[]
 text=head+r'''
_Static_assert(sizeof(void*)==4,"native32");
typedef struct{u32 opcode,relation,tag,mutation,current,second,result,byte,helper;}Fixture;
static const Fixture*current;static u8 actor[128]__attribute__((aligned(8))),event[16]__attribute__((aligned(8)));static u32 calls,bad,kind;
static void helper(u8*p,u32 k){calls++;kind=k;if(p!=actor)bad=1;if(current->mutation&1){*(u32*)(actor+0x18)=0xA9123456;actor[0x1C]=0x5A;}if(current->mutation&2){*(u32*)event=0xCAFEBABE;*(u32*)(event+4)=0xFA123456;event[8]=0xA7;event[9]=0xE2;}}
void func_1516972C(u8*p){helper(p,1);}void func_1519F400(u8*p){helper(p,2);}
'''
 text+='\n'.join(v.replace(F,'test_'+k)for k,v in dict(selected=body,**bad).items())
 for c in cs:
  initial=fixture(c);first=read(initial,EVENT);second=read(initial,EVENT+4);value=read(initial,ACTOR+0x18);tag=(second&255)^(0 if c.tag_match else 255);helper=0
  if c.opcode in(0,4)and(value==first or c.tag_match):
   helper=1 if c.opcode==0 else 2
   if c.mutation&1:value=0xA9123456;tag=0x5A
  elif c.opcode==45:
   if value==first:value=second;tag=0x27
   elif value==second:value=first;tag=0xD3
  values=(c.opcode,c.relation,c.tag_match,c.mutation,read(initial,ACTOR+0x18),second,value,tag,helper);rows.append('{'+','.join('0x%Xu'%u32(v)for v in values)+'}')
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 text+=r'''
typedef void(*Update)(u8*,u8*,u8);
static int check(Update fn){u32 n,i;u8 expected;for(n=0;n<CASE_COUNT;n++){current=fixtures+n;calls=bad=kind=0;for(i=0;i<128;i++)actor[i]=(u8)(i*29+0x59);for(i=0;i<16;i++)event[i]=(u8)(i*29+0x59);*(u32*)(actor+0x18)=current->current;actor[0x1C]=(u8)((current->second&255)^(current->tag?0:255));*(u32*)event=0x89ABCDEF;*(u32*)(event+4)=current->second;event[8]=0xD3;event[9]=0x27;fn(actor,event,(u8)current->opcode);if(bad||kind!=current->helper||calls!=(current->helper!=0))return 1;for(i=0;i<128;i++){expected=(u8)(i*29+0x59);if(i>=0x18&&i<0x1C)expected=(u8)(current->result>>(8*(i-0x18)));if(i==0x1C)expected=(u8)current->byte;if(actor[i]!=expected)return 2;}for(i=0;i<16;i++){u32 first=0x89ABCDEF,second=current->second;u8 a=0xD3,b=0x27;expected=(u8)(i*29+0x59);if(current->helper&&(current->mutation&2)){first=0xCAFEBABE;second=0xFA123456;a=0xA7;b=0xE2;}if(i<4)expected=(u8)(first>>(8*i));else if(i<8)expected=(u8)(second>>(8*(i-4)));else if(i==8)expected=a;else if(i==9)expected=b;if(event[i]!=expected)return 3;}}return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,k in enumerate(bad):text+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');return text,dict(cases=len(rows),negative_controls=len(bad),signature='void(u8*,u8*,u8)',all_record_event_bytes_checked=True,helper_identity_and_pointer_checked=True,all_256_opcodes=True,guest_only_aliases_and_private_homes=True,native_little_endian_byte_word_overlap_modeled=True)
def run_native(selected):
 text,counts=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,**counts,UBSan=True)
 return dict(profiles=reports,**counts)
