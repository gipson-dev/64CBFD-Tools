"""Bounded actor point transform; real point helper and explicit rotation service."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_four_head_lookup_match import payload
r=o=s=None
ENTRY,ROTATE,POINT,PARENT=0x151644F4,0x150A8050,0x150A7960,0x151644A8
OWNER,ACTOR,OTHER,THIRD,INPUT,VECTOR=0x30000,0xA0000,0xB0000,0xC0000,0x60000,0x80000
f32=lambda x:floating(bits(x))
@dataclass(frozen=True)
class Case:
 pattern:int=0
 height:float=2.75
 angleX:float=10.0
 angleZ:float=-20.0
 mutation:int=0
 alias:int=0
 phase:int=0
def seed(c):
 m=[bits(0.0)]*16
 for i in (0,5,10,15):m[i]=bits(1.0)
 if c.pattern:
  for i,v in ((1,-.25),(4,.75),(5,-1.25),(6,.5),(8,-.5),(9,.25)):m[i]=bits(v)
 return m
def fixture(c):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)}
 for base,size in ((OWNER,128),(ACTOR,128),(OTHER,128),(THIRD,128),(INPUT,32),(VECTOR,32)):
  assert not STACK-1024<=base<STACK+512,'Public fixture overlaps the private-stack filter'
  m.update({base+i:(i*13+0x59)&255 for i in range(size)})
 translation=OWNER+0x24 if c.alias==1 else INPUT
 actor=translation-0xE if c.alias==2 else OWNER+6 if c.alias==3 else ACTOR
 put(m,OWNER+0x14,actor);put(m,OWNER+0x18,bits(c.height));put(m,OWNER+0x1C,bits(.5));put(m,OWNER+0x20,VECTOR)
 for i,v in enumerate((10.0 if c.alias==3 else -3.75,6.5,-9.25)):put(m,translation+i*4,bits(v))
 for i,v in enumerate((c.angleX*2,1,c.angleZ*2)):put(m,VECTOR+i*4,bits(v))
 return m,(OWNER,translation,bits(c.height),bits(c.angleX),bits(c.angleZ))
def effect(memory,c,args,which):
 if c.mutation&(1 if which==ROTATE else 2):
  put(memory,OWNER+0x14,OTHER if which==ROTATE else THIRD)
  if which==ROTATE:
   for i,v in enumerate((12.5,-14.25,16.75)):put(memory,args[1]+4*i,bits(v))
def transformed(matrix,height):
 values=[]
 for i in range(3):
  a=f32(floating(matrix[i])*0.0);b=f32(floating(matrix[4+i])*height)
  c=f32(floating(matrix[8+i])*0.0);d=floating(matrix[12+i])
  values.append(f32(f32(a+b)+f32(c+d)))
 return values
def reference(initial,c,args):
 m=dict(initial);matrix=seed(c);effect(m,c,args,ROTATE)
 for i in range(3):matrix[12+i]=read(m,args[1]+4*i)
 out=transformed(matrix,floating(args[2]));effect(m,c,args,POINT)
 for i,v in enumerate(out):
  assert math.isfinite(v)and -(2**31)<=v<2**31
  put(m,read(m,OWNER+0x14)+0xE+i*2,math.trunc(v)&65535,2)
 return m,matrix,out
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,args,entry=ENTRY,connected=None,parent=False):
  self.c,self.root_args,self.observations=c,args,[]
  super().__init__(words,memory,c,entry=entry,s={},arguments=(OWNER,)if parent else args,connected=connected)
  self.before_f=self.f[:]
 def record_call(self,t):
  assert t in (ROTATE,POINT,ENTRY),hex(t)
  a=tuple(self.arguments({ROTATE:4,POINT:7,ENTRY:5}[t]));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==POINT:
   self.observations.append([read(self.memory,a[0]+4*i)for i in range(16)])
   effect(self.memory,self.c,self.root_args,POINT)
 def hook(self,t):
  assert t==ROTATE,hex(t);a=self.calls[-1][1]
  for i,value in enumerate(seed(self.c)):put(self.memory,a[0]+4*i,value)
  effect(self.memory,self.c,self.root_args,ROTATE)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for j in (1,2,3,*range(4,16),24,25):self.r[j]=0xA5000000+j
  self.f[:20]=[0xA5000000+j for j in range(20)]
def linked(obj):
 raw,rs=payload(obj,'func_151644F4');w=list(struct.unpack('>%dI'%(len(raw)//4),raw))
 for offset,bindings in rs.items():
  assert len(bindings)==1 and bindings[0][0]=='R_MIPS_26'
  target={"func_150A8050":ROTATE,"func_150A7960":POINT}[bindings[0][1]];w[offset//4]=(w[offset//4]&0xFC000000)|((target>>2)&0x3FFFFFF)
 return w
def public(m):return {a:v for a,v in m.items()if not STACK-1024<=a<STACK+512}
def run_case(words,rom,c,entry=ENTRY,parent=False):
 initial,args=fixture(c);expected,matrix,out=reference(initial,c,args)
 point=list(struct.unpack_from('>40I',rom,0xD4E10));connected=dict(zip(range(POINT,POINT+160,4),point))
 if parent:
  connected.update(zip(range(ENTRY,ENTRY+len(words)*4,4),words));program=list(struct.unpack_from('>19I',rom,0x191958));start=PARENT
 else:program=words;start=entry
 m=Oracle(program,initial,c,args,start,connected,parent).run()
 assert public(m.memory)==public(expected),(c,parent,'public memory',[(hex(a),m.memory.get(a),v)for a,v in public(expected).items()if m.memory.get(a)!=v][:8])
 calls=[(t,a)for t,a in m.calls if t!=ENTRY]
 home=STACK+c.phase-(32 if parent else 0);matrix_address=home-120+0x2C
 assert calls==[(ROTATE,(matrix_address,args[3],0,args[4])),(POINT,(matrix_address,0,args[2],0,home-120+0x6C,home-120+0x70,home-120+0x74))],(c,parent,calls)
 assert m.observations==[matrix]
 assert all(m.r[j]==m.before[j]for j in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
 if parent:assert m.r[2]==1
 return m
def guest():
 rom=(r/'conker/conker.us.bin').read_bytes();programs=[list(struct.unpack_from('>52I',rom,0x1919A4))]+[linked(o/name)for name in ('selected-final.o','qualified-padded.o','make-shadow/src/game_18D770.c.o')]
 assert all(program==programs[0]for program in programs)
 cases=[]
 for pattern,height,mutation,alias,phase in itertools.product((0,1),(-100.,-1.25,-0.0,0.,2.75,200.),range(4),(0,1,2),(0,8)):
  cases.append(Case(pattern,height,10.,-20.,mutation,alias,phase))
 cases.extend(Case(pattern=0,height=0,alias=3,phase=p)for p in(0,8))
 seen=set();count=0
 for entry in (ENTRY,0x17007FFC,0x1F00FFFC):
  for c in cases:
   outputs=[run_case(program,rom,c,entry)for program in programs]
   for m in outputs[1:]:assert m.memory==outputs[0].memory and m.trace==outputs[0].trace and m.r==outputs[0].r and m.f==outputs[0].f
   seen.update(pc-entry for pc in outputs[0].visits if entry<=pc<entry+208);count+=1
 assert seen==set(range(0,208,4))
 parents=0
 for pattern,height,mutation,phase in itertools.product((0,1),(-100.,-1.25,0.,2.75,200.),range(4),(0,8)):
  c=Case(pattern,height,10.,-20.,mutation,1,phase)
  for program in programs:run_case(program,rom,c,parent=True)
  parents+=1
 return dict(cases=count,programs=4,executions=count*4,parent_cases=parents,parent_executions=parents*4,body_words=52,all_body_words_reached=True,root_rebases=3,original_parent_words=19,original_point_helper_words=40,rotation_provider_opaque=True,live_input_and_actor_mutations=True,guest_pointer_aliases=True,full_public_memory_canaries_saved_state=True,all_machine_states_and_traces_equal=True,finite_trunc32_domain=True,hardware_FCSR_NaN_claimed=False)
def native():
 bodies=[s.SELECTED];changes=[
  ('missing_height','matrix, 0.0f, height, 0.0f','matrix, 0.0f, 0.0f, 0.0f'),
  ('wrong_translation_y','matrix[3][1] = translation->unk4;','matrix[3][1] = translation->unk8;'),
  ('wrong_z','owner->actor->unk12 = point[2];','owner->actor->unk12 = point[0];'),
  ('missing_y','owner->actor->unk10 = point[1];','(void)point[1];'),
  ('swapped_x','owner->actor->unkE = point[0];','owner->actor->unkE = point[1];'),
  ('captured_actor','    f32 point[3];','    struct226 *actor = owner->actor;\n    f32 point[3];')]
 for name,old,new in changes:
  assert old in s.SELECTED;body=s.SELECTED.replace(old,new)
  if name=='captured_actor':body=body.replace('owner->actor->','actor->')
  bodies.append(body)
 code=s.HEADERS+'\n'.join(body.replace('func_151644F4','candidate_'+str(i))for i,body in enumerate(bodies))
 code+='''
typedef union {u32 bits;f32 value;} FloatBits;
typedef void (*Candidate)(ActorMatrixPositionState*,struct17*,f32,f32,f32);
static Candidate candidates[]={'''+','.join('candidate_'+str(i)for i in range(7))+'''};
typedef struct {u32 height,matrix[16],translation[3];s16 expected[3];u32 mutation;} Test;
static const Test tests[]={
'''
 cases=[]
 for pattern,height,mutation in itertools.product((0,1),(-100.,-1.25,-0.0,0.,2.75,200.),range(4)):
  c=Case(pattern,height,10.,-20.,mutation,0,0);initial,args=fixture(c);expected,matrix,out=reference(initial,c,args)
  cases.append('{0x%Xu,{%s},{%s},{%s},%d}'%(bits(height),','.join('0x%Xu'%v for v in seed(c)),','.join('0x%Xu'%read(initial,INPUT+i*4)for i in range(3)),','.join(str(math.trunc(v))for v in out),mutation))
 code+=',\n'.join(cases)+'''};
static ActorMatrixPositionState state;
static struct226 actors[3];
static struct17 translation;
static const Test *current;
static u32 calls;
void func_150A8050(f32 matrix[4][4],f32 x,f32 y,f32 z){u32 i;for(i=0;i<16;i++)((u32*)matrix)[i]=current->matrix[i];calls++;
 if(current->mutation&1){state.actor=&actors[1];translation.unk0=12.5f;translation.unk4=-14.25f;translation.unk8=16.75f;}}
void func_150A7960(f32 matrix[4][4],f32 x,f32 y,f32 z,f32 *ox,f32 *oy,f32 *oz){f32 out[3],a,b,c,d;u32 i;
 for(i=0;i<3;i++){a=matrix[0][i]*x;b=matrix[1][i]*y;c=matrix[2][i]*z;d=matrix[3][i];out[i]=(a+b)+(c+d);}
 *ox=out[0];*oy=out[1];*oz=out[2];calls++;if(current->mutation&2)state.actor=&actors[2];}
static int run(void){u32 i,j,k,a,changed,killed=0,index;FloatBits h;unsigned char *bytes;int same;
 typedef char StateHeightOffset[__builtin_offsetof(ActorMatrixPositionState,height)==0x18?1:-1];
 typedef char StateTranslationOffset[__builtin_offsetof(ActorMatrixPositionState,translation)==0x24?1:-1];
 typedef char StateSize[sizeof(ActorMatrixPositionState)==0x30?1:-1];
 (void)sizeof(StateHeightOffset);(void)sizeof(StateTranslationOffset);(void)sizeof(StateSize);
 for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++)for(j=0;j<7;j++){
  current=&tests[i];for(a=0;a<3;a++){bytes=(unsigned char*)&actors[a];for(k=0;k<sizeof(struct226);k++)bytes[k]=0xA5;}
  state.actor=&actors[0];h.bits=current->height;calls=0;
  for(k=0;k<3;k++)((u32*)&translation)[k]=current->translation[k];
  candidates[j](&state,&translation,h.value,10.0f,-20.0f);
  index=(current->mutation&2)?2:(current->mutation&1)?1:0;same=calls==2;
  for(a=0;a<3;a++){bytes=(unsigned char*)&actors[a];for(k=0;k<sizeof(struct226);k++){
   changed=(a==index&&k>=0xE&&k<0x14);if(!changed&&bytes[k]!=0xA5)same=0;}}
  if(actors[index].unkE!=current->expected[0]||actors[index].unk10!=current->expected[1]||actors[index].unk12!=current->expected[2])same=0;
  if(!same){if(!j)return 10;killed|=1u<<(j-1);}
 }
 return killed==63?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=o/'native-actor-transform.c';path.write_text(code);reports=[]
 for profile in ('-O0','-O2','-O3'):
  exe=o/('native-actor-transform'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(path)],cwd=r,capture_output=True,text=True);(o/('native-actor-transform'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  reports.append(dict(profile=profile,cases=len(cases),UBSan=True,negative_controls=[name for name,_,_ in changes],all_controls_effective=True))
 return reports
def qualify(root,output,source):
 global r,o,s
 r,o,s=Path(root),Path(output),source
 report=dict(guest=guest(),native=native(),matching_credit=0)
 (o/'runtime-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report
