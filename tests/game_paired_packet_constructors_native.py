import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_paired_packet_constructors_match as p
out=p.out;root=p.root
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=(out/'paired_source.c').read_text();types=selected[selected.index('typedef struct { f32 v[6]'):selected.index('/* Construct the fixed packet')]
 bodies=[body(selected,n) for n in ('func_1514E00C','func_1514E194')]
 controls={
  'size':('source.size[0] = 20.0f','source.size[0] = 19.0f'),
  'type':('desc.type = 3','desc.type = 4'),
  'flags':('desc.flags40 = 0x12002','desc.flags40 = 0x12003'),
  'color':('desc.color[1] = 0x8E','desc.color[1] = 0x8F'),
  'global':('source.scalar20 = D_800A5E08','source.scalar20 = D_800A5E0C'),
  'identity':('runtime.identity = owner[0x3B]','runtime.identity = owner[0x3A]'),
  'runtime':('runtime.v[2] = 59.0f','runtime.v[2] = 58.0f'),
  'attach':('(s32)owner, 6)', '(s32)owner, 5)'),
  'effect':('owner, 5, -1, 255, 1','owner, 4, -1, 255, 1'),
 }
 code='''#include <ultra64.h>\n_Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");\n'''+types+'''\nvoid func_151D74B0(u8 *,u8,s8,u8,s32);\ns32 func_1514EC1C(s32,s32,s16);\n'''
 code+=r'''
 f32 D_800A5E08,D_800A5E0C,D_800A5E10,D_800A5E14;
 static u8 owner[256];static u32 bad,calls,which,answer,identity,mutate;
 static u32 word(f32 v){union {u32 u;f32 f;} x;x.f=v;return x.u;}
 static f32 value(u32 v){union {u32 u;f32 f;} x;x.u=v;return x.f;}
 u8 *func_15189FF0(u8 *d,u8 *s,const void *v,u8 kind,u8 mode,u8 first,u8 variant){
  PacketDescriptor1514 *p=(PacketDescriptor1514*)d;PacketSource1514 *q=(PacketSource1514*)s;const PacketRuntime1514 *r=(const PacketRuntime1514*)v;u32 i;
  calls++;if(calls!=1||kind!=2||mode||first||variant)bad=1;
  if(p->type!=3||p->flags02!=0x401||p->flags04||p->zero08||p->zero0c||p->flags40!=0x12002||p->strength!=255||p->color[0]!=255||p->color[1]!=0x8e||p->color[2]!=0x19||p->color[3]!=255)bad=1;
  for(i=0;i<6;i++)if(word(p->vector[i]))bad=1;
  for(i=0;i<4;i++)if(word(q->size[i])!=(which?0x41800000:0x41a00000))bad=1;
  if(word(q->zero10)||word(q->zero14)||word(q->half18)!=0x3f000000||word(q->half1c)!=0x3f000000||word(q->scalar20)!=(which?0x3f345678:0x3f123456)||word(q->one48)!=0x3f800000)bad=1;
  for(i=0;i<4;i++)if(q->tail[i])bad=1;
  if(word(r->v[0])!=0x420c0000||word(r->v[1])!=0x41d80000||word(r->v[2])!=0x426c0000||word(r->v[3])!=0x420c0000||word(r->v[4])!=0x41d80000||word(r->v[5])!=(which?0xc056789a:0xc0345678)||r->owner!=owner||r->kind!=6||r->identity!=identity||r->mode!=-1)bad=1;
  if(mutate)owner[0x3b]^=0x55;return (u8*)answer;
 }
 s32 func_1514EC1C(s32 a,s32 b,s16 c){calls++;if(calls!=2||(u32)a!=answer||(u32)b!=(u32)owner||c!=6)bad=1;return 7;}
 void func_151D74B0(u8 *a,u8 b,s8 c,u8 d,s32 e){calls++;if(calls!=3||a!=owner||b!=5||c!=-1||d!=255||e!=1||owner[0x3b]!=(identity^(mutate?0x55:0)))bad=1;}
 '''
 for idx,b in enumerate(bodies):code+='\n'+b.replace(('func_1514E00C','func_1514E194')[idx],f'test_{idx}',1)+'\n'
 for name,(a,b) in controls.items():
  assert bodies[0].count(a)==1,name
  code+='\n'+bodies[0].replace(a,b,1).replace('func_1514E00C','control_'+name,1)+'\n'
 code+=r'''
 typedef void (*T)(u8 *);
 static int check(T test,u32 variant){u32 id,ok,m;which=variant;
  D_800A5E08=value(0x3f123456);D_800A5E0C=value(0xc0345678);D_800A5E10=value(0x3f345678);D_800A5E14=value(0xc056789a);
  for(id=0;id<256;id++)for(ok=0;ok<2;ok++)for(m=0;m<2;m++){
   identity=id;answer=ok?0x50000:0;mutate=m;owner[0x3b]=id;owner[0x3a]=id^0xff;calls=bad=0;test(owner);if(bad||calls!=3)return 1;
  }return 0;}
 static int run(void){if(check(test_0,0)||check(test_1,1))return 1;
 '''
 for i,name in enumerate(controls):code+=f'if(!check(control_{name},0))return {20+i};\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_screen.c';src.write_text(code);profiles={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_screen'+opt);r=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.stdout[-3000:],r.stderr[-3000:])
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases_per_target=1024,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=profiles,helpers='modeled',source_installed=False);(out/'native_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
