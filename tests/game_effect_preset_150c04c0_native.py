"""SDK32 preset source, original fields, mixed-width boundary and controls."""
import json,subprocess
from tools.experiments import game_effect_preset_150c04c0_match as packet
from tools.tests.test_game_projected_packet_draw import native_command
r,o=packet.ROOT,packet.OUT
def controls(body):
 result={'flag-low-bit':body.replace('if (enabled)','if (enabled & 1)'),
 'variant-byte':body.replace('localResource = variant;','localResource = (u8)variant;'),
 'missing-state':body.replace('preset.state = state;','preset.state = 0;'),
 'wrong-chance':body.replace('preset.chance = D_800A0188;','preset.chance = D_800A018C;'),
 'wrong-aspect':body.replace('preset.aspect = 10.0f;','preset.aspect = 9.0f;'),
 'wrong-extra-size':body.replace('preset.extraSize = 4;','preset.extraSize = 3;')}
 assert all(v!=body for v in result.values());return result
def program():
 decl=(o/'selected-final/declarations.c').read_text();body=(o/'selected-final/body.c').read_text().replace('func_150C04C0(','subject(')
 src='#include <ultra64.h>\n'+decl+r'''
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(s32)==4,"SDK32 ABI");
_Static_assert(sizeof(EffectPresetEC420)==100&&sizeof(EffectAnglesEC420)==8&&sizeof(EffectSizeEC420)==4,"Packet sizes");
_Static_assert(__builtin_offsetof(EffectPresetEC420,state)==52&&__builtin_offsetof(EffectPresetEC420,resources)==72&&__builtin_offsetof(EffectPresetEC420,flags)==88&&__builtin_offsetof(EffectPresetEC420,extraData)==96,"Packet offsets");
EffectSizeEC420 D_800A0108;
f32 D_800A0170,D_800A0174,D_800A0178,D_800A017C,D_800A0180,D_800A0184,D_800A0188,D_800A018C,D_800A0190;
static u32 bits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static u32 calls,failure,variant,enabled,channel,context,state;
static EffectPositionEC420 position;
__attribute__((noinline,noclone)) void func_15150400(EffectPresetEC420 *p,EffectAnglesEC420 *a,u8 ch,s32 ctx){
 calls++;
 if(p->countBase!=9||p->countRange!=4||bits(p->position.x)!=bits(position.x)||bits(p->position.y)!=bits(position.y)||bits(p->position.z)!=bits(position.z))failure=1;
 if(bits(p->speedBase)!=0x40800000u||bits(p->speedRange)!=0x40e00000u||bits(p->verticalBase)!=0xbfa3d70bu||bits(p->verticalRange)!=0x3eac0832u)failure=1;
 if(p->lifetimeBase!=80||p->lifetimeRange!=60||bits(p->sizeBase)!=0x3f19999au||bits(p->sizeRange)!=0x3ee66667u||bits(p->jitter)!=0x41889db3u)failure=1;
 if((u32)p->state!=state||bits(p->chance)!=0x3f408313u||bits(p->offsetBase)!=0x3e50e561u||bits(p->offsetRange)!=0x3e27ef9eu||bits(p->aspect)!=0x41200000u)failure=1;
 if(!p->resources||!p->sizes||!p->extraData||p->resourceCount!=1||bits(p->radius)!=0x429c0000u||p->flags!=((enabled&255)!=0)||p->kind!=14||p->extraSize!=4)failure=1;
 if(p->resources&&(u32)*p->resources!=variant)failure=1;
 if(p->sizes&&bits(*p->sizes)!=0x3f800000u)failure=1;
 if(p->extraData&&bits(*(f32*)p->extraData)!=0x3f266667u)failure=1;
 if(a->first!=0||a->firstRange!=255||a->second!=-50||a->secondRange!=35||ch!=(channel&255)||(u32)ctx!=context)failure=1;
}
'''+body+r'''
static int run(void){u32 i,j,k,high[3]={0,0x80000000u,0xCAFE0000u};
 D_800A0108.value=real(0x3f800000u);D_800A0170=real(0x3f266667u);D_800A0174=real(0xbfa3d70bu);D_800A0178=real(0x3eac0832u);
 D_800A017C=real(0x3f19999au);D_800A0180=real(0x3ee66667u);D_800A0184=real(0x41889db3u);D_800A0188=real(0x3f408313u);D_800A018C=real(0x3e50e561u);D_800A0190=real(0x3e27ef9eu);
 for(k=0;k<3;k++)for(i=0;i<256;i++)for(j=0;j<256;j++){
  enabled=high[k]|i;channel=high[k]|j;variant=high[k]|(i<<8)|j;context=~variant;state=i?0x12340000u|i:0;
  position.x=real(0x3f800000u|i);position.y=real(0x80000000u|j);position.z=real(0x7fc00000u|(i<<8)|j);
  calls=failure=0;subject(&position,(struct ExtendedState15F680*)state,(s32)variant,(u8)enabled,(u8)channel,(s32)context);
  if(calls!=1||failure)return 1;
 }
 return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 return src,body
def main():
 src,body=program();profiles={}
 def run(text,label,opt):
  p=o/(label+'.c');p.write_text(text);exe=o/(label+opt)
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr
  return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in ('-O0','-O2','-O3'):
  q=run(src,'native',opt);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b''),(opt,q.returncode,q.stderr)
  profiles[opt]=dict(cases=196608,SDK32=True,UBSan=True,strict_aliasing=True,all_named_fields_and_typed_locals_compared=True)
 effective=[]
 for label,changed in controls((o/'selected-final/body.c').read_text()).items():
  altered=changed.replace('func_150C04C0(','subject(');q=run(src.replace(body,altered),'control-'+label,'-O2');assert q.returncode==1,(label,q.returncode,q.stderr);effective.append(label)
 report=dict(profiles=profiles,effective_output_comparison_controls=effective,source_installed=packet.installed(),matching_credit=0,limits='Complete SDK32 source and typed packet consumer boundary. Native uninitialized padding and consumer internals are not read or qualified.')
 (o/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
