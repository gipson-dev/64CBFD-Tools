from pathlib import Path
import json,subprocess
from tools.tests import game_direction_subdivide_151a8340_behavior as b
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-direction-subdivide-151a8340-screen';s=(o/'selected.c').read_text();a=s.index('typedef struct {f32 x,y,z,outX,outY,outZ;}');z=s.index('extern s32 (*D_8008F940',a);head=s[a:z];a=s.index('/* Recursively displace');z=s.index('\nvoid func_151A8560',a);body=s[a:z]
bad={'wrong_range_cutoff':body.replace('last - first < 2','last - first < 3'),
 'wrong_depth_cutoff':body.replace('depth <= 0','depth < 0'),
 'wrong_midpoint':body.replace('((last - first) >> 1)','1'),
 'wrong_noise_bias':body.replace('+ -amplitude','+ amplitude'),
 'cached_output_array':body.replace('((DirectionState151A7A90 *)record)->vertices[middle]','(left - first)[middle]'),
 'reload_anchor':body.replace('        draw = func_150ADA68();','        draw = func_150ADA68();\n        left = ((DirectionState151A7A90 *)record)->vertices + first;'),
 'wrong_z_delta':body.replace('left->z + dz * 0.5f','left->z + dy * 0.5f').replace('        draw = func_150ADA68();','        (void)dz;\n        draw = func_150ADA68();')}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==7
code='#include <ultra64.h>\ntypedef struct {f32 unk0,unk4,unk8;} struct17;\n'+head+'\nf32 func_150ADA68(void);\n'+'\n'.join(v.replace('func_151A8340','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+=r'''
typedef union {u32 u;f32 f;} Bits;
typedef struct {u32 first,last,amplitude,depth,mutation,seed,alternate,draws;u32 observations[32],values[192];} Case;
static const Case cases[]={
'''
rows=[];arr=lambda v:'{'+','.join(hex(b.u32(x))+'u' for x in v)+'}'
for c in b.cases():
 if c.phase:continue
 m,calls,obs=b.reference(b.fixture(c),c);scalar=(c.first,c.last,b.fb(c.amplitude),c.depth,c.mutation,c.seed,int(b.read(m,c.record+100)==b.ALT),len(obs));observations=[int(p==b.ALT) for t,p in obs];assert len(observations)<=32
 values=[b.read(m,p+24*i+4*j) for p in (b.BASE,b.ALT) for i in range(-2,14) for j in range(6)]
 rows.append('{'+','.join(hex(b.u32(x))+'u' for x in scalar)+','+arr(observations or [0])+','+arr(values)+'}')
code+=',\n'.join(rows)+'\n};\n'+r'''
typedef struct {DirectionState151A7A90 state;u8 tail[148];} Object;
typedef char Layout[sizeof(Object)==256&&sizeof(DirectionVertex151A7A90)==24&&__builtin_offsetof(DirectionState151A7A90,vertices)==100?1:-1];
static Object object;static DirectionVertex151A7A90 primary[16],alternate[16];static u8 before[256];static const Case*current;static u32 draws,error;
static f32 real(u32 v){Bits b;b.u=v;return b.f;}static u32 word(f32 v){Bits b;b.f=v;return b.u;}
f32 func_150ADA68(void){static const f32 samples[]={.125f,.75f,.5f,1.f,0.f,-.25f};f32 value=samples[(draws+current->seed)%6];DirectionVertex151A7A90*base=primary+2;u32 n,k;
 if(draws>=current->draws||object.state.vertices!=(current->observations[draws]?alternate+2:primary+2))error=1;draws++;
 if(current->mutation&1){DirectionVertex151A7A90*v=base+(s16)current->first;object.state.vertices=draws&1?alternate+2:primary+2;v->x+=.125f;v->y-=.25f;v->z+=.5f;}
 if(current->mutation&2)for(n=0;n<2;n++)for(k=0;k<16;k++){DirectionVertex151A7A90*v=(n?alternate:primary)+k;v->x+=.125f;v->y+=.25f;v->z-=.125f;}
 return value;}
static void(*candidates[])(u8*,s16,s16,f32,s16)={candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5,candidate_6,candidate_7};
static int run(void){u32 i,j,k,n,killed=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;
 for(j=0;j<8;j++){
  for(k=0;k<256;k++)((u8*)&object)[k]=(u8)(k*19+current->seed*7);object.state.vertices=primary+2;
  for(n=0;n<2;n++)for(k=0;k<16;k++){s32 index=(s32)k-2;DirectionVertex151A7A90*v=(n?alternate:primary)+k;v->x=.25f*index+n;v->y=.5f*index-n;v->z=-.125f*index;v->outX=10.f+index;v->outY=20.f+index;v->outZ=30.f+index;}
  for(k=0;k<256;k++)before[k]=((u8*)&object)[k];draws=error=0;candidates[j]((u8*)&object,(s16)current->first,(s16)current->last,real(current->amplitude),(s16)current->depth);
  if(draws!=current->draws||object.state.vertices!=(current->alternate?alternate+2:primary+2))error=1;
  for(n=0;n<2;n++)for(k=0;k<16;k++){DirectionVertex151A7A90*v=(n?alternate:primary)+k;u32 base=n*96+k*6;if(word(v->x)!=current->values[base]||word(v->y)!=current->values[base+1]||word(v->z)!=current->values[base+2]||word(v->outX)!=current->values[base+3]||word(v->outY)!=current->values[base+4]||word(v->outZ)!=current->values[base+5])error=1;}
  for(k=0;k<256;k++)if(!(k>=100&&k<104)&&((u8*)&object)[k]!=before[k])error=1;
  if(error){if(!j)return 10;killed|=1u<<(j-1);}
 }
}return killed==127u?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
p=o/'native-direction-subdivide.c';p.write_text(code);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=o/('native-direction-subdivide'+opt+alias);q=subprocess.run(native_command(opt)+[alias,'-o',str(exe),str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=r,capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr);profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,typed_disjoint_inputs=True,helpers_modeled=True)
(o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
