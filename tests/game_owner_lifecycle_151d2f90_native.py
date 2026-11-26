"""Actual lifecycle C, typed partial actor view, opaque providers and controls."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_owner_lifecycle_151d2f90_match as target_packet
o=target_packet.OUT
def main():
 source=target_packet.MANIFEST['selected_source'];assert (o/'selected-owner.c').read_text()==source;a=source.index('/* Validate the owner, update attachment/lifetime state, then dispatch callbacks. */');body=source[a:source.index('\n}\n',a)+3];a=source.index('typedef struct {\n    u8 retained00[0x10];\n    struct127 *actor;');types=source[a:source.index('void func_151D2F90(struct102 *);',a)];(o/'candidate-body.c').write_text(body);(o/'candidate-types.h').write_text(types)
 header='''typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned int u32;typedef int s32;
#define NULL ((void*)0)
typedef struct{u8 opaque[16];}struct102;struct struct255;
/* Partial native view covers every accessed canonical struct127 field. */
typedef struct{s32 interaction_state;u8 id;u8 retained05[0x36];u8 unique_id;u8 retained3C[0x38];u8 unk74;u8 retained75[0x15F];struct struct255 *unk1D4;}struct127;
extern s32 D_800BE9E4;
'''+types+'''
void func_1516972C(struct102 *);void func_151D2F90(struct102 *);
typedef char Layout[sizeof(void*)==4&&sizeof(LifecycleRecord151D2F90)==32&&__builtin_offsetof(LifecycleRecord151D2F90,flags)==24&&__builtin_offsetof(LifecycleRecord151D2F90,lifetime)==22&&__builtin_offsetof(struct127,unique_id)==59&&__builtin_offsetof(struct127,unk74)==116&&__builtin_offsetof(struct127,unk1D4)==468?1:-1];
typedef struct{u32 pre[4];LifecycleRecord151D2F90 record,follow;struct127 actor,other;u32 post[4];}Data;
typedef struct{u32 count,stage[8],argument[8],released;}Observation;
extern Data data;extern Observation observation;extern u32 row,mutation,answer;
''';(o/'native-shared.h').write_text(header)
 provider=r'''
static void observe(u32 stage,LifecycleRecord151D2F90*p){u32 n=observation.count++;observation.stage[n]=stage;observation.argument[n]=(u32)p;if(stage==4){observation.released=(u32)p;p->retained00[8]^=0x55;return;}if(stage){if(mutation&1){p->update=(p->update==0)?-1:0;p->flags^=0x81;p->lifetime=-3;D_800BE9E4=(s32)0x80000001u;}if(mutation&2){p->actor=&data.other;data.other.interaction_state=0;p->retained00[0]^=0xAA;}}}
__attribute__((noipa))static s32 update(LifecycleRecord151D2F90*p){observe(0,p);return(s32)answer;}
__attribute__((noipa))static void begin(LifecycleRecord151D2F90*p){observe(1,p);}
__attribute__((noipa))static void end(LifecycleRecord151D2F90*p){observe(2,p);}
__attribute__((noipa))static void expire(LifecycleRecord151D2F90*p){observe(3,p);}
__attribute__((noipa))void func_1516972C(struct102*p){observe(4,(void*)p);}
LifecycleUpdate151D2F90 D_8008FC4C[1]={update};LifecycleAction151D2F90 D_8008FC50[1]={begin},D_8008FC54[1]={end},D_8008FC58[1]={expire};
''';(o/'native-provider.c').write_text('#include "native-shared.h"\n'+provider)
 harness=r'''
Data data;Observation observation;u32 row,mutation,answer;s32 D_800BE9E4;
typedef struct{Data data;Observation observation;s32 delta;}Capture;static Capture actual,current;
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
__attribute__((noinline,noclone))static void reference(struct102*input){LifecycleRecord151D2F90*p=(void*)input;struct127*a=p->actor;u8 old=p->flags&2;if(a->interaction_state==0||a->id==255||p->actorIdentifier!=a->unique_id){func_1516972C(input);return;}if(a->unk1D4&&(a->unk74&15)!=15)p->flags|=2;else p->flags&=253;if(p->flags&1){p->lifetime=(s16)((u32)(s32)p->lifetime-(u32)D_800BE9E4);if(p->lifetime<0){if(p->expired!=-1)D_8008FC58[(s32)p->expired](p);func_1516972C(input);return;}}if((p->flags&2)!=old){if(p->flags&2)D_8008FC50[p->beginAttachment](p);else D_8008FC54[p->endAttachment](p);}if(p->update!=-1&&D_8008FC4C[p->update](p)==0)func_1516972C(input);}
static void fixture(void){u32 i,gate=row&3;static const s16 life[]={-32768,-1,0,1,32767,300,2,-2};static const u32 ticks[]={0,1,0xffffffffu,0x80000000u},answers[]={0,1,0xffffffffu,0x80000000u};for(i=0;i<sizeof(data);i++)((u8*)&data)[i]=(u8)(i*19+row);for(i=0;i<sizeof(observation);i++)((u8*)&observation)[i]=0;for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;data.actor.interaction_state=gate==1?0:1;data.actor.id=gate==2?255:1;data.actor.unique_id=42;data.actor.unk74=(row&32)?15:0;data.actor.unk1D4=(row&16)?(void*)0x12345000:NULL;data.record.actor=&data.actor;data.record.actorIdentifier=gate==3?43:42;data.record.lifetime=life[(row>>5)&7];data.record.flags=(u8)(((row>>2)&3)|((row&512)?252:0));data.record.update=(row&1024)?0:-1;data.record.expired=(row&2048)?0:-1;data.record.beginAttachment=data.record.endAttachment=0;data.follow=data.record;data.other=data.actor;D_800BE9E4=(s32)ticks[(row>>8)&3];answer=answers[(row>>7)&3];mutation=(row>>6)&3;}
static void capture(void){u32 i;for(i=0;i<sizeof(Data);i++)((u8*)&current.data)[i]=((u8*)&data)[i];current.observation=observation;current.delta=D_800BE9E4;}
static s32 fail(void){u32 msg[4]={row,current.observation.count,actual.observation.count,current.observation.released^actual.observation.released};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<4096;row++){fixture();func_151D2F90((struct102*)&data.record);capture();actual=current;fixture();reference((struct102*)&data.record);capture();if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
''';(o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-provider.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('owner-active','actor->interaction_state == 0','actor->interaction_state != 0'),('owner-kind','actor->id == 255','actor->id == 254'),('identity','actor->unique_id != record->actorIdentifier','actor->unique_id == record->actorIdentifier'),('matrix','actor->unk1D4 != NULL','actor->unk1D4 == NULL'),('matrix-mode','(actor->unk74 & 15) != 15','(actor->unk74 & 15) != 14'),('clock','lifetime -=','lifetime +='),('expiration','record->expired != -1','record->expired != 0'),('begin-action','D_8008FC50[','D_8008FC54['),('old-state','wasAttached = record->flags & 2','wasAttached = 0'),('update-status','](record) == 0','](record) != 0')]:
  assert old in body,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 q=dict(cases_per_profile=4096,profiles=profiles,translation_units=3,actual_C_void_struct102_entry_and_typed_header32=True,native_partial_struct127_view_asserts_every_accessed_field_offset=True,full_typed_arenas_canaries_globals_calls_and_released_pointer_equal=True,valid_callback_selector_zero_or_sentinel_minus_one_only=True,opaque_noipa_providers_and_late_reachable_record_mutations=True,native_does_not_expose_or_rewrite_incoming_stack_homes=True,strict_aliasing_UBSan_traps_LTO_types=True,no_signal_or_trap_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
