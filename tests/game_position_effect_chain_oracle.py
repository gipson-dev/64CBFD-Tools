"""Captured actor coordinates, unsigned random remainder and three effect providers."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=Path.cwd();o=r/'conker/build/game-position-effect-chain-match';F='func_150B2494';ENTRY=0x150B2494;BODY=220;ACTOR=0x30000;TABLE=0x8008A0B4
SYMS=dict(func_150ADA20=0x150ADA20,func_1514C678=0x1514C678,func_151D5404=0x151D5404,func_151D3FF4=0x151D3FF4)
@dataclass(frozen=True)
class Case:
 rng:int=0x87654321
 x:int=0x3F800000
 y:int=0xC1080000
 z:int=0x80000000
 mutation:int=0
 phase:int=0
 unused1:int=0xAABBCC09
 unused2:int=0xFFFFFFFF
 actor:int=ACTOR
def vector(c):return STACK+c.phase-12
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)};m.update({c.actor+i:(i*29+0x59)&255 for i in range(0x240)})
 for a,w in zip((0x14,0x180,0x1C),(c.x,c.y,c.z)):put(m,c.actor+a,w)
 return m
def effect(m,c,stage):
 if stage==0:
  if c.mutation&1:
   for a,w in zip((0x14,0x180,0x1C),(0x41280000,0xC0200000,0x7FC54321)):put(m,c.actor+a,w)
  if c.mutation&2:put(m,vector(c),0xC29B8000)
 elif stage==1:
  if c.mutation&4:put(m,c.actor+0x14,0x42060000)
  if c.mutation&8:put(m,vector(c)+4,0x3E800000);put(m,vector(c)+8,0x41BF0000)
 elif stage==2:
  if c.mutation&16:
   for i,w in enumerate((0xC0E00000,0x3FC00000,0x80000000)):put(m,vector(c)+4*i,w)
  if c.mutation&32:put(m,STACK+c.phase+4,0xDEADBEEF);put(m,STACK+c.phase+8,0x80000000)
def vec(m,c):return tuple(read(m,vector(c)+4*i)for i in range(3))
def reference(initial,c,s=SYMS):
 m=dict(initial);v=vector(c);home=STACK+c.phase;put(m,home+4,c.unused1);put(m,home+8,c.unused2)
 for i,a in enumerate((0x14,0x180,0x1C)):put(m,v+4*i,read(m,c.actor+a))
 calls=[(s['func_150ADA20'],())];effect(m,c,0)
 calls.append((s['func_1514C678'],(*vec(m,c),0x43070000,0,255,c.rng%15+27,7,0,0,0,255)));effect(m,c,1)
 calls.append((s['func_151D5404'],(v,0x44BBC000,0x453B8000,0x39AEC33E,12,15,255,0)));observations=[vec(m,c)];effect(m,c,2)
 calls.append((s['func_151D3FF4'],(v,255,0)));observations.append(vec(m,c));return m,calls,observations
def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
def cases():
 floats=(0,0x80000000,1,0x80000001,0x3F800000,0xBF800000,0x477FFF80,0xC77FFF80,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
 randoms=(0,1,14,15,16,29,30,0x7FFFFFFF,0x80000000,0x80000001,0xFFFFFFFF)
 rows=[Case(rng=n,x=floats[i],y=floats[(i+3)%len(floats)],z=floats[-i-1],mutation=mu,phase=p,unused1=n^0xAABBCC09,unused2=n^0x87654321)for n,i,mu,p in itertools.product(randoms,range(len(floats)),(0,1,4,16,21,63),(0,8))]
 rows.extend(Case(rng=n,mutation=mu)for n,mu in itertools.product(range(256),(0,21)))
 return tuple(dict.fromkeys(rows))
def native_safe(c):return c.actor==ACTOR and not c.phase and not c.mutation&(2|8)
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(c.actor,c.unused1,c.unused2));self.before=self.r[:];self.before_f=self.f[:];self.observations=[]
 def record_call(self,t):
  s=self.syms
  if t==s['func_1514C678']:a=(self.f[12],self.f[14],self.r[6],self.r[7],*(read(self.memory,self.r[29]+4*i)for i in range(4,12)))
  else:a=tuple(self.arguments({s['func_150ADA20']:0,s['func_151D5404']:8,s['func_151D3FF4']:3,ENTRY:3}[t]))
  self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t in(s['func_151D5404'],s['func_151D3FF4']):self.observations.append(tuple(read(self.memory,a[0]+4*i)for i in range(3)))
 def hook(self,t):
  stage={self.syms['func_150ADA20']:0,self.syms['func_1514C678']:1,self.syms['func_151D5404']:2,self.syms['func_151D3FF4']:3}[t];effect(self.memory,self.case,stage)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=self.case.rng if stage==0 else 0xA5000002
def linked(obj,label,s=SYMS,entry=ENTRY):
 text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>55I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.observations)
def verify(m,initial,c,s=SYMS):
 want,calls,observations=reference(initial,c,s);assert(public(m.memory),m.calls,m.observations)==(public(want),calls,observations),c
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]
 assert vec(m.memory,c)==vec(want,c)
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');ps=[linked(p,'guest-program-'+str(i))for i,p in enumerate(objects)];assert ps[0]==ps[1]==ps[2];visited=set();count=0
 for c in cases():
  initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+BODY,4));prefixes=0
 for c in(Case(),Case(mutation=63,phase=8)):
  initial=fixture(c);full=Oracle(ps[0],initial,c);full.run()
  for cut in range(full.all_accesses):
   machines=[]
   for words in ps:
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing prefix',cut))
    machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);prefixes+=1
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s={name:0x10008000+0x10000*j+k*0x100000 for j,name in enumerate(SYMS)};programs=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for rng,mu,phase in itertools.product((0,14,15,0x80000000,0xFFFFFFFF),(0,21,63),(0,8)):
   c=Case(rng=rng,mutation=mu,phase=phase);initial=fixture(c);machines=[]
   for words in programs:m=Oracle(words,initial,c,s,entry);m.run();verify(m,initial,c,s);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);rebased+=1
 aliases=0
 for field,component,mu in itertools.product((0x14,0x180,0x1C),range(3),(0,21,63)):
  c=Case(actor=STACK-12+4*component-field,mutation=mu)
  if {c.actor+a for a in(0x14,0x180,0x1C)}&{STACK-20,STACK+4,STACK+8}:continue
  initial=fixture(c);machines=[]
  for words in ps:m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);aliases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>2I',rom,0x22EBC4)==(ENTRY,0xFFFFFFFF);caller_rows=[]
 for pc,off,n,end,kind in((0x15027364,0x54814,3,0x15027370,'direct'),(0x15141B4C,0x16EFFC,5,0x15141B60,'table'),(0x15141BAC,0x16F05C,8,0x15141BCC,'table')):
  window=list(struct.unpack_from('>%dI'%n,rom,off));cc=0
  for rng,mu,unused,phase in itertools.product((0,0x80000000,0xFFFFFFFF),(0,21),(-1,32767),(0,8)):
   c=Case(rng=rng,mutation=mu,unused1=9,unused2=(0 if pc==0x15141B4C else unused&0xFFFFFFFF),phase=phase);initial=fixture(c);put(initial,TABLE+10*8,ENTRY);put(initial,0x60000+14,c.unused2,2);machines=[]
   if kind=='direct':put(initial,STACK+c.phase+0x764,c.actor)
   for words in ps:
    code=dict(zip(range(ENTRY,ENTRY+BODY,4),words));code[end]=0;m=Oracle(window,initial,c,entry=pc,connected=code);m.r[18]=c.actor;m.r[19]=c.unused1;m.r[16]=TABLE;m.r[14]=TABLE+10*8;m.r[2]=0x60000;m.r[12]=10
    if kind=='direct':m.r[5]=9;put(m.memory,m.r[29]+0x764,c.actor);m.case=Case(**dict(c.__dict__,unused2=0xFFFFFFFF))
    m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing caller boundary')
    want,calls,observations=reference(initial,m.case);assert(public(m.memory),m.calls,m.observations)==(public(want),[(ENTRY,(c.actor,c.unused1,m.case.unused2))]+calls,observations);machines.append(m)
   assert state(machines[0])==state(machines[1])==state(machines[2]);cc+=1
  caller_rows.append(dict(entry=hex(pc),ROM=hex(off),words=n,cases=cc,end=hex(end),kind=kind,full_parent_claimed=False))
 return dict(cases=count,executions=count*3,covered_words=55,compiler_words=55,slot_words=55,alignment_words=0,frame=72,guards=0,access_prefix_pairs=prefixes,rebase_layouts=3,rebase_cases=rebased,guest_actor_vector_alias_cases=aliases,caller_windows=caller_rows,callback_table='D_8008A0B4',callback_index=10,callback_word_ROM='0x22EBC4',literal_full_state_equal=True,opaque_PRNG_and_effect_providers=True,private_only=True,installed=False,matching_credit=0)

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def controls(body):
 return dict(wrong_height=body.replace('actor + 0x180','actor + 0x1C'),wrong_scale=body.replace('135.0f','134.0f'),wrong_modulus=body.replace('% 15','% 16'),wrong_random_base=body.replace('+ 27','+ 26'),signed_remainder=body.replace('(u32)func_150ADA20()','func_150ADA20()'),wrong_priority=body.replace('0, 255, (u32)','0, 254, (u32)'),wrong_linear_scale=body.replace('3000.0f','2999.0f'),late_snapshot=body.replace('    f32 position[3];','    f32 position[3];\n    u32 rng = (u32)func_150ADA20();').replace('(u32)func_150ADA20() % 15','rng % 15'),cached_vector=body.replace('    f32 position[3];','    f32 position[3];\n    f32 cached[3];').replace('    func_151D5404(position','    cached[0]=position[0]; cached[1]=position[1]; cached[2]=position[2];\n    func_151D5404(position').replace('func_151D3FF4(position','func_151D3FF4(cached'))
def native_harness(selected):
 head=selected[:selected.index('/* Capture')];body=selected[selected.index('/* Capture'):];bad=controls(body);assert all(x!=body for x in bad.values())
 text=head+r'''
_Static_assert(sizeof(void*)==4,"native32");
typedef struct{u32 rng,x,y,z,mutation,unused1,unused2,first[12],second[8],third[3],vec1[3],vec2[3],final[3];} Fixture;
static const Fixture *current;static u32 stage,bad;static f32 *retained;
static u8 actor[0x240] __attribute__((aligned(8))),before[0x240];
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
s32 func_150ADA20(void){if(stage++)bad=1;if(current->mutation&1){*(f32*)(actor+0x14)=10.5f;*(f32*)(actor+0x180)=-2.5f;*(f32*)(actor+0x1C)=real(0x7FC54321);}return(s32)current->rng;}
void func_1514C678(f32 x,f32 y,f32 z,f32 scale,s16 a,s16 b,s16 c,u8 d,s32 e,f32 f,void*g,u8 h){u32 v[12]={word(x),word(y),word(z),word(scale),(u32)a,(u32)b,(u32)c,d,(u32)e,word(f),(u32)g,h},i;if(stage++!=1)bad=2;for(i=0;i<12;i++)if(v[i]!=current->first[i])bad=3;if(current->mutation&4)*(f32*)(actor+0x14)=33.5f;}
void func_151D5404(f32*p,f32 a,f32 b,f32 c,s32 d,s32 e,s32 f,s32 g){u32 v[8]={0,word(a),word(b),word(c),(u32)d,(u32)e,(u32)f,(u32)g},i;if(stage++!=2)bad=4;for(i=1;i<8;i++)if(v[i]!=current->second[i])bad=5;for(i=0;i<3;i++)if(word(p[i])!=current->vec1[i])bad=6;retained=p;if(current->mutation&16){p[0]=-7.0f;p[1]=1.5f;p[2]=real(0x80000000);}}
void func_151D3FF4(f32*p,u8 a,s32 b){u32 i;if(stage++!=3||p!=retained||a!=255||b)bad=7;for(i=0;i<3;i++)if(word(p[i])!=current->vec2[i])bad=8;}
'''
 text+='\n'.join(source.replace(F,'test_'+name)for name,source in dict(selected=body,**bad).items());rows=[]
 arr=lambda values:'{'+','.join('0x%Xu'%(x&0xFFFFFFFF)for x in values)+'}'
 for c in cases():
  if not native_safe(c):continue
  want,calls,observations=reference(fixture(c),c);values=(c.rng,c.x,c.y,c.z,c.mutation,c.unused1,c.unused2)
  rows.append('{'+','.join('0x%Xu'%(x&0xFFFFFFFF)for x in values)+','+','.join(map(arr,(calls[1][1],calls[2][1],calls[3][1],observations[0],observations[1],tuple(read(want,c.actor+a)for a in(0x14,0x180,0x1C)))))+'}')
 text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join(rows)+'\n};\n'
 text+=r'''
typedef void(*Callback)(u8*,s32,s32);
static s32 check(Callback fn){u32 n,i;for(n=0;n<CASE_COUNT;n++){current=fixtures+n;stage=bad=0;retained=0;for(i=0;i<0x240;i++)actor[i]=(u8)(i*29+0x59);*(u32*)(actor+0x14)=current->x;*(u32*)(actor+0x180)=current->y;*(u32*)(actor+0x1C)=current->z;for(i=0;i<0x240;i++)before[i]=actor[i];fn(actor,(s32)current->unused1,(s32)current->unused2);if(bad||stage!=4)return 1;*(u32*)(before+0x14)=current->final[0];*(u32*)(before+0x180)=current->final[1];*(u32*)(before+0x1C)=current->final[2];for(i=0;i<0x240;i++)if(actor[i]!=before[i])return 2;}return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(bad):text+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return text,dict(cases=len(rows),negative_controls=len(bad),callback_signature='void(u8*,s32,s32)',native_private_stack_mutations_claimed=False,vector_live_after_provider=True,actor_snapshot_before_PRNG=True)
def run_native(selected):
 text,counts=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,**counts,UBSan=True)
 return dict(profiles=reports,**counts)
