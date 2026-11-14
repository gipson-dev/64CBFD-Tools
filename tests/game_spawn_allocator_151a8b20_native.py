from pathlib import Path
import sys,json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-spawn-allocator-151a8b20-screen'
from tools.tests import game_spawn_allocator_151a8b20_behavior as b
s=(o/'selected.c').read_text();a=s.index('typedef struct {\n    ParitySpawnRequest request;');z=s.index('\ns32 func_151A8CEC',a);piece=s[a:z];head,body=piece.split('/* Allocate an actor',1);body='/* Allocate an actor'+body
start=s.index('typedef struct {\n    u8 kind;');end=s.index('} ParitySpawnRequest;',start)+len('} ParitySpawnRequest;');request=s[start:end]
bad={
 'wrong_snapshot_size':body.replace('request, 0x28','request, 0x24'),
 'wrong_default_lifetime':body.replace('? 300 : lifetime','? 301 : lifetime'),
 'wrong_zero':body.replace('payload.zero4C = 0','payload.zero4C = 1'),
 'wrong_payload_size':body.replace('&payload, 0x58','&payload, 0x54'),
 'wrong_owner_coordinate':body.replace('((s16 *)state->request.owner)[2]','((s16 *)state->request.owner)[1]'),
 'wrong_spatial_gate':body.replace('state->request.kind & 4','state->request.kind & 8'),
 'wrong_scale':body.replace('* state->request.zero[4] * D_800A8F54','* state->request.zero[4]')}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==7
code='#include <ultra64.h>\ntypedef struct struct260 struct260;typedef struct struct37 struct37;typedef struct struct134 struct134;\nvoid *memcpy(void *,const void *,u32);\n'+request+'\n'+head+'\n'.join(v.replace('func_151A8B20','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+=r'''
typedef union {u32 u;f32 f;} Bits;
typedef struct {u32 flags,hasOwner,life; s32 extra;u32 channel,context,mutation,outcome,seed,duration,mode,bytes,lookupX,lookupZ,heightOwner,finalFlags,finalOwner,constant,spatial,scale,mark;} Case;
static const Case cases[]={
'''
rows=[]
for c in b.cases():
 if c.phase or c.mutation&2:continue
 m,calls,obs,answer=b.reference(b.fixture(c),c);factory=next(a for t,a in calls if t==b.FACTORY);lookup=next((a for t,a in calls if t==b.LOOKUP),(0,0));height=next((a[0] for t,a in calls if t==b.HEIGHT),0);state=c.output+40
 values=[c.flags,bool(c.owner),b.u32(c.lifetime),c.extra,c.channel,c.context,c.mutation,c.outcome,c.seed,factory[0],factory[4],factory[6],*lookup,0 if not height else (1 if height==b.OWNER else 2),m[state],0 if not b.read(m,state+4) else (1 if b.read(m,state+4)==b.OWNER else 2),b.read(m,state+44),b.read(m,state+80),b.read(m,state+84),b.read(m,b.MARK)]
 rows.append('{'+','.join(str(v) if i==3 else '0x%Xu'%v for i,v in enumerate(values))+'}')
code+=',\n'.join(rows)+'\n};\n'
code+=r'''
typedef char RequestLayout[sizeof(ParitySpawnRequest)==40?1:-1];
typedef char PayloadLayout[sizeof(SpawnPayload151A8B20)==88 && __builtin_offsetof(SpawnPayload151A8B20,spatial)==80?1:-1];
typedef struct {u8 header[40];SpawnPayload151A8B20 payload;} Object;
static ParitySpawnRequest input;static Object output;static s16 owner[3],owner2[3];static u8 snapshot[40];static void*firstDest;
f32 D_800A8F50,D_800A8F54;static const Case*current;static u32 copies,factories,resets,lookups,heights,error,mark;
static f32 real(u32 x){Bits b;b.u=x;return b.f;}static u32 word(f32 x){Bits b;b.f=x;return b.u;}
static void effect(u32 stage){SpawnPayload151A8B20*p=&output.payload;
 if(!current->mutation)return;
 if(stage==0){input.kind^=0x80;input.owner=(u8*)owner2;D_800A8F50=2.;}
 if(stage==1){p->request.kind^=6;p->request.owner=(u8*)owner2;p->request.zero[4]=4.;}
 if(stage==2){owner[0]=owner2[0]=100;owner[2]=owner2[2]=-100;p->request.zero[0]=42.;p->request.zero[2]=-42.;D_800A8F54=.5;}
 if(stage==3){p->request.kind^=2;p->request.owner=0;p->request.zero[4]=5.;}
}
void *memcpy(void*dest,const void*src,u32 n){u32 i;const u8*bytes=(const u8*)src;
 if(!copies){
  if(src!=&input||n!=40)error=1;firstDest=dest;
  for(i=0;i<40;i++)snapshot[i]=((const u8*)&input)[i];
 }else{
  const SpawnPayload151A8B20*p=(const SpawnPayload151A8B20*)src;
  if(copies!=1||dest!=&output.payload||src!=firstDest||n!=88||!factories)error=1;
  for(i=0;i<40;i++)if(((const u8*)src)[i]!=snapshot[i])error=1;
  if(word(p->zero28)||word(p->initial2C)!=current->constant||p->zero44||p->zero48||p->zero49||p->zero4C)error=1;
 }
 if(n<=88)for(i=0;i<n;i++)((u8*)dest)[i]=bytes[i];effect(copies?1:0);copies++;return dest;
}
struct260 *func_15149130(s16 duration,s8 a1,s8 a2,s8 a3,u8 mode,u8 a5,struct37*bytes,u8 channel,s32 context){
 if(copies!=1||factories||(u32)(s32)duration!=current->duration||a1!=-1||a2!=0x25||a3!=-1||mode!=current->mode||a5!=0x22||(u32)bytes!=current->bytes||channel!=(u8)current->channel||context!=(s32)current->context)error=1;
 factories++;mark=0x11223344;return current->outcome?(struct260*)&output:0;
}
void func_1510F800(s32 mode){if(mode||!factories||copies!=2||resets)error=1;resets++;effect(2);}
u8 *func_1510FD20(s32 x,s32 z){if(resets!=1||lookups||(u32)x!=current->lookupX||(u32)z!=current->lookupZ)error=1;lookups++;effect(3);return (u8*)(0x60000+current->seed);}
f32 func_15144598(struct134*p){u32 which=p==(struct134*)owner?1:p==(struct134*)owner2?2:0;if(!which||which!=current->heightOwner||heights)error=1;heights++;mark=0x55667788;return -2.25f;}
typedef u8*(*Candidate)(void*,s16,s32,u8,s32);
'''
code+='static Candidate candidates[]={'+','.join('candidate_'+str(i) for i in range(8))+'};\n'
code+=r'''
static int run(void){u32 i,j,k,killed=0;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;
  for(j=0;j<8;j++){u8*answer;SpawnPayload151A8B20*p=&output.payload;
   for(k=0;k<40;k++)((u8*)&input)[k]=(k*19+current->seed*7)&255;
   input.kind=current->flags;input.owner=current->hasOwner?(u8*)owner:0;input.zero[0]=-12.75;input.zero[2]=32766.75;input.zero[4]=current->seed?real(0xc0600001):-3.5;
   for(k=0;k<sizeof(output);k++)((u8*)&output)[k]=(k*19+current->seed*7)&255;
   owner[0]=owner2[0]=-32768;owner[1]=owner2[1]=0;owner[2]=owner2[2]=32767;D_800A8F50=.5;D_800A8F54=current->seed?real(0x3e99999a):.25;
   copies=factories=resets=lookups=heights=error=mark=0;firstDest=0;
   answer=candidates[j](&input,current->life,current->extra,current->channel,current->context);
   if(answer!=(current->outcome?(u8*)&output:0)||factories!=1||copies!=(current->outcome?2:1)||resets!=lookups||heights!=!!current->heightOwner||mark!=current->mark)error=1;
   if(current->outcome){
    u8*wantOwner=current->finalOwner==1?(u8*)owner:current->finalOwner==2?(u8*)owner2:0;
    if(p->request.kind!=current->finalFlags||p->request.owner!=wantOwner||word(p->zero28)||word(p->initial2C)!=current->constant||p->zero44||p->zero48||p->zero49||p->zero4C||p->spatial!=(s32)current->spatial||word(p->scale)!=current->scale)error=1;
   }
   for(k=0;k<40;k++)if(output.header[k]!=(u8)(k*19+current->seed*7))error=1;
   if(error){if(j==0)return 10;killed|=1u<<(j-1);}
  }
 }
 return killed==127u?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
p=o/'native-spawn-allocator.c';p.write_text(code);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=o/('native-spawn-allocator'+opt+alias);q=subprocess.run(native_command(opt)+[alias,'-o',str(exe),str(p)],cwd=r,capture_output=True,text=True)
  assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(exe)],cwd=r,capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr)
  profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,retained_payload_bytes_excluded=30,typed_disjoint_inputs=True,helpers_modeled=True)
(o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
