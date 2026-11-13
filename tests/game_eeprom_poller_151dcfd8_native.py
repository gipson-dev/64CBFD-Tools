from pathlib import Path
import subprocess,sys
from tools.experiments import game_eeprom_poller_151dcfd8_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
 fn=body((out/'after.c').read_text(),'func_151DCFD8')
 controls={'receive':('!= -1','== -1'),'length':('D_800E0A2C <= 0','D_800E0A2C < 0'),'write':('D_800E0A28) != 0','D_800E0A28) == 0'),'step':('D_800E0A2C -= 8','D_800E0A2C -= 7'),'address':('D_800E0A24++','D_800E0A24 += 2'),'buffer':('D_800E0A28 += 8','D_800E0A28 += 4'),'clock':('12000ULL','12001ULL'),'result':('        return 1;','        return 0;')}
 head='''#include <ultra64.h>
 OSMesgQueue *D_800E0A20;u8 D_800E0A24;u8 *D_800E0A28;s32 D_800E0A2C;u64 D_8002BD10;
 OSTimer D_80042A58;OSMesg D_80042A90;OSMesgQueue __osEepromTimerQ;
 s32 func_151DD4E0(OSMesgQueue*,u8,u8*);
 '''
 code=head+fn.replace('func_151DCFD8(', 'selected(',1)+'\n'
 for name,(old,new) in controls.items():assert old in fn,name;code+=fn.replace('func_151DCFD8(', 'bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+=r'''
 static OSMesgQueue queue;static u8 storage[128];static s32 wantmode,recv_result,write_result,mutation;static u32 recv_calls,write_calls,timer_calls,wrong;
 static u64 deadline(u64 clock){u64 product=0,q=0;u32 r=0;for(u32 i=0;i<14;i++)if(12000u&(1u<<i))product+=clock<<i;for(s32 i=63;i>=0;i--){r=(r<<1)|(u32)((product>>i)&1);if(r>=1000000u){r-=1000000u;q|=1ULL<<i;}}return q;}
 s32 osRecvMesg(OSMesgQueue *q,OSMesg *message,s32 mode){recv_calls++;if(q!=&__osEepromTimerQ||message||mode!=wantmode)wrong=1;if(mutation&1)D_800E0A2C=9;return recv_result;}
 s32 func_151DD4E0(OSMesgQueue *q,u8 address,u8 *buffer){write_calls++;if(q!=&queue||address!=255||buffer!=storage)wrong=1;if(mutation&2){D_800E0A2C=17;D_800E0A24=254;D_800E0A28=storage+16;}return write_result;}
 int osSetTimer(OSTimer *timer,OSTime count,OSTime interval,OSMesgQueue *q,OSMesg message){timer_calls++;if(timer!=&D_80042A58||count!=deadline(D_8002BD10)||interval||q!=&__osEepromTimerQ||message!=&D_80042A90)wrong=1;return -99;}
 typedef s32 (*Fn)(s32);
 static int check(Fn fn){
  static const s32 lengths[]={-1,0,1,8,9},modes[]={0,1};static const u64 clocks[]={0ULL,0xffffffffULL,0x100000000ULL,0xffffffffffffffffULL};
  for(u32 pending=0;pending<2;pending++)for(u32 recv=0;recv<2;recv++)for(u32 len=0;len<5;len++)for(u32 write=0;write<2;write++)for(u32 mode=0;mode<2;mode++)for(u32 clk=0;clk<4;clk++)for(u32 mut=0;mut<4;mut++){
   D_800E0A20=pending?&queue:(OSMesgQueue*)0;D_800E0A24=255;D_800E0A28=storage;D_800E0A2C=lengths[len];D_8002BD10=clocks[clk];wantmode=modes[mode];recv_result=recv?-1:0;write_result=write?-1:0;mutation=mut;recv_calls=write_calls=timer_calls=wrong=0;
   s32 result=fn(wantmode);s32 n=(mut&1)&&pending?9:lengths[len];u32 expected_recv=pending,expected_write=pending&&!recv&&n>0,expected_timer=expected_write&&!write;
   if(wrong||recv_calls!=expected_recv||write_calls!=expected_write||timer_calls!=expected_timer||result!=(s32)expected_timer)return 1;
   if(!pending){if(D_800E0A20||D_800E0A2C!=lengths[len]||D_800E0A24!=255||D_800E0A28!=storage)return 1;}
   else if(recv){if(D_800E0A20!=&queue||D_800E0A2C!=n||D_800E0A24!=255||D_800E0A28!=storage)return 1;}
   else if(n<=0||write){if(D_800E0A20||D_800E0A2C)return 1;}
   else {s32 after=(mut&2)?17:n;u8 addr=(mut&2)?254:255;u8 *buf=(mut&2)?storage+16:storage;if(D_800E0A20!=&queue||D_800E0A2C!=after-8||D_800E0A24!=(u8)(addr+1)||D_800E0A28!=buf+8)return 1;}
  }
  return 0;
 }
 static int run(void){if(check(selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=out/'native.c';path.write_text(code);runtime=Path('/lib/i386-linux-gnu/libgcc_s.so.1');assert runtime.is_file()
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run([x for x in native_command(opt) if x!='-static']+['-fno-strict-aliasing','-mstackrealign',str(path),str(runtime),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
  print(opt,'1280 native cases and',len(controls),'negative controls passed',flush=True)
