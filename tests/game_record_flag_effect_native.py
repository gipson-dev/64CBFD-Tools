from pathlib import Path
import json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def qualify(r,o):
 body=(o/'selected-input.c').read_text();headers=(o/'selected-headers.c').read_text()
 controls=(('wrong-inverted-bit',body.replace('bits & 2 ? 0 : 2','bits & 2 ? 2 : 0')),
  ('missing-bit-8',body.replace('bits & 8 ? 8 : 0','bits & 8 ? 0 : 0')),
  ('missing-bit-16',body.replace('bits & 0x10 ? 0x10 : 0','bits & 0x10 ? 0 : 0')),
  ('wrong-selector-byte',body.replace('record[0x1F]','record[0x1E]')),
  ('wrong-global-float',body.replace('*(f32 *)&D_8009667C','1.0f')),
  ('wrong-range',body.replace('100.0f','50.0f')),
  ('wrong-return',body.replace('return 1;','return 0;')))
 assert all(text!=body for _,text in controls)
 code=headers+r'''
 u32 D_8009667C;
 static union{u32 align;u8 bytes[96];} storage;
 static u8 *rec;static u32 bits,selector,height,mode,count,error;
 static u32 fpbits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
 void func_151A9390(u8 flags,u8 choice,const void *position,const f32 *floating,f32 h,f32 range,s32 lifetime,u8 alpha,s32 enable){
  count++;
  if(flags!=((bits&31u)^2u)||choice!=selector||position!=rec||floating||fpbits(h)!=height||fpbits(range)!=0x42C80000u||lifetime!=-1||alpha!=255||enable!=1)error=1;
  if(mode){*(u32*)(rec+24)=0xFEDCBA98u;rec[31]=255;D_8009667C=0xDEADBEEFu;}
 }
 '''
 for i,(_,text)in enumerate((('valid',body),)+controls):code+=text.replace('func_15014144(','root_%d('%i)+'\n'
 code+='static s32 (*roots[])(u8*)={'+','.join('root_%d'%i for i in range(8))+'};\n'
 code+=r'''
 static int run(void){u32 i,j,k,n,failed,killed=0,answer,cases=0;static const u32 fp[]={0,0x80000000u,0x3F800000u,0x7FC12345u};static const u32 sel[]={0,1,8,9,255};
  for(n=0;n<64;n++)for(i=0;i<5;i++)for(j=0;j<4;j++)for(mode=0;mode<2;mode++){
   bits=(n&31u)|(n&32u?0x80000000u:0);selector=sel[i];height=fp[j];cases++;
   for(k=0;k<8;k++){
    u32 at;for(at=0;at<96;at++)storage.bytes[at]=(at*29+90)&255;
    rec=storage.bytes+16;*(u32*)(rec+24)=bits;rec[31]=selector;D_8009667C=height;count=error=0;
    answer=roots[k](rec);failed=error||count!=1||answer!=1||D_8009667C!=(mode?0xDEADBEEFu:height)||*(u32*)(rec+24)!=(mode?0xFEDCBA98u:bits)||rec[31]!=(mode?255:selector);
    for(at=0;at<96;at++)if(!(at>=40&&at<44)&&at!=47&&storage.bytes[at]!=(u8)(at*29+90))failed=1;
    if(!k&&failed)return 2;if(k&&failed)killed|=1u<<(k-1);
   }
  }
  return cases==2560&&killed==127u?0:3;
 }
 '''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 rows=[]
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  rows.append(dict(profile=opt,cases=2560,executions=20480,all_seven_controls_effective=True,controls=[n for n,_ in controls],UBSan=True,whole_record_canaries=True,all_nine_arguments_checked=True,float_bit_patterns=4,low_five_flag_combinations=32,high_bit_patterns=2,selector_boundaries=5,helper_mutations_checked=True,return_one=True))
 (o/'private-native-runtime.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows,flush=True)
 return rows
