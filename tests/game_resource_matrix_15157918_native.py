"""Native SDK32 matrix screen with semantic negative controls."""
import itertools,json,subprocess
from tools.experiments import game_resource_matrix_15157918_match as match
from tools.tests import game_resource_matrix_15157918_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
p=match.OUT;root=match.ROOT
name=match.NAME;function=match.MANIFEST['body'];decl=match.MANIFEST['declarations']
controls={'position':('view->position[0]','view->position[1]'),
          'rotation_arg':('view->params[0]','view->params[1]'),
          'scale':('params[3]','params[2]'),
          'matrix_cell':('[1][2] *=','[1][3] *=')}
for n,(a,b) in controls.items():assert function.count(a)>=1,n
code='''#include <ultra64.h>
'''+decl+r'''
_Static_assert(sizeof(void*)==4 && __builtin_offsetof(ResourceMatrixView,position)==0x54 &&
 __builtin_offsetof(ResourceMatrixView,matrix)==0x7c &&
 __builtin_offsetof(ResourceMatrixView,params)==0x120,"SDK32 layout");
u8 D_800BE9C0;
static u32 object[0x140/4] __attribute__((aligned(8)));
union FloatBits {f32 f;u32 u;};
struct Case {u32 index,mutation,pattern,expectedIndex;u32 input[80],output[80];};
static const struct Case cases[]={
'''
cases=[]
for idx,mut,scale,pattern in itertools.product((0,1),(0,1),(g.bits(0.0),g.bits(-1.0),g.bits(0.5),g.bits(2.0)),range(4)):
 c=g.Case(idx,mut,scale,pattern,0);initial=g.fixture(c);expected,_=g.reference(c)
 vals=[idx,mut,pattern,expected[g.INDEX]]
 ins=[g.read(initial,g.OBJ+i*4) for i in range(80)];outs=[g.read(expected,g.OBJ+i*4) for i in range(80)]
 code+='{'+','.join(str(v) for v in vals)+',{'+','.join('0x%08Xu'%v for v in ins)+'},{'+','.join('0x%08Xu'%v for v in outs)+'}},\n'
 cases.append(c)
code+=r'''};
static const struct Case *current;static int calls,bad;
static u32 fb(f32 f){union FloatBits x;x.f=f;return x.u;}
void func_150A8050(f32 m[4][4],f32 x,f32 y,f32 z){u32 i;ResourceMatrixView *v=(void*)object;
 if(m!=v->matrix[current->index]||fb(x)!=current->input[0x120/4]||
    fb(y)!=current->input[0x124/4]||fb(z)!=current->input[0x128/4])bad=1;
 calls++;
 for(i=0;i<16;i++)m[i/4][i%4]=(f32)((s32)i-(s32)current->pattern*3)*0.25f;
 if(current->mutation){D_800BE9C0^=1;v->position[0]=-4.0f;v->position[1]=5.5f;
  v->position[2]=6.25f;v->params[3]=-0.5f;}
}
'''
for variant,text in [('selected',function)]+[(n,function.replace(a,b,1)) for n,(a,b) in controls.items()]:
 code+='\n'+text.replace(name,'test_'+variant,1)+'\n'
code+=r'''
typedef s32(*T)(u8*);
static int check(T fn){u32 i,j;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
 current=&cases[i];for(j=0;j<80;j++)object[j]=current->input[j];
 D_800BE9C0=current->index;calls=bad=0;
 if(fn((u8*)object)!=1||bad||calls!=1||D_800BE9C0!=current->expectedIndex)return 1;
 for(j=0;j<80;j++)if(object[j]!=current->output[j])return 2;
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
report=dict(profiles=profiles,source_installed=match.body((root/match.MANIFEST['source']).read_text(),match.NAME)==function,scope='two defined slots, modeled matrix builder, finite arithmetic')
(p/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
