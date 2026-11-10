"""Native SDK32 execution with typed view records and cursor-return helpers."""
import json,struct,subprocess
from tools.tests import game_view_split_borders_151103c8_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
TYPE='''typedef struct {u8 pad0[0x24];f32 top,bottom,left,right;u8 pad34[0x88];f32 mtx[4][4];u8 padFC[0x84];} Record13D350;'''
def build():
 cs=[c for c in g.cases()if not c.alias and c.index<4 and g.reference(g.fixture(c),c)[3]];expected=bytearray();rows=[]
 for i,c in enumerate(cs):
  m,calls,answer,valid=g.reference(g.fixture(c),c);expected.extend(struct.pack('>I',i)+bytes(m[g.COMMANDS+j]for j in range(4096))+bytes(m[g.selected(c)+j]for j in range(384)))
  for name in('D_80082FA0','D_80082FA4','D_800BE620','D_800BE624'):expected.extend(struct.pack('>I',g.read(m,g.symbols()[name])))
  expected.extend(bytes(g.read(m,g.symbols()['D_800DBEA8']+j,1)for j in range(3))+b'\0'+struct.pack('>II',answer,len(calls)))
  for t,args in calls:expected.extend(struct.pack('>II',t,len(args))+b''.join(struct.pack('>I',v)for v in args))
  rows.append('{'+','.join('0x%Xu'%g.u32(v)for v in(c.index,c.mode,c.width,c.height,*c.view,*c.colors,c.mutation,c.after,c.returns,*c.homes,c.seed))+'}')
 code=r'''
#include <ultra64.h>
TYPE
_Static_assert(sizeof(void*)==4,"SDK32");_Static_assert(sizeof(Gfx)==8,"Gfx");_Static_assert(sizeof(Record13D350)==0x180,"view stride");_Static_assert(__builtin_offsetof(Record13D350,top)==0x24,"top");_Static_assert(__builtin_offsetof(Record13D350,bottom)==0x28,"bottom");_Static_assert(__builtin_offsetof(Record13D350,left)==0x2C,"left");_Static_assert(__builtin_offsetof(Record13D350,right)==0x30,"right");_Static_assert(__builtin_offsetof(Record13D350,mtx)==0xBC,"matrix");
static Record13D350 views[4];Record13D350*D_800BE628=views;
s32 D_80082FA0,D_80082FA4,D_800BE620,D_800BE624;u8 D_800DBEA8[3];
static Gfx arena[512];static const u32*c;static u32 used,count;static u8 logdata[256],output[4512];
static f32 real(u32 v){union{u32 u;f32 f;}a;a.u=v;return a.f;}
static void be(u8*p,u32 v){p[0]=(u8)(v>>24);p[1]=(u8)(v>>16);p[2]=(u8)(v>>8);p[3]=(u8)v;}
static u32 getbe(const u8*p){return((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
static u32 logical(Gfx*p){return 0x50000+(u32)((u8*)p-(u8*)arena);}
static Gfx*call(u32 t,Gfx*p,u32 n,const u32*a){u32 j,delta= t==0x15110544?40:t==0x1501A490?16:8;if(used+8+4*(n+1)>256)__builtin_trap();be(logdata+used,t);be(logdata+used+4,n+1);be(logdata+used+8,logical(p));used+=12;for(j=0;j<n;j++){be(logdata+used,a[j]);used+=4;}count++;p->words.w0=0xAB000000|count;p->words.w1=t;
 if((c[11]&1)&&t==0x15110544){D_80082FA0=(s32)c[12];D_80082FA4=0;}if((c[11]&2)&&t==0x1501A490){D_800BE620=17;D_800BE624=-15;}if((c[11]&4)&&t==0x1501A6CC&&count==3){D_80082FA0=(s32)c[12];D_800BE620=-31;D_800BE624=33;}if(c[11]&8)for(j=0;j<3;j++)D_800DBEA8[j]=0;
 return c[13]?(Gfx*)((u8*)arena+0x200+count*0x80):(Gfx*)((u8*)p+delta);
}
Gfx*func_15110544(Gfx*p,s32 a,s32 b,s32 d,s32 e,u8 r,u8 g,u8 v){u32 values[7]={(u32)a,(u32)b,(u32)d,(u32)e,r,g,v};return call(0x15110544,p,7,values);}
s32 func_1501A490(Gfx*p,s16 a,s32 b,s32 d,s32 e,s32 f){u32 values[5]={(u32)a,(u32)b,(u32)d,(u32)e,(u32)f};return(s32)call(0x1501A490,p,5,values);}
Gfx*func_1501A6CC(Gfx*p,s32 a,s32 b,s32 d,s32 e){u32 values[4]={(u32)a,(u32)b,(u32)d,(u32)e};return call(0x1501A6CC,p,4,values);}
BODY
static const u32 cases[][18]={ROWS};
static int flush(const u8*p,u32 n){u32 done=0;while(done<n){s32 a;__asm__ volatile("int $0x80":"=a"(a):"0"(4),"b"(1),"c"(p+done),"d"(n-done):"memory");if(a<=0)return 1;done+=(u32)a;}return 0;}
static int run(void){u32 i,j,k,answer;u8*p,*o=output+4100;Record13D350*v;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  c=cases[i];used=count=0;D_80082FA0=(s32)c[1];D_80082FA4=(s32)c[0];D_800BE620=(s32)c[2];D_800BE624=(s32)c[3];for(j=0;j<3;j++)D_800DBEA8[j]=(u8)c[8+j];v=views+c[0];p=(u8*)v;for(j=0;j<384;j++)p[j]=(u8)((j+16)*29+c[17]*11+90);
  v->left=real(c[4]);v->top=real(c[5]);v->right=real(c[6]);v->bottom=real(c[7]);for(j=0;j<512;j++){u8 bytes[8];for(k=0;k<8;k++)bytes[k]=(u8)((16+8*j+k)*29+c[17]*11+90);arena[j].words.w0=getbe(bytes);arena[j].words.w1=getbe(bytes+4);}
  answer=logical(func_151103C8(arena,real(c[14]),real(c[15]),real(c[16])));be(output,i);for(j=0;j<512;j++){be(output+4+8*j,arena[j].words.w0);be(output+8+8*j,arena[j].words.w1);}for(j=0;j<384;j++)o[j]=p[j];be(o+0x2C,c[4]);be(o+0x24,c[5]);be(o+0x30,c[6]);be(o+0x28,c[7]);be(o+384,(u32)D_80082FA0);be(o+388,(u32)D_80082FA4);be(o+392,(u32)D_800BE620);be(o+396,(u32)D_800BE624);for(j=0;j<3;j++)o[400+j]=D_800DBEA8[j];o[403]=0;be(o+404,answer);be(o+408,count);
  if(flush(output,4512)||flush(logdata,used))return 1;
 }return 0;
}
'''.replace('TYPE',TYPE).replace('BODY',(g.out/'selected-body.c').read_text(encoding='utf-8')).replace('ROWS',',\n'.join(rows))
 return code+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),bytes(expected),len(cs)
def main():
 code,expected,n=build();path=g.out/'native.c';path.write_text(code);profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=g.out/('native'+opt);r=subprocess.run(native_command(opt)+['-DF3DEX_GBI_2',str(path),'-o',str(exe)],cwd=g.root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60)
  if r.stdout!=expected:
   at=next((i for i,(a,b)in enumerate(zip(r.stdout,expected))if a!=b),min(len(r.stdout),len(expected)));raise AssertionError((opt,r.returncode,len(r.stdout),len(expected),at,r.stdout[max(0,at-12):at+20].hex(),expected[max(0,at-12):at+20].hex(),r.stderr))
  assert r.returncode==0 and not r.stderr,(opt,r.returncode,r.stderr);profiles[opt]=dict(cases=n,exact_public_and_call_bytes=len(expected),UBSan=True,SDK32=True,typed_records=True,strict_aliasing=True)
 report=dict(profiles=profiles,invalid_float_casts_sparse_indices_and_aliases_guest_only=True);(g.out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
