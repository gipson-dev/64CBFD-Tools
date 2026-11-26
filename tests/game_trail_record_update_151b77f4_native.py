"""Actual target and both callback bodies, compatible cross-TU types, Native32."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_trail_record_update_151b77f4_match as target_packet
o=target_packet.OUT
def main():
 source=(o/'selected-owner.c').read_text()
 def body(fn):a,z=function_span(source,fn);return source[a:z]
 target=body('func_151B77F4');callbacks='\n'.join(body(fn)for fn in('func_151B7678','func_151B76CC'))
 vector=source[source.index('typedef struct {'):source.index('} ActorPosition151B6320;')+len('} ActorPosition151B6320;')]
 start=source.index('typedef struct {\n    ActorPosition151B6320 position;\n    f32 distance;');end=source.index('/* Both table entries',start)
 matrix=source[source.index('typedef struct { u8 reserved00[0x18];'):source.index('/* Transform a local offset')]
 header='typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;typedef float f32;\n#define NULL ((void*)0)\n'+vector+'\n'+source[start:end]+matrix+'\ns32 func_151B7678(void *,void *);s32 func_151B76CC(void *,void *);s32 func_151B77F4(TrailOwner151B77F4 *);\n'
 header+='typedef char Layout[sizeof(void*)==4&&sizeof(TrailOwner151B77F4)==156&&sizeof(TrailAux151B77F4)==12&&sizeof(TrailRecord151B77F4)==20&&sizeof(TrailAttached151B77F4)==76&&__builtin_offsetof(TrailOwner151B77F4,records)==148&&__builtin_offsetof(TrailOwner151B77F4,aux)==152?1:-1];\n'
 (o/'native-shared.h').write_text(header);(o/'native-callbacks.c').write_text('#include "native-shared.h"\n'+callbacks+'\ns32 (*D_8008FB90[])(void *,void *)={func_151B7678,func_151B76CC};\n')
 harness=r'''
typedef struct{u32 live;u8 pad04[16];f32 x,y,z;u8 pad20[27];u8 identity;u8 pad3C[4];}Actor;
typedef struct{u32 before[4];TrailOwner151B77F4 owner;u32 after[4];}OwnerArena;
typedef struct{u32 before[4];TrailRecord151B77F4 items[8];u32 after[4];}RecordArena;
typedef struct{u32 before[4];TrailAttached151B77F4 object;u32 after[4];}AttachedArena;
typedef struct{OwnerArena arena;RecordArena records[2];TrailAux151B77F4 aux[2];AttachedArena attached[2];Actor actor;TrailInputLink151B7678 input;MatrixSource151B76CC source;MatrixLink151B76CC link;}Data;
static Data data;static u32 row,mode,calls,initialCSR,selector;static f32 distanceValue;s32 D_800BE9E4;
typedef struct{u32 kind,args[16],CSR;Data data;s32 delta;}Observation;
typedef struct{Observation before[3];Data data;u32 calls,result,CSR;s32 delta;}Capture;
static Capture current,actual;
static void copy(void*d,const void*s,u32 n){u8*a=d;const u8*b=s;u32 i;for(i=0;i<n;i++)a[i]=b[i];}
static u32 equal(const void*a,const void*b,u32 n){const u8*x=a,*y=b;u32 i;for(i=0;i<n;i++)if(x[i]!=y[i])return 0;return 1;}
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}static f32 value(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v));return v;}static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v));}
static Observation*observe(u32 kind){Observation*p=&current.before[calls++];p->kind=kind;p->CSR=csr();p->data=data;p->delta=D_800BE9E4;return p;}
static void callbackEffect(void){
 if(mode&1)data.aux[0].attached=data.aux[0].attached?NULL:&data.attached[1].object;
 if(mode&2){data.arena.owner.aux=&data.aux[1];data.arena.owner.records=data.records[1].items;}
 if(mode&4){data.arena.owner.head=2;data.arena.owner.tail=3;data.arena.owner.count=127;}
 data.source.scaleX=-.5f;data.source.scaleY=1.25f;data.source.translation[0]=7.125f;
 setCSR(initialCSR|1u);
}
__attribute__((noinline,noclone))void func_150A8050(f32 m[4][4],f32 x,f32 y,f32 z){u32 i,j;Observation*p=observe(1);p->args[0]=word(x);p->args[1]=word(y);p->args[2]=word(z);for(i=0;i<4;i++)for(j=0;j<4;j++)m[i][j]=(f32)((s32)(i*4+j)-5)*.125f;callbackEffect();}
__attribute__((noinline,noclone))void func_150A7960(f32 m[4][4],f32 x,f32 y,f32 z,f32*ox,f32*oy,f32*oz){u32 i,j;Observation*p=observe(2);for(i=0;i<4;i++)for(j=0;j<4;j++)p->args[4*i+j]=word(m[i][j]);if(word(x)!=0||word(y)!=0||word(z)!=word(-250.f)||ox!=&data.arena.owner.position.x||oy!=&data.arena.owner.position.y||oz!=&data.arena.owner.position.z)__builtin_trap();*ox=m[3][0]+x;*oy=m[3][1]+y;*oz=m[3][2]+z;setCSR(initialCSR|2u);}
__attribute__((noinline,noclone))f32 func_15143E64(f32*d){Observation*p=observe(3);u32 i;for(i=0;i<3;i++)p->args[i]=word(d[i]);
 if(mode&8){data.arena.owner.position.x=-7.125f;data.arena.owner.position.y=8.25f;data.arena.owner.position.z=-9.5f;}
 if(mode&16){data.arena.owner.aux=&data.aux[1];data.arena.owner.records=data.records[1].items;}
 if(mode&32){data.arena.owner.head=3;data.arena.owner.tail=0;data.arena.owner.count=-1;}
 setCSR(initialCSR|4u);return distanceValue;
}
static s32 callbackReference(TrailOwner151B77F4*p,ActorPosition151B6320*out){
 if(selector==0){TrailInputLink151B7678*l=p->aux->link;Actor*a=(Actor*)l->record;if(!a->live||l->identity!=a->identity)return 0;out->x=a->x;out->y=a->y;out->z=a->z;return 1;}
 else{f32 m[4][4];u32 i,j;MatrixSource151B76CC*s=((MatrixLink151B76CC*)p->aux->link)->source;func_150A8050(m,s->rotation[0],s->rotation[1],s->rotation[2]);for(j=0;j<3;j++)m[3][j]=s->translation[j];for(i=0;i<3;i++)for(j=0;j<3;j++)m[i][j]*=i==1?s->scaleY:s->scaleX;func_150A7960(m,0.f,0.f,-250.f,&out->x,&out->y,&out->z);return 1;}
}
__attribute__((noinline,noclone))static s32 reference(TrailOwner151B77F4*p){
 TrailAux151B77F4*aux=p->aux;TrailRecord151B77F4*base=p->records;ActorPosition151B6320 old;f32 d[3],distance;TrailRecord151B77F4*record;
 if(D_800BE9E4<=0)return 1;old=p->position;if(!callbackReference(p,&p->position))return 0;
 if(aux->attached)aux->attached->position=p->position;
 d[0]=p->position.x-old.x;d[1]=p->position.y-old.y;d[2]=p->position.z-old.z;distance=func_15143E64(d);
 record=base+p->head;record->position=p->position;record->distance=distance;record->opacity=255;
 p->head=(s8)((int)p->head+1);if(p->head==p->capacity)p->head=0;p->count=(s8)((int)p->count+1);
 if(p->head==p->tail){p->tail=(s8)((int)p->tail+1);if(p->tail==p->capacity)p->tail=0;p->count=(s8)((int)p->count-1);}return 1;
}
static void fixture(void){u32 i;static const u32 modes[]={0,3,2,1};
 for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;for(i=0;i<sizeof(data);i++)((u8*)&data)[i]=(u8)(i*19+row);
 data.arena.owner.position.x=1.5f;data.arena.owner.position.y=-2.75f;data.arena.owner.position.z=3.125f;
 data.arena.owner.capacity=4;data.arena.owner.head=(row>>7)&3;data.arena.owner.tail=(row>>9)&3;data.arena.owner.count=(s8)(row>>4);
 data.arena.owner.records=data.records[0].items;data.arena.owner.aux=&data.aux[0];
 for(i=0;i<2;i++){data.aux[i].attached=(row&128)?NULL:&data.attached[i].object;data.aux[i].callback=(u8)selector;data.aux[i].link=selector?(void*)&data.link:(void*)&data.input;}
 data.actor.live=(row&256)?0:1;data.actor.identity=83;data.actor.x=4.25f;data.actor.y=-5.5f;data.actor.z=6.75f;data.input.record=(u8*)&data.actor;data.input.identity=(row&512)?84:83;
 data.link.source=&data.source;data.source.scaleX=.5f;data.source.scaleY=.75f;for(i=0;i<3;i++){data.source.rotation[i]=.25f*(f32)(i+1);data.source.translation[i]=2.25f*(f32)(i+1);}
 D_800BE9E4=(row&1024)?((row&2048)?-1:0):1;distanceValue=value(0x40500000u+(row&7)*0x1000u);calls=0;initialCSR=0x1f80u|(modes[(row>>5)&3]<<13);setCSR(initialCSR);
}
static void capture(s32 result){current.result=(u32)result;current.calls=calls;current.CSR=csr();current.delta=D_800BE9E4;current.data=data;}
static s32 fail(void){u32 msg[4]={row,current.result,current.calls,current.CSR};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<4096;row++){mode=row&63;selector=(row>>6)&1;fixture();capture(func_151B77F4(&data.arena.owner));copy(&actual,&current,sizeof(actual));fixture();capture(reference(&data.arena.owner));if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 (o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-callbacks.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,timeout=30);diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex();report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=diagnostic,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,target,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('return','    return 1;','    return 0;'),('opacity','record->opacity = 255;','record->opacity = 254;'),('distance','record->distance = distance;','record->distance = -distance;'),('capacity','owner->head == owner->capacity','owner->head != owner->capacity'),('no-count','        owner->count++;',''),('captured-table','record = &records[owner->head];','record = &owner->records[owner->head];'),('captured-aux','if (aux->attached != NULL)','if (owner->aux->attached != NULL)')]:
  assert target.count(old)==1,name;text=target.replace(old,new)
  if name=='captured-table':text=text.replace('    TrailRecord151B77F4 *record;','    TrailRecord151B77F4 *record;\n    (void)records;')
  if name=='captured-aux':text=text.replace('            aux->attached->position','            owner->aux->attached->position')
  controls.append(dict(name=name,**run('control-'+name,text,'-O2',42)))
 q=dict(cases_per_profile=4096,profiles=profiles,translation_units=3,both_actual_callback_C_bodies_and_actual_compatible_function_table=True,callback0_live_identity_and_position_fields=True,callback1_captured_source_scale_translation_matrix_and_output_pointers=True,valid_typed_owner_aux_link_actor_record_attached_arenas_only=True,all_arena_bytes_canaries_pointer_fields_provider_snapshots_integer_return_and_FCSR=True,strict_aliasing_UBSan_traps_LTO_types=True,no_trap_or_signal_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
