"""Defined SDK32 object layouts, mutating services and effective source controls."""
from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_surface_angular_effect_15194408_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments import game_surface_angular_effect_15194408_match as screen
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
PRE='''typedef unsigned char u8; typedef unsigned short u16; typedef unsigned int u32;
typedef short s16; typedef int s32; typedef float f32;
#define NULL ((void *)0)
#define offsetof __builtin_offsetof
void *memcpy(void *d,const void *s,u32 n) { u32 i;for(i=0;i<n;i++)((u8 *)d)[i]=((const u8 *)s)[i];return d; }
void *memset(void *d,int c,u32 n) { u32 i;for(i=0;i<n;i++)((u8 *)d)[i]=(u8)c;return d; }
'''
HARNESS=r'''
typedef struct { u8 before[0x14]; f32 x,y,z; u8 tail[0x320]; } NativeActor;
typedef char assert_pointer_32[sizeof(void *)==4?1:-1];
typedef char assert_surface_36[sizeof(Surface15194408)==36?1:-1];
typedef char assert_angles_8[sizeof(Angles15194408)==8?1:-1];
typedef char assert_trail_68[sizeof(Trail15194408)==68?1:-1];
typedef char assert_position_14[offsetof(NativeActor,x)==0x14?1:-1];
typedef char assert_selector_34[offsetof(Trail15194408,selector)==0x34?1:-1];
typedef char assert_opaque_38[offsetof(Trail15194408,opaqueChance)==0x38?1:-1];
typedef char assert_request_40[offsetof(Trail15194408,requestValue)==0x40?1:-1];
static NativeActor actor,other; static int calls,mode,seed,bad;
static Surface15194408 *lastSurface;
f32 D_800A8294,D_800A8298,D_800A829C;
static u32 fb(f32 value) { u32 b;memcpy(&b,&value,4);return b; }
static f32 ff(u32 value) { f32 b;memcpy(&b,&value,4);return b; }
static void check(int value) { if(!value) bad=1; }
void *func_151AE7B0(u8 *p,f32 scale,s16 life,u8 channel,s32 category) {
    check(calls++==0 && p==(u8 *)&actor && fb(scale)==0x3F19999Au && life==90 && channel==255 && category==1);
    if(mode&1) { ((u8 *)&actor)[4]=255;actor.x=42.0f;actor.y=-13.0f;actor.z=17.0f; }
    return NULL;
}
void func_1504715C(void *result,void *p) {
    int i;check(calls++==1 && p==(void *)&actor);lastSurface=(Surface15194408 *)result;
    for(i=0;i<36;i++) ((u8 *)result)[i]=(u8)(i*7+seed*11+0x63);
    if(mode&2) { actor.x=-32.0f;actor.y=2.0f;actor.z=80.0f;D_800A8294=-0.5f;D_800A8298=2.0f;D_800A829C=0.25f; }
}
void func_15153F18(void *a,void *b,s32 surface,s32 channel,s32 category) {
    int i;f32 raised=actor.y+50.0f;Angles15194408 *angle=(Angles15194408 *)a;Trail15194408 *t=(Trail15194408 *)b;
    check(calls++==2 && (void *)surface==(void *)lastSurface && channel==255 && category==1);
    check(angle->firstAngleBase==0 && angle->firstAngleRange==255 && angle->secondAngleBase==-63 && angle->secondAngleRange==35);
    check(fb(t->position[0])==fb(actor.x) && fb(t->position[1])==fb(raised) && fb(t->position[2])==fb(actor.z));
    check(t->timeBase==6.0f && t->timeRange==3.0f && fb(t->scaleBase)==fb(D_800A8294) && fb(t->scaleRange)==fb(D_800A8298));
    check(t->radiusBase==13.0f && t->radiusRange==8.0f && t->countBase==12 && t->countRange==5);
    check(t->requestSelectorBase==3 && t->requestSelectorRange==2 && t->durationBase==30 && t->durationRange==30);
    check(t->modeBase==100 && t->modeRange==100 && t->selector==0 && fb(t->opaqueChance)==fb(D_800A829C));
    check(t->firstValue==16 && t->secondValue==15 && t->requestValue==0);
    for(i=0;i<36;i++) check(((u8 *)lastSurface)[i]==(u8)(i*7+seed*11+0x63));
}
static int run(void) {
    static const u32 ys[]={0,0x80000000u,0x7FC12345u,0x7F800000u,0xFF800000u,1};
    int k,j,m,i;
    for(k=0;k<256;k++) for(m=0;m<4;m++) for(j=0;j<6;j++) {
        memset(&actor,0xA5,sizeof(actor));memset(&other,0x5A,sizeof(other));
        mode=m;seed=j;calls=bad=0;lastSurface=NULL;
        ((u8 *)&actor)[4]=(u8)k;actor.x=10.0f;actor.y=ff(ys[j]);actor.z=-20.0f;
        D_800A8294=ff(0x3E570A3Du);D_800A8298=ff(0x3ECFDF3Bu);D_800A829C=ff(0x3E99999Au);
        func_15194408((j&1)?NULL:(u8 *)&other,(u8 *)&actor);
        check(calls==(k<5?3:0));
        for(i=0;i<(int)sizeof(other);i++)check(((u8 *)&other)[i]==0x5A);
        for(i=0;i<(int)sizeof(actor);i++)if(i!=4 && !(i>=0x14 && i<0x20))check(((u8 *)&actor)[i]==0xA5);
        check(((u8 *)&actor)[4]==(u8)((k<5 && (mode&1))?255:k));
        if(bad)return 1;
    }
    return 0;
}
'''
CONTROLS={
 'wrong-kind-bound':screen.BODY.replace('    case 4:', '    case 4:\n    case 5:'),
 'wrong-attach-scale':screen.BODY.replace('0.6f','0.5f'),
 'wrong-attach-duration':screen.BODY.replace('0.6f, 90','0.6f, 91'),
 'wrong-surface-actor':screen.BODY.replace('func_1504715C(&surface, actor)','func_1504715C(&surface, unused)'),
 'wrong-height':screen.BODY.replace('+ 50.0f','+ 49.0f'),
 'wrong-angle':screen.BODY.replace('secondAngleBase = -63','secondAngleBase = -64'),
 'wrong-count':screen.BODY.replace('countBase = 12','countBase = 11'),
 'wrong-selector':screen.BODY.replace('trail.selector = 0','trail.selector = 1'),
 'wrong-scale-range':screen.BODY.replace('trail.scaleRange = D_800A8298','trail.scaleRange = D_800A8294'),
 'early-position':screen.BODY.replace('    switch (actor[4])','    f32 capturedX = *(f32 *)(actor + 0x14);\n    switch (actor[4])').replace('trail.position[0] = *(f32 *)(actor + 0x14)','trail.position[0] = capturedX')
}
def main():
 profiles={};controls=[]
 for name,body,flag in [('O0',screen.BODY,'-O0'),('O2',screen.BODY,'-O2'),('O3',screen.BODY,'-O3')]+[(n,b,'-O2')for n,b in CONTROLS.items()]:
  assert name.startswith('O') or body!=screen.BODY
  path=out/('native-'+name+'.c');exe=path.with_suffix('.exe');path.write_text(PRE+screen.TYPES+'\n'+body+'\n'+HARNESS+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
  command=native_command(flag)+['-fstrict-aliasing','-fexcess-precision=standard','-ffp-contract=off',str(path),'-o',str(exe)]
  q=subprocess.run(command,capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True,text=True)
  if name.startswith('O'):
   assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.returncode,q.stdout,q.stderr)
   profiles[name]=dict(cases=6144,typed_layout_asserted=True,strict_aliasing=True,UBSan=True)
  else:assert q.returncode!=0,name;controls.append(name)
 r=dict(profiles=profiles,effective_source_controls=controls,helper_contracts_only=True,incoming_home_mutation_excluded=True,source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':main()
