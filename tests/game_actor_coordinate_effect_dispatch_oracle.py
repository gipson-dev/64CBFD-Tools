"""Attachment effects: complete callback words, mixed float ABI and live post-call reads."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_coordinate_query_result_oracle import trunc
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-actor-coordinate-effect-dispatch-match';F='func_150D8A34';ENTRY=0x150D8A34;BODY=216;OWNER=0x30000;ALT=0x31000
SYMS=dict(D_800A0B30=0x800A0B30,D_800A0B34=0x800A0B34,func_150D88E0=0x150D88E0,func_151875E0=0x151875E0,func_15165F80=0x15165F80)
MATRIX=0x150A7960;TABLE=0x8008A0B4
@dataclass(frozen=True)
class Case:
 active:int=0x50000
 selector:int=3
 unused:int=0x87654321
 x:int=0x3FE00000
 y:int=0xC1080000
 z:int=0xBFE00000
 height:int=0x41280000
 scale:int=0x3DCCCCCD
 speed:int=0x3CF5C28F
 mutation:int=0
 phase:int=0
 owner:int=OWNER
 connected:int=0
def vector(c):return STACK+c.phase-12
def fixture(c,s=SYMS):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-768,512)}
 for j,base in enumerate((c.owner,ALT)):
  m.update({base+i:(i*29+j*13+0x59)&255 for i in range(0x340)});put(m,base+0x1D4,c.active);put(m,base+0x180,c.height if j==0 else 0x42060000)
 put(m,s['D_800A0B30'],c.scale);put(m,s['D_800A0B34'],c.speed);return m
def effect(m,c,stage,s=SYMS):
 if stage==0:
  if c.mutation&1:put(m,c.owner+0x180,0xC0B00000)
  if c.mutation&2:put(m,s['D_800A0B30'],0x3FC00000);put(m,s['D_800A0B34'],0xBE800000)
  if c.mutation&4:put(m,c.owner+0x1D4,0)
  if c.mutation&8:put(m,STACK+c.phase,ALT)
 elif stage==1:
  if c.mutation&16:put(m,vector(c),0xC29B8000);put(m,vector(c)+8,0x41BF0000);put(m,c.owner+0x180,0x41280000)
  if c.mutation&32:put(m,STACK+c.phase,ALT)
  if c.mutation&64:put(m,s['D_800A0B30'],0x7FC12345);put(m,s['D_800A0B34'],0x80000000)
def reference(initial,c,s=SYMS,entry=ENTRY):
 m=dict(initial);calls=[];words=();home=STACK+c.phase;v=vector(c);put(m,home+4,c.selector);put(m,home+8,c.unused)
 if not read(m,c.owner+0x1D4):return m,calls,words
 put(m,home,c.owner);selector=c.selector&255;calls.append((s['func_150D88E0'],(v,c.owner,selector)))
 if c.connected:
  ox,oz,bone={3:(0xC0E00000,0x41F00000,18),4:(0xC0800000,0x420C0000,21),5:(0x40A00000,0x41A00000,15),6:(0x40A00000,0x41F80000,24)}[selector];helperSP=home-128
  calls.append((MATRIX,((read(m,c.owner+0x1D4)+bone*64)&0xFFFFFFFF,ox,0,oz,helperSP+56,helperSP+52,helperSP+48)))
 for i,w in enumerate((c.x,c.y,c.z)):put(m,v+4*i,w)
 effect(m,c,0,s)
 calls.append((s['func_151875E0'],(read(m,v),read(m,v+4),read(m,v+8),30,15,7,read(m,s['D_800A0B30']),read(m,s['D_800A0B34']))))
 effect(m,c,1,s);owner=read(m,home);words=(read(m,v),bits(floating(read(m,owner+0x180))+4.0),read(m,v+8))
 calls.append((s['func_15165F80'],(0xFFFFFFFF,trunc(words[0]),trunc(words[1]),trunc(words[2]),4,50,0,255,0)))
 return m,calls,words
def public(m):return{a:b for a,b in m.items()if not STACK-768<=a<STACK+512}
def cases():
 fs=(0,0x80000000,0x3FE00000,0xBFE00000,0x477FFF80,0xC77FFF80,0x4EFFFFFF,0x4F000000,0xCF000000,0xCF000001,0x7F800000,0xFF800000,0x7FC12345,1,0x80000001,0x3F7FFFFF)
 rows=[Case(active=a,selector=s,unused=s^0x87654321,x=fs[i],z=fs[-i-1],height=fs[(i+3)%len(fs)],mutation=mu,phase=p)for a,s,mu,i,p in itertools.product((0,0x50000),(0,3,6,255,0xAABBCC04),(0,1,2,4,8,16,32,64,127),range(4),(0,8))]
 rows.extend(Case(active=a,selector=s,unused=s*0x01010101,phase=p)for a,s,p in itertools.product((0,0x50000),range(256),(0,8)))
 rows.extend(Case(x=x,y=fs[(i+5)%len(fs)],z=z,height=h,scale=fs[(i+7)%len(fs)],speed=fs[(i+9)%len(fs)],phase=p)for i,x in enumerate(fs)for z,h,p in itertools.product(fs,fs[::2],(0,8)))
 rows.extend(Case(selector=s,unused=u,phase=p)for s,u,p in itertools.product((0x7FFFFFFF,0x80000003,0xFFFFFFFF),(0,1,0x80000000,0xFFFFFFFF),(0,8)))
 return tuple(dict.fromkeys(rows))
def native_safe(c):
 if c.owner!=OWNER or c.phase or c.mutation&(8|32):return False
 _,_,words=reference(fixture(c),c)
 # All independently compiled negative controls must remain in the native C domain too.
 words=(*words,c.x,c.y,c.z,bits(floating(c.height)+4.0))
 return all(math.isfinite(floating(w))and -(2**31)<=floating(w)<2**31 for w in words)
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(c.owner,c.selector,c.unused));self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==13:
   prior=self.own_instruction;self.own_instruction=True;self.dispatched_word=w
   try:self.f[w>>6&31]=trunc(self.f[w>>11&31])
   finally:self.own_instruction=prior
  else:super().execute(w)
 def record_call(self,t):
  s=self.syms
  if t==s['func_151875E0']:a=(self.f[12],self.f[14],self.r[6],self.r[7],*(read(self.memory,self.r[29]+4*i)for i in range(4,8)))
  else:a=tuple(self.arguments({s['func_150D88E0']:3,s['func_15165F80']:9,MATRIX:7,ENTRY:3}[t]))
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  c=self.case;s=self.syms;a=self.calls[-1][1]
  if t==s['func_150D88E0']:
   assert a==(vector(c),c.owner,c.selector&255)
   for i,w in enumerate((c.x,c.y,c.z)):put(self.memory,a[0]+4*i,w)
   effect(self.memory,c,0,s)
  elif t==MATRIX:
   for p,w in zip(a[4:],(c.x,c.y,c.z)):put(self.memory,p,w)
   effect(self.memory,c,0,s)
  elif t==s['func_151875E0']:effect(self.memory,c,1,s)
  else:assert t==s['func_15165F80']
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0xA5000002
def linked(obj,label,s=SYMS,entry=ENTRY):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>54I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo)
def verify(m,initial,c,s=SYMS,entry=ENTRY):
 want,calls,_=reference(initial,c,s,entry);assert(public(m.memory),m.calls)==(public(want),calls),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]
 if calls:assert data(m.memory,vector(c),12)==data(want,vector(c),12)
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2];visited=set();count=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+BODY,4));prefixes=0
 for c in(Case(),Case(active=0),Case(mutation=127),Case(x=0x7FC12345,height=0x7F800000,phase=8)):
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
  s=dict(D_800A0B30=0x80007FF0+k*0x100000,D_800A0B34=0x8001FFF0+k*0x100000,func_150D88E0=0x10008000+k*0x10000,func_151875E0=0x10018000+k*0x10000,func_15165F80=0x10028000+k*0x10000);programs=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for active,selector,mu,phase in itertools.product((0,0x50000),(3,0xAABBCC04),(0,16,127),(0,8)):
   c=Case(active=active,selector=selector,mutation=mu,phase=phase);initial=fixture(c,s)
   for words in programs:m=Oracle(words,initial,c,s,entry);m.run();verify(m,initial,c,s,entry)
   rebased+=1
 aliases=0
 for component,mu,phase in itertools.product(range(3),(0,1,16,127),(0,8)):
  c=Case(owner=STACK+phase-12+4*component-0x180,mutation=mu,phase=phase);initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);aliases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();helper=dict(zip(range(0x150D88E0,0x150D8A20,4),struct.unpack_from('>80I',rom,0x105D90)));connected_count=0
 for selector,mu,phase in itertools.product((3,4,5,6),(0,1,2,4,8,16,32,127),(0,8)):
  c=Case(selector=selector,mutation=mu,phase=phase,connected=1);initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c,connected=helper);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);connected_count+=1
 # Actual dispatch windows reload the function from the two-word callback table.
 caller_rows=[]
 for pc,off,n,end in((0x15141B4C,0x16EFFC,5,0x15141B60),(0x15141BAC,0x16F05C,8,0x15141BCC)):
  window=list(struct.unpack_from('>%dI'%n,rom,off));caller_count=0
  for active,selector,unused,mu,phase in itertools.product((0,0x50000),(3,0xAABBCC04),(-1,0,32767),(0,16),(0,8)):
   c=Case(active=active,selector=selector,unused=unused&0xFFFFFFFF,mutation=mu,phase=phase);initial=fixture(c);put(initial,TABLE+8*8,ENTRY);put(initial,0x60000+14,unused,2);want,calls,_=reference(initial,c);machines=[]
   for words in ps:
    code=dict(zip(range(ENTRY,ENTRY+BODY,4),words));code[end]=0;m=Oracle(window,initial,c,entry=pc,connected=code);m.r[18]=c.owner;m.r[19]=c.selector;m.r[16]=TABLE;m.r[14]=TABLE+8*8;m.r[2]=0x60000;m.r[12]=8;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    if pc==0x15141B4C:m.case=replace(c,unused=0);expected=reference(initial,m.case)
    else:expected=(want,calls,())
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing dispatcher window boundary')
    assert(public(m.memory),m.calls)==(public(expected[0]),[(ENTRY,(c.owner,c.selector,m.case.unused))]+expected[1]);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);caller_count+=1
  caller_rows.append(dict(entry=hex(pc),ROM=hex(off),words=n,cases=caller_count,end=hex(end),callback_table=hex(TABLE),callback_index=8,full_parent_claimed=False))
 assert struct.unpack_from('>2I',rom,0x22EBB4)==(ENTRY,0xFFFFFFFF)
 return dict(cases=count,executions=count*3,covered_words=54,compiler_words=54,slot_words=55,alignment_words=1,frame=64,guards=0,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,guest_vector_height_alias_cases=aliases,original_coordinate_helper_words=80,connected_coordinate_cases=connected_count,helper_selector_domain='3..6',caller_windows=caller_rows,callback_table='D_8008A0B4',callback_index=8,callback_word_ROM='0x22EBB4',callback_word_VA='0x8008A0F4',literal_full_state_equal=True,invalid_truncation_model='low-word integer-indefinite only; no FCSR claim',native_float_to_int_requires_finite_in_range=True,private_only=True,installed=False,matching_credit=0)

import sys
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
q=sys.modules[__name__]
def controls(body):
 return dict(inverted_gate=body.replace('!= 0','== 0'),wrong_selector=body.replace('(u8)selector','(s8)selector'),wrong_effect_kind=body.replace('], 30, 15, 7','], 29, 15, 7'),wrong_height_increment=body.replace('+ 4.0f','+ 3.0f'),wrong_final_axis=body.replace('(s32)position[2]','(s32)position[1]'),wrong_priority=body.replace('50, 0, 255, 0','50, 0, 254, 0'),cached_height=body.replace('    f32 position[3];','    f32 position[3];\n    f32 cachedHeight = *(f32 *)(owner + 0x180);').replace('*(f32 *)(owner + 0x180) + 4.0f','cachedHeight + 4.0f'),repeated_gate=body.replace('        func_151875E0','        if (*(s32 *)(owner + 0x1D4) == 0) return;\n        func_151875E0'),cached_vector=body.replace('    f32 position[3];','    f32 position[3];\n    f32 cachedX, cachedZ;').replace('        func_151875E0','        cachedX = position[0]; cachedZ = position[2];\n        func_151875E0').replace('(s32)position[0]','(s32)cachedX').replace('(s32)position[2]','(s32)cachedZ'))

def native_harness(selected):
 head=selected[:selected.index('/* Use')];body=selected[selected.index('/* Use'):];bad=controls(body);assert all(x!=body for x in bad.values())
 text=head+r'''
_Static_assert(sizeof(void*)==4,"native32");
typedef struct {u32 active,selector,unused,x,y,z,height,scale,speed,mutation,count,call2[8],call3[9],finalHeight,finalActive,finalScale,finalSpeed;} Fixture;
static const Fixture*current;static u32 stage,bad;
static u8 actors[2][0x340] __attribute__((aligned(8))),before[2][0x340] __attribute__((aligned(8)));
static f32 *retained;
f32 D_800A0B30,D_800A0B34;
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
s32 func_150D88E0(f32*p,u8*owner,s32 selector){if(stage++||owner!=actors[0]||(u32)selector!=(current->selector&255))bad=1;retained=p;p[0]=real(current->x);p[1]=real(current->y);p[2]=real(current->z);
 if(current->mutation&1)*(f32*)(owner+0x180)=-5.5f;if(current->mutation&2){D_800A0B30=1.5f;D_800A0B34=-0.25f;}if(current->mutation&4)*(u32*)(owner+0x1D4)=0;return 1;}
s32 func_151875E0(f32 x,f32 y,f32 z,s32 kind,s32 a,s32 b,f32 scale,f32 speed){u32 v[8],i;v[0]=word(x);v[1]=word(y);v[2]=word(z);v[3]=(u32)kind;v[4]=(u32)a;v[5]=(u32)b;v[6]=word(scale);v[7]=word(speed);if(stage++!=1)bad=2;for(i=0;i<8;i++)if(v[i]!=current->call2[i])bad=3;
 if(current->mutation&16){retained[0]=-77.75f;retained[2]=23.875f;*(f32*)(actors[0]+0x180)=10.5f;}if(current->mutation&64){D_800A0B30=real(0x7FC12345);D_800A0B34=real(0x80000000);}return 0x12345678;}
s32 func_15165F80(s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,u8 h,s32 j){u32 v[9],i;v[0]=(u32)a;v[1]=(u32)b;v[2]=(u32)c;v[3]=(u32)d;v[4]=(u32)e;v[5]=(u32)f;v[6]=(u32)g;v[7]=h;v[8]=(u32)j;if(stage++!=2)bad=4;for(i=0;i<9;i++)if(v[i]!=current->call3[i])bad=5;return 0;}
'''
 text+='\n'.join(source.replace('func_150D8A34','test_'+name)for name,source in dict(selected=body,**bad).items());rows=[]
 def arr(values):return '{'+','.join('0x%Xu'%(x&0xFFFFFFFF)for x in values)+'}'
 for c in q.cases():
  if not q.native_safe(c):continue
  initial=q.fixture(c);want,calls,_=q.reference(initial,c);scalars=[c.active,c.selector,c.unused,c.x,c.y,c.z,c.height,c.scale,c.speed,c.mutation,len(calls)];second=calls[1][1]if calls else(0,)*8;third=calls[2][1]if calls else(0,)*9;final=[q.read(want,c.owner+0x180),q.read(want,c.owner+0x1D4),q.read(want,q.SYMS['D_800A0B30']),q.read(want,q.SYMS['D_800A0B34'])]
  rows.append('{'+','.join('0x%Xu'%(x&0xFFFFFFFF)for x in scalars)+','+arr(second)+','+arr(third)+','+','.join('0x%Xu'%x for x in final)+'}')
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 text+=r'''
typedef void(*Callback)(u8*,s32,s32);
static s32 check(Callback fn){u32 n,i,j;for(n=0;n<CASE_COUNT;n++){current=fixtures+n;stage=bad=0;retained=0;
 for(j=0;j<2;j++){for(i=0;i<0x340;i++)actors[j][i]=(u8)(i*29+j*13+0x59);*(u32*)(actors[j]+0x1D4)=current->active;*(u32*)(actors[j]+0x180)=j?0x42060000:current->height;for(i=0;i<0x340;i++)before[j][i]=actors[j][i];}
 D_800A0B30=real(current->scale);D_800A0B34=real(current->speed);fn(actors[0],(s32)current->selector,(s32)current->unused);
 if(bad||stage!=current->count||word(D_800A0B30)!=current->finalScale||word(D_800A0B34)!=current->finalSpeed)return 1;
 *(u32*)(before[0]+0x180)=current->finalHeight;*(u32*)(before[0]+0x1D4)=current->finalActive;for(j=0;j<2;j++)for(i=0;i<0x340;i++)if(actors[j][i]!=before[j][i])return 2;
 }return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(bad):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text,dict(cases=len(rows),negative_controls=len(bad),callback_signature='void(u8*,s32,s32)',conversion_domain='finite float32 values within signed32 range',private_argument_home_mutations_claimed=False,vector_lifetime_across_effect=True)

def run_native(selected):
 text,counts=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,**counts,UBSan=True)
 return dict(profiles=reports,**counts)
