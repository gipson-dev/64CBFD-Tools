"""Native 32-bit tests for the explicit signed-convert/add-2^32 path."""
from pathlib import Path
import json,struct,subprocess
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-line-record-1512dd50-durable';text=(out/'pointer-reuse-00.c').read_text();head=text[:text.index('/* Generated placeholder declarations. */')];start=text.index('#ifdef __GNUC__');end=text.index('/* Build the inline line record',start);source=head+text[start:end]+body(text,'func_1512DD50')+'\n'
f=lambda x:struct.unpack('>f',struct.pack('>f',x))[0]
def expected(v):
 signed=v if v<0x80000000 else v-0x100000000
 value=f(float(signed));value=f(value+4294967296.0) if signed<0 else value
 return struct.unpack('>I',struct.pack('>f',value))[0]
values={0,1,0x7fffffff,0x80000000,0x80000001,0x8000007f,0x80000080,0x80000081,0xffffff7f,0xffffff80,0xffffff81,0xffffffff}
values.update((0x80000000+i)&0xffffffff for i in range(0,65536,67))
values.update((0x9e3779b9*i+0x12345678)&0xffffffff for i in range(128))
values=sorted(values);rows=['{0x%08xu,0x%08xu,0x%08xu,0x%08xu}'%(v,v^0xffffffff,expected(v),expected(v^0xffffffff)) for v in values]
harness=r'''
#include <ultra64.h>
#include "functions.h"
#include "variables.h"
static struct108 owner; static int calls,error;
f32 func_150AD930(f32 *p){calls++;if(p[0]!=6.0f||p[1]!=6.0f||p[2]!=0.75f)error=20;return 2.0f;}
void func_1512DD50(struct108 *);
static void write32(unsigned off,u32 v){u8*p=(u8*)&owner+off;p[0]=v;p[1]=v>>8;p[2]=v>>16;p[3]=v>>24;}
static u32 read32(unsigned off){u8*p=(u8*)&owner+off;return (u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
typedef struct {u32 a,b,expectedA,expectedB;} Row;
static const Row rows[]={ROWS};
static int run(void){unsigned i,j;u8*p=(u8*)&owner;
 if(sizeof(void*)!=4||__builtin_offsetof(struct108,unk870)!=0x870)return 10;
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
  for(j=0;j<sizeof(owner);j++)p[j]=0xa5;
  owner.unk70C=1;owner.unk70E=-2;owner.unk710=3;owner.unk712=3;
  owner.unk720=0.5f;owner.unk724=1.0f;owner.unk728=2.0f;owner.unk72C=-0.25f;
  write32(0x71c,rows[i].a);write32(0x704,rows[i].b);write32(0x718,0x123456e1u);calls=error=0;
  func_1512DD50(&owner);
  if(error||calls!=1||read32(0x874)!=0xc0000000u||read32(0x878)!=0xc0a00000u||read32(0x87c)!=0x40280000u)return 11;
  if(read32(0x880)!=0x40400000u||read32(0x884)!=0x40400000u||read32(0x888)!=0x3ec00000u||read32(0x88c)!=0x3f000000u)return 12;
  if(read32(0x890)!=rows[i].expectedA||read32(0x894)!=rows[i].expectedB||read32(0x898)||read32(0x89c)||p[0x870]!=0xe1)return 13;
 }
 return 0;
}
'''.replace('ROWS',',\n'.join(rows))
fixture=out/'native-sweep-harness.c';fixture.write_text(harness+START);candidate=out/'native-sweep-candidate.c';candidate.write_text(source);passed=[]
for opt in ('-O0','-O2','-O3'):
 exe=out/('native-sweep-'+opt[1:]);p=subprocess.run(native_command(opt)+[str(candidate),str(fixture),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert p.returncode==0,(opt,p.stderr);r=subprocess.run([str(exe)]);assert r.returncode==0,(opt,r.returncode);passed.append(opt)
controls=(('missing-first-correction','if (((LineSource1512DD50 *)&owner->unk6FC)->first < 0) dy += 4294967296.0f;','if (0) dy += 4294967296.0f;'),('wrong-first-source','->first;\n    if (((LineSource1512DD50 *)&owner->unk6FC)->first','->second;\n    if (((LineSource1512DD50 *)&owner->unk6FC)->first'),('wrong-direction','record->x = size * vector.unk0;','record->x = size * vector.unk1;'),('wrong-kind','->kind;','->first;'))
rejected=[]
for name,old,new in controls:
 if name=='wrong-first-source':old='->first; /* Match MIPS signed conversion followed by unsigned adjustment. */';new='->second; /* Match MIPS signed conversion followed by unsigned adjustment. */'
 if name=='wrong-direction':new='record->x = size * vector.unk8;'
 assert source.count(old)==1,(name,source.count(old));p=out/(name+'.c');p.write_text(source.replace(old,new));exe=out/name;cc=subprocess.run(native_command('-O2')+[str(p),str(fixture),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not cc.returncode,(name,cc.stderr);r=subprocess.run([str(exe)]);assert r.returncode!=0,('ineffective',name);rejected.append(name)
report={'values_per_optimization':len(values),'optimizations':passed,'effective_controls':rejected,'helper_modeled':True,'ubsan_trapping':True,'expected_generated_from_mips_rounding_model':True};(out/'native-sweep.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
