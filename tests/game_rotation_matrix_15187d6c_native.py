"""Native finite-input matrix checks and effective negative controls."""
import itertools,subprocess
from tools.experiments import game_rotation_matrix_15187d6c_match as match
from tools.tests import game_rotation_matrix_15187d6c_oracle as oracle
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run(state):
 root,p=match.ROOT,match.OUT
 g=vars(oracle)
 func=match.MANIFEST['body']
 controls={'sign':('m[0][0] = cy * cz - t * sz;','m[0][0] = cy * cz + t * sz;'),'first_angle':('sx = sinf(x);','sx = sinf(y);'),'sine_axis':('m[1][2] = sx;','m[1][2] = sy;'),'last_axis':('m[2][2] = cx * cy;','m[2][2] = cx * cz;'),'skip_identity':('    func_151EFE00(m);','')}
 for k,(a,b) in controls.items():assert func.count(a)==1,k
 cases=[]
 for xyz in itertools.product((-90.,-45.,-1.,0.,1.,30.,90.),repeat=3):
  c=g['Case'](*[g['bits'](v) for v in xyz]);want,calls=g['expected'](c);trig=[g['bits']((__import__('math').sin if t==g['SIN'] else __import__('math').cos)(g['floating'](v))) for t,v in calls[:6]];cases.append((c,want,calls,trig))
 code='#include <ultra64.h>\nextern f32 D_8008D578;\nvoid func_151EFE00(f32 [4][4]);\n'
 code+=r'''
 _Static_assert(sizeof(void*)==4,"SDK32");
 typedef struct {u32 angle[3],want[16],input[6],trig[6];} Case;
 static const Case cases[]={
 '''
 for c,want,calls,trig in cases:
  arr=lambda seq:','.join('0x%08Xu'%v for v in seq)
  code+='{ {'+arr((c.x,c.y,c.z))+'}, {'+arr(want)+'}, {'+arr(v for t,v in calls[:6])+'}, {'+arr(trig)+'} },\n'
 code+=r'''};
 f32 D_8008D578;static const Case *current;static u32 calls,error;
 static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
 static f32 val(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
 __attribute__((noinline,noclone)) f32 sinf(f32 x){u32 i=calls++;if(i>=6||(i&1)||word(x)!=current->input[i])error=1;return val(current->trig[i%6]);}
 __attribute__((noinline,noclone)) f32 cosf(f32 x){u32 i=calls++;if(i>=6||!(i&1)||word(x)!=current->input[i])error=1;return val(current->trig[i%6]);}
 __attribute__((noinline,noclone)) void func_151EFE00(f32 m[4][4]){u32 i;calls++;for(i=0;i<16;i++)((f32*)m)[i]=i%5==0?1.f:0.f;}
 '''
 for n,s in [('selected',func)]+[(k,func.replace(a,b,1)) for k,(a,b) in controls.items()]:code+='\n'+s.replace('func_15187D6C','test_'+n,1)+'\n'
 code+=r'''
 typedef void(*Fn)(f32[4][4],f32,f32,f32);
 static int check(Fn fn){u32 i,j;f32 m[4][4];D_8008D578=val(0x3c8efa35u);
  for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=&cases[i];calls=error=0;for(j=0;j<16;j++)((f32*)m)[j]=-99.f;
  fn(m,val(current->angle[0]),val(current->angle[1]),val(current->angle[2]));
  if(error||calls!=7)return 1;for(j=0;j<16;j++)if(word(((f32*)m)[j])!=current->want[j])return 2;}return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,k in enumerate(controls):code+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=p/'native.c';path.write_text(code);outcomes={}
 for opt in ('-O0','-O2','-O3'):
  output=p/('native'+opt);z=subprocess.run(native_command(opt)+['-fno-builtin',str(path),'-o',str(output)],cwd=root,capture_output=True,text=True);assert z.returncode==0,(opt,z.stdout,z.stderr)
  z=subprocess.run([str(output)],capture_output=True);assert z.returncode==0,(opt,z.returncode,z.stderr);outcomes[opt]=dict(cases=len(cases),negatives=len(controls),UBSan=True)
 return outcomes
