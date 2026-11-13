"""Check defined native32 dispatch behavior and effective negative controls."""
import subprocess
from tools.experiments import game_owner_mode_1514ea1c_direct as packet
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run():
    function=body(packet.MANIFEST['selected_source'],'func_1514EA1C')
    controls={
        'conditional':('owner[0x22] == 2','owner[0x22] == 1'),
        'case4':('case 4: func_1518E37C(owner, 3)','case 4: func_1518E37C(owner, 4)'),
        'case7':('case 7: func_1518E37C(owner, 5)','case 7: func_1518E37C(owner, 4)'),
        'case10':('case 10: func_1518E37C(owner, 6)','case 10: func_1518E37C(owner, 7)'),
        'case12':('case 12: func_1518E37C(owner, 2)','case 12: func_1518E37C(owner, 3)'),
        'context':('func_1514E89C(owner, mode, context)','func_1514E89C(owner, mode, 0)'),
        'handled':('    return 1;\n}', '    return 0;\n}'),
    }
    code='''#include <ultra64.h>\nvoid func_1518E37C(u8 *,u8);s32 func_1514E89C(u8 *,s32,s32);\n'''+function.replace('func_1514EA1C(','selected(',1)+'\n'
    for name,(old,new) in controls.items():
        assert old in function,name
        code+=function.replace('func_1514EA1C(','bad_'+name+'(',1).replace(old,new,1)+'\n'
    code+=r'''
static u8 owner[128];static int setcalls,defaultcalls,bad;static s32 expected_mode,expected_context,delegate_result;static u8 value;
void func_1518E37C(u8 *p,u8 v){if(p!=owner)bad=1;setcalls++;value=v;owner[0x23]=v;}
s32 func_1514E89C(u8 *p,s32 mode,s32 context){if(p!=owner||mode!=expected_mode||context!=expected_context)bad=1;defaultcalls++;return delegate_result;}
typedef s32 (*Fn)(u8 *,s32,s32);
static int check(Fn fn){
 static const s32 modes[]={(-2147483647-1),-2,-1,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,2147483647};
 static const u8 states[]={0,1,2,3,255};static const s32 returns[]={0,1,(s32)0x87654321u};static const s32 contexts[]={0,1,(s32)0x87654321u};
 for(int i=0;i<19;i++)for(int j=0;j<5;j++)for(int k=0;k<3;k++)for(int t=0;t<3;t++){
  for(int x=0;x<128;x++)owner[x]=(u8)(x*7+1);owner[0x22]=states[j];setcalls=defaultcalls=bad=0;value=0;
  expected_mode=modes[i];expected_context=contexts[k];delegate_result=returns[t];s32 result=fn(owner,modes[i],contexts[k]);
  if(modes[i]>=3&&modes[i]<=12){
   static const u8 codes[]={3,3,2,5,5,2,6,6,2,2};u8 want=codes[modes[i]-3];
   if((modes[i]==3||modes[i]==6||modes[i]==9)&&states[j]!=2)want=2;
   if(bad||setcalls!=1||defaultcalls||value!=want||owner[0x23]!=want||result!=1)return 1;
  }else if(bad||setcalls||defaultcalls!=1||result!=returns[t])return 1;
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''
    for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
    code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    path=packet.OUT/'native.c';path.write_text(code)
    for opt in ('-O0','-O2','-O3'):
        exe=packet.OUT/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True)
        assert r.returncode==0,r.stderr
        r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
