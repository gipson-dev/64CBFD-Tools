"""Execute the recovered C under the 32-bit SDK ABI at three optimization levels."""
import json,subprocess
from tools.experiments import game_menu_radial_150b879c_match as s
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run(state=None):
 fn=s.PIN['body'];controls={
 'kind':('packet.field08 = 0xE03','packet.field08 = 0xE04'),
 'type':('packet.field1D = 41','packet.field1D = 40'),
 'duration':(' & 15) + 25',' & 7) + 25'),
 'alpha':('% 71U + 60','% 71U + 59'),
 'position':('packet.position.x = x','packet.position.x = y'),
 'size':('sample * D_8009FD90 + D_8009FD94','sample * D_8009FD94 + D_8009FD90'),
 'speed':('sample * 154.0f + 205.0f','sample * 154.0f + 204.0f'),
 'direction':('&packet.direction.x, &packet.direction.z','&packet.direction.z, &packet.direction.x'),
 'flag1':('? 0x40 : 0','? 0x20 : 0'),
 'flag2':('? 0x80 : 0','? 0x20 : 0'),
 'flags-base':(' | 0xC000',' | 0x8000'),
 'tail':('packet.field64 = -1','packet.field64 = 0'),
 'height':('packet.field24 = D_8009FDA0','packet.field24 = D_8009FD8C'),
 'capture':('bonus = D_8009FD8C','bonus = D_8009FDA0'),
 'factory':('&packet, 1, 4, slot, 1','&packet, 1, 4, slot, 0'),
 'return':('    return 1;','    return 0;')}
 for key,(old,new)in controls.items():assert fn.count(old)==1,key
 owner=(s.FROZEN/s.SOURCE).read_text();typ=owner[owner.rfind('typedef struct {',0,owner.index('} MenuRadialPacketE4070;')):owner.index('} MenuRadialPacketE4070;')+len('} MenuRadialPacketE4070;')]
 code='#include <ultra64.h>\ntypedef struct {f32 x,y,z;} MenuBurstPointE4070;\n'+typ+'\n'+s.PIN['declarations']+'\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid *func_15130374(void *,u8,s32,u8,s32);\n'
 code+=r'''
 _Static_assert(sizeof(void*)==4 && sizeof(MenuRadialPacketE4070)==112 && __builtin_offsetof(MenuRadialPacketE4070,flags)==0x58 && __builtin_offsetof(MenuRadialPacketE4070,field65)==0x65,"SDK32 descriptor ABI");
 f32 D_8009FD8C,D_8009FD90,D_8009FD94,D_8009FD98,D_8009FD9C,D_8009FDA0;
 static u32 mode,flags,success,mut,calls,errors,ri,fi;static union{u32 align;u8 bytes[256];} output;
 static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
 s32 func_150ADA20(void){u32 values[]={mode,mode*0x1234567u,flags&1,flags>>1};u32 expected[]={0,1,5,6};u32 index=ri++;if(index>=4||calls++!=expected[index])errors++;if(mut&1 && index==0)D_8009FD8C=8.5f;return values[index];}
 f32 func_150ADA68(void){u32 index=fi++;if(index>=2||calls++!=2+index)errors++;if(mut&1 && index==0){D_8009FD90=96.0f;D_8009FD94=102.0f;D_8009FD98=.25f;}return index==0?.5f:.25f;}
 void func_15143874(s16 heading,f32 speed,f32*x,f32*z){if(calls++!=4||heading!=(s16)mode||word(speed)!=word(30.4375f))errors++;*x=7.25f;*z=9.75f;if(mut&2)D_8009FDA0=3.5f;}
 void *func_15130374(void*v,u8 a,s32 n,u8 slot,s32 context){u32 i;MenuRadialPacketE4070*d=v;if(calls++!=7||a!=1||n!=4||slot!=(u8)mode||context!=1)errors++;
 if(d->field00!=0x200005||d->field04||d->field08!=0xe03||d->field0A!=(s16)((mode&15)+25)||d->field0C||d->field10||d->field14!=64||d->field15!=11||d->field16!=106||d->field17!=255||d->field18!=176||d->field19!=160||d->field1A!=42||d->field1B!=(u8)((mode*0x1234567u)%71u+60)||d->field1C!=255||d->field1D!=41||d->field1E!=28||d->field20!=9||d->field22!=25||word(d->field24)!=word((mut&2)?3.5f:1.5f)||word(d->field28)!=word((mut&1)?37.5f:74.25f)||word(d->field2C)!=word((mut&1)?37.5f:74.25f)||word(d->position.x)!=word(1.25f)||word(d->position.y)!=word(-2.5f)||word(d->position.z)!=word(3.75f)||word(d->field3C)||word(d->field40)||word(d->field44)||word(d->direction.x)!=word(7.25f)||word(d->direction.y)||word(d->direction.z)!=word(9.75f)||word(d->field54)||d->flags!=(0xce05|((flags&1)?0x40:0)|((flags&2)?0x80:0))||d->field60!=3||d->field61!=3||d->field62!=10||d->field63!=-1||d->field64!=-1||d->field65)errors++;
 if(success){for(i=0;i<112;i++)output.bytes[0x10+i]=((u8*)v)[i];output.bytes[0x9c]=0;}return success?output.bytes:0;}
 void *memcpy(void*a,const void*b,size_t n){u32 i;u8*dst=a;const u8*src=b;if(calls++!=8||dst!=output.bytes+0xa8||n!=4||word(*(const f32*)b)!=word(2.25f))errors++;for(i=0;i<n;i++)dst[i]=src[i];return a;}
 '''
 variants=[('selected',fn)]+[(key,fn.replace(old,new,1))for key,(old,new)in controls.items()]
 variants.append(('capture-late',fn.replace('    bonus = D_8009FD8C;\n','').replace('    allocated = func_15130374','    bonus = D_8009FD8C;\n    allocated = func_15130374')))
 for key,body in variants:code+='\n'+body.replace('func_150B879C','test_'+key.replace('-','_'),1)+'\n'
 code+=r'''
 typedef s32(*Fn)(s32,s16,f32,f32,f32,f32,f32,f32,s16,u8,f32,s32,f32,s32,u8);
 static int check(Fn fn){for(mode=0;mode<256;mode++)for(flags=0;flags<4;flags++)for(success=0;success<2;success++)for(mut=0;mut<4;mut++){D_8009FD8C=2.25f;D_8009FD90=95.f;D_8009FD94=101.f;D_8009FD98=.5f;D_8009FD9C=.125f;D_8009FDA0=1.5f;calls=errors=ri=fi=0;if(fn(3,2,1.25f,-2.5f,3.75f,0,0,0,(s16)mode,0,0,0,0,0,(u8)mode)!=1||errors||calls!=8+success||ri!=4||fi!=2)return 1;}return 0;}
 static int run(void){if(check(test_selected))return 1;
 '''
 for i,(key,_)in enumerate(variants[1:]):code+='if(!check(test_'+key.replace('-','_')+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=s.OUT/'native.c';path.write_text(code);results={}
 for opt in('-O0','-O2','-O3'):
  exe=s.OUT/('native'+opt);run=subprocess.run(native_command(opt)+['-fno-builtin',str(path),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True);assert run.returncode==0,(opt,run.stderr)
  run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr)
  results[opt]=dict(cases=8192,negative_controls=len(variants)-1,UBSan=True)
 report=dict(passes=True,profiles=results,incoming_private_aliases_not_claimed=True)
 (s.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
