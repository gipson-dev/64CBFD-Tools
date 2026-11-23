"""SDK32 typed owner, actor, payload, record and matrix objects; bounded providers."""
from pathlib import Path
import importlib.util,json,re,struct,subprocess,sys
from tools.experiments import game_actor_ring_emitter_15196b4c_match as p
r=p.ROOT;o=p.OUT
from tools.tests import game_actor_ring_emitter_15196b4c_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
OWNER=[(0x1e,2),(0x25,1),(0x2c,1),(0x2d,1),(0x2e,1),(0x2f,1),(0x30,1)]+[(i,4)for i in(0x10,0x14,0x18,0x94,0x98)]
PAYLOAD=[(0,4),(5,1),(7,1)]+[(i,4)for i in range(8,0x50,4)]+[(0x50,1),(0x53,1),(0x54,1)]+[(i,4)for i in(0x58,0x5c,0x78,0x7c,0x84,0x88)]
RECORD=[(i,4)for i in range(0,28,4)]+[(28,2),(30,1),(31,1),(32,1),(33,1)]
ACTOR=[(0x1d4,4)]
def values(m,base,fields):return[g.read(m,base+a,n)for a,n in fields]
def vectors():
 lines=['typedef struct{u32 at,width;}Field;'];rows=[]
 def arr(name,values):lines.append('static const u32 '+name+'[]={'+','.join(str(v&0xffffffff)+'u'for v in values)+'};');return name
 for name,fields in(('ownerFields',OWNER),('payloadFields',PAYLOAD),('recordFields',RECORD),('actorFields',ACTOR)):lines.append('static const Field '+name+'[]={'+','.join('{%du,%du}'%v for v in fields)+'};')
 for index,c in enumerate(g.cases()):
  m=g.fixture(c);expected,calls,result=g.reference(m,c);parts=[str(v&0xffffffff)+'u'for v in(c.seed,c.cap,c.head,c.tail,c.mutations,c.dt,result,g.read(expected,g.MARK),g.read(expected,g.MARK+4),len(calls),g.read(expected,g.S['D_800BE9A4']))]
  for suffix,vals in(('oi',values(m,g.OWNER,OWNER)),('oo',values(expected,g.OWNER,OWNER)),('pi',[v for base in(g.P,g.ALT_P)for v in values(m,base,PAYLOAD)]),('po',[v for base in(g.P,g.ALT_P)for v in values(expected,base,PAYLOAD)]),('ri',[v for base in(g.RECORDS,g.ALT_RECORDS)for i in range(c.cap)for v in values(m,base+i*36,RECORD)]),('ro',[v for base in(g.RECORDS,g.ALT_RECORDS)for i in range(c.cap)for v in values(expected,base+i*36,RECORD)]),('ai',[v for base in(g.ACTOR,g.ALT_ACTOR)for v in values(m,base,ACTOR)]),('ao',[v for base in(g.ACTOR,g.ALT_ACTOR)for v in values(expected,base,ACTOR)])):
   parts.append(arr('v'+str(index)+suffix,vals))
  events=[]
  for target,args in calls:
   role=g.SCALE.index(target)if target in g.SCALE else 3 if target==g.TRANSFORM else 4 if target==g.FIRST else 5 if target==g.SECOND else 6
   events.append('{%du,%du,{%s}}'%(role,len(args),','.join(str(v&0xffffffff)+'u'for v in args)or'0'))
  name='v'+str(index)+'events';lines.append('static const Event '+name+'[]={'+(','.join(events)or'{0,0,{0}}')+'};');parts.append(name);rows.append('{'+','.join(parts)+'}')
 lines.append('typedef struct{u32 seed,cap,head,tail,mutations,dt,result,mark0,mark1,calls,finalDt;const u32*oi,*oo,*pi,*po,*ri,*ro,*ai,*ao;const Event*events;}Vector;');lines.append('static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};');(o/'native-vectors.h').write_text('\n'.join(lines)+'\n');return len(rows)
def program():
 source=(o/'baseline/conker/src/game/generated_1C2C60.c').read_text();types=[]
 for name in('EffectPoint15196438','EffectPayload15196438','EffectRecord15196748'):
  match=re.search(r'typedef struct\s*\{[^{}]*\}\s*'+name+r';',source);assert match,name;types.append(match[0])
 body=(o/'selected-final/body.c').read_text().replace('func_15196B4C(','subject(')
 text='#include <ultra64.h>\n#include "structs.h"\n'+''.join(types)+r'''
typedef struct{u32 role,count,arg[3];}Event;
#include "native-vectors.h"
typedef struct{u8 pad0[16];EffectPoint15196438 position;s16 lifetime;u16 flags;u8 pad20[5],capacity,pad26[6];s8 count,head,tail;u8 first,second,pad31[0x23];EffectPoint15196438 point;u8 pad60[0x34];u8*records,*payload;u8 trailing[4];}Core;
typedef struct{EffectRecord15196748 entries[127];u8 guard[16];}Storage;
typedef struct{f32 translation[3];u8 gap[52];}Matrix;
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(Core)==160&&sizeof(EffectPayload15196438)==144&&sizeof(EffectRecord15196748)==36&&sizeof(Matrix)==64,"SDK32 widths");
_Static_assert(__builtin_offsetof(Core,position)==16&&__builtin_offsetof(Core,capacity)==0x25&&__builtin_offsetof(Core,count)==0x2c&&__builtin_offsetof(Core,records)==0x94&&__builtin_offsetof(Core,payload)==0x98&&__builtin_offsetof(struct127,unk1D4)==0x1d4,"SDK32 offsets");
static Core owner __attribute__((aligned(16)));static Storage storage,alternate;static EffectPayload15196438 packet,other;static struct127 actor,otherActor;static Matrix matrices[256],otherMatrices[256],originalMatrices[512];static f32*world;
static const Vector*v;static u32 marker[2],error,callCount,ordinals[7],failedCase,failedReason;static Event events[256];f32 D_800BE9A4;
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static int equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static f32 real(u32 bits){f32 f;copy(&f,&bits,4);return f;}
static void set(void*p,u32 value,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=(u8)(value>>(8*i));}
static u32 get(const void*p,u32 n){u32 i,value=0;for(i=0;i<n;i++)value|=(u32)((const u8*)p)[i]<<(8*i);return value;}
static u32 norm(u32 x){u32 start;
''' + ''.join('start=(u32)'+n+';if(start<=x&&x<start+'+size+')return '+hex(base)+'u+x-start;\n'for n,size,base in(('&owner','sizeof(owner)',g.OWNER),('&packet','sizeof(packet)',g.P),('&other','sizeof(other)',g.ALT_P),('storage.entries','sizeof(storage.entries)',g.RECORDS),('alternate.entries','sizeof(alternate.entries)',g.ALT_RECORDS),('&actor','sizeof(actor)',g.ACTOR),('&otherActor','sizeof(otherActor)',g.ALT_ACTOR),('matrices','sizeof(matrices)',g.MATRIX),('otherMatrices','sizeof(otherMatrices)',g.ALT_MATRIX)))+r'''
if(world&&x==(u32)world)return '''+hex(g.WORLD)+r'''u;return x;}
static void fill(void*p,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=(u8)(i*19+v->seed*13+0x51);}
static void initialize(void*p,const Field*f,u32 n,const u32*values,u32 kind){u32 i,x;for(i=0;i<n;i++){x=values[i];if(kind==1&&f[i].at==0x94){((Core*)p)->records=(u8*)storage.entries;continue;}if(kind==1&&f[i].at==0x98){((Core*)p)->payload=(u8*)&packet;continue;}if(kind==2&&f[i].at==0){((EffectPayload15196438*)p)->owner=x=='''+hex(g.ACTOR)+r'''u?&actor:&otherActor;continue;}if(kind==3){((struct127*)p)->unk1D4=x==0?0:x=='''+hex(g.MATRIX)+r'''u?(void*)matrices:(void*)otherMatrices;continue;}set((u8*)p+f[i].at,x,f[i].width);}}
static int compare(const void*p,const Field*f,u32 n,const u32*values,u32 kind){u32 i,x;for(i=0;i<n;i++){x=get((const u8*)p+f[i].at,f[i].width);if((kind==1&&(f[i].at==0x94||f[i].at==0x98))||(kind==2&&f[i].at==0)||kind==3)x=norm(x);if(x!=values[i])return 0;}return 1;}
static int untouched(const void*p,u32 bytes,const Field*f,u32 n,u32 stride,u32 count){u32 i,j,covered;for(i=0;i<bytes;i++){covered=0;if(i/stride<count)for(j=0;j<n;j++)if(f[j].at<=i%stride&&i%stride<f[j].at+f[j].width)covered=1;if(!covered&&((const u8*)p)[i]!=(u8)(i*19+v->seed*13+0x51))return 0;}return 1;}
static u32 event(u32 role,u32 count,u32 a,u32 b,u32 c){u32 ordinal=ordinals[role]++;Event*e;if(callCount>=256){error=1;return ordinal;}e=&events[callCount++];e->role=role;e->count=count;e->arg[0]=norm(a);e->arg[1]=norm(b);e->arg[2]=norm(c);marker[0]=marker[0]*33+role+1;marker[1]++;return ordinal;}
static f32 scale(u32 role,s32 p){event(role,1,(u32)p,0,0);if((u32)p!=(u32)&owner)error=1;if(v->mutations&1){packet.owner=&otherActor;packet.matrixIndex=255;D_800BE9A4=real(0x3f400000);}return((s32)(v->seed%9)-4)*0.25f;}
__attribute__((noinline,noclone))static f32 scale0(s32 p){return scale(0,p);}
__attribute__((noinline,noclone))static f32 scale1(s32 p){return scale(1,p);}
__attribute__((noinline,noclone))static f32 scale2(s32 p){return scale(2,p);}
f32(*D_8008F870[3])(s32)={scale0,scale1,scale2};
__attribute__((noinline,noclone))void func_15143134(f32*input,f32*output,u8*matrix){u32 n=ordinals[3],i;f32 point[3];if(n==1)world=output;event(3,3,(u32)input,(u32)output,(u32)matrix);if(n>1){error=1;return;}for(i=0;i<3;i++)point[i]=input[i]+((f32*)matrix)[i];for(i=0;i<3;i++)output[i]=point[i];if(n==0&&(v->mutations&2)){owner.records=(u8*)alternate.entries;owner.payload=(u8*)&other;packet.owner->unk1D4=(void*)otherMatrices;packet.localEnd.axis[0]=7.0f;packet.matrixIndex^=1;}}
static void child(u32 role,u8*p,f32*point){u32 n=event(role,2,(u32)p,(u32)point,0);if(p!=(u8*)&owner||point!=world){error=1;return;}if(v->mutations&4){point[0]=2.0f+n;packet.field53=(u8)(211+n);packet.field54=(u8)(133+n);packet.firstScale=-0.5f;owner.records=(u8*)alternate.entries;owner.payload=(u8*)&other;}if((v->mutations&8)&&n==0){if(role==4){packet.field88=2.0f;packet.field84=0.25f;}else{owner.tail=(v->tail+1)%v->cap;owner.head=(v->head+1)%v->cap;owner.count=v->cap-1;}}}
__attribute__((noinline,noclone))void func_15198D88(u8*p,f32*point){child(4,p,point);}
__attribute__((noinline,noclone))void func_151990AC(u8*p,f32*point){child(5,p,point);}
__attribute__((noinline,noclone))s32 func_150ADA20(void){static const u32 choices[6]={0,5,6,0x7fffffff,0x80000000,0xffffffff};u32 n=event(6,0,0,0,0);if(v->mutations&16){packet.field50=(u8)(27+n*39);packet.firstScale=0.25f*(n+1);owner.tail=(v->tail+n+1)%v->cap;owner.head=(v->head+n)%v->cap;owner.count=v->cap-1;}if((v->mutations&32)&&n==0){packet.field4C=0.5f;D_800BE9A4=-0.5f;}return(s32)choices[(v->seed+n)%6];}
'''+body+r'''
static int fail(u32 k,u32 why){failedCase=k;failedReason=why;return 1;}
static int run(void){u32 k,i,j; s32 answer;for(k=0;k<sizeof(vectors)/sizeof(vectors[0]);k++){
v=&vectors[k];error=callCount=marker[0]=marker[1]=0;world=0;for(i=0;i<7;i++)ordinals[i]=0;
fill(&owner,sizeof(owner));fill(&packet,sizeof(packet));fill(&other,sizeof(other));fill(&storage,sizeof(storage));fill(&alternate,sizeof(alternate));fill(&actor,sizeof(actor));fill(&otherActor,sizeof(otherActor));fill(matrices,sizeof(matrices));fill(otherMatrices,sizeof(otherMatrices));
initialize(&owner,ownerFields,'''+str(len(OWNER))+r''',v->oi,1);initialize(&packet,payloadFields,'''+str(len(PAYLOAD))+r''',v->pi,2);initialize(&other,payloadFields,'''+str(len(PAYLOAD))+r''',v->pi+'''+str(len(PAYLOAD))+r''',2);initialize(&actor,actorFields,1,v->ai,3);initialize(&otherActor,actorFields,1,v->ai+1,3);
for(i=0;i<v->cap;i++){initialize(&storage.entries[i],recordFields,'''+str(len(RECORD))+r''',v->ri+i*'''+str(len(RECORD))+r''',0);initialize(&alternate.entries[i],recordFields,'''+str(len(RECORD))+r''',v->ri+(v->cap+i)*'''+str(len(RECORD))+r''',0);}
for(i=0;i<256;i++)for(j=0;j<3;j++){matrices[i].translation[j]=(i+j+v->seed%7)*0.125f;otherMatrices[i].translation[j]=matrices[i].translation[j]+10.0f;}
copy(originalMatrices,matrices,sizeof(matrices));copy(originalMatrices+256,otherMatrices,sizeof(otherMatrices));D_800BE9A4=real(v->dt);answer=subject((u8*)&owner);
if(error||(u32)answer!=v->result||callCount!=v->calls||marker[0]!=v->mark0||marker[1]!=v->mark1||get(&D_800BE9A4,4)!=v->finalDt)return fail(k,1);
for(i=0;i<callCount;i++){if(events[i].role!=v->events[i].role||events[i].count!=v->events[i].count)return fail(k,2);for(j=0;j<events[i].count;j++)if(events[i].arg[j]!=v->events[i].arg[j])return fail(k,3);}
if(!compare(&owner,ownerFields,'''+str(len(OWNER))+r''',v->oo,1)||!compare(&packet,payloadFields,'''+str(len(PAYLOAD))+r''',v->po,2)||!compare(&other,payloadFields,'''+str(len(PAYLOAD))+r''',v->po+'''+str(len(PAYLOAD))+r''',2)||!compare(&actor,actorFields,1,v->ao,3)||!compare(&otherActor,actorFields,1,v->ao+1,3))return fail(k,4);
for(i=0;i<v->cap;i++)if(!compare(&storage.entries[i],recordFields,'''+str(len(RECORD))+r''',v->ro+i*'''+str(len(RECORD))+r''',0)||!compare(&alternate.entries[i],recordFields,'''+str(len(RECORD))+r''',v->ro+(v->cap+i)*'''+str(len(RECORD))+r''',0))return fail(k,5);
if(!untouched(&owner,sizeof(owner),ownerFields,'''+str(len(OWNER))+r''',sizeof(owner),1)||!untouched(&packet,sizeof(packet),payloadFields,'''+str(len(PAYLOAD))+r''',sizeof(packet),1)||!untouched(&other,sizeof(other),payloadFields,'''+str(len(PAYLOAD))+r''',sizeof(other),1)||!untouched(&actor,sizeof(actor),actorFields,1,sizeof(actor),1)||!untouched(&otherActor,sizeof(otherActor),actorFields,1,sizeof(otherActor),1)||!untouched(&storage,sizeof(storage),recordFields,'''+str(len(RECORD))+r''',36,v->cap)||!untouched(&alternate,sizeof(alternate),recordFields,'''+str(len(RECORD))+r''',36,v->cap)||!equal(originalMatrices,matrices,sizeof(matrices))||!equal(originalMatrices+256,otherMatrices,sizeof(otherMatrices)))return fail(k,6);
}return 0;}
__attribute__((force_align_arg_pointer))void _start(void){int result=run();u32 report[2];if(result){report[0]=failedCase;report[1]=failedReason;__asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(report),"d"(8):"memory");}__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 return text,body
def main():
 count=vectors();source,body=program();profiles={}
 def run(text,label,opt):
  path=o/(label+'.c');out=o/label;path.write_text(text);q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fmax-errors=1',str(path),'-o',str(out)],cwd=r,capture_output=True);(o/(label+'-compile.txt')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode();q=subprocess.run([str(out)],capture_output=True,timeout=60);assert b'runtime error:'not in q.stderr,(label,q.stderr);return q
 for opt in('-O0','-O2','-O3'):
  q=run(source,'native-'+opt[1:],opt);assert q.returncode==0,(opt,q.stdout,q.stderr);profiles[opt]=dict(cases=count,SDK32=True,strict_aliasing=True,UBSan=True)
 controls=[('wrong-matrix-gate','return 0;','return 1;'),('wrong-phase-boundary','if (payload->field4C > 1.0f)','if (payload->field4C >= 1.0f)'),('wrong-random-modulus','random % 6U','random % 5U'),('reselected-matrix','func_15143134(payload->localEnd.axis, transformedEnd.axis, matrix);','func_15143134(payload->localEnd.axis, transformedEnd.axis, (u8 *)payload->owner->unk1D4 + payload->matrixIndex * 64);'),('reloaded-payload','func_15143134(payload->localEnd.axis, transformedEnd.axis, matrix);','payload = (EffectPayload15196438 *)*(u8 **)(owner + 0x98);\n    func_15143134(payload->localEnd.axis, transformedEnd.axis, matrix);'),('reloaded-records','random = (u32)func_150ADA20();','random = (u32)func_150ADA20();\n            records = (EffectRecord15196748 *)*(u8 **)(owner + 0x94);'),('wrong-gravity-axis','record->velocity[1] +=','record->velocity[0] +='),('signed-duration','lifetime = payload->field53','lifetime = (s8)payload->field53'),('wrong-head-advance','owner[0x2D] = head + 1','owner[0x2D] = head + 2'),('reloaded-final-payload','        *previousPoint = point;','        payload = (EffectPayload15196438 *)*(u8 **)(owner + 0x98);\n        *previousPoint = point;')];failures=[]
 for label,old,new in controls:
  assert body.count(old)==1,(label,body.count(old));changed=source.replace(body,body.replace(old,new));assert changed!=source;q=run(changed,'control-'+label,'-O2');assert q.returncode!=0 and len(q.stderr)==8,(label,q.returncode,q.stderr);failures.append(dict(name=label,first_rejected_case=list(struct.unpack('<2I',q.stderr))))
 q=dict(profiles=profiles,effective_controls=failures,owner_fields=len(OWNER),payload_fields=len(PAYLOAD),record_fields=len(RECORD),actual_actor_SDK_layout=True,initialized_padding_records_guards_matrices_checked=True,source_installed=p.installed(),matching_credit=0,limits='Valid disjoint typed SDK32 objects and bounded providers. Guest-only aliases, raw fault/private/FCSR state and hardware acceptance are separate.');(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
