"""Private native32 disjoint-object screen for motion crossing."""
from pathlib import Path
import json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-motion-crossing-150e6230-durable';source=(out/'formatted.c').read_text();start=source.index('extern f32 D_800BE9A4;');end=source.index('\ns32 func_150E63A0',start);body=source[start:end]
harness='''
static union { f32 f[0x180/4]; u32 w[0x180/4]; u8 b[0x180]; } actor;
f32 D_800BE9A4; static s32 mode,cbret,calls,error; static f32 dotvalue;
static s32 do_callback(u8 *a);
s32 (*D_80088A10[])(u8 *) = {do_callback};
f32 func_15144A74(f32 *d,f32 *s) {
 calls++; if(d[0]!=3.f||d[1]!=10.f||d[2]!=-6.f||s!=(f32 *)(actor.b+0x114))error=1;
 if(mode&1){actor.f[0x138/4]=1.f;actor.f[0x40/4]=1.5f;D_800BE9A4=.75f;} return dotvalue;
}
static s32 do_callback(u8 *a) {
 calls++;if(a!=actor.b)error=2;
 if(mode&2){actor.f[0x50/4]=2.f;actor.f[0x38/4]=9.f;D_800BE9A4=1.25f;} return cbret;
}
static int run(void) {
 int cases=0;const f32 dots[]={-1.f,0.f,1.f}, signs[]={-1.f,1.f};
 for(int enabled=0;enabled<2;enabled++)for(int di=0;di<3;di++)for(int si=0;si<2;si++)for(int selector=-1;selector<1;selector++)for(mode=0;mode<4;mode++)for(int cr=0;cr<2;cr++){
  for(int i=0;i<0x180/4;i++)actor.w[i]=0;
  actor.b[0x110]=enabled;actor.b[0x13c]=(u8)selector;
  actor.f[0x34/4]=2.f;actor.f[0x38/4]=-3.f;actor.f[0x3c/4]=4.f;
  actor.f[0x40/4]=.5f;actor.f[0x44/4]=-1.f;actor.f[0x48/4]=2.f;actor.f[0x50/4]=3.f;
  actor.f[0x114/4]=5.f;actor.f[0x118/4]=7.f;actor.f[0x11c/4]=-2.f;actor.f[0x138/4]=signs[si];
  D_800BE9A4=.5f;dotvalue=dots[di];cbret=cr?0x1fe:0x100;calls=error=0;
  int called=enabled&&((dotvalue<0.f?-1.f:1.f)!=((mode&1)?1.f:signs[si]))&&selector==0;
  int result=func_150E6230(actor.b);int expected=!enabled?1:((dotvalue<0.f?-1.f:1.f)==((mode&1)?1.f:signs[si]))?1:called?(cr?-2:0):0;
  f32 tick=called&&(mode&2)?1.25f:enabled&&(mode&1)?.75f:.5f;
  f32 speed=called&&(mode&2)?2.f:3.f;f32 vx=enabled&&(mode&1)?1.5f:.5f;f32 y=called&&(mode&2)?9.f:-3.f;
  if(error||calls!=enabled+called||result!=expected)return 10+error;
  if(actor.f[0x34/4]!=2.f+(vx*speed)*tick||actor.f[0x38/4]!=y+(-1.f*speed)*tick||actor.f[0x3c/4]!=4.f+(2.f*speed)*tick)return 20;
  cases++;
 }
 return cases==192?0:30;
}
'''
prefix='#include <ultra64.h>\n'
controls={'sign-equality':[('< 0.0f ? -1.0f : 1.0f','<= 0.0f ? -1.0f : 1.0f')],
          'no-sign-extension':[('s8 result = 1;','s32 result = 1;'),('result = (s8)D_80088A10[selector](actor)','result = D_80088A10[selector](actor)')],
          'wrong-motion':[('vx = *(f32 *)(actor + 0x40) * speed','vx = *(f32 *)(actor + 0x40) + speed')]}
def run(label,code,opt,alias):
 src=out/('native-'+label+'.c');exe=out/('native-'+label+opt+'-'+alias);src.write_text(prefix+code+harness+START)
 p=subprocess.run(native_command(opt)+['-mstackrealign','-fstrict-aliasing' if alias=='strict' else '-fno-strict-aliasing',str(src),'-o',str(exe)],capture_output=True,text=True);assert p.returncode==0,p.stderr
 return subprocess.run([str(exe)],capture_output=True,text=True).returncode
for opt in ('-O0','-O2','-O3'):
 for alias in ('strict','no-strict'):assert run('candidate',body,opt,alias)==0,(opt,alias)
for name,changes in controls.items():
 altered=body
 for old,new in changes:
  assert altered.count(old)==1;altered=altered.replace(old,new)
 for alias in ('strict','no-strict'):assert run(name,altered,'-O2',alias)!=0,(name,alias)
report={'cases_per_configuration':192,'optimizations':3,'alias_modes':2,'controls':list(controls),'ubsan':True,'uncredited':True}
(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
