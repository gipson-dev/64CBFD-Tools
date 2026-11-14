from pathlib import Path
import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
p=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=p/'conker/build/game-selector-mask-1515942c-screen';source=Path(__import__('os').environ.get('SELECTOR_SOURCE',out/'selected.c')).read_text();lo=source.index('s32 func_1515942C(');hi=source.index('\n}\n',lo)+2;source=source[lo:hi]
prefix=r'''#include <ultra64.h>
static u32 actorWords[0x300/4],nodeWords[0x40/4],dataWords[0x80/4];
s32 func_1514ECE0(void *node,s16 key,void **out){if(key!=0x13)return 0;*out=node;return node!=0;}
'''
harness=r'''
static u32 selector(s16 v,int offset,u32 all){return v==-1?all:(1U<<(((s32)v+offset)&31));}
static int model(s16 *v,u8 *d){u32 wanted=selector(v[0],0,7)|selector(v[1],3,0x38)|selector(v[2],6,0x1c0)|selector(v[3],9,0x1e00)|selector(v[4],13,0x3e000);u32 actual=(1U<<(d[0]&31))|(1U<<((d[1]+3)&31))|(1U<<((d[2]+6)&31))|(1U<<((d[3]+9)&31))|(1U<<((d[4]+13)&31));return (wanted|actual)==wanted;}
static int run(void){u8 *actor=(u8 *)actorWords,*node=(u8 *)nodeWords,*data=(u8 *)dataWords;s16 v[5];int checks=0;*(void **)(actor+0x2f4)=node;*(void **)(node+0x10)=data;
 for(int i=0;i<5;i++)data[0x2c+i]=i;
 for(int field=0;field<5;field++)for(int x=-32768;x<=32767;x++){
  for(int j=0;j<5;j++)v[j]=-1;v[field]=(s16)x;
  if(func_1515942C(actor,v[0],v[1],v[2],v[3],v[4])!=model(v,data+0x2c))return 42;checks++;
 }
 for(int j=0;j<5;j++)v[j]=-1;
 for(int field=0;field<5;field++)for(int x=0;x<256;x++){
  for(int i=0;i<5;i++)data[0x2c+i]=i;data[0x2c+field]=(u8)x;
  if(func_1515942C(actor,v[0],v[1],v[2],v[3],v[4])!=model(v,data+0x2c))return 42;checks++;
 }
 return checks==328960?0:20;
}
'''
(out/'native.c').write_text(prefix+source+harness+START)
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=out/('native'+opt+alias);p=subprocess.run(native_command(opt)+['-mstackrealign',alias,'-o',str(exe),str(out/'native.c')],capture_output=True,text=True);assert p.returncode==0,p.stderr
  r=subprocess.run([str(exe)],capture_output=True);print(opt,alias,'exit',r.returncode,flush=True);assert r.returncode==0
c=(out/'native.c').read_text();old='((fourth + 9) & 31)';assert c.count(old)==1;wrong=out/'native-control.c';wrong.write_text(c.replace(old,'((fourth + 9) & 15)'))
for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
 exe=out/('negative'+alias);p=subprocess.run(native_command('-O2')+['-mstackrealign',alias,'-o',str(exe),str(wrong)],capture_output=True,text=True);assert p.returncode==0,p.stderr
 r=subprocess.run([str(exe)],capture_output=True);print('control',alias,'exit',r.returncode,flush=True);assert r.returncode==42
