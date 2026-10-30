"""Distance-triggered angle blend: bounded float32, original providers and caller windows."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,math,struct,subprocess
from tools.experiments import game_distance_angle_blend_match as source
from tools.tests.test_game_angle_blend_update import AngleOracle,angle_delta
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
r=Path.cwd();o=r/source.BUILD;F=source.FUNCTION;ENTRY=source.ENTRY
ACTOR,ALT,ORIENT,UPDATE,ANGLE,FLAG,STEP,FINAL=0x30000,0x34000,0x15123A54,0x1512C150,0x15048A70,0x800C3671,0x800A3694,0x800A3698
SYMS=dict(func_15123A54=ORIENT,func_1512C150=UPDATE)
OTHER=(0x1512B100,0x1512C20C,0x1512BB10)
u32=lambda v:v&0xFFFFFFFF
f32=lambda v:floating(bits(v))
COORDS=tuple(tuple(bits(v)for v in row)for row in((0,0,0,0),(41,0,0,0),(42,0,0,0),(43,0,0,0),(3,4,0,0),(-30,30,0,0),(100000,100000,99970,99970),(-5,0,-47,0)))+((bits(42)-1,0,0,0),(bits(42)+1,0,0,0),(1,0,0,0),(0x80000000,0,0,0))
HEADINGS=(0,0x80000000,bits(180)-1,bits(180),bits(180)+1,bits(-180),0x7F800000,0xFF800000,0x7FC12345,0x7FA12345)
@dataclass(frozen=True)
class Case:
 kind:int=0
 heading:int=0
 coords:tuple=COORDS[0]
 phase_bits:int=0x3F000000
 current:int=0x420C0000
 target:int=0xC32C0000
 flags:int=0x80000001
 mutation:int=0
 phase:int=0
 tag:int=1
 window_flip:int=-1

def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,1024)}
 for p in(ACTOR,ALT):m.update({p+i:(i*13+0xA5)&255 for i in range(-16,0x920)})
 for p in(ACTOR,ALT):
  for off,v in((0x2C,c.kind),(0x390,c.heading),(0x370,0x12345678),(0x374,bits(15)),(0x384,c.current),(0x37C,c.target),(0x5CC,c.phase_bits),(0x240,c.flags)):
   put(m,p+off,u32(v))
  for off,v in zip((0x2F8,0x300,0x2BC,0x2C4),c.coords):put(m,p+off,v)
  put(m,p+0x23C,c.tag,1)
 put(m,FLAG,1,1);put(m,STEP,0x3BC49BA6);put(m,FINAL,0x4479C000);return m

def public(m):return{p:v for p,v in m.items()if not STACK-2048<=p<STACK+1024}

def mutation(m,c,p,home):
 if c.mutation&1:
  for off,v in((0x384,bits(123)),(0x5CC,bits(.995)),(0x240,0xA5A50001),(0x37C,bits(720))):put(m,p+off,v)
 if c.mutation&2:put(m,home,ALT)

def blend(m,p):
 phase=bits(floating(read(m,p+0x5CC))+floating(read(m,STEP)));phase=bits(1.)if floating(phase)>1 else phase;put(m,p+0x5CC,phase)
 if floating(phase)==1:
  put(m,p+0x384,read(m,FINAL));put(m,p+0x240,read(m,p+0x240)&0xFFFFFFFD);return[]
 a=(read(m,p+0x384),read(m,p+0x37C));delta=angle_delta(*a);put(m,p+0x384,bits(floating(read(m,p+0x384))+f32(floating(delta)*floating(phase))));return[(ANGLE,a)]

def reference(initial,c,s=SYMS,connected=False,p=ACTOR,home=None):
 m=dict(initial);home=STACK+c.phase if home is None else home;calls=[];direction=2. if floating(read(m,p+0x390))<180 else-2.
 if read(m,p+0x2C)not in(0x40,0x80):
  x=f32(floating(read(m,p+0x2F8))-floating(read(m,p+0x2BC)));z=f32(floating(read(m,p+0x300))-floating(read(m,p+0x2C4)))
  d=bits(math.sqrt(f32(f32(x*x)+f32(z*z))));put(m,p+0x370,d)
  if floating(d)<42:
   put(m,p+0x384,bits(floating(read(m,p+0x37C))-f32(45.*direction)));put(m,p+0x5CC,0);calls.append((s['func_15123A54'],(p,)))
   if connected:put(m,p+0x600,0,1);put(m,p+0x604,read(m,p+0x374))
   else:mutation(m,c,p,home);p=ALT if c.mutation&2 else p
   put(m,p+0x240,read(m,p+0x240)|2)
 calls.append((s['func_1512C150'],(p,)));calls.extend(blend(m,p));return m,calls

def linked(obj,label,entry=ENTRY,s=SYMS):
 text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()))
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
 return list(struct.unpack('>58I',sections(p.with_suffix('.elf'))['.text'][1][:232]))

def helpers(s=SYMS,connected=False):
 rom=(r/'conker/conker.us.bin').read_bytes();code=dict(zip(range(s['func_1512C150'],s['func_1512C150']+176,4),struct.unpack_from('>44I',rom,0x159600)))
 # Independent root rebases keep this connected original updater at its retail address.
 if s['func_1512C150']!=UPDATE:return{}
 code.update(zip(range(ANGLE,ANGLE+96,4),struct.unpack_from('>24I',rom,0x75F20)))
 if connected:code.update(zip(range(s['func_15123A54'],s['func_15123A54']+0xD1C,4),struct.unpack_from('>839I',rom,0x150F04)))
 return code

class Oracle(AngleOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=SYMS,connected=False,code=None):
  self.c=c;self.syms=s;self.connected_orient=connected;self.cut=None;self.accesses=0;self.trace=[];self.provider_observations=[];self.updates=[];self.other_count=0
  extra=helpers(s,connected)if code is None else code
  TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(ACTOR,),connected=extra)
  self.before=self.r[:];self.saved_f=self.f[20:];self.root_home=STACK+c.phase
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
  if t==ANGLE:a=(self.f[12],self.f[14])
  else:
   assert t in(ENTRY,self.syms['func_15123A54'],self.syms['func_1512C150'],*OTHER),hex(t);a=tuple(self.arguments(1))
  self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==ENTRY:self.root_home=self.r[29]
  if t==self.syms['func_15123A54']:self.provider_observations.append(tuple(read(self.memory,a[0]+off)for off in(0x384,0x5CC,0x240,0x370)))
  if t==self.syms['func_1512C150']:self.updates.append(a[0])
 def hook(self,t):
  a=self.calls[-1][1];value=0x76543210
  if t==self.syms['func_15123A54']:mutation(self.memory,self.c,a[0],self.root_home)
  elif t==self.syms['func_1512C150']:
   # Rebased standalone updater protocol, with identical bounded C contract.
   for target,args in blend(self.memory,a[0]):self.calls.append((target,args));self.events.append(('CALL',target,args))
  elif t in OTHER:
   if t==OTHER[0]:
    self.other_count+=1
    if self.c.window_flip>=0 and self.other_count==1:put(self.memory,ACTOR+0x23C,self.c.window_flip,1)
  else:raise AssertionError(('Unowned angle provider',hex(t)))
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678;self.r[2]=value

def state(m):return(complete(m),m.trace,m.current_pc,m.delay_of,m.accesses,m.provider_observations,m.updates)

def check(m,initial,c,s=SYMS,connected=False):
 want,calls=reference(initial,c,s,connected);assert public(m.memory)==public(want),(c,'memory');assert m.calls==calls,(c,m.calls,calls)
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.saved_f

def cases():
 for i in range(384):
  yield Case(kind=(0,0x40,0x80,0xC0,0x100,0xFFFFFFFF)[i%6],heading=HEADINGS[(i//6)%10],coords=COORDS[(i//3)%12],phase_bits=(0,bits(.5),bits(.995),bits(1),bits(-1))[i%5],current=bits((-540,-179,0,179,540)[i%5]),target=bits((540,179,0,-179,-540)[i%5]),flags=(0,2,0x80000001,0xFFFFFFFF)[i%4],mutation=i%4,phase=(i%2)*8)
 for heading,coords,kind,mutation in itertools.product(HEADINGS,COORDS,(0,0x40,0x80),range(4)):
  yield Case(kind=kind,heading=heading,coords=coords,mutation=mutation)

def guest_suite():
 ws=[linked(p,'guest-'+str(i))for i,p in enumerate((o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o'))];assert ws[0]==ws[1]==ws[2];visits=set();provider_visits=set();update_visits=set();angle_visits=set();count=0
 for i,c in enumerate(cases()):
  connected=i%5==0;initial=fixture(c);ms=[Oracle(w,initial,c,connected=connected).run()for w in ws]
  for m in ms:check(m,initial,c,connected=connected)
  assert state(ms[0])==state(ms[1])==state(ms[2]);visits.update(ms[0].visits&set(range(ENTRY,ENTRY+232,4)));provider_visits.update(ms[0].visits&set(range(ORIENT,ORIENT+0xD1C,4)));update_visits.update(ms[0].visits&set(range(UPDATE,UPDATE+176,4)));angle_visits.update(ms[0].visits&set(range(ANGLE,ANGLE+96,4)));count+=1
 assert set(range(ENTRY,ENTRY+232,4))-visits=={ENTRY+56};assert ws[0][14]==ws[0][9]==0x44817000
 cuts=delay=0
 for c in(Case(kind=0x40),Case(coords=COORDS[2]),Case(),Case(mutation=3,phase=8)):
  initial=fixture(c);m=Oracle(ws[0],initial,c).run()
  for cut in range(m.accesses):
   ms=[Oracle(w,initial,c)for w in ws]
   for m in ms:
    m.cut=cut
    try:m.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError('Ineffective access cut')
   assert state(ms[0])==state(ms[1])==state(ms[2]);cuts+=1;delay+=ms[0].delay_of is not None
 rebased=0
 for j,entry in enumerate((0x17007FFC,0x2500FFFC,0x15008000)):
  s={k:entry+0x10000+i*0x10000 for i,k in enumerate(SYMS)};bs=[linked(p,'rebase-%d-%d'%(j,i),entry=entry,s=s)for i,p in enumerate((o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o'))]
  for c in(Case(),Case(kind=0x40),Case(coords=COORDS[2]),Case(mutation=3)):
   initial=fixture(c);ms=[Oracle(w,initial,c,entry=entry,s=s).run()for w in bs]
   for m in ms:check(m,initial,c,s)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebased+=1
 return dict(cases=count,executions=count*3,body_words=58,reachable_words=len(visits),unreachable_duplicate_words=1,unreachable_word14_fixed=True,bindings=2,guards=0,access_prefix_cases=cuts,branch_delay_cuts=delay,rebased_cases=rebased,original_orientation_words=839,orientation_flag_route_words_visited=len(provider_visits),orientation_full_routine_claimed=False,original_updater_words=44,updater_words_visited=len(update_visits),original_angle_helper_words=24,angle_helper_words_visited=len(angle_visits),complete_RAM_registers_trace_and_fault_context=True,private_home_redirection=True,general_FCSR_or_hardware_claimed=False)

def caller_suite():
 rom=(r/'conker/conker.us.bin').read_bytes();jal=(0x0C000000|(ENTRY>>2&0x3FFFFFF)).to_bytes(4,'big');calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];pointers=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==ENTRY.to_bytes(4,'big')];assert calls==[0x150484,0x1504B0]and not pointers
 ws=[linked(p,'caller-target-'+str(i))for i,p in enumerate((o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o'))];count=0;visits=set()
 for entry,at,n in((0x15122FD4,0x150484,19),(0x15123000,0x1504B0,8)):
  words=list(struct.unpack_from('>%dI'%n,rom,at));end=0x15123020
  for tag,flip,kind,coord,mutation,phase in itertools.product((0,1),(0,1),(0,0x40),(0,2),range(4),(0,8)):
   c=Case(kind=kind,coords=COORDS[coord],mutation=mutation,phase=phase,tag=tag,window_flip=flip);initial=fixture(c);want=dict(initial);expected=[];repeat=1
   for index in range(2 if entry==0x15122FD4 else 1):
    if index and want[ACTOR+0x23C]==0:break
    expected.append((ENTRY,(ACTOR,)));want,more=reference(want,c);expected.extend(more)
    for target in OTHER:
     expected.append((target,(ACTOR,)))
     if target==OTHER[0]and index==0:put(want,ACTOR+0x23C,flip,1)
   ms=[]
   for body in ws:
    code=helpers();code.update(zip(range(ENTRY,ENTRY+232,4),body));m=Oracle(words,initial,c,entry=entry,code=code);m.r[16]=ACTOR;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends={end}
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller window failed to reach its boundary')
    assert public(m.memory)==public(want),(entry,c,'memory');assert m.calls==expected,(entry,c,m.calls,expected);assert m.r[16]==ACTOR;ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);visits.update(ms[0].visits&set(range(entry,end,4)));count+=1
 return dict(cases=count,original_windows=2,window_words=[19,8],parent='func_15122C5C',call_ROM=['0x150484','0x1504B0'],caller_words_visited=len(visits),exit='0x15123020',arguments=1,return_ignored=True,live_optional_second_call=True,original_updater_and_angle_helper_connected=True,parent_C_still_placeholder=True,full_parent_or_hardware_claimed=False)

def controls(body):
 edits={
 'heading-boundary':('actor->unk390 < 180.0f','actor->unk390 <= 180.0f'),
 'direction':('direction = 2.0f;','direction = 1.0f;'),
 'type-exclusion':('actor->unk2C != 0x40','actor->unk2C != 0x41'),
 'x-source':('actor->unk2F8 - actor->unk2BC','actor->unk2F8 - actor->unk2C4'),
 'z-source':('z = actor->unk300 - actor->unk2C4;','z = actor->unk2F8 - actor->unk2C4;'),
 'squared-distance':('sqrtf(x * x + z * z)','x * x + z * z'),
 'distance-store':('*(f32 *)actor->pad370 = distance;','(void)distance;'),
 'distance-boundary':('distance < 42.0f','distance <= 42.0f'),
 'threshold':('distance < 42.0f','distance < 43.0f'),
 'angle-sign':('actor->unk37C - 45.0f * direction','actor->unk37C + 45.0f * direction'),
 'phase-reset':('actor->unk5CC = 0.0f;','actor->unk5CC = 1.0f;'),
 'flag-before-provider':('func_15123A54(actor);\n            actor->unk240 |= 2;','actor->unk240 |= 2;\n            func_15123A54(actor);'),
 'flag-bit':('actor->unk240 |= 2;','actor->unk240 |= 4;'),
 'skip-provider':('func_15123A54(actor);','(void)actor;'),
 'skip-updater':('func_1512C150(actor);','(void)actor;')}
 result={}
 for n,(a,b)in edits.items():assert body.count(a)==1,(n,a);result[n]=body.replace(a,b,1)
 return result

def compiled_controls():
 effective={};corpus=list(itertools.islice(cases(),384))+[Case(heading=bits(180)),Case(coords=COORDS[2]),Case(coords=COORDS[3]),Case(mutation=1)]
 for name,body in controls(source.SELECTED).items():
  obj,diag=source.compile_owner(r,o,source.HEADERS+body,'IDO-control-'+name);source.check_owner_diagnostics(diag)
  text,fs,rs=parse_object(obj);f=fs[F];asm,unknown=emit_function(text,f,rs,F,SYMS);assert not unknown;p=o/('IDO-control-'+name);p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%ENTRY+'\n'.join('%s = 0x%X;'%(n,v)for n,v in SYMS.items()))
  subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);words=list(struct.unpack('>%dI'%(f['size']//4),sections(p.with_suffix('.elf'))['.text'][1][:f['size']]))
  for c in corpus:
   initial=fixture(c);m=Oracle(words,initial,c).run()
   try:check(m,initial,c)
   except AssertionError:effective[name]='independent state/protocol disagreement';break
  else:raise AssertionError('Ineffective IDO control: '+name)
 return dict(successful_IDO_compiles=len(effective),effective_semantic_controls=effective,compiler_or_interpreter_errors_counted=False)

def native_harness(body):
 text=(r/'conker/src/game/generated_157840.c').read_text();a,b=source.function_span(text,'func_1512C150');updater=text[a:b].replace('void func_1512C150(','static void retainedBlend(')
 text=(r/'conker/src/game_75E60.c').read_text();a,b=source.function_span(text,'func_15048A70');angle=text[a:b]
 coords=','.join('{'+','.join('0x%Xu'%v for v in row)+'}'for row in COORDS);headings=','.join('0x%Xu'%v for v in HEADINGS)
 return source.HEADERS+'''\nextern f32 D_800A3694,D_800A3698;
f32 func_15048A70(f32,f32);
'''+updater+'\n'+angle+'\n'+body+r'''
typedef char DistanceOffset[__builtin_offsetof(struct108,pad370)==0x370?1:-1];
typedef char PhaseOffset[__builtin_offsetof(struct108,unk5CC)==0x5CC?1:-1];
static u32 word(const f32*p){union{u32 u;f32 f;}v;v.f=*p;return v.u;}
static f32 value(u32 n){union{u32 u;f32 f;}v;v.u=n;return v.f;}
__attribute__((noinline)) f32 sqrtf(f32 v){f32 out;__asm__("sqrtss %1,%0":"=x"(out):"x"(v));return out;}
static f32 referenceSqrt(f32 v){double d=(double)v;__asm__("sqrtsd %1,%0":"=x"(d):"x"(d));return(f32)d;}
static struct108 actor,expectedActor;static int mutationMode,providerCalls,updateCalls,error;static u32 initialFlags;static f32 beforeAngle;
f32 D_800A3694,D_800A3698;
static const u32 coords[12][4]={COORDS};static const u32 headings[10]={HEADINGS};
static void mutate(struct108*p){if(mutationMode){p->unk384=123.0f;p->unk5CC=.995f;p->unk240=0xA5A50001u;p->unk37C=720.0f;}}
__attribute__((noinline)) s32 func_15123A54(struct108*p){providerCalls++;if(p!=&actor||word(&p->unk5CC)!=0||word(&p->unk384)!=word(&beforeAngle)||(u32)p->unk240!=initialFlags)error=1;mutate(p);return(s32)0xF6543210u;}
__attribute__((noinline)) void func_1512C150(struct108*p){updateCalls++;if(p!=&actor)error=2;retainedBlend(p);}
static void modelBlend(struct108*p){f32 phase=p->unk5CC+D_800A3694;f32 delta,product;
 if(phase>1.0f)phase=1.0f;p->unk5CC=phase;if(phase==1.0f){p->unk384=D_800A3698;p->unk240&=~2;}else{
 delta=p->unk37C-p->unk384;if(delta< -180.0f)delta+=360.0f;else if(delta>=180.0f)delta-=360.0f;product=delta*phase;p->unk384+=product;}}
static int run(void){static const s32 kinds[]={0,0x40,0x80,0xC0,0x100,-1};static const f32 phases[]={0.0f,.5f,.995f,1.0f};
 static const f32 angles[]={-540,-179,0,179,540};u32 n,i;int kind,coord,mut,phase,active;u8*a=(u8*)&actor,*e=(u8*)&expectedActor;
 D_800A3694=value(0x3BC49BA6);D_800A3698=value(0x4479C000);
 for(n=0;n<256;n++)for(kind=0;kind<6;kind++)for(coord=0;coord<12;coord++)for(mut=0;mut<2;mut++)for(phase=0;phase<4;phase++){
 f32 x,z,total,distance,direction;for(i=0;i<sizeof(actor);i++)a[i]=(u8)(i*13+n);actor.unk2C=kinds[kind];
 {union{u32 u;f32 f;}v;v.u=headings[n%10];actor.unk390=v.f;}
 actor.unk2F8=value(coords[coord][0]);actor.unk300=value(coords[coord][1]);actor.unk2BC=value(coords[coord][2]);actor.unk2C4=value(coords[coord][3]);
 actor.unk5CC=phases[phase];actor.unk384=angles[n%5];actor.unk37C=-angles[n%5];actor.unk240=(s32)(0xA5A50000u|n);initialFlags=(u32)actor.unk240;mutationMode=mut;
 for(i=0;i<sizeof(actor);i++)e[i]=a[i];active=0;direction=expectedActor.unk390<180.0f?2.0f:-2.0f;
 if(kinds[kind]!=0x40&&kinds[kind]!=0x80){x=expectedActor.unk2F8-expectedActor.unk2BC;z=expectedActor.unk300-expectedActor.unk2C4;total=x*x+z*z;distance=referenceSqrt(total);*(f32*)expectedActor.pad370=distance;
 if(distance<42.0f){active=1;beforeAngle=expectedActor.unk37C-45.0f*direction;expectedActor.unk384=beforeAngle;expectedActor.unk5CC=0.0f;mutate(&expectedActor);expectedActor.unk240|=2;}}
 modelBlend(&expectedActor);providerCalls=updateCalls=error=0;func_1512C068(&actor);if(error)return error;if(providerCalls!=active||updateCalls!=1)return 3;
 for(i=0;i<sizeof(actor);i++)if(a[i]!=e[i])return 4;
 }return 0;}
'''.replace('COORDS',coords).replace('HEADINGS',headings)+START

def native_suite():
 profiles={};effective={}
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]+'.c');p.write_text(native_harness(source.SELECTED));exe=p.with_suffix('');q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stderr);profiles[opt]=dict(exit=0,cases=147456,UBSan=True)
 for name,body in controls(source.SELECTED).items():
  p=o/('native-control-'+name+'.c');p.write_text(native_harness(body));exe=p.with_suffix('');q=subprocess.run(native_command('-O2')+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode in range(1,5)and not q.stdout and not q.stderr,(name,q.returncode,q.stderr);effective[name]=q.returncode
 return dict(cases_per_profile=147456,profiles=profiles,SDK32_layout=True,real_updater_C=True,real_one_fold_helper_C=True,heading_patterns=10,planar_coordinate_patterns=12,phase_patterns=4,type_patterns=6,negative_controls=len(effective),effective_native_controls=effective,all_actor_bytes_checked=True,orientation_provider_bounded=True,portable_private_stack_alias_or_general_FCSR_or_hardware_claimed=False)
