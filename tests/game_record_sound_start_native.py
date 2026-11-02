"""Typed enqueue arguments, helper mutations and post-call state publication."""
from pathlib import Path
import json,subprocess

def qualify(root,output,source,headers,oracle):
 rows=[]
 for c in oracle.cases():
  initial=oracle.fixture(c);args=oracle.arguments(initial,c)
  logical=(args[0],*args[1:5],args[5]&65535,oracle.u32(oracle.half(args[6])),*args[7:])
  values=(c.selector,c.flags,c.state,c.profile,c.mutation,oracle.read(initial,c.record+0x18),oracle.read(initial,c.record+0x1C))
  coords=[oracle.half(oracle.read(initial,c.record+i*2,2))for i in range(3)]
  rows.append('{ {%s},{%s},{%s} }'%(','.join('0x%Xu'%oracle.u32(v)for v in values),','.join(str(v)for v in coords),','.join('0x%Xu'%v for v in logical)))
 prefix=headers.replace('#include <ultra64.h>','typedef unsigned char u8;typedef short s16;typedef unsigned short u16;typedef int s32;typedef unsigned int u32;typedef float f32;')
 prefix+='''
struct Case {u32 v[7];s16 xyz[3];u32 args[12];};
static const struct Case cases[]={ROWS};
struct Packet {u32 fence0[4];GeneratedCDE80Record record;u32 fence1[4];};
static struct Packet packet,expected;
static const struct Case *current;
static u32 calls,bad,outer;
__attribute__((noipa))
u16 func_1000FA64(u16 sound,s16 x,s16 y,s16 z,s32 scale,u16 flags,s16 low,s32 arg7,void*arg8,s32 arg9,s32 mode,s32 arg11){
 u32 a[12]={sound,(u32)x,(u32)y,(u32)z,(u32)scale,flags,(u32)low,(u32)arg7,(u32)arg8,(u32)arg9,(u32)mode,(u32)arg11};u32 i;
 calls++;
 if(packet.record.field20!=0)bad=1;
 for(i=0;i<12;i++)if(a[i]!=current->args[i])bad=1;
 if(current->v[4]&1){packet.record.field20=(s32)0xDEADBEEFu;packet.record.field1C=0x13579BDF;packet.record.flags^=255;packet.record.field17^=255;}
 if(current->v[4]&2)outer=9;
 return 0xBEEF;
}
'''.replace('ROWS',','.join(rows))
 suffix='''
static void (* volatile call)(GeneratedCDE80Record*)=func_150A23E4;
int run(void){u32 i,j,seed;u8 *bytes=(u8*)&packet,*wanted=(u8*)&expected;
 if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(GeneratedCDE80Record)!=52||__builtin_offsetof(GeneratedCDE80Record,field20)!=32)return 9;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  current=&cases[i];seed=current->v[0];for(j=0;j<sizeof(packet);j++)bytes[j]=(u8)(j*29+seed*13+90);
  packet.record.origin0=current->xyz[0];packet.record.origin1=current->xyz[1];packet.record.origin2=current->xyz[2];
  packet.record.field17=current->v[0];packet.record.flags=current->v[1];packet.record.field20=(s32)current->v[2];
  packet.record.field18=(s32)current->v[5];packet.record.field1C=(s32)current->v[6];
  for(j=0;j<sizeof(packet);j++)wanted[j]=bytes[j];
  expected.record.field20=1;
  if(current->v[2]==0&&(current->v[4]&1)){expected.record.field1C=0x13579BDF;expected.record.flags^=255;expected.record.field17^=255;}
  calls=bad=0;outer=0x12345678;call(&packet.record);
  if(bad||calls!=(current->v[2]==0))return 1;
  if(outer!=((current->v[2]==0&&(current->v[4]&2))?9u:0x12345678u))return 1;
  for(j=0;j<sizeof(packet);j++)if(bytes[j]!=wanted[j])return 1;
 }
 return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
 controls={
  'selected':source,
  'byte-gate':source.replace('record->field20 == 0','(record->field20 & 255) == 0'),
  'missing-extra':source.replace('extra = 0x8000','extra = 0'),
  'missing-mode':source.replace('mode = 0x108','mode = 8'),
  'wrong-scale':source.replace('* 327','* 328'),
  'lost-low':source.replace('record->field1C & 0xFFFF','0'),
  'early-state':source.replace('        func_1000FA64(', '        record->field20 = 1;\n        func_1000FA64('),
  'wrong-publication':source.replace('record->field20 = 1','record->field20 = 0',1),
 }
 assert all(v!=source for k,v in controls.items()if k!='selected');results=[]
 for opt in('-O0','-O2','-O3'):
  for label,body in controls.items():
   p=output/('native-'+label+'-'+opt[1:]+'.c');p.write_text(prefix+body+suffix);binary=p.with_suffix('.bin')
   command=['cc','-m32',opt,'-std=c11','-msse2','-mfpmath=sse','-mstackrealign','-fno-builtin','-fno-strict-aliasing','-ffp-contract=off','-ffreestanding','-static','-fno-stack-protector','-fno-pie','-no-pie','-nostdlib','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wl,-e,_start','-o',str(binary),str(p)]
   q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0,(label,q.stderr)
   q=subprocess.run([str(binary)],capture_output=True,timeout=20);assert q.returncode==(0 if label=='selected'else 1),(opt,label,q.returncode,q.stdout.hex(),q.stderr)
   results.append(dict(profile=opt,label=label,status=q.returncode))
 report=dict(success=True,private_only=True,matching_credit=0,cases_per_profile=len(rows),profiles=['O0','O2','O3'],effective_controls_each=7,typed_12_argument_helper=True,callee_halfword_narrowing=True,record_and_surrounding_fences=True,helper_observes_state_before_final_publication=True,helper_mutation_preserved=True,UBSan=True,guest_incoming_home_mutations_not_native_C_claim=True,results=results)
 (output/'private-native-v16.json').write_text(json.dumps(report,indent=2)+'\n');return report
