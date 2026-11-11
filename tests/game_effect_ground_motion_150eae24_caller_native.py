import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_effect_ground_motion_150eae24_match as p
out=p.out;root=p.root
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 src=(out/'caller-install.c').read_text();selected=body(src,'func_151603FC').replace('    s32 pad;\n','')
 assert ')(arg0) == 0' in selected
 controls={'wrong_arg':(')(arg0) == 0',')(other) == 0'),'wrong_result':(')(arg0) == 0',')(arg0) != 0'),'wrong_tick':('arg0->unk10 -= D_800BE9E4','arg0->unk10 += D_800BE9E4')}
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u8 pad[14];u8 unkE;s8 unkF;s16 unk10;} struct225;
 static struct225 record,otherRecord;static struct225 *other=&otherRecord;s32 D_800BE9E4;static int seen,cleaned,answer,bad;
 s32 callback(struct225 *p){seen++;if(p!=&record)bad=1;return answer;}
 s32 (*D_8008B0F0[24])(void);
 void func_1516972C(struct225 *p){cleaned++;if(p!=&record)bad=1;}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_151603FC','test_'+key,1)+'\n'
 code+=r'''
 typedef void(*Fn)(struct225*);
 static int check(Fn test){int expiry,index,flag;for(expiry=0;expiry<2;expiry++)for(index=0;index<2;index++)for(flag=0;flag<2;flag++)for(answer=0;answer<2;answer++){
  int expectSkip=expiry&&flag;record.unkE=flag;record.unkF=index?19:-1;record.unk10=expiry?0:5;D_800BE9E4=1;D_8008B0F0[19]=(s32(*)(void))(void (*)(void))callback;seen=cleaned=bad=0;test(&record);
  if(bad||seen!=(!expectSkip && index)||cleaned!=(expectSkip||(!expectSkip&&index&&!answer)))return 1;
  if(record.unk10!=(flag?(expiry?-1:4):(expiry?0:5)))return 2;
  }return 0;}
 static int run(void){if(check(test_selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'caller-native-screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('caller-native-screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=16,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,callback_type_tested_for_target=True,other_table_entry_types_not_qualified=True,source_installed=False);(out/'caller-native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
