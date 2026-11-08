"""Camera snapshots, cached float arguments, late pointer reload and output order."""
from dataclasses import dataclass,replace
import itertools,math,re,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,SIN,COS,FOLLOW,PARENT=0x151794C8,0x150AD78C,0x150AD780,0x15179B14,0x1517947C
CAM0,CAM1,MARK=0x30000,0x34000,0x70000
u32=lambda n:n&0xFFFFFFFF
FPARGS=(0,0x80000000,0x3F800000,0xBF800000,1,0x007FFFFF,0x7F800000,0xFF800000,0x7FC12345,0x7F812345,0xFFFFFFFF)
RETURNS=(0,0x80000000,0x3F000000,0xBF000000,0x3F800000,0xBF800000,0x3EAAAAAB,1)
@dataclass(frozen=True)
class Case:
 xyz:tuple=(0x41440000,0xC1A60000,0x42270000)
 a0:int=0x3E800000
 a1:int=0xBF400000
 values:tuple=(0x3F000000,0x3E800000,0,0x3F400000)
 mode:int=0
 home_mode:int=0
 phase:int=0
 seed:int=0
 alias:int=0
 count:int=31
 count_mutation:object=None
def symbols(i=0,c=Case()):
 g,o,s,k=((0x800DBFF0,0x800DD438,SIN,COS),(0x80027FFC,0x80038004,0x1701FFFC,0x17118000),(0x9000FFF0,0x90018000,0x1E17FFFC,0x1E288000))[i]
 o={1:CAM0+0x2F8,2:g,3:STACK+c.phase-4,4:STACK+c.phase-20}.get(c.alias,o)
 return dict(D_800DBFF0=g,D_800DD438=o,func_150AD78C=s,func_150AD780=k)
def fixture(c=Case(),s=None):
 s=symbols(c=c)if s is None else s;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,1024)}
 for base,n in((CAM0-32,1100),(CAM1-32,1100),(s['D_800DBFF0']-16,48),(s['D_800DD438']-16,48),(MARK,32)):
  for i in range(n):m.setdefault(u32(base+i),(i*29+c.seed*11+0x5A)&255)
 for p in(CAM0,CAM1):
  for i,w in enumerate(c.xyz):put(m,p+0x2F8+4*i,w)
  put(m,p+0x398,c.a0 if p==CAM0 else 0x3FA00000);put(m,p+0x3A0,c.a1 if p==CAM0 else 0xBF200000)
 put(m,s['D_800DBFF0'],CAM0);put(m,0x800DD436,c.count,2)
 return m
def effect(m,c,s,stage,home):
 if stage==3 and c.count_mutation is not None:put(m,0x800DD436,c.count_mutation,2)
 if c.mode&(1<<stage):
  p=read(m,s['D_800DBFF0'])
  for i,v in enumerate((42.25+stage,-19.75-stage,9.5+stage)):put(m,p+0x2F8+4*i,bits(v))
  put(m,p+0x398,bits(0.125+stage));put(m,p+0x3A0,bits(0.5+stage));put(m,s['D_800DBFF0'],CAM1 if p==CAM0 else CAM0)
  put(m,MARK+4*stage,0xA1700000+stage)
 if c.home_mode&1:
  for off,v in((4,20+stage),(8,40+stage),(12,-60-stage)):put(m,home-off,u32(v))
 if c.home_mode&2 and stage in(1,3):put(m,home-28,0x3E800000)
 if c.home_mode&4 and stage==3:put(m,home-24,0xC2020000)
 if c.home_mode&8 and stage==3:put(m,home-20,0x41880000)
def homes(m,sp):
 for i in range(4):put(m,sp+4*i,0xB5000000+i)
def trunc(v):
 f=floating(v);assert math.isfinite(f)and-2147483648<=math.trunc(f)<=2147483647,('Outside bounded conversion domain',hex(v),f)
 return math.trunc(f)
def mul(a,b):return bits(floating(a)*floating(b))
def add(a,b):return bits(floating(a)+floating(b))
def sub(a,b):return bits(floating(a)-floating(b))
def reference(initial,c=Case(),s=None,home=None,ra=0xDEAD0000,saved=(0x3F800014,0x3F800015)):
 s=symbols(c=c)if s is None else s;m=dict(initial);home=STACK+c.phase if home is None else home;sp=home-64
 put(m,sp+28,ra);put(m,sp+16,saved[1]<<32|saved[0],8);p=read(m,s['D_800DBFF0'])
 for off,source in((60,0x2F8),(56,0x2FC),(52,0x300)):put(m,sp+off,u32(trunc(read(m,p+source))))
 angle=read(m,p+0x398);calls=[]
 def call(stage,a):
  calls.append((s['func_150AD78C'if stage%2==0 else'func_150AD780'],(a,)));effect(m,c,s,stage,home);homes(m,sp);return c.values[stage]
 put(m,sp+36,call(0,angle));cos0=call(1,angle)
 vertical=mul(bits(500.0),read(m,sp+36));horizontal=mul(bits(-500.0),cos0)
 put(m,sp+44,vertical);put(m,sp+40,horizontal);angle=read(m,read(m,s['D_800DBFF0'])+0x3A0)
 put(m,sp+36,call(2,angle));cos1=call(3,angle)
 horizontal,sine=read(m,sp+40),read(m,sp+36);x,z,y=(signed(read(m,sp+i))for i in(60,52,56))
 newx=trunc(add(bits(float(x)),add(0,mul(horizontal,sine))))
 newz=add(bits(float(z)),sub(mul(horizontal,cos1),0));fy=bits(float(y));out=s['D_800DD438']
 put(m,out,newx&65535,2)
 newy=add(fy,read(m,sp+44));put(m,out+4,trunc(newz)&65535,2);put(m,out+2,trunc(newy)&65535,2)
 return m,calls
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None,arguments=None):
  super().__init__(words,memory,c,entry=entry,s=symbols(c=c)if s is None else s,connected=connected,arguments=()if arguments is None else arguments)
  self.f[20:]=[FPARGS[(c.seed+i)%len(FPARGS)]for i in range(12)];self.saved_f=self.f[20:]
  self.stage=0;self.before_f=self.f[:]
 def record_call(self,t):
  if t==ENTRY:self.target_home=self.r[29];a=()
  elif t==FOLLOW:a=tuple(self.arguments(1))
  else:
   assert t==self.syms['func_150AD78C'if self.stage%2==0 else'func_150AD780'],(self.stage,hex(t));a=(self.f[12],)
  self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  if t==FOLLOW:
   homes(self.memory,self.r[29])
   for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
   self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0x87654321,0x12345678,True
   return
  stage=self.stage;self.stage+=1;effect(self.memory,self.case,self.syms,stage,self.target_home);homes(self.memory,self.r[29])
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=self.case.values[stage]
  self.hi,self.lo,self.condition=0x87654321,0x12345678,True
def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def original_object(core,q,out):
 text=(out/'frozen/conker/asm/1A6360.s').read_text();body=re.search(r'^glabel func_151794C8\n.*?(?=^glabel |\Z)',text,re.M|re.S).group()
 p=out/'original-reference.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+body+'\n.size '+core.FUNCTION+',.-'+core.FUNCTION+'\n')
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I','conker/include','-o',str(p.with_suffix('.o')),str(p)],cwd=core.ROOT,check=True,capture_output=True)
 q['original'],q['original_refs']=core.function_blob(p.with_suffix('.o'))
def programs(core,q,s):
 a,b=(list(core.bound_blob(q[n],q[r],s))for n,r in(('original','original_refs'),('raw','refs')));assert a==b;return a,b
def cases():
 coords=((12.25,-20.75,41.75),(0.,-0.,1.),(-32768.75,32767.75,65535.5),(123456.5,-98765.75,0.5),(-0.75,0.75,-1.5))
 rows=[Case(xyz=tuple(map(bits,xyz)),values=tuple(RETURNS[(v+j*3)%len(RETURNS)]for j in range(4)),mode=mode,phase=phase,seed=v)
       for xyz,v,mode,phase in itertools.product(coords,range(8),range(16),(0,8))]
 rows +=[Case(a0=a,a1=b,mode=m)for a,b,m in itertools.product(FPARGS,FPARGS,(0,1,2,3,4,8,15))]
 rows +=[Case(home_mode=m,mode=n)for m,n in itertools.product(range(16),(0,3,15))]
 return rows
def guest(core,q):
 original_object(core,q,core.ROOT/core.BUILD);rows=[(c,symbols(c=c),ENTRY)for c in cases()];seen=set()
 for i in(1,2):rows.extend((Case(mode=m,home_mode=h),symbols(i),0x17508000 if i==1 else 0x1F007FFC)for m,h in itertools.product((0,1,2,3,15),(0,1,2,15)))
 for c,s,entry in rows:
  initial=fixture(c,s);models=[Oracle(w,initial,c,entry=entry,s=s).run()for w in programs(core,q,s)]
  wanted,calls=reference(initial,c,s,saved=tuple(models[0].before_f[20:22]))
  assert all((m.memory,m.calls)==(wanted,calls)for m in models),(c,s)
  assert literal(models[0])==literal(models[1]);assert all(m.r[2]==s['D_800DD438']for m in models);seen.update(pc-entry for pc in models[0].visits)
 assert seen==set(range(0,312,4)),sorted(set(range(0,312,4))-seen)
 aliases=0
 for c in(Case(alias=a,mode=m,home_mode=h,phase=p)for a,m,h,p in itertools.product((1,2,3,4),(0,3,15),(0,1,2),(0,8))):
  if c.alias==4:c=replace(c,values=(0x3F000000,0,0,0x3F400000))
  s=symbols(c=c);initial=fixture(c,s);models=[Oracle(w,initial,c,s=s).run()for w in programs(core,q,s)];wanted,calls=reference(initial,c,s,saved=tuple(models[0].before_f[20:22]))
  assert all((m.memory,m.calls)==(wanted,calls)for m in models),c
  assert literal(models[0])==literal(models[1]);aliases+=1
 cuts=0
 for c in(Case(),Case(mode=15,home_mode=15),Case(alias=2,mode=3),Case(alias=4)):
  s=symbols(c=c);initial=fixture(c,s);ps=programs(core,q,s);full=Oracle(ps[0],initial,c,s=s).run()
  for cut in range(full.all_accesses):
   models=[]
   for w in ps:
    m=Oracle(w,initial,c,s=s);m.cut=cut
    try:m.run();raise AssertionError('Unfired trigonometric access cut')
    except AccessBoundary:pass
    models.append(m)
   assert literal(models[0])==literal(models[1]);cuts+=1
 return dict(cases=len(rows),reached_words=78,alias_cases=aliases,fault_prefix_cuts=cuts,independent_complete_memory=True,literal_state=True,
             F20_F21_and_all_callee_saved_FP_preserved=True,all_four_cached_float_arguments=True,late_camera_pointer_reload=True,
             helper_result_arithmetic_and_conversions_bounded_finite=True,angle_payloads_are_ABI_provider_probes=True,
             FP_exception_FCSR_and_hardware_acceptance_not_claimed=True,synthetic_private_aliases_guest_only=True)
def connections(core,q):
 rom=(core.ROOT/'conker/conker.us.bin').read_bytes();body=struct.unpack_from('>19I',rom,0x1A692C);count=0;zero_cases=0
 for c,initial_count,mutation in itertools.product((Case(mode=m,home_mode=h,phase=p)for m,h,p in itertools.product((0,3,15),(0,1,2,15),(0,8))),(0,1,29,30,31,32767,-1,-32768),(None,0,1,29,30,-31,-32768)):
  c=replace(c,count=initial_count,count_mutation=mutation);s=symbols(c=c);initial=fixture(c,s);models=[]
  for w in programs(core,q,s):
   code=dict(zip(range(ENTRY,ENTRY+312,4),w));m=Oracle(body,initial,c,entry=PARENT,s=s,connected=code)
   home=STACK+c.phase;parent_sp=home-64;m.r[29]=parent_sp
   for off,r in((32,16),(36,17),(40,18),(44,31)):put(m.memory,parent_sp+off,m.before[r])
   before=dict(m.memory)
   if initial_count==0:
    # The gated path does not read the camera pointer at all.
    for j in range(4):m.memory.pop(s['D_800DBFF0']+j,None);before.pop(s['D_800DBFF0']+j,None)
   m.run();models.append(m)
   if initial_count:
    wanted,calls=reference(before,c,s,home=parent_sp,ra=0x15179498,saved=tuple(m.before_f[20:22]))
    n=read(wanted,0x800DD436,2);n=(n^32768)-32768;quotient=(abs(n)//30)*(-1 if n<0 else 1)
    homes(wanted,parent_sp);expected=[(ENTRY,()),*calls,(FOLLOW,(u32(quotient),))]
   else:wanted,expected=before,[]
   assert(m.memory,m.calls)==(wanted,expected),(c,initial_count,mutation,m.calls,expected)
  assert literal(models[0])==literal(models[1]);count+=1;zero_cases+=initial_count==0
 return dict(original_tail_window_cases=count,caller_window_words=19,window_entry=hex(PARENT),parent_function='func_15179008',parent_words=304,
  zero_gate_unmapped_camera_cases=zero_cases,late_signed_halfword_reload=True,signed_division30=True,saved_RA_S0_S1_S2_restored=True,
  target_result_ignored=True,bounded_followup_provider=True,complete_parent_followup_and_math_owner_not_qualified=True)

_native_rows=None
def native_rows():
 global _native_rows
 if _native_rows is not None:return _native_rows
 rows=[]
 for c in(c for c in cases()if not c.phase and not c.home_mode):
  s=symbols(c=c);initial=fixture(c,s);wanted,calls=reference(initial,c,s)
  fields=[read(wanted,p+off)for p in(CAM0,CAM1)for off in(0x2F8,0x2FC,0x300,0x398,0x3A0)]
  lists=(c.xyz,(c.a0,c.a1),c.values,tuple(a[1][0]for a in calls),tuple(read(wanted,s['D_800DD438']+i*2,2)for i in range(3)),fields)
  arrays=['{'+','.join('0x%Xu'%n for n in values)+'}'for values in lists]
  rows.append('{'+','.join(arrays)+',%d,%d}'%(c.mode,int(read(wanted,s['D_800DBFF0'])==CAM1)))
 _native_rows=('\n,'.join(rows),len(rows));return _native_rows
def native_text(core,selected=None):
 s=core.SELECTED if selected is None else selected;s=s.replace('extern s16 D_800DD438[3];','')
 rows,n=native_rows()
 return '#include <ultra64.h>\n#include "structs.h"\n'+r'''
typedef struct {u32 before[4];s16 values[3];u32 after[4];} Output;
static Output output;
#define D_800DD438 output.values
'''+s+r'''
typedef char Layout[(sizeof(void*)==4&&__builtin_offsetof(struct108,unk2F8)==0x2F8&&__builtin_offsetof(struct108,unk2FC)==0x2FC&&__builtin_offsetof(struct108,unk300)==0x300&&__builtin_offsetof(struct108,unk398)==0x398&&__builtin_offsetof(struct108,unk3A0)==0x3A0)?1:-1];
typedef struct {u32 before[4];struct108 item;u32 after[4];} Camera;
typedef struct {u32 xyz[3],angles[2],values[4],args[4];u16 out[3];u32 fields[10];unsigned mode,selected;} Case;
static const Case cases[]={
__ROWS__
};
u8 *D_800DBFF0;
static Camera cameras[2],expected[2];static Output expectedOutput;static const Case*c;static unsigned calls,error;
static void bytes(void*d,const void*s,unsigned n){u8*p=d;const u8*q=s;unsigned i;for(i=0;i<n;i++)p[i]=q[i];}
static void fill(void*d,unsigned n,u8 value){u8*p=d;unsigned i;for(i=0;i<n;i++)p[i]=(u8)(value+i*17);}
static int equal(const void*a,const void*b,unsigned n){const u8*p=a,*q=b;unsigned i;for(i=0;i<n;i++)if(p[i]!=q[i])return 0;return 1;}
static u32 word(f32 f){u32 w;bytes(&w,&f,4);return w;}
static void field(struct108*p,unsigned off,u32 w){bytes((u8*)p+off,&w,4);}
static f32 provider(unsigned kind,f32 angle){
 unsigned stage=calls++;f32 result;struct108*p=(struct108*)D_800DBFF0;
 if(stage>=4){error=1;return 0.0f;}
 if(kind!=(stage&1)||word(angle)!=c->args[stage])error=1;
 if(c->mode&(1u<<stage)){
  p->unk2F8=42.25f+(f32)stage;p->unk2FC=-19.75f-(f32)stage;p->unk300=9.5f+(f32)stage;
  p->unk398=0.125f+(f32)stage;p->unk3A0=0.5f+(f32)stage;
  D_800DBFF0=(u8*)(p==&cameras[0].item?&cameras[1].item:&cameras[0].item);
 }
 bytes(&result,&c->values[stage],4);return result;
}
float func_150AD78C(float angle){return provider(0,angle);}
float func_150AD780(float angle){return provider(1,angle);}
static int run(void){
 static const unsigned offsets[5]={0x2F8,0x2FC,0x300,0x398,0x3A0};unsigned i,j,k;
 for(i=0;i<__COUNT__;i++){
  c=&cases[i];calls=error=0;fill(cameras,sizeof(cameras),0xA5);fill(&output,sizeof(output),0x5A);
  for(j=0;j<2;j++){
   for(k=0;k<3;k++)field(&cameras[j].item,offsets[k],c->xyz[k]);
   field(&cameras[j].item,0x398,j?0x3FA00000:c->angles[0]);field(&cameras[j].item,0x3A0,j?0xBF200000:c->angles[1]);
  }
  D_800DBFF0=(u8*)&cameras[0].item;bytes(expected,cameras,sizeof(cameras));bytes(&expectedOutput,&output,sizeof(output));
  for(j=0;j<2;j++)for(k=0;k<5;k++)field(&expected[j].item,offsets[k],c->fields[j*5+k]);
  for(j=0;j<3;j++)expectedOutput.values[j]=(s16)c->out[j];
  func_151794C8();
  if(calls!=4||error||D_800DBFF0!=(u8*)&cameras[c->selected].item)return 1;
  if(!equal(cameras,expected,sizeof(cameras))||!equal(&output,&expectedOutput,sizeof(output)))return 2;
 }
 return 0;
}
'''.replace('__ROWS__',rows).replace('__COUNT__',str(n))+START
def controls(core):
 s=core.SELECTED
 late=s
 initial=''
 for field_name,name in(('unk2F8','x'),('unk2FC','y'),('unk300','z')):
  line='    '+name+' = (s32)((struct108 *)D_800DBFF0)->'+field_name+';';assert line in late;late=late.replace(line+'\n','');initial+=line+'\n'
 late=late.replace('    x = (s32)((f32)x',initial+'    x = (s32)((f32)x')
 snapshot=s.replace('    s32 x;','    struct108 *initialCamera = (struct108 *)D_800DBFF0;\n    s32 x;').replace('angle = ((struct108 *)D_800DBFF0)->unk3A0;','angle = initialCamera->unk3A0;')
 changes={
  'wrong_vertical_gain':('500.0f * sine','250.0f * sine'),
  'wrong_horizontal_sign':('-500.0f * horizontal','500.0f * horizontal'),
  'uncached_first_cos_angle':('horizontal = func_150AD780(angle);','horizontal = func_150AD780(((struct108 *)D_800DBFF0)->unk398);'),
  'wrong_second_angle':('angle = ((struct108 *)D_800DBFF0)->unk3A0;','angle = ((struct108 *)D_800DBFF0)->unk398;'),
  'wrong_x_sign':('zero + horizontal * sine','zero - horizontal * sine'),
  'wrong_z_factor':('horizontal * angle - zero','horizontal * sine - zero'),
  'wrong_y_output':('D_800DD438[1] = y;','D_800DD438[1] = z;'),
  'missing_x_store':('    D_800DD438[0] = x;',''),
 }
 assert all(a in s for a,b in changes.values())
 rows={n:s.replace(a,b)for n,(a,b)in changes.items()}
 rows.update(stale_camera_pointer=snapshot,late_coordinate_snapshots=late,
  untruncated_initial_x=s.replace('    s32 x;','    f32 x;').replace('x = (s32)((struct108 *)D_800DBFF0)->unk2F8;','x = ((struct108 *)D_800DBFF0)->unk2F8;'),
  stub=s[:s.index('void func_151794C8(void)')]+'void func_151794C8(void) {}')
 assert all(v!=s for v in rows.values());return rows
def native(core,out):
 rows=[('valid-'+opt[1:],None,opt,True)for opt in('-O0','-O2','-O3')]+[(n,b,'-O2',False)for n,b in controls(core).items()];records=[]
 for name,body,opt,valid in rows:
  p=out/('native-'+name);p.with_suffix('.c').write_text(native_text(core,body))
  compile=subprocess.run([*native_command(opt),'-mstackrealign',str(p.with_suffix('.c')),'-o',str(p)],cwd=core.ROOT,capture_output=True,text=True)
  assert compile.returncode==0 and not compile.stdout and not compile.stderr,(name,compile.stdout,compile.stderr)
  run=subprocess.run([str(p)],capture_output=True,text=True,timeout=30)
  assert not run.stdout and not run.stderr and((run.returncode==0)==valid),(name,run.returncode,run.stdout,run.stderr)
  records.append(dict(name=name,opt=opt,exit=run.returncode,valid=valid))
 return dict(cases_per_profile=native_rows()[1],profiles=['O0','O2','O3'],trapping_UBSan=True,effective_controls=len(controls(core)),records=records,
             typed_camera_and_output_objects=True,complete_object_canaries=True,independent_precomputed_numeric_and_call_arguments=True,
             finite_integer_conversion_domain=True,exception_FCSR_and_actual_math_leaf_accuracy_not_claimed=True)
