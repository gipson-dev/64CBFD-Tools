from pathlib import Path
import itertools,subprocess,sys
from tools.experiments import game_extent_15149a94_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_extent_15149a94_oracle as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_point_transform_match import read
def run():
 fn=body((out/'after.c').read_text(),'func_15149A94')
 controls={'flag':('actor[0x74] & 2','actor[0x74] & 4'),'timer':('< 5)','< 4)'),'dispatch':('actor[0x70], 13,','actor[0x70], 14,'),'clear':('&= ~1','&= ~2'),'second':('params + 0x20','params + 0x24')}
 code='''#include <ultra64.h>
 typedef struct struct171 { u8 bytes[512]; } struct171;
 f32 D_800A578C=0.75f,D_800A5790=0.75f;
 void func_1513F680(struct171*,u8,u8,u8,u8);
 '''+fn.replace('func_15149A94(', 'selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert old in fn,name
  code+=fn.replace('func_15149A94(', 'bad_'+name+'(',1).replace(old,new,1)+'\n'
 rows=[]
 for flags,timer,x,y,factor,mutation in itertools.product((0,2,8,10),(-1,4,5,100),(0.,3.,4.),(0.,6.,8.),(0.,0.5,1.),(0,1)):
  c=guest.Case(flags,timer,x,y,factor,mutation);initial=guest.fixture(c);m,calls=guest.reference(initial,c)
  values=[flags,timer&65535,guest.bits(x),guest.bits(y),guest.bits(factor),mutation,read(m,guest.ACTOR+0x2c),read(m,guest.ACTOR+0x30),read(m,guest.ACTOR+0x58),read(m,guest.ACTOR+0x1c,2),m[guest.ACTOR+0x70],m[guest.ACTOR+0x71],m[guest.ACTOR+0x72],m[guest.ACTOR+0x73],m[guest.ACTOR+0x74],m[guest.ACTOR+0x158],len(calls)]
  for i in range(2):values.extend(calls[i][1][1:] if i<len(calls) else (0,0,0,0))
  rows.append('{'+','.join('0x%Xu'%v for v in values)+'}')
 code+='''
 typedef struct { u32 flags,timer,x,y,factor,mutation,ex,ey,eflags,etimer,e70,e71,e72,e73,e74,e158,ncalls,a0,a1,a2,a3,b0,b1,b2,b3; } Row;
 static const Row rows[]={'''+',\n'.join(rows)+'''};
 static u32 data[128], calls[2][4], count, mutation;
 void func_1513F680(struct171 *p,u8 a,u8 b,u8 c,u8 d){
  u8 *actor=(u8*)p; if(count<2){calls[count][0]=a;calls[count][1]=b;calls[count][2]=c;calls[count][3]=d;}count++;
  actor[0x70]=a;actor[0x71]=b;actor[0x72]=c;actor[0x73]=d;
  if(mutation){*(u16*)(actor+0x1c)=3;actor[0x158]=23;}
 }
 typedef s32 (*Fn)(u8*);
 static int check(Fn fn) {
  for(u32 k=0;k<sizeof(rows)/sizeof(rows[0]);k++){
   const Row *r=&rows[k];u8 *a=(u8*)data;for(u32 i=0;i<512;i++)a[i]=(i*29+0x35)&255;
   *(u32*)(a+0x2c)=r->x;*(u32*)(a+0x30)=r->y;*(f32*)(a+0x118)=4.f;*(f32*)(a+0x130)=8.f;*(u32*)(a+0x154)=r->factor;
   *(u16*)(a+0x1c)=r->timer;*(u32*)(a+0x58)=0x12345679;a[0x74]=r->flags;a[0x70]=7;a[0x72]=9;a[0x73]=11;a[0x158]=22;count=0;mutation=r->mutation;
   if(fn(a)!=1 || *(u32*)(a+0x2c)!=r->ex || *(u32*)(a+0x30)!=r->ey || *(u32*)(a+0x58)!=r->eflags || *(u16*)(a+0x1c)!=r->etimer || a[0x70]!=r->e70 || a[0x71]!=r->e71 || a[0x72]!=r->e72 || a[0x73]!=r->e73 || a[0x74]!=r->e74 || a[0x158]!=r->e158 || count!=r->ncalls)return 1;
  u32 expected[]={r->a0,r->a1,r->a2,r->a3,r->b0,r->b1,r->b2,r->b3};for(u32 i=0;i<count;i++)for(u32 j=0;j<4;j++)if(calls[i][j]!=expected[i*4+j])return 1;
  }
  return 0;
 }
 static int run(void){ if(check(selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 path=out/'native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
  print(opt,len(rows),'native cases and',len(controls),'negative controls passed',flush=True)
