"""Actual dispatcher C in three native32 TUs with typed records and escaped outputs."""
from tools.experiments import game_owner_action_dispatch_1514d15c_match as target_packet
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(target_packet.ROOT))
from tools.experiments.game_remaining_donor_candidates import function_span
r=target_packet.ROOT;o=target_packet.OUT
HEADER=r'''
typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef void(*Callback)(u8*);
typedef struct{u8 retained[0x2f0];void*otherHead;void*head;u8 tail[0x34];}Owner;
typedef struct{u32 pre[4];Owner owners[6];u32 fence[4];u32 effects[4][4];u8 third[64],second[64],rows[32][64];u8*rowPointers[32];Callback callbacks[58];u8 enabled;u32 markers[8];u32 post[4];}Arena;
typedef struct{u32 count,calls[16][6],finds,callbacks;}Observation;
extern Arena arena;extern Observation observation;extern u32 row,mode;extern s32*outPointers[3];
#define D_800CC2D0 ((u8*)&arena.owners[2])
#define D_800BE616 arena.enabled
#define D_8008AA70 arena.callbacks
#define D_8008AACC arena.callbacks[23]
#define D_8008AB90 arena.rowPointers
#define D_800A5ED8 arena.third
#define D_800A5EC0 arena.second
void*func_15155FD4(s32);void func_1516972C(void*);void func_15155780(s32,u8);u8 func_1514CA80(u8*,s32*,s32*,s32*);s32 func_1514D15C(u8*);
typedef char Layout[sizeof(void*)==4&&sizeof(Owner)==0x32c&&__builtin_offsetof(Owner,head)==0x2f4&&__builtin_offsetof(Owner,otherHead)==0x2f0?1:-1];
extern Callback const originalCallbacks[58];
'''
PROVIDER=r'''
static void event(u32 target,u32 a,u32 b,u32 c,u32 d){u32*i=observation.calls[observation.count++];i[0]=target;i[1]=a;i[2]=b;i[3]=c;i[4]=d;i[5]=0;}
static u32 recordID(u8*p){return((u32)p-(u32)arena.owners)/sizeof(Owner);}
__attribute__((noipa))void*func_15155FD4(s32 index){u32 n=observation.finds++;event(0x15155fd4,(u32)index,0,0,0);arena.markers[0]++;if(mode&1)arena.enabled=1;return n<((row>>1)&3)?arena.effects[n]:0;}
__attribute__((noipa))void func_1516972C(void*p){event(0x1516972c,((u32)p-(u32)arena.effects)/16,0,0,0);*(u32*)p=0;arena.markers[1]++;}
__attribute__((noipa))void func_15155780(s32 index,u8 channel){event(0x15155780,(u32)index,channel,0,0);arena.markers[2]++;}
__attribute__((noipa))u8 func_1514CA80(u8*p,s32*a,s32*b,s32*c){event(0x1514ca80,recordID(p),1,2,3);if(a==b||a==c||b==c||*a!=-1||*b!=-1||*c!=-1)__builtin_trap();outPointers[0]=a;outPointers[1]=b;outPointers[2]=c;*a=*b=*c=1;return(u8)row;}
__attribute__((noipa))static void callback(u32 id,u8*p){u32 n=++observation.callbacks;event(0x20000000+id*32,recordID(p),0,0,0);arena.markers[3]++;p[0x66]^=(u8)(n*11);if((mode&2)&&n==1){((Owner*)p)->head=arena.effects[2];arena.third[1]=57;}if((mode&4)&&n==2){*outPointers[0]=2;*outPointers[1]=2;arena.second[2]=23;}if((mode&8)&&n==3){*outPointers[0]=3;arena.rowPointers[*outPointers[1]]=arena.rows[0];}}
'''
HARNESS=r'''
Arena arena;Observation observation;u32 row,mode;s32*outPointers[3];
typedef struct{Arena arena;Observation observation;u32 csr,result;}Capture;static Capture actual,current;
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
__attribute__((noinline,noclone))static s32 reference(u8*p){s32 a=-1,b=-1,c=-1;u8 flags,selector;void*effect;Callback chosen;s32 index=(s32)((u32)p-(u32)D_800CC2D0);if(((Owner*)p)->head)return 0;index/=0x32c;while((effect=func_15155FD4(index))!=0)func_1516972C(effect);if(index==0&&!arena.enabled)func_15155780(index,255);arena.callbacks[23](p);flags=func_1514CA80(p,&a,&b,&c);if(flags==0)return 0;if(flags&4){selector=arena.third[c];if(selector)arena.callbacks[selector](p);}if(flags&2){selector=arena.second[b];if(selector)arena.callbacks[selector](p);}if((flags&3)==3){chosen=arena.callbacks[arena.rowPointers[b][a]];if(chosen)chosen(p);}return 1;}
static void fixture(void){u32 i,j,id=(row>>12)%6,gate=(row/24576)&1;static const u8 selects[3][3]={{0,0,0},{23,23,23},{57,1,2}};const u8*s=selects[(row>>6)%3];for(i=0;i<sizeof(arena);i++)((u8*)&arena)[i]=(u8)(i*29+row*13+90);for(i=0;i<sizeof(observation);i++)((u8*)&observation)[i]=0;for(i=0;i<sizeof(current);i++)((u8*)&current)[i]=0;for(i=0;i<6;i++){arena.owners[i].otherHead=0;arena.owners[i].head=0;}arena.owners[id].head=gate?arena.effects[3]:0;arena.enabled=(u8)((row>>4)&1);mode=(row>>8)&15;for(i=0;i<58;i++)arena.callbacks[i]=((row>>7)&1)&&i!=23&&!(s[0]&&i==s[0])&&!(s[1]&&i==s[1])&&!((mode&2)&&i==57)?0:originalCallbacks[i];for(i=0;i<64;i++){arena.third[i]=s[0];arena.second[i]=s[1];}for(i=0;i<32;i++){arena.rowPointers[i]=arena.rows[i];for(j=0;j<64;j++)arena.rows[i][j]=s[2];}for(i=0;i<8;i++)arena.markers[i]=0;for(i=0;i<3;i++)outPointers[i]=0;setCSR(0x1f80u|((row&3)<<13)|((row&16)?1u:0u));}
static void capture(s32 value){current.csr=csr();current.arena=arena;current.observation=observation;current.result=(u32)value;}
static s32 fail(void){u32 msg[4]={row,current.observation.count,current.result^actual.result,current.csr^actual.csr};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");return 42;}
static s32 main(void){for(row=0;row<49152;row++){fixture();capture(func_1514D15C((u8*)&arena.owners[(row>>12)%6]));actual=current;fixture();capture(reference((u8*)&arena.owners[(row>>12)%6]));if(!equal(&actual,&current,sizeof(actual)))return fail();}return 0;}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 value=main();__asm__ volatile("int $0x80"::"a"(1),"b"(value):"memory");__builtin_unreachable();}
'''

def main():
 source=target_packet.MANIFEST['selected_source'];assert (o/'selected-owner.c').read_text()==source;a,z=function_span(source,'func_1514D15C');body=source[a:z];(o/'native-shared.h').write_text(HEADER)
 callbacks='\n'.join(f'__attribute__((noipa))static void callback_{i}(u8*p){{callback({i},p);}}'for i in range(58));table='\nCallback const originalCallbacks[58]={'+','.join('callback_'+str(i)for i in range(58))+'};\n';(o/'native-provider.c').write_text('#include "native-shared.h"\n'+PROVIDER+callbacks+table);(o/'native-harness.c').write_text('#include "native-shared.h"\n'+HARNESS)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,want):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-provider.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stderr);q=subprocess.run([str(exe)],capture_output=True,timeout=60);report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex(),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==want,(name,report);return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')];controls=[]
 for name,old,new in [('head-gate','owner + 0x2F4','owner + 0x2F0'),('record-stride','index /= 0x32C;','index /= 0x330;'),('unsigned-negative-index','index /= 0x32C;','index = (u32)index / 0x32C;'),('reset-channel','index, 0xFF','index, 0xFE'),('first-gate','if (flags & 4)','if (flags & 8)'),('second-gate','if (flags & 2)','if (flags & 4)'),('return','return 1;','return 0;')]:
  assert old in body,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 cached=body.replace('    u8 flags;','    s32 capturedSecond;\n    u8 flags;').replace('    if (flags == 0) return 0;','    if (flags == 0) return 0;\n    capturedSecond = second;').replace('D_800A5EC0[second]','D_800A5EC0[capturedSecond]').replace('D_8008AB90[second]','D_8008AB90[capturedSecond]');controls.append(dict(name='cached-output',**run('control-cached-output',cached,'-O2',42)))
 q=dict(cases_per_profile=49152,profiles=profiles,translation_units=3,actual_C_s32_byte_pointer_ABI=True,typed_812byte_owner_and_both_pointer_field_offsets_asserted=True,full_arena_canaries_pointer_tables_calls_return_and_MXCSR_equal=True,all256_flags_six_owner_records_and_negative_zero_positive_logical_indices=True,pre_callback_aliases_callback_table23=True,escaped_classifier_outputs_legitimately_mutated_within_lifetime=True,opaque_noipa_providers_not_original_classifier=True,strict_aliasing_UBSan_traps_LTO_types=True,no_signal_or_trap_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0)
 (o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
