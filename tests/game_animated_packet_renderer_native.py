import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_animated_packet_renderer_match as p
out=p.out;root=p.root
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 source=(out/'candidate_source.c').read_text();types=source[source.index('typedef struct { u32 *frames; } AnimatedTexture15167;'):source.index('/* Emit the current animated texture')];start=source.index('Gfx *func_15167C58(Gfx *output');selected=source[start:source.index('\n}',start)+2]
 controls={
  'packed':('(s32)((u32)(s32)state->phase << 8)','(s32)((u32)(s32)state->phase << 7)'),
  'frame':('state->phase >> 8','state->phase >> 7'),
  'width':('<< 8), 2,','<< 8), 3,'),
  'kind':('state->phase >> 8], 5','state->phase >> 8], 6'),
  'flags':('mode = 3','mode = 4'),
  'x':('packet.x = state->x','packet.x = state->y'),
  'height':('packet.height = state->height','packet.height = state->width'),
  'alpha':('packet.alpha = state->alpha','packet.alpha = 0'),
  'zero':('packet.zero = 0','packet.zero = 1'),
  'modeflag':('| 4, (u8 *)&sync.value','| 8, (u8 *)&sync.value'),
 }
 code='''#include <ultra64.h>\n_Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");\n'''+types+r'''
 u32 D_800A4AC8[24];static AnimatedState15167 state;static AnimatedTexture15167 texture;static u32 frames[16];static Gfx commands[16];static u8 *packetptr,*syncptr;static u32 calls,bad,mutate;static s16 initialPhase;static s8 initialMode;
 Gfx *func_15142E24(Gfx *o,void *t,s32 packed,s32 w,s32 h,s32 v,s32 frame,u8 kind,u8 *packet,u8 *sync,s32 flags){
  calls++;if(calls!=1||o!=commands||t!=&texture||(u32)packed!=((u32)(s32)initialPhase<<8)||w!=2||h!=256||v!=256||(u32)frame!=frames[4+(initialPhase>>8)]||kind!=5||flags!=3||*sync!=1)bad=1;
  packetptr=packet;syncptr=sync;if(mutate){state.x=-200;state.y=201;state.z=-202;state.width=203;state.height=204;state.mode^=0xff;state.alpha^=0x55;packet[11]=0x5a;*sync^=0x5a;D_800A4AC8[6]=0x12345678;D_800A4AC8[7]=0x87654321;}return commands+4;
 }
 Gfx *func_15142FBC(Gfx *o,u32 a,u32 b,u8 *sync){
  calls++;if(calls!=2||o!=commands+4||a!=0x2c00||b!=(D_800A4AC8[6]|D_800A4AC8[7]|4)||sync!=syncptr||*sync!=(u8)(mutate?(1^0x5a):1))bad=1;
  if(mutate){packetptr[2]^=0x33;*sync^=0xa5;}return commands+8;
 }
 Gfx *func_15095760(Gfx *o,s16 *data){
  AnimatedPacket15167 *p=(AnimatedPacket15167*)data;calls++;if(calls!=3||o!=commands+8||(u8*)data!=packetptr||p->x!=state.x||p->z!=state.z||p->width!=state.width||p->height!=state.height||p->alpha!=state.alpha||p->zero||state.mode!=(s8)(initialMode^(mutate?0xff:0)))bad=1;
  if(!mutate&&p->y!=state.y)bad=1;if(mutate&&packetptr[11]!=0x5a)bad=1;return commands+12;
 }
 '''
 code+='\n'+selected.replace('func_15167C58','test_selected',1)+'\n'
 for name,(a,b)in controls.items():
  assert selected.count(a)==1,(name,selected.count(a))
  code+='\n'+selected.replace(a,b,1).replace('func_15167C58','control_'+name,1)+'\n'
 code+=r'''
 typedef Gfx *(*T)(Gfx*,AnimatedState15167*,s32);
 static int check(T test){s32 phases[5]={-257,-1,0,256,767};u32 i,j,k,m;Gfx *result;
  for(i=0;i<16;i++)frames[i]=0x12340000+i;
  for(i=0;i<5;i++)for(j=0;j<4;j++)for(m=0;m<2;m++){
   initialPhase=(s16)phases[i];initialMode=(s8)(j==0?0:j==1?127:j==2?128:255);mutate=m;calls=bad=0;packetptr=syncptr=0;
   texture.frames=frames+4;state.texture=&texture;state.phase=initialPhase;state.x=1;state.y=2;state.z=3;state.width=4;state.height=5;state.mode=initialMode;state.alpha=77;
   for(k=0;k<24;k++)D_800A4AC8[k]=(1u<<(k%28));
   result=test(commands,&state,(s32)0xabcdef01u);if(bad||calls!=3||result!=commands+12)return 1;
  }return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+=f'if(!check(control_{name}))return {20+i};\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_screen'+opt);r=subprocess.run(native_command(opt)+['-Wno-type-limits','-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.stdout[-3000:],r.stderr[-3000:])
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases=40,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=profiles,helpers='modeled',source_installed=False);(out/'native_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
