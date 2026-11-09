import json,subprocess,sys
from pathlib import Path
from tools.experiments.game_resource_motion_151563b8_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_resource_motion_151563b8_oracle as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_resource_motion_151563b8_match import NEW_SOURCE
owner=NEW_SOURCE;selected=body(owner,'func_151563B8')
header='#include <ultra64.h>\n#include "structs.h"\n'+owner[owner.index('extern s32 D_800BE9E4;'):owner.index('/* Update wrapped lifetime')]

def controls():
 pairs={
 'timer_flag':('state->flags & 1','state->flags & 2'),
 'zero_expires':('state->remaining < 0','state->remaining <= 0'),
 'fade_flag':('state->flags & 8','state->flags & 4'),
 'fade_equality':('state->remaining < state->fadeStart','state->remaining <= state->fadeStart'),
 'wide_alpha':('s16 alpha =','s32 alpha ='),
 'unsigned_alpha':('if (alpha < state->alpha)','if ((u16)alpha < state->alpha)'),
 'x_direction':('state->x +=','state->x -='),
 'y_velocity':('state->dy*','state->dx*'),
 'skip_w':('        state->w += state->dw*D_800BE9A4;',''),
 'remove_gate':('if (expired) func_1516972C','if (!expired) func_1516972C'),
 }
 rows={n:selected.replace(a,b)for n,(a,b)in pairs.items()};assert all(b!=selected for b in rows.values());return rows

def main():
 cases=list(guest.native_cases())
 rows='\n'.join('{'+','.join('0x%Xu'%v for v in(c.flags,c.remaining,c.ticks,c.step,c.threshold,c.rate,c.alpha,c.seed,c.mutation))+'},'for c in cases)
 program=header+r'''
typedef char Layout[(sizeof(void*)==4 && sizeof(struct102)==0x1D8 && sizeof(ResourceMotion183640)==0x54 &&
 __builtin_offsetof(ResourceMotion183640,x)==0x10 && __builtin_offsetof(ResourceMotion183640,dx)==0x1C &&
 __builtin_offsetof(ResourceMotion183640,u)==0x28 && __builtin_offsetof(ResourceMotion183640,du)==0x34 &&
 __builtin_offsetof(ResourceMotion183640,flags)==0x40 && __builtin_offsetof(ResourceMotion183640,remaining)==0x42 &&
 __builtin_offsetof(ResourceMotion183640,alpha)==0x4C && __builtin_offsetof(ResourceMotion183640,fadeStart)==0x4E &&
 __builtin_offsetof(ResourceMotion183640,fadeRate)==0x50 && __builtin_offsetof(struct102,unk2C)==0x2C)?1:-1];
typedef struct{u32 flags,remaining,ticks,step,threshold,rate,alpha,seed,mutation;} Row;
static const Row rows[]={
'''+rows+r'''
};
s32 D_800BE9E4;f32 D_800BE9A4;
static struct102 object;
static u8 expected[sizeof(object)],snapshot[sizeof(object)];
static u32 expectedTicks,expectedStep,expectedCalls,currentCalls,error,expectedMark,mark;
static const Row*row;
static u32 word(f32 f){union{f32 f;u32 w;}v;v.f=f;return v.w;}
static f32 value(u32 w){union{f32 f;u32 w;}v;v.w=w;return v.f;}
static u32 rd32(const u8*p){return(u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
static u32 rd16(const u8*p){return(u32)p[0]|(u32)p[1]<<8;}
static void wr32(u8*p,u32 w){u32 i;for(i=0;i<4;i++)p[i]=(u8)(w>>(i*8));}
static void wr16(u8*p,u32 w){p[0]=(u8)w;p[1]=(u8)(w>>8);}
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static int equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static s32 signedHalf(u32 w){w&=65535;return w&32768?(s32)w-65536:(s32)w;}
static void effect(u8*p,u32*ticks,u32*step,u32*marker){
 u32 i;*marker=0x13579BDF;
 if(row->mutation){for(i=0;i<0x54;i++)p[i]=(u8)(i*7+0xC3);*ticks=0xDEADBEEF;*step=word(7.25f);}
}
static void model(void){
 u32 j;const u32 dst[]={0x10,0x14,0x18,0x28,0x2C,0x30};s32 timer,alpha;f32 product,sum;
 expectedCalls=0;
 if(expected[0x40]&1){timer=signedHalf((u32)signedHalf(rd16(expected+0x42))-expectedTicks);wr16(expected+0x42,(u32)timer);if(timer<0)expectedCalls=1;}
 if(expectedCalls){copy(snapshot,expected,sizeof(object));effect(expected,&expectedTicks,&expectedStep,&expectedMark);return;}
 for(j=0;j<6;j++){product=value(rd32(expected+dst[j]+12))*value(expectedStep);sum=value(rd32(expected+dst[j]))+product;wr32(expected+dst[j],word(sum));}
 timer=signedHalf(rd16(expected+0x42));
 if((expected[0x40]&8)&&timer<signedHalf(rd16(expected+0x4E))){alpha=signedHalf((u32)(timer*signedHalf(rd16(expected+0x50))));if(alpha<expected[0x4C])expected[0x4C]=(u8)alpha;}
}
__attribute__((noinline,noclone)) void func_1516972C(struct102*p){
 u32 ticks=(u32)D_800BE9E4,step=word(D_800BE9A4);
 if(++currentCalls!=1||p!=&object||!equal((u8*)p,snapshot,sizeof(object))||ticks!=row->ticks||step!=row->step)error=1;
 effect((u8*)p,&ticks,&step,&mark);D_800BE9E4=(s32)ticks;D_800BE9A4=value(step);
}
'''+selected+'\n'
 for name,b in controls().items():program+=b.replace('func_151563B8(','negative_'+name+'(',1)+'\n'
 program+=r'''
typedef void(*Update)(struct102*);
static int test(Update fn){
 u32 n,i,j;const u32 offsets[]={0x10,0x14,0x18,0x1C,0x20,0x24,0x28,0x2C,0x30,0x34,0x38,0x3C};f32 v;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
  row=&rows[n];for(i=0;i<sizeof(object);i++)((u8*)&object)[i]=(u8)((i+16)*29+row->seed*11+0x5A);
  for(j=0;j<12;j++){
   switch(row->seed%4){case 0:v=((f32)j-5.f)*.25f;break;case 1:v=((f32)j+1.f)*-1.5f;break;case 2:v=0.f;break;default:v=((f32)j-3.f)*1024.125f;}
   wr32((u8*)&object+offsets[j],word(v));
  }
  ((u8*)&object)[0x40]=(u8)row->flags;wr16((u8*)&object+0x42,row->remaining);((u8*)&object)[0x4C]=(u8)row->alpha;
  wr16((u8*)&object+0x4E,row->threshold);wr16((u8*)&object+0x50,row->rate);
  D_800BE9E4=(s32)row->ticks;D_800BE9A4=value(row->step);mark=expectedMark=0xA5A5A5A5;
  copy(expected,(u8*)&object,sizeof(object));expectedTicks=row->ticks;expectedStep=row->step;model();
  error=currentCalls=0;fn(&object);
  if(error||currentCalls!=expectedCalls||!equal((u8*)&object,expected,sizeof(object))||(u32)D_800BE9E4!=expectedTicks||word(D_800BE9A4)!=expectedStep||mark!=expectedMark)return 1;
 }
 return 0;
}
static __attribute__((noinline,noclone)) int aliasProbe(struct102*a,ResourceMotion183640*b){a->unk2C=0;b->v=1.f;return a->unk2C==0x3F800000;}
static int run(void){
 if(!aliasProbe(&object,(ResourceMotion183640*)&object))return 2;
 if(test(func_151563B8))return 3;
'''
 for j,name in enumerate(controls()):program+=' if(!test(negative_%s))return %d;\n'%(name,10+j)
 program+=' return 0;\n}\n'+START
 (out/'native.c').write_text(program);profiles=[]
 for opt in('-O0','-O2','-O3'):
  binary=out/('native'+opt);cmd=native_command(opt)+['-fstrict-aliasing','-Wstrict-aliasing=2','-fno-builtin','-mstackrealign',str(out/'native.c'),'-o',str(binary)]
  p=subprocess.run(cmd,cwd=root,capture_output=True,text=True);(out/('native'+opt+'-build.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
  rc=subprocess.run([str(binary)],capture_output=True).returncode;assert rc==0,(opt,rc)
  row=dict(profile=opt,cases=len(cases),semantic_controls=len(controls()),strict_aliasing=True,UBSan_traps=True);profiles.append(row);print(json.dumps(row),flush=True)
 signed=selected.replace('(s16)((u32)state->remaining - (u32)D_800BE9E4)','(s16)(state->remaining - D_800BE9E4)')
 assert signed!=selected
 (out/'native-signed-control.c').write_text(program.replace(selected,signed,1))
 (out/'native-noalias-control.c').write_text(program.replace('__attribute__((__may_alias__))',''))
 extra=[]
 for opt in('-O0','-O2','-O3'):
  row=dict(profile=opt)
  for label in('signed','noalias'):
   binary=out/('native-'+label+opt);p=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fno-builtin','-mstackrealign',str(out/('native-'+label+'-control.c')),'-o',str(binary)],cwd=root,capture_output=True,text=True);assert p.returncode==0,p.stderr
   rc=subprocess.run([str(binary)],capture_output=True).returncode
   if label=='signed':assert rc==-4,(label,opt,rc)
   else:assert rc==(0 if opt=='-O0'else 2),(label,opt,rc)
   row[label]=rc
  extra.append(row)
 report=dict(cases_per_profile=len(cases),profiles=profiles,semantic_controls=len(controls()),native_only_controls=extra,
             typed_void_resource_callback=True,struct102_size=0x1D8,partial_view_size=0x54,all_record_and_global_bytes=True,
             native_aliasing_GNU_qualified=True,generic_ISO_portability_claim=False)
 (out/'native-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
