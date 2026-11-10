"""SDK32 native source, exact output and actual C recursion under UBSan."""
import dataclasses,json,struct,subprocess
from tools.tests import game_actor_state_dispatch_1506045c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_remaining_donor_candidates import body
def payload(m):
 return b''.join(bytes(m[a+i]for i in range(n))for a,n in[(g.ACTOR,812),(g.A,512),(g.B,512),(g.MARK,32),(g.CONTROL,8)])+bytes(m[g.TABLE+i*812]for i in range(256))+bytes([m[g.DISABLED]])+b''.join(bytes(m[a+i]for i in range(4))for a in(g.TICKS,g.MODE,g.CONTROL_PTR))
def record(i,calls,data):
 calls=[c for c in calls if c[0]!=g.ENTRY];v=[i,len(calls)]
 for t,a in calls:v.extend((t,len(a),*a))
 return struct.pack('<%dI'%len(v),*[x&0xFFFFFFFF for x in v])+struct.pack('<I',len(data))+data
def build():
 cs=[c for c in g.cases()if c.identity<=26];expected=bytearray();rows=[];fields=[f.name for f in dataclasses.fields(g.Case)];ix={n:i for i,n in enumerate(fields)}
 for i,c in enumerate(cs):
  m,calls=g.reference(g.fixture(c),c);expected.extend(record(i,calls,payload(m)));rows.append('{'+','.join('0x%Xu'%g.u32(getattr(c,f))for f in fields)+'}')
 pre=r'''
#include <ultra64.h>
#include "structs.h"
u8 D_800C35EA;
s32 D_800BE9E4,D_800BE9F0,D_800CC284;
u8 D_800CBFA8[256*812+1];
static struct127 actor;
static union { u32 align; u8 bytes[512]; } state_a,state_b;
static union { u32 align; u8 bytes[32]; } marker;
static union { u32 align; u8 bytes[8]; } controller;
static const u32 *c;
static u32 ncalls,targets[16],lengths[16],calls[16][9],used;
static u8 output[16384];
static u32 bits(f32 f){union { f32 f; u32 u; }v;v.f=f;return v.u;}
static f32 real(u32 u){union { f32 f; u32 u; }v;v.u=u;return v.f;}
static void bytes(const u8*p,u32 n){u32 i;for(i=0;i<n;i++)output[used++]=p[i];}
static void word(u32 x){u8 b[4];b[0]=(u8)x;b[1]=(u8)(x>>8);b[2]=(u8)(x>>16);b[3]=(u8)(x>>24);bytes(b,4);}
static void be(u8*p,u32 n,u32 x){while(n){p[--n]=(u8)x;x>>=8;}}
static void logcall(u32 target,u32 n,const u32*a){u32 i;targets[ncalls]=target;lengths[ncalls]=n;for(i=0;i<n;i++)calls[ncalls][i]=a[i];ncalls++;}
static u8*current(void){return(u8*)actor.unk31C;}
static void swap(void){actor.unk31C=(struct126*)(current()==state_a.bytes?state_b.bytes:state_a.bytes);}
s32 func_15080738(s32 command){u32 args[]={(u32)command};logcall(0x15080738,1,args);marker.align++;
 if(c[MUT]&1){actor.unk31C=(struct126*)state_b.bytes;state_b.bytes[0x75]=0x91;state_b.bytes[0x78]=0x2A;state_b.bytes[0x7C]=7;}
 if(c[MUT]&2){actor.stunned=1;actor.unk137=1;actor.unk65=1;D_800BE9F0=0x2E;}return(s32)c[QUERY];}
s32 func_15065A5C(struct127*a,u32 buttons,u32 flags,f32 height,s32 secondary,s32 command,s32 stunned,s32 expired,s32 force){
 u32 args[]={0x30000,buttons,flags,bits(height),(u32)secondary,(u32)command,(u32)stunned,(u32)expired,(u32)force};logcall(0x15065A5C,9,args);marker.align++;
 if(c[MUT]&4){swap();current()[0x7B]=1;}if(c[MUT]&8){actor.stunned=1;current()[0x75]^=0x55;current()[0x78]=0x8A;}return(s32)(c[RESULT]^marker.align);}
s32 func_150642AC(struct127*a,u32 flags,f32 height,s32 force,s32 result){u32 args[]={0x30000,flags,bits(height),(u32)force,(u32)result};logcall(0x150642AC,5,args);marker.align++;
 if(c[MUT]&16){swap();current()[0x75]^=0xAA;current()[0x7C]=0x81;}return(s32)0xDEADBEEFu;}
'''.replace('MUT',str(ix['mutation'])).replace('QUERY',str(ix['query'])).replace('RESULT',str(ix['result']))
 candidate=body((g.out/'selected-source.c').read_text(),'func_1506045C')
 post=r'''
static const u32 cases[][FIELDS]={ROWS};
static void pattern(u8*p,u32 n,u32 seed){u32 i;for(i=0;i<n;i++)p[i]=(u8)(i*29+seed*11+90);}
static void snapshot(void){u8 b[812],s[512],v[4];u32 i,j;
 for(i=0;i<812;i++)b[i]=((u8*)&actor)[i];be(b+0x31C,4,current()==state_a.bytes?0x50000:0x51000);bytes(b,812);
 for(j=0;j<2;j++){u8*p=j?state_b.bytes:state_a.bytes;for(i=0;i<512;i++)s[i]=p[i];be(s+0x72,2,*(u16*)(p+0x72));bytes(s,512);}
 for(i=0;i<32;i++)b[i]=marker.bytes[i];be(b,4,marker.align);bytes(b,32);
 for(i=0;i<8;i++)b[i]=controller.bytes[i];be(b,2,*(u16*)controller.bytes);bytes(b,8);
 for(i=0;i<256;i++)bytes(D_800CBFA8+i*812,1);bytes(&D_800C35EA,1);
 be(v,4,(u32)D_800BE9E4);bytes(v,4);be(v,4,(u32)D_800BE9F0);bytes(v,4);be(v,4,0x71000);bytes(v,4);}
static int flush(void){u32 done=0;while(done<used){s32 n;__asm__ volatile("int $0x80":"=a"(n):"0"(4),"b"(1),"c"(output+done),"d"(used-done):"memory");if(n<=0)return 1;done+=(u32)n;}return 0;}
static int run(void){u32 i,j,k,seed;u8*p;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  c=cases[i];seed=c[SEED];pattern((u8*)&actor,812,seed);pattern(state_a.bytes,512,seed);pattern(state_b.bytes,512,seed);pattern(marker.bytes,32,seed);pattern(controller.bytes,8,seed);
  actor.unk31C=(struct126*)state_a.bytes;actor.unk65=(u8)c[IDENTITY];actor.stunned=(u8)c[STUNNED];actor.unk137=(u8)c[BUSY];actor.unk13C=(u8)c[FORCE];
  for(j=0;j<2;j++){p=j?state_b.bytes:state_a.bytes;*(u16*)(p+0x72)=(u16)c[TIMER];p[0x75]=(u8)c[COMMAND];p[0x78]=(u8)c[OVERLAY];p[0x7C]=(u8)c[FALLBACK];p[0x17]=(u8)c[FORCE_COMMAND];p[0x4E]=(u8)c[BLOCKED];p[0x7B]=(u8)c[EXTRA];}
  marker.align=0;D_800C35EA=(u8)c[DISABLED];D_800BE9E4=(s32)c[TICKS];D_800BE9F0=(s32)c[MODE];D_800CC284=(s32)controller.bytes;*(u16*)controller.bytes=(u16)c[CONTROLS];
  for(j=0;j<256;j++)D_800CBFA8[j*812]=(u8)c[CATEGORY];used=ncalls=0;
  func_1506045C(&actor,c[BUTTONS],c[FLAGS],real(c[HEIGHT]),(s32)c[SECONDARY]);word(i);word(ncalls);
  for(j=0;j<ncalls;j++){word(targets[j]);word(lengths[j]);for(k=0;k<lengths[j];k++)word(calls[j][k]);}
  word(2145);snapshot();if(flush())return 1;
 }return 0;}
'''
 for key,name in [('SEED','seed'),('IDENTITY','identity'),('STUNNED','stunned'),('BUSY','actor_busy'),('FORCE','actor_force'),('TIMER','timer'),('COMMAND','command'),('OVERLAY','overlay'),('FALLBACK','fallback'),('FORCE_COMMAND','force_command'),('BLOCKED','blocked'),('EXTRA','extra'),('DISABLED','disabled'),('TICKS','ticks'),('MODE','mode'),('CONTROLS','controls'),('CATEGORY','category'),('BUTTONS','buttons'),('FLAGS','flags'),('HEIGHT','height'),('SECONDARY','secondary')]:
  import re
  post=re.sub(r'\b'+key+r'\b',str(ix[name]),post)
 post=post.replace('FIELDS',str(len(fields))).replace('ROWS',',\n'.join(rows))
 return pre+'\n'+candidate+'\n'+post+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),bytes(expected),len(cs)
def main():
 source,expected,n=build();path=g.out/'native.c';path.write_text(source);report={}
 for opt in('-O0','-O2','-O3'):
  exe=g.out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(path),'-o',str(exe)],cwd=g.root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60)
  if r.stdout!=expected:
   at=next((i for i,(a,b)in enumerate(zip(r.stdout,expected))if a!=b),min(len(r.stdout),len(expected)));raise AssertionError((opt,r.returncode,len(r.stdout),len(expected),at,r.stdout[max(0,at-16):at+32].hex(),expected[max(0,at-16):at+32].hex(),r.stderr))
  assert r.returncode==0 and not r.stderr,(opt,r.returncode,r.stderr)
  report[opt]=dict(cases=n,exact_output_bytes=len(expected),UBSan=True,actual_C_recursion=True,SDK32=True,strict_aliasing_disabled=True)
 result=dict(profiles=report,guest_extended_indices_excluded=3384-n,opaque_helper_algorithms_not_qualified=True)
 (g.out/'native.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
