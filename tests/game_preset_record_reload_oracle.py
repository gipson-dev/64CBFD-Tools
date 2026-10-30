"""Preset reload: snapshot copy, live base pointer, bounded callbacks and native32."""
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
r=Path.cwd();o=r/'conker/build/game-preset-record-reload-match';F='func_150F5340';ENTRY=0x150F5340;BODY=212;SIZE=224;BANKS=(0x30000,0x40000);MARK=0x70000;SYMS=dict(D_800A1AB0=0x800A1AB0,D_800D3098=0x800D3098,func_151C970C=0x151C970C,func_1515F170=0x1515F170)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 pattern:int=0
 mutation:int=0
 seed:int=0
 bank:int=0
 phase:int=0
 alias:int=0
def preset(c):return tuple((6+i,16-i,(i*5+c.seed*7)%64,(0,1,63,6)[i%4])[c.pattern]for i in range(17))
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-512,128)}
 for base in BANKS:m.update({base+i:(i*29+0x59)&255 for i in range(64*52)})
 for i,v in enumerate(preset(c)):put(m,s['D_800A1AB0']+4*i,v)
 put(m,s['D_800D3098'],BANKS[c.bank]);put(m,MARK,0);put(m,MARK+4,0);return m
def effect(m,c,n,address,s=SYMS,home=None):
 home=STACK+c.phase-112 if home is None else home
 if c.mutation&1:
  for i in range(17):put(m,s['D_800A1AB0']+4*i,(i+n+c.seed+23)%64)
 if c.mutation&2:put(m,s['D_800D3098'],BANKS[(n+c.seed+1)&1])
 if c.mutation&4:put(m,u32(address+4),BANKS[1]if c.alias==3 else 0xB1000000+n)
 put(m,MARK,n+1)
 for i in range(4):put(m,home+4*i,0xB5000000+i)
def reference(initial,c,s=SYMS,home=None,saved=None):
 home=STACK+c.phase if home is None else home;frame=home-112;local=frame+40;m=dict(initial)
 if saved is not None:
  for reg,at in((17,24),(31,36),(19,32),(18,28),(16,20)):put(m,frame+at,saved[reg])
 # Mirror the observed five 12-byte iterations, then the two remaining words.
 for i in range(17):put(m,local+4*i,read(m,s['D_800A1AB0']+4*i))
 calls=[]
 for n in range(17):
  address=u32(read(m,s['D_800D3098'])+read(m,local+n*4)*52);calls.append((s['func_151C970C'],(1,address)));effect(m,c,n,address,s,frame)
 calls.append((s['func_1515F170'],(9,1)));put(m,MARK+4,0x90000001)
 for i in range(4):put(m,frame+4*i,0xB5000000+i)
 return m,calls
def cases():return tuple(Case(*a)for a in itertools.product(range(4),range(8),range(4),(0,1),(0,8)))
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=());self.before=self.r[:];self.before_f=self.f[:];self.reloaded=0
 def record_call(self,t):
  assert t in(self.syms['func_151C970C'],self.syms['func_1515F170'],ENTRY);a=tuple(self.arguments(0 if t==ENTRY else 2));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  a=self.calls[-1][1]
  if t==self.syms['func_151C970C']:assert a[0]==1;effect(self.memory,self.case,self.reloaded,a[1],self.syms,self.target_home-112);self.reloaded+=1
  else:
   assert t==self.syms['func_1515F170']and a==(9,1);put(self.memory,MARK+4,0x90000001)
   for i in range(4):put(self.memory,self.target_home-112+4*i,0xB5000000+i)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def linked(obj,label,s=SYMS,entry=ENTRY):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);raw=sections(p.with_suffix('.elf'))['.text'][1];return list(struct.unpack('>53I',raw[:BODY]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo)
def verify(m,initial,c,s=SYMS):
 want,calls=reference(initial,c,s,saved=m.before);assert(m.memory,m.calls)==(want,calls),c
 assert m.reloaded==17 and m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');programs=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];count=0;visited=set()
 for c in cases():
  initial=fixture(c);ms=[]
  for program in programs:m=Oracle(program,initial,c);m.run();verify(m,initial,c);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);visited.update(ms[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+BODY,4));prefixes=0
 for c in(Case(),Case(2,7,3,1,8)):
  initial=fixture(c);full=Oracle(programs[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   ms=[]
   for program in programs:
    m=Oracle(program,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing prefix',cut))
    ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);prefixes+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(D_800A1AB0=0x80007FF0+k*0x100000,D_800D3098=0x8001FFF0+k*0x100000,func_151C970C=0x10008000+k*0x100000,func_1515F170=0x10018000+k*0x100000);ps=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for c in(Case(pattern,mu,3,bank,8)for pattern,mu,bank in itertools.product(range(4),(0,7),(0,1))):
   initial=fixture(c,s);ms=[]
   for program in ps:m=Oracle(program,initial,c,s,entry);m.run();verify(m,initial,c,s);ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebased+=1
 aliases=0
 for kind,mu,phase in itertools.product((1,2,3),(0,1,2,4,7),(0,8)):
  c=Case(1,mu,0,0,phase,kind);s=dict(SYMS)
  if kind==1:s['D_800A1AB0']=BANKS[0]
  elif kind==2:s['D_800A1AB0']=STACK+phase-72
  else:s['D_800D3098']=BANKS[0]+4
  initial=fixture(c,s);ps=[linked(p,'alias-'+str(aliases)+'-'+str(i),s)for i,p in enumerate(objects)];ms=[]
  for program in ps:m=Oracle(program,initial,c,s);m.run();verify(m,initial,c,s);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);aliases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();jal=0x0C000000|((ENTRY>>2)&0x3FFFFFF);assert[at for at in range(0,len(rom),4)if rom[at:at+4]==struct.pack('>I',jal)]==[0x5289C];assert not any(rom[at:at+4]==struct.pack('>I',ENTRY)for at in range(0,len(rom),4));window=struct.unpack_from('>4I',rom,0x5289C);assert window==(jal,0,0x1000046F,0x24020001);cc=0
 for c in(Case(pattern,mu,3,bank,phase)for pattern,mu,bank,phase in itertools.product(range(4),(0,7),(0,1),(0,8))):
  initial=fixture(c);ms=[]
  for program in programs:
   code=dict(zip(range(ENTRY,ENTRY+BODY,4),program));code[0x150265B4]=0;m=Oracle(window,initial,c,entry=0x150253EC,connected=code);before=m.r[:];before[31]=0x150253F4;want,calls=reference(initial,c,saved=before);m.code=WindowCode(m.code,m);m.code.ends=(0x150265B4,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller boundary')
   assert(m.memory,m.calls,m.r[2])==(want,[(ENTRY,())]+calls,1);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);cc+=1
 return dict(cases=count,executions=count*3,covered_words=53,compiler_words=53,slot_words=56,alignment_words=3,frame=112,guards=0,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,guest_alias_cases=aliases,caller_windows=1,caller_window_words=4,caller_window_cases=cc,direct_JAL_sites=1,function_pointer_sites=0,result_overwritten_with_one=True,all_17_submissions_and_final_enable=True,original_and_C_full_state_equal=True,bounded_helpers=True,complete_helpers_or_parent_claimed=False,private_only=True,installed=False,matching_credit=0)
def controls(body):return dict(wrong_count=body.replace('index < 17','index < 16'),wrong_mode=body.replace('func_151C970C(1,','func_151C970C(2,'),wrong_category=body.replace('func_1515F170(9, 1)','func_1515F170(8, 1)'),wrong_enable=body.replace('func_1515F170(9, 1)','func_1515F170(9, 0)'),wrong_index=body.replace('preset.indices[index]','preset.indices[(index + 1) % 17]'),live_preset=body.replace('    RecordReloadPreset1227F0 preset = D_800A1AB0;\n','').replace('preset.indices[index]','D_800A1AB0.indices[index]'),cached_base=body.replace('u8 index;','ReloadRecord1227F0 *cached = D_800D3098;\n    u8 index;').replace('&D_800D3098[','&cached['),wrong_stride=body.replace('(s32)&D_800D3098[preset.indices[index]]','(s32)((u8 *)D_800D3098 + preset.indices[index] * 48)'),missing_final=body.replace('func_1515F170(9, 1);',';'))
def native_harness(selected):
 head,body=selected.split('/* Reload',1);body='/* Reload'+body;bad=controls(body);assert all(v!=body for v in bad.values());cs=[c for c in cases()if not c.phase];rows=['{'+','.join(str(x)+'u'for x in(c.pattern,c.mutation,c.seed,c.bank))+'}'for c in cs]
 text=head+r'''
_Static_assert(sizeof(void*)==4,"native32");
typedef struct{u32 pattern,mutation,seed,bank;}Fixture;static const Fixture*current;
static ReloadRecord1227F0 banks[2][64]__attribute__((aligned(8)));RecordReloadPreset1227F0 D_800A1AB0;ReloadRecord1227F0*D_800D3098;
static u32 snapshot[17],expectedPreset[17],markers[2][64],marked[2][64],calls,enables,bad,expectedBank;
static u32 value(u32 p,u32 i,u32 seed){static const u32 duplicate[4]={0,1,63,6};if(p==0)return 6+i;if(p==1)return 16-i;if(p==2)return(i*5+seed*7)%64;return duplicate[i%4];}
void func_151C970C(s32 mode,s32 address){u32 i,n=calls++,bank=expectedBank,index=n<17?snapshot[n]:0;if(n>=17||mode!=1||(u32)address!=(u32)&banks[bank][index]){bad=1;return;}if(current->mutation&1)for(i=0;i<17;i++)D_800A1AB0.indices[i]=(i+n+current->seed+23)%64;if(current->mutation&2){expectedBank=(n+current->seed+1)&1;D_800D3098=banks[expectedBank];}if(current->mutation&4)*(u32*)(banks[bank][index].bytes+4)=0xB1000000+n;}
void func_1515F170(s32 category,u8 enabled){if(category!=9||enabled!=1||calls!=17)bad=1;enables++;}
'''
 text+='\n'.join(v.replace(F,'test_'+k)for k,v in dict(selected=body,**bad).items());text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 text+=r'''
typedef void(*Reload)(void);
static int check(Reload fn){u32 f,i,j,b,n,bank;u8 expected;for(f=0;f<CASE_COUNT;f++){current=fixtures+f;calls=enables=bad=0;expectedBank=bank=current->bank;for(i=0;i<17;i++)snapshot[i]=expectedPreset[i]=D_800A1AB0.indices[i]=value(current->pattern,i,current->seed);for(b=0;b<2;b++)for(i=0;i<64;i++){markers[b][i]=marked[b][i]=0;for(j=0;j<52;j++)banks[b][i].bytes[j]=(u8)((i*52+j)*29+0x59);}for(n=0;n<17;n++){if(current->mutation&4){marked[bank][snapshot[n]]=1;markers[bank][snapshot[n]]=0xB1000000+n;}if(current->mutation&2)bank=(n+current->seed+1)&1;if(current->mutation&1)for(i=0;i<17;i++)expectedPreset[i]=(i+n+current->seed+23)%64;}D_800D3098=banks[current->bank];fn();if(bad||calls!=17||enables!=1||expectedBank!=bank||D_800D3098!=banks[bank])return 1;for(i=0;i<17;i++)if(D_800A1AB0.indices[i]!=expectedPreset[i])return 2;for(b=0;b<2;b++)for(i=0;i<64;i++)for(j=0;j<52;j++){expected=(u8)((i*52+j)*29+0x59);if(marked[b][i]&&j>=4&&j<8)expected=(u8)(markers[b][i]>>(8*(j-4)));if(banks[b][i].bytes[j]!=expected)return 3;}}return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,k in enumerate(bad):text+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');return text,dict(cases=len(rows),negative_controls=len(bad),signature='void(void)',all_preset_global_pointer_and_record_bytes_checked=True,all_17_arguments_and_final_enable_checked=True,source_snapshot_and_live_record_base_checked=True,guest_private_stack_aliases_not_portable_claimed=True)
def run_native(selected):
 text,counts=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,**counts,UBSan=True)
 return dict(profiles=reports,**counts)
