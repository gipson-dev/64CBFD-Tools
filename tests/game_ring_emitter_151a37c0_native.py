"""Native32 execution of the entire recovered C against guest-qualified images."""
from pathlib import Path
import importlib.util,json,subprocess,time
from tools.experiments import game_ring_emitter_151a37c0_recovery as source
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
O=source.OUT;PIN=source.PIN
from tools.tests import game_ring_emitter_151a37c0_oracle as g
PF=[(i,4) for i in(8,12,16,20,32,36,52,56,60,64,72)]+[(i,2) for i in(24,26,28)]
EF=[(24*i+j,n) for i in range(8) for j,n in((0,4),(4,4),(8,4),(12,4),(16,2),(18,2))]
def image(m,base,n,fields):
 b=bytearray(g.data(m,base,n))
 for at,size in fields:b[at:at+size]=b[at:at+size][::-1]
 return b
def corpus():
 valid=[c for c in g.cases() if c.alias==0 and c.rule=='left' and all(getattr(c,k)&0x7F800000!=0x7F800000 for k in('pending','scale','elapsed','value','rate','step'))]
 result=[valid[i*len(valid)//512] for i in range(512)]+[g.Case(cap=3,head=1,tail=2,count=g.s8(v),phase_base=v,phase_range=v,phase_value=v,pending=0x40100000,seed=v) for v in range(256)]
 assert len(result)==768;return result
def make_source():
 rows=[];array=lambda b:'{'+','.join(map(str,b))+'}'
 for c in corpus():
  initial=g.fixture(c);expected,answer,calls,ops=g.reference(c);copied=any(x[0]==g.COPY and x[1][0]=='snapshot-out' for x in calls)
  images=[]
  for memory in(initial,expected):
   fields=[(0x28+at,n) for at,n in PF if at<48] if memory is expected and copied else []
   for base,n,fs in((g.E,156,[(0x10,4),(0x14,4),(0x18,4),(0x1C,2),(0x1E,2)]),(g.P,80,PF),(g.A,192,EF),(g.T,512,[(0,4)]),(g.ALTP,80,PF),(g.ALTA,192,EF),(g.CREATED,128,fields)):
    images.append(array(image(memory,base,n,fs)))
  metadata=(c.cap,c.hit,c.factory,c.motion,c.random,c.qeffects,c.rng_effects,c.factory_effects,c.seed,c.step,g.read(expected,g.TIME),answer,len(calls),int(copied),int(g.read(expected,g.E+0x94)==g.ALTA),int(g.read(expected,g.E+0x98)==g.ALTP))
  callids=[x[0] for x in calls];assert len(callids)<=32;callids+=[0]*(32-len(callids))
  rows.append('{'+','.join('0x%Xu'%v for v in metadata)+','+','.join(images)+','+array(callids)+'}')
 replacement=PIN['replacement'];at=replacement.index('/* Sample linked-owner');types,body=replacement[:at],replacement[at:]
 prefix='''#include <ultra64.h>
typedef struct {f32 x,y,z;} RingPosition151A361C;
typedef struct {u32 words[12];} OwnerSetupDescriptor151A3390;
s32 func_151A4E34(u8 *,void *);void func_151A4E9C(u8 *);void *memcpy(void *,const void *,u32);
__attribute__((noreturn))static void quit(int code){__asm__ volatile(".byte 0xcd,0x80" : : "a"(1),"b"(code):"memory");__builtin_unreachable();}
static void check(int v){if(!v)quit(3);}
static void copyBytes(void *d,const void *s,u32 n){for(u32 i=0;i<n;i++)((volatile u8 *)d)[i]=((const volatile u8 *)s)[i];}
static void setWord(void *p,u32 v){copyBytes(p,&v,4);}
static u32 word(const void *p){u32 v;copyBytes(&v,p,4);return v;}
static f32 number(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
f32 fabsf(f32 x){u32 v=word(&x)&0x7FFFFFFFu;return number(v);}
f32 sqrtf(f32 x){f32 y;__asm__("sqrtss %1,%0":"=x"(y):"x"(x));return y;}
'''+types+'''
f32 D_800A8D58,D_800BE9A4;
typedef struct {u8 pre00[12],variant,pre0D[3];RingPosition151A361C position;u16 timer,flags;u8 pre20[5],capacity,pre26[6],count,head,tail,pre2F[0x65];RingSample151A37C0 *entries;RingPayload151A37C0 *state;} NativeOwner;
typedef struct {u32 cap,hit,create,motion,random,qeffects,rngEffects,factoryEffects,seed,step,finalStep,answer,ncall,copied,altEntries,altState;
 u8 ie[156],ip[80],ia[192],it[512],iap[80],iaa[192],ic[128],fe[156],fp[80],fa[192],ft[512],fap[80],faa[192],fc[128];u32 calls[32];} NativeCase;
static NativeOwner owner;static RingPayload151A37C0 payload,altPayload;static RingSample151A37C0 entries[8],altEntries[8];static u32 actor[128];static u8 createdBuffer[128];
static const NativeCase *current;static u32 ordinal,rngOrdinal;static const void *snapshot;
_Static_assert(sizeof(NativeOwner)==156&&sizeof(RingPayload151A37C0)==80&&sizeof(RingSample151A37C0)==24&&sizeof(OwnerSetupDescriptor151A3390)==48,"native object sizes");
_Static_assert(__builtin_offsetof(NativeOwner,entries)==0x94&&__builtin_offsetof(NativeOwner,state)==0x98&&__builtin_offsetof(NativeOwner,flags)==0x1e&&__builtin_offsetof(RingPayload151A37C0,position)==0x34&&__builtin_offsetof(RingPayload151A37C0,elapsed)==0x48,"native object offsets");
static void call(u32 t){check(ordinal<current->ncall&&current->calls[ordinal]==t);ordinal++;}
s32 func_151A4E34(u8 *p,void *out){
 call(0x151A4E34);check(p==(u8*)&payload&&out==&owner.position);
 if(current->qeffects&1){owner.flags^=8;owner.variant^=0x35;}
 if(current->qeffects&2){owner.entries=altEntries;owner.state=&altPayload;}
 if(current->qeffects&4){payload.value=.75f;payload.rate=-.25f;payload.elapsed=1.5f;payload.pending=2.25f;}
 if(current->qeffects&8)D_800BE9A4=.25f;
 static const f32 point[6][3]={{3,4,0},{0,0,0},{-3,0,-4},{.00001f,0,0},{.0001f,0,0},{0,0,0}};
 if(current->hit==1){copyBytes(out,point[current->motion],12);if(current->motion==5)setWord(out,0x38D1B718u);}
 return current->hit==1;
}
void func_151A4E9C(u8 *p){call(0x151A4E9C);check(p==(u8*)&owner);owner.flags&=0xFFFD;((u8*)&owner)[0x30]=0;owner.state->kind|=1;owner.state->kind|=4;}
void *memcpy(void *d,const void *s,u32 n){
 call(0x10022EC0);check(n==48);
 if(s==&payload){check(snapshot==0);snapshot=d;}
 else check(s==snapshot&&d==createdBuffer+0x28);
 copyBytes(d,s,n);return d;
}
void *func_151491F4(s16 a,s8 b,s8 cc,u8 d,u8 e,s32 f,u8 h,s32 i){
 call(0x151491F4);check(a==300&&b==-1&&cc==10&&d==0&&e==5&&f==48&&h==owner.variant&&i==0);
 if(current->factoryEffects){payload.value=2.f;((u8*)&payload)[7]^=0x5A;payload.phaseBase=17;}
 return current->create?createdBuffer:0;
}
s32 func_150ADA20(void){
 call(0x150ADA20);u32 n=rngOrdinal++;s32 old=(s8)owner.tail;
 if(current->rngEffects&1){payload.phase=255;payload.phaseBase=250;payload.phaseRange=255;}
 if(current->rngEffects&2){owner.head=(owner.head+1)%owner.capacity;owner.count=(current->seed*7+1)&255;owner.tail=(old+1)%owner.capacity;}
 if(current->rngEffects&4){entries[old].position.x=9.f;entries[old].value=-1.25f;}
 if((current->rngEffects&8)&&n==0){payload.pending=1.25f;D_800BE9A4=-.5f;}
 s32 result;copyBytes(&result,&current->random,4);return result;
}
'''
 suffix='''
static const NativeCase cases[]={
'''+',\n'.join(rows)+'''};
static s32(*volatile invoke)(u8*)=func_151A37C0;
static void same(const void *object,const u8 *expected,u32 n,u32 skip,u32 length){for(u32 i=0;i<n;i++)if(i<skip||i>=skip+length)check(((const u8*)object)[i]==expected[i]);}
static int run(void){for(u32 k=0;k<sizeof(cases)/sizeof(cases[0]);k++){
 const NativeCase *c=&cases[k];current=c;ordinal=rngOrdinal=0;snapshot=0;
 copyBytes(&owner,c->ie,156);copyBytes(&payload,c->ip,80);copyBytes(entries,c->ia,192);copyBytes(actor,c->it,512);copyBytes(&altPayload,c->iap,80);copyBytes(altEntries,c->iaa,192);copyBytes(createdBuffer,c->ic,128);
 owner.entries=entries;owner.state=&payload;payload.owner=(u8*)actor;altPayload.owner=(u8*)actor;setWord(&D_800BE9A4,c->step);setWord(&D_800A8D58,0x38D1B717u);
 check((u32)invoke((u8*)&owner)==c->answer);check(ordinal==c->ncall);
 same(&owner,c->fe,156,0x94,8);check(owner.entries==(c->altEntries?altEntries:entries)&&owner.state==(c->altState?&altPayload:&payload));
 same(&payload,c->fp,80,0,4);same(&altPayload,c->fap,80,0,4);check(payload.owner==(u8*)actor&&altPayload.owner==(u8*)actor);
 same(entries,c->fa,192,0,0);same(altEntries,c->faa,192,0,0);same(actor,c->ft,512,0,0);
 same(createdBuffer,c->fc,128,c->copied?0x28:0,c->copied?4:0);if(c->copied)check(word(createdBuffer+0x28)==(u32)actor);
 check(word(&D_800BE9A4)==c->finalStep&&word(&D_800A8D58)==0x38D1B717u);
 }return 0;}
'''
 return prefix,body,suffix
def main():
 prefix,body,suffix=make_source()
 variants={'selected':body,'inline-RNG-operand-order':body.replace('            random = (u32)func_150ADA20();\n','').replace('    u32 random;\n','').replace('random %','(u32)func_150ADA20() %'),'owner-live-gate':body.replace('*(s32 *)state->owner == 0','*(s32 *)state->owner != 0'),
 'identity-gate':body.replace('state->identity != state->owner[0x3B]','state->identity == state->owner[0x3B]'),
 'snapshot-extent':body.replace(', state, 0x30)',', state, 0x2C)'),
 'factory-type':body.replace('(300, -1, 10, 0, 5, 48,','(300, -1, 9, 0, 5, 48,'),
 'elapsed-direction':body.replace('state->elapsed + D_800BE9A4','state->elapsed - D_800BE9A4'),
 'signed-RNG-modulo':body.replace('random % ((u32)state->phaseRange + 1)','(s32)random % ((s32)state->phaseRange + 1)'),
 'ring-head-test':body.replace('owner + 0x2D) == *(s8 *)(owner + 0x2E)','owner + 0x2D) != *(s8 *)(owner + 0x2E)'),
 'pending-decrement':body.replace('state->pending -= 1.0f','state->pending -= 2.0f'),
 'entry-phase':body.replace('entry->phase = state->phase','entry->phase = state->phaseBase'),
 'entry-slot':body.replace('entry = &entries[*(s8 *)(owner + 0x2E)]','entry = &entries[0]'),
 'position-Y-consumed':body.replace('position.y += stepY','position.y += stepX; (void)stepY')}
 results=[]
 for label,fn in variants.items():
  assert label=='selected' or fn!=body,label
  for opt in(('-O0','-O2') if label=='selected' else ('-O2',)):
   path=O/('native-'+label+opt+'.c');exe=path.with_suffix('');path.write_text(prefix+fn+suffix+START);start=time.monotonic()
   q=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=source.ROOT,capture_output=True,text=True)
   assert q.returncode==0 and not q.stderr,(label,q.stdout,q.stderr)
   p=subprocess.run([str(exe)],capture_output=True,timeout=30);assert p.returncode==(0 if label=='selected' else 3),(label,opt,p.returncode)
   row=dict(label=label,opt=opt,exit_code=p.returncode,seconds=round(time.monotonic()-start,3));results.append(row);print(json.dumps(row),flush=True)
 report=dict(cases_per_profile=len(corpus()),native32=True,UB_traps=True,all_count_bytes=True,complete_public_objects_and_48byte_snapshots=True,valid_disjoint_native_storage=True,runs=results,source_installed=False,c_match_credit=0)
 (O/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
