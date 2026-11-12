import json,math,subprocess,sys
from pathlib import Path
from tools.experiments import game_twin_view_vertices_match as p
out=p.out;root=p.root
from tools.tests import game_twin_view_vertices_guest as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.game_record_vertex_callback_1513e83c_native import digest,trace
from tools.tests.game_billboard_quad_1513ead8_native import LINK_FLAGS
controls={
 'width_add':('*(f32 *)(actor + 0x4C) * *(f32 *)(actor + 0x2C)','*(f32 *)(actor + 0x4C) + *(f32 *)(actor + 0x2C)'),
 'height_add':('*(f32 *)(actor + 0x50) * *(f32 *)(actor + 0x30)','*(f32 *)(actor + 0x50) + *(f32 *)(actor + 0x30)'),
 'skip_copy':('if (fresh)', 'if (0)'),
 'flag':('cursor[0].v.flag = 0','cursor[0].v.flag = 1'),
 'side_sign':('*(f32 *)(actor + 0x34) + side','*(f32 *)(actor + 0x34) - side'),
 'return_null':('    return first;','    (void)first; return NULL;'),
}
def native_cases():
 result=[]
 for c in g.cases():
  if c.connected or c.alias or c.private or c.phase or not 0<=c.view<4:continue
  if not all(math.isfinite(g.floating(v)) for v in (c.width,c.height)):continue
  width=g.floating(c.width);height=g.floating(c.height);z,x=g.billboard.AXES[c.axis];scales=((1,1),(-.5,2),(0,-1))[c.scale];w=g.base.mul(width,scales[0]);h=g.base.mul(height,scales[1]);values=(g.base.add(10.5,g.base.mul(x,w)),g.billboard.sub(10.5,g.base.mul(x,w)),g.base.add(-12.25,h),g.billboard.sub(3.75,g.base.mul(z,w)),g.base.add(3.75,g.base.mul(z,w)))
  if all(math.isfinite(v) and -2147483648<=v<2147483648 for v in values):result.append(c)
 return result
def main():
 regions=((g.ACTOR,512),(g.BUFFER,320),(g.ALT,320),(g.base.PAGE,1),(g.AXIS_Z,32));fields=('view','width','height','fresh','success','scale','mutation','page','seed','axis');cases=native_cases();rows=[]
 for c in cases:
  expected=g.reference(g.fixture(c,'little'),c,'little');h=digest(b''.join(g.base.ram.data(expected['memory'],p,n)for p,n in regions));values=[g.u32(getattr(c,k))for k in fields]+[h,digest(trace(expected['calls'])),expected['value']];rows.append('{'+','.join('0x%Xu'%v for v in values)+'}')
 axes=','.join('{'+','.join('0x%Xu'%g.bits(v) for v in pair)+'}'for pair in g.billboard.AXES)
 code='#include <ultra64.h>\n#include <string.h>\nvoid func_151D5D60(void *,s16,s32,Vtx **,u8 *);\nextern f32 D_800DD1D8[],D_800DD1E8[];\n'
 for target,owner,index in g.TARGETS:
  source=(out/('variant_'+target+'_source.c')).read_text();start=source.index('Vtx *func_'+target+'(u8 *actor, s16 view) {');i=source.index('{',start);depth=0
  for j in range(i,len(source)):
   if source[j]=='{':depth+=1
   if source[j]=='}':
    depth-=1
    if depth==0:break
  selected=source[start:j+1]
  for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
   if name!='selected':assert text!=selected,(target,name)
   code+='\n'+text.replace('func_'+target,'test_'+target+'_'+name,1)+'\n'
 code+=r'''
typedef char Pointer32[sizeof(void *)==4?1:-1];
typedef char Vertex16[sizeof(Vtx)==16?1:-1];
typedef struct{u32 view,width,height,fresh,success,scale,mutation,page,seed,axis,hash,trace,value;}Case;
static const Case cases[]={'''+',\n'.join(rows)+r'''};
static const u32 axes[6][2]={'''+axes+r'''};
static u8 actor[512] __attribute__((section(".actor"),used,aligned(8)));
static u8 buffer[320] __attribute__((section(".buffer"),used,aligned(8)));
static u8 alternate[320] __attribute__((section(".alternate"),used,aligned(8)));
static u8 page __attribute__((section(".page"),used));
f32 D_800DD1D8[4] __attribute__((section(".axisZ"),used,aligned(4)));
f32 D_800DD1E8[4] __attribute__((section(".axisX"),used,aligned(4)));
static const Case *current;static u32 traceHash,copies,bad;
static void wr(u8 *p,u32 v,u32 n){u32 i;for(i=0;i<n;i++){p[i]=(u8)v;v>>=8;}}
static f32 real(u32 word){union{u32 u;f32 f;}v;v.u=word;return v.f;}
static u32 word(f32 number){union{u32 u;f32 f;}v;v.f=number;return v.u;}
static void mix(u32 v){u32 i;for(i=0;i<4;i++){traceHash=(traceHash^(u8)v)*16777619u;v>>=8;}}
void func_151D5D60(void *p,s16 view,s32 bytes,Vtx **out,u8 *fresh){
 mix(0x151D5D60);mix(5);mix((u32)p);mix((u32)(s32)view);mix((u32)bytes);mix(0x200);mix(0x201);
 if((u32)p!=(u32)actor+0x100||bytes!=64)bad=1;*out=current->success?(Vtx *)(buffer+(page?0:64)):0;*fresh=(u8)current->fresh;
}
void *memcpy(void *dest,const void *src,size_t n){u32 i;u8 *d=dest;const u8 *s=src;
 mix(0x10022EC0);mix(3);mix((u32)d);mix((u32)s);mix((u32)n);if(n!=64||s!=actor+0xC0)bad=1;
 for(i=0;i<n;i++)d[i]=s[i];copies++;
 if(current->mutation&&copies==1){wr(actor+0x100+(s32)(s16)current->view*4,(u32)alternate,4);wr(actor+0x2C,word(-4.75f),4);}return dest;
}
typedef Vtx *(*T)(u8 *,s16);
static int check(T test){u8 *p[6]={actor,buffer,alternate,&page,(u8 *)D_800DD1D8,(u8 *)D_800DD1E8};u32 n[6]={512,320,320,1,16,16};u32 i,j,k,h,mxcsr;Vtx *answer;
 __asm__ volatile("stmxcsr %0":"=m"(mxcsr));if(mxcsr&0xE040u)return 2;
 if((u32)actor!=0x30000||(u32)buffer!=0x60000||(u32)alternate!=0x70000||(u32)&page!=0x800BE9C0||(u32)D_800DD1D8!=0x800DD1D8||(u32)D_800DD1E8!=0x800DD1E8)return 2;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  current=&cases[i];for(k=0;k<4;k++)for(j=0;j<n[k];j++)p[k][j]=(u8)(j*29+current->seed*11+90);
  wr(actor+0x2C,current->width,4);wr(actor+0x30,current->height,4);wr(actor+0x34,word(10.5f),4);wr(actor+0x38,word(-12.25f),4);wr(actor+0x3C,word(3.75f),4);
  wr(actor+0x40,word(.25f),4);wr(actor+0x44,word(-.5f),4);wr(actor+0x48,word(1.0f),4);
  for(k=0;k<3;k++){const f32 scales[3][3]={{1,1,1},{-.5f,2,1.5f},{0,-1,3}};wr(actor+0x4C+k*4,word(scales[current->scale][k]),4);}
  for(k=0;k<4;k++){D_800DD1D8[k]=real(axes[current->axis][0]);D_800DD1E8[k]=real(axes[current->axis][1]);}
  wr(actor+0x100+(s32)(s16)current->view*4,(u32)buffer,4);page=(u8)current->page;traceHash=2166136261u;copies=bad=0;
  answer=test(actor,(s16)current->view);h=2166136261u;for(k=0;k<6;k++)for(j=0;j<n[k];j++)h=(h^p[k][j])*16777619u;
  if(bad||h!=current->hash||traceHash!=current->trace||(u32)answer!=current->value)return 1;
 }return 0;}
static int run(void){
'''
 for target,owner,index in g.TARGETS:
  code+='if(check(test_'+target+'_selected))return 1;\n'
  for i,name in enumerate(controls):code+='if(!check(test_'+target+'_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n__attribute__((force_align_arg_pointer)) void _start(void){int answer=run();__asm__ volatile("int $0x80"::"a"(1),"b"(answer):"memory");__builtin_unreachable();}\n'
 src=out/'native_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_screen'+opt);r=subprocess.run(native_command(opt)+['-fno-builtin',str(src),*LINK_FLAGS,'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.stdout[-4000:],r.stderr[-4000:]);r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases_per_target=len(cases),targets=2,negative_controls_per_target=len(controls),UBSan=True)
 report=dict(profiles=profiles,helpers='modeled',source_installed=False);(out/'native_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
