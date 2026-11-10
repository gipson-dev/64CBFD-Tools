"""Execute action side effects; discard every fall-through C result explicitly."""
import json,struct,subprocess
from tools.tests import game_event_dispatch_1509d780_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def build():
 cs=[c for c in g.cases()if c.packet_mode<2];expected=bytearray();rows=[]
 for i,c in enumerate(cs):
  m,calls,value=g.reference(g.fixture(c),c);defined=g.u32(c.command)==9 and not c.found
  expected.extend(struct.pack('<I',i)+struct.pack('>I',0 if defined else 0xDEADBEEF))
  expected.extend(bytes(m[g.PACKET+j]for j in range(16))+bytes(m[g.ACTOR+j]for j in range(32))+bytes(m[g.FLAG-8+j]for j in range(24))+bytes(m[g.MARK+j]for j in range(32)))
  for target,args in calls:expected.extend(struct.pack('>II',target,len(args))+b''.join(struct.pack('>I',v)for v in args))
  rows.append('{'+','.join('0x%Xu'%g.u32(v)for v in(c.command,c.word,c.half,c.byte,c.found,c.result,c.incoming,c.mutation,c.packet_mode,c.phase,c.seed))+'}')
 source=r'''
#include <ultra64.h>
struct struct127;
_Static_assert(sizeof(void*)==4,"SDK32");
static union {u32 align;u8 bytes[16];} packet_store;
static union {u32 align;u8 bytes[24];} flag_store;
#define D_800D9920 flag_store.bytes[8]
static u32 actor_store[8],mark[8],count;
static u8 calls[40],record[112];
static const u32*c;
static u8*packet;
static void be(u8*p,u32 v){p[0]=(u8)(v>>24);p[1]=(u8)(v>>16);p[2]=(u8)(v>>8);p[3]=(u8)v;}
static u32 getbe(const u8*p){return((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
static u32 cb(u32 target,u32 n,u32 a,u32 b,u32 d){u32 values[3],i;values[0]=a;values[1]=b;values[2]=d;if(count+8+4*n>40)__builtin_trap();be(calls+count,target);be(calls+count+4,n);count+=8;for(i=0;i<n;i++){be(calls+count,values[i]);count+=4;}
 mark[0]++;mark[1]=target;mark[2]=n?a:0;
 if((c[7]&1)&&packet)packet[0]^=0x55;if(c[7]&2)D_800D9920=0xAB;if(c[7]&4)actor_store[1]^=0x12345678;
 return c[5]+mark[0]*0x10203u;
}
static s32 func_150EB8C4(void){return(s32)cb(0x150EB8C4,0,0,0,0);}
static void func_150F9720(u8 a){cb(0x150F9720,1,a,0,0);}
static void func_151616D0(u8 a,u8 b,s32 d){cb(0x151616D0,3,a,b,(u32)d);}
static struct struct127*func_1505EEF4(s32 key){cb(0x1505EEF4,1,(u32)key,0,0);return c[4]?(struct struct127*)actor_store:0;}
static s32 func_150F6DB0(u8*a){if(a!=(u8*)actor_store)__builtin_trap();return(s32)cb(0x150F6DB0,1,0x50000,0,0);}
static void func_151CD394(s32 a){cb(0x151CD394,1,(u32)a,0,0);}
static void func_150E35DC(s32 a){cb(0x150E35DC,1,(u32)a,0,0);}
static void func_150B3DD0(void){cb(0x150B3DD0,0,0,0,0);}
static s32 func_150C5C9C(s32 a){if((u32)a!=(u32)actor_store)__builtin_trap();return(s32)cb(0x150C5C9C,1,0x50000,0,0);}
static void func_150C522C(void){cb(0x150C522C,0,0,0,0);}
static void func_151D2718(s32 a){cb(0x151D2718,1,(u32)a,0,0);}
BODY
static const u32 cases[][11]={ROWS};
static int flush(const u8*p,u32 size){u32 done=0;while(done<size){s32 n;__asm__ volatile("int $0x80":"=a"(n):"0"(4),"b"(1),"c"(p+done),"d"(size-done):"memory");if(n<=0)return 1;done+=(u32)n;}return 0;}
static int run(void){u32 i,j,value;u8*p;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  c=cases[i];packet=c[8]?0:packet_store.bytes;count=0;for(j=0;j<8;j++)mark[j]=0;
  for(j=0;j<16;j++)packet_store.bytes[j]=(u8)(j*29+c[10]*11+90);
  p=(u8*)actor_store;for(j=0;j<32;j++)p[j]=(u8)(j*29+c[10]*11+90);actor_store[1]=getbe(p+4);
  for(j=0;j<24;j++)flag_store.bytes[j]=(u8)(j*29+c[10]*11+90);
  if(packet){be(packet+4,c[1]);if(c[0]==9||c[0]==18||c[0]==36)*(u32*)(packet+4)=c[1];if(c[0]==19)*(s16*)(packet+6)=(s16)c[2];if(c[0]==39)packet[7]=(u8)c[3];}
  value=0xDEADBEEF;if(c[0]==9&&!c[4])value=(u32)func_1509D780((s32)c[0],packet);else(void)func_1509D780((s32)c[0],packet);
  record[0]=(u8)i;record[1]=(u8)(i>>8);record[2]=(u8)(i>>16);record[3]=(u8)(i>>24);be(record+4,value);
  for(j=0;j<16;j++)record[8+j]=packet_store.bytes[j];
  if(packet){if(c[0]==9||c[0]==18||c[0]==36)be(record+12,*(u32*)(packet+4));if(c[0]==19){record[14]=(u8)((u16)*(s16*)(packet+6)>>8);record[15]=(u8)*(s16*)(packet+6);}}
  p=(u8*)actor_store;for(j=0;j<32;j++)record[24+j]=p[j];be(record+28,actor_store[1]);
  for(j=0;j<24;j++)record[56+j]=flag_store.bytes[j];for(j=0;j<8;j++)be(record+80+4*j,mark[j]);if(flush(record,112)||flush(calls,count))return 1;
 }return 0;
}
'''.replace('BODY',(g.out/'selected-body.c').read_text(encoding='utf-8')).replace('ROWS',',\n'.join(rows))
 return source+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),bytes(expected),len(cs)
def main():
 source,expected,n=build();path=g.out/'native.c';path.write_text(source);report={}
 for opt in('-O0','-O2','-O3'):
  exe=g.out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-Wno-return-type',str(path),'-o',str(exe)],cwd=g.root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60)
  if r.stdout!=expected:
   at=next((i for i,(a,b)in enumerate(zip(r.stdout,expected))if a!=b),min(len(r.stdout),len(expected)));raise AssertionError((opt,r.returncode,len(r.stdout),len(expected),at,r.stdout[max(0,at-12):at+20].hex(),expected[max(0,at-12):at+20].hex(),r.stderr))
  assert r.returncode==0 and not r.stderr,(opt,r.returncode,r.stderr);report[opt]=dict(cases=n,exact_public_and_call_bytes=len(expected),UBSan=True,SDK32=True,strict_aliasing=False,fallthrough_results_discarded=True,explicit_null_result_checked=True)
 result=dict(profiles=report,return_type_warning_disabled_for_deliberate_fallthrough=True,portable_C_fallthrough_results_qualified=False,guest_only_packet_alias_cases=True);(g.out/'native.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
