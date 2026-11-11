import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_resource_table_loader_150163d0_match as p
out=p.out;root=p.root
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-selected.c').read_text(),'func_150163D0')
 controls={
  'mode':(' 3, 12, resource, 9',' 2, 12, resource, 9'),
  'file':(' 3, 12, resource, 9',' 3, 11, resource, 9'),
  'kind':(' 3, 12, resource, 9',' 3, 12, resource, 8'),
  'success':(' > 0)', ' >= 0)'),
  'count':('count++','count += 2'),
  'stride':('cursor += 2','cursor += 4'),
  'destination':('D_800D18B0[i * 2] +=','D_800D18B0[i * 2 + 1] +='),
  'base':('+= (u32)D_800D18B0','+= (u32)D_800D18B0 + 4'),
  'failure':('D_800D18B0 = NULL','D_800D18B0 = (u32 *)1'),
 }
 code=r'''#include <ultra64.h>
 #include <stdarg.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 u32 *D_800D18B0; static u32 table[64];static u32 answer,expected_resource;static int errors;
 u32 func_1502B7F0(void **out,u32 depth,...){va_list ap;u32 kind,resource,flags;va_start(ap,depth);kind=va_arg(ap,u32);resource=va_arg(ap,u32);flags=va_arg(ap,u32);va_end(ap);if(out!=(void**)&D_800D18B0||depth!=3||kind!=12||resource!=expected_resource||flags!=9)errors++;*out=table;return answer;}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_150163D0','test_'+key,1)+'\n'
 code+=r'''
 typedef void (*T)(u32);
 static int check(T test){u32 n,i,j,before[64],results[]={0,1,0x7fffffff,0x80000000,0xffffffff};
  for(n=0;n<13;n++)for(j=0;j<5;j++){for(i=0;i<64;i++)table[i]=i<28?0xFEED0000+i:0;for(i=0;i<n;i++)table[2*i]=0x80+7*i;table[2*n]=0;for(i=0;i<64;i++)before[i]=table[i];D_800D18B0=(u32*)1;answer=results[j];expected_resource=n+19;errors=0;test(expected_resource);
  if(errors)return 1;if((s32)answer>0){if(D_800D18B0!=table)return 2;for(i=0;i<n;i++)before[2*i]+=(u32)table;}else if(D_800D18B0!=NULL)return 3;
  for(i=0;i<64;i++)if(table[i]!=before[i])return 4;
  }return 0;}
 static int run(void){if(check(test_selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_150163D0_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_150163D0_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=65,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,valid_disjoint_table_only=True,source_installed=False);(out/'native_150163D0_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
