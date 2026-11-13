"""Native 32-bit finite-domain checks with effective negative controls."""
import subprocess
from tools.experiments import game_paired_height_descriptor_screen as packet
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run():
 report={}
 for spec in packet.MANIFEST['targets']:
  name=spec['name'];fn=body(spec['selected_source'],name);first=name.endswith('5F94')
  a=spec['selected_source'].index('typedef struct { u8 *context;');b=spec['selected_source'].index('s32 '+name+'(',a)
  declarations=spec['selected_source'][a:b]
  controls={'threshold':('- 100.0f','- 99.0f'),'active':('local.payload.active = 1','local.payload.active = 0'),
            'duration':('desc.duration = 300','desc.duration = 301'),'size':('desc.size = '+('25.0f' if first else '80.0f'),'desc.size = 10.0f'),
            'fallback':(' + D_800A0414' if first else ' + D_800A0454',' - D_800A0414' if first else ' - D_800A0454')}
  text='#include <ultra64.h>\n'+declarations+'\n'+fn.replace(name+'(','selected(',1)+'\n'
  for label,(old,new) in controls.items():
   assert fn.count(old)==1,(label,old);text+=fn.replace(name+'(','bad_'+label+'(',1).replace(old,new,1)+'\n'
  cs=('D_800A0410','D_800A0414','D_800A0418') if first else ('D_800A0450','D_800A0454','D_800A0458')
  text+='\nf32 '+','.join(cs)+';\n'
  text+='''
 static u32 actor_words[128],context_words[64],out_words[64];
 static u8 descriptor[48]; static u32 hit,allocated,mutation,nquery,nfactory,ncopy,failed;
 static f32 expected_y;
 void *memcpy(void *d,const void *s,u32 n){u32 i;u8 *dst=d;const u8 *src=s;ncopy++;for(i=0;i<n;i++)dst[i]=src[i];return d;}
 s32 func_15045800(f32 *p,u16 mode,f32 low,void *result){
  u8 *a=(u8*)actor_words;nquery++;if(mode||p[0]!=1.25f||p[1]!=expected_y+100.0f||p[2]!=-3.0f||low!=expected_y-100.0f||result!=(u8*)context_words+0x34)failed=1;
  *(f32*)result=18.5f;if(mutation&1)*(f32*)(a+0x18)=7.5f;if(mutation&2)a[0x3b]^=0x55;return hit;
 }
 void *func_1513418C(void *p,s32 count,u8 selector,s32 category){u32 i;u8 *src=p;nfactory++;if(count!=12||selector!=255||category)failed=2;for(i=0;i<48;i++)descriptor[i]=src[i];return allocated?(void*)out_words:(void*)0;}
 typedef union {u32 i;f32 f;} FloatBits;
 static u32 word(const u8*p){return (u32)p[0]|((u32)p[1]<<8)|((u32)p[2]<<16)|((u32)p[3]<<24);}
 static u32 bits(f32 x){FloatBits v;v.f=x;return v.i;}
 typedef s32 (*Routine)(u8*,u8*);
 static int check(Routine f){u32 yi,h,al,mut,seed,i;f32 ys[3]={4.5f,-7.0f,1000.0f};u8 *a=(u8*)actor_words,*ctx=(u8*)context_words,*out=(u8*)out_words;
 for(yi=0;yi<3;yi++)for(h=0;h<2;h++)for(al=0;al<2;al++)for(mut=0;mut<4;mut++)for(seed=0;seed<2;seed++){
  s32 answer;f32 height;for(i=0;i<sizeof(actor_words);i++)a[i]=(u8)(i+seed*19);for(i=0;i<sizeof(context_words);i++)ctx[i]=(u8)(i+seed*23);for(i=0;i<sizeof(out_words);i++)out[i]=0xa5;
  *(f32*)(a+0x14)=1.25f;*(f32*)(a+0x18)=ys[yi];*(f32*)(a+0x1c)=-3.0f;a[0x3b]=0x73;
  expected_y=ys[yi];hit=h;allocated=al;mutation=mut;nquery=nfactory=ncopy=failed=0;
 '''+cs[0]+'''=100.0f;'''+cs[1]+'''=9.0f;'''+cs[2]+'''=2.0f;
  answer=f(a,ctx);height=h?18.5f:((mut&1)?7.5f:ys[yi])+9.0f;
  if(failed||nquery!=1||nfactory!=1||ncopy!=al||(u32)answer!=(al?(u32)out:0))return 1;
  if(word(descriptor)!=0||word(descriptor+4)!=0||descriptor[8]!=(u8)(0x73^((mut&2)?0x55:0))||word(descriptor+12)!=(u32)a||descriptor[16]||word(descriptor+20)||word(descriptor+24)||word(descriptor+28))return 2;
  if(word(descriptor+32)!=bits('''+('25.0f' if first else '80.0f')+''')||word(descriptor+36)!=bits(2.0f)||descriptor[40]!=0x2c||descriptor[41]!=1||descriptor[42]!=10||descriptor[43]!='''+('4' if first else '5')+'''||descriptor[44]!='''+('1' if first else '2')+'''||descriptor[45]!='''+('2' if first else '3')+''')return 3;
  if(al&&(word(out+0x58)!=(u32)ctx||out[0x5c]!=1||word(out+0x60)!=bits(height)))return 4;
 }return 0;}
 static int run(void){if(check(selected))return 10;
'''
  for index,label in enumerate(controls):text+='if(!check(bad_'+label+'))return '+str(20+index)+';\n'
  text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
  file=packet.OUT/(name+'-native.c');file.write_text(text);results={}
  for opt in ('-O0','-O2','-O3'):
   exe=packet.OUT/(name+'-native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-fno-builtin-memcpy',str(file),'-o',str(exe)],cwd=packet.ROOT,capture_output=True,text=True)
   assert r.returncode==0,(r.stdout,r.stderr)
   r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0,(name,opt,r.returncode,r.stderr)
   results[opt]={'cases':96,'effective_negative_controls':len(controls),'ubsan':True}
  report[name]=results
 return report
