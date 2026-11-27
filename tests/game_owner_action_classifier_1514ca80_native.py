"""Actual classifier C, typed alias storage and independent native32 reference."""
from tools.experiments import game_owner_action_classifier_1514ca80_match as target_packet
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(target_packet.ROOT));o=target_packet.OUT;pass
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests.game_owner_action_classifier_1514ca80_guest import THIRD,SECOND,NESTED
HEADER=r'''
typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef struct{u32 pre[4];s32 owner[32];s32 output[3];u32 post[4];}Arena;
extern Arena arena;extern s32 D_800BE9F0;
u8 func_1514CA80(u8*,s32*,s32*,s32*) __attribute__((noipa));
u8 reference(u8*,s32*,s32*,s32*) __attribute__((noipa));
typedef char Layout[sizeof(void*)==4&&sizeof(s32)==4&&sizeof(Arena)==172?1:-1];
'''
REFERENCE=r'''
u8 reference(u8*owner,s32*first,s32*second,s32*third){
 u8 flags=0; s32 value=thirdMap[owner[4]],level;
 if(value>=0){*third=value;flags=4;}
 level=D_800BE9F0;
 if((u32)level>=54u||secondMap[level]<0)return flags;
 *second=secondMap[level];flags|=2;value=-1;
 if(level==43){if(owner[4]==156||owner[4]==157)value=0;}
 else if(level==2)value=nested2[owner[0x3b]];
 else if(level==10)value=nested10[owner[0x3b]];
 else if(level==14)value=nested14[owner[0x3b]];
 else if(wanted[level]>=0&&owner[0x3b]==wanted[level])value=0;
 if(value>=0){*first=value;flags|=1;}
 return flags;
}
'''
HARNESS=r'''
Arena arena; s32 D_800BE9F0;
typedef struct{Arena arena;s32 level;u32 result,csr;}Capture;
static Capture actual,expected;static u32 ordinal;
static u32 csr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v)::"memory");return v;}
static void setCSR(u32 v){__asm__ volatile("ldmxcsr %0"::"m"(v):"memory");}
static void report(u32 a,u32 b,u32 c,u32 d){u32 msg[4]={a,b,c,d};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(msg),"d"(sizeof(msg)):"memory");}
static u32 equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static void fixture(u32 kind,s32 level,u32 who){u32 i;for(i=0;i<sizeof(arena);i++)((u8*)&arena)[i]=(u8)(i*29+ordinal*13+90);((u8*)arena.owner)[4]=(u8)kind;((u8*)arena.owner)[0x3b]=(u8)who;for(i=0;i<3;i++)arena.output[i]=-1;D_800BE9F0=level;setCSR(0x1f80u|((ordinal&3)<<13)|((ordinal&16)?1u:0u));}
static void pointers(u32 alias,s32**a,s32**b,s32**c){*a=&arena.output[0];*b=&arena.output[1];*c=&arena.output[2];switch(alias){case 1:*b=*c=*a;break;case 2:*c=&D_800BE9F0;break;case 3:*b=&D_800BE9F0;break;case 4:*a=&D_800BE9F0;break;case 5:*b=&arena.owner[1];break;case 6:*b=&arena.owner[14];break;case 7:*c=&arena.owner[1];break;case 8:*c=&arena.owner[14];break;case 9:*a=*b=*c=0;break;case 10:*a=*b=0;break;}}
static void capture(Capture*p,u8 result){p->arena=arena;p->level=D_800BE9F0;p->result=result;p->csr=csr();}
static s32 one(u32 kind,s32 level,u32 who,u32 alias){s32*a,*b,*c;fixture(kind,level,who);pointers(alias,&a,&b,&c);capture(&actual,func_1514CA80((u8*)arena.owner,a,b,c));fixture(kind,level,who);pointers(alias,&a,&b,&c);capture(&expected,reference((u8*)arena.owner,a,b,c));if(!equal(&actual,&expected,sizeof(actual))){report(ordinal,actual.result^expected.result,actual.csr^expected.csr,alias);return 42;}ordinal++;return 0;}
static s32 main(void){u32 kind,who,j,k,a;s32 level;
 static const u32 ids[12]={0,1,6,7,8,9,13,15,16,23,25,255};
 static const u32 kinds[6]={0,94,153,156,157,255};
 static const s32 levels[9]={-1,0,2,10,14,29,43,53,54};
 static const u32 whos[7]={1,8,9,15,16,25,255};
 static const u32 extraKinds[2]={0,186};static const s32 nested[3]={2,10,14};
 for(kind=0;kind<256;kind++)for(level=-1;level<65;level++)for(j=0;j<12;j++)if(one(kind,level,ids[j],0))return 42;
 for(k=0;k<2;k++)for(j=0;j<3;j++)for(who=0;who<256;who++)if(one(extraKinds[k],nested[j],who,0))return 42;
 for(k=0;k<6;k++)for(j=0;j<9;j++)for(who=0;who<7;who++)for(a=1;a<9;a++)if(one(kinds[k],levels[j],whos[who],a))return 42;
 if(one(255,-1,0,9)||one(0,-1,0,10))return 42;
 report(ordinal,0,0,0);return 0;
}
__attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 result=main();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
def main():
 source=target_packet.MANIFEST['selected_source'];assert (o/'selected-source.c').read_text()==source;a,z=function_span(source,'func_1514CA80');body=source[a:z];(o/'native-shared.h').write_text(HEADER);(o/'native-harness.c').write_text('#include "native-shared.h"\n'+HARNESS)
 def array(name,values):return 'static const s32 '+name+'['+str(len(values))+']={'+','.join(map(str,values))+'};\n'
 tables=array('thirdMap',[THIRD.get(i,-1)for i in range(256)])+array('secondMap',[SECOND.get(i,-1)for i in range(54)])
 for level in (2,10,14):tables+=array('nested'+str(level),[NESTED[level].get(i,-1)for i in range(256)])
 tables+=array('wanted',[-1 if i not in SECOND or i in(2,10,14,43,12,6)else {29:9,7:16,16:6,20:16}.get(i,1)for i in range(54)])
 (o/'native-reference.c').write_text('#include "native-shared.h"\n'+tables+REFERENCE)
 flags=['cc','-m32','-std=gnu99','-ffreestanding','-fno-builtin','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-frounding-math','-ftrapping-math','-fno-fast-math','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-misleading-indentation']
 def run(name,text,opt,want):
  path=o/(name+'.c');path.write_text('#include "native-shared.h"\n'+text+'\n');exe=o/(name+'.exe');q=subprocess.run([*flags,opt,str(path),str(o/'native-reference.c'),str(o/'native-harness.c'),'-o',str(exe)],capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(name,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,timeout=60);d=list(struct.unpack('<4I',q.stdout))if len(q.stdout)==16 else q.stdout.hex();report=dict(profile=opt,comparison_exit=q.returncode,diagnostic=d,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());assert q.returncode==want,(name,report)
  if want==0:assert d==[207314,0,0,0],d
  return report
 profiles=[run('native-'+opt,body,'-'+opt,0)for opt in ('O0','O2','O3')];controls=[]
 for name,old,new in [('owner-kind-byte','switch (owner[4])','switch (owner[5])'),('third-flag','flags = 4;','flags = 8;'),('second-flag','flags |= 2;','flags |= 4;'),('first-flag','flags |= 1;','flags |= 0;'),('second-output','*second = 21;','*third = 21;')]:
  assert old in body;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),'-O2',42)))
 for name,expression,var in [('early-level','D_800BE9F0','cachedLevel'),('cached-kind','owner[4]','cachedKind'),('cached-unique-id','owner[0x3B]','cachedWho')]:
  bad=body.replace(expression,var);opening=bad.index('{')+1;bad=bad[:opening]+f'\n    s32 {var} = {expression};'+bad[opening:];controls.append(dict(name=name,**run('control-'+name,bad,'-O2',42)))
 q=dict(cases_per_profile=207314,profiles=profiles,translation_units=3,actual_C_u8_four_argument_ABI=True,typed_s32_output_and_owner_alias_storage=True,all_owner_kinds_all_levels_minus1_to64_all_nested_unique_ids=True,alias_pointer_patterns=9,unused_null_output_cases=2,full_arenas_level_return_canaries_and_MXCSR_equal=True,strict_aliasing_UBSan_traps_LTO_types=True,actual_and_reference_noipa=True,guest_big_endian_and_native_host_endian_qualified_separately=True,no_signal_or_trap_counted_as_control=True,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
