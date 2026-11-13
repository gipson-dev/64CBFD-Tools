from tools.experiments import game_checksum_record_spawn_match as packet
from pathlib import Path
import subprocess
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
 O=packet.OUT;src=(O/'candidate.c').read_text();f=body(src,'func_150AEB9C');decl=src[:src.index('void func_150AEB9C(')]
 controls={'checksum':('<< 1','<< 2'),'rows':(' + 0x22C',' + 0x228'),'lifetime':('entry->lifetime','entry->lifetime + 1'),'factory':('0x27, 8, 0xff','0x26, 8, 0xff'),'owner':('owner[0x3B]','owner[0x3A]'),'kind':('.kind','.pad')}
 code='#include <ultra64.h>\nextern u8 D_800DCE50[0x340];\nvoid *func_151491F4(s16,s8,s8,u8,u8,s32,u8,s32);\n'+decl+'\n'+f.replace('func_150AEB9C(','selected(',1)+'\n'
 for k,(old,new) in controls.items():
  assert f.count(old)==1,(k,old);code+=f.replace('func_150AEB9C(','bad_'+k+'(',1).replace(old,new,1)+'\n'
 code+=r"""
 __asm__(".data\n.align 4\n.globl func_15001A08\nfunc_15001A08:\n.space 252\n.long 0x5a7216b0\n.globl D_15001B08\nD_15001B08:\n.text\n");
 u8 D_800DCE50[0x340];s32 D_800886E0;ChecksumRecordEntry *D_800886E4;
 static ChecksumRecordEntry table[4],other[4];static u32 owner[256],out[4][64];
 static u32 mode,fail,calls,broken;
 void *func_151491F4(s16 a,s8 b,s8 c,u8 d,u8 e,s32 f,u8 g,s32 h){
  u32 n=calls++;ChecksumRecordEntry *p=D_800886E4+n;
  if(a!=p->lifetime||b!=0||c!=-1||d!=1||e!=0x27||f!=8||g!=255||h!=0)broken=1;
  if(n==0){if(mode&1)D_800886E0=1;if(mode&2)D_800886E4=other;if(mode&4)((u8*)owner)[0x3b]^=0x5a;}
  return n==fail?0:(u8*)out[n];
 }
 typedef void (*Fn)(u8 *);
 static int check(Fn fn){u32 count,mismatch,i;for(count=0;count<4;count++)for(mismatch=0;mismatch<2;mismatch++)for(mode=0;mode<8;mode++)for(fail=0;fail<4;fail++){
  u32 expectedCalls=0;u32 *window=(u32*)func_15001A08;u8 *a=(u8*)owner;
  for(i=0;i<0x340;i++)D_800DCE50[i]=0xa5;for(i=0;i<4;i++){table[i].kind=0x30+i;table[i].pad=0x11+i;table[i].lifetime=-300+i*47;other[i].kind=0x70+i;other[i].pad=0x21+i;other[i].lifetime=-300+i*47;}
  for(i=0;i<sizeof(owner);i++)a[i]=(u8)(i*29+0x5a);for(i=0;i<sizeof(out);i++)((u8*)out)[i]=0xa5;
  window[63]=0x5a7216b0u^(mismatch?1u:0u);D_800886E0=count;D_800886E4=table;broken=calls=0;fn(a);
  if(broken)return 1;
  if(*(u32*)(D_800DCE50+0x8c)!=(mismatch?0:0xa5a5a5a5u)||*(u32*)(D_800DCE50+0x22c)!=(mismatch?0:0xa5a5a5a5u))return 2;
  while(expectedCalls<count){u32 n=expectedCalls++;if(n==fail)break;if((mode&1)&&n==0)break;}
  if(calls!=expectedCalls)return 3;
  for(i=0;i<expectedCalls;i++)if(i!=fail){u8 *x=(u8*)out[i];u8 identity=(u8)(0x3b*29+0x5a);if(mode&4)identity^=0x5a;
   if(*(u8**)(x+0x28)!=a||x[0x2c]!=identity||x[0x2d]!=(u8)(((mode&2)?0x70:0x30)+i))return 4;}
  }
  return 0;}
 static int run(void){if(check(selected))return 10;
 """
 for i,k in enumerate(controls):code+='if(!check(bad_'+k+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 (O/'native.c').write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=O/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(O/'native.c'),'-o',str(exe)],capture_output=True,text=True);assert not r.returncode,r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert not r.returncode,(opt,r.returncode,r.stderr)
  print(opt,'256 cases, 6 effective negative controls, UBSan')
