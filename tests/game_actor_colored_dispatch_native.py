import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_actor_colored_dispatch_match as p
out=p.out;root=p.root
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 source=p.MANIFEST['selected'];start=source.index('s32 func_151026BC(actor,');end=source.index('\n#endif',start);selected=source[start:end]
 controls={
  'null':('if (actor == NULL) return 0;','if (actor == NULL) return 1;'),
  'special50':('case 0x58: case 0x5B: case 0x80:','case 0x59: case 0x5B: case 0x80:'),
  'special255':('case 0x5A: case 0x5F: case 0x74:','case 0x5C: case 0x5F: case 0x74:'),
  'fallback':('owner->unk31C->unk78 == 0x3B','owner->unk31C->unk78 == 0x3A'),
  'first':('first = 50; second = 255; break;','first = 51; second = 255; break;'),
  'second':('first = 255; second = 0; break;','first = 255; second = 1; break;'),
  'first_vector':('D_800A21A0[arg2]','D_800A21F4[arg2]'),
  'second_vector':('D_800A21F4[arg2]','D_800A21A0[arg2]'),
  'mode':('D_800A2248[arg2]','D_800A2248[0]'),
  'halfword':('arg1, first, second, 0,','(s16)(arg1+1), first, second, 0,'),
  'float20':('20.0f, 20.0f,','19.0f, 20.0f,'),
  'float4':('4.0f, D_800A233C','3.0f, D_800A233C'),
  'byte3':('D_800A233C, arg3, arg4, arg5','D_800A233C, (u8)(arg3+1), arg4, arg5'),
  'byte4':('D_800A233C, arg3, arg4, arg5','D_800A233C, arg3, (u8)(arg4+1), arg5'),
  'word5':('D_800A233C, arg3, arg4, arg5','D_800A233C, arg3, arg4, arg5+1'),
 }
 code=r'''#include <ultra64.h>
 #include "structs.h"
 _Static_assert(sizeof(void*)==4 && __builtin_offsetof(struct127,unk31C)==0x31c && __builtin_offsetof(struct126,unk78)==0x78,"SDK32 actor layout");
 f32 D_800A21A0[7][3],D_800A21F4[7][3],D_800A233C;u8 D_800A2248[8];
 static struct127 actor;static struct126 attached;static u32 mode,first,second,calls,bad;
 s32 func_15100600(struct127 *a,f32 *b,f32 *c,u8 d,s16 e,u8 f,u8 g,u8 h,f32 i,f32 j,f32 k,f32 l,u8 m,u8 n,s32 o){
  calls++;if(a!=&actor||b!=D_800A21A0[mode]||c!=D_800A21F4[mode]||d!=D_800A2248[mode]||e!=(s16)0x8001||f!=first||g!=second||h!=0||i!=20.0f||j!=20.0f||k!=4.0f||l!=0.08f||m!=0x81||n!=0xfe||(u32)o!=0xabcdef01u)bad=1;return (s32)0x87654321u;
 }
 '''
 variants=[('selected',selected)]+[(name,selected.replace(a,b,1))for name,(a,b) in controls.items()]
 for name,body in variants:
  assert name=='selected' or body!=selected,name
  fn='test_'+name;code+=f's32 {fn}(u8 *,int,int,int,int,s32);\n'+body.replace('func_151026BC(',fn+'(',1)+'\n'
 code+=r'''
 typedef s32(*T)(u8*,int,int,int,int,s32);
 static int check(T test){u32 id,kind,m,p;for(id=0;id<256;id++)for(kind=0;kind<2;kind++)for(m=0;m<7;m++)for(p=0;p<2;p++){
  actor.id=id;actor.unk31C=&attached;attached.unk78=kind?0x3b:0x3a;mode=m;calls=bad=0;D_800A233C=0.08f;
  if(id==0x58||id==0x5b||id==0x80){first=50;second=255;}
  else if(id==0x5a||id==0x5f||id==0x74||id==0x75||id==0x7a){first=255;second=0;}
  else if(kind){first=255;second=0;}else{first=50;second=255;}
  if((u32)test(p?(u8*)&actor:0,(s32)0x12348001u,(s32)(0x12340000u|m),(s32)0xfedcba81u,(s32)0x876543feu,(s32)0xabcdef01u)!=(p?0x87654321u:0u)||calls!=p||bad)return 1;
  }return 0;}
 static int run(void){u32 i;for(i=0;i<8;i++)D_800A2248[i]=i*13+5;if(check(test_selected))return 1;
 '''
 for i,name in enumerate(controls):code+=f'if(!check(test_{name}))return {20+i};\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_screen'+opt);r=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.stdout[-2000:],r.stderr[-2000:]);r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases=256*2*7*2,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=profiles,valid_vector_rows_only=True,helper='modeled',source_installed=False);(out/'native_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
