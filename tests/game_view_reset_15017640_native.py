"""Actual recovered C in native32 typed storage, with complete byte snapshots."""
from dataclasses import replace
from pathlib import Path
import hashlib,itertools,json,os,shutil,subprocess
from tools.experiments import game_view_reset_15017640_candidates as source
from tools.tests import game_view_reset_15017640_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def vectors():
 rows=[]
 for i,xyz in enumerate(itertools.product((-32768,-1,0,1,255,32767),repeat=3)):
  rows.append(g.Case(xyz,(0,0x80000000,0x3f800000,0x461c4000)[i%4],i%8,i&255))
 for xyz,mode in itertools.product(((-32768,0,32767),(1,-1,255)),range(8)):rows.append(g.Case(xyz,0x461c4000,mode,mode*31))
 return rows

def controls(body):
 return (body.replace('index < 6','index < 4'),body.replace('= D_8009DCB4[','= (u16) D_8009DCB4['),body.replace('sizeof(D_800D24C8)','0x40'),body.replace('    s32 index;','    s32 index;\n    f32 farPlane = D_800968B0;').replace('53.0f, D_800968B0,','53.0f, farPlane,'),body.replace('60.6f','60.0f'))

def program():
 arr=lambda data:'{'+','.join(str(x) for x in data)+'}'
 rows=[]
 for c in vectors():
  initial=g.fixture(c);expected,calls,states=g.reference(initial,c)
  rows.append('{%d,%d,%s,%s,%s,%s}'%(c.mode,c.seed,arr(g.snapshot(initial)),arr(states[0]),arr(states[1]),arr(g.snapshot(expected))))
 body=source.pointer_body();functions=[body]+[b.replace('func_15017640','negative%d'%i) for i,b in enumerate(controls(body))]
 code=r'''
#include <ultra64.h>
typedef struct {Mtx matrix;f32 scales[6],position[3];u8 pad64[4];f32 motion[3];s32 reset;u8 pad78[12];u16 norm;u8 modes[2],flag,pad89[3];void *link;u8 records[6][16];s32 count;u8 padF4[4],scratch[192];s32 counter;} ViewState;
static struct {u8 prefix[32];ViewState v;u8 suffix[28];} bank;
static union {u8 bytes[16];s16 half[8];} config;
static union {u8 bytes[12];u32 words[3];f32 values[3];} farState;
typedef char Layout[(sizeof(void*)==4&&sizeof(bank)==504&&__builtin_offsetof(ViewState,scales)==0x40&&__builtin_offsetof(ViewState,norm)==0x84&&__builtin_offsetof(ViewState,records)==0x90&&__builtin_offsetof(ViewState,scratch)==0xf8&&__builtin_offsetof(ViewState,counter)==0x1b8)?1:-1];
#define D_800D23D0 bank.v.matrix
#define D_800D2454 bank.v.norm
#define D_800D2410 bank.v.scales
#define D_800D2428 bank.v.position
#define D_800D2438 bank.v.motion
#define D_800D2444 bank.v.reset
#define D_800D2458 bank.v.flag
#define D_800D245C bank.v.link
#define D_800D2460 bank.v.records
#define D_800D24C0 bank.v.count
#define D_800D24C8 bank.v.scratch
#define D_800D2588 bank.v.counter
#define D_8009DCB4 (config.half+2)
#define D_800968B0 farState.values[1]
struct Input {u32 mode,seed;u8 input[532],prezero[532],preprojection[532],final[532];};
static const struct Input cases[]={ROWS};static const struct Input *active;static u32 bad,calls;
static const u32 wordOffsets[]={32,36,40,44,48,52,56,60,64,68,72,76,80,84,88,92,96,100,104,108,112,116,120,124,128,136,140,144,148,172,272,472};
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static void reverse(u8*p,u32 n){u32 i;for(i=0;i<n/2;i++){u8 t=p[i];p[i]=p[n-1-i];p[n-1-i]=t;}}
static void swapFields(u8*p){u32 i;for(i=0;i<sizeof(wordOffsets)/sizeof(wordOffsets[0]);i++)reverse(p+wordOffsets[i],4);reverse(p+164,2);for(i=0;i<16;i+=2)reverse(p+504+i,2);for(i=0;i<12;i+=4)reverse(p+520+i,4);}
static void snapshot(u8*out){copy(out,(u8*)&bank,504);copy(out+504,config.bytes,16);copy(out+520,farState.bytes,12);swapFields(out);}
static void check(const u8*expected){u8 actual[532];u32 i;snapshot(actual);for(i=0;i<532;i++)if(actual[i]!=expected[i])bad=1;}
static u32 word(f32 x){u32 n;__builtin_memcpy(&n,&x,4);return n;}
void bzero(void*destination,int n){int i;
 if(calls++!=0||destination!=(void*)bank.v.scratch||n!=192)bad=1;check(active->prezero);
 if(n>192){bad=1;return;}for(i=0;i<n;i++)((u8*)destination)[i]=0;
 if(active->mode&1)farState.words[1]=0x43af4000;
 if(active->mode&2){bank.v.position[1]=-2.5f;bank.v.scales[1]=-2.f;bank.v.records[4][13]=0x67;bank.v.flag=0xe1;}}
void guPerspective(Mtx*m,u16*norm,f32 fovy,f32 aspect,f32 nearPlane,f32 farPlane,f32 scale){u32 i,j,w;
 if(calls++!=1||m!=&bank.v.matrix||norm!=&bank.v.norm||word(fovy)!=0x42480000||word(aspect)!=0x42726666||word(nearPlane)!=0x42540000||word(farPlane)!=farState.words[1]||word(scale)!=0x3f800000)bad=1;
 check(active->preprojection);
 for(i=0;i<16;i++){w=0;for(j=0;j<4;j++)w=(w<<8)|(((i*4+j)*11+active->seed+0x37)&255);__builtin_memcpy((u8*)m+i*4,&w,4);}*norm=0x7fa5;
 if(active->mode&4){bank.v.records[5][13]=0x71;bank.v.counter=(s32)0xdeadbeef;}}
FUNCTIONS
static void setup(const struct Input*p){u8 bytes[532];copy(bytes,p->input,532);swapFields(bytes);copy((u8*)&bank,bytes,504);copy(config.bytes,bytes+504,16);copy(farState.bytes,bytes+520,12);active=p;bad=calls=0;}
static int run(void){u32 i,j,killed=0;void(*functions[])(void)={func_15017640,negative0,negative1,negative2,negative3,negative4};
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){setup(cases+i);functions[0]();check(active->final);if(bad||calls!=2)return 10;}
 for(j=1;j<6;j++){for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){setup(cases+i);functions[j]();check(active->final);if(bad||calls!=2){killed++;break;}}}return killed==5?0:20;}
void __attribute__((force_align_arg_pointer)) _start(void){int n=run();__asm__ volatile("int $0x80"::"a"(1),"b"(n));__builtin_unreachable();}
'''
 return code.replace('ROWS',',\n'.join(rows)).replace('FUNCTIONS','\n'.join(functions))

def main():
 root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD;code=program();path=out/'native-view-reset.c';path.write_text(code)
 rows=[]
 for opt in ('-O0','-O2','-O3'):
  binary=out/('native-view-reset'+opt);args=[*native_command(opt),'-fno-tree-loop-distribute-patterns','-o',str(binary),str(path)]
  q=subprocess.run(args,cwd=root,capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
  run=subprocess.run([str(binary)],capture_output=True);assert run.returncode==0,(opt,run.returncode)
  rows.append(dict(profile=opt,cases=len(vectors()),public_bytes=532,snapshots_per_case=4,source_controls=5,undefined_behavior_traps=True,entry_stack_realigned=True,generated_c_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest()))
 (out/'native-report.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows),flush=True)
if __name__=='__main__':main()
