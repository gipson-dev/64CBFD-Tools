"""Descriptor type gate, live post-allocation copy and bounded buffer initialization."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,re,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-gated-effect-buffer-constructor-match';F='func_1518E3C4';ENTRY=0x1518E3C4;BODY=220;DESC=0x30000;ALT=0x31000;TYPE=0x60000;TYPEALT=0x61000;OUTPUT=0x50000;SIZE=0x9EC
SYMS=dict(func_15167A68=0x15167A68,memcpy=0x10022EC0,bzero=0x100226F0)
@dataclass(frozen=True)
class Case:
 kind:int=0
 priority:int=255
 outcome:int=1
 mutation:int=0
 phase:int=0
 seed:int=0
 descriptor:int=DESC
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,512)}
 for base,n in((DESC,12),(ALT,12),(TYPE,16),(TYPEALT,16),(OUTPUT,SIZE)):
  m.update({base+i:(i*29+c.seed*11+0x5A)&255 for i in range(n)})
 for base,pointer in((c.descriptor,TYPE),(ALT,TYPEALT)):
  put(m,base,pointer);put(m,base+4,0x87654321^c.seed);put(m,base+8,0xAABBCCDD^c.seed)
 m[TYPE+4]=c.kind;m[TYPEALT+4]=150;return m
def effect(m,c):
 if c.mutation&1:put(m,c.descriptor,TYPEALT);put(m,c.descriptor+4,0x12345678);put(m,c.descriptor+8,0xFEDCBA98)
 if c.mutation&2:put(m,STACK+c.phase,ALT)
 if c.mutation&4:put(m,STACK+c.phase+4,0xAABBCC00)
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def reference(initial,c,s=SYMS):
 m=dict(initial);home=STACK+c.phase;put(m,home,c.descriptor);put(m,home+4,c.priority);calls=[];copies=[]
 if m[read(m,c.descriptor)+4]==150:return m,calls,0,copies
 calls.append((s['func_15167A68'],(33,1,SIZE,1,c.priority&255,1)));effect(m,c)
 if not c.outcome:return m,calls,0,copies
 source=read(m,home);payload=data(m,source,12);calls.append((s['memcpy'],(OUTPUT+0x18,source,12)));copies.append(payload)
 for i,b in enumerate(payload):m[OUTPUT+0x18+i]=b
 for at,w in((0x28,0),(0x30,0),(0x10,1),(0x14,0),(0x24,0),(0x38,0),(0x3C,0),(0x40,0),(0x34,0x3F800000)):put(m,OUTPUT+at,w)
 m[OUTPUT+0x2C]=8;m[OUTPUT+0x2D]=4;calls.append((s['bzero'],(OUTPUT+0x48,0x960)))
 for i in range(0x960):m[OUTPUT+0x48+i]=0
 return m,calls,OUTPUT,copies
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def cases():
 rows=[Case(kind=k,priority=p,outcome=a,mutation=mu,phase=phase,seed=(k+p+mu)&3)for k,p,a,mu,phase in itertools.product((0,149,150,151,255),(0,128,255,0xAABBCC81),(0,1),(0,1,2,4,7),(0,8))]
 rows.extend(Case(kind=k,priority=k,outcome=a,seed=k&7)for k,a in itertools.product(range(256),(0,1)))
 rows.extend(Case(priority=p,mutation=1,seed=p&7)for p in range(256));return tuple(dict.fromkeys(rows))
def native_safe(c):return not c.phase and not c.mutation&(2|4)and c.descriptor==DESC
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(c.descriptor,c.priority));self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  a=tuple(self.arguments({self.syms['func_15167A68']:6,self.syms['memcpy']:3,self.syms['bzero']:2,ENTRY:2}[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==self.syms['memcpy']:self.copy_observations.append(data(self.memory,a[1],a[2]))
 def hook(self,t):
  a=self.calls[-1][1];s=self.syms;c=self.case
  if t==s['func_15167A68']:effect(self.memory,c);value=OUTPUT if c.outcome else 0
  elif t==s['memcpy']:
   assert a[2]==12;raw=data(self.memory,a[1],a[2]);assert not(a[0]<a[1]+a[2]and a[1]<a[0]+a[2])
   for i,b in enumerate(raw):self.memory[a[0]+i]=b
   value=a[0]
  else:
   assert t==s['bzero']and a==(OUTPUT+0x48,0x960)
   for i in range(a[1]):self.memory[a[0]+i]=0
   value=0xDEADBEEF
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=value
def linked(obj,label,s=SYMS,entry=ENTRY):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>55I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.copy_observations)
def verify(m,initial,c,s=SYMS):
 want,calls,value,copies=reference(initial,c,s);assert(public(m.memory),m.calls,m.r[2],m.copy_observations)==(public(want),calls,value,copies),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2];visited=set();count=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+BODY,4));prefixes=0
 for c in(Case(kind=150),Case(outcome=0,mutation=7),Case(mutation=7,phase=8)):
  initial=fixture(c);full=Oracle(ps[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in ps:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access prefix',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s={name:0x10008000+0x10000*j+k*0x100000 for j,name in enumerate(SYMS)};programs=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for kind,outcome,mu,phase in itertools.product((0,150),(0,1),(0,7),(0,8)):
   c=Case(kind=kind,outcome=outcome,mutation=mu,phase=phase);initial=fixture(c);machines=[]
   for words in programs:m=Oracle(words,initial,c,s,entry);m.run();verify(m,initial,c,s);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);rebased+=1
 rom=(r/'conker/conker.us.bin').read_bytes();asm=(r/'conker/asm/1BA1D0.s').read_text();windows=[]
 for match in re.finditer(r'/\* ([0-9A-F]+) ([0-9A-F]+) [0-9A-F]{8} \*/  jal\s+func_1518E3C4',asm):
  off=int(match[1],16);pc=int(match[2],16);raw=rom[off:off+8];words=struct.unpack('>2I',raw);assert words[0]==0x0D4638F1;cc=0;end=pc+8;delay=words[1];n=2
  if delay!=0x93A5005B:
   assert delay in(0xA7AB0042,0xA7B90042)
   assert struct.unpack_from('>I',rom,off-0x24)[0]==(0x87AB0052 if delay==0xA7AB0042 else 0x87B90052)
   off-=4;pc-=4;n=3;words=struct.unpack_from('>3I',rom,off);assert words[0]==0x93A5005B
  for kind,outcome,priority in itertools.product((0,150),(0,1),(0,255)):
   c=Case(kind=kind,outcome=outcome,priority=priority,mutation=1,descriptor=STACK+0x3C);initial=fixture(c);put(initial,STACK+0x5B,c.priority,1);put(initial,STACK+0x52,0x8001,2);expected_initial=dict(initial);machines=[]
   if n==3:put(expected_initial,STACK+0x42,0x8001,2)
   for program in ps:
    code=dict(zip(range(ENTRY,ENTRY+BODY,4),program));code[end]=0;m=Oracle(words,initial,c,entry=pc,connected=code);m.code=WindowCode(m.code,m);m.code.ends=(end,)
    if n==3:m.r[11 if delay==0xA7AB0042 else 25]=0xFFFF8001
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing caller window boundary')
    want,calls,value,copies=reference(expected_initial,c);assert(public(m.memory),m.calls,m.r[2],m.copy_observations)==(public(want),[(ENTRY,(c.descriptor,c.priority))]+calls,value,copies);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);cc+=1
  windows.append(dict(entry=hex(pc),ROM=hex(off),words=n,cases=cc,end=hex(end),A0_entry_precondition='caller SP+0x3C descriptor',priority_load='unsigned byte caller SP+0x5B',delay_word=hex(delay),halfword_entry_precondition='signed caller SP+0x52 in T3/T9'if n==3 else None,full_parent_claimed=False))
 assert len(windows)==18
 return dict(cases=count,executions=count*3,covered_words=55,compiler_words=55,slot_words=55,alignment_words=0,frame=40,guards=0,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,caller_windows=windows,allocated_bytes=SIZE,cleared_offset=0x48,cleared_bytes=0x960,untouched_bytes=90,bounded_allocator_and_SDK_providers=True,SDK_original_instructions_executed=False,literal_full_state_equal=True,private_only=True,installed=False,matching_credit=0)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def controls(body):
 return dict(wrong_type=body.replace('== 150','== 149'),wrong_kind=body.replace('(0x21, 1','(0x20, 1'),wrong_allocation_size=body.replace('0x9EC','0x9E8'),wrong_copy_offset=body.replace('memcpy(record + 0x18','memcpy(record + 0x1C'),wrong_copy_length=body.replace('descriptor, 12','descriptor, 8'),wrong_clear_offset=body.replace('bzero(record + 0x48','bzero(record + 0x4C'),wrong_clear_length=body.replace('0x960','0x95C'),wrong_scale=body.replace('= 1.0f','= 2.0f'),repeated_type_gate=body.replace('    memcpy(record','    if ((*(u8 **)descriptor)[4] == 150) return NULL;\n    memcpy(record'))
def digest(raw,lo,hi):
 n=2166136261
 for i,b in enumerate(raw):
  if not lo<=i<hi:n=((n^b)*16777619)&0xFFFFFFFF
 return n
def native_harness(selected):
 head,body=selected.split('/* Reject',1);body='/* Reject'+body;bad=controls(body);assert all(x!=body for x in bad.values())
 text=head+r'''
_Static_assert(sizeof(void*)==4,"native32");
typedef struct{u32 kind,priority,outcome,mutation,seed,calls,outputHash,descriptorHash,alt;u8 outputPrefix[72],descriptorBytes[12];} Fixture;
static const Fixture*current;static u32 stage,bad;
static u8 descriptor[12] __attribute__((aligned(8))),type[16],altType[16],buffer[0x9EC] __attribute__((aligned(8)));
static u32 hash(const u8*p,u32 n,u32 lo,u32 hi){u32 i,h=2166136261u;for(i=0;i<n;i++)if(i<lo||i>=hi)h=(h^p[i])*16777619u;return h;}
void *func_15167A68(s32 a,s32 b,s32 c,s32 d,u8 e,u8 f){if(stage++||a!=33||b!=1||c!=0x9EC||d!=1||e!=(current->priority&255)||f!=1)bad=1;
 if(current->mutation&1){*(void**)descriptor=altType;*(u32*)(descriptor+4)=0x12345678;*(u32*)(descriptor+8)=0xFEDCBA98;}return current->outcome?buffer:NULL;}
void *memcpy(void*d,const void*s,u32 n){u32 i;if(stage++!=1||d!=buffer+0x18||s!=descriptor||n!=12)bad=2;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];return d;}
void bzero(void*d,int n){u32 i;if(stage++!=2||d!=buffer+0x48||n!=0x960)bad=3;for(i=0;i<(u32)n;i++)((u8*)d)[i]=0;}
'''
 text+='\n'.join(source.replace(F,'test_'+name)for name,source in dict(selected=body,**bad).items());rows=[]
 for c in cases():
  if not native_safe(c):continue
  want,calls,value,copies=reference(fixture(c),c);output=bytearray(data(want,OUTPUT,SIZE));descriptor=bytearray(data(want,DESC,12))
  # Native32 stores scalar words little-endian; preserve untouched byte backing.
  if value:
   for at in(0x10,0x14,0x18,0x1C,0x20,0x24,0x28,0x30,0x34,0x38,0x3C,0x40):output[at:at+4]=output[at:at+4][::-1]
  for at in(0,4,8):descriptor[at:at+4]=descriptor[at:at+4][::-1]
  values=(c.kind,c.priority,c.outcome,c.mutation,c.seed,len(calls),digest(output,0x18,0x1C),digest(descriptor,0,4),int(read(want,DESC)==TYPEALT))
  array=lambda b:'{'+','.join(str(x)for x in b)+'}'
  rows.append('{'+','.join('0x%Xu'%(x&0xFFFFFFFF)for x in values)+','+array(output[:72])+','+array(descriptor)+'}')
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 text+=r'''
typedef void*(*Constructor)(void*,u8);
static s32 check(Constructor fn){u32 n,i;void*answer;for(n=0;n<CASE_COUNT;n++){current=fixtures+n;stage=bad=0;
 for(i=0;i<0x9EC;i++)buffer[i]=(u8)(i*29+current->seed*11+0x5A);for(i=0;i<16;i++)type[i]=altType[i]=(u8)(i*29+current->seed*11+0x5A);
 type[4]=(u8)current->kind;altType[4]=150;*(void**)descriptor=type;*(u32*)(descriptor+4)=0x87654321u^current->seed;*(u32*)(descriptor+8)=0xAABBCCDDu^current->seed;
 answer=fn(descriptor,(u8)current->priority);if(bad||stage!=current->calls)return 1;if(answer!=(current->kind!=150&&current->outcome?(void*)buffer:NULL))return 2;
 if(hash(buffer,0x9EC,0x18,0x1C)!=current->outputHash||hash(descriptor,12,0,4)!=current->descriptorHash)return 3;
 if(*(void**)descriptor!=(current->alt?(void*)altType:(void*)type))return 4;if(answer&&*(void**)(buffer+0x18)!=*(void**)descriptor)return 5;
 if(!answer)for(i=0x18;i<0x1C;i++)if(buffer[i]!=(u8)(i*29+current->seed*11+0x5A))return 6;
 for(i=0;i<0x9EC;i++){u8 expected;if(i>=0x18&&i<0x1C)continue;expected=i<72?current->outputPrefix[i]:answer&&i<0x9A8?0:(u8)(i*29+current->seed*11+0x5A);if(buffer[i]!=expected)return 7;}
 for(i=4;i<12;i++)if(descriptor[i]!=current->descriptorBytes[i])return 8;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(bad):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text,dict(cases=len(rows),negative_controls=len(bad),signature='void*(void*,u8)',allocated_bytes=SIZE,cleared_bytes=0x960,untouched_bytes=90,all_seeded_output_bytes_checked=True,native_private_argument_home_mutations_claimed=False,bounded_allocator_and_SDK_providers=True)
def run_native(selected):
 text,counts=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,**counts,UBSan=True)
 return dict(profiles=reports,**counts)
