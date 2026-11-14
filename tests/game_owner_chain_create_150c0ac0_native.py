from pathlib import Path
import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
p=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=p/'conker/build/game-owner-chain-create-150c0ac0-screen';source=Path(__import__('os').environ.get('OWNER_CHAIN_SOURCE',out/'selected.c')).read_text();lo=source.index('u8 *func_150C0AC0(');hi=source.index('\n}\n',lo)+2;source=source[lo:hi].replace('memcpy(', 'test_copy(')
prefix=r'''#include <ultra64.h>
static u8 descriptor[64], resource[64], position[32], output[0x300],expected[0x300];
static s32 allocate_ok,mutation,failed,allocation_calls,copy_calls,expected_size;static u8 expected_slot;
void *func_15167A68(s32 a,s32 b,s32 c,s32 d,u8 e,u8 f){allocation_calls++;if(a!=0x25||b!=1||c!=expected_size||d!=1||e!=expected_slot||f!=1)failed=1;if(mutation&1)descriptor[0x18]^=2;if(mutation&2)*(s16 *)(descriptor+0x14)=3;return allocate_ok?output+0x40:0;}
void *test_copy(void *d,const void *s,u32 n){u8 *dst=d;const u8 *src=s;copy_calls++;if(n!=28)failed=1;for(u32 i=0;i<n;i++)dst[i]=src[i];return d;}
'''
harness=r'''
static int run(void){const s16 counts[]={-2,-1,0,1,3,5,20};s32 checked=0;
 for(int n=0;n<7;n++)for(int flag=0;flag<2;flag++)for(int res=0;res<3;res++)for(int ok=0;ok<2;ok++)for(int mut=0;mut<4;mut++)for(int slot=0;slot<2;slot++){
  if(flag&&res==0&&ok&&(mut&1))continue;
  for(int i=0;i<64;i++){descriptor[i]=0x53;resource[i]=0x53;}for(int i=0;i<32;i++)position[i]=0x53;for(int i=0;i<0x300;i++)output[i]=expected[i]=0x5a;
  *(u8 **)descriptor=position;*(u8 **)(descriptor+8)=res?resource:0;*(s16 *)(descriptor+0x14)=counts[n];descriptor[0x18]=flag?2:0;
  *(u32 *)resource=res==1?0x12345678:0;*(u32 *)(resource+0x14)=0x7fc12345;*(u32 *)(resource+0x1c)=0x80000000;*(u32 *)position=0x3f800000;*(u32 *)(position+8)=0xffc56789;
  allocate_ok=ok;mutation=mut;failed=allocation_calls=copy_calls=0;expected_slot=slot?0x80:0xff;expected_size=(s32)counts[n]*8+0x48;
  int should_alloc=flag||res==1;u8 model_desc[28];for(int i=0;i<28;i++)model_desc[i]=descriptor[i];
  if(should_alloc&&mut&1)model_desc[0x18]^=2;if(should_alloc&&mut&2)*(s16 *)(model_desc+0x14)=3;
  if(should_alloc&&ok){
   u8 *r=expected+0x40;for(int i=0;i<28;i++)r[0x18+i]=model_desc[i];*(u32 *)(r+0x40)=(u32)(output+0x40+0x48);
   if(model_desc[0x18]&2){*(u32 *)(r+0x34)=*(u32 *)position;*(u32 *)(r+0x38)=*(u32 *)(position+8);}
   else{*(u32 *)(r+0x34)=*(u32 *)(resource+0x14);*(u32 *)(r+0x38)=*(u32 *)(resource+0x1c);}
   *(u32 *)(r+0x3c)=0;*(s16 *)(r+0x44)=-1;*(s16 *)(r+0x46)=0;
   s16 count=*(s16 *)(model_desc+0x14);for(s16 i=0;i<count-1;i++)*(s16 *)(r+0x48+i*8+4)=i+1;*(s16 *)(r+0x48+count*8-4)=-1;*(u32 *)(r+0x10)=1;*(u32 *)(r+0x14)=0;
  }
  u8 *answer=func_150C0AC0(descriptor,expected_slot,1);
  if(failed||allocation_calls!=should_alloc||copy_calls!=(should_alloc&&ok)||answer!=(should_alloc&&ok?output+0x40:0))return 42;
  for(int i=0;i<0x300;i++)if(output[i]!=expected[i])return 42;checked++;
 }
 return checked==644?0:20;
}
'''
(out/'native.c').write_text(prefix+source+harness+START)
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  dest=out/('native'+opt+alias);cmd=native_command(opt)+['-mstackrealign',alias,'-o',str(dest),str(out/'native.c')];c=subprocess.run(cmd,capture_output=True,text=True);assert c.returncode==0,c.stderr
  r=subprocess.run([str(dest)],capture_output=True);print(opt,alias,'exit',r.returncode,flush=True);assert r.returncode==0
