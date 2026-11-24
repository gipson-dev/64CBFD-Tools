"""Exact typed callback on SDK32; finite casts and explicit unsigned wrap."""
import json,subprocess
from tools.experiments import game_random_spray_150c2558_match as p
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import game_random_spray_150c2558_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
def main():
 vectors=list(g.cases());literal=lambda x:'0x%08Xu'%(x&0xffffffff);rows=[]
 for c in vectors:
  z,angle=g.values(c);rows.append((c.channel,c.x,c.y,c.z,c.random,c.coefficient,c.mutation,z,angle))
 header='static const struct {u32 channel,x,y,z,random,coefficient,mutation,expectedZ,angle;} vectors[]={'+','.join('{'+','.join(map(literal,row))+'}'for row in rows)+'};\n';(o/'native-vectors.h').write_bytes(header.encode());fields=sorted(g.FIELDS+[(0,4,0),(4,4,0),(8,4,0),(40,2,0)])
 table='static const struct {u32 offset,width,value;} fields[]={'+','.join('{%d,%d,%s}'%(a,n,literal(v))for a,n,v in fields)+'};\n'
 selected=p.MANIFEST['selected_source'];start=selected.index('typedef struct {\n    f32 x, y, z, field0C');end=selected.index('/* Generated placeholder declarations. */',start);decl=selected[start:end]
 prefix='''#include <ultra64.h>
_Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
static __attribute__((noreturn)) void stop(s32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static f32 frombits(u32 v){union {u32 w;f32 f;} x;x.w=v;return x.f;}
f32 D_800A0270;
static u32 vector,stage;
'''+decl+table+'\n#include "native-vectors.h"\n'+'''
_Static_assert(sizeof(FixedSpray150C2290)==136,"packet size");
_Static_assert(__builtin_offsetof(FixedSpray150C2290,retained84)==132,"retained word");
f32 func_150ADA68(void){if(stage++!=0)stop(42);if(vectors[vector].mutation)D_800A0270=.125f;return frombits(vectors[vector].random);}
void func_15151A38(void *packet,u8 channel,s32 context){const u8 *data=packet;u32 i,j,want;
 if(stage++!=1 || channel!=(u8)vectors[vector].channel || context!=1)stop(42);
 for(i=0;i<sizeof(fields)/sizeof(*fields);i++){
  want=fields[i].value;
  if(fields[i].offset==0)want=vectors[vector].x;
  if(fields[i].offset==4)want=vectors[vector].y;
  if(fields[i].offset==8)want=vectors[vector].expectedZ;
  if(fields[i].offset==40)want=vectors[vector].angle;
  for(j=0;j<fields[i].width;j++)if(data[fields[i].offset+j]!=(u8)(want>>(j*8)))stop(42);
 }
 if(vectors[vector].mutation)for(i=0;i<136;i++)((u8*)packet)[i]=(u8)i;
 D_800A0270=frombits(0xdeadbeef);
}
'''
 suffix='''
typedef s32 (*EventSpray)(s32,s16,f32,f32,f32,f32,f32,f32,u8,u8,f32,s32,f32,s32,u8);
static int run(void){EventSpray callback=func_150C2558;s32 result;
 for(vector=0;vector<sizeof(vectors)/sizeof(*vectors);vector++){
  stage=0;D_800A0270=frombits(vectors[vector].coefficient);
  result=callback(1,7,frombits(vectors[vector].x),frombits(vectors[vector].y),frombits(vectors[vector].z),1.f,-2.f,3.f,0x81,0x7f,2.f,9,4.f,10,(u8)vectors[vector].channel);
  if(stage!=2 || result!=1)return 42;
 }return 0;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 actual=body(selected,p.FUNCTION);profiles={}
 def run(text,label,opt):
  src=o/(label+'.c');binary=o/label;src.write_bytes((prefix+text+suffix).encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(src),'-o',str(binary)],capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,q.stderr
  q=subprocess.run([str(binary)],capture_output=True,timeout=30);assert not q.stderr,q.stderr;return q.returncode,src,binary
 for opt in ['-O0','-O2','-O3']:
  code,src,binary=run(actual,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(cases=len(vectors),source_sha256=p.sha(src),binary_sha256=p.sha(binary),SDK32=True,strict_aliasing=True,UBSan=True,exact_15_parameter_function_pointer=True)
 controls=[]
 for name,old,new in [('offset','z + 15.0f','z + 16.0f'),('random-scale','* 30.0f','* 31.0f'),('angle-offset','- 64u','- 63u'),('x','descriptor.x = x','descriptor.x = y'),('count','field24 = 1','field24 = 2'),('channel','&descriptor, channel, 1','&descriptor, channel ^ 1, 1'),('context','&descriptor, channel, 1','&descriptor, channel, 0'),('return','return 1;','return 0;')]:
  assert old in actual,name;code,src,binary=run(actual.replace(old,new),'control-'+name,'-O2');assert code==42,(name,code);controls.append(dict(name=name,observed_comparison=code,source_sha256=p.sha(src),binary_sha256=p.sha(binary)))
 q=dict(profiles=profiles,effective_source_controls=controls,no_signal_or_UBSan_trap_counted=True,finite_representable_float_to_int_domain=True,INT32_MIN_unsigned_subtraction_exercised=True,unwritten_bytes_not_read_by_native_fixture=True,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(dict(profiles=3,cases_per_profile=len(vectors),effective_controls=len(controls))),flush=True);return q
if __name__=='__main__':main()
