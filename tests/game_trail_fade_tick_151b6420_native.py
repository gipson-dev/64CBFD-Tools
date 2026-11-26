"""Actual recovered C in two TUs, typed rings, strict FP and complete controls."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_trail_fade_tick_151b6420_match as target_packet
o=target_packet.OUT
def main():
 source=(o/'selected-owner.c').read_text();a,z=function_span(source,'func_151B6420');body=source[a:z];start=source.index('typedef struct {\n    ActorPosition151B6320 position;\n    f32 lifetime;');end=source.index('/* Age the trail ring',start)
 header='typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;\ntypedef struct{f32 x,y,z;}ActorPosition151B6320;\n'+source[start:end]+'s32 func_151B6420(TrailFadeOwner151B6420*);\n'
 header+='typedef char Layout[sizeof(void*)==4&&sizeof(TrailFadeOwner151B6420)==152&&sizeof(TrailFadeRecord151B6420)==28&&__builtin_offsetof(TrailFadeOwner151B6420,position)==84&&__builtin_offsetof(TrailFadeOwner151B6420,flags)==30&&__builtin_offsetof(TrailFadeOwner151B6420,records)==148&&__builtin_offsetof(TrailFadeRecord151B6420,distance)==24?1:-1];\n';(o/'native-shared.h').write_text(header)
 harness=r'''
typedef struct{u32 before[4];TrailFadeOwner151B6420 owner;u32 after[4];}OwnerArena;
typedef struct{u32 before[4];TrailFadeRecord151B6420 records[8];u32 after[4];}RecordArena;
typedef struct{OwnerArena owner;RecordArena records;}Data;
static Data data;f32 D_800BE9A4,D_800AA470;static u32 row,initialCSR;
typedef struct{Data data;u32 result,CSR,dt,factor;}Capture;static Capture actual,current;
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}static f32 value(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
__attribute__((noinline,noclone))static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
__attribute__((noinline,noclone))static s32 reference(TrailFadeOwner151B6420*p){
 TrailFadeRecord151B6420*base=p->records;s32 index;
 if(p->count<2&&(p->flags&8))return 0;
 index=p->head;
 while(index!=p->tail){TrailFadeRecord151B6420*r;--index;if(index<0)index=(s32)p->capacity-1;r=base+index;r->lifetime=r->lifetime-D_800BE9A4;
 if(r->lifetime<0.f){while(index!=p->tail){p->tail=(s8)((s32)p->tail+1);if(p->tail==p->capacity)p->tail=0;p->count=(s8)((s32)p->count-1);}}}
 if(p->count>0){f32 coefficient=D_800AA470,oldest;index=p->tail;oldest=base[index].distance;
 do{TrailFadeRecord151B6420*r=base+index;f32 difference=r->distance-oldest;f32 scaled=difference*coefficient;s32 shade=(s32)scaled;r->opacity=(u8)(shade>155?155:shade);index++;if(index>=p->capacity)index=0;}while(index!=p->head);}
 if(p->count>0)p->position=base[(s32)p->tail].position;else{p->position.x=0.f;p->position.y=0.f;p->position.z=0.f;}return 1;
}
static void fixture(void){u32 i,cap=1+(row&7);static const u32 modes[]={0,3,2,1};static const u32 floats[]={0,0x80000000u,0x3e800000u,0xbf000000u,0x3fa00000u,1,0x00800000u,0x3e000001u};
 for(i=0;i<sizeof(data);i++)((u8*)&data)[i]=(u8)(i*19+row);for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;
 data.owner.owner.capacity=(u8)cap;data.owner.owner.head=(s8)((row>>3)%cap);data.owner.owner.tail=(s8)((row>>6)%cap);data.owner.owner.count=(s8)(row>>4);data.owner.owner.records=data.records.records;data.owner.owner.flags=(row>>8)&8;
 for(i=0;i<8;i++){TrailFadeRecord151B6420*p=&data.records.records[i];p->position.x=1.5f+(f32)i*.0625f;p->position.y=-2.75f;p->position.z=3.125f;p->lifetime=((i+(row>>7))&1)?-.25f:.5f;p->opacity=83;p->distance=(f32)(i*1000);if(row&256)p->distance=-p->distance;}
 D_800BE9A4=value(floats[(row>>10)&7]);D_800AA470=(row&512)?-.25f:value(0x3efced92u);initialCSR=0x1f80u|(modes[(row>>5)&3]<<13);setCSR(initialCSR);
}
static void capture(s32 result){current.result=(u32)result;current.CSR=csr();current.data=data;current.dt=word(D_800BE9A4);current.factor=word(D_800AA470);}
static s32 fail(void){u32 msg[4]={row,current.result,current.CSR,actual.CSR};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<8192;row++){fixture();capture(func_151B6420(&data.owner.owner));actual=current;fixture();capture(reference(&data.owner.owner));if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 (o/'native-harness.c').write_text('#include "native-shared.h"\n'+harness)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stdout,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=30);diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex();report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=diagnostic,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==expected,(name,report);return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('return','    return 1;','    return 0;'),('maximum','record->opacity = 155;','record->opacity = 154;'),('age-sign','record->lifetime < 0.0f','record->lifetime > 0.0f'),('multiply','(record->distance - oldestDistance) * factor','(record->distance - oldestDistance) + factor'),('distance','(record->distance - oldestDistance)','(record->distance + oldestDistance)'),('count','                owner->count--;',''),('position','owner->position = records[owner->tail].position;','owner->position = records[0].position;')]:
  assert body.count(old)==1,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 q=dict(cases_per_profile=8192,profiles=profiles,translation_units=2,valid_typed_capacity1_to8_native_rings_only=True,signed_count_boundaries_and_finite_in_range_float_to_s32_conversion=True,full_owner_record_arenas_canaries_globals_return_and_MXCSR=True,all_four_rounding_modes_and_finite_subnormal_DT=True,strict_aliasing_UBSan_traps_LTO_types=True,no_trap_or_signal_counted_as_control=True,arbitrary_aliases_invalid_conversion_and_invalid_ring_termination_guest_only_or_unclaimed=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0)
 (o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
