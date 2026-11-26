"""Actual leaf C with typed finite rings, two TUs, strict FP and native controls."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_particle_ring_tick_150b40e8_match as target_packet
o=target_packet.OUT
def main():
 source=(o/'selected-owner.c').read_text();a,z=function_span(source,'func_150B40E8');body=source[a:z];start=source.index('typedef struct {\n    ParticlePosition150B3F5C position;\n    ParticlePosition150B3F5C velocity;');end=source.index('/* Advance the particle ring',start)
 header='typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;\ntypedef struct{f32 x,y,z;}ParticlePosition150B3F5C;\n'+source[start:end]+'s32 func_150B40E8(ParticleRingOwner150B40E8*);\n'
 header+='typedef char Layout[sizeof(void*)==4&&sizeof(ParticleRingOwner150B40E8)==156&&sizeof(ParticleRingRecord150B40E8)==36&&sizeof(ParticleRingAux150B40E8)==44&&__builtin_offsetof(ParticleRingOwner150B40E8,referencePosition)==84&&__builtin_offsetof(ParticleRingOwner150B40E8,records)==148&&__builtin_offsetof(ParticleRingRecord150B40E8,lifetime)==30?1:-1];\n';(o/'native-shared.h').write_text(header)
 harness=r'''
typedef struct{u32 before[4];ParticleRingOwner150B40E8 owner;u32 after[4];}OwnerArena;
typedef struct{u32 before[4];ParticleRingRecord150B40E8 records[8];u32 after[4];}RecordArena;
typedef struct{u32 before[4];ParticleRingAux150B40E8 aux;u32 after[4];}AuxArena;
typedef struct{OwnerArena owner;RecordArena records;AuxArena aux;}Data;
static Data data;s32 D_800BE9E4;f32 D_800BE9A4;static u32 row,initialCSR;
typedef struct{Data data;u32 result,CSR,dt;s32 delta;}Capture;static Capture actual,current;
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}static f32 value(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
__attribute__((noinline,noclone))static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
__attribute__((noinline,noclone))static s32 reference(ParticleRingOwner150B40E8*p){
 ParticleRingRecord150B40E8*base=p->records;ParticleRingAux150B40E8*aux=p->aux;s32 index=p->head,tail=p->tail;
 if(p->count<2&&(aux->flags&1))return 0;
 while(index!=tail){ParticleRingRecord150B40E8*r;s32 dead;--index;if(index<0)index=(s32)p->capacity-1;r=base+index;r->opacity=255;r->lifetime=(s16)((s32)r->lifetime-D_800BE9E4);dead=r->lifetime<0;
 r->velocity.y=r->velocity.y+aux->verticalAcceleration*D_800BE9A4;
 r->position.x=r->position.x+r->velocity.x*D_800BE9A4;r->position.y=r->position.y+r->velocity.y*D_800BE9A4;r->position.z=r->position.z+r->velocity.z*D_800BE9A4;r->extent=r->extent+aux->extentRate*D_800BE9A4;
 if(dead){while(index!=p->tail){p->tail=(s8)((s32)p->tail+1);if(p->tail==p->capacity)p->tail=0;p->count=(s8)((s32)p->count-1);}}
 tail=p->tail;}
 if(p->count>0)p->referencePosition=base[tail].position;else{p->referencePosition.x=0.f;p->referencePosition.y=0.f;p->referencePosition.z=0.f;}return 1;
}
static void fixture(void){u32 i,cap=1+(row&7);static const u32 modes[]={0,3,2,1};static const s32 deltas[]={-65536,-1,0,1,65536};static const s16 lives[]={-32768,-1,0,1,32767};static const u32 floats[]={0,0x80000000u,0x3e800000u,0xbf000000u,0x3fa00000u,1,0x00800000u,0x3e000001u};
 for(i=0;i<sizeof(data);i++)((u8*)&data)[i]=(u8)(i*19+row);for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;
 data.owner.owner.capacity=(u8)cap;data.owner.owner.head=(s8)((row>>3)%cap);data.owner.owner.tail=(s8)((row>>6)%cap);data.owner.owner.count=(s8)(row>>4);data.owner.owner.records=data.records.records;data.owner.owner.aux=&data.aux.aux;data.aux.aux.flags=(row>>12)&1;data.aux.aux.verticalAcceleration=-.375f;data.aux.aux.extentRate=.125f;
 for(i=0;i<8;i++){ParticleRingRecord150B40E8*p=&data.records.records[i];p->position.x=1.5f+(f32)i*.0625f;p->position.y=-2.75f;p->position.z=3.125f;p->velocity.x=.125f;p->velocity.y=-.25f;p->velocity.z=.5f;p->extent=2.25f;p->opacity=83;p->lifetime=lives[(i+(row>>7))%5];}
 D_800BE9E4=deltas[(row>>8)%5];D_800BE9A4=value(floats[(row>>10)&7]);initialCSR=0x1f80u|(modes[(row>>5)&3]<<13);setCSR(initialCSR);
}
static void capture(s32 result){current.result=(u32)result;current.CSR=csr();current.data=data;current.delta=D_800BE9E4;current.dt=word(D_800BE9A4);}
static s32 fail(void){u32 msg[4]={row,current.result,current.CSR,actual.CSR};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<8192;row++){fixture();capture(func_150B40E8(&data.owner.owner));actual=current;fixture();capture(reference(&data.owner.owner));if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 (o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stdout,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex();report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=diagnostic,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('return','    return 1;','    return 0;'),('opacity','record->opacity = 255;','record->opacity = 254;'),('lifetime-sign','record->lifetime < 0','record->lifetime > 0'),('gravity','aux->verticalAcceleration * D_800BE9A4','aux->verticalAcceleration + D_800BE9A4'),('position','record->velocity.x * D_800BE9A4','record->velocity.z * D_800BE9A4'),('count','                owner->count--;',''),('reference','owner->referencePosition = records[owner->tail].position;','owner->referencePosition = records[0].position;')]:
  assert body.count(old)==1,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 q=dict(cases_per_profile=8192,profiles=profiles,translation_units=2,valid_typed_capacity1_to8_native_rings_only=True,signed_count_and_lifetime_boundaries_and_bounded_safe_s32_subtraction=True,full_owner_records_aux_arenas_canaries_globals_return_and_MXCSR=True,all_four_rounding_modes_and_finite_subnormal_DT=True,strict_aliasing_UBSan_traps_LTO_types=True,no_trap_or_signal_counted_as_control=True,arbitrary_aliases_and_invalid_ring_termination_guest_only_or_unclaimed=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
