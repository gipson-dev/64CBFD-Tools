"""SDK32 tests read only defined fields; retained84 remains guest-only evidence."""
import json,subprocess
from tools.experiments import game_fixed_spray_150c2290_match as p
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import game_fixed_spray_150c2290_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
def main():
 decl=p.MANIFEST['selected_source'].split('typedef struct {\n    f32 x, y, z, field0C',1)[1];decl='typedef struct {\n    f32 x, y, z, field0C'+decl;decl=decl[:decl.index('/* Generated placeholder declarations. */')]
 fields=list(g.FIELDS)+[(at,4,0)for at,n in g.FLOATS];fields.sort();literal=lambda x:'0x%08Xu'%(x&0xffffffff)
 definitions='static const struct {u32 offset,width,value;} fields[]={'+','.join('{%d,%d,%s}'%(a,n,literal(v))for a,n,v in fields)+'};\n'
 prefix='''#include <ultra64.h>
_Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
static __attribute__((noreturn)) void stop(s32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
f32 D_800A0258,D_800A025C,D_800A0260,D_800A0264;
static u32 channel,pattern,calls;
static const u32 patterns[4][4]={{0,0x80000000,0x3f800000,0xbf800000},{1,0x007fffff,0x7f7fffff,0xff7fffff},{0x7f800000,0xff800000,0x7fc12345,0xffcabcde},{0x3eaaaaab,0xbeaaaaab,0x12345678,0x87654321}};
static void writebits(f32 *to,u32 v){u8 *b=(u8*)to;u32 i;for(i=0;i<4;i++)b[i]=(u8)(v>>(i*8));}
'''+decl+definitions+'''
_Static_assert(sizeof(FixedSpray150C2290)==136,"packet size");
_Static_assert(__builtin_offsetof(FixedSpray150C2290,retained84)==132,"retained word");
void func_15151A38(void *packet,u8 c,s32 context){
 const u8 *data=packet;u32 i,j,want,index=0;
 if(c!=(u8)channel || context!=1 || ++calls!=1)stop(42);
 for(i=0;i<sizeof(fields)/sizeof(*fields);i++){
  want=fields[i].value;
  if(fields[i].offset==0 || fields[i].offset==8 || fields[i].offset==12 || fields[i].offset==20)want=patterns[pattern][index++];
  for(j=0;j<fields[i].width;j++)if(data[fields[i].offset+j]!=(u8)(want>>(j*8)))stop(42);
 }
 /* Writes through unsigned char may include padding; no prior value is read. */
 if(channel&1)for(i=0;i<136;i++)((u8*)packet)[i]=(u8)i;
 writebits(&D_800A0258,0xdeadbeef);writebits(&D_800A025C,0xdeadbeef);writebits(&D_800A0260,0xdeadbeef);writebits(&D_800A0264,0xdeadbeef);
}
'''
 suffix='''static int run(void){u32 c;for(pattern=0;pattern<4;pattern++)for(c=0;c<256;c++){
 channel=(0xabcd0000U|c);calls=0;
 writebits(&D_800A0258,patterns[pattern][0]);writebits(&D_800A025C,patterns[pattern][1]);writebits(&D_800A0260,patterns[pattern][2]);writebits(&D_800A0264,patterns[pattern][3]);
 func_150C2290((u8)channel);if(calls!=1)return 42;
 }return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 actual=body(p.MANIFEST['selected_source'],'func_150C2290');profiles={}
 def run(text,label,opt):
  src=o/(label+'.c');binary=o/label;src.write_bytes((prefix+text+'\n'+suffix).encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(src),'-o',str(binary)],capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,q.stderr
  q=subprocess.run([str(binary)],capture_output=True,timeout=30);assert not q.stderr,q.stderr;return q.returncode,src,binary
 for opt in('-O0','-O2','-O3'):
  code,src,binary=run(actual,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(cases=1024,source_sha256=p.sha(src),binary_sha256=p.sha(binary),SDK32=True,strict_aliasing=True,UBSan=True)
 controls=[]
 for name,old,new in [('count','field24 = 2','field24 = 1'),('negative-range','field28 = -0x29','field28 = -0x28'),('type','field3A = 0x28','field3A = 0x29'),('float','descriptor.y = 40.0f','descriptor.y = 41.0f'),('channel','&descriptor, channel, 1','&descriptor, channel ^ 1, 1'),('context','&descriptor, channel, 1','&descriptor, channel, 0')]:
  assert old in actual,name;code,src,binary=run(actual.replace(old,new),'control-'+name,'-O2');assert code==42,(name,code);controls.append(dict(name=name,observed_comparison=code,source_sha256=p.sha(src),binary_sha256=p.sha(binary)))
 q=dict(profiles=profiles,effective_source_controls=controls,no_signal_or_UBSan_trap_counted=True,void_result_not_compared=True,unwritten_bytes_and_retained84_not_read_by_native_fixture=True,signaling_NaN_bits_guest_only=True,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(dict(profiles=3,cases_per_profile=1024,effective_controls=len(controls))),flush=True);return q
if __name__=='__main__':main()
