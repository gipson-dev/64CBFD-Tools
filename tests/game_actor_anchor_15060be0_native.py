"""Native SDK32 memory views, explicit alias mode and valid conversion domain."""
import json,struct,subprocess
from tools.tests import game_actor_anchor_15060be0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def cases():return[c for c in g.cases()if c.alias==0 and(c.identity<187 or c.identity==255)and g.reference(g.fixture(c),c)[1]]
def build():
 cs=cases();rows=[];expected=bytearray()
 for i,c in enumerate(cs):
  result=g.reference(g.fixture(c),c)[0];expected.extend(struct.pack('<I',i)+b''.join(struct.pack('>H',g.read(result,g.ACTOR+0x1BC+j*2,2))for j in range(3)));row=(c.identity,c.present,c.disabled,c.distance,c.scale,c.index,*c.direction,*c.origin,*c.position,c.seed);rows.append('{'+','.join('0x%Xu'%g.u32(v)for v in row)+'}')
 source=r'''
#include <ultra64.h>
#include "variables.h"
_Static_assert(sizeof(void*)==4,"SDK32");
_Static_assert(sizeof(s16)==2&&sizeof(s32)==4,"widths");
_Static_assert(sizeof(struct127)==812,"actor stride");
_Static_assert(sizeof(struct124)==44,"model size");
_Static_assert(__builtin_offsetof(struct127,pad1BC)==0x1BC,"anchor");
_Static_assert(__builtin_offsetof(struct127,unk1D4)==0x1D4,"transforms");
static struct127 actor;
static struct124 model;
static u32 matrix_words[4096];
struct124 *D_800D1C90[187];
u8 D_800C3E90;
static u8 before_actor[812],before_model[44],before_buffer[16384];
static struct124 *before_table[187];
static u8 record[10];
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
f32 sqrtf(f32 x){__asm__ volatile("sqrtss %0,%0":"+x"(x));return x;}
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static int different(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 1;return 0;}
'''+(g.out/'selected-body.c').read_text()+r'''
static const u32 cases[][16]={ROWS};
static int flush(void){u32 done=0;while(done<10){s32 n;__asm__ volatile("int $0x80":"=a"(n):"0"(4),"b"(1),"c"(record+done),"d"(10-done):"memory");if(n<=0)return 1;done+=(u32)n;}return 0;}
static int run(void){u32 i,j,k;const u32*c;u16*outputs;f32*matrix;u8*p;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  c=cases[i];p=(u8*)&actor;for(j=0;j<812;j++)p[j]=(u8)((0x30000+j)*29+c[15]*11+90);
  p=(u8*)&model;for(j=0;j<44;j++)p[j]=(u8)((0x50000+j)*29+c[15]*11+90);
  p=(u8*)matrix_words;for(j=0;j<16384;j++)p[j]=(u8)((0x60000+j)*29+c[15]*11+90);
  actor.id=(u8)c[0];actor.unk1D4=c[1]?(struct255*)matrix_words:NULL;actor.y_scale=real(c[4]);actor.x_position=real(c[12]);actor.y_position=real(c[13]);actor.z_position=real(c[14]);
  for(j=0;j<187;j++)D_800D1C90[j]=&model;D_800C3E90=(u8)c[2];*(s16*)model.pad14=(s16)c[3];((u8*)&model)[0x27]=(u8)c[5];matrix=(f32*)matrix_words+c[5]*16;
  for(j=0;j<3;j++){matrix[4+j]=real(c[6+j]);matrix[12+j]=real(c[9+j]);}
  copy(before_actor,&actor,812);copy(before_model,&model,44);copy(before_buffer,matrix_words,16384);copy(before_table,D_800D1C90,sizeof(before_table));
  func_15060BE0(&actor);
  if(different(before_model,&model,44)||different(before_buffer,matrix_words,16384)||different(before_table,D_800D1C90,sizeof(before_table))||D_800C3E90!=(u8)c[2])return 2;
  p=(u8*)&actor;for(j=0;j<812;j++)if(!(0x1BC<=j&&j<0x1C2)&&p[j]!=before_actor[j])return 3;
  record[0]=(u8)i;record[1]=(u8)(i>>8);record[2]=(u8)(i>>16);record[3]=(u8)(i>>24);outputs=(u16*)&actor.pad1BC;
  for(j=0;j<3;j++){k=outputs[j];record[4+2*j]=(u8)(k>>8);record[5+2*j]=(u8)k;}if(flush())return 1;
 }return 0;
}
'''.replace('ROWS',',\n'.join(rows))
 return source+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),bytes(expected),len(cs)
def main():
 source,expected,n=build();path=g.out/'native.c';path.write_text(source);report={}
 for opt in('-O0','-O2','-O3'):
  exe=g.out/('native'+opt);cmd=native_command(opt)+['-fno-strict-aliasing','-fsanitize=float-cast-overflow',str(path),'-o',str(exe)];r=subprocess.run(cmd,cwd=g.root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr;r=subprocess.run([str(exe)],capture_output=True,timeout=60)
  if r.stdout!=expected:
   at=next((i for i,(a,b)in enumerate(zip(r.stdout,expected))if a!=b),min(len(r.stdout),len(expected)));raise AssertionError((opt,r.returncode,len(r.stdout),len(expected),at,r.stdout[max(0,at-12):at+20].hex(),expected[max(0,at-12):at+20].hex(),r.stderr))
  assert r.returncode==0 and not r.stderr;report[opt]=dict(cases=n,exact_output_bytes=len(expected),SDK32=True,UBSan=True,float_cast_overflow_sanitized=True,strict_aliasing=False,all_other_actor_bytes_and_complete_inputs_unchanged=True)
 result=dict(profiles=report,valid_signed32_conversion_domain=True,big_endian_overlap_and_extended_table_cases_guest_only=True);(g.out/'native.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
