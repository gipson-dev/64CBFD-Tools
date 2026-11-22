"""SDK32 snapshot/classifier model with effective descriptor and precision controls."""
from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_source_heading_trail_151945cc_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments import game_source_heading_trail_151945cc_match as screen
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
BASE_TYPES=screen.MANIFEST['base_types']
PRE='''typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;
typedef short s16;typedef int s32;typedef float f32;typedef double f64;
#define NULL ((void *)0)
#define offsetof __builtin_offsetof
void *memcpy(void *d,const void *s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];return d;}
void *memset(void *d,int c,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=(u8)c;return d;}
'''
HARNESS=r'''
typedef struct {u8 p0[0x14];f32 x,y,z;u8 p20[0x5A];u16 heading;u8 tail[0x2C4];} NativeActor;
typedef char assert_sdk32[sizeof(void*)==4?1:-1];
typedef char assert_surface[sizeof(Surface15194408)==36?1:-1];
typedef char assert_angles[sizeof(Angles15194408)==8?1:-1];
typedef char assert_trail[sizeof(Trail151945CC)==68?1:-1];
typedef char assert_heading[offsetof(NativeActor,heading)==0x7A?1:-1];
typedef char assert_position[offsetof(NativeActor,x)==0x14?1:-1];
typedef char assert_scale_range[offsetof(Trail151945CC,scaleRange)==24?1:-1];
typedef char assert_radius_base[offsetof(Trail151945CC,radiusBase)==28?1:-1];
static NativeActor actor,source;static int calls,mode,kind,category,seed,alias,bad;
static f32 snapX,snapY,snapZ;static s16 expectedHeading;static Surface15194408 *lastSurface;
u8 D_800A3FE6[1600];f64 D_800A82A0;f32 D_800A82A8,D_800A82AC,D_800A82B0,D_800A82B4,D_800A82B8;
static u32 fb(f32 v){u32 b;memcpy(&b,&v,4);return b;}static f32 ff(u32 b){f32 v;memcpy(&v,&b,4);return v;}
static void check(int x){if(!x)bad=1;}
void func_1504715C(void *result,void *p){
 int i;check(calls++==0&&p==(void*)&actor);lastSurface=(Surface15194408*)result;
 for(i=0;i<36;i++)((u8*)result)[i]=(u8)(i*7+seed*11+0x63);
 if(mode&1){(alias?&actor:&source)->heading=0xFF00;actor.x=42.f;actor.y=-13.f;actor.z=17.f;}
}
s32 func_15134070(u8 *p){
 check(calls++==1&&p==(u8*)&actor);
 if(mode&2){actor.x=-32.f;actor.y=2.f;actor.z=80.f;D_800A82A8=-.5f;D_800A82AC=2.f;D_800A82B0=.25f;D_800A82B4=9.f;D_800A82B8=.75f;D_800A82A0=-100.0;}
 if((mode&4)&&kind!=99)D_800A3FE6[kind*16]^=3;
 return kind;
}
void func_15153F18(void *a,void *b,s32 surface,s32 channel,s32 context){
 int i;Angles15194408 *v=(Angles15194408*)a;Trail151945CC *t=(Trail151945CC*)b;
 check(calls++==2&&(void*)surface==(void*)lastSurface&&channel==255&&context==1);
 check(v->firstAngleBase==expectedHeading&&v->firstAngleRange==128&&v->secondAngleBase==-160&&v->secondAngleRange==32);
 check(fb(t->position.x)==fb(snapX)&&fb(t->position.y)==fb(snapY)&&fb(t->position.z)==fb(snapZ));
 check(fb(t->timeBase)==fb(D_800A82A8)&&fb(t->timeRange)==fb(D_800A82AC)&&fb(t->scaleBase)==fb(D_800A82B0));
 check(t->scaleRange==0.f&&fb(t->radiusBase)==fb(D_800A82B4)&&fb(t->radiusRange)==fb(D_800A82B8));
 check(t->countBase==15&&t->countRange==12&&t->requestSelectorBase==3&&t->requestSelectorRange==1);
 check(t->durationBase==31&&t->durationRange==19&&t->modeBase==155&&t->modeRange==100);
 check(t->selector==(D_800A3FE6[kind*16]==1)&&t->opaqueChance==.5f&&t->firstValue==16&&t->secondValue==15&&t->requestValue==0);
 for(i=0;i<36;i++)check(((u8*)lastSurface)[i]==(u8)(i*7+seed*11+0x63));
}
void *func_151B4CD0(u8 *p,u8 channel,s32 context){check(calls++==3&&p==(u8*)&actor&&channel==255&&context==1);return NULL;}
static int one(int h,int k,int cat,int m,int al,u32 y,f64 dy){
 int i,accepted;memset(&actor,0xA5,sizeof(actor));memset(&source,0x5A,sizeof(source));memset(D_800A3FE6,0xA5,sizeof(D_800A3FE6));
 calls=bad=0;kind=k;category=cat;mode=m;alias=al;seed=h&7;lastSurface=NULL;
 (alias?&actor:&source)->heading=(u16)h;actor.x=10.f;actor.y=ff(y);actor.z=-20.f;
 D_800A3FE6[kind*16]=(u8)category;D_800A82A0=dy;
 D_800A82A8=ff(0x40D66666u);D_800A82AC=ff(0x40151EB8u);D_800A82B0=ff(0x3F2E147Bu);D_800A82B4=ff(0x408CCCCDu);D_800A82B8=ff(0x40A9999Au);
 snapX=actor.x;snapY=(f32)((f64)actor.y+D_800A82A0);snapZ=actor.z;expectedHeading=(s16)(((u16)h>>8)-128);
 accepted=kind!=99&&((mode&4)?(category^3):category)!=2;
 func_151945CC((u8*)(alias?&actor:&source),(u8*)&actor,(u8*)&kind);
 check(calls==(accepted?4:2));
 for(i=0;i<(int)sizeof(actor);i++)if(!(i>=0x14&&i<0x20)&&!(alias&&i>=0x7A&&i<0x7C))check(((u8*)&actor)[i]==0xA5);
 for(i=0;i<(int)sizeof(source);i++)if(!(i>=0x7A&&i<0x7C))check(((u8*)&source)[i]==0x5A);
 return bad;
}
static int run(void){
 static const int ks[]={0,1,98,99},cats[]={0,1,2,255},hs[]={0,0x7FFF,0x8000,0xFFFF};
 static const u32 ys[]={0,0x80000000u,0x7FC12345u,0x7F800000u,0xFF800000u,1};
 static const f64 ds[]={270.0,270.00001,-270.00001,0.0000000001};
 int h,k,c,m,a,y,d;
 for(h=0;h<256;h++)if(one(h*257,0,1,0,0,0x3F800000u,270.0))return 1;
 for(h=0;h<4;h++)for(k=0;k<4;k++)for(c=0;c<4;c++)for(m=0;m<8;m++)for(a=0;a<2;a++)for(y=0;y<6;y++)if(one(hs[h],ks[k],cats[c],m,a,ys[y],270.0))return 2;
 for(d=0;d<4;d++)for(m=0;m<3;m+=2)if(one(0xFF00,0,1,m,0,0xC3870000u,ds[d]))return 3;
 return 0;
}
'''
CONTROLS={
 'signed-heading':screen.BODY.replace('*(u16 *)(source + 0x7A)','*(s16 *)(source + 0x7A)'),
 'wrong-heading-bias':screen.BODY.replace('heading - 64','heading - 63'),
 'wrong-classifier-gate':screen.BODY.replace('category != 99','category != 98'),
 'wrong-category-gate':screen.BODY.replace('category != 2','category != 3'),
 'wrong-selector':screen.BODY.replace('category == 1','category == 0'),
 'wrong-classifier-stride':screen.BODY.replace('category * 16','category * 15'),
 'wrong-radius-field':screen.BODY.replace('trail.scaleRange = 0.0f;','trail.radiusBase = 0.0f;').replace('trail.radiusBase = D_800A82B4;','trail.scaleRange = D_800A82B4;'),
 'single-height-precision':screen.BODY.replace('+ D_800A82A0','+ (f32)D_800A82A0'),
 'late-position':screen.BODY.replace('    position.x = *(f32 *)(actor + 0x14);\n','').replace('            trail.position = position;','            position.x = *(f32 *)(actor + 0x14);\n            trail.position = position;'),
 'late-heading':screen.BODY.replace('    heading = (*(u16 *)(source + 0x7A) >> 8) - 64;\n','').replace('            angles.firstAngleBase = heading - 64;','            heading = (*(u16 *)(source + 0x7A) >> 8) - 64;\n            angles.firstAngleBase = heading - 64;')}
def main():
 profiles={};controls=[]
 for name,body,opt in [('O0',screen.BODY,'-O0'),('O2',screen.BODY,'-O2'),('O3',screen.BODY,'-O3')]+[(n,b,'-O2')for n,b in CONTROLS.items()]:
  if not name.startswith('O'):assert body!=screen.BODY
  path=out/('native-'+name+'.c');exe=path.with_suffix('.exe')
  path.write_text(PRE+BASE_TYPES+'\n'+screen.TYPES+'\n'+body+'\n'+HARNESS+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fexcess-precision=standard','-ffp-contract=off',str(path),'-o',str(exe)],capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True)
  if name.startswith('O'):
   assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.returncode,q.stderr)
   profiles[name]=dict(cases=6408,typed_layout_asserted=True,strict_aliasing=True,UBSan=True)
  else:assert q.returncode!=0,name;controls.append(name)
 r=dict(profiles=profiles,effective_source_controls=controls,helper_contracts_only=True,sparse_indices_and_home_mutations_guest_only=True,source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':main()
