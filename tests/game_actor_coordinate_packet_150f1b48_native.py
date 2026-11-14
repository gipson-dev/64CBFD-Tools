"""Native32 packet boundary and alias tests with semantic controls."""
from pathlib import Path
import json,os,subprocess
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-coordinate-packet-150f1b48-durable';source=(out/'formatted.c').read_text()
start=source.index('u8 *func_150F1B48(');end=source.index('\n}',start)+2;fn=source[start:end]
header='''#include <ultra64.h>
extern u16 D_800CC354[]; extern s16 D_800CC298[]; extern s32 D_800BE9E4; extern f32 D_800A18F4,D_800A18F8;
'''
controls={
 'wrong-actor':fn.replace('== 0x21','== 0x20'),
 'wrong-rate':fn.replace('* 0x222u','* 0x221u'),
 'wrong-lower':fn.replace('-0x1999','-0x1998'),
 'wrong-upper':fn.replace('0x1555','0x1554'),
 'early-narrow':fn.replace('(s32)((u32)(s32)D_800CC298[9] - (u32)delta)','(s16)((u32)(s32)D_800CC298[9] - (u32)delta)'),
 'early-snapshot':fn.replace('    packet[0] = 0xb2;\n    next = D_800CC298[9];','    next = D_800CC298[9];\n    packet[0] = 0xb2;'),
 'wrong-return':fn.replace('return output + 24;','return output + 22;')}
assert all(code!=fn for code in controls.values())
harness='''
u16 D_800CC354[1626];s16 D_800CC298[32];s32 D_800BE9E4;f32 D_800A18F4=-6553.60009765625f,D_800A18F8=5461.33349609375f;
static s16 other[32],expected_state[32],expected_other[32];
static s32 signedwrap(u32 x){return (s32)x;}
static void reference(s16 *p,int slot){
 s32 step=(s32)((u32)D_800BE9E4*546u);s32 next;
 if(*(u16 *)((u8 *)D_800CC354+(u32)slot*812u)==0x21){
  next=signedwrap((u32)(s32)expected_state[9]-(u32)step);
  expected_state[9]=(D_800A18F4<(f32)next)?(s16)next:-0x1999;
 }else{
  next=signedwrap((u32)(s32)expected_state[9]+(u32)step);
  expected_state[9]=((f32)next<D_800A18F8)?(s16)next:0x1555;
 }
 p[0]=178;next=expected_state[9];p[2]=184;p[1]=(s16)next;
 for(int i=2;i<6;i++){next=expected_state[9];p[i*2]=(s16)(178+i*6);p[i*2-1]=(s16)next;}
 p[11]=expected_state[9];
}
static int run(void){
 static const s32 values[]={-32768,-6554,-1,0,5461,32767};
 static const u32 steps[]={0,1,2,0x7fffffffu,0x80000000u,0xffffffffu};
 static const int offsets[]={-1,0,4,8,12,16,18,20};
 for(int slot=0;slot<4;slot++)for(int v=0;v<6;v++)for(int t=0;t<6;t++)for(int active=0;active<2;active++)for(int o=0;o<8;o++){
  for(int i=0;i<32;i++){D_800CC298[i]=expected_state[i]=(s16)(i*221+17);other[i]=expected_other[i]=(s16)(i*109+3);}
  D_800CC298[9]=expected_state[9]=(s16)values[v];D_800BE9E4=(s32)steps[t];
  *(u16 *)((u8 *)D_800CC354+slot*812)=active?0x21:0x20;
  s16 *p=offsets[o]<0?other:(s16 *)((u8 *)D_800CC298+offsets[o]);
  s16 *e=offsets[o]<0?expected_other:(s16 *)((u8 *)expected_state+offsets[o]);
  reference(e,slot);u8 *ret=func_150F1B48((u8 *)p,slot);if(ret!=(u8 *)p+24)return 1;
  for(int i=0;i<32;i++)if(D_800CC298[i]!=expected_state[i]||other[i]!=expected_other[i])return 2;
 }
 return 0;
}
'''
def run(name,code,opt):
    src=out/(name+'.c');exe=out/(name+'-'+opt[1:]);src.write_text(header+code+harness+START)
    p=subprocess.run(native_command(opt)+[str(src),'-o',str(exe)],capture_output=True,text=True);assert p.returncode==0,p.stderr
    return subprocess.run([str(exe)],capture_output=True,text=True)
for opt in ('-O0','-O2','-O3'):
    p=run('native-candidate',fn,opt);assert p.returncode==0,(opt,p.returncode,p.stderr)
    for name,code in controls.items():
        p=run('control-'+name,code,opt);assert p.returncode!=0,(opt,name)
report={'cases_per_optimization':2304,'optimizations':['O0','O2','O3'],'effective_controls':list(controls),'ubsan':True,'uncredited':True}
(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
