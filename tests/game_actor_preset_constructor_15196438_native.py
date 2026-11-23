"""SDK32 typed presets/packets; only initialized native fields are compared."""
from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_actor_preset_constructor_15196438_match as p
r=p.ROOT;o=p.OUT
from tools.tests import game_actor_preset_constructor_15196438_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
PRESET=[(0,2),(4,4),(8,4),(12,1),(16,4),(20,1)]+[(i,4)for i in range(0x18,0x30,4)]+[(i,1)for i in range(0x30,0x34)]+[(0x34,4),(0x38,4)]+[(i,1)for i in range(0x3C,0x43)]+[(0x44,2),(0x46,1),(0x47,1),(0x48,4),(0x4C,1),(0x50,4),(0x54,1),(0x58,4)]+[(i,1)for i in range(0x5C,0x60)]
FIELDS=[(0,4)]+[(i,1)for i in range(4,8)]+[(i,4)for i in range(8,0x40,4)]+[(0x40,4),(0x48,4),(0x4C,4)]+[(i,1)for i in range(0x50,0x55)]+[(0x58,4),(0x5C,4)]+[(i,1)for i in range(0x60,0x66)]+[(0x66,2)]+[(i,1)for i in range(0x68,0x6B)]+[(0x6C,4),(0x70,4),(0x74,1),(0x78,4),(0x7C,4),(0x80,1),(0x84,4),(0x88,4)]+[(i,1)for i in range(0x8C,0x90)]
REQUEST=[(0,4),(4,4),(8,4),(12,2),(14,2),(16,4),(21,1)]
def values(m,base,fields):return[g.read(m,base+at,width)for at,width in fields]
def byte_values(data,fields):return[int.from_bytes(data[at:at+n],'big')for at,n in fields]
def vector_header():
 rows=[]
 def array(v):return'{'+','.join(str(x&0xffffffff)+'u'for x in v)+'}'
 for c in g.cases():
  initial=g.fixture(c);expected,calls,result,observations=g.reference(initial,c);home=g.STACK+c.phase;packet=home-172;request=home-28
  def normalize(v):
   if packet<=v<packet+0x90:return 0xABC00000+v-packet
   if v==request:return 0xABC00100
   return v
  def role(t):return 0 if t in g.SOUND else 1 if t==g.TRANSFORM else 2 if t==g.ALLOCATE else 3 if t==g.COPY else 4+g.SCALE.index(t)if t in g.SCALE else 7
  events=['{%du,%du,%s}'%(role(t),len(a),array([normalize(x)for x in a]))for t,a in calls]
  points=[v for k,v in observations if k=='point'];req=next((v for k,v in observations if k=='request'),bytes(28));data=next((v for k,v in observations if k=='packet'),bytes(0x90))
  params=[c.seed,c.null,c.matrix,c.preset,c.channel,c.context,c.success,c.mutations,c.sound_return,c.scale_bits,result,g.read(expected,g.OWNER+0x1D4),expected[g.OWNER+0x3B],g.read(expected,g.CREATED+0x98)]
  rows.append('{'+','.join(str(v&0xffffffff)+'u'for v in params)+','+array(values(initial,g.S['D_800A87A0']+c.preset*96,PRESET))+','+array(values(initial,g.PAYLOAD,FIELDS))+','+array(values(initial,g.ALTERNATE,FIELDS))+','+array(byte_values(data,FIELDS))+','+array(values(expected,g.PAYLOAD,FIELDS))+','+array(values(expected,g.ALTERNATE,FIELDS))+','+array(byte_values(req,REQUEST))+','+array([int.from_bytes(v[k:k+4],'big')for v in points for k in(0,4,8)]+[0]*(6-len(points)*3))+','+array([x for step in range(2)for x in g.output_bits(c,step)])+','+array([g.read(initial,g.MARK),g.read(initial,g.MARK+4)])+','+array([g.read(expected,g.MARK),g.read(expected,g.MARK+4)])+','+str(len(events))+'u,{'+','.join(events)+'}}')
 header='typedef struct{u32 at,width;}Field;\n'
 for name,fields in(('presetFields',PRESET),('payloadFields',FIELDS),('requestFields',REQUEST)):header+='static const Field '+name+'[]={'+','.join('{%du,%du}'%p for p in fields)+'};\n'
 header+=f'typedef struct{{u32 seed,null,matrix,preset,channel,context,success,mutations,soundReturn,scaleBits,result,wantMatrix,wantId,wantPayload;u32 table[{len(PRESET)}],initialPayload[{len(FIELDS)}],initialAlternate[{len(FIELDS)}],packet[{len(FIELDS)}],payload[{len(FIELDS)}],alternate[{len(FIELDS)}],request[{len(REQUEST)}],inputs[6],outputs[6],initialMark[2],wantMark[2],calls;Event events[7];}}Vector;\n'
 header+='static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n';(o/'native-vectors.h').write_text(header);return len(rows)
def program():
 body=p.MANIFEST['body'].replace('func_15196438(','subject(');decl=p.MANIFEST['declarations']
 src='#include <ultra64.h>\n#include "structs.h"\n#include <string.h>\n'+decl+r'''
typedef struct{u32 role,count,arg[11];}Event;
#include "native-vectors.h"
typedef struct{u8 opaque[0x98];u8 *payload;}Core;
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(EffectPoint15196438)==12&&sizeof(EffectPreset15196438)==96&&sizeof(EffectPayload15196438)==144&&sizeof(EffectRequest15196438)==28,"SDK32 effect record sizes");
_Static_assert(__builtin_offsetof(struct127,unique_id)==0x3b&&__builtin_offsetof(struct127,unk1D4)==0x1d4&&__builtin_offsetof(EffectPayload15196438,soundHandle)==0x66&&__builtin_offsetof(EffectPayload15196438,setupCallback)==0x60&&__builtin_offsetof(EffectPayload15196438,field8F)==0x8f&&__builtin_offsetof(EffectPreset15196438,field5F)==0x5f&&__builtin_offsetof(EffectRequest15196438,count)==0x15&&__builtin_offsetof(Core,payload)==0x98,"SDK32 field offsets");
static struct127 actor;static Core created;static EffectPayload15196438 storage,alternate;
static u8 matrices[0x4100]__attribute__((aligned(16)));static u32 marker[2];
EffectPreset15196438 D_800A87A0[7];
static const Vector*v;static u32 step,callCount,error;static u8 *packet,*request;static Event events[7];
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static void set(void*p,u32 value,u32 n){u32 k;for(k=0;k<n;k++)((u8*)p)[k]=(u8)(value>>(8*k));}
static u32 get(const void*p,u32 n){u32 k,value=0;for(k=0;k<n;k++)value|=(u32)((const u8*)p)[k]<<(8*k);return value;}
static f32 real(u32 bits){f32 f;copy(&f,&bits,4);return f;}
static u32 norm(u32 value){if(value==(u32)&actor)return 0x30000;if(value==(u32)&created)return 0x50000;if(value==(u32)&storage)return 0x60000;if(value==(u32)&alternate)return 0x61000;if(value>=(u32)matrices&&value<(u32)(matrices+sizeof(matrices)))return 0x40000+value-(u32)matrices;if(packet&&value>=(u32)packet&&value<(u32)(packet+0x90))return 0xabc00000+value-(u32)packet;if(request&&value==(u32)request)return 0xabc00100;return value;}
static void event(u32 role,u32 count,const u32*args){u32 i;Event*e;if(callCount==7){error=1;return;}e=&events[callCount++];e->role=role;e->count=count;for(i=0;i<count;i++)e->arg[i]=norm(args[i]);}
static void initialize(void*p,const Field*f,u32 n,const u32*values,u32 owner){u32 i,value;for(i=0;i<n;i++){value=values[i];if(owner&&f[i].at==0&&value==0x30000)value=(u32)&actor;set((u8*)p+f[i].at,value,f[i].width);}}
static int compare(const void*p,const Field*f,u32 n,const u32*values,u32 owner,u32 skipScale){u32 i,value;for(i=0;i<n;i++){if(skipScale&&f[i].at==0x38)continue;value=get((const u8*)p+f[i].at,f[i].width);if(owner&&f[i].at==0)value=norm(value);if(value!=values[i])return 0;}return 1;}
__attribute__((noinline,noclone)) static s32 sound(void){event(0,0,0);if(v->mutations&1){actor.unk1D4=(struct255*)(matrices+64);actor.unique_id^=0x55;}return(s32)v->soundReturn;}
s32(*D_8008F890[1])(void)={sound};
__attribute__((noinline,noclone)) void func_15143134(f32*input,f32*output,u8*matrix){u32 a[3],i;if(step==0)packet=(u8*)input-8;if(step>=2){error=1;return;}if(input!=(f32*)(packet+(step?0x14:8))||output!=(f32*)(packet+(step?0x2c:0x20)))error=1;for(i=0;i<3;i++){if(get(input+i,4)!=v->inputs[step*3+i])error=1;set(output+i,v->outputs[step*3+i],4);}a[0]=(u32)input;a[1]=(u32)output;a[2]=(u32)matrix;event(1,3,a);step++;if(v->mutations&2)actor.unk1D4=(struct255*)(matrices+128);}
__attribute__((noinline,noclone)) u8*func_15147A80(void*req,s32 bytes,s32 entry,s32 active,s32 first,s32 second,s32 resource,s32 value,void*optional,u8 channel,s32 context){u32 a[11];request=req;a[0]=(u32)req;a[1]=bytes;a[2]=entry;a[3]=active;a[4]=first;a[5]=second;a[6]=resource;a[7]=value;a[8]=(u32)optional;a[9]=channel;a[10]=context;event(2,11,a);if(!compare(req,requestFields,sizeof(requestFields)/sizeof(requestFields[0]),v->request,0,0))error=1;marker[0]=0x13579bdf;created.payload=(u8*)&storage;return v->success?(u8*)&created:0;}
__attribute__((noinline,noclone)) void*memcpy(void*dst,const void*src,size_t n){u32 a[3];a[0]=(u32)dst;a[1]=(u32)src;a[2]=n;event(3,3,a);if(dst!=&storage||src!=packet||n!=0x90||!compare(src,payloadFields,sizeof(payloadFields)/sizeof(payloadFields[0]),v->packet,1,1))error=1;copy(dst,src,n);return dst;}
__attribute__((noinline,noclone)) static f32 scale0(s32 p){u32 a[1];a[0]=p;event(4,1,a);if(v->mutations&4)storage.setupCallback=-1;if(v->mutations&8)created.payload=(u8*)&alternate;return real(v->scaleBits);}
__attribute__((noinline,noclone)) static f32 scale1(s32 p){u32 a[1];a[0]=p;event(5,1,a);if(v->mutations&4)storage.setupCallback=-1;if(v->mutations&8)created.payload=(u8*)&alternate;return real(v->scaleBits);}
__attribute__((noinline,noclone)) static f32 scale2(s32 p){u32 a[1];a[0]=p;event(6,1,a);if(v->mutations&4)storage.setupCallback=-1;if(v->mutations&8)created.payload=(u8*)&alternate;return real(v->scaleBits);}
f32(*D_8008F870[3])(s32)={scale0,scale1,scale2};
__attribute__((noinline,noclone)) static void setup(u8*p){u32 a[1];a[0]=(u32)p;event(7,1,a);marker[1]=(u32)&created;}
void(*D_8008F87C[1])(u8*)={setup};
'''+body+r'''
static int run(void){u32 k,i,j,value;u8*result;
 for(k=0;k<sizeof(vectors)/sizeof(vectors[0]);k++){
  v=&vectors[k];step=callCount=error=0;packet=request=0;
  for(i=0;i<sizeof(actor);i++)((u8*)&actor)[i]=(u8)(i*29+v->seed*11+0x51);
  for(i=0;i<sizeof(created);i++)((u8*)&created)[i]=(u8)(i*29+v->seed*11+0x51);
  for(i=0;i<sizeof(D_800A87A0);i++)((u8*)D_800A87A0)[i]=0;
  actor.unique_id=(u8)(0x80+v->seed*7);actor.unk1D4=v->matrix?(struct255*)matrices:0;created.payload=(u8*)&storage;
  initialize(&D_800A87A0[v->preset],presetFields,sizeof(presetFields)/sizeof(presetFields[0]),v->table,0);
  initialize(&storage,payloadFields,sizeof(payloadFields)/sizeof(payloadFields[0]),v->initialPayload,1);initialize(&alternate,payloadFields,sizeof(payloadFields)/sizeof(payloadFields[0]),v->initialAlternate,1);marker[0]=v->initialMark[0];marker[1]=v->initialMark[1];
  result=subject(v->null?0:&actor,(s32)v->preset,(s32)v->channel,(s32)v->context);
  if(error||norm((u32)result)!=v->result||callCount!=v->calls||actor.unique_id!=v->wantId||norm((u32)actor.unk1D4)!=v->wantMatrix||norm((u32)created.payload)!=v->wantPayload)return 1;
  if(!compare(&storage,payloadFields,sizeof(payloadFields)/sizeof(payloadFields[0]),v->payload,1,0)||!compare(&alternate,payloadFields,sizeof(payloadFields)/sizeof(payloadFields[0]),v->alternate,1,0)||norm(marker[0])!=v->wantMark[0]||norm(marker[1])!=v->wantMark[1])return 1;
  for(i=0;i<callCount;i++){if(events[i].role!=v->events[i].role||events[i].count!=v->events[i].count)return 1;for(j=0;j<events[i].count;j++){value=events[i].arg[j];if(value!=v->events[i].arg[j])return 1;}}
 }
 return 0;
}
__attribute__((force_align_arg_pointer))void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 return src,body
def main():
 count=vector_header();src,body=program();profiles={}
 def run(text,label,opt):
  f=o/(label+'.c');f.write_text(text);exe=o/(label+opt);q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fmax-errors=1',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr)[-5000:];return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in('-O0','-O2','-O3'):
  q=run(src,'native',opt);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b''),(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,strict_aliasing=True,UBSan=True)
 changes={'wrong-owner-id':body.replace('effect.ownerId = actor->unique_id;','effect.ownerId = actor->unique_id ^ 1;'),'wrong-preset':body.replace('&D_800A87A0[presetIndex]','&D_800A87A0[(presetIndex + 1) % 7]'),'wrong-channel-byte':body.replace('(u8)channel','(u8)(channel >> 8)'),'wrong-request-kind':body.replace('request.kind = 3;','request.kind = 4;'),'wrong-request-flags':body.replace('request.flags = preset->flags;','request.flags = preset->flags ^ 0x100;'),'wrong-zero-sign':body.replace('effect.field3C = 0.0f;','effect.field3C = -0.0f;'),'wrong-result':body.replace('return created;','return NULL;'),'reloaded-matrix':body.replace('func_15143134(effect.localEnd.axis, effect.end.axis, matrix);','func_15143134(effect.localEnd.axis, effect.end.axis, (u8 *)effect.owner->unk1D4 + (effect.matrixIndex << 6));'),'wrong-sound-fallback':body.replace('effect.soundHandle = 0;','effect.soundHandle = 1;'),'fresh-public-setup':body.replace('if (effect.setupCallback != -1)','if (payload->setupCallback != -1)').replace('D_8008F87C[effect.setupCallback]','D_8008F87C[payload->setupCallback]')};effective=[]
 for label,changed in changes.items():
  assert changed!=body;q=run(src.replace(body,changed),'control-'+label,'-O2');assert q.returncode==1 and not q.stderr,(label,q.returncode,q.stderr);effective.append(label)
 q=dict(profiles=profiles,effective_controls=effective,preset_fields=len(PRESET),initialized_payload_fields=len(FIELDS),request_fields=len(REQUEST),limits='Actual SDK32 struct127, typed float arrays and preset/payload/request structures. Only initialized native fields are read for comparison. Guest-seeded padding and complete o32 unsigned-byte outgoing-word restoration are separate gates.',source_installed=p.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
