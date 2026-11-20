"""SDK32 checks on compatible objects and the C-defined conversion domain."""
from dataclasses import replace
import json,math,re,subprocess
from tools.experiments import game_list_depth_1517ec1c_recovery as source
from tools.tests import game_list_depth_1517ec1c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def digest(m):
    h=2166136261
    for base,size in g.BLOCKS:
        for i in range(0,size,4):h=((h^g.read(m,base+i))*16777619)&0xFFFFFFFF
    return h
def harness(body=source.BODY):
    _,selected=source.source()
    record=re.search(r'typedef struct ListRecord1AB530 \{.*?\} ListRecord1AB530;',selected,re.S)[0]
    views=re.search(r'typedef struct \{\n    u8 opaque0\[0x2F8\];.*?extern s32 D_80082FA4;',selected,re.S)[0]
    rows=[]
    for old in g.cases():
        c=replace(old,alias=0);initial=g.fixture(c);want,calls,result,value=g.reference(initial,c)
        # The emitted MIPS suite separately covers invalid conversion inputs.
        if value is not None and(not math.isfinite(g.floating(value))or not-1.<g.floating(value)<4294967296.):continue
        meta=[c.index,c.mode,g.answer(c),result,digest(want),g.read(want,g.PAGE,1),
              int(g.read(want,g.CAMERAS)!=g.CAMERA),int(g.read(want,g.VIEW_BASE)!=g.VIEWS)]
        before=[g.read(initial,g.NODE-16+4*i)for i in range(21)]
        vectors=[meta,before,list(g.outputs(c))]
        rows.append('{'+','.join('{'+','.join('0x%Xu'%v for v in x)+'}'for x in vectors)+'}')
    text='#include <ultra64.h>\n'+record+'\n'+views+'\n'+source.PREAMBLE+r'''
struct Case {u32 meta[8],before[21],projected[4];};
static const struct Case cases[]={ROWS};
static const struct Case *current;
static struct {u32 before[4];ListRecord1AB530 record;u32 after[4];} node;
static struct {u32 before[4];ProjectionCamera1AB530 values[2];u32 after[4];} cameras;
static struct ViewStore {u32 before[4];ProjectionView1AB530 value;u32 after[4];} views,otherViews;
static struct {u32 before[4];u32 value;u32 after[4];} output;
ProjectionCamera1AB530 *D_800DBFF0;
ProjectionView1AB530 *D_800BE628;
u8 D_800BE9C0;
const PackedDepthRange1AB530 D_80089630[8]={{6,0},{5,0x20000},{4,0x30000},{3,0x38000},{2,0x3C000},{1,0x3E000},{0,0x3F000},{0,0x3F800}};
static u32 calls,error;
static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}
static void putWord(void*p,u32 v){u8*q=p;q[0]=v;q[1]=v>>8;q[2]=v>>16;q[3]=v>>24;}
static u32 getWord(const void*p){const u8*q=p;return(u32)q[0]|(u32)q[1]<<8|(u32)q[2]<<16|(u32)q[3]<<24;}
static void paint(void*p,u32 n,u32 pattern){u32 i,k,w;for(i=0;i<n;i+=4){w=0;
 for(k=0;k<4;k++)w=(w<<8)|((i+k)*29+pattern*11+0x5A)%256;putWord((u8*)p+i,w);}}
static u32 hash(u32 h,const void*p,u32 n){u32 i;for(i=0;i<n;i+=4)h=(h^getWord((const u8*)p+i))*16777619u;return h;}
static u32 hashNode(u32 h){u32 i,w;for(i=0;i<sizeof(node);i+=4){w=getWord((const u8*)&node+i);
 if(i==16+0x28)w=(u32)(u16)node.record.state28<<16|node.record.sample2A;
 if(i==16+0x2C)w=(u32)node.record.depth2C<<16|(u32)node.record.flags2E<<8|node.record.first2F;
 if(i==16+0x30)w=(u32)node.record.second30<<24|(u32)node.record.opaque31[0]<<16|(u32)node.record.opaque31[1]<<8|node.record.opaque31[2];
 h=(h^w)*16777619u;}return h;}
static u32 hashView(u32 h,const struct ViewStore*p){u32 i,w;for(i=0;i<sizeof(*p);i+=4){w=getWord((const u8*)p+i);
 if(i>=16+0x40&&i<16+0x60)w=(w<<16)|(w>>16);h=(h^w)*16777619u;}return h;}
__attribute__((noinline,noipa)) f32 sqrtf(f32 value){f32 result;__asm__("sqrtss %1,%0":"=x"(result):"x"(value));return result;}
__attribute__((noinline,noipa)) s32 func_1509563C(f32 x,f32 y,f32 z,f32*px,f32*py,f32*depth,f32*divisor,f32 maximum){
 if(calls++!=0||word(x)!=current->before[4]||word(y)!=current->before[5]||word(z)!=current->before[6]||
    px!=&node.record.valueC||py!=&node.record.value10||depth==divisor||word(maximum)!=0x457A0000u)error=1;
 *px=real(current->projected[0]);*py=real(current->projected[1]);
 *depth=real(current->projected[2]);*divisor=real(current->projected[3]);
 if(current->meta[1]==1)node.record.flags2E^=4;
 if(current->meta[1]==2){D_800DBFF0=&cameras.values[1];node.record.sample2A^=65535;D_800BE9C0^=1;node.record.position[0]=3.f;}
 if(current->meta[1]==3){D_800BE628=&otherViews.value;node.record.direction[0]=2.f;}
 return(s32)current->meta[2];
}
BODY
static int run(void){u32 n,i,k,h;int result;
 if(sizeof(void*)!=4||sizeof(ListRecord1AB530)!=52||sizeof(ProjectionCamera1AB530)!=0x9A0||sizeof(ProjectionView1AB530)!=0x180||
    __builtin_offsetof(ListRecord1AB530,depth2C)!=0x2C||__builtin_offsetof(ProjectionView1AB530,viewports)!=0x40||
    sizeof(node)!=84||sizeof(output)!=36)return 10;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  current=&cases[n];for(i=0;i<21;i++)putWord((u8*)&node+4*i,current->before[i]);
  node.record.state28=(s16)(current->before[14]>>16);node.record.sample2A=current->before[14];
  node.record.depth2C=current->before[15]>>16;node.record.flags2E=current->before[15]>>8;node.record.first2F=current->before[15];
  node.record.second30=current->before[16]>>24;node.record.opaque31[0]=current->before[16]>>16;
  node.record.opaque31[1]=current->before[16]>>8;node.record.opaque31[2]=current->before[16];
  paint(&cameras,sizeof(cameras),current->meta[0]);paint(&views,sizeof(views),current->meta[0]);
  paint(&otherViews,sizeof(otherViews),current->meta[0]);paint(&output,sizeof(output),current->meta[0]);
  for(i=0;i<3;i++){cameras.values[0].position[i]=0.f;cameras.values[1].position[i]=i==0?-2.f:0.f;}
  for(k=0;k<2;k++)for(i=0;i<2;i++){
   ProjectionView1AB530*v=k?&otherViews.value:&views.value;
   u32 j,w;for(j=0;j<4;j++){w=getWord((u8*)v+0x40+i*16+j*4);putWord((u8*)v+0x40+i*16+j*4,(w<<16)|(w>>16));}
   v->viewports[i].vp.vscale[2]=i==0?1:-2;v->viewports[i].vp.vtrans[2]=i==0?0:30;}
  D_800DBFF0=&cameras.values[0];D_800BE628=&views.value;D_800BE9C0=current->meta[0]&1;calls=error=0;
  result=func_1517EC1C(&node.record,&output.value);
  h=hash(hashView(hashView(hash(hashNode(2166136261u),&cameras,sizeof(cameras)),&views),&otherViews),&output,sizeof(output));
  if(error||calls!=1)return 11;
  if(result!=(int)current->meta[3]||h!=current->meta[4]||D_800BE9C0!=current->meta[5]||
     D_800DBFF0!=&cameras.values[current->meta[6]]||D_800BE628!=(current->meta[7]?&otherViews.value:&views.value))return 12;
 }
 return 0;}
'''
    return text.replace('ROWS',',\n'.join(rows)).replace('BODY',body)+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),len(rows)
def run():
    out=source.OUT/'native';out.mkdir(exist_ok=True);valid=[];text,count=harness()
    def execute(label,text,opt):
        p=out/(label+'.c');p.write_text(text);exe=out/label
        q=subprocess.run(native_command(opt)+['-fno-builtin-sqrtf',str(p),'-o',str(exe)],cwd=source.ROOT,capture_output=True,text=True)
        assert q.returncode==0,q.stdout+q.stderr
        return subprocess.run([str(exe)],timeout=15,capture_output=True).returncode
    for opt in('-O0','-O2','-O3'):
        code=execute(opt[1:],text,opt);assert code==0,(opt,code)
        valid.append(dict(optimization=opt,cases=count,strict_aliasing=True,UBSan=True,C_defined_conversion_domain=True))
    controls={'inclusive-facing':source.BODY.replace('dx < record->facingThreshold','dx <= record->facingThreshold'),
        'wrong-depth-mantissa':source.BODY.replace('0x7FFU','0x3FFU'),
        'wrong-depth-factor':source.BODY.replace('* 32.0f','* 16.0f')}
    for name,body in controls.items():
        assert body!=source.BODY
        altered,_=harness(body);assert execute(name,altered,'-O2')==12,name
    report=dict(valid=valid,rejected=list(controls),bounded_projection_helper=True,
        guest_aliases_not_claimed_portable_C=True,FP_exceptions_not_qualified=True)
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report
