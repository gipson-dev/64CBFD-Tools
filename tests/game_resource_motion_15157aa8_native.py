"""Native SDK32 motion screen with semantic negative controls."""
import itertools,json,subprocess
from tools.experiments import game_resource_motion_15157aa8_match as match
from tools.tests import game_resource_motion_15157aa8_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
p=match.OUT;root=match.ROOT
name=match.NAME;function=match.MANIFEST['body'];decl=match.MANIFEST['declarations']
controls={'motion_gate':('if (state->flags & 1)','if (state->flags & 0x10)'),
          'damping':('state->velocity.x *= state->damping;','state->velocity.x += state->damping;'),
          'gravity':('accelerationY = state->accelerationY;','accelerationY = -state->accelerationY;'),
          'integration':('0.5f * accelerationX','1.0f * accelerationX'),
          'rotation':('state->angle.z += state->angularVelocity.z','state->angle.z -= state->angularVelocity.z')}
for n,(a,b) in controls.items():assert function.count(a)==1,n
code='''#include <ultra64.h>\n'''+decl+r'''
_Static_assert(sizeof(void*)==4 && __builtin_offsetof(ResourceMotionView,position)==0x54 &&
 __builtin_offsetof(ResourceMotionView,parameters)==0x120 &&
 __builtin_offsetof(ResourceMotionParameters,velocity)==0x10 &&
 __builtin_offsetof(ResourceMotionParameters,flags)==0x30,"SDK32 layout");
s32 D_800BE9E4;f32 D_800BE9A4,D_800BE9A8;
static union {ResourceMotionView view;u8 raw[0x170];} object;
union FloatBits {f32 f;u32 u;};
static u32 fb(f32 f){union FloatBits v;v.f=f;return v.u;}
static f32 bf(u32 u){union FloatBits v;v.u=u;return v.f;}
struct Case {u32 flags,ticks,time,inverse,pattern;u32 expected[9];};
static const struct Case cases[]={
'''
cases=[]
for flags,ticks,time,inv,pattern in itertools.product(range(16),(0,1,2,4,8,12),
        (g.bits(0.0),g.bits(.5),g.bits(1.0)),(g.bits(0.0),g.bits(1.0),g.bits(2.0)),range(2)):
 c=g.Case(flags,ticks,time,inv,pattern,0);m=g.reference(c)
 expected=[g.read(m,g.OBJ+off+i*4) for off in (0x54,0x120,0x130) for i in range(3)]
 code+='{'+','.join(str(x) for x in (flags,ticks,time,inv,pattern))+',{'+','.join('0x%08Xu'%x for x in expected)+'}},\n';cases.append(c)
code+='};\n'
for variant,text in [('selected',function)]+[(n,function.replace(a,b,1)) for n,(a,b) in controls.items()]:
 code+='\n'+text.replace(name,'test_'+variant,1)+'\n'
code+=r'''
typedef s32(*T)(u8*);
static int check(T fn){u32 i,j;u8 before[0x170];
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  const struct Case *c=&cases[i];ResourceMotionView *v=&object.view;ResourceMotionParameters *s=&v->parameters;
  f32 k=(f32)c->pattern*.125f;for(j=0;j<sizeof(object.raw);j++)object.raw[j]=(u8)(j*13+0x5a);
  v->position.x=10.f+k;v->position.y=-5.f+k;v->position.z=3.f+k;
  s->angle.x=2.f+k;s->angle.y=3.f+k;s->angle.z=-4.f+k;
  s->velocity.x=2.5f+k;s->velocity.y=-3.f+k;s->velocity.z=1.5f+k;
  s->angularVelocity.x=1.f+k;s->angularVelocity.y=-.5f+k;s->angularVelocity.z=.25f+k;
  s->accelerationY=-.75f;s->damping=c->pattern?1.f:.5f;s->flags=c->flags;
  D_800BE9E4=c->ticks;D_800BE9A4=bf(c->time);D_800BE9A8=bf(c->inverse);
  for(j=0;j<sizeof(object.raw);j++)before[j]=object.raw[j];
  if(fn(object.raw)!=1)return 1;
  if(fb(v->position.x)!=c->expected[0]||fb(v->position.y)!=c->expected[1]||fb(v->position.z)!=c->expected[2]||
     fb(s->angle.x)!=c->expected[3]||fb(s->angle.y)!=c->expected[4]||fb(s->angle.z)!=c->expected[5]||
     fb(s->velocity.x)!=c->expected[6]||fb(s->velocity.y)!=c->expected[7]||fb(s->velocity.z)!=c->expected[8])return 2;
  for(j=0;j<sizeof(object.raw);j++)if(!(j>=0x54&&j<0x60)&&!(j>=0x120&&j<0x12c)&&
      !(j>=0x130&&j<0x13c)&&object.raw[j]!=before[j])return 3;
 }return 0;}
static int run(void){if(check(test_selected))return 1;
'''
for i,n in enumerate(controls):code+='if(!check(test_'+n+'))return '+str(20+i)+';\n'
code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
path=p/'native-sdk32.c';path.write_text(code);profiles={}
for opt in ('-O0','-O2','-O3'):
 out=p/('native-sdk32'+opt);z=subprocess.run(native_command(opt)+['-fno-builtin',str(path),'-o',str(out)],cwd=root,capture_output=True,text=True)
 assert z.returncode==0 and not z.stderr and not z.stdout,(opt,z.stdout,z.stderr)
 z=subprocess.run([str(out)],capture_output=True);assert z.returncode==0,(opt,z.returncode,z.stderr)
 profiles[opt]=dict(cases=len(cases),negative_controls=len(controls),UBSan=True)
report=dict(profiles=profiles,source_installed=match.body((root/match.MANIFEST['source']).read_text(),match.NAME)==function,scope='finite inputs, tick counts 0,1,2,4,8,12')
(p/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
