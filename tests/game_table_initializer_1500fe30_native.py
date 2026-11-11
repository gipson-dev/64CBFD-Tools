"""Private SDK32 table-initializer screen with helper mutation controls."""
import json,subprocess
from tools.experiments import game_table_initializer_1500fe30_match as p
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=p.body((p.out/'selected-source.c').read_text(),p.NAME)
 controls={'group':('i / 5','i / 4'),'marker':('marker = -1','marker = -2'),
           'modulus':('func_150ADA20() % 5','func_150ADA20() % 4'),
           'loop_count':('i < 10; i++','i < 9; i++'),
           'allocation_size':('allocate_memory(100, 1, 0, 0)','allocate_memory(96, 1, 0, 0)'),
           'zero_size':('bzero(D_800BE4E0, 100)','bzero(D_800BE4E0, 96)'),
           'finish_arg':('func_150C851C(100)','func_150C851C(99)'),
           'first_copy':('D_800BE4E0[0].next','D_800BE4E0[0].choice'),
           'last_copy':('D_800BE4E0[i + 3].next','D_800BE4E0[i + 3].choice')}
 code='''#include <ultra64.h>\n'''+r'''
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u8 group;u8 pad1;s8 marker;u8 pad3;s16 choice;s16 previous;s16 next;} Entry10;
 _Static_assert(sizeof(Entry10)==10,"retail entry size");
 static u32 a_words[32],b_words[32],ea_words[32],eb_words[32];
 static u8 *a=(u8*)a_words,*b=(u8*)b_words,*ea=(u8*)ea_words,*eb=(u8*)eb_words;
 Entry10 *D_800BE4E0;static int mutation,seed,stage,ordinal,bad;
 void *allocate_memory(s32 size,s32 flag,s32 x,s32 y){if(stage++!=0||size!=100||flag!=1||x||y)bad=1;return a;}
 void bzero(void *ptr,int size){int i;if(stage++!=1||ptr!=a||size!=100)bad=1;for(i=0;i<size;i++)((u8*)ptr)[i]=0;}
 u32 func_150ADA20(void){u32 value;if(stage++!=2+ordinal||ordinal>=10)bad=1;
  if(mutation&&ordinal==2)D_800BE4E0=(Entry10*)b;if(mutation&&ordinal==6)D_800BE4E0=(Entry10*)a;
  value=0xffffffffu-7u*(u32)ordinal-(u32)seed*29u;ordinal++;return value;}
 void func_150C851C(s32 n){int i;if(stage++!=12||n!=100)bad=1;if(mutation)D_800BE4E0=(Entry10*)b;
  for(i=0;i<10;i++)D_800BE4E0[i].next=(s16)(i*101+seed*13-200);}
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace(p.NAME,'test_'+name,1)+'\n'
 code+=r'''
 static void reference(void){int i;Entry10 *cur=(Entry10*)ea;for(i=0;i<100;i++)ea[i]=0;
  for(i=0;i<10;i++){
   cur[i].group=(u8)(i/5);cur[i].marker=-1;
   if(mutation&&i==2)cur=(Entry10*)eb;if(mutation&&i==6)cur=(Entry10*)ea;
   cur[i].choice=(s16)((0xffffffffu-7u*(u32)i-(u32)seed*29u)%5u);
  }
  if(mutation)cur=(Entry10*)eb;
  for(i=0;i<10;i++)cur[i].next=(s16)(i*101+seed*13-200);
  for(i=0;i<10;i++)cur[i].previous=cur[i].next;
 }
 typedef void(*Test)(void);
 static int check(Test fn){u32 i;for(mutation=0;mutation<2;mutation++)for(seed=0;seed<4;seed++){
  for(i=0;i<128;i++){a[i]=ea[i]=(u8)(i*29+seed*11+0x5a);b[i]=eb[i]=(u8)(i*29+seed*11+0x5a);}
  stage=ordinal=bad=0;D_800BE4E0=(Entry10*)0x12345678u;reference();fn();
  if(bad||stage!=13||ordinal!=10||D_800BE4E0!=(Entry10*)(mutation?b:a))return 1;
  for(i=0;i<128;i++)if(a[i]!=ea[i]||b[i]!=eb[i])return 1;
  }return 0;}
 static int run(void){if(check(test_selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=p.out/'native-screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=p.out/('native-screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=p.root,capture_output=True,text=True)
  assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr)
  reports[opt]=dict(cases=8,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helpers_modeled=True,global_pointer_mutations=True,null_allocation_excluded=True,source_installed=False)
 (p.out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
