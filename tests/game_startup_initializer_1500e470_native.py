import subprocess,sys,json
from pathlib import Path
from tools.experiments import game_startup_initializer_1500e470_match as p
out=p.out;root=p.root
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 s=(out/'selected-source.c').read_text();selected=body(s,'func_1500E470')
 controls={'sentinel':('D_800DD190 = -1','D_800DD190 = 0'),'zero_size':('bzero(&D_800DD198, 24)','bzero(&D_800DD198, 23)'), 'flag':('D_800DD404 = 0xFF','D_800DD404 = 0xFE'), 'table':('D_800BE4E0 = 0','D_800BE4E0 = 1'), 'result':('D_800E0A10 = value','D_800E0A10 = value + 1'), 'constant':('func_151EF640(64)','func_151EF640(63)'), 'arg':('func_151732E0(arg0)','func_151732E0(arg0 + 1)'), 'final_flag':('(D_800D2E4C->unk4 & 128) == 0','(D_800D2E4C->unk4 & 128) != 0')}
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u8 pad[10];u8 unkA;} Control;
 typedef struct {u8 pad[4];u8 unk4;} Flags;
 static Control control;static Flags flags;Control *D_800B0DF0=&control;Flags *D_800D2E4C=&flags;
 s8 D_800DD190;u8 D_800DD198[24],D_800DD404,D_800DD405,D_800DD406,D_8008CD00,D_80088B60,D_800E0A10;
 s32 D_800E0930,D_800E0934,D_800E0940,D_800BE4E0;
 static int logv[32],n,bad,seed,expected_flag;static void logcall(int v){logv[n++]=v;}
 void bzero(void *p,int size){int i;logcall(1);if(p!=D_800DD198||size!=24)bad=1;for(i=0;i<size;i++)((u8*)p)[i]=0;}
 u8 func_15012720(void){logcall(2);return 0xa0+seed;}
 void func_15012370(void){logcall(3);if(D_800E0A10!=(u8)(0xa0+seed))bad=1;}
 void func_151EF640(int v){logcall(4);if(v!=64)bad=1;}
 void func_151732E0(int v){logcall(5);if(v!=0x12345678)bad=1;}
 void func_15004FE0(int v){logcall(6);if(v!=0x12345678)bad=1;}
 void func_150127B0(void){logcall(7);}void func_1519582C(void){logcall(8);}void func_15008BE0(void){logcall(9);}void func_15008B90(void){logcall(10);}void func_1500E5C0(void){logcall(11);}
 void callback1(void){logcall(12);}void callback2(void){logcall(12);}void (*D_80082D90[])(void)={0,callback1,callback2};
 void func_1500ABA0(int v){logcall(13);if(v!=0x12345678)bad=1;}void func_1500BEC0(void){logcall(14);}void func_1500AC14(void){logcall(15);}void func_151872B0(int v){logcall(16);if(v!=0x12345678)bad=1;}void func_15178EB0(void){logcall(17);}void func_15012FE0(void){logcall(18);}void func_151645C4(int v){logcall(19);if(v!=expected_flag)bad=1;}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_1500E470','test_'+key,1)+'\n'
 code+=r'''
 typedef void(*T)(s32);
 static int check(T test){int i,sel,flag;for(sel=0;sel<3;sel++)for(flag=0;flag<2;flag++)for(seed=0;seed<2;seed++){
  n=bad=0;control.unkA=sel;flags.unk4=flag?128:0;expected_flag=!flag;
  D_800DD190=0;D_800DD404=D_800DD405=D_800DD406=D_8008CD00=D_80088B60=D_800E0A10=42;D_800E0930=D_800E0934=D_800E0940=D_800BE4E0=42;
  for(i=0;i<24;i++)D_800DD198[i]=42;test(0x12345678);
  if(bad||D_800DD190!=-1||D_800DD404!=255||D_800DD405||D_800DD406||D_8008CD00||D_80088B60||D_800E0930||D_800E0934||D_800E0940||D_800BE4E0||D_800E0A10!=(u8)(0xa0+seed))return 1;
  for(i=0;i<24;i++)if(D_800DD198[i])return 2;
  if(n!=18+(sel!=0))return 3;
  for(i=0;i<11;i++)if(logv[i]!=i+1)return 4;
  if(sel && logv[11]!=12)return 5;
  for(i=0;i<7;i++)if(logv[11+(sel!=0)+i]!=13+i)return 6;
  }return 0;}
 static int run(void){if(check(test_selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native-screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native-screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=12,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helpers_modeled=True,source_installed=False);(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
