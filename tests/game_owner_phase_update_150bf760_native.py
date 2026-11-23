"""Actual SDK32 parent and return relay checked against independent vectors."""
import hashlib,json,subprocess
from tools.experiments import game_owner_phase_update_150bf760_match as packet
from tools.tests import game_owner_phase_update_150bf760_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
r,o=packet.ROOT,packet.OUT
def vectors():
 roles={g.S[n]:i for i,n in enumerate(('func_1511B51C','func_15195FB0','func_15195DD4','func_15083E90','func_15083E0C','func_150825C0','func_15060F28','sinf'))};rows=[];excluded=0
 for c in g.cases():
  initial=g.fixture(c);want,calls,fault=g.reference(initial,c)
  if fault or c.zero_page:excluded+=1;continue
  inputs=[c.phase,c.numerator,c.duration,c.present,c.created,c.handle,c.state,c.mutation,c.gate,c.index,c.sine,c.result,c.seed]
  expected=[g.read(want,c.owner+0x1C),want[c.owner+0x73],g.read(want,c.owner+0x124),g.read(want,c.owner+0xA8),want[g.OBJECT+0x232],g.read(want,g.OBJECT+0x218),want[g.TABLE+c.index*48+2],g.read(want,g.S['D_800902B8'])]
  marks=[g.read(want,g.MARK+4*i)for i in range(5)];events=[]
  for target,args in calls:
   values=[0xABC00001 if v==c.owner else 0xABC00002 if v==g.OBJECT else v for v in args];events.append('{'+str(roles[target])+'u,'+str(len(args))+'u,{'+','.join(str(v&0xFFFFFFFF)+'u'for v in[*values,*([0]*(7-len(values)))])+'}}')
  assert len(events)<=8
  rows.append('{'+','.join(str(v&0xFFFFFFFF)+'u'for v in inputs+expected)+',{'+','.join(str(v)+'u'for v in marks)+'},'+str(len(events))+'u,{'+','.join(events or['{0u,0u,{0u,0u,0u,0u,0u,0u,0u}}'])+'}}')
 header='static const Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n';(o/'native-vectors.h').write_text(header);return len(rows),excluded
def controls(body,relay):
 call='    func_1511B51C(owner);\n';phase='    phase = owner[0x73] & 3;\n';assert call in body and phase in body
 changed={
 'cached-phase':(body.replace(phase,'').replace(call,phase+call),relay),
 'wrong-gate':(body.replace('D_800C35EA == 1 && D_800C35E8 != 1','D_800C35EA == 1 || D_800C35E8 != 1'),relay),
 'wrong-ratio':(body.replace('0x18) - 2.0f','0x18) - 1.0f'),relay),
 'wrong-curve-factor':(body.replace('progress * D_800A0124 * D_800A0128','progress * D_800A012C * D_800A0128'),relay),
 'wrong-object-id':(body.replace('func_15083E90(20)','func_15083E90(19)'),relay),
 'repaired-final-null-test':(body.replace('object == NULL && object[0x232] != 3','object != NULL && object[0x232] != 3'),relay),
 'wrong-counter-reset':(body.replace('*(s32 *)(object + 0x218) = 0;','*(s32 *)(object + 0x218) = 1;',1),relay),
 'discarded-relay-result':(body,relay.replace('    return func_15195DD4(','    func_15195DD4(').replace('\n}', '\n    return 0;\n}')),
 'narrowed-relay-result':(body,relay.replace('    return func_15195DD4(','    return (u8)func_15195DD4(')),
 'wrong-relay-bank':(body,relay.replace('arg0 + 0x1C','arg0 + 0x124'))}
 assert all(a!=body or b!=relay for a,b in changed.values());return changed
def program():
 body=(o/'selected-final/body.c').read_text().replace('func_150BF760(','subject(');relay=packet.MANIFEST['provider_body'].replace('func_15195FB0(','actual_relay(');decl=(o/'selected-final/declarations.c').read_text()
 src='#include <ultra64.h>\n'+decl+r'''
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(s32)==4&&sizeof(PhaseResourceEC420)==48,"SDK32 layouts");
typedef struct {u8 prefix[0x1c];s32 bank;u8 gap20[0x53];u8 phase;u8 gap74[0x34];f32 offset;u8 gapac[0x78];s32 handle;u8 tail[0x58];} NativeOwner;
typedef struct {u8 pre[8];f32 numerator;u8 mid[12];f32 duration;} NativeAnimation;
typedef struct {u8 pre[0x218];s32 counter;u8 middle[0x16];u8 state;u8 tail[0x9d];u8 *animation;} NativeObject;
_Static_assert(sizeof(NativeOwner)==0x180&&__builtin_offsetof(NativeOwner,phase)==0x73&&__builtin_offsetof(NativeOwner,offset)==0xa8&&__builtin_offsetof(NativeOwner,handle)==0x124,"Owner view");
_Static_assert(__builtin_offsetof(NativeObject,state)==0x232&&__builtin_offsetof(NativeObject,animation)==0x2d0,"Object view");
typedef struct {u32 role,n,arg[7];} Event;
typedef struct {u32 phase,numerator,duration,present,created,handle,state,mutation,gate,index,sine,result,seed;u32 wantBank,wantPhase,wantHandle,wantOffset,wantState,wantCounter,wantField02,wantCode;u32 marks[5],calls;Event events[8];} Vector;
#include "native-vectors.h"
static struct {u32 pre[4];NativeOwner owner;u32 post[4];} region;
static NativeOwner expectedOwner;
static NativeAnimation animation;
static NativeObject object,expectedObject;
static PhaseResourceEC420 resources[7],expectedResources[7];
static Event events[16];static u32 count,lookups,marks[5],overflow;
static const Vector *current;
u8 D_800C35EA,D_800C35E8;s32 D_800902B8;PhaseResourceEC420 *D_800D20FC;
f32 D_800A0124,D_800A0128,D_800A012C,D_800A0130;
static u32 bits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static int sameFloat(u32 a,u32 b){return a==b||((a&0x7fffffff)>0x7f800000&&(b&0x7fffffff)>0x7f800000);}
static void copy(void *d,const void *s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static int equal(const void *a,const void *b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static u32 normalized(u32 a){return a==(u32)&region.owner?0xabc00001u:a==(u32)&object?0xabc00002u:a;}
static void event(u32 role,u32 n,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f,u32 g){Event *p;if(count==16){overflow=1;return;}p=&events[count++];p->role=role;p->n=n;p->arg[0]=normalized(a);p->arg[1]=normalized(b);p->arg[2]=normalized(c);p->arg[3]=normalized(d);p->arg[4]=normalized(e);p->arg[5]=normalized(f);p->arg[6]=normalized(g);}
__attribute__((noinline,noclone)) void func_1511B51C(u8 *owner){event(0,1,(u32)owner,0,0,0,0,0,0);marks[0]=0x13570000;
 if(current->mutation){region.owner.phase^=1;region.owner.handle=0;region.owner.bank=(s32)(0xabcd0000u|(current->seed&65535));D_800902B8=0x76543210;}
}
__attribute__((noinline,noclone)) s32 func_15195DD4(s32 bank,s32 code,s32 a,s32 b,s32 c,s32 d,s32 e){event(2,7,bank,code,a,b,c,d,e);marks[2]=0x13570002;return(s32)current->result;}
'''+relay+r'''
__attribute__((noinline,noclone)) s32 func_15195FB0(u8 *owner,s32 code,s32 a,s32 b,s32 c,s32 d,s32 e){event(1,7,(u32)owner,code,a,b,c,d,e);return actual_relay(owner,code,a,b,c,d,e);}
__attribute__((noinline,noclone)) u8 *func_15083E90(u8 id){u32 present=lookups++?current->created:current->present;event(3,1,id,0,0,0,0,0,0);return present?(u8*)&object:0;}
__attribute__((noinline,noclone)) s32 func_15083E0C(u8 id){event(4,1,id,0,0,0,0,0,0);return(s32)current->index;}
__attribute__((noinline,noclone)) s32 func_150825C0(s32 index,s32 mode){event(5,2,index,mode,0,0,0,0,0);marks[3]=0x13570003;return 0x12345678;}
__attribute__((noinline,noclone)) void func_15060F28(u8 *p,s32 mode){event(6,2,(u32)p,mode,0,0,0,0,0);marks[4]=0x13570004;}
__attribute__((noinline,noclone)) f32 sinf(f32 arg){event(7,1,bits(arg),0,0,0,0,0,0);marks[1]=0x13570001;if(current->mutation)object.state^=3;return real(current->sine);}
'''+body+r'''
static int run(void){u32 i,j,k,n;const Vector *v;
 for(k=0;k<sizeof(vectors)/sizeof(vectors[0]);k++){
  current=v=&vectors[k];count=lookups=overflow=0;
  for(i=0;i<sizeof(region.owner);i++)((u8*)&region.owner)[i]=(i*17+v->seed*13+0xa5)&255;
  for(i=0;i<sizeof(object);i++)((u8*)&object)[i]=(i*29+v->seed*11+0x51)&255;
  for(i=0;i<sizeof(resources);i++)((u8*)resources)[i]=(i*29+v->seed*11+0x51)&255;
  for(i=0;i<5;i++){marks[i]=0;for(j=0;j<4;j++)marks[i]=(marks[i]<<8)|(((i*4+j)*29+v->seed*11+0x51)&255);}
  region.owner.bank=(s32)(0x63000000u+v->seed);region.owner.phase=(v->seed*4&0xfc)|v->phase;region.owner.handle=v->handle;region.owner.offset=real(0x42c60000);
  animation.numerator=real(v->numerator);animation.duration=real(v->duration);object.animation=(u8*)&animation;object.state=v->state;object.counter=(s32)0x87654321u;
  D_800902B8=0x12345678;D_800D20FC=&resources[2];D_800C35EA=v->gate==1||v->gate==2?1:v->gate==3?2:0;D_800C35E8=v->gate==2?1:v->gate==3?255:0;
  CONSTANT_ASSIGNMENTS
  copy(&expectedOwner,&region.owner,sizeof(expectedOwner));copy(&expectedObject,&object,sizeof(object));copy(expectedResources,resources,sizeof(resources));
  expectedOwner.bank=v->wantBank;expectedOwner.phase=v->wantPhase;expectedOwner.handle=v->wantHandle;expectedOwner.offset=real(v->wantOffset);expectedObject.state=v->wantState;expectedObject.counter=v->wantCounter;expectedResources[2+(s32)v->index].field02=v->wantField02;
  for(n=0;n<4;n++){region.pre[n]=0x13570000u+n;region.post[n]=0x24680000u+n;}
  subject((u8*)&region.owner);
  if(overflow||count!=v->calls||D_800902B8!=(s32)v->wantCode||!sameFloat(bits(region.owner.offset),v->wantOffset))return 1;
  expectedOwner.offset=real(bits(region.owner.offset));
  if(!equal(&region.owner,&expectedOwner,sizeof(expectedOwner))||!equal(&object,&expectedObject,sizeof(object))||!equal(resources,expectedResources,sizeof(resources)))return 1;
  for(i=0;i<5;i++)if(marks[i]!=v->marks[i])return 1;
  for(i=0;i<count;i++){if(events[i].role!=v->events[i].role||events[i].n!=v->events[i].n)return 1;for(j=0;j<events[i].n;j++)if(events[i].role==7?(j!=0||!sameFloat(events[i].arg[j],v->events[i].arg[j])):events[i].arg[j]!=v->events[i].arg[j])return 1;}
  for(n=0;n<4;n++)if(region.pre[n]!=0x13570000u+n||region.post[n]!=0x24680000u+n)return 1;
 }
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 src=src.replace('CONSTANT_ASSIGNMENTS',';'.join(n+'=real('+hex(v)+'u)'for n,v in packet.MANIFEST['constants'].items())+';');return src,body,relay
def main():
 cases,excluded=vectors();src,body,relay=program();profiles={}
 def run(text,label,opt):
  p=o/(label+'.c');p.write_text(text);exe=o/(label+opt);q=subprocess.run(native_command(opt)+['-msse2','-mfpmath=sse','-fexcess-precision=standard','-ffp-contract=off','-fstrict-aliasing','-fmax-errors=1',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr)[-5000:]
  return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in('-O0','-O2','-O3'):
  q=run(src,'native',opt);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b''),(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=cases,SDK32=True,UBSan=True,strict_aliasing=True,independent_vector_fields_and_events=True,actual_parent_and_return_relay_C=True)
 effective=[]
 for label,(changed,changed_relay)in controls((o/'selected-final/body.c').read_text(),packet.MANIFEST['provider_body']).items():
  q=run(src.replace(body,changed.replace('func_150BF760(','subject(')).replace(relay,changed_relay.replace('func_15195FB0(','actual_relay(')),'control-'+label,'-O2');assert q.returncode==1,(label,q.returncode,q.stderr);effective.append(label)
 report=dict(profiles=profiles,effective_output_comparison_controls=effective,excluded_guest_fault_or_zero_page_cases=excluded,vectors_sha256=hashlib.sha256((o/'native-vectors.h').read_bytes()).hexdigest(),source_installed=packet.installed(),matching_credit=0,limits='Complete raw SDK32 parent and corrected relay on valid ordinary native buffers. Guest-only owner-home aliases and null/mapped-zero cases are excluded. Arithmetic NaNs compare by class; FCSR, sine/service internals and gameplay are not qualified.');(o/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
