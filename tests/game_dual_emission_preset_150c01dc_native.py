"""SDK32 raw C with independently checked packets, lifetime and callback ABI."""
import json,subprocess
from tools.experiments import game_dual_emission_preset_150c01dc_match as packet
from tools.tests.test_game_projected_packet_draw import native_command
r,o=packet.ROOT,packet.OUT
def controls(body):
 snapshot='''    position.x = *(f32 *)(owner + 0x38);
    position.y = height + 20.0f;
    position.z = *(f32 *)(owner + 0x40);
'''
 call='        owner[0xC], owner[1]);\n';assert snapshot in body and call in body
 result={'late-position-snapshot':body.replace(call,call+snapshot),
 'wrong-height':body.replace('height + 20.0f','height + 19.0f'),
 'wrong-kind':body.replace('emission.kind = 108;','emission.kind = 107;'),
 'wrong-second-color':body.replace('emission.field23 = 100;','emission.field23 = 155;'),
 'wrong-resource-count':body.replace('&scale.value, 1, 0.0f','&scale.value, 2, 0.0f'),
 'wrong-shared-scale':body.replace('sharedScale = D_800A0160;','sharedScale = D_800A0168;'),
 'wrong-flags':body.replace('0x840E07','0x840E06'),
 'wrong-callback-result':body.replace('return 0;','return 1;')}
 assert all(v!=body for v in result.values());return result
def program():
 body=(o/'selected-final/body.c').read_text().replace('func_150C01DC(','subject(');decl=(o/'selected-final/declarations.c').read_text();old=packet.MANIFEST['old_source'];types=old[old.index('typedef struct { f32 x, y, z; } EmissionPositionEC420;'):old.index('extern f32 D_800A0134')]
 values=packet.MANIFEST['constants'];names=list(values)
 src='#include <ultra64.h>\n'+types+decl+'\n'+r'''
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(s32)==4,"SDK32 ABI");
_Static_assert(sizeof(EmissionPresetEC420)==108&&sizeof(BurstConfigurationEC420)==60&&sizeof(EmissionPositionEC420)==12,"Packet sizes");
_Static_assert(__builtin_offsetof(EmissionPresetEC420,position)==56&&__builtin_offsetof(EmissionPresetEC420,flags)==92&&__builtin_offsetof(EmissionPresetEC420,payloadValue)==104,"Emission offsets");
_Static_assert(__builtin_offsetof(BurstConfigurationEC420,position)==8&&__builtin_offsetof(BurstConfigurationEC420,lifetime)==44&&__builtin_offsetof(BurstConfigurationEC420,spread)==56,"Burst offsets");
typedef struct {u8 header[0x38];f32 x,y,z;u8 tail[0x13c];} NativeOwner;
static struct {u32 pre[4];NativeOwner owner;u32 post[4];} region;
ResourceOneEC420 D_800A0100;ScaleOneEC420 D_800A0104;
f32 D_800A014C,D_800A0150,D_800A0154,D_800A0158,D_800A015C,D_800A0160,D_800A0164,D_800A0168,D_800A016C;
static u32 bits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
'''
 src+='static const u32 constants[11]={'+','.join(hex(values[n])+'u'for n in names)+'};\n'
 src+='static f32 *globals[10]={&D_800A0104.value,'+','.join('&'+n for n in names[2:])+'};\n'
 src+=r'''
static u32 calls,failure,seed,mutation,wantX,wantY,wantZ,wantGlobal[11],channel,context;
__attribute__((noinline,noclone)) void func_15152190(BurstConfigurationEC420 *p,s32 *resources,f32 *scales,s32 count,f32 radius,u8 mode,u8 ch,s32 ctx){u32 i;
 if(calls!=0||resources[0]!=(s32)constants[0]||bits(scales[0])!=constants[1]||count!=1||bits(radius)!=0||mode!=1||ch!=channel||ctx!=(s32)context)failure=1;calls++;
 if(p->count!=5||p->countRange!=4||bits(p->position.x)!=wantX||bits(p->position.y)!=wantY||bits(p->position.z)!=wantZ||p->angle||p->angleRange!=255||p->pitch!=-64||p->pitchRange!=34)failure=1;
 if(bits(p->speed)!=0x41400000||bits(p->speedRange)!=0x41000000||bits(p->vertical)!=constants[2]||bits(p->verticalRange)!=constants[3]||p->lifetime!=30||p->lifetimeRange!=15||bits(p->scale)!=constants[4]||bits(p->scaleRange)!=constants[5]||bits(p->spread)!=constants[6])failure=1;
 if(mutation){region.owner.x=real(0xc1200000);region.owner.z=real(0x80000000);region.owner.header[1]^=255;region.owner.header[12]^=255;
  D_800A0100.value=(s32)(constants[0]^((seed+1)<<4));for(i=0;i<10;i++)*globals[i]=real(constants[i+1]^((seed+1)<<4));
 }
}
__attribute__((noinline,noclone)) void func_15153634(void *descriptor,u8 mode,u8 ch,s32 ctx){EmissionPresetEC420 *p=descriptor;
 if(calls!=1||mode!=255||ch!=(channel^(mutation?255:0))||ctx!=(s32)(context^(mutation?255:0)))failure=1;calls++;
 if(p->count!=5||p->countRange!=8||p->kind!=108||p->field06!=0x5103||p->header!=0x200005||p->field0C||p->field10!=30||p->field12!=15||p->field14||p->field18)failure=1;
 if(p->field1C!=78||p->field1D!=84||p->field1E!=123||p->field1F!=255||p->field20!=164||p->field21!=161||p->field22!=200||p->field23!=100||p->field24!=155||p->field25!=255)failure=1;
 if(p->field26!=14||p->field28!=18||p->field2A!=14||bits(p->field2C)!=wantGlobal[8]||bits(p->field30)!=0x435a0000||bits(p->field34)!=wantGlobal[9])failure=1;
 if(bits(p->position.x)!=wantX||bits(p->position.y)!=wantY||bits(p->position.z)!=wantZ||p->field44||p->field46!=-40||p->field48!=255||p->field4A!=40)failure=1;
 if(bits(p->field4C)!=0x41980000||bits(p->field50)!=0x41000000||bits(p->field54)!=wantGlobal[7]||bits(p->field58)!=wantGlobal[7]||p->flags!=0x840e07)failure=1;
 if(p->field60!=16||p->field61!=-1||p->field62!=8||p->field63!=6||p->field64!=1||bits(p->payloadValue)!=wantGlobal[10])failure=1;
}
'''+body+r'''
static int run(void){u32 i,j,k,n;volatile f32 rounded;
 const u32 ys[16]={0,0x80000000,0x3f800000,0xbf800000,0xc28c0000,0xc2d20000,0x4c000000,0xcc000000,1,0x80000001,0x00800000,0x7f7fffff,0x3eaaaaab,0x42f60001,0x4bffffff,0xcbffffff};
 for(k=0;k<2;k++)for(j=0;j<16;j++)for(i=0;i<256;i++){
  seed=i;mutation=k;calls=failure=0;channel=(i*31+128)&255;context=(i*17+129)&255;
  wantX=0x3f800001u^(i<<8);wantZ=0x7fc01234u^(i<<8);region.owner.x=real(wantX);region.owner.z=real(wantZ);region.owner.y=real(0x42c60000);region.owner.header[1]=context;region.owner.header[12]=channel;
  rounded=real(ys[j])+20.0f;wantY=bits(rounded);
  D_800A0100.value=constants[0];for(n=0;n<10;n++)*globals[n]=real(constants[n+1]);
  for(n=0;n<11;n++)wantGlobal[n]=constants[n]^(k?((i+1)<<4):0);
  for(n=0;n<4;n++){region.pre[n]=0x13570000u+n;region.post[n]=0x24680000u+n;}
  if(subject((u8*)&region.owner,real(0x7fc01234),real(0x80000000),real(0x7f800000),real(ys[j]),region.owner.tail)!=0)return 1;
  if(calls!=2||failure||bits(region.owner.x)!=(k?0xc1200000u:wantX)||bits(region.owner.z)!=(k?0x80000000u:wantZ))return 1;
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
 for opt in('-O0','-O2','-O3'):
  q=run(src,'native',opt);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b''),(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=8192,SDK32=True,UBSan=True,strict_aliasing=True,float32_height_rounding=True,snapshots_and_reloaded_byte_parameters=True)
 effective=[]
 for label,changed in controls((o/'selected-final/body.c').read_text()).items():
  q=run(src.replace(body,changed.replace('func_150C01DC(','subject(')),'control-'+label,'-O2');assert q.returncode==1,(label,q.returncode,q.stderr);effective.append(label)
 report=dict(profiles=profiles,effective_output_comparison_controls=effective,source_installed=packet.installed(),matching_credit=0,limits='Complete raw SDK32 C, all initialized packet fields and both typed boundaries. Packet padding is not read natively; provider internals and gameplay are not qualified.');(o/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
