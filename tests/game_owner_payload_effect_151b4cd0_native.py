"""Native SDK32 descriptor fields; padding and physical homes stay guest-only."""
import json,struct,subprocess
from tools.tests import game_owner_payload_effect_151b4cd0_oracle as g
from tools.experiments import game_owner_payload_effect_151b4cd0_match as p
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def build():
 cs=[c for c in g.cases()if not c.mutation&56 and c.alias<2];expected=bytearray();rows=[]
 for i,c in enumerate(cs):
  m,calls,answer,packets,copies=g.reference(g.fixture(c),c);expected.extend(struct.pack('>I',i)+bytes(m[g.OWNER+j]for j in range(0x340))+bytes(m[g.OUTPUT+j]for j in range(160)))
  expected.extend(struct.pack('>I',g.read(m,g.symbols()['D_800AA3D0']))+bytes(m[g.symbols()['D_800A3FE6']+j]for j in range(320))+struct.pack('>II',answer,len(calls)))
  packet=bytearray(packets[0]if packets else bytes(48))
  for at in g.PADDING:packet[at]=0
  expected.extend(packet)
  for t,args in calls:expected.extend(struct.pack('>II',t,len(args))+b''.join(struct.pack('>I',v)for v in args))
  rows.append('{'+','.join('0x%Xu'%g.u32(v)for v in(bool(c.owner),c.kind,c.class_byte,c.identity,c.selector,c.category,c.random,c.scale,c.outcome,c.mutation,c.after,c.alias,c.phase,c.seed))+'}')
 code=r'''
#include <ultra64.h>
TYPE
_Static_assert(sizeof(void*)==4,"SDK32");_Static_assert(sizeof(OwnerEffectDescriptor1E2180)==48,"descriptor");_Static_assert(__builtin_offsetof(OwnerEffectDescriptor1E2180,ownerIdentity)==8,"identity");_Static_assert(__builtin_offsetof(OwnerEffectDescriptor1E2180,owner)==12,"owner");_Static_assert(__builtin_offsetof(OwnerEffectDescriptor1E2180,attachment)==16,"attachment");_Static_assert(__builtin_offsetof(OwnerEffectDescriptor1E2180,vector)==20,"vector");_Static_assert(__builtin_offsetof(OwnerEffectDescriptor1E2180,duration)==40,"duration");_Static_assert(__builtin_offsetof(OwnerEffectDescriptor1E2180,mode)==45,"mode");
static u8 owner[0x340],result[160],packet[48],output[1376],logdata[160];
u8 D_800A3FE6[320];f32 D_800AA3D0;
static const u32*c;static u32 used,count;
static void setfloat(f32*p,u32 v){u8*a=(u8*)p;a[0]=(u8)v;a[1]=(u8)(v>>8);a[2]=(u8)(v>>16);a[3]=(u8)(v>>24);}
static u32 bits32(f32 v){union{u32 u;f32 f;}a;a.f=v;return a.u;}
static void be(u8*p,u32 v){p[0]=(u8)(v>>24);p[1]=(u8)(v>>16);p[2]=(u8)(v>>8);p[3]=(u8)v;}
static u32 logical(const void*p){if(!p)return 0;if(p==owner)return 0x30000;if(p==result)return 0x50000;if(p==owner+0x58)return 0x30058;if(p==result+0x58)return 0x50058;__builtin_trap();}
static void call(u32 t,u32 n,const u32*a){u32 i;if(used+8+4*n>160)__builtin_trap();be(logdata+used,t);be(logdata+used+4,n);used+=8;for(i=0;i<n;i++){be(logdata+used,a[i]);used+=4;}count++;}
s32 func_15134070(u8*p){u32 v=logical(p);call(0x15134070,1,&v);if(c[9]&1){if(c[1]!=99)D_800A3FE6[c[1]*16]=(u8)c[10];owner[0x3B]=(u8)(c[3]^0x33);}return(s32)c[1];}
void func_1516962C(s32 kind,void*p,u8 state){u32 v[3]={(u32)kind,logical(p),state};call(0x1516962C,3,v);if(c[9]&2){owner[0x3B]^=0x66;setfloat(&D_800AA3D0,0x7FC12345);}}
s32 func_150ADA20(void){call(0x150ADA20,0,0);if(c[9]&4){D_800A3FE6[c[1]*16]=(u8)c[10];D_800AA3D0=2.f;owner[0x3B]=0xEE;}return(s32)c[6];}
void*func_1513418C(void*p,s32 bytes,u8 selector,s32 category){OwnerEffectDescriptor1E2180*d=p;u32 i,v[4]={0x90000+c[12]-52,(u32)bytes,selector,(u32)category};u8*a=p;call(0x1513418C,4,v);
 for(i=0;i<48;i++)packet[i]=0;
 for(i=0;i<48;i++)if(!(i>=9&&i<12)&&!(i>=17&&i<20)&&i<46)packet[i]=a[i];
 be(packet,d->zero0);be(packet+4,d->zero4);be(packet+12,logical(d->owner));for(i=0;i<3;i++)be(packet+20+4*i,bits32(d->vector[i]));be(packet+32,bits32(d->value20));be(packet+36,bits32(d->value24));packet[40]=(u8)((u16)d->duration>>8);packet[41]=(u8)d->duration;
 return c[8]?(c[11]?owner:result):0;
}
void*memcpy(void*d,const void*s,u32 n){u32 i,v[3]={logical(d),0x90000+c[12]-56,n};u8*dst=d;const u8*src=s;call(0x10022EC0,3,v);for(i=0;i<n;i++)dst[i]=src[i];return d;}
BODY
static const u32 cases[][14]={ROWS};
static int flush(const u8*p,u32 n){u32 done=0;while(done<n){s32 a;__asm__ volatile("int $0x80":"=a"(a):"0"(4),"b"(1),"c"(p+done),"d"(n-done):"memory");if(a<=0)return 1;done+=(u32)a;}return 0;}
static int run(void){u32 i,j,answer;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
 c=cases[i];used=count=0;for(j=0;j<0x340;j++)owner[j]=(u8)((j+16)*29+c[13]*11+90);for(j=0;j<160;j++)result[j]=(u8)((j+16)*29+c[13]*11+90);for(j=0;j<320;j++)D_800A3FE6[j]=(u8)((j+96)*29+c[13]*11+90);for(j=0;j<48;j++)packet[j]=0;
 owner[0]=0;owner[1]=0;owner[2]=0;owner[3]=1;owner[4]=(u8)c[3];owner[0x3B]=(u8)c[3];for(j=0;j<4;j++)owner[0x1D4+j]=0;owner[0x74]=15;setfloat(&D_800AA3D0,c[7]);if(c[1]!=99)D_800A3FE6[c[1]*16]=(u8)c[2];
 answer=logical(func_151B4CD0(c[0]?owner:0,(u8)c[4],(s32)c[5]));be(output,i);for(j=0;j<0x340;j++)output[4+j]=owner[j];for(j=0;j<160;j++)output[836+j]=result[j];be(output+996,bits32(D_800AA3D0));for(j=0;j<320;j++)output[1000+j]=D_800A3FE6[j];be(output+1320,answer);be(output+1324,count);for(j=0;j<48;j++)output[1328+j]=packet[j];
 if(flush(output,1376)||flush(logdata,used))return 1;
 }return 0;}
'''.replace('TYPE','typedef'+p.DECLS.split('typedef',1)[1]).replace('BODY',(g.out/'selected-body.c').read_text(encoding='utf-8')).replace('ROWS',',\n'.join(rows)).replace('0x90000',hex(g.STACK))
 return code+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),bytes(expected),len(cs)
def main():
 code,expected,n=build();path=g.out/'native.c';path.write_text(code);profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=g.out/('native'+opt);r=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=g.root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60)
  if r.stdout!=expected:
   at=next((i for i,(a,b)in enumerate(zip(r.stdout,expected))if a!=b),min(len(r.stdout),len(expected)));raise AssertionError((opt,r.returncode,len(r.stdout),len(expected),at,r.stdout[max(0,at-12):at+20].hex(),expected[max(0,at-12):at+20].hex(),r.stderr))
  assert r.returncode==0 and not r.stderr,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases=n,exact_public_and_defined_packet_call_bytes=len(expected),UBSan=True,SDK32=True,typed_records=True,strict_aliasing=True)
 report=dict(profiles=profiles,padding_not_read_or_asserted=True,physical_homes_and_private_payload_mutations_guest_only=True,private_stack_addresses_normalized_in_native_logs=True);(g.out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
