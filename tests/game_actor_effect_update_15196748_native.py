"""Actual SDK32 objects, initialized fields, mutation-capable typed providers."""
from pathlib import Path
import json,struct,subprocess,sys
from tools.experiments import game_actor_effect_update_15196748_match as p
r=p.ROOT;o=p.OUT
from tools.tests import game_actor_effect_update_15196748_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
OWNER_FIELDS=[(0x1e,2),(0x25,1),(0x2c,1),(0x2d,1),(0x2e,1),(0x2f,1),(0x30,1)]+[(i,4)for i in(0x54,0x58,0x5c,0x94,0x98)]
PAYLOAD_FIELDS=[(0,4),(6,1),(0x40,4),(0x52,1),(0x6a,1),(0x58,4),(0x64,1),(0x68,1),(0x61,1),(0x66,2)]+[(i,1)for i in range(0x8c,0x90)]
RECORD_FIELDS=[(i,4)for i in range(0,28,4)]+[(28,2),(30,1),(31,1),(33,1)]
def values(m,base,fields):return[g.read(m,base+a,n)for a,n in fields]
def vector_header():
 lines=['typedef struct{u32 at,width;}Field;'];rows=[]
 def arr(name,vals):lines.append('static const u32 '+name+'[]={'+','.join(str(x&0xffffffff)+'u'for x in vals)+'};');return name
 for name,fields in(('ownerFields',OWNER_FIELDS),('payloadFields',PAYLOAD_FIELDS),('recordFields',RECORD_FIELDS)):lines.append('static const Field '+name+'[]={'+','.join('{%du,%du}'%v for v in fields)+'};')
 for index,c in enumerate(g.cases()):
  m=g.fixture(c);expected,calls,value=g.reference(m,c);params=(c.seed,c.cap,c.head,c.mutations,c.tick_result,c.tick,c.dt,value,g.read(expected,g.MARK),g.read(expected,g.MARK+4),len(calls));parts=[str(v&0xffffffff)+'u'for v in params]
  for suffix,vals in(('oi',values(m,g.OWNER,OWNER_FIELDS)),('oo',values(expected,g.OWNER,OWNER_FIELDS)),('pi',[x for base in(g.PAYLOAD,g.ALT_PAYLOAD)for x in values(m,base,PAYLOAD_FIELDS)]),('po',[x for base in(g.PAYLOAD,g.ALT_PAYLOAD)for x in values(expected,base,PAYLOAD_FIELDS)]),('ri',[x for base in(g.RECORDS,g.ALT_RECORDS)for i in range(c.cap)for x in values(m,base+i*36,RECORD_FIELDS)]),('ro',[x for base in(g.RECORDS,g.ALT_RECORDS)for i in range(c.cap)for x in values(expected,base+i*36,RECORD_FIELDS)])):
   parts.append(arr('v'+str(index)+suffix,vals))
  events=[]
  for t,a in calls:
   role=0 if t==g.SPAWN else 1 if t==g.SOUND else 2 if t==g.NOP else 3+g.TICKS.index(t);events.append('{%du,%du,{%s}}'%(role,len(a),','.join(str(x&0xffffffff)+'u'for x in a)))
  name='v'+str(index)+'events';lines.append('static const Event '+name+'[]={'+(','.join(events)or'{0,0,{0,0}}')+'};');parts.append(name);rows.append('{'+','.join(parts)+'}')
 lines.append('typedef struct{u32 seed,cap,head,mutations,tickResult,tick,dt,result,mark0,mark1,calls;const u32 *oi,*oo,*pi,*po,*ri,*ro;const Event*events;}Vector;');lines.append('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};');(o/'native-vectors.h').write_text('\n'.join(lines)+'\n');return len(rows)
def program():
 declarations=p.MANIFEST['native_base_declarations']+'\n'+p.MANIFEST['declarations'];body=p.MANIFEST['body'].replace('func_15196748(','subject(')
 text='#include <ultra64.h>\n#include "structs.h"\n#include <string.h>\n'+declarations+r'''
typedef struct{u32 role,count,arg[2];}Event;
#include "native-vectors.h"
typedef struct{u8 pad0[0x1c];s16 lifetime;u16 flags;u8 pad20[5],capacity,pad26[6];s8 count,head,tail;u8 first,second,pad31[0x23];EffectPoint15196438 point;u8 pad60[0x34];u8*records,*payload;u8 trailing[4];}Core;
typedef struct{EffectRecord15196748 entries[127];u8 guard[16];}Storage;
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(EffectRecord15196748)==36&&sizeof(EffectPayload15196438)==144&&sizeof(Core)==160,"SDK32 widths");
_Static_assert(__builtin_offsetof(Core,capacity)==0x25&&__builtin_offsetof(Core,count)==0x2c&&__builtin_offsetof(Core,point)==0x54&&__builtin_offsetof(Core,records)==0x94&&__builtin_offsetof(Core,payload)==0x98&&__builtin_offsetof(EffectRecord15196748,lifetime)==28&&__builtin_offsetof(EffectRecord15196748,mark)==31,"SDK32 offsets");
static Core owner __attribute__((aligned(16)));static Storage storage,alternate;static EffectPayload15196438 packet,other;
static u32 marker[2],error,callCount,failedCase,failedReason;static Event events[132];static const Vector*v;
s32 D_800BE9E4;f32 D_800BE9A4;
static void copy(void*d,const void*s,u32 n){u32 k;for(k=0;k<n;k++)((u8*)d)[k]=((const u8*)s)[k];}
static f32 real(u32 bits){f32 f;copy(&f,&bits,4);return f;}
static void set(void*p,u32 value,u32 n){u32 k;for(k=0;k<n;k++)((u8*)p)[k]=(u8)(value>>(8*k));}
static u32 get(const void*p,u32 n){u32 k,value=0;for(k=0;k<n;k++)value|=(u32)((const u8*)p)[k]<<(8*k);return value;}
static u32 norm(u32 value){if(value==(u32)&owner)return '''+hex(g.OWNER)+r''';if(value==(u32)&packet)return '''+hex(g.PAYLOAD)+r''';if(value==(u32)&other)return '''+hex(g.ALT_PAYLOAD)+r''';if(value==(u32)storage.entries)return '''+hex(g.RECORDS)+r''';if(value==(u32)alternate.entries)return '''+hex(g.ALT_RECORDS)+r''';return value;}
static void fill(void*p,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=(u8)(i*19+v->seed*13+0x51);}
static void initialize(void*p,const Field*f,u32 n,const u32*values,u32 kind){u32 i,value;for(i=0;i<n;i++){value=values[i];if(kind==1&&f[i].at==0x94){((Core*)p)->records=(u8*)storage.entries;continue;}if(kind==1&&f[i].at==0x98){((Core*)p)->payload=(u8*)&packet;continue;}if(kind==2&&f[i].at==0){((EffectPayload15196438*)p)->owner=(struct127*)&owner;continue;}set((u8*)p+f[i].at,value,f[i].width);}}
static int compare(const void*p,const Field*f,u32 n,const u32*values,u32 kind){u32 i,value;for(i=0;i<n;i++){value=get((const u8*)p+f[i].at,f[i].width);if((kind==1&&(f[i].at==0x94||f[i].at==0x98))||(kind==2&&f[i].at==0))value=norm(value);if(value!=values[i])return 0;}return 1;}
static int untouched(const void*p,u32 bytes,const Field*f,u32 n,u32 stride,u32 count){u32 i,j,covered;for(i=0;i<bytes;i++){covered=0;if(i/stride<count)for(j=0;j<n;j++)if(f[j].at<=i%stride&&i%stride<f[j].at+f[j].width)covered=1;if(!covered&&((const u8*)p)[i]!=(u8)(i*19+v->seed*13+0x51))return 0;}return 1;}
static void event(u32 role,u32 count,u32 first,u32 second){Event*e;if(callCount>=132){error=1;return;}e=&events[callCount++];e->role=role;e->count=count;e->arg[0]=norm(first);e->arg[1]=second;marker[0]=marker[0]*33+role+1;}
__attribute__((noinline,noclone))void func_15198110(u8*p,s32 index){event(0,2,(u32)p,(u32)index);if(p!=(u8*)&owner||index<0||(u32)index>=v->cap){error=1;return;}marker[1]++;if(v->mutations&1){storage.entries[index].lifetime=(index+3)*5;packet.field58=real(0x3e800000);}if(v->mutations&2){owner.records=(u8*)alternate.entries;owner.payload=(u8*)&other;}if(v->mutations&32){owner.head=index;owner.count=1;D_800BE9A4=real(0xbf000000);D_800BE9E4=3;}}
__attribute__((noinline,noclone))static void sound(struct PointSoundOwner*p){event(1,1,(u32)p,0);if((void*)p!=&owner)error=1;if(v->mutations&4){packet.field68=0;packet.tickCallback=2;storage.entries[v->head].point.axis[0]=real(0x41200000);}}
void(*D_8008F894[1])(struct PointSoundOwner*)={sound};
__attribute__((noinline,noclone))static void nop(s32 p){event(2,1,(u32)p,0);if((u32)p!=(u32)&owner)error=1;if(v->mutations&8){owner.head=v->cap-1;owner.count=1;packet.tickCallback=1;}}
void(*D_8008F89C[1])(s32)={nop};
static s32 tick(u32 role,u8*p){event(role,1,(u32)p,0);if(p!=(u8*)&owner)error=1;if(v->mutations&16){owner.head=v->cap-1;owner.count=v->seed%2?0:1;}return v->tickResult;}
__attribute__((noinline,noclone))static s32 tick0(u8*p){return tick(3,p);}
__attribute__((noinline,noclone))static s32 tick1(u8*p){return tick(4,p);}
__attribute__((noinline,noclone))static s32 tick2(u8*p){return tick(5,p);}
s32(*D_8008F880[3])(u8*)={tick0,tick1,tick2};
'''+body+r'''
static int fail(u32 k,u32 why){failedCase=k;failedReason=why;return 1;}
static int run(void){u32 k,i,j; s32 result;for(k=0;k<sizeof(vectors)/sizeof(vectors[0]);k++){
 v=&vectors[k];error=callCount=marker[0]=marker[1]=0;fill(&owner,sizeof(owner));fill(&packet,sizeof(packet));fill(&other,sizeof(other));fill(&storage,sizeof(storage));fill(&alternate,sizeof(alternate));
 initialize(&owner,ownerFields,''' +str(len(OWNER_FIELDS))+r''',v->oi,1);initialize(&packet,payloadFields,'''+str(len(PAYLOAD_FIELDS))+r''',v->pi,2);initialize(&other,payloadFields,'''+str(len(PAYLOAD_FIELDS))+r''',v->pi+'''+str(len(PAYLOAD_FIELDS))+r''',2);
 for(i=0;i<v->cap;i++){initialize(&storage.entries[i],recordFields,'''+str(len(RECORD_FIELDS))+r''',v->ri+i*'''+str(len(RECORD_FIELDS))+r''',0);initialize(&alternate.entries[i],recordFields,'''+str(len(RECORD_FIELDS))+r''',v->ri+(v->cap+i)*'''+str(len(RECORD_FIELDS))+r''',0);}
 D_800BE9E4=(s32)v->tick;D_800BE9A4=real(v->dt);result=subject((u8*)&owner);
 if(error||(u32)result!=v->result||callCount!=v->calls||marker[0]!=v->mark0||marker[1]!=v->mark1)return fail(k,1);
 for(i=0;i<callCount;i++){if(events[i].role!=v->events[i].role||events[i].count!=v->events[i].count)return fail(k,2);for(j=0;j<events[i].count;j++)if(events[i].arg[j]!=v->events[i].arg[j])return fail(k,3);}
 if(!compare(&owner,ownerFields,'''+str(len(OWNER_FIELDS))+r''',v->oo,1)||!compare(&packet,payloadFields,'''+str(len(PAYLOAD_FIELDS))+r''',v->po,2)||!compare(&other,payloadFields,'''+str(len(PAYLOAD_FIELDS))+r''',v->po+'''+str(len(PAYLOAD_FIELDS))+r''',2))return fail(k,4);
 for(i=0;i<v->cap;i++)if(!compare(&storage.entries[i],recordFields,'''+str(len(RECORD_FIELDS))+r''',v->ro+i*'''+str(len(RECORD_FIELDS))+r''',0)||!compare(&alternate.entries[i],recordFields,'''+str(len(RECORD_FIELDS))+r''',v->ro+(v->cap+i)*'''+str(len(RECORD_FIELDS))+r''',0))return fail(k,5);
 if(!untouched(&owner,sizeof(owner),ownerFields,'''+str(len(OWNER_FIELDS))+r''',sizeof(owner),1)||!untouched(&packet,sizeof(packet),payloadFields,'''+str(len(PAYLOAD_FIELDS))+r''',sizeof(packet),1)||!untouched(&other,sizeof(other),payloadFields,'''+str(len(PAYLOAD_FIELDS))+r''',sizeof(other),1)||!untouched(&storage,sizeof(storage),recordFields,'''+str(len(RECORD_FIELDS))+r''',36,v->cap)||!untouched(&alternate,sizeof(alternate),recordFields,'''+str(len(RECORD_FIELDS))+r''',36,v->cap))return fail(k,6);
 }return 0;}
__attribute__((force_align_arg_pointer))void _start(void){int result=run();u32 report[2];if(result){report[0]=failedCase;report[1]=failedReason;__asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(report),"d"(8):"memory");}__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 return text,body
def main():
 count=vector_header();source,body=program();profiles={}
 def run(s,label,opt):
  f=o/(label+'.c');f.write_text(s);exe=o/(label+opt);q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fmax-errors=1',str(f),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr)[-5000:];return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in('-O0','-O2','-O3'):
  q=run(source,'native',opt);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b''),(opt,q.returncode,struct.unpack('<2I',q.stderr)if len(q.stderr)==8 else q.stderr);profiles[opt]=dict(cases=count,SDK32=True,strict_aliasing=True,UBSan=True)
 changes={'wrong-entry-gate':body.replace('(payload->kind & 1)','(payload->kind & 2)'),'wrong-delay-boundary':body.replace('record->delay > 0','record->delay >= 0'),'wrong-velocity-axis':body.replace('record->velocity[1] += payload->firstScale','record->velocity[0] += payload->firstScale'),'wrong-expiry-boundary':body.replace('if (record->lifetime < 0)','if (record->lifetime <= 0)'),'wrong-forward-count':body.replace('remaining = payload->field8C;','remaining = payload->field8C + 1;'),'wrong-reverse-scale':body.replace('(record->mark * ramp) >> 8','(record->mark * ramp) >> 7'),'wrong-tick-result':body.replace('D_8008F880[payload->tickCallback](owner) == 0','D_8008F880[payload->tickCallback](owner) != 0'),'reloaded-output-records':body.replace('= records[*(s8 *)(owner + 0x2D)].point;','= ((EffectRecord15196748 *)*(u8 **)(owner + 0x94))[*(s8 *)(owner + 0x2D)].point;'),'reloaded-callback-payload':body.replace('    if (payload->field64 != -1) {','    payload = (EffectPayload15196438 *)*(u8 **)(owner + 0x98);\n    if (payload->field64 != -1) {'),'wrong-zero-sign':body.replace('= 0.0f;','= -0.0f;')};effective=[]
 for label,changed in changes.items():
  assert changed!=body,label;q=run(source.replace(body,changed),'control-'+label,'-O2');assert q.returncode==1 and len(q.stderr)==8 and not q.stdout,(label,q.returncode,q.stderr);effective.append(dict(name=label,first_rejected_case=struct.unpack('<2I',q.stderr)))
 q=dict(profiles=profiles,effective_controls=effective,owner_fields=len(OWNER_FIELDS),payload_fields=len(PAYLOAD_FIELDS),record_fields=len(RECORD_FIELDS),initialized_padding_and_array_guards_checked=True,source_installed=p.installed(),matching_credit=0,limits='Valid disjoint typed SDK32 Core, payload and record objects. Public pointer replacement and callback mutations are defined; guest-only partial overlaps and private homes are separate. Providers are bounded, not recovered callee bodies.');(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
