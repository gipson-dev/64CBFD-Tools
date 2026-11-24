"""SDK32 defined-field lifecycle checks with effective comparison controls."""
import json,subprocess
from tools.experiments import game_opening_spray_150c1f60_match as p
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import game_opening_spray_150c1f60_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT

def main():
 selected=p.MANIFEST['selected_source'];decl=selected[selected.index('typedef struct { f32 x, y, z; } OpeningPointEF410;'):selected.index('/* Generated placeholder declarations. */')]
 def table(name,fields,floats=()):
  return 'static const Field '+name+'[]={'+','.join('{%d,%d,0x%08Xu,%d}'%(a,n,v&0xffffffff,0)for a,n,v in fields)+(' ,'if fields and floats else'')+','.join('{%d,4,0,%d}'%(a,g.GLOBALS.index(n)+1)for a,n in floats)+'};\n'
 prefix='''#include <ultra64.h>
_Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
static __attribute__((noreturn)) void stop(s32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
'''+decl+'\n'+','.join('f32 '+n if i==0 else n for i,n in enumerate(g.GLOBALS))+';\n'+'''
_Static_assert(sizeof(OpeningPointEF410)==12,"position");
_Static_assert(sizeof(OpeningBandHeaderEF410)==8,"header");
_Static_assert(sizeof(OpeningBandEF410)==64,"band");
_Static_assert(sizeof(OpeningSprayEF410)==136,"spray");
_Static_assert(sizeof(OpeningLocalsEF410)==208,"locals");
_Static_assert(__builtin_offsetof(OpeningLocalsEF410,band)==8,"band offset");
_Static_assert(__builtin_offsetof(OpeningLocalsEF410,spray)==72,"spray offset");
_Static_assert(__builtin_offsetof(OpeningSprayEF410,retained84)==132,"retained");
typedef struct {u32 offset,width,value,global;} Field;
static u32 channel,pattern,calls;static void *packet_address;
static u8 expected[136],defined[136];
static const u32 patterns[4][4]={{0,0x80000000,0x3f800000,0xbf800000},{1,0x007fffff,0x7f7fffff,0xff7fffff},{0x3eaaaaab,0xbeaaaaab,0x12345678,0x87654321},{0x3f000001,0xbf000001,0x3f123456,0xbf654321}};
static void bits(void *to,u32 v){u8 *b=to;u32 i;for(i=0;i<4;i++)b[i]=(u8)(v>>(i*8));}
static u32 globalbits(u32 i,u32 stage){return stage && (channel&1)?0x3e000000+stage*0x10000+i*0x101:patterns[pattern][i%4];}
static void globals(u32 stage){
'''+''.join(' bits(&%s,globalbits(%d,stage));\n'%(n,i)for i,n in enumerate(g.GLOBALS))+'''}
static void apply(u8 *out,u8 *mask,const Field *fields,u32 n,u32 stage){u32 i,j,v;for(i=0;i<n;i++){
 v=fields[i].global?globalbits(fields[i].global-1,stage):fields[i].value;
 for(j=0;j<fields[i].width;j++){out[fields[i].offset+j]=(u8)(v>>(j*8));mask[fields[i].offset+j]=1;}
}}
static void compare(const u8 *data,const u8 *want,const u8 *mask,u32 n){u32 i;for(i=0;i<n;i++)if(mask[i] && data[i]!=want[i])stop(42);}
'''+table('first',g.FIRST,g.FIRST_FLOATS)+table('second',g.SECOND,g.SECOND_FLOATS)+table('header',g.HEADER)+table('band',g.BAND_FIELDS,g.BAND_FLOATS)+'''
#define APPLY(a,m,t,s) apply(a,m,t,sizeof(t)/sizeof(*t),s)
static void mutate(void *packet,u32 stage){u32 i;u8 *data=packet;
 if(channel&1){for(i=0;i<136;i++)data[i]=expected[i]=(u8)(i*7+stage*13);
 /* All defined floating members get finite representations before C reads. */
 for(i=0;i<9;i++){bits(data+4*i,0x3f000000+stage*0x10000+i*0x101);bits(expected+4*i,0x3f000000+stage*0x10000+i*0x101);}
 }
 globals(stage);
}
void func_15151A38(void *packet,u8 c,s32 context){u32 i;
 if(c!=(u8)channel || context!=1 || ++calls>2)stop(42);
 if(calls==1){packet_address=packet;for(i=0;i<136;i++)defined[i]=0;APPLY(expected,defined,first,0);}
 else{if(packet!=packet_address)stop(42);APPLY(expected,defined,second,1);}
 compare(packet,expected,defined,136);mutate(packet,calls);
}
void func_15150178(void *head,void *payload,s32 context,u8 c,s32 extra){u8 want[64]={0},mask[64]={0},h[8]={0},hm[8]={0};u32 i;
 if(++calls!=3 || c!=(u8)channel || context!=0 || extra!=1)stop(42);
 for(i=0;i<12;i++){want[i]=expected[i];mask[i]=1;}
 APPLY(want,mask,band,2);APPLY(h,hm,header,0);compare(payload,want,mask,64);compare(head,h,hm,8);
}
'''
 suffix='''static int run(void){u32 c;for(pattern=0;pattern<4;pattern++)for(c=0;c<256;c++){
 channel=0xabcd0000U|c;calls=0;globals(0);func_150C1F60((u8)channel);if(calls!=3)return 42;
 }return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 actual=body(selected,p.FUNCTION);profiles={}
 def run(text,label,opt):
  src=o/(label+'.c');binary=o/label;src.write_bytes((prefix+text+'\n'+suffix).encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(src),'-o',str(binary)],capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,q.stderr
  q=subprocess.run([str(binary)],capture_output=True,timeout=30);assert not q.stderr,q.stderr;return q.returncode,src,binary
 for opt in('-O0','-O2','-O3'):
  code,src,binary=run(actual,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(cases=1024,source_sha256=p.sha(src),binary_sha256=p.sha(binary),SDK32=True,strict_aliasing=True,UBSan=True)
 controls=[]
 for name,old,new in [('second-count','locals.spray.field24 = 2','locals.spray.field24 = 1'),('reset-untouched','locals.spray.field24 = 2;','locals.spray.field24 = 2;\n    locals.spray.field3A = 40;'),('stale-position','locals.band.position = locals.spray.position;','locals.band.position.x = D_800A0230; locals.band.position.y = 40.0f; locals.band.position.z = D_800A0234;'),('header','angle0Base = -159','angle0Base = -158'),('life-range','lifeRange = 25','lifeRange = 0'),('channel','&locals.spray, channel, 1','&locals.spray, channel ^ 1, 1'),('context','&locals.band, 0, channel, 1','&locals.band, 1, channel, 1'),('late-global','locals.band.sizeBase = D_800A0250','locals.band.sizeBase = D_800A0230')]:
  assert old in actual,name;code,src,binary=run(actual.replace(old,new),'control-'+name,'-O2');assert code==42,(name,code);controls.append(dict(name=name,observed_comparison=code,source_sha256=p.sha(src),binary_sha256=p.sha(binary)))
 q=dict(profiles=profiles,effective_source_controls=controls,no_signal_or_UBSan_trap_counted=True,void_result_not_compared=True,unwritten_bytes_not_read_by_native_fixture=True,signaling_NaN_bits_guest_only=True,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(dict(profiles=3,cases_per_profile=1024,effective_controls=len(controls))),flush=True);return q

if __name__=='__main__':main()
