"""SDK32 source checks with independently predicted complete public buffers."""
import json,subprocess
from tools.experiments import game_view_point_projection_1517eaac_recovery as source
from tools.tests import game_view_point_projection_1517eaac_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

BLOCKS=((g.CAMERA-16,4*0x9A0+32),(g.VIEW-16,4*0x180+32),(g.OUTPUT-16,48))
def digest(m):
    h=2166136261
    for p,n in BLOCKS:
        for i in range(0,n,4):h=((h^g.read(m,p+i))*16777619)&0xFFFFFFFF
    return h
def harness(body=source.BODY):
    rows=[]
    for c in g.cases():
        if c.phase:continue
        m,calls,result=g.reference(g.fixture(c),c)
        values=[c.view,c.pattern,c.mode,c.alias,result,g.read(m,g.INDEX),digest(m),*g.values(c),*g.projected(c)]
        rows.append('{'+','.join('0x%Xu'%v for v in values)+'}')
    text='#include <ultra64.h>\n'+source.PREAMBLE+r'''
static const u32 cases[][14]={ROWS};
static const u32 *current;
static struct {u32 before[4];ProjectionCamera1AB530 values[4];u32 after[4];} cameras;
static struct {u32 before[4];ProjectionView1AB530 values[4];u32 after[4];} views;
static struct {u32 before[4];f32 values[4];u32 after[4];} outputs;
ProjectionCamera1AB530 *D_800DBFF0=cameras.values;
ProjectionView1AB530 *D_800BE628=views.values;
s32 D_80082FA4;
static u32 calls,error;
static f32 (*retainedMatrix)[4];
static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}
static void putWord(void*p,u32 v){u8*q=p;q[0]=v;q[1]=v>>8;q[2]=v>>16;q[3]=v>>24;}
static u32 getWord(const void*p){const u8*q=p;return(u32)q[0]|(u32)q[1]<<8|(u32)q[2]<<16|(u32)q[3]<<24;}
static void paint(void*p,u32 n,u32 pattern){u32 i,k,w;for(i=0;i<n;i+=4){w=0;
 for(k=0;k<4;k++)w=(w<<8)|((i+k)*29+pattern*11+0x5A)%256;putWord((u8*)p+i,w);}}
static u32 hash(u32 h,const void*p,u32 n){u32 i;for(i=0;i<n;i+=4)h=(h^getWord((const u8*)p+i))*16777619u;return h;}
__attribute__((noinline,noipa)) void func_15110360(s32 view,f32 matrix[4][4],f32 x,f32 y,f32 z){
 u32 i;ProjectionCamera1AB530*c=&cameras.values[current[0]];
 if(calls++!=0||view!=(s32)current[0]||word(x)!=(word(c->rotationX)^0x80000000u)||
    word(y)!=(word(c->rotationY)^0x80000000u)||word(z)!=word(c->rotationZ))error=1;
 retainedMatrix=matrix;for(i=0;i<16;i++)matrix[i/4][i%4]=(f32)((s32)i-7)*(f32)(current[1]+1)*0.125f;
 if(current[2]&1)D_80082FA4=(current[0]+1)&3;
}
__attribute__((noinline,noipa)) void func_150A7A00(f32 matrix[4][4],f32 x,f32 y,f32 z,f32*px,f32*py,f32*pz,f32*pw){
 u32 i;if(calls++!=1||matrix!=retainedMatrix||word(x)!=current[7]||word(y)!=current[8]||word(z)!=current[9])error=2;
 for(i=0;i<16;i++)if(word(matrix[i/4][i%4])!=word((f32)((s32)i-7)*(f32)(current[1]+1)*0.125f))error=3;
 *px=real(current[10]);*py=real(current[11]);*pz=real(current[12]);*pw=real(current[13]);
 if(current[2]&2){views.values[D_80082FA4].scaleX=-123.5f;views.values[D_80082FA4].scaleY=999.25f;D_80082FA4=(D_80082FA4+2)&3;}
}
BODY
static int run(void){u32 n,i,h;f32 *px,*py;int result;
 if(sizeof(void*)!=4||sizeof(ProjectionCamera1AB530)!=0x9A0||sizeof(ProjectionView1AB530)!=0x180||
    __builtin_offsetof(ProjectionCamera1AB530,rotationX)!=0x388||__builtin_offsetof(ProjectionCamera1AB530,rotationZ)!=0x5EC||
    sizeof(outputs)!=48)return 10;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  current=cases[n];paint(&cameras,sizeof(cameras),current[1]);paint(&views,sizeof(views),current[1]);paint(&outputs,sizeof(outputs),current[1]);
  for(i=0;i<4;i++){cameras.values[i].rotationY=(f32)(i+1)*0.125f;cameras.values[i].rotationX=-(f32)(i+2)*0.25f;
   cameras.values[i].rotationZ=(f32)((s32)i-2)*0.5f;views.values[i].scaleX=(f32)(i+1)*80.25f;views.values[i].scaleY=(f32)(i+1)*60.5f;}
  px=&outputs.values[0];py=&outputs.values[1];
  if(current[3]==1)py=px;
  if(current[3]==2){i=(current[0]+1)&3;px=&views.values[i].scaleX;py=&views.values[i].scaleY;}
  if(current[3]==3){px=&cameras.values[current[0]].rotationY;py=&cameras.values[current[0]].rotationX;}
  D_80082FA4=current[0];calls=error=0;
  result=func_1517EAAC(real(current[7]),real(current[8]),real(current[9]),px,py);
  h=hash(hash(hash(2166136261u,&cameras,sizeof(cameras)),&views,sizeof(views)),&outputs,sizeof(outputs));
  if(error||calls!=2)return 11;
  if(result!=(int)current[4]||D_80082FA4!=(s32)current[5]||h!=current[6])return 12;
 }
 return 0;}
'''
    return text.replace('ROWS',',\n'.join(rows)).replace('BODY',body)+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),len(rows)
def run():
    out=source.OUT/'native';out.mkdir(exist_ok=True)
    valid=[];text,count=harness()
    def execute(label,text,opt):
        p=out/(label+'.c');p.write_text(text);exe=out/label
        q=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=source.ROOT,capture_output=True,text=True)
        assert q.returncode==0,q.stdout+q.stderr
        return subprocess.run([str(exe)],timeout=15,capture_output=True).returncode
    for opt in('-O0','-O2','-O3'):
        assert execute(opt[1:],text,opt)==0,opt
        valid.append(dict(optimization=opt,cases=count,strict_aliasing=True,UBSan=True))
    controls={'inclusive-depth':source.BODY.replace('projectedW > 10.0f','projectedW >= 10.0f'),
        'wrong-screen-y':source.BODY.replace('scaleY - projectedY','scaleY + projectedY'),
        'uncleared-y':source.BODY.replace('    *screenY = 0.0f;','')}
    for name,body in controls.items():
        assert body!=source.BODY
        altered,_=harness(body);assert execute(name,altered,'-O2')==12,name
    report=dict(valid=valid,rejected=list(controls),bounded_helpers=True,hardware_or_gameplay_claim=False)
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report
