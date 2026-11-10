"""SDK32 native executions with exact canonical call and public-byte output."""
import json,struct,subprocess,sys
from pathlib import Path
import os
root=Path(os.environ.get("CBFD_CONSUMER_ROOT",Path(__file__).resolve().parents[2])).resolve();out=root/"conker/build/game-actor-audio-15060778-match"
from tools.tests import game_actor_audio_handle_15060778_oracle as game, game_sound_slot_10010be8_oracle as init, game_object_audio_10010ffc_oracle as caller
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def record(kind,index,result,calls,payload):
 v=[kind,index,result,len(calls)]
 for t,args in calls:v.extend((t,len(args),*args))
 v.append(len(payload));return struct.pack('<%dI'%len(v),*[x&0xFFFFFFFF for x in v])+payload

def source_and_expected():
 gs=game.cases();cs=init.cases();fs=caller.native_cases();expected=bytearray();grows=[];irows=[];frows=[]
 for i,c in enumerate(gs):
  m,calls,_=game.reference(game.fixture(c),c);payload=bytes(m[game.ACTOR+j]for j in range(812))+bytes(m[game.MARK+j]for j in range(32));expected+=record(0,i,0,calls,payload)
  grows.append([c.sound,c.volume,c.pitch,c.near,c.far,c.flags,c.handle1,c.handle2,c.material,c.actor_pitch,*c.coords,c.query,c.created,c.mutation,c.seed,int(bool(c.actor))])
 for i,c in enumerate(cs):
  m,calls,result=init.reference(init.fixture(c),c);payload=b''.join(bytes(m[p+j]for j in range(n))for p,n in ((init.TABLE,192),(init.BANK,4),(init.MIX,1),(init.VOICE,4096),(init.OTHER,256),(init.NEWVOICE,256),(init.MARK,32)));expected+=record(1,i,result,calls,payload)
  irows.append([c.handle,c.sound,c.volume,c.pan,c.cents,c.mix,c.bus,c.global_mix,c.occupied,c.active,c.reserved,int(c.matching),c.generation,c.mutation,c.seed])
 for i,c in enumerate(fs):
  m,calls,result=caller.reference(caller.fixture(c),c);payload=bytes(m[caller.ACTOR+j]for j in range(812))+bytes(m[caller.MARK+j]for j in range(32));expected+=record(2,i,result,calls,payload)
  frows.append([c.handle,c.sound,c.volume,c.pitch,c.effect,int(bool(c.actor)),c.state,c.camera,c.identity,c.height,c.scale,*c.coords,c.bus,c.created,c.seed])
 array=lambda rows:',\n'.join('{'+','.join('0x%08Xu'%(v&0xFFFFFFFF)for v in row)+'}'for row in rows)
 pgame=body((out/'public-audit/game-proposal.c').read_text(),'func_15060778').replace('void func_15060778(', 'void candidate_game(',1)
 pinit=body((out/'public-audit/init-proposal.c').read_text(),'func_10010BE8').replace('u16 func_10010BE8(', 'u16 candidate_allocate(',1)
 pcaller=body((out/'public-audit/init-proposal.c').read_text(),'func_10010FFC').replace('u16 func_10010FFC(', 'u16 candidate_caller(',1)
 pre=r'''
#include <ultra64.h>
#include "structs.h"
#include "variables.h"
u16 func_10010BE8(u16,s32,u16,u8,s16,u8,u8);
u16 func_10010E78(u16,s32,u16,s16,u8,s32,s16,s16,s16,s16,s16);
s32 func_1001147C(u16);
void func_1000F85C(u16,s16,s32);
void func_1000F91C(u16,u16,s16,u8,s32,s16,s16,s16,s16,s16);
s32 func_100173C4(struct31 **);
void func_10017594(struct31 *);
struct31 *func_10017438(void*,s16,u16,u8,f32,u8,u8,struct31 **);
struct120 D_800425E0[16];s32 D_8003E368;s8 D_80041FD8;u8 D_80041FD9;
struct124 *D_800D1C90[187];static struct124 descriptors[187];static u8 descriptor_before[187][44];
static struct127 actor;
typedef union{u32 align;u8 bytes[256];} Voice;
static Voice voices[16],other,newvoice;
static u8 mark[32],output[16384];static u32 used,ncalls,targets[64],lengths[64],calls[64][11];
static const u32 *g,*c;static u32 seed;
_Static_assert(sizeof(void*)==4,"SDK32");_Static_assert(sizeof(struct120)==12,"slot");_Static_assert(sizeof(struct127)==812,"actor");_Static_assert(sizeof(struct31)<=256,"voice");
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static void be(u8*p,u32 n,u32 v){u32 i;for(i=0;i<n;i++)p[n-1-i]=(u8)(v>>(8*i));}
static u32 frombe(const u8*p){return ((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
static void bump(void){be(mark,4,frombe(mark)+1);}
static void bytes(const u8*p,u32 n){u32 i;for(i=0;i<n;i++)output[used++]=p[i];}
static void word(u32 v){u32 i;for(i=0;i<4;i++)output[used++]=(u8)(v>>(8*i));}
static u32 ptr(const void*p){u32 v=(u32)p;
 if(v>=(u32)D_800425E0&&v<(u32)D_800425E0+192)return 0x800425E0u+v-(u32)D_800425E0;
 if(v>=(u32)voices&&v<(u32)voices+4096)return 0x90000u+v-(u32)voices;
 if(v>=(u32)&other&&v<(u32)&other+256)return 0xA1000u+v-(u32)&other;
 if(v>=(u32)&newvoice&&v<(u32)&newvoice+256)return 0xA2000u+v-(u32)&newvoice;return v;
}
static void logcall(u32 t,u32 n,const u32*a){u32 i;targets[ncalls]=t;lengths[ncalls]=n;for(i=0;i<n;i++)calls[ncalls][i]=a[i];ncalls++;bump();}
static void game_mutation(void){actor.unk8C=0xBEEF;actor.unk8E=0xCAFE;actor.unk184=0x80;actor.unk13F=255;actor.x_position=-32768.75f;actor.y_position=32767.75f;actor.z_position=-0.75f;}
s32 func_1001147C(u16 h){u32 a[]={h};logcall(0x1001147C,1,a);if(g[15])game_mutation();return(s32)g[13];}
void func_1000F85C(u16 h,s16 cmd,s32 val){u32 a[]={h,(u32)(s32)cmd,(u32)val};logcall(0x1000F85C,3,a);if(cmd==16&&g[15]){actor.unk184=0;actor.unk13F=1;}}
void func_1000F91C(u16 h,u16 vol,s16 pitch,u8 effect,s32 zero,s16 x,s16 y,s16 z,s16 near,s16 far){u32 a[]={h,vol,(u32)(s32)pitch,effect,(u32)zero,(u32)(s32)x,(u32)(s32)y,(u32)(s32)z,(u32)(s32)near,(u32)(s32)far};logcall(0x1000F91C,10,a);}
u16 func_10010BE8(u16 h,s32 sound,u16 vol,u8 pan,s16 pitch,u8 effect,u8 bus){u32 a[]={h,(u32)sound,vol,pan,(u32)(s32)pitch,effect,bus};logcall(0x10010BE8,7,a);return(u16)g[14];}
u16 func_10010E78(u16 h,s32 sound,u16 vol,s16 pitch,u8 effect,s32 zero,s16 x,s16 y,s16 z,s16 near,s16 far){u32 a[]={h,(u32)sound,vol,(u32)(s32)pitch,effect,(u32)zero,(u32)(s32)x,(u32)(s32)y,(u32)(s32)z,(u32)(s32)near,(u32)(s32)far};logcall(0x10010E78,11,a);return(u16)g[14];}
s32 func_100173C4(struct31 **p){u32 a[]={ptr(p)};u32 i=(u32)((u8*)p-(u8*)D_800425E0-8)/12;u32 result=(c[9]>>i)&1;logcall(0x100173C4,1,a);
 if(c[13]&1)D_800425E0[i].unk4^=0x8000;if(c[13]&2)*p=(struct31*)&other;if(c[13]&4)D_80041FD8=(s8)((u8)D_80041FD8^255);return(s32)result;}
void func_10017594(struct31*p){u32 a[]={ptr(p)};logcall(0x10017594,1,a);((u8*)p)[0x40]^=0x55;if(c[13]&8)D_80041FD8=(s8)((u8)D_80041FD8+1);}
f32 alCents2Ratio(s32 cents){u32 a[]={(u32)cents};logcall(0x10019AB0,1,a);if(c[13]&16){D_8003E368=0x71000;D_80041FD8=(s8)((u8)D_80041FD8^255);}return real(cents&1?0x3F123456u:0x3FA54321u);}
struct31*func_10017438(void*bank,s16 sound,u16 vol,u8 pan,f32 pitch,u8 mix,u8 bus,struct31**p){u32 a[]={(u32)bank,(u32)(s32)sound,vol,pan,bits(pitch),mix,bus,ptr(p)};logcall(0x10017438,8,a);*p=(struct31*)&newvoice;if(c[13]&16)*(u16*)((u8*)p-6)=0xDEAD;return(struct31*)&newvoice;}
'''
 post=r'''
static const u32 game_cases[][18]={GAME_ROWS};
static const u32 init_cases[][15]={INIT_ROWS};
static const u32 caller_cases[][17]={CALLER_ROWS};
static void pattern(u8*p,u32 n){u32 i;for(i=0;i<n;i++)p[i]=(u8)(i*29+seed*11+90);}
static void header(u32 kind,u32 index,u32 result){u32 i,j;word(kind);word(index);word(result);word(ncalls);for(i=0;i<ncalls;i++){word(targets[i]);word(lengths[i]);for(j=0;j<lengths[i];j++)word(calls[i][j]);}}
static int flush(void){u32 done=0;while(done<used){s32 n;__asm__ volatile("int $0x80":"=a"(n):"0"(4),"b"(1),"c"(output+done),"d"(used-done):"memory");if(n<=0)return 1;done+=(u32)n;}return 0;}
static void actor_bytes(u32 mode){u8 p[812];u32 i;for(i=0;i<812;i++)p[i]=((u8*)&actor)[i];be(p+0x8C,2,actor.unk8C);be(p+0x8E,2,actor.unk8E);be(p+0x184,4,actor.unk184);be(p+20,4,bits(actor.x_position));be(p+24,4,bits(actor.y_position));be(p+28,4,bits(actor.z_position));if(mode){be(p,4,(u32)actor.interaction_state);be(p+0x318,4,(u32)actor.camera);be(p+0x14C,4,bits(actor.xz_scale));}bytes(p,812);}
static int run(void){u32 i,j,k,result,temp[18];const u32*f;u8 p[12];
 for(i=0;i<sizeof(game_cases)/sizeof(game_cases[0]);i++){g=game_cases[i];seed=g[16];pattern((u8*)&actor,812);pattern(mark,32);actor.unk8C=(u16)g[6];actor.unk8E=(u16)g[7];actor.unk184=(s32)g[8];actor.unk13F=(u8)g[9];actor.x_position=real(g[10]);actor.y_position=real(g[11]);actor.z_position=real(g[12]);used=ncalls=0;
  candidate_game((s32)g[0],g[17]?&actor:NULL,(u16)g[1],(s32)g[2],(s32)g[3],(s32)g[4],(s32)g[5]);header(0,i,0);word(844);actor_bytes(0);bytes(mark,32);if(flush())return 1;
 }
 for(i=0;i<sizeof(init_cases)/sizeof(init_cases[0]);i++){c=init_cases[i];seed=c[14];pattern((u8*)voices,4096);pattern(other.bytes,256);pattern(newvoice.bytes,256);pattern(mark,32);
  for(j=0;j<16;j++){D_800425E0[j].unk0=(u16)(0x100+j);D_800425E0[j].unk2=(u16)(c[12]+j*16);D_800425E0[j].unk4=c[10]>>j&1?0x8000:0;D_800425E0[j].unk6=(u16)((((j*12+6)*29+seed*11+90)&255)<<8|(((j*12+7)*29+seed*11+90)&255));D_800425E0[j].unk8=c[8]>>j&1?(struct31*)&voices[j]:NULL;}
  D_800425E0[c[0]&15].unk0=(u16)(c[11]?c[0]:c[0]^0x10);D_8003E368=0x70000;D_80041FD8=(s8)c[7];used=ncalls=0;
  result=candidate_allocate((u16)c[0],(s32)c[1],(u16)c[2],(u8)c[3],(s16)c[4],(u8)c[5],(u8)c[6]);header(1,i,result);word(4869);
  for(j=0;j<16;j++){be(p,2,D_800425E0[j].unk0);be(p+2,2,D_800425E0[j].unk2);be(p+4,2,D_800425E0[j].unk4);be(p+6,2,D_800425E0[j].unk6);be(p+8,4,ptr(D_800425E0[j].unk8));bytes(p,12);}
  be(p,4,(u32)D_8003E368);bytes(p,4);p[0]=(u8)D_80041FD8;bytes(p,1);bytes((u8*)voices,4096);bytes(other.bytes,256);bytes(newvoice.bytes,256);bytes(mark,32);if(flush())return 2;
 }
 for(i=0;i<sizeof(caller_cases)/sizeof(caller_cases[0]);i++){f=caller_cases[i];seed=f[16];pattern((u8*)&actor,812);pattern(mark,32);
  actor.unk8C=(u16)(((u32)((u8*)&actor)[0x8C]<<8)|((u8*)&actor)[0x8D]);actor.unk8E=(u16)(((u32)((u8*)&actor)[0x8E]<<8)|((u8*)&actor)[0x8F]);actor.unk184=(s32)frombe((u8*)&actor+0x184);
  actor.interaction_state=(s32)f[6];actor.id=(u8)f[8];actor.camera=(void*)f[7];actor.xz_scale=real(f[10]);actor.x_position=real(f[11]);actor.y_position=real(f[12]);actor.z_position=real(f[13]);D_80041FD9=(u8)f[14];
  for(j=0;j<187;j++){D_800D1C90[j]=&descriptors[j];for(k=0;k<44;k++)((u8*)&descriptors[j])[k]=(u8)((j*44+k)*29+seed*11+90);descriptors[j].unkE=(s16)f[9];for(k=0;k<44;k++)descriptor_before[j][k]=((u8*)&descriptors[j])[k];}
  for(j=0;j<18;j++)temp[j]=0;temp[14]=f[15];g=temp;used=ncalls=0;result=candidate_caller((s32)f[0],(s32)f[1],(u16)f[2],(s16)f[3],(u8)f[4],f[5]?&actor:NULL);header(2,i,result);word(844);actor_bytes(1);bytes(mark,32);
  for(j=0;j<187;j++){if(D_800D1C90[j]!=&descriptors[j])return 10;for(k=0;k<44;k++)if(descriptor_before[j][k]!=((u8*)&descriptors[j])[k])return 11;}if(D_80041FD9!=(u8)f[14])return 12;if(flush())return 3;
 }
 return 0;}
'''.replace('GAME_ROWS',array(grows)).replace('INIT_ROWS',array(irows)).replace('CALLER_ROWS',array(frows))
 # 192 + 4 + 1 + 4096 + 256 + 256 + 32 = 4837 public bytes.
 post=post.replace('word(4869)','word(4837)')
 return pre+pgame+'\n'+pinit+'\n'+pcaller+'\n'+post+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),bytes(expected),dict(game_cases=len(gs),init_cases=len(cs),caller_cases=len(fs))

def main():
 source,expected,counts=source_and_expected();p=out/'audio-native.c';p.write_text(source);profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('audio-native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60)
  if r.stdout!=expected:
   at=next((i for i,(a,b)in enumerate(zip(r.stdout,expected))if a!=b),min(len(r.stdout),len(expected)))
   raise AssertionError((opt,r.returncode,len(r.stdout),len(expected),at,r.stdout[max(0,at-12):at+16].hex(),expected[max(0,at-12):at+16].hex(),r.stderr))
  assert r.returncode==0 and not r.stderr,(opt,r.returncode,r.stderr)
  profiles[opt]=dict(exit=0,UBSan=True,exact_output_bytes=len(expected),**counts)
 r=dict(profiles=profiles,SDK32=True,canonical_calls_and_complete_public_bytes=True,stub_helper_algorithms_not_qualified=True)
 (out/'audio-native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
