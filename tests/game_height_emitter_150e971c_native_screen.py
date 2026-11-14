"""Uncredited native32 ordering screen for the private callback candidates."""
from pathlib import Path
import json,os,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-height-emitter-150e971c-durable'
source=(out/'padded.c').read_text();pos=source.index('typedef struct HeightEmissionDescriptor113D60');body=source[pos:]
prefix='''#include <ultra64.h>
typedef struct struct210 struct210;
f32 func_150ADA68(void); s32 func_150ADA20(void);
'''
harness='''
struct struct210 { s32 unused; };
static union { u32 w[0x1b0/4]; f32 f[0x1b0/4]; u8 b[0x1b0]; } actor;
static int mode, calls, error;
s32 func_151337C0(u8 *p) { calls++; if(p!=actor.b) error=1; if(mode&1) actor.f[0x3c/4]=-3.0f; return 1; }
f32 func_150ADA68(void) { calls++; return 0.25f; }
s32 func_150ADA20(void) { calls++; if(mode&2) { actor.f[0x38/4]=9.0f; actor.f[0x170/4]=15.0f; actor.b[1]=0xa9; } return 0x123456ab; }
struct210 *func_1513C73C(s32 ptr,u8 a,u8 b,s32 context,f32 x,f32 y,f32 z,f32 range,f32 range2,u8 r,u8 d,s32 e,u8 slot,s32 tag) {
 HeightEmissionDescriptor113D60 *p=(HeightEmissionDescriptor113D60 *)ptr; calls++;
 if(a||b||context!=(s32)(actor.b+0x178)||z!=6.f||range!=25.f||range2!=25.f||r!=0xab||d||e||slot!=0x52)error=2;
 if(x!=((mode&2)?9.f:4.f))error=10;
 if(y!=((mode&2)?20.f:15.f))error=11;
 if(tag!=((mode&2)?0xa9:0x67))error=12;
 if(p->flags!=0x9701||p->lifetime!=100||p->kind!=11||p->field07||p->field08||p->field0c||p->field10!=255||p->field11!=255||p->field12!=255||p->field13!=255||p->field14!=255||p->field15!=255||p->field16||p->field17!=7||p->resource!=0x3b0003||p->field22!=20||p->field24!=12)error=3;
 return 0;
}
static int run(void) {
 int cases=0;
 for(int h=0;h<3;h++)for(int flag=0;flag<2;flag++)for(mode=0;mode<4;mode++) {
  for(int i=0;i<0x1b0/4;i++)actor.w[i]=0;
  actor.f[0x38/4]=4.f; actor.f[0x3c/4]=h==0?0.f:h==1?10.f:11.f;actor.f[0x40/4]=6.f;actor.f[0x170/4]=10.f;
  actor.w[0x174/4]=flag?10:9;actor.b[0x0c]=0x52;actor.b[1]=0x67;calls=error=0;
  int less=(mode&1)||h==0;int result=func_150E971C(actor.b);
  if(error||result!=!less||calls!=(less&&flag?4:1))return 1+error;
  cases++;
 }
 return cases==24?0:10;
}
'''
compiled=(out/'snapshot.c').read_text();snapshot=compiled[compiled.index('typedef struct HeightEmissionDescriptor113D60'):]
assert snapshot.count('random = func_150ADA20();')==1 and snapshot.count('(random & 255)')==1
def run(label,code,opt,alias):
 src=out/'native-screen.c';exe=out/('native-'+label+opt+'-'+alias);src.write_text(prefix+code+harness+START)
 p=subprocess.run(native_command(opt)+['-mstackrealign','-fstrict-aliasing' if alias=='strict' else '-fno-strict-aliasing',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True)
 assert p.returncode==0,p.stderr
 return subprocess.run([str(exe)],capture_output=True,text=True).returncode
for label,code in (('direct',body),('snapshot',snapshot)):
 for opt in ('-O0','-O2','-O3'):
  for alias in ('strict','no-strict'):
   result=run(label,code,opt,alias)
   assert result==(13 if label=='direct' else 0),(label,opt,alias,result)
controls={'wrong-gate':('== 10)', '== 9)'), 'wrong-height-offset':('*(f32 *)state + 5.0f','*(f32 *)state + 6.0f'),
          'wrong-range':('func_150ADA68() * 20.0f + 20.0f','func_150ADA68() * 16.0f + 20.0f')}
for label,(before,after) in controls.items():
 assert snapshot.count(before)==1
 for alias in ('strict','no-strict'):assert run(label,snapshot.replace(before,after),'-O2',alias)!=0,(label,alias)
report={'cases_per_configuration':24,'optimizations':3,'alias_modes':2,'direct_rejected_as_stale_tag':True,
        'snapshot_passed':True,'effective_controls':list(controls),'ubsan':True,'uncredited':True}
(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
