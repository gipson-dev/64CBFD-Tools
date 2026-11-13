from pathlib import Path
import json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_remaining_donor_candidates import body
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-intro-init-15010880-durable';source=(out/'typed-proposal.c').read_text();src=out/'native-candidate.c'
src.write_text(source[:source.index('/* Generated placeholder declarations. */')]+body(source,'func_15010880')+'\n')
harness=r'''
#include <ultra64.h>
#define func_15149130 func_15149130_legacy_signature
#include "functions.h"
#undef func_15149130
#define D_800D3098 D_800D3098_legacy_array
#include "variables.h"
#undef D_800D3098
extern void func_15010880(void);
u8 *D_800D3098; s32 D_800E0934; struct102 *D_800D2E4C;
static struct102 info; static union { u32 align; u8 bytes[128]; } output;
static int audio_calls,create_calls,copy_calls,error,enabled,first_result,audio_mutation,factory_mutation;
void func_150DE32C(void) {}
void func_15177410(s32 a,s32 b,s32 c,s32 d,s32 e,f32 f,s32 g,f32 h,s32 i,s32 j,s32 k,s32 l,s32 m,s32 n,s32 o,s32 p){
 if(a!=16||b!=233||c!=-437||d!=1123||e!=-3263||f!=90.0f||g!=15000||h!=36.0f||i!=77||j!=15||k!=127||l!=127||m!=127||n!=127||o!=127||p!=127)error=20;
 audio_calls++;if(audio_mutation){D_800D3098=(u8*)((u32)D_800D3098^0x80000001u);info.unk12^=0x40;}}
struct260 *func_15149130(s16 a,s8 b,s8 c,s8 d,u8 e,u8 f,s32 g,u8 h,s32 i){
 create_calls++;if(create_calls==1){if(a!=300||b!=-1||c!=94||d!=-1||e||f||g!=12||h!=255||i!=1)error=21;if(factory_mutation)info.unk12^=0x40;return first_result?(struct260*)output.bytes:NULL;}
 if(a!=5||b!=9||c!=-1||d!=-1||e!=1||f||g||h!=255||i!=1)error=22;return NULL;}
void *memcpy(void *d,const void *s,unsigned int n){u8*to=d;const u8*from=s;unsigned i;copy_calls++;if(n!=12||to!=output.bytes+40)error=23;for(i=0;i<n;i++)to[i]=from[i];return d;}
static int run(void){static const u32 bases[]={0u,0x7fffffffu,0xfffffff0u,0x81234567u};unsigned n,k;int flag,result,am,fm;u32 base;
 if(sizeof(void*)!=4||sizeof(struct177)!=12||__builtin_offsetof(struct102,unk12)!=18)return 10;
 for(n=0;n<4;n++)for(flag=0;flag<2;flag++)for(result=0;result<2;result++)for(am=0;am<2;am++)for(fm=0;fm<2;fm++){
  for(k=0;k<sizeof(output.bytes);k++)output.bytes[k]=0xa5;
  D_800D3098=(u8*)bases[n];D_800D2E4C=&info;info.unk12=flag?0x40:0;D_800E0934=0;
  audio_calls=create_calls=copy_calls=error=0;first_result=result;audio_mutation=am;factory_mutation=fm;
  func_15010880();base=bases[n]^(am?0x80000001u:0);enabled=flag^am^fm;
  if(error||audio_calls!=1||create_calls!=1+enabled||copy_calls!=result||D_800E0934!=(s32)func_150DE32C)return 11;
  if(result){if(output.bytes[40]||output.bytes[41]||*(u32*)(output.bytes+44)!=base+0xea0u||*(u32*)(output.bytes+48)!=base+0xed4u)return 12;}
  for(k=0;k<sizeof(output.bytes);k++)if((!result||k<40||k>=52)&&output.bytes[k]!=0xa5)return 13;
 }
 return 0;
}
'''
fixture=out/'native-harness.c';fixture.write_text(harness+START);runs=[]
for opt in ('-O0','-O2','-O3'):
 exe=out/('native'+opt[1:]);argv=native_command(opt)+['-ffunction-sections','-Wl,--gc-sections','-Iconker/src/libultra/io',str(src),str(fixture),'-o',str(exe)]
 p=subprocess.run(argv,cwd=root,capture_output=True,text=True);assert p.returncode==0,(argv,p.stdout,p.stderr)
 r=subprocess.run([str(exe)]);assert r.returncode==0,(opt,r.returncode)
 runs.append(opt)
controls=(('wrong-audio','func_15177410(16, 233','func_15177410(17, 233'),('wrong-hook','D_800E0934 = (s32)func_150DE32C;','D_800E0934 = 0;'),('wrong-payload-kind','tmp.unk0 = 0;','tmp.unk0 = 1;'),('wrong-payload-offset','base + 0xEA0U','base + 0xEA4U'),('wrong-payload-size','0, 0, 12, 255, 1','0, 0, 16, 255, 1'),('wrong-gate','& 0x40','& 0x20'),('wrong-copy-length','memcpy((u8 *)record + 0x28, &tmp, 12);','memcpy((u8 *)record + 0x28, &tmp, 4);'))
body=src.read_text();rejected=[]
for label,old,new in controls:
 assert body.count(old)==1,(label,body.count(old))
 candidate=out/(label+'.c');candidate.write_text(body.replace(old,new));exe=out/label
 argv=native_command('-O2')+['-ffunction-sections','-Wl,--gc-sections','-Iconker/src/libultra/io',str(candidate),str(fixture),'-o',str(exe)]
 p=subprocess.run(argv,cwd=root,capture_output=True,text=True);assert p.returncode==0,(label,p.stderr)
 r=subprocess.run([str(exe)]);assert r.returncode!=0,('ineffective control',label);rejected.append(label)
report={'optimizations':runs,'cases_each':64,'effective_controls':rejected,'ubsan_trapping':True,'callback_providers_modeled':True,'stack_padding_value_not_assumed':True};(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
