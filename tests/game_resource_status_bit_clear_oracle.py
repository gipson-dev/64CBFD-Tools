"""Resource status and 64-bit row masks; original and guarded literal states."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,re,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-resource-status-bit-clear-match';F='func_150A2864';ENTRY=0x150A2864;BODY=220;RECORDS=0x50000;CALLERBYTE=0x70000
SYMS=dict(D_800D3094=0x800D3094,D_800D3098=0x800D3098,D_800D30F0=0x800D30F0,D_800D3270=0x800D3270,__ll_lshift=0x100268A4)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 identity:int=65
 status:int=1
 count:int=192
 seed:int=0
 phase:int=0
 alias:int=0
def record(c,s):
 if c.alias==1:return u32(s['D_800D30F0']+8-20-(c.identity&4095)*52)
 if c.alias==2:return u32(s['D_800D3094']+3-20-(c.identity&4095)*52)
 return RECORDS
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,512)};target=u32(record(c,s)+(c.identity&4095)*52)
 m.update({u32(target+i):(i*29+c.seed*11+0x59)&255 for i in range(-32,96)})
 for i in range(112):put(m,s['D_800D30F0']+8*i,((0xFEDCBA9876543210^(i*0x1030507090B0D0F)^(c.seed*0x1111111111111111))&((1<<64)-1)),8)
 put(m,s['D_800D3094'],c.count);put(m,s['D_800D3098'],record(c,s));m[CALLERBYTE]=c.identity&255;return m
def reference(initial,c,s=SYMS):
 m=dict(initial);identity=c.identity&4095;calls=[]
 if identity<read(m,s['D_800D3094']):m[u32(read(m,s['D_800D3098'])+52*identity+20)]=c.status&255
 if u32(c.status)==1:
  for i in range(16):
   calls.append((s['__ll_lshift'],(0,1,0,identity&63)));at=s['D_800D30F0']+24*i+8*(identity>>6);put(m,at,read(m,at,8)&~(1<<(identity&63)),8)
 return m,calls
def public(m):return{a:b for a,b in m.items()if not STACK-512<=a<STACK+512}
def cases():
 rows=[Case(identity=(0x12345000|i),count=0,seed=i%4)for i in range(4096)]
 rows.extend(Case(identity=i,status=st,count=n,seed=seed,phase=phase)for i,st,n,seed,phase in itertools.product((0,1,31,32,63,64,65,127,128,191,192,4095,0xFFFFFFFF),(0,1,2,257,0xFFFFFFFF),(0,1,192,0xFFFFFFFF),(0,3),(0,8)))
 rows.extend(Case(identity=i,status=st,count=n,seed=seed)for i,st,n,seed in itertools.product(range(192),(0,1,257,0xFFFFFFFF),(0,192,0xFFFFFFFF),(0,3)))
 return tuple(dict.fromkeys(rows))
def native_safe(c):return(c.identity&4095)<192 and not c.phase and not c.alias
class Oracle(FactoryOracle):
 def execute(self,word):
  if word>>26==0 and word&63==39:
   self.r[word>>11&31]=u32(~(self.r[word>>21&31]|self.r[word>>16&31]));self.r[0]=0;return
  return super().execute(word)
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(c.identity,c.status));self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):
  assert t in(self.syms['__ll_lshift'],ENTRY);a=tuple(self.arguments(4 if t==self.syms['__ll_lshift']else 2));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert t==self.syms['__ll_lshift'];a=self.calls[-1][1];assert a[0:3]==(0,1,0)and 0<=a[3]<64
  # Bounded SDK model: argument-home stores and split 64-bit result. Original
  # MIPS-III helper instructions are not executed by this 32-bit interpreter.
  for i,v in enumerate(a):self.put(self.r[29]+4*i,v,4)
  result=1<<a[3];self.r[2]=result>>32;self.r[3]=result&0xFFFFFFFF
  for reg in(1,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
def linked(obj,label,s=SYMS,entry=ENTRY):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>55I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo)
def verify(m,initial,c,s=SYMS):
 want,calls=reference(initial,c,s);assert(public(m.memory),m.calls)==(public(want),calls),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'qualified-padded.o',o/'selected-final.o');ps=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[1];visited=set();count=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+BODY,4));prefixes=0
 for c in(Case(status=0),Case(identity=191,status=1)):
  initial=fixture(c);full=Oracle(ps[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in ps[:2]:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing prefix',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1]);prefixes+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(D_800D3094=0x80007FF0+k*0x100000,D_800D3098=0x8001FFF0+k*0x100000,D_800D30F0=0x8002FFF0+k*0x100000,D_800D3270=0x80030170+k*0x100000,__ll_lshift=0x10008000+k*0x100000);programs=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for identity,status,limit in itertools.product((0,31,32,63,64,191),(0,1,257),(0,192)):
   c=Case(identity=identity,status=status,count=limit);initial=fixture(c,s);machines=[]
   for words in programs:m=Oracle(words,initial,c,s,entry);m.run();verify(m,initial,c,s);machines.append(m)
   assert state(machines[0])==state(machines[1]);rebased+=1
 aliases=0
 for alias,identity,status in itertools.product((1,2),(0,65,191),(0,1,257)):
  c=Case(identity=identity,status=status,alias=alias);initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1]);aliases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();windows=[]
 for asmfile in('10B7D0.s','10CD70.s','1188E0.s','CD860.s'):
  asm=(r/'conker/asm'/asmfile).read_text()
  for match in re.finditer(r'/\* ([0-9A-F]+) ([0-9A-F]+) 0D428A19 \*/  jal\s+func_150A2864',asm):
   off=int(match[1],16);pc=int(match[2],16);words=struct.unpack_from('>2I',rom,off);end=pc+8;cc=0;parent=re.findall(r'^glabel (\w+)',asm[:match.start()],re.M)[-1]
   for identity,status in itertools.product((0,31,32,65,191),(0,1,257)):
    if words[1]==0x92240000:actual=Case(identity=identity,status=status)
    else:actual=Case(identity=identity,status=0 if words[1]==0x00002825 else 1);assert words[1]in(0x00002825,0x24050001)
    initial=fixture(actual);machines=[]
    for program in ps:
     code=dict(zip(range(ENTRY,ENTRY+BODY,4),program));code[end]=0;m=Oracle(words,initial,actual,entry=pc,connected=code);m.r[17]=CALLERBYTE;m.code=WindowCode(m.code,m);m.code.ends=(end,)
     try:m.run()
     except WindowBoundary:pass
     else:raise AssertionError('Missing caller boundary')
     want,calls=reference(initial,actual);assert(public(m.memory),m.calls)==(public(want),[(ENTRY,(actual.identity,actual.status))]+calls);machines.append(m)
    assert state(machines[0])==state(machines[1]);cc+=1
   windows.append(dict(entry=hex(pc),ROM=hex(off),words=2,cases=cc,end=hex(end),assembly_file='conker/asm/'+asmfile,caller=parent,delay_word=hex(words[1]),A0_precondition='identity already in A0'if words[1]!=0x92240000 else 'unsigned byte through S1',A1_precondition='full status already in A1'if words[1]==0x92240000 else 'constant zero/one in delay',full_parent_claimed=False))
 assert len(windows)==6
 return dict(cases=count,executions=count*3,covered_words=55,compiler_words=55,slot_words=55,alignment_words=0,frame=64,guards=10,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,guest_alias_cases=aliases,caller_windows=windows,original_and_normalized_literal_full_state_equal=True,raw_C_public_memory_and_calls_equal=True,raw_C_volatile_register_or_interrupted_private_stack_equality_claimed=False,SDK_helper_is_bounded_provider=True,SDK_original_instructions_executed=False,private_only=True,installed=False,matching_credit=0)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def controls(body):
 return dict(wrong_ID_mask=body.replace('0xFFF','0x7F'),signed_count=body.replace('(u32)D_800D3094','D_800D3094').replace('identity < D_800D3094','(s32)identity < D_800D3094'),wrong_status_byte=body.replace('[0x14]','[0x15]'),low_byte_gate=body.replace('status == 1','(u8)status == 1'),wrong_bit_mask=body.replace('0x3F','0x1F'),wrong_word=body.replace('identity >> 6','identity >> 5'),wrong_stride=body.replace('row += 3','row += 6'),wrong_bit_operation=body.replace('row[word] & ~','row[word] | ~'),missing_record_store=body.replace('((u8 *)&D_800D3098[identity])[0x14] = status;',';'))
def initial_word(i,seed):return(0xFEDCBA9876543210^(i*0x1030507090B0D0F)^(seed*0x1111111111111111))&((1<<64)-1)
def native_harness(selected):
 head,body=selected.split('/* Set',1);body='/* Set'+body;bad=controls(body);assert all(v!=body for v in bad.values());rows=[c for c in cases()if native_safe(c)]
 text=head+r'''
_Static_assert(sizeof(void*)==4,"native32");_Static_assert(sizeof(GeneratedCDE80Record)==52,"record stride");
typedef struct{u32 identity,status,count,seed;}Fixture;
static GeneratedCDE80Record records[192];GeneratedCDE80Record *D_800D3098=records;s32 D_800D3094;u64 D_800D30F0[112];
__asm__(".globl D_800D3270\n.set D_800D3270,D_800D30F0+384");
static u64 initial(u32 i,u32 seed){return 0xFEDCBA9876543210ULL^((u64)i*0x1030507090B0D0FULL)^((u64)seed*0x1111111111111111ULL);}
'''
 text+='\n'.join(v.replace(F,'test_'+k)for k,v in dict(selected=body,**bad).items());text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{%su,%su,%su,%su}'%(c.identity,u32(c.status),u32(c.count),c.seed)for c in rows)+'\n};\n'
 text+=r'''
typedef void(*Update)(u32,s32);
static s32 check(Update fn){u32 n,i,id;const Fixture*c;u8 expected;u64 word;for(n=0;n<CASE_COUNT;n++){c=fixtures+n;id=c->identity&4095;D_800D3094=(s32)c->count;D_800D3098=records;
 for(i=0;i<sizeof(records);i++)((u8*)records)[i]=(u8)(i*29+c->seed*11+0x59);for(i=0;i<112;i++)D_800D30F0[i]=initial(i,c->seed);
 fn(c->identity,(s32)c->status);if(D_800D3094!=(s32)c->count||D_800D3098!=records)return 1;
 for(i=0;i<sizeof(records);i++){expected=(u8)(i*29+c->seed*11+0x59);if(id<c->count&&i==id*52+20)expected=(u8)c->status;if(((u8*)records)[i]!=expected)return 2;}
 for(i=0;i<112;i++){word=initial(i,c->seed);if(c->status==1&&i>=id/64&&i-id/64<48&&(i-id/64)%3==0)word&=~(1ULL<<(id&63));if(D_800D30F0[i]!=word)return 3;}
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,k in enumerate(bad):text+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text,dict(cases=len(rows),negative_controls=len(bad),signature='void(u32,s32)',native_identity_domain='masked0..191',native_table_words=112,actual_sentinel_alias_offset=384,all_record_and_table_bytes_checked=True,pure_C_shift_no_provider_calls=True)
def run_native(selected):
 text,counts=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,**counts,UBSan=True)
 return dict(profiles=reports,**counts)
