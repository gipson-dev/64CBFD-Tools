"""Private SDK32 initialization callback screen and effective negative controls."""
import json,subprocess
from tools.experiments import game_init_callback_1500ffcc_match as p
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=p.body((p.out/'selected-source.c').read_text(),p.NAME)
 controls={
  'first_kind':('300, -1, 18, 0','300, -1, 19, 0'),
  'second_kind':('300, -1, 23, -1','300, -1, 24, -1'),
  'second_setup':('0, 1, 0, -4','0, 0, 0, -4'),
  'first_zero':('first = 0.0f;','first = 1.0f;'),
  'pair_zero':('pair[0] = 0.0f;','pair[0] = 1.0f;'),
  'first_gate':('if (record != 0)','if (record != 0 && 0)'),
  'second_gate':('if (D_80088870 != 0)','if (D_80088870 != 0 && 0)'),
  'second_copy':('D_80088870 + 0x28, pair, 8','D_80088870 + 0x28, pair, 4'),
  'sound_call':('func_1500FF9C();','func_1500FE30();')}
 code='''#include <ultra64.h>\n#include <string.h>\n'''+r'''
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 s32 D_800B0E00,D_800B0E04,D_800902DC;u8 *D_80088870;
 static u32 firstbuf[32],secondbuf[32];static u8 *rec1=(u8*)firstbuf,*rec2=(u8*)secondbuf;
 static int alloc1,alloc2,mutation,bad,stage,setup_count,copies;
 void *func_15195AA8(s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,s32 h){
  int ordinal=setup_count++;if(stage++!=ordinal || a!=(ordinal?D_800B0E04:D_800B0E00)||b!=D_800902DC||c!=1||d!=-1||e!=0||f!=ordinal||g!=0||h!=-4)bad=1;
  if(!ordinal && mutation){D_800B0E04=(s32)0x12344321u;D_800902DC=(s32)0xfedcba98u;}return 0;
 }
 s32 func_1500FE30(void){if(stage++!=2)bad=1;return 0;}
 void func_1500FF9C(void){if(stage++!=3)bad=1;}
 u8 *func_151491F4(s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,s32 h){
  if(stage++!=4||a!=300||b!=-1||c!=18||d!=0||e!=14||f!=4||g!=255||h!=0)bad=1;return alloc1?rec1:0;
 }
 u8 *func_15149130(s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,s32 h,s32 i){
  if(stage++!=(5+alloc1)||a!=300||b!=-1||c!=23||d!=-1||e!=0||f!=20||g!=8||h!=255||i!=1)bad=1;return alloc2?rec2:0;
 }
 void *memcpy(void *d,const void *s,size_t size){u32 i;u8 *dst=d;const u8 *src=s;
  if((stage==5 && (!alloc1||dst!=rec1+0x28||size!=4))||(stage!=5 && (stage!=6+alloc1||!alloc2||dst!=rec2+0x28||size!=8)))bad=1;
  stage++;copies++;for(i=0;i<size;i++){if(src[i])bad=1;dst[i]=src[i];}return d;
 }
 '''
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace(p.NAME,'test_'+name,1)+'\n'
 code+=r'''
 typedef void(*Test)(void);
 static int check(Test fn){u32 i;int seed;for(alloc1=0;alloc1<2;alloc1++)for(alloc2=0;alloc2<2;alloc2++)for(mutation=0;mutation<2;mutation++)for(seed=0;seed<2;seed++){
  D_800B0E00=(s32)0x12345678u;D_800B0E04=(s32)0x87654321u;D_800902DC=(s32)0x11223344u;D_80088870=(u8*)0x77889900u;
  for(i=0;i<128;i++)rec1[i]=rec2[i]=(u8)(i*29+seed*11+0x5a);
  bad=stage=setup_count=copies=0;fn();
  if(bad||setup_count!=2||stage!=6+alloc1+alloc2||copies!=alloc1+alloc2||D_80088870!=(alloc2?rec2:0))return 1;
  for(i=0;i<128;i++){
   u8 initial=(u8)(i*29+seed*11+0x5a),a=alloc1&&i>=0x28&&i<0x2c?0:initial,b=alloc2&&i>=0x28&&i<0x30?0:initial;
   if(rec1[i]!=a||rec2[i]!=b)return 1;
  }
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
  reports[opt]=dict(cases=16,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helpers_modeled=True,bounded_allocations=True,source_installed=False,byte_exact=False)
 (p.out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
