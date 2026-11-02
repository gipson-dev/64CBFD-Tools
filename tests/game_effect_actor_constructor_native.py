from pathlib import Path
import json, subprocess
from tools.experiments import game_effect_actor_constructor_match as source
HARNESS=r'''
f32 D_800A601C,D_800A6020,D_800A6024,D_800A6028,D_800A602C;
static f32 values[5];static u32 rng_index,allocation,errors,slot_seen[256];static s32 wanted_context;static u8 wanted_slot;
static EffectVector15154884 *live_position;static u8 actor[0x200],descriptor_copy[120],payload_copy[20];static u32 alloc_calls,copy_calls;
static void bytes(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static int equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
f32 func_150ADA68(void){f32 out=values[rng_index];rng_index++;
 if(rng_index==3){live_position->x=9.0f;live_position->y=8.0f;live_position->z=7.0f;}
 if(rng_index==4){D_800A6020=-2.0f;D_800A6024=6.0f;D_800A6028=1.5f;D_800A602C=-4.0f;}
 return out;}
void *func_15132A4C(void*d,s32 a,s32 b,s32 n,u8 slot,s32 context){alloc_calls++;bytes(descriptor_copy,d,120);
 if(a||b||n!=20||slot!=wanted_slot||context!=wanted_context){errors++;}slot_seen[slot]=1;return allocation?actor:0;}
void *memcpy(void*d,const void*s,u32 n){copy_calls++;if(n==20)bytes(payload_copy,s,20);bytes(d,s,n);return d;}
static int private_byte(u32 i){return(i>=0x59&&i<=0x5B)||i==0x69||i==0x6B||i==0x71||i>=0x76;}
static int check_descriptor(const EffectVector15154884*p){u8 want[120];u32 i;for(i=0;i<120;i++)want[i]=descriptor_copy[i];
 #define WF(o,v) do{f32 q=(v);bytes(want+(o),&q,4);}while(0)
 #define W32(o,v) do{u32 q=(v);bytes(want+(o),&q,4);}while(0)
 #define W16(o,v) do{u16 q=(v);bytes(want+(o),&q,2);}while(0)
 WF(0,1);WF(4,1);WF(8,0);WF(12,0);WF(0x10,values[0]*360.0f);WF(0x14,values[1]*360.0f);WF(0x18,values[2]*360.0f);
 WF(0x1C,1);WF(0x20,1);WF(0x24,1);WF(0x28,p->x);WF(0x2C,p->y);WF(0x30,p->z);WF(0x34,0);WF(0x38,0);WF(0x3C,0);
 WF(0x40,values[3]*D_800A6020+D_800A6024);WF(0x44,0);WF(0x48,values[4]*D_800A6028+D_800A602C);WF(0x4C,0);
 W32(0x50,0x140);W16(0x54,0x12C);W16(0x56,0x55);want[0x58]=0;W32(0x5C,0);want[0x60]=0xFF;want[0x61]=0x12;
 for(i=0x62;i<0x68;i++){want[i]=0;}want[0x68]=2;want[0x6A]=0;W32(0x6C,0);want[0x70]=0;W16(0x72,1);W16(0x74,0xFF);
 for(i=0;i<120;i++){if(!private_byte(i)&&want[i]!=descriptor_copy[i])return 0;}return 1;}
static int run(void){u32 c,i;for(c=0;c<256;c++){EffectVector15154884 guarded[3];f32 lifetime;void*result;u8 before[sizeof(guarded)];
 for(i=0;i<sizeof(guarded);i++){((u8*)guarded)[i]=(u8)(0xA5+i);}guarded[1].x=1.5f;guarded[1].y=-2.25f;guarded[1].z=7.75f;bytes(before,guarded,sizeof(guarded));
 live_position=&guarded[1];for(i=0;i<5;i++)values[i]=(f32)((i+c)%6)*0.25f-0.25f;
 D_800A601C=2.0f;D_800A6020=4.0f;D_800A6024=-1.0f;D_800A6028=8.0f;D_800A602C=0.5f;
 lifetime=0.5f+(f32)(c%9);allocation=(c>>1)&1;wanted_slot=(u8)c;wanted_context=(s32)(0xD4000000u+c*0x101u);
 rng_index=alloc_calls=copy_calls=errors=0;for(i=0;i<sizeof(actor);i++)actor[i]=(u8)(i*7+c);result=func_15154884(&guarded[1],lifetime,-3.5f+c*.25f,100.0f+c,wanted_slot,wanted_context);
 if(rng_index!=5||alloc_calls!=1||errors||!check_descriptor(&guarded[1]))return 20;
 if(result!=(allocation?(void*)actor:0)||copy_calls!=allocation)return 30;
 if(allocation){f32 want[5]={lifetime,-3.5f+c*.25f,100.0f+c,0.0f,2.0f/lifetime};if(!equal(payload_copy,want,20)||!equal(actor+0x170,want,20))return 40;}
 if(!equal(guarded,before,sizeof(EffectVector15154884))||!equal((u8*)guarded+2*sizeof(EffectVector15154884),before+2*sizeof(EffectVector15154884),sizeof(EffectVector15154884)))return 50;
 }
 rng_index=alloc_calls=copy_calls=errors=0;if(func_15154884(live_position,0.0f,1.0f,2.0f,0,0)||rng_index||alloc_calls||copy_calls)return 55;
 rng_index=alloc_calls=copy_calls=errors=0;if(func_15154884(live_position,-2.0f,1.0f,2.0f,0,0)||rng_index||alloc_calls||copy_calls)return 56;
 for(i=0;i<256;i++){if(!slot_seen[i]&&i%5)return 60;}return 0;}
int main(void){return run();}
'''
def qualify(root,out):
 headers=source.HEADERS.replace('#include <ultra64.h>','#include <stdint.h>\n#include <stddef.h>\ntypedef int8_t s8; typedef uint8_t u8; typedef int16_t s16; typedef uint16_t u16; typedef int32_t s32; typedef uint32_t u32; typedef float f32;')
 text=headers+'\n'+source.SELECTED+'\n'+HARNESS
 (out/'native_harness_v1.c').write_text(text)
 reports=[]
 for opt in ('O0','O2','O3'):
  binary=out/f'native-v1-{opt}'
  cmd=['gcc','-std=c99','-'+opt,'-Wall','-Wextra','-Werror','-fno-builtin','-fsanitize=undefined','-fno-sanitize-recover=all',str(out/'native_harness_v1.c'),'-o',str(binary)]
  p=subprocess.run(cmd,capture_output=True,text=True);assert p.returncode==0,(p.stdout,p.stderr)
  q=subprocess.run([str(binary)],capture_output=True,text=True);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  reports.append(dict(optimization=opt,cases=256,UBSan_clean=True,compiler_stderr=p.stderr,runtime_stderr=q.stderr))
 report=dict(success=True,private_only=True,matching_credit=0,profiles=reports,cases_per_profile=256,total_executions=768,
  complete_position_bytes=12,descriptor_natural_bytes=120,descriptor_required_bytes=112,private_descriptor_bytes=8,
  complete_payload_bytes=20,all256_slots=True,allocation_success_failure=True,live_position_and_constants=True,
  whole_position_fences=True,UBSan_clean=True,independent_native_control=True)
 (out/'private-native-v1.json').write_text(json.dumps(report,indent=2)+'\n')
 return report
 
 

if __name__=='__main__':
 root=Path.cwd();print(json.dumps(qualify(root,root/source.BUILD),indent=2))

