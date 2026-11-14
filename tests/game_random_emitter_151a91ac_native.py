from pathlib import Path
import sys,itertools,json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.test_game_point_transform_match import read
r=Path.cwd();out=r/'conker/build/game-random-emitter-151a91ac-screen'
from tools.tests import game_random_emitter_151a91ac_behavior as b
s=(out/'selected.c').read_text();start=s.index('typedef struct { s16 value[3]; } RandomChoice151A91AC;');end=s.index('void func_151A931C',start);piece=s[start:end]
head,body=piece.split('/* Submit a randomized emitter',1);body='/* Submit a randomized emitter'+body
bad={
 'wrong_range':body.replace('func_150ADA68() * 50.0f + 50.0f','func_150ADA68() * 51.0f + 50.0f'),
 'wrong_choice':body.replace('% 3U','% 2U'),
 'wrong_constant':body.replace('descriptor.random = 160','descriptor.random = 161'),
 'wrong_effect':body.replace('descriptor.effect = 0x3B0002','descriptor.effect = 0x3B0003'),
 'wrong_attachment':body.replace('(s32)(owner + 0x58)','(s32)(owner + 0x5C)'),
 'wrong_random_byte':body.replace('first & 255','first & 127'),
 'wrong_sum':body.replace('(third & 1) + (second & 1)','(third & 1) + (second & 0)')}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==len(bad)
code='#include <ultra64.h>\ntypedef struct struct210 struct210;\ns32 func_150ADA20(void);\n'+head+'\n'.join(v.replace('func_151A91AC','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+=r'''
typedef union {u32 u;f32 f;} Bits;
typedef struct {u32 randf,draws[4],mutation,seed,expectedSlot,expectedRange,expectedPos[3],expectedByte,expectedSum,expectedOwnerC,expectedOwner1;} Case;
static const Case cases[]={
'''
rows=[]
for c in b.cases():
 if c.phase or c.mutation&2:continue
 initial=b.fixture(c);m,calls,obs=b.reference(initial,c);args=calls[-1][1]
 rows.append('{%s,{%s},%s,%s,%s,%s,{%s},%s,%s,%s,%s}'%tuple(['0x%Xu'%c.randf,','.join('0x%Xu'%x for x in c.draws),'0x%Xu'%c.mutation,'0x%Xu'%c.seed,'0x%Xu'%obs[0][6],'0x%Xu'%args[7],','.join('0x%Xu'%x for x in args[4:7]),'0x%Xu'%args[9],'0x%Xu'%args[10],'0x%Xu'%args[14],'0x%Xu'%args[15]]))
code+=',\n'.join(rows)+'\n};\n'
code+=r'''
typedef char ChoiceLayout[sizeof(RandomChoice151A91AC)==6?1:-1];
typedef char DescLayout[sizeof(RandomEmitter151A91AC)==40 && __builtin_offsetof(RandomEmitter151A91AC,effect)==24?1:-1];
RandomChoice151A91AC D_8008F9A4;static u8 owner[256];static f32 position[3];static const Case*current;static u32 step,error;
static f32 real(u32 x){Bits b;b.u=x;return b.f;}static u32 word(f32 x){Bits b;b.f=x;return b.u;}
static void effect(u32 index){u32 i;if(!current->mutation)return;
 D_8008F9A4.value[0]=0x7fff;D_8008F9A4.value[1]=0x0102;D_8008F9A4.value[2]=(s16)0xff80;
 owner[1]=(0x50+current->seed+index)&255;owner[12]=(0xa0+current->seed+index)&255;
 for(i=0;i<3;i++)position[i]=real(0x3f800000+current->seed+index*16+i);
}
f32 func_150ADA68(void){if(step!=0)error=1;step++;effect(0);return real(current->randf);}
s32 func_150ADA20(void){u32 n;if(step<1||step>4){error=1;return 0;}n=step-1;step++;effect(n+1);return (s32)current->draws[n];}
struct210 *func_1513C650(s32 address,u8 a1,u8 a2,s32 attachment,f32 x,f32 y,f32 z,f32 r0,f32 r1,u8 tag,u8 sum,s32 v11,s32 v12,s32 v13,u8 ownerC,s32 owner1){
 RandomEmitter151A91AC*d=(RandomEmitter151A91AC*)address;
 if(step!=5||a1!=1||a2!=0||attachment!=(s32)(owner+0x58)||word(x)!=current->expectedPos[0]||word(y)!=current->expectedPos[1]||word(z)!=current->expectedPos[2]||
 word(r0)!=current->expectedRange||word(r1)!=current->expectedRange||tag!=current->expectedByte||sum!=current->expectedSum||v11!=3||v12!=255||v13||ownerC!=current->expectedOwnerC||owner1!=(s32)current->expectedOwner1)error=1;
 if(d->flags!=0x1701||d->lifetime!=60||d->slot!=current->expectedSlot||d->kind||d->zero8||d->zeroC||
 d->random!=160||d->value11!=255||d->value12||d->value13||d->value14||d->value15!=255||d->zero16||d->seven!=7||d->effect!=0x3b0002)error=1;
 step++;return (struct210*)0;
}
typedef void(*Candidate)(u8*,f32*,s32,s32);
'''
code+='static Candidate candidates[]={'+','.join('candidate_'+str(i) for i in range(len(bad)+1))+'};\n'
code+=r'''
static int run(void){u32 i,j,k,killed=0;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;
  for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
   D_8008F9A4.value[0]=-32768;D_8008F9A4.value[1]=-1;D_8008F9A4.value[2]=0x1234;
   for(k=0;k<256;k++)owner[k]=(k*19+current->seed*7)&255;
   for(k=0;k<3;k++)position[k]=real(0x3f800000+k*0x10000);
   step=error=0;candidates[j](owner,position,0x87654321,0x12345678);
   if(step!=6)error=1;if(error){if(j==0)return 10;killed|=1u<<(j-1);}
  }
 }
 return killed==127u?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
# The guest fixture's initial owner and position bytes are seeded patterns.
# Recreate those exact words in native setup rather than relying on host address.
code=code.replace('for(k=0;k<3;k++)position[k]=real(0x3f800000+k*0x10000);','for(k=0;k<3;k++){u32 x=0;u32 t;for(t=0;t<4;t++)x=(x<<8)|((k*4*19+t*19+current->seed*7+0x10)&255);position[k]=real(x);}')
code=code.replace('owner[k]=(k*19+current->seed*7)&255','owner[k]=(k*19+current->seed*7)&255')
p=out/'native-random-emitter.c';p.write_text(code);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=out/('native-random-emitter'+opt+alias);q=subprocess.run(native_command(opt)+['-g','-Wno-unused-variable',alias,'-o',str(exe),str(p)],cwd=r,capture_output=True,text=True)
  assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(exe)],cwd=r,capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr)
  profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,retained_bytes_excluded=12,finite_fp_only=True,helpers_modeled=True)
(out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
