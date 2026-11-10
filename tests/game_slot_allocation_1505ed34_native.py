"""Run the actual pointer-return C body with SDK32 and canonical record output."""
import json,struct,subprocess
from tools.tests import game_slot_allocation_1505ed34_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def build():
 cs=[c for c in g.cases()if not c.sparse];expected=bytearray();rows=[]
 for i,c in enumerate(cs):
  m,calls,result=g.reference(g.fixture(c),c);chosen=(result-g.TABLE)//812
  expected.extend(struct.pack('<I',i)+struct.pack('>II',chosen,len(calls)))
  expected.extend(bytes(m[g.TABLE+j]for j in range(26*812)))
  expected.extend(bytes(m[g.MARK+j]for j in range(32)))
  for target,args in calls:expected.extend(bytes((1 if target==g.CLEAN else 2,(args[0]-g.TABLE)//812)))
  rows.append('{'+','.join('0x%Xu'%g.u32(v)for v in(c.empty,c.clear,c.recycle,c.pattern,c.reserved,c.mutation,c.seed))+'}')
 source=r'''
#include <ultra64.h>
#include "structs.h"
_Static_assert(sizeof(void*)==4,"SDK32");
_Static_assert(sizeof(struct127)==812,"actor stride");
_Static_assert(__builtin_offsetof(struct127,interaction_state)==0,"state");
_Static_assert(__builtin_offsetof(struct127,unk1D4)==0x1D4,"transform");
struct127 D_800CC2D0[26];
static u8 transforms[26][64],mark[32],record[12+26*812+32],calls[4];
static u32 call_count;
static const u32*c;
static void be(u8*p,u32 v){p[0]=(u8)(v>>24);p[1]=(u8)(v>>16);p[2]=(u8)(v>>8);p[3]=(u8)v;}
static u32 getbe(const u8*p){return((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
static u32 slot(struct127*a){s32 i=a-D_800CC2D0;if(i<0||i>=26)__builtin_trap();return(u32)i;}
static void logcall(u8 kind,u32 index){if(call_count>=2)__builtin_trap();calls[2*call_count]=kind;calls[2*call_count+1]=(u8)index;call_count++;}
static __attribute__((noinline)) void func_15060F28(struct127*a,s32 unused){u32 i=slot(a);if(unused)__builtin_trap();logcall(1,i);be(mark,getbe(mark)+1);be((u8*)a+0x50,0xC1EA0000|i);
 if(c[5]&1)a->interaction_state=0;if(c[5]&2)D_800CC2D0[(i+1)%26].interaction_state=0;if(c[5]&4)a->unk1D4=0;
}
static __attribute__((noinline)) void func_1505F188(struct127*a){u32 i=slot(a);logcall(2,i);be(mark+4,getbe(mark+4)+1);be((u8*)a+0x54,0x1A170000|i);
 if(c[5]&8)a->interaction_state=0x2468ACE0;if(c[5]&16)D_800CC2D0[0].interaction_state=-1;
}
BODY
static const u32 cases[][7]={ROWS};
static int flush(const u8*p,u32 size){u32 done=0;while(done<size){s32 n;__asm__ volatile("int $0x80":"=a"(n):"0"(4),"b"(1),"c"(p+done),"d"(size-done):"memory");if(n<=0)return 1;done+=(u32)n;}return 0;}
static int run(void){u32 i,j,k,v;u8*p;struct127*result;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  c=cases[i];p=(u8*)D_800CC2D0;for(j=0;j<26*812;j++)p[j]=(u8)((j+16)*29+c[6]*11+90);
  for(j=0;j<32;j++)mark[j]=(u8)(j*29+c[6]*11+90);be(mark,0);be(mark+4,0);call_count=0;
  for(j=0;j<26;j++){D_800CC2D0[j].interaction_state=(s32)c[3];D_800CC2D0[j].unk1D4=(struct255*)transforms[j];}
  D_800CC2D0[25].interaction_state=(s32)c[4];
  if((s32)c[2]>=0)D_800CC2D0[c[2]].interaction_state=39;
  if((s32)c[1]>=0){D_800CC2D0[c[1]].interaction_state=39;D_800CC2D0[c[1]].unk1D4=0;}
  if((s32)c[0]>=0)D_800CC2D0[c[0]].interaction_state=0;
  result=(struct127 *)func_1505ED34();record[0]=(u8)i;record[1]=(u8)(i>>8);record[2]=(u8)(i>>16);record[3]=(u8)(i>>24);be(record+4,slot(result));be(record+8,call_count);
  p=(u8*)D_800CC2D0;for(j=0;j<26*812;j++)record[12+j]=p[j];
  for(j=0;j<26;j++){k=12+j*812;be(record+k,(u32)D_800CC2D0[j].interaction_state);v=D_800CC2D0[j].unk1D4==0?0:D_800CC2D0[j].unk1D4==(struct255*)transforms[j]?0x30000+64*j:0xDEADDEAD;be(record+k+0x1D4,v);}
  for(j=0;j<32;j++)record[12+26*812+j]=mark[j];if(flush(record,sizeof(record))||flush(calls,2*call_count))return 1;
 }return 0;
}
'''.replace('BODY',(g.out/'selected-body.c').read_text(encoding='utf-8')).replace('ROWS',',\n'.join(rows))
 return source+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),bytes(expected),len(cs)
def main():
 source,expected,n=build();path=g.out/'native.c';path.write_text(source);report={}
 for opt in('-O0','-O2','-O3'):
  exe=g.out/('native'+opt);r=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(path),'-o',str(exe)],cwd=g.root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60)
  if r.stdout!=expected:
   at=next((i for i,(a,b)in enumerate(zip(r.stdout,expected))if a!=b),min(len(r.stdout),len(expected)));raise AssertionError((opt,r.returncode,len(r.stdout),len(expected),at,r.stdout[max(0,at-12):at+20].hex(),expected[max(0,at-12):at+20].hex(),r.stderr))
  assert r.returncode==0 and not r.stderr,(opt,r.returncode,r.stderr);report[opt]=dict(cases=n,exact_public_and_call_bytes=len(expected),strict_aliasing=True,UBSan=True,SDK32=True)
 result=dict(profiles=report,sparse_unmapped_cases_guest_only=True,opaque_cleanup_and_initializer=True);(g.out/'native.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
