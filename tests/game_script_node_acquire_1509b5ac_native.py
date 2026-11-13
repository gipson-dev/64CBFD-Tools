import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_script_node_acquire_1509b5ac_match as source
ROOT,OUT=source.ROOT,source.OUT
body=source.MANIFEST['body']
header=r'''
typedef int s32; typedef short s16; typedef unsigned short u16; typedef unsigned char u8;
#define NULL ((void *)0)
typedef struct {u16 unk0,unk2,unk4,unk6,unk8,unkA;} struct248;
typedef struct ScriptNodeC8950 {u16 kind;u8 padding[0x16];struct ScriptNodeC8950 *next,*prev;} ScriptNodeC8950;
static u8 bitmap[128]; static u8 *D_800D2E4C=bitmap; static s32 D_8003C8E0;
static struct {struct248 header;u8 tail[64];} object;
static int exists,mutation,lookups,creates,inserts,events,zeros,bad;
static struct248 *func_1509B704(s16 id) {lookups++;return exists?&object.header:0;}
static struct248 *func_1509B8FC(s16 id) {creates++;return &object.header;}
static void func_1509B810(ScriptNodeC8950 *p) {inserts++;if(mutation&1)object.header.unk0^=0x401;}
static s32 func_150ADAF0(void *p,s32 a) {events++;if(D_8003C8E0!=0x06000000||p!=&object.header||a)bad++;if(mutation&2)object.header.unk0^=0x400;return 0;}
static void fill(void *v,u8 b,int n){u8*p=v;while(n--)*p++=b;}
static void bzero(void *p,s32 n) {zeros++;fill(p,0,n);}
'''
main=r'''
static int run(void) {
 int count=0;static const int ids[]={0,7,8,127,215};static const int kinds[]={0,0x400,0x800,0x1000,0x1400,0x1800,0xffff};
 for(int i=0;i<5;i++)for(int force=0;force<2;force++)for(exists=0;exists<2;exists++)for(int k=0;k<7;k++)for(int early=0;early<2;early++)for(int late=0;late<2;late++)for(mutation=0;mutation<4;mutation++) {
  int id=ids[i],kind=kinds[k],key=(kind^((mutation&1)?0x401:0))&1023;
  fill(bitmap,0,sizeof(bitmap));fill(&object,0xA5,sizeof(object));object.header.unk0=kind;object.header.unk6=8;object.header.unkA=32;
  if(early)bitmap[id>>3]|=1<<(id&7);if(late)bitmap[key>>3]|=1<<(key&7);
  int blocked=!force&&(bitmap[id>>3]&(1<<(id&7)));int expected_flags=kind;int expected_event=0,expected_zero=0;
  if(!blocked&&!exists) {if(mutation&1)expected_flags^=0x401;key=expected_flags&1023;if(!(bitmap[key>>3]&(1<<(key&7)))){expected_event=1;if(mutation&2)expected_flags^=0x400;}if(!force||(expected_flags&0x400))expected_flags|=0x4000;}
  if(!blocked&&exists&&force&&(kind&0x1000)&&!(kind&0x800))expected_zero=1;
  D_8003C8E0=0x12345678;lookups=creates=inserts=events=zeros=bad=0;
  struct248 *ret=func_1509B5AC(id,force);
  if(ret!=(blocked?0:&object.header)||object.header.unk0!=expected_flags||lookups!=1||creates!=(!blocked&&!exists)||inserts!=creates||events!=expected_event||zeros!=expected_zero||bad||D_8003C8E0!=(expected_event?0:0x12345678))return 1;
  u8 *p=(u8*)&object;for(int t=0;t<8;t++)if(p[32+t]!=(expected_zero?0:0xA5))return 2;
  count++;
 }
 return count==2240?0:3;
}
'''
controls={
 'early':('if (force == 0 &&','if (force != 0 &&'),
 'bitmap':('1 << (scriptId & 7)','1 << ((scriptId + 1) & 7)'),
 'event_color':('D_8003C8E0 = 0x06000000','D_8003C8E0 = 0x05000000'),
 'flag':('node->unk0 |= 0x4000','node->unk0 |= 0x2000'),
 'force':('force != 0 && (node->unk0 & 0x1000)','force == 0 && (node->unk0 & 0x1000)'),
 'zero_size':('node->unkA, node->unk6','node->unkA, node->unk6 - 1'),
}
def compile_run(name,source,opt):
 path=OUT/('native-'+name+'.c');exe=OUT/('native-'+name+'-'+opt[1:]);path.write_text(header+source+main+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
 p=subprocess.run([*native_command(opt,True),'-fno-builtin',str(path),'-o',str(exe)],capture_output=True,text=True);assert p.returncode==0,p.stderr
 return subprocess.run([str(exe)],capture_output=True,text=True)
for opt in ('-O0','-O2','-O3'):
 result=compile_run('source',body,opt);assert result.returncode==0,(opt,result.stdout,result.stderr);print(opt,'native cases 2240',flush=True)
for name,(a,b) in controls.items():
 assert body.count(a)==1,name
 result=compile_run('control-'+name,body.replace(a,b),'-O2');assert result.returncode!=0,(name,result.stdout,result.stderr)
print('six semantic controls rejected',flush=True)
