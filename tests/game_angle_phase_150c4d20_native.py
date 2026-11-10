"""Execute the semantic C using typed SDK32 records and effectful helpers."""
import json,struct,subprocess
from tools.tests import game_angle_phase_150c4d20_oracle as g
from tools.experiments import game_angle_phase_150c4d20_match as p
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def build():
 cs=[c for c in g.cases()if not c.alias and g.reference(g.fixture(c),c)[2]];expected=bytearray();rows=[]
 for i,c in enumerate(cs):
  m,calls,valid=g.reference(g.fixture(c),c);data=bytearray(m[g.RECORD+j]for j in range(160))
  for j in(0,0x60):struct.pack_into('>I',data,j,g.canonical(g.read(m,g.RECORD+j)))
  expected.extend(struct.pack('>I',i)+data)
  for name in('D_800BE9E4','D_800A03F0','D_800A03F4','D_800A03F8'):expected.extend(struct.pack('>I',g.read(m,g.symbols()[name])))
  expected.extend(struct.pack('>I',len(calls)))
  for t,args in calls:expected.extend(struct.pack('>II',t,len(args))+b''.join(struct.pack('>I',v)for v in args))
  rows.append('{'+','.join('0x%Xu'%g.u32(v)for v in(c.angle,c.velocity,c.timer,c.ticks,c.flags,*c.coords,c.result,c.mutation,c.seed))+'}')
 code=r'''
#include <ultra64.h>
TYPE
_Static_assert(sizeof(void*)==4,"SDK32");
_Static_assert(sizeof(AnglePhaseRecord)==0x80,"known prefix");
_Static_assert(__builtin_offsetof(AnglePhaseRecord,x)==0x10,"position");
_Static_assert(__builtin_offsetof(AnglePhaseRecord,flags)==0x4F,"flags");
_Static_assert(__builtin_offsetof(AnglePhaseRecord,angular_velocity)==0x60,"velocity");
_Static_assert(__builtin_offsetof(AnglePhaseRecord,phase)==0x7C,"phase");
static struct {AnglePhaseRecord state;u8 rest[0x20];} storage;
s32 D_800BE9E4;
f32 D_800A03F0,D_800A03F4,D_800A03F8;
static const u32*c;
static u8 logdata[64],output[184];static u32 used,count;
static f32 real(u32 v){union{u32 u;f32 f;}a;a.u=v;return a.f;}
static u32 bits32(f32 v){union{u32 u;f32 f;}a;a.f=v;return a.u;}
static u32 canonical32(u32 v){return(v&0x7F800000)==0x7F800000&&(v&0x7FFFFF)?0x7FC00000:v;}
static void be(u8*p,u32 v){p[0]=(u8)(v>>24);p[1]=(u8)(v>>16);p[2]=(u8)(v>>8);p[3]=(u8)v;}
static void effect(u32 t){if(c[9]&1){storage.state.angle=t==0x10010F88?-90.f:400.f;storage.state.angular_velocity=123.f;storage.state.phase=0x12345678;storage.state.flags^=4;}if(c[9]&2){D_800BE9E4=123;D_800A03F0=.02f;D_800A03F4=.25f;D_800A03F8=.5f;}}
static void call(u32 t,u32 n,const u32*a){u32 i;if(used+8+4*n>64)__builtin_trap();be(logdata+used,t);be(logdata+used+4,n);used+=8;for(i=0;i<n;i++){be(logdata+used,a[i]);used+=4;}count++;effect(t);}
u16 func_10010F88(s32 a,u16 b,s16 d,u8 e,s32 f,s16 x,s16 y,s16 z,s16 h,s16 k){u32 values[10]={(u32)a,b,(u32)d,e,(u32)f,(u32)x,(u32)y,(u32)z,(u32)h,(u32)k};call(0x10010F88,10,values);return 0xF00D;}
f32 func_15048A40(u8 a){u32 v=a;call(0x15048A40,1,&v);return real(c[8]);}
BODY
static const u32 cases[][11]={ROWS};
static int flush(const u8*p,u32 n){u32 done=0;while(done<n){s32 a;__asm__ volatile("int $0x80":"=a"(a):"0"(4),"b"(1),"c"(p+done),"d"(n-done):"memory");if(a<=0)return 1;done+=(u32)a;}return 0;}
static int run(void){u32 i,j;u8*data=(u8*)&storage;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  c=cases[i];used=count=0;for(j=0;j<160;j++)data[j]=(u8)(j*29+c[10]*11+90);
  storage.state.angle=real(c[0]);storage.state.angular_velocity=real(c[1]);storage.state.phase=(s32)c[2];storage.state.flags=(u8)c[4];storage.state.x=(s16)c[5];storage.state.y=(s16)c[6];storage.state.z=(s16)c[7];
  D_800BE9E4=(s32)c[3];D_800A03F0=.009f;D_800A03F4=.1f;D_800A03F8=.8f;
  func_150C4D20(&storage.state);
  be(output,i);for(j=0;j<160;j++)output[4+j]=data[j];be(output+4,canonical32(bits32(storage.state.angle)));be(output+4+0x60,canonical32(bits32(storage.state.angular_velocity)));be(output+4+0x7C,(u32)storage.state.phase);
  output[4+0x10]=(u8)((u16)storage.state.x>>8);output[4+0x11]=(u8)storage.state.x;output[4+0x12]=(u8)((u16)storage.state.y>>8);output[4+0x13]=(u8)storage.state.y;output[4+0x14]=(u8)((u16)storage.state.z>>8);output[4+0x15]=(u8)storage.state.z;
  be(output+164,(u32)D_800BE9E4);be(output+168,bits32(D_800A03F0));be(output+172,bits32(D_800A03F4));be(output+176,bits32(D_800A03F8));be(output+180,count);
  if(flush(output,184)||flush(logdata,used))return 1;
 }return 0;
}
'''.replace('TYPE','typedef'+p.DECLS.split('typedef',1)[1]).replace('BODY',(g.out/'selected-body.c').read_text(encoding='utf-8')).replace('ROWS',',\n'.join(rows))
 return code+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),bytes(expected),len(cs)
def main():
 code,expected,n=build();path=g.out/'native.c';path.write_text(code);results={}
 for opt in('-O0','-O2','-O3'):
  exe=g.out/('native'+opt);r=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=g.root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60)
  if r.stdout!=expected:
   at=next((i for i,(a,b)in enumerate(zip(r.stdout,expected))if a!=b),min(len(r.stdout),len(expected)));raise AssertionError((opt,r.returncode,len(r.stdout),len(expected),at,r.stdout[max(0,at-12):at+20].hex(),expected[max(0,at-12):at+20].hex(),r.stderr))
  assert r.returncode==0 and not r.stderr,(opt,r.returncode,r.stderr);results[opt]=dict(cases=n,exact_public_and_call_bytes=len(expected),UBSan=True,SDK32=True,typed_records=True,strict_aliasing=True)
 result=dict(profiles=results,NaNs_canonicalized=True,invalid_float_to_s32_and_global_aliases_guest_only=True);(g.out/'native.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
