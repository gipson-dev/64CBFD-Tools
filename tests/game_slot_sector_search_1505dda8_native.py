"""Execute the actual typed C body with SDK32, strict aliasing and UBSan."""
import json,struct,subprocess
from tools.tests import game_slot_sector_search_1505dda8_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def native_cases():return[c for c in g.cases()if c.limit<26 and not c.stop_after and not c.mutation&16]
def payload(m,c):
 a=g.actor(c);return bytes(m[a+i]for i in range(812))+b''.join(struct.pack('>I',g.read(m,g.TABLE+i*812))for i in range(26))+bytes(m[g.MARK+i]for i in range(32))+struct.pack('>I',g.read(m,g.LIMIT))
def build():
 cs=native_cases();rows=[];expected=bytearray()
 for i,c in enumerate(cs):
  m,calls,result=g.reference(g.fixture(c),c);expected.extend(struct.pack('<I',i)+struct.pack('>II',result,len(calls))+payload(m,c)+bytes(calls));rows.append('{'+','.join('0x%Xu'%g.u32(v)for v in(c.limit,c.pattern,c.match,c.heading,c.angle,c.width,c.velocity,c.scale,c.distance,c.miss,c.mutation,c.new_limit,c.alias,c.unused,c.seed,c.state))+'}')
 source=r'''
#include <ultra64.h>
#include "structs.h"
_Static_assert(sizeof(void*)==4,"SDK32");
_Static_assert(sizeof(struct127)==812,"actor stride");
_Static_assert(__builtin_offsetof(struct127,xz_velocity)==0x3C,"velocity");
_Static_assert(__builtin_offsetof(struct127,unk76)==0x76,"heading");
struct127 D_800CC2D0[26];
s32 D_80082FA0;
static struct127 independent_actor;
static struct127 *current_actor;
static u32 mark[8],call_count;
static u8 call_slots[32],record[964];
static const u32 *c;
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static void be(u8*p,u32 u){p[0]=(u8)(u>>24);p[1]=(u8)(u>>16);p[2]=(u8)(u>>8);p[3]=(u8)u;}
static f32 func_1505DF10(struct127*a,u8 slot,u16*h,f32*xz,f32*y,s32 unused){u32 v;
 if(a!=current_actor||unused!=0||!h||!xz||!y||(void*)h==(void*)xz||(void*)h==(void*)y||(void*)xz==(void*)y||call_count>=32)__builtin_trap();
 call_slots[call_count++]=slot;mark[0]++;*h=(u16)c[3];*xz=real(0xC1200000);*y=real(0x3F000000);
 if(c[10]&1)a->unk76^=0x100;if(c[10]&2)a->xz_velocity=8.0f;if(c[10]&4)D_80082FA0=(s32)c[11];
 if(c[10]&8)D_800CC2D0[(slot+1)&255].interaction_state=0;
 v=((s32)slot==(s32)c[2]||(s32)c[2]==-2)?c[8]:c[9];mark[1]=v;mark[2]=slot;return real(v);
}
'''+(g.out/'selected-body.c').read_text()+r'''
static const u32 cases[][16]={ROWS};
static int flush(const u8*p,u32 size){u32 done=0;while(done<size){s32 n;__asm__ volatile("int $0x80":"=a"(n):"0"(4),"b"(1),"c"(p+done),"d"(size-done):"memory");if(n<=0)return 1;done+=(u32)n;}return 0;}
static int run(void){u32 i,j,k,v;u8*p;s32 result;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  c=cases[i];current_actor=(s32)c[12]<0?&independent_actor:&D_800CC2D0[c[12]];p=(u8*)current_actor;for(j=0;j<812;j++)p[j]=(u8)(j*29+c[14]*11+90);
  if((s32)c[12]<0){v=0;for(j=0;j<4;j++)v=(v<<8)|((j*29+c[14]*11+90)&255);current_actor->interaction_state=(s32)v;}
  p=(u8*)mark;for(j=0;j<32;j++)p[j]=(u8)(j*29+c[14]*11+90);
  for(j=0;j<26;j++)D_800CC2D0[j].interaction_state=(c[1]==0?1:c[1]==1?0:c[1]==2?j%2==0:(s32)j==(s32)c[2])?(s32)c[15]:0;
  current_actor->xz_velocity=real(c[6]);current_actor->unk76=(u16)c[4];D_80082FA0=(s32)c[0];mark[0]=0;call_count=0;
  result=func_1505DDA8(current_actor,(u8)c[13],(u16)c[5],real(c[7]));
  record[0]=(u8)i;record[1]=(u8)(i>>8);record[2]=(u8)(i>>16);record[3]=(u8)(i>>24);be(record+4,(u32)result);be(record+8,call_count);
  p=(u8*)current_actor;for(j=0;j<812;j++)record[12+j]=p[j];be(record+12,(u32)current_actor->interaction_state);be(record+12+0x3C,bits(current_actor->xz_velocity));v=current_actor->unk76;record[12+0x76]=(u8)(v>>8);record[12+0x77]=(u8)v;
  for(j=0;j<26;j++)be(record+824+4*j,(u32)D_800CC2D0[j].interaction_state);
  p=(u8*)mark;for(j=0;j<32;j++)record[928+j]=p[j];
  for(j=0;j<3;j++)be(record+928+4*j,mark[j]);
  if(!call_count){for(j=1;j<3;j++){v=0;for(k=0;k<4;k++)v=(v<<8)|((j*4+k)*29+c[14]*11+90)%256;be(record+928+4*j,v);}}
  be(record+960,(u32)D_80082FA0);if(flush(record,sizeof(record))||flush(call_slots,call_count))return 1;
 }return 0;
}
'''.replace('ROWS',',\n'.join(rows))
 return source+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),bytes(expected),len(cs)
def main():
 source,expected,n=build();path=g.out/'native.c';path.write_text(source);report={}
 for opt in('-O0','-O2','-O3'):
  exe=g.out/('native'+opt);r=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(path),'-o',str(exe)],cwd=g.root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60)
  if r.stdout!=expected:
   at=next((i for i,(a,b)in enumerate(zip(r.stdout,expected))if a!=b),min(len(r.stdout),len(expected)));raise AssertionError((opt,r.returncode,len(r.stdout),len(expected),at,r.stdout[max(0,at-12):at+20].hex(),expected[max(0,at-12):at+20].hex(),r.stderr))
  assert r.returncode==0 and not r.stderr,(opt,r.returncode,r.stderr);report[opt]=dict(cases=n,exact_public_and_call_bytes=len(expected),strict_aliasing=True,UBSan=True,SDK32=True)
 result=dict(profiles=report,guest_only_large_table_and_argument_home_cases_excluded=True,FCSR_or_hardware_qualified=False);(g.out/'native.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
