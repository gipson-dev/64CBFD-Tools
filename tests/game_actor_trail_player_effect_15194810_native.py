"""SDK32 valid-object semantics and effective source controls."""
from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_actor_trail_player_effect_15194810_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments import game_actor_trail_player_effect_15194810_match as screen
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
BASE_TYPES=screen.MANIFEST['base_types']
PRE='''typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;
typedef signed char s8;typedef short s16;typedef int s32;typedef float f32;typedef double f64;
#define NULL ((void *)0)
#define offsetof __builtin_offsetof
void *memcpy(void *d,const void *s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];return d;}
void *memset(void *d,int c,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=(u8)c;return d;}
s32 func_150ADA20(void);u8 *func_151D8868(void *,s32,u8,s32);
'''
HARNESS=r'''
typedef struct {u8 p0[4];u8 kind;u8 p5[15];f32 x,y,z;u8 tail[64];} NativeActor;
typedef char assert_sdk32[sizeof(void*)==4?1:-1];
typedef char assert_actor_position[offsetof(NativeActor,x)==0x14?1:-1];
typedef char assert_point[sizeof(TrailPoint151945CC)==12?1:-1];
typedef char assert_surface[sizeof(Surface15194408)==36?1:-1];
typedef char assert_angles[sizeof(Angles15194408)==8?1:-1];
typedef char assert_trail[sizeof(Trail151945CC)==68?1:-1];
typedef char assert_sound_layout[sizeof(PlayerEffect15194810)==8&&offsetof(PlayerEffect15194810,duration)==2&&offsetof(PlayerEffect15194810,callback)==6?1:-1];
typedef char assert_trail_selector[offsetof(Trail151945CC,selector)==52?1:-1];
typedef char assert_trail_final[offsetof(Trail151945CC,requestValue)==64?1:-1];
static NativeActor actor,source;static int calls,mode,kind,seed,bad;
static u32 randomValue;static f32 snapX,snapY,snapZ;static void *lastSurface;
f32 D_800A82E4,D_800A82E8,D_800A82EC;
static u32 fb(f32 v){u32 b;memcpy(&b,&v,4);return b;}static f32 ff(u32 b){f32 v;memcpy(&v,&b,4);return v;}
static void check(int x){if(!x)bad=1;}
void func_1504715C(void *result,void *p){
 int i;check(calls++==0&&p==(void*)&actor);lastSurface=result;
 for(i=0;i<36;i++)((u8*)result)[i]=(u8)(i*7+seed*11+0x63);
 if(mode&1){actor.kind=255;actor.x=42.f;actor.y=-13.f;actor.z=17.f;}
 if(mode&2){D_800A82E4=-.5f;D_800A82E8=2.f;D_800A82EC=.25f;}
}
void func_15153F18(void *av,void *tv,s32 surface,s32 channel,s32 context){
 Angles15194408 *a=av;Trail151945CC *t=tv;int i;
 check(calls++==1&&(void*)surface==lastSurface&&channel==255&&context==1);
 check(a->firstAngleBase==0&&a->firstAngleRange==255&&a->secondAngleBase==-63&&a->secondAngleRange==57);
 check(fb(t->position.x)==fb(snapX)&&fb(t->position.y)==fb(snapY)&&fb(t->position.z)==fb(snapZ));
 check(t->timeBase==10.f&&t->timeRange==5.f&&fb(t->scaleBase)==fb(D_800A82E4)&&fb(t->scaleRange)==fb(D_800A82E8));
 check(t->radiusBase==5.f&&fb(t->radiusRange)==fb(D_800A82EC));
 check(t->countBase==15&&t->countRange==10&&t->requestSelectorBase==3&&t->requestSelectorRange==2);
 check(t->durationBase==70&&t->durationRange==22&&t->modeBase==155&&t->modeRange==100);
 check(t->selector==0&&t->opaqueChance==.5f&&t->firstValue==16&&t->secondValue==15&&t->requestValue==0);
 for(i=0;i<36;i++)check(((u8*)lastSurface)[i]==(u8)(i*7+seed*11+0x63));
 if(mode&4){actor.x=-32.f;actor.y=2.f;actor.z=80.f;}
}
s32 func_150ADA20(void){check(calls++==2);return (s32)randomValue;}
u8 *func_151D8868(void *p,s32 arg1,u8 arg2,s32 arg3){
 s8 *s=p;s16 duration;memcpy(&duration,s+2,2);
 check(calls++==3&&arg1==0&&arg2==255&&arg3==0);
 check(s[0]==1&&duration==(s16)(randomValue%11u+20u)&&s[4]==8&&s[5]==1&&s[6]==-1);return NULL;
}
static int one(int k,u32 r,int m,int alias,u32 y){
 int i;memset(&actor,0xA5,sizeof(actor));memset(&source,0x5A,sizeof(source));
 calls=bad=0;kind=k;randomValue=r;mode=m;seed=k&7;lastSurface=NULL;
 actor.kind=(u8)k;actor.x=10.f;actor.y=ff(y);actor.z=-20.f;
 D_800A82E4=ff(0x3F2CCCCDu);D_800A82E8=ff(0x3E6C8B44u);D_800A82EC=ff(0x41C8CCCDu);
 snapX=actor.x;snapY=actor.y+95.f;snapZ=actor.z;
 func_15194810((u8*)(alias?&actor:&source),(u8*)&actor,(u8*)&kind);
 check(calls==((k<5||k==83)?4:0));
 for(i=0;i<(int)sizeof(actor);i++)if(i!=4&&!(i>=0x14&&i<0x20))check(((u8*)&actor)[i]==0xA5);
 for(i=0;i<(int)sizeof(source);i++)check(((u8*)&source)[i]==0x5A);
 return bad;
}
static int run(void){
 static const int ks[]={0,4,5,82,83,84,255};
 static const u32 rs[]={0,10,11,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};
 static const u32 ys[]={0,0x80000000u,0x7FC12345u,0x7F800000u,0xFF800000u,1};
 int k,r,m,a,y;
 for(k=0;k<256;k++)if(one(k,(u32)k*0x01010101u,0,0,0x3F800000u))return 1;
 for(k=0;k<7;k++)for(r=0;r<6;r++)for(m=0;m<8;m++)for(a=0;a<2;a++)for(y=0;y<6;y++)if(one(ks[k],rs[r],m,a,ys[y]))return 2;
 return 0;
}
'''
CONTROLS={
 'missing-special-kind':screen.BODY.replace('    case 0x53:\n',''),
 'wrong-kind-range':screen.BODY.replace('    case 4:\n','    case 5:\n'),
 'wrong-height':screen.BODY.replace('+ 95.0f','+ 94.0f'),
 'wrong-scale-field':screen.BODY.replace('trail.scaleRange = D_800A82E8','trail.scaleRange = D_800A82E4'),
 'wrong-radius-field':screen.BODY.replace('trail.radiusBase = 5.0f','trail.radiusBase = 0.0f'),
 'signed-random-remainder':screen.BODY.replace('func_150ADA20() % 0xBU','(s32)func_150ADA20() % 11'),
 'wrong-random-span':screen.BODY.replace('% 0xBU','% 0xAU'),
 'wrong-player-effect-level':screen.BODY.replace('effect.level = 8','effect.level = 9'),
 'late-position':screen.BODY.replace('        position.x = *(f32 *)(actor + 0x14);\n','').replace('        trail.position = position;','        position.x = *(f32 *)(actor + 0x14);\n        trail.position = position;')}
def main():
 profiles={};controls=[]
 for name,body,opt in [('O0',screen.BODY,'-O0'),('O2',screen.BODY,'-O2'),('O3',screen.BODY,'-O3')]+[(n,b,'-O2')for n,b in CONTROLS.items()]:
  if not name.startswith('O'):assert body!=screen.BODY
  path=out/('native-'+name+'.c');exe=path.with_suffix('.exe')
  path.write_text(PRE+BASE_TYPES+'\n'+screen.TYPES+'\n'+body+'\n'+HARNESS+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True)
  if name.startswith('O'):
   assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.returncode,q.stderr)
   profiles[name]=dict(cases=4288,typed_layout_asserted=True,strict_aliasing=True,UBSan=True)
  else:assert q.returncode!=0,name;controls.append(name)
 r=dict(profiles=profiles,effective_source_controls=controls,helper_contracts_only=True,uninitialized_padding_not_read=True,source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':main()
