from pathlib import Path
import importlib.util,sys,itertools,json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path.cwd();out=root/'conker/build/game-mode-descriptor-150f5420-screen'
from tools.tests import game_mode_descriptor_150f5420_behavior as b
s=(out/'selected.c').read_text();start=s.index('extern u8 D_800917F8');end=s.index('\n}',s.index('void *func_150F5420',start))+2;piece=s[start:end]
head,body=piece.split('/* Construct a mode-specific',1);body='/* Construct a mode-specific'+body
bad={
 'mask_second':body.replace('(first << 16) | second','(first << 16) | (second & 0xffff)'),
 'truncate_sum':body.replace('sum = first + second + third','sum = (u16)(first + second + third)'),
 'drop_third':body.replace('sum = first + second + third','sum = first + second'),
 'wrong_pack':body.replace('(third << 16) | sum','(third << 16) + sum'),
 'wrong_mode2_width':body.replace('descriptor.field2C = 240','descriptor.field2C = 241'),
 'wrong_nonzero_asset':body.replace('descriptor.asset = D_80091930','descriptor.asset = D_8009193C'),
 'wrong_step':body.replace('descriptor.field36 = 24','descriptor.field36 = 25'),
 'lost_return':body.replace('return func_15169968(&descriptor);','func_15169968(&descriptor); return NULL;')}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==len(bad)
code='#include <ultra64.h>\n'+head+'\n'.join(v.replace('func_150F5420','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+='\nu8 D_800917F8[4],D_80091930[4],D_8009193C[4],D_80091948[4];\ntypedef struct {u32 args[4];u8 expected[60];} Case;\nstatic const Case cases[]={\n'
vals=(0,1,0xffff,0x10000,0x7fffffff,0x80000000,0xffffffff)
rows=[]
for a,d,e,mode in itertools.product(vals,vals,vals,(0,1,2,3,0xffffffff)):
 c=b.Case((a,d,e,mode));expected=bytearray(60)
 for at,value,n in b.fields(c):expected[at:at+n]=(value&((1<<(8*n))-1)).to_bytes(n,'little')
 rows.append('{{%s},{%s}}'%(','.join('0x%Xu'%v for v in c.args),','.join(str(v) for v in expected)))
code+=',\n'.join(rows)+'\n};\n'
defined=sorted({at+i for at,v,n in b.fields(b.Case()) for i in range(n) if at+i>=4})
code+='static const u8 defined[]={'+','.join(map(str,defined))+'};\n'
code+=r'''
typedef char Layout[sizeof(void*)==4 && sizeof(ModeDescriptor150F5420)==60 && __builtin_offsetof(ModeDescriptor150F5420,packedFirstSecond)==8 && __builtin_offsetof(ModeDescriptor150F5420,field1C)==28 && __builtin_offsetof(ModeDescriptor150F5420,field39)==57?1:-1];
static const Case *current;static u32 observations,error,outcome;static u8 result[76];
void *func_15169968(void *p){u32 i,at;ModeDescriptor150F5420 *d=p;u32 mode=current->args[3];
 u8 *expected=mode==0?D_800917F8:mode==1?D_80091930:mode==2?D_80091948:D_8009193C;
 observations++;if(d->asset!=expected)error=1;
 for(i=0;i<sizeof(defined);i++){at=defined[i];if(((u8*)p)[at]!=current->expected[at])error=1;}
 return outcome?result:NULL;
}
typedef void *(*Candidate)(u32,u32,u32,s32);
'''
code+='static Candidate candidates[]={'+','.join('candidate_'+str(i) for i in range(len(bad)+1))+'};\n'
code+=r'''
static int run(void){u32 i,j,killed=0;void *got;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)for(outcome=0;outcome<2;outcome++){
  current=cases+i;
  for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
   observations=error=0;got=candidates[j](current->args[0],current->args[1],current->args[2],(s32)current->args[3]);
   if(got!=(outcome?(void*)result:NULL)||observations!=1)error=1;
   if(error){if(!j)return 10;killed|=1u<<(j-1);}
  }
 }
 return killed==255u?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
p=out/'native-mode-descriptor.c';p.write_text(code);results=[]
for profile in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=out/('native-mode-'+profile+'-'+alias);q=subprocess.run(native_command(profile)+[alias,'-o',str(exe),str(p)],cwd=root,capture_output=True,text=True)
  assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(profile,alias,q.returncode,q.stderr)
  results.append([profile,alias])
report=dict(native32=True,cases=len(rows)*2,profiles=results,undefined_behavior_sanitizer=True,negative_controls=list(bad),controls_detected=True,indeterminate_bytes_excluded=9,typed_layout_checked=True)
(out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
