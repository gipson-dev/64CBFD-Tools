"""Exercise private C on native32 over its defined disjoint-memory domain."""
from pathlib import Path
import json, subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-actor-effect-dispatch-150b3ab0-durable'
source=(out/'candidate-12.c').read_text();start=source.index('typedef struct { f32 x');end=source.index('\ns32 func_150B3C0C',start);body=source[start:end]
HARNESS='''
s32 D_800BE9E8;u8 *D_800DBFF0;f32 D_8009FBC0[3];
static union { u32 a; u8 b[0x200]; } actor;
static union { u32 a; u8 b[0x700]; } frame,second;
static u8 base[0x2000];
static int errors,step,randomIndex,mutation;static u8 expectedSlot;static u32 values[3];
void func_1512D748(void *p,s32 a,s32 b){
 if(step++!=0||p!=base+0x1340||a!=6||b!=1)errors++;
 if(mutation){*(u8 **)(actor.b+0x1d4)=second.b;*(u16 *)(actor.b+0x7a)=0x0180;}
}
void func_15143134(f32 *p,f32 *o,u8 *m){
 EffectPosition150B3AB0 *q=(EffectPosition150B3AB0 *)o;
 if(step++!=1||p!=D_8009FBC0||m!=(mutation?second.b:frame.b)+0x640||q->angle!=(mutation?0x41:0x13f))errors++;
 q->x=1.25f;q->y=-2.5f;q->z=3.75f;
}
s32 func_150ADA20(void){step++;return (s32)values[randomIndex++];}
void func_1514C858(f32 x,f32 y,f32 z,f32 w,s32 angle,s32 a,s32 b,s32 c,s32 d,s32 e,f32 f,s32 g,s32 slot){
 if(step++!=3||x!=1.25f||y!=-2.5f||z!=3.75f||w!=10.0f||angle!=(mutation?0x41:0x13f)||a||b!=255||c!=(s32)(values[0]%31+40)||d!=8||e||f!=0.0f||g||slot!=expectedSlot)errors++;
}
u8 *func_151D8868(u8 *ptr,s32 a,u8 b,s32 c){
 EffectPacket150B3AB0 *p=(EffectPacket150B3AB0 *)ptr;
 if(step++!=6||a||b!=expectedSlot||c||p->kind!=1||p->size!=(s32)((values[1]&15)+12)||p->mode!=((values[2]&3)+5)||p->enabled!=1||p->value!=-1)errors++;
 return 0;
}
void func_151D3FF4(f32 *ptr,u8 a,s32 b){
 EffectPosition150B3AB0 *p=(EffectPosition150B3AB0 *)ptr;
 if(step++!=7||a!=expectedSlot||b||p->x!=1.25f||p->y!=-2.5f||p->z!=3.75f||p->angle!=(mutation?0x41:0x13f))errors++;
}
static int run(void){
 int count=0;
 for(int active=0;active<3;active++)for(int slot=0;slot<2;slot++)for(mutation=0;mutation<2;mutation++)for(int variant=0;variant<3;variant++){
  *(u8 **)(actor.b+0x1d4)=active==2?frame.b:0;*(u16 *)(actor.b+0x7a)=0xff80;
  D_800BE9E8=2;D_800DBFF0=base;expectedSlot=slot?255:0;
  for(int i=0;i<3;i++)values[i]=variant==0?0:variant==1?0xffffffffu:(i==0?31:i==1?15:3);
  errors=step=randomIndex=0;func_150B3AB0(active?actor.b:0,expectedSlot);
  if(errors||step!=(active==2?8:0)||randomIndex!=(active==2?3:0))return 1;
  count++;
 }
 return count==36?0:2;
}
'''
controls={'wrong-angle':('>> 8) + 0x40','>> 8) + 0x41'),'wrong-lifetime':('(func_150ADA20() & 15) + 12','(func_150ADA20() & 15) + 13'),'wrong-packet-mode':('(func_150ADA20() & 3) + 5','(func_150ADA20() & 3) + 4'),'wrong-priority':('position.angle, 0, 255,','position.angle, 0, 254,')}
def run(label,code,opt,alias):
 src=out/(label+'.c');exe=out/(label+opt+'-'+alias);src.write_text('#include <ultra64.h>\n'+code+'\n'+HARNESS+START)
 p=subprocess.run(native_command(opt)+['-mstackrealign','-fstrict-aliasing' if alias=='strict' else '-fno-strict-aliasing',str(src),'-o',str(exe)],capture_output=True,text=True);assert p.returncode==0,p.stderr
 return subprocess.run([str(exe)],capture_output=True,text=True).returncode
for opt in ('-O0','-O2','-O3'):
 for alias in ('strict','no-strict'):
  assert run('native-candidate',body,opt,alias)==0,(opt,alias)
  for label,(old,new) in controls.items():
   assert body.count(old)==1;assert run('control-'+label,body.replace(old,new),opt,alias)!=0,(opt,alias,label)
report={'cases_per_configuration':36,'optimizations':3,'alias_modes':2,'controls':list(controls),'ubsan':True,'uncredited':True}
(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
