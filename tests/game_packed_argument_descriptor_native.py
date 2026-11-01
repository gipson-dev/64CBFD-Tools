"""Native32 checks only defined descriptor bytes, full-word packing and return ABI."""
import json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def harness(selected,oracle):
 head,body=selected.split('/* Pack three',1);body='/* Pack three'+body
 bad=dict(masked_second=body.replace('(first<<16)|second','(first<<16)|(second&0xFFFF)'),
  truncated_sum=body.replace('u32 sum=first+second+third','u32 sum=(u16)(first+second+third)'),
  missing_third=body.replace('u32 sum=first+second+third','u32 sum=first+second'),
  wrong_packed_operation=body.replace('(third<<16)|sum','(third<<16)+sum'),
  wrong_asset=body.replace('descriptor.asset=D_800917EC','descriptor.asset=D_800917EC+4'),
  wrong_constant=body.replace('descriptor.field28=0x18FC','descriptor.field28=0x18FD'),
  wrong_scalar=body.replace('descriptor.field20=D_800A26A0','descriptor.field20=1.0f'),
  lost_return=body.replace('return func_15169968(&descriptor);','func_15169968(&descriptor);\n    return NULL;'))
 assert len(set(bad.values()))==8 and all(v!=body for v in bad.values())
 code=head+'\n'.join(v.replace('func_1510A930','candidate_'+str(i))for i,v in enumerate([body,*bad.values()]))
 code+='\nu8 D_800917EC[8];f32 D_800A26A0;\ntypedef struct {u32 args[3];u32 scalar;u8 expected[60];} Case;\nstatic const Case cases[]={\n';rows=[]
 for args in oracle.corpus():
  for scalar in (0,0x80000000,0x3F800000,0x7FC12345):
   expected=bytearray(60)
   for at,value,n in oracle.fields(args,scalar,0):expected[at:at+n]=(value&((1<<(8*n))-1)).to_bytes(n,'little')
   rows.append('{{%s},0x%Xu,{%s}}'%(','.join('0x%Xu'%v for v in args),scalar,','.join(str(v)for v in expected)))
 code+=',\n'.join(rows)+'\n};\n'
 code+='static const u8 defined[]={'+','.join(str(x)for x in oracle.DEFINED if x>=4)+'};\n'
 code+=r'''
typedef char Layout[sizeof(void*)==4 && sizeof(PackedArgumentDescriptor)==60 && __builtin_offsetof(PackedArgumentDescriptor,packedFirstSecond)==8 && __builtin_offsetof(PackedArgumentDescriptor,field1C)==28 && __builtin_offsetof(PackedArgumentDescriptor,field39)==57?1:-1];
typedef union {u32 u;f32 f;} Word;
static const Case *current;static u32 observations,error,outcome;
typedef struct {u32 before;u8 record[76];u32 after;} World;
static World world;
void *func_15169968(void *p){u32 i,at;PackedArgumentDescriptor *d=p;
 observations++;
 if(d->asset!=D_800917EC)error=1;
 for(i=0;i<sizeof(defined);i++){at=defined[i];if(((u8*)p)[at]!=current->expected[at])error=1;}
 /* Native checks avoid reading or promising values for the nine indeterminate bytes. */
 if(outcome){for(i=0;i<sizeof(defined);i++){at=defined[i];world.record[16+at]=((u8*)p)[at];}return world.record;}
 return NULL;
}
typedef void *(*Candidate)(u32,u32,u32);
'''
 code+='static Candidate candidates[]={'+','.join('candidate_'+str(i)for i in range(9))+'};\n'
 code+=r'''
static int run(void){u32 i,j,k,killed=0;void *got;Word scalar;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)for(outcome=0;outcome<2;outcome++){
  current=cases+i;
  for(j=0;j<9;j++){
   world.before=0x12345678;world.after=0x87654321;for(k=0;k<sizeof(world.record);k++)world.record[k]=0xA5;
   observations=error=0;scalar.u=current->scalar;D_800A26A0=scalar.f;
   got=candidates[j](current->args[0],current->args[1],current->args[2]);
   if(got!=(outcome?(void*)world.record:NULL)||observations!=1)error=1;
   scalar.f=D_800A26A0;if(scalar.u!=current->scalar)return 12;
   if(world.before!=0x12345678||world.after!=0x87654321)return 13;
   for(k=0;k<16;k++)if(world.record[k]!=0xA5)return 14;
   if(error){if(!j)return 10;killed|=1u<<(j-1);}
  }
 }
 return killed==255u?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return code,list(bad),len(rows)*2
def run_native(root,out,selected,oracle):
 code,names,count=harness(selected,oracle);p=out/'native-descriptor.c';p.write_text(code);rows=[]
 for profile in ('-O0','-O2','-O3'):
  exe=out/('native-descriptor'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(p)],cwd=root,capture_output=True,text=True);(out/('native-descriptor'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  rows.append(dict(profile=profile,UBSan=True,baseline_cases=count,negative_controls=names,all_controls_effective=True))
 result=dict(native32=True,defined_bytes=51,unwritten_bytes_excluded=9,typed_layout_asserted=True,return_pointer_and_null_checked=True,global_and_record_canaries_unchanged=True,portable_C_padding_equality_claimed=False,rows=rows)
 (out/'native-descriptor.json').write_text(json.dumps(result,indent=2)+'\n');return result
