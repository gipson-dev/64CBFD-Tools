"""Actual SDK32 C, pre-call snapshots, separate float rounding and typed fields."""
import json,subprocess
from tools.experiments import game_actor_emission_preset_150bffe0_match as packet
from tools.tests.test_game_projected_packet_draw import native_command
r,o=packet.ROOT,packet.OUT
def controls(body):
 snapshot='''    position.x = *(f32 *)(actor + 0x14);
    position.y = *(f32 *)(actor + 0x180) + 70.0f;
    position.z = *(f32 *)(actor + 0x1C);
'''
 call='    func_15136C3C(actor,0,0,1,0,0,255,1);\n';assert snapshot in body and call in body
 result={'late-snapshot':body.replace(snapshot,'').replace(call,call+snapshot),
 'combined-height-rounding':body.replace('+ 70.0f','+ 105.0f').replace('+ 35.0f','+ 0.0f'),
 'wrong-kind':body.replace('packet.kind = 108;','packet.kind = 107;'),
 'wrong-color':body.replace('packet.field22 = 200;','packet.field22 = 201;'),
 'wrong-first-boundary':body.replace('actor,0,0,1,0,0,255,1','actor,0,0,1,0,0,254,1'),
 'wrong-payload':body.replace('packet.payloadValue = D_800A0148;','packet.payloadValue = D_800A0144;'),
 'wrong-flags':body.replace('0x40040E07','0x40040E06')}
 assert all(v!=body for v in result.values());return result
def program():
 body=(o/'selected-final/body.c').read_text().replace('func_150BFFE0(','subject(');decl=(o/'selected-final/declarations.c').read_text()
 src='#include <ultra64.h>\n'+decl+r'''
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(s32)==4,"SDK32 ABI");
_Static_assert(sizeof(EmissionPresetEC420)==108&&sizeof(EmissionPositionEC420)==12,"Descriptor sizes");
_Static_assert(__builtin_offsetof(EmissionPresetEC420,position)==56&&__builtin_offsetof(EmissionPresetEC420,flags)==92&&__builtin_offsetof(EmissionPresetEC420,payloadValue)==104,"Descriptor offsets");
typedef struct {u8 a[0x14];f32 x;u8 b[4];f32 z;u8 c[0x160];f32 y;} NativeActor;
_Static_assert(__builtin_offsetof(NativeActor,y)==0x180,"Actor layout");
static struct {u32 pre[4];NativeActor actor;u32 post[4];} region;
f32 D_800A0134,D_800A0138,D_800A013C,D_800A0140,D_800A0144,D_800A0148;
static u32 bits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static const u32 constants[6]={0x3f828f5c,0x43e18000,0x43fa8000,0x3eb53f7d,0x3f20418a,0x3f60a72f};
static f32 *globals[6]={&D_800A0134,&D_800A0138,&D_800A013C,&D_800A0140,&D_800A0144,&D_800A0148};
static u32 calls,failure,seed,mutation,wantX,wantY,wantZ,wantGlobal[6];
__attribute__((noinline,noclone)) void func_15136C3C(void *a0,u8 a1,u8 a2,u8 a3,u8 a4,u8 a5,u8 a6,s32 a7){u32 i;
 if(calls!=0||a0!=&region.actor||a1||a2||a3!=1||a4||a5||a6!=255||a7!=1)failure=1;
 calls++;
 if(mutation){region.actor.x=real(0xc1200000);region.actor.y=real(0x4c800001);region.actor.z=real(0x80000000);
  for(i=0;i<6;i++)*globals[i]=real(constants[i]^((seed+1)<<4));
 }
}
__attribute__((noinline,noclone)) void func_15153634(void *descriptor,u8 a1,u8 a2,s32 a3){EmissionPresetEC420 *p=descriptor;
 if(calls!=1||a1!=255||a2!=255||a3!=1)failure=1;calls++;
 if(p->count!=17||p->countRange!=7||p->kind!=108||p->field06!=0x5103||p->header!=0x200005||p->field0C||p->field10!=40||p->field12!=20||p->field14||p->field18)failure=1;
 if(p->field1C!=78||p->field1D!=84||p->field1E!=123||p->field1F!=255||p->field20!=164||p->field21!=161||p->field22!=200||p->field23!=155||p->field24!=100||p->field25!=255)failure=1;
 if(p->field26!=30||p->field28!=8||p->field2A!=30||bits(p->field2C)!=wantGlobal[0]||bits(p->field30)!=wantGlobal[1]||bits(p->field34)!=wantGlobal[2])failure=1;
 if(bits(p->position.x)!=wantX||bits(p->position.y)!=wantY||bits(p->position.z)!=wantZ||p->field44!=0||p->field46!=-20||p->field48!=255||p->field4A!=30)failure=1;
 if(bits(p->field4C)!=0x41700000||bits(p->field50)!=0x421c0000||bits(p->field54)!=wantGlobal[3]||bits(p->field58)!=wantGlobal[4]||p->flags!=0x40040e07)failure=1;
 if(p->field60!=16||p->field61!=-1||p->field62!=8||p->field63!=6||p->field64!=1||bits(p->payloadValue)!=wantGlobal[5])failure=1;
}
'''+body+r'''
static int run(void){u32 i,j,k,n;volatile f32 intermediate;
 const u32 ys[16]={0,0x80000000,0x3f800000,0xbf800000,0xc28c0000,0xc2d20000,0x4c000000,0xcc000000,1,0x80000001,0x00800000,0x7f7fffff,0x3eaaaaab,0x42f60001,0x4bffffff,0xcbffffff};
 for(k=0;k<2;k++)for(j=0;j<16;j++)for(i=0;i<256;i++){
  seed=i;mutation=k;calls=failure=0;
  wantX=0x3f800001u^(i<<8);wantZ=0x7fc01234u^(i<<8);region.actor.x=real(wantX);region.actor.z=real(wantZ);region.actor.y=real(ys[j]);
  intermediate=real(ys[j])+70.0f;wantY=bits(intermediate+35.0f);
  for(n=0;n<6;n++){*globals[n]=real(constants[n]);wantGlobal[n]=constants[n]^(k?((i+1)<<4):0);}
  for(n=0;n<4;n++){region.pre[n]=0x13570000u+n;region.post[n]=0x24680000u+n;}
  subject((u8*)&region.actor);
  if(calls!=2||failure)return 1;
  if(bits(region.actor.x)!=(k?0xc1200000u:wantX)||bits(region.actor.y)!=(k?0x4c800001u:ys[j])||bits(region.actor.z)!=(k?0x80000000u:wantZ))return 1;
  for(n=0;n<4;n++)if(region.pre[n]!=0x13570000u+n||region.post[n]!=0x24680000u+n)return 1;
 }
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 return src,body
def main():
 src,body=program();profiles={}
 def run(text,label,opt):
  p=o/(label+'.c');p.write_text(text);exe=o/(label+opt);q=subprocess.run(native_command(opt)+['-msse2','-mfpmath=sse','-fexcess-precision=standard','-fstrict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr
  return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in ('-O0','-O2','-O3'):
  q=run(src,'native',opt);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b''),(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=8192,SDK32=True,UBSan=True,strict_aliasing=True,separate_float32_rounding=True,pre_call_snapshots_and_all_fields=True)
 effective=[]
 for label,changed in controls((o/'selected-final/body.c').read_text()).items():
  q=run(src.replace(body,changed.replace('func_150BFFE0(','subject(')),'control-'+label,'-O2');assert q.returncode==1,(label,q.returncode,q.stderr);effective.append(label)
 report=dict(profiles=profiles,effective_output_comparison_controls=effective,source_installed=packet.installed(),matching_credit=0,limits='Complete raw SDK32 C and both typed boundaries; packet padding is not read natively, and provider internals/gameplay are not qualified.');(o/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
