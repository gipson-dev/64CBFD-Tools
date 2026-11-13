from pathlib import Path
import subprocess,sys
from tools.experiments.game_slot_notification_15156028_match import ROOT as root, OUT as out
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
fn=body((out/'durable-after.c').read_text(),'func_15156028')
controls={'kind':fn.replace('kind == 0x2D','kind == 0x2E'),'release':fn.replace('kind == 0)','kind == 1)'),'bounds':fn.replace('first < 25','first < 26'),'divide':fn.replace('/ 0x32C','/ 0x32D'),'firstswap':fn.replace('record[0x10] = second;','record[0x10] = first;'),'secondswap':fn.replace('record[0x10] = first;','record[0x10] = second;'),'secondtest':fn.replace('second == record[0x10]','first == record[0x10]'),'remove':fn.replace('func_1516972C((struct102 *)record);',';')};assert all(v!=fn for v in controls.values())
unit='''#include <ultra64.h>\n#include "structs.h"\ntypedef char SlotABI[(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(struct127)==0x32c && __builtin_offsetof(struct127,unique_id)==0x3b)?1:-1];\nstruct127 D_800CC2D0[26];
typedef union {u32 alignment; u8 data[256];} Area;static Area actual,wanted;static int releases,error;static u8 *expectedRecord;
void func_1516972C(struct102 *ptr){u8*p=(u8*)ptr;if(p!=expectedRecord)error=1;p[17]^=0x5a;releases++;}
'''
for name,text in {'selected':fn,**controls}.items():unit+='\n'+text.replace('func_15156028(',name+'(',1)+'\n'
unit+='''
typedef void(*Target)(void*,s32,u8);
static const u32 offsets[]={0xfffffcd4u,0xfffffcd5u,0xffffffffu,0,812,19488,20300,0x7fffffffu};
static s32 q(u32 value){return (s32)(value-(u32)D_800CC2D0)/812;}
static int check(Target target){u32 i,j,k,c,alias,x;static const u8 tags[]={0,1,24,255},kinds[]={0,45,2,255};
 for(i=0;i<8;i++)for(j=0;j<8;j++)for(k=0;k<4;k++)for(c=0;c<4;c++)for(alias=0;alias<2;alias++){
  u8*record=actual.data+(alias?48:8);u8*event=actual.data+64;u8*wr=wanted.data+(alias?48:8);u8*we=wanted.data+64;s32 first,second;int expectedReleases=0;
  for(x=0;x<256;x++)actual.data[x]=(u8)(x*11+7);
  *(u32*)(void*)event=(u32)D_800CC2D0+offsets[i];*(u32*)(void*)(event+4)=(u32)D_800CC2D0+offsets[j];record[16]=tags[k];
  for(x=0;x<256;x++)wanted.data[x]=actual.data[x];
  if(kinds[c]==0){first=q(*(u32*)(void*)we);if(first>=0&&first<25&&first==wr[16]){wr[17]^=0x5a;expectedReleases=1;}}
  else if(kinds[c]==45){first=q(*(u32*)(void*)we);second=q(*(u32*)(void*)(we+4));if(first>=0&&first<25&&second>=0&&second<25){if(first==wr[16])wr[16]=(u8)second;else if(second==wr[16])wr[16]=(u8)first;}}
  releases=error=0;expectedRecord=record;target(record,(s32)event,kinds[c]);if(error||releases!=expectedReleases)return 1;
  for(x=0;x<256;x++)if(actual.data[x]!=wanted.data[x])return 2;
 }return 0;
}
static int run(void){if(check(selected))return 10;\n'''
for i,name in enumerate(controls):unit+='if(!check('+name+'))return '+str(20+i)+';\n'
unit+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
src=out/'native-abi-screen.c';src.write_text(unit)
for opt in ('O0','O2','O3'):
 exe=out/('native-abi-'+opt);p=subprocess.run([*native_command('-'+opt,True),'-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert p.returncode==0,(opt,p.stderr);p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stderr)
print('native32 at O0/O2/O3: 2048 cases each, 8 effective semantic controls, trapping UBSan',flush=True)
