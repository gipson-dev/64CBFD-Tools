from pathlib import Path
import json,subprocess
from tools.tests import game_attached_direction_constructor_151a8624_behavior as b
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-attached-direction-constructor-151a8624-screen';s=(o/'selected.c').read_text();a=s.index('typedef struct {\n    u8 *target;\n    u8 identity, pad05[3];\n    struct17 local;');z=s.index('/* Construct an attached',a);head=s[a:z];a=z;z=s.index('\n\n\ntypedef struct {',a);body=s[a:z]
bad={'wrong_default_lifetime':body.replace('lifetime == -1 ? 300','lifetime == -1 ? 301'),
 'wrong_vertex_count':body.replace('descriptor.count = 9','descriptor.count = 8'),
 'wrong_matrix_index':body.replace('cache.matrixIndex = matrixIndex','cache.matrixIndex = matrixIndex ^ 1'),
 'wrong_identity':body.replace('owner[0x3B]','owner[0x3A]'),
 'wrong_lifetime_flags':body.replace('flags = lifetime == -1 ? 0 : 1','flags = lifetime == -1 ? 1 : 0'),
 'wrong_payload_size':body.replace('extraBytes + 40u','extraBytes + 36u'),
 'short_cache_copy':body.replace('&cache, sizeof(cache)','&cache, sizeof(cache) - 4')}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==7
code='#include <ultra64.h>\ntypedef struct {f32 unk0,unk4,unk8;} struct17;\ns32 func_151A7950(u8*,s32,u8,s32);\nvoid*memcpy(void*,const void*,u32);\n'+head+'\n'.join(v.replace('func_151A8624','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+=r'''
typedef union {u32 u;f32 f;} Bits;
typedef struct {u32 present,offset,matrix,lifetime,kind,mode,second,extra,channel,context,outcome,mutation,seed,packedOffset,minimum,range,scale,amplitude;u32 descriptor[15],descriptorBytes[6],tag[4],cache[6],cacheBytes[4];} Case;
static const Case cases[]={
'''
rows=[];arr=lambda xs:'{'+','.join(hex(b.u32(x))+'u' for x in xs)+'}'
for c in b.cases():
 if c.phase:continue
 m,cache,desc=b.build(b.fixture(c),c)
 scalars=(int(bool(c.owner)),int(bool(c.offset)),c.matrix,c.lifetime,c.kind,c.mode,c.second,c.extra,c.channel,c.context,c.outcome,c.mutation,c.seed,c.packed-b.PACKED,c.minimum,c.range,c.scale,c.amplitude)
 words=[b.read(m,desc+at) for at in (4,8,16,24,*range(32,76,4))] if c.owner else [0]*15
 db=[b.read(m,desc,2),b.read(m,desc+2,2),m[desc+12],m[desc+28],m[desc+29],m[desc+76]] if c.owner else [0]*6
 tag=[m[desc+20+i] for i in range(4)] if c.owner else [0]*4;cw=[b.read(m,cache+at) for at in (8,12,16,24,28,32)] if c.owner else [0]*6;cb=[m[cache+at] for at in (4,20,36,37)] if c.owner else [0]*4
 rows.append('{'+','.join(hex(b.u32(v))+'u' for v in scalars)+','+','.join(arr(v) for v in (words,db,tag,cw,cb))+'}')
code+=',\n'.join(rows)+'\n};\n'+r'''
typedef struct {u8 prefix[96];void*cache;u8 tail[412];} Record;
typedef struct {DirectionPackedWord151A8624 value;u8 tail[4];} Token0;
typedef struct {u8 prefix;DirectionPackedWord151A8624 value;u8 tail[3];} Token1;
typedef char Layout[sizeof(Record)==512&&sizeof(DirectionDescriptor151A8624)==80&&sizeof(AttachedDirectionCache151A8624)==40&&__builtin_offsetof(AttachedDirectionCache151A8624,attachmentMode)==36&&__builtin_offsetof(DirectionDescriptor151A8624,packed)==20?1:-1];
static Record record;static AttachedDirectionCache151A8624 cache,other;static u8 owner[256],before[512],cacheBefore[40];static struct17 position,offset;
static Token0 token0 __attribute__((aligned(4)));static Token1 token1 __attribute__((aligned(4)));static DirectionPackedWord151A8624*token;
static const Case*current;static u32 calls,error;f32 D_800A8DE0;
static f32 real(u32 v){Bits b;b.u=v;return b.f;}static u32 word(f32 v){Bits b;b.f=v;return b.u;}
static void effect(void){u32 i;if(!(current->mutation&1))return;owner[59]^=0x7f;position.unk0=20.f;position.unk4=21.f;position.unk8=22.f;if(current->offset){offset.unk0=-20.f;offset.unk4=-21.f;offset.unk8=-22.f;}for(i=0;i<4;i++)token->bytes[i]^=0x55;D_800A8DE0=2.f;}
s32 func_151A7950(u8*source,s32 bytes,u8 channel,s32 context){DirectionDescriptor151A8624*p=(DirectionDescriptor151A8624*)source;u32 i,values[15];if(calls++!=0||(u32)bytes!=current->extra+40u||channel!=(current->channel&255)||(u32)context!=current->context)error=1;
 if((u16)p->lifetime!=current->descriptorBytes[0]||(u16)p->count!=current->descriptorBytes[1]||p->flags!=current->descriptorBytes[2]||(u8)p->firstCallback!=current->descriptorBytes[3]||(u8)p->secondCallback!=current->descriptorBytes[4]||p->kind!=current->descriptorBytes[5])error=1;
 values[0]=word(p->minimum);values[1]=word(p->range);values[2]=word(p->amplitude);values[3]=word(p->scale);values[4]=word(p->start.unk0);values[5]=word(p->start.unk4);values[6]=word(p->start.unk8);values[7]=word(p->end.unk0);values[8]=word(p->end.unk4);values[9]=word(p->end.unk8);values[10]=word(p->direction.unk0);values[11]=word(p->direction.unk4);values[12]=word(p->direction.unk8);values[13]=word(p->length);values[14]=word(p->reciprocal);
 for(i=0;i<15;i++)if(values[i]!=current->descriptor[i])error=1;for(i=0;i<4;i++)if(p->packed.bytes[i]!=current->tag[i])error=1;effect();if(current->outcome)record.cache=&cache;return current->outcome?(s32)&record:0;}
void*memcpy(void*d,const void*s,u32 n){u32 i;u8*dst=d;const u8*src=s;if(calls++!=1||d!=&cache||n!=40)error=1;for(i=0;i<n;i++)dst[i]=src[i];if(current->mutation&2)record.cache=&other;return (void*)0x12345678u;}
static s32(*candidates[])(u8*,struct17*,u8,s16,f32,f32,DirectionPackedWord151A8624*,f32,struct17*,u8,u8,s8,s32,u8,s32)={candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5,candidate_6,candidate_7};
static int run(void){u32 i,j,k,killed=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;
 for(j=0;j<8;j++){s32 answer;u32 cw[6];for(k=0;k<512;k++)((u8*)&record)[k]=(u8)(k*29+current->seed*11+0x5a);for(k=0;k<40;k++)((u8*)&cache)[k]=(u8)(k*29+current->seed*11+0x5a);for(k=0;k<256;k++)owner[k]=(u8)(k*29+current->seed*11+0x5a);owner[59]=0x87;
  position.unk0=1.25f;position.unk4=-2.5f;position.unk8=3.75f;offset.unk0=-.5f;offset.unk4=1.5f;offset.unk8=real(0x80000000u);token=current->packedOffset?&token1.value:&token0.value;for(k=0;k<4;k++)token->bytes[k]=(u8)((k+current->packedOffset)*29+current->seed*11+0x5a);D_800A8DE0=real(current->amplitude);
  for(k=0;k<512;k++)before[k]=((u8*)&record)[k];for(k=0;k<40;k++)cacheBefore[k]=((u8*)&cache)[k];calls=error=0;
  answer=candidates[j](current->present?owner:0,&position,(u8)current->matrix,(s16)current->lifetime,real(current->minimum),real(current->range),token,real(current->scale),current->offset?&offset:0,(u8)current->kind,(u8)current->mode,(s8)current->second,(s32)current->extra,(u8)current->channel,(s32)current->context);
  if((u32)answer!=(current->present&&current->outcome?(u32)&record:0)||calls!=(current->present?(current->outcome?2:1):0))error=1;
  if(current->present&&current->outcome){cw[0]=word(cache.local.unk0);cw[1]=word(cache.local.unk4);cw[2]=word(cache.local.unk8);cw[3]=word(cache.offset.unk0);cw[4]=word(cache.offset.unk4);cw[5]=word(cache.offset.unk8);for(k=0;k<6;k++)if(cw[k]!=current->cache[k])error=1;if(cache.target!=owner||cache.identity!=current->cacheBytes[0]||cache.matrixIndex!=current->cacheBytes[1]||cache.attachmentMode!=current->cacheBytes[2]||cache.flags!=current->cacheBytes[3]||record.cache!=(current->mutation&2?(void*)&other:(void*)&cache))error=1;}
  else for(k=0;k<40;k++)if(((u8*)&cache)[k]!=cacheBefore[k])error=1;
  for(k=0;k<512;k++)if(!(current->present&&current->outcome&&k>=96&&k<100)&&((u8*)&record)[k]!=before[k])error=1;
  if(owner[59]!=(current->present&&(current->mutation&1)?(0x87^0x7f):0x87))error=1;
  if(error){if(!j)return 10;killed|=1u<<(j-1);}
 }
}return killed==127u?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
p=o/'native-attached-direction-constructor.c';p.write_text(code);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=o/('native-attached-direction-constructor'+opt+alias);q=subprocess.run(native_command(opt)+[alias,'-o',str(exe),str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=r,capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr);profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,typed_disjoint_inputs=True,uninitialized_padding_not_compared=True,helpers_modeled=True)
(o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
