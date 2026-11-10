"""Typed float aliases under native SDK32 and strict-aliasing optimization."""
import json,struct,subprocess
from tools.tests import game_paired_float_approach_1505a250_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_remaining_donor_candidates import body
def payload(m):
 output=bytearray(bytes(m[g.OUTPUT+i]for i in range(32)))
 for offset in(8,12):output[offset:offset+4]=struct.pack('>I',g.canonical(int.from_bytes(output[offset:offset+4],'big')))
 return bytes(output)+struct.pack('>II',g.canonical(g.read(m,g.TIMESTEP)),g.read(m,g.TIMESTEP+4))
def build():
 cases=[c for c in g.cases()if c.alias<4];expected=bytearray();rows=[]
 for i,c in enumerate(cases):
  result,_=g.reference(g.fixture(c),c);expected.extend(struct.pack('<I',i)+payload(result));rows.append('{'+','.join('0x%Xu'%v for v in(c.target_x,c.target_z,c.x,c.z,c.rate,c.timestep,c.alias,c.seed))+'}')
 source=r'''
#include <ultra64.h>
f32 D_800D1550[2];
static f32 output_values[8];
static u8 record[44];
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 canonical(u32 u){return((u&0x7F800000u)==0x7F800000u&&(u&0x7FFFFFu))?0x7FC00000u:u;}
f32 sqrtf(f32 x){__asm__ volatile("sqrtss %0,%0":"+x"(x));return x;}
f32 fabsf(f32 x){return real(bits(x)&0x7FFFFFFFu);}
'''+body((g.out/'selected-source.c').read_text(),'func_1505A250')+r'''
static const u32 cases[][8]={ROWS};
static void be(u8*p,u32 u){p[0]=(u8)(u>>24);p[1]=(u8)(u>>16);p[2]=(u8)(u>>8);p[3]=(u8)u;}
static int flush(void){u32 done=0;while(done<44){s32 n;__asm__ volatile("int $0x80":"=a"(n):"0"(4),"b"(1),"c"(record+done),"d"(44-done):"memory");if(n<=0)return 1;done+=(u32)n;}return 0;}
static int run(void){u32 i,j,k,v;f32*x,*z;const u32*c;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  c=cases[i];for(j=0;j<8;j++){v=0;for(k=0;k<4;k++)v=(v<<8)|(((j*4+k)*29+c[7]*11+90)&255);output_values[j]=real(v);}
  output_values[2]=real(c[2]);output_values[3]=real(c[3]);D_800D1550[0]=real(c[5]);D_800D1550[1]=real(0x2468ACE0);
  x=c[6]==2?&D_800D1550[0]:&output_values[2];z=c[6]==1?&output_values[2]:c[6]==3?&D_800D1550[0]:&output_values[3];
  func_1505A250(real(c[0]),real(c[1]),real(c[4]),x,z);
  record[0]=(u8)i;record[1]=(u8)(i>>8);record[2]=(u8)(i>>16);record[3]=(u8)(i>>24);
  for(j=0;j<8;j++){v=bits(output_values[j]);if(j==2||j==3)v=canonical(v);be(record+4+j*4,v);}be(record+36,canonical(bits(D_800D1550[0])));be(record+40,bits(D_800D1550[1]));if(flush())return 1;
 }return 0;}
'''.replace('ROWS',',\n'.join(rows))
 return source+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),bytes(expected),len(cases)
def main():
 source,expected,n=build();p=g.out/'native.c';p.write_text(source);report={}
 for opt in('-O0','-O2','-O3'):
  exe=g.out/('native'+opt);r=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],cwd=g.root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60)
  if r.stdout!=expected:
   at=next((i for i,(a,b)in enumerate(zip(r.stdout,expected))if a!=b),min(len(r.stdout),len(expected)));raise AssertionError((opt,r.returncode,len(r.stdout),len(expected),at,r.stdout[max(0,at-12):at+20].hex(),expected[max(0,at-12):at+20].hex(),r.stderr))
  assert r.returncode==0 and not r.stderr,(opt,r.returncode,r.stderr);report[opt]=dict(cases=n,exact_canonical_output_bytes=len(expected),strict_aliasing=True,UBSan=True,SDK32=True)
 result=dict(profiles=report,NaNs_canonicalized_by_class=True,parameter_home_aliases_guest_only=True,FCSR_or_hardware_qualified=False);(g.out/'native.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
