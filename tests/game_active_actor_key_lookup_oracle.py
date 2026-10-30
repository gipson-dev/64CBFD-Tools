"""Bounded actor-key lookup proof: exact link, guest loads and native32 ABI."""
from pathlib import Path
from dataclasses import dataclass
import json,struct,subprocess,itertools
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_classifier_candidates import sections
r=Path.cwd();o=r/'conker/build/game-active-actor-key-lookup-match';F='func_1505EEF4';ENTRY=0x1505EEF4;BODY=220;BASE=0x800CC2D0;STRIDE=0x32C
@dataclass(frozen=True)
class Case:
 key:int=37
 slot:int=24
 second:int=-1
 state:int=1
 phase:int=0
 pattern:int=0

def cases():
 rows=[]
 for key,slot,phase in itertools.product(range(256),(-1,0,1,4,24,25),(0,8)):rows.append(Case(key,slot,phase=phase))
 for slot,state,phase in itertools.product(range(26),(0,1,0x100,0x80000000,0xFFFFFFFF),(0,8)):rows.append(Case(slot%256,slot,state=state,phase=phase))
 for slot,second,phase in itertools.product(range(25),(0,4,24,25),(0,8)):rows.append(Case(255,slot,second,state=0x80000000,phase=phase,pattern=1))
 for key,slot,phase in itertools.product((-2147483648,-1,256,511,2147483647),(-1,0,1,24,25),(0,8)):rows.append(Case(key,slot,phase=phase))
 return tuple(dict.fromkeys(rows))

def fixture(c,base=BASE):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for i in range(26):
  p=base+i*STRIDE;put(m,p,0 if c.pattern==0 else 1);m[p+0x13F]=(c.key+1)&255
 for i in (c.slot,c.second):
  if i>=0:put(m,base+i*STRIDE,c.state);m[base+i*STRIDE+0x13F]=c.key&255
 return m

def reference(m,c,base=BASE):
 for i in range(25):
  if read(m,base+i*STRIDE) and m[base+i*STRIDE+0x13F]==c.key:return base+i*STRIDE
 return 0

class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,entry=ENTRY,base=BASE,connected=None):
  super().__init__(words,memory,c,entry=entry,s={},arguments=(c.key&0xFFFFFFFF,),connected=connected);self.before=self.r[:]
 def record_call(self,t):
  assert t==ENTRY;args=(self.r[4],);self.calls.append((t,args));self.events.append(('CALL',t,args))
 def hook(self,t):raise AssertionError(('Unexpected provider',hex(t)))

def linked(obj,label,base=BASE,entry=ENTRY):
 p=o/label;s={'D_800CC2D0':base,'D_800CC5FC':base+STRIDE,'D_800CC40F':base+0x13F};p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(obj)],capture_output=True,check=True)
 return list(struct.unpack('>55I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))

def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo)

def verify(m,initial,c,base=BASE):
 assert m.r[2]==reference(initial,c,base),(c,hex(m.r[2]));assert m.memory==initial
 assert m.r[29]==m.before[29] and m.r[16:24]==m.before[16:24] and m.r[28]==m.before[28]
 assert not any(x[0]=='W'for x in m.trace)

def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o');programs=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1];visited=set();count=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in programs:
   m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1]);visited.update(machines[0].visits);count+=1
 expected=set(range(ENTRY,ENTRY+BODY,4))-{ENTRY+x for x in(0x58,0x7C,0xA0)};assert visited==expected,(sorted(expected-visited),sorted(visited-expected));prefixes=0
 for c in(Case(),Case(slot=-1),Case(slot=0),Case(slot=4,state=0),Case(key=-1,slot=24),Case(slot=1,second=24,pattern=1)):
  initial=fixture(c);full=Oracle(programs[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in programs:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access prefix',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1]);prefixes+=1
 rebased=0
 for k,base in enumerate((0x80007FF0,0x80018000,0x8002FFF0)):
  entry=(0x15001000,0x1F008000,0x1000FFF0)[k];ps=[linked(p,'guest-rebase-'+str(k)+'-'+str(i),base,entry)for i,p in enumerate(objects)];assert ps[0]==ps[1]
  for key,slot,phase in itertools.product((-1,0,128,255,256),(0,1,4,24,25,-1),(0,8)):
   c=Case(key,slot,phase=phase);initial=fixture(c,base)
   for words in ps:m=Oracle(words,initial,c,entry,base);m.run();verify(m,initial,c,base)
   rebased+=1
 # A first-slot hit needs no mapping for later records or its unrelated fields.
 c=Case(slot=0);m0=fixture(c);sparse={a:b for a,b in m0.items()if STACK-256<=a<STACK+256 or BASE<=a<BASE+4 or a==BASE+0x13F}
 for words in programs:m=Oracle(words,sparse,c);m.run();assert m.r[2]==BASE and m.memory==sparse
 rom=(r/'conker/conker.us.bin').read_bytes();caller_count=0;caller_rows=[]
 for pc,offset,kind in((0x15023890,0x50D40,'a3'),(0x150979D8,0xC4E88,'home')):
  window=list(struct.unpack_from('>2I',rom,offset));assert window[0]==0x0D417BBD;assert window[1]==(0x00E02025 if kind=='a3'else 0xAFA40018)
  for key,slot,phase in itertools.product((-1,0,128,255,256),(0,1,24,25,-1),(0,8)):
   c=Case(key,slot,phase=phase);initial=fixture(c);want=reference(initial,c);machines=[]
   for words in programs:
    code=dict(zip(range(ENTRY,ENTRY+BODY,4),words));code[pc+8]=0;m=Oracle(window,initial,c,entry=pc,connected=code)
    if kind=='a3':m.r[7]=key&0xFFFFFFFF
    m.code=WindowCode(m.code,m);m.code.ends=(pc+8,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing original caller boundary')
    assert m.r[2]==want
    memory=dict(initial)
    if kind=='home':put(memory,STACK+phase+24,key&0xFFFFFFFF)
    assert m.memory==memory;machines.append(m)
   assert state(machines[0])==state(machines[1]);caller_count+=1
  caller_rows.append(dict(entry=hex(pc),ROM=hex(offset),words=2,cases=50,full_parent_claimed=False))
 jal=0x0D417BBD;refs=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==jal];ptrs=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==ENTRY]
 report=dict(cases=count,executions=count*2,covered_words=len(visited),unreachable_offsets=[0x58,0x7C,0xA0],compiler_words=55,frame=0,guards=0,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,sparse_executions=2,caller_windows=caller_rows,caller_window_cases=caller_count,JAL_ROM_offsets=refs,aligned_pointer_words=ptrs,literal_full_state_equal=True,read_only=True,private_only=True,installed=False,matching_credit=0)
 return report


import sys
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
q=sys.modules[__name__]
def native_harness(selected):
 pre='#include <ultra64.h>\ntypedef s8 int8_t;\ntypedef struct { s32 interaction_state; u8 p04[0x123]; u8 unk127; u8 p128[0x17]; u8 unk13F; u8 p140[0x1EC]; } struct127;\n_Static_assert(sizeof(void*)==4,"native32");\n_Static_assert(sizeof(struct127)==0x32C,"stride");\n_Static_assert(__builtin_offsetof(struct127,unk13F)==0x13F,"key");\nstruct127 D_800CC2D0[26];\nstatic void fill(void*p,u8 value,u32 n){u8*b=p;u32 i;for(i=0;i<n;i++)b[i]=value;}\nstatic void copy(void*p,const void*q,u32 n){u8*b=p;const u8*a=q;u32 i;for(i=0;i<n;i++)b[i]=a[i];}\nstatic int different(const void*p,const void*q,u32 n){const u8*b=p,*a=q;u32 i;for(i=0;i<n;i++)if(b[i]!=a[i])return 1;return 0;}\n'
 rows=['{%d,%d,%d,0x%Xu,%d}'%(c.key,c.slot,c.second,c.state,c.pattern)for c in q.cases()]
 return pre+'\n'+selected+'\n'+'''
static struct { s32 key,slot,second; u32 state; int pattern; } cases[]={
'''+',\n'.join(rows)+r'''};
static int run(void) {
 unsigned n; int i,j; struct127 before[26]; struct127 *expected,*result;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++) {
  fill(D_800CC2D0,0xA5,sizeof(D_800CC2D0));
  for(i=0;i<26;i++) {D_800CC2D0[i].interaction_state=cases[n].pattern ? 1 : 0;D_800CC2D0[i].unk13F=(u8)(cases[n].key+1u);D_800CC2D0[i].unk127=(u8)(cases[n].key+2u);}
  for(j=0;j<2;j++) {i=j ? cases[n].second : cases[n].slot;if(i>=0) {D_800CC2D0[i].interaction_state=(s32)cases[n].state;D_800CC2D0[i].unk13F=(u8)cases[n].key;}}
  expected=NULL;for(i=0;i<25;i++)if(D_800CC2D0[i].interaction_state && (s32)D_800CC2D0[i].unk13F==cases[n].key) {expected=&D_800CC2D0[i];break;}
  copy(before,D_800CC2D0,sizeof(before));result=func_1505EEF4(cases[n].key);
  if(result!=expected || different(before,D_800CC2D0,sizeof(before))) return 1;
 }
 return 0;
}
'''

def controls(selected):
 return {
 'reserved-slot':selected.replace('index < 25','index < 26'),
 'skip-first-slot':selected.replace('actor = D_800CC2D0','actor = D_800CC2D0 + 1').replace('index = 0','index = 1'),
 'ignore-active-word':selected.replace('actor->interaction_state != 0','1'),
 'signed-key-byte':selected.replace('actor->unk13F == key','(int8_t)actor->unk13F == key'),
 'narrow-key-argument':selected.replace('s32 key','u8 key'),
 'wrong-key-field':selected.replace('actor->unk13F','actor->unk127'),
 'always-null':selected.replace('return actor;','return NULL;')}

def run_native(selected):
 report={};bad=controls(selected)
 for label,source in [('selected',selected),*bad.items()]:
  assert label=='selected'or source!=selected,label
  for profile in (('O0','O2','O3')if label=='selected'else('O2',)):
   p=o/('native-'+label+'-'+profile);p.with_suffix('.c').write_text(native_harness(source)+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'));command=native_command('-'+profile)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)];result=subprocess.run(command,capture_output=True,text=True);assert result.returncode==0 and not result.stdout and not result.stderr,result.stderr
   run=subprocess.run([str(p)],capture_output=True,text=True);assert run.returncode==(0 if label=='selected'else 1),(label,run.returncode,run.stdout,run.stderr);assert 'runtime error:'not in run.stderr
   report[label+'-'+profile]=dict(exit=run.returncode,stdout=run.stdout,stderr=run.stderr)
 return dict(cases=len(q.cases()),profiles=report,negative_controls=len(bad),UBSan=True)
