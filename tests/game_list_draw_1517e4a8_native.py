from pathlib import Path
import json,subprocess
from tools.tests import game_list_draw_1517e4a8_oracle as g
from tools.experiments import game_list_draw_1517e4a8_recovery as source
from tools.experiments.game_list_render_1517e28c_recovery import RECORD
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ROOT=source.ROOT;OUT=source.OUT
BODY=source.BODY

def hseq(values):
    h=2166136261
    for v in values:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
    return h
def trace_hash(trace):
    return hseq([v for target,args,state,packet in trace for v in(target,len(args),*args,*state,len(packet),*packet)])
def public_hash(m):
    return hseq([*g.snapshot(m),*[g.read(m,b+4*i)for b in(g.CURSOR,g.OTHER)for i in range(512)]])
def rows():
    result=[]
    for c in g.cases():
        memory=g.fixture(c);want,trace,cursor=g.reference(memory,c)
        values=[c.seed,c.width,c.height,g.bits(c.x),g.bits(c.y),c.state&65535,c.enabled,c.group,c.count&0xFFFFFFFF,
            c.falloff,c.strength&0xFFFFFFFF,c.intensity,c.old_intensity,c.ticks,c.touched,c.mode,
            cursor,trace_hash(trace),public_hash(want),len(trace)]
        result.append('{'+','.join('0x%Xu'%v for v in values)+'}')
    return ',\n'.join(result),len(result)

def harness(body=BODY):
    data,count=rows();preamble=source.PREAMBLE
    code='#include <ultra64.h>\n'+RECORD+'\n'+preamble+r'''
static const u32 cases[][20]={ROWS};
static const u32 *current;
static struct Slot {ListRecord1AB530 record;u8 tail[12];} node;
static Gfx commands[256],other[256];
static u8 intensityStorage[4];
FlareDescriptor1AB530 D_800903AC;
static FlareDescriptor1AB530 alternateDescriptor;
const u8 D_800A7250[16]={128,64,128,255,128,64,128,32,64,32,32,32,32,32,0,0};
s32 D_800BE620,D_800BE624,D_800BE9E4;
f32 D_800380A0,D_800380A4;
u8 D_800DDD60,D_800D2DA8,D_800D2DA9,D_800D2DAA,D_800D2DAB;
static u32 trace,ordinal,error,expectedPacketSeen;
static FlareDrawPacket1AB530 *packetIdentity;
static u32 hash(u32 h,u32 w){return(h^w)*16777619u;}
static u32 word(f32 x){union{u32 w;f32 f;}v;v.f=x;return v.w;}
static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
f32 fabsf(f32 x){return real(word(x)&0x7FFFFFFFu);}
static u32 address(const void*p){u32 a=(u32)p;
 if(!p)return 0;
 if(a>=(u32)commands&&a<(u32)commands+sizeof(commands))return 0x50000u+a-(u32)commands;
 if(a>=(u32)other&&a<(u32)other+sizeof(other))return 0x60000u+a-(u32)other;
 if(p==&D_800903AC)return 0x800903ACu;
 if(p==&alternateDescriptor)return 0x800903B8u;
 error=1;return 0xDEAD0000u;}
static u32 stateHash(u32 h){
 h=hash(h,word(node.record.valueC));h=hash(h,word(node.record.value10));h=hash(h,(u16)node.record.state28);h=hash(h,node.record.second30);
 h=hash(h,D_800BE620);h=hash(h,D_800BE624);h=hash(h,D_800BE9E4);h=hash(h,D_800DDD60);h=hash(h,word(D_800380A0));h=hash(h,word(D_800380A4));
 h=hash(h,D_800D2DA8);h=hash(h,D_800D2DA9);h=hash(h,D_800D2DAA);h=hash(h,D_800D2DAB);return hash(h,intensityStorage[0]);}
static void call(u32 target,u32 n,const u32 *args,FlareDrawPacket1AB530*p){u32 i;
 ordinal++;trace=hash(hash(trace,target),n);for(i=0;i<n;i++)trace=hash(trace,args[i]);trace=stateHash(trace);trace=hash(trace,p?7:0);
 if(p){
  if(expectedPacketSeen&&packetIdentity!=p)error=1;packetIdentity=p;expectedPacketSeen=1;
  trace=hash(trace,(u16)p->extentX);trace=hash(trace,(u16)p->extentY);trace=hash(trace,p->alpha);
  trace=hash(trace,p->animationStep);trace=hash(trace,p->animationFrame);trace=hash(trace,p->flipFlags);trace=hash(trace,address(p->descriptor));}}
__attribute__((noinline,noipa)) Gfx *func_1517EA4C(Gfx*p){u32 args[1]={address(p)};call(0x1517EA4Cu,1,args,0);
 gDPPipeSync(p++);gDPSetCombine(p++,0xFFB3FF,0xFF65FEFF);gDPSetOtherMode(p++,0x2C0F,0x504344);return p;}
__attribute__((noinline,noipa)) s32 func_150950D4(s32 output,FlareDescriptor1AB530*descriptor,s32 a2,s32 a3,s32 a4,s32 a5,s32 a6,s32 a7,s32 a8,s32 a9){
 Gfx*p=(Gfx*)(u32)output;u32 args[10]={address(p),address(descriptor),a2,a3,a4,a5,a6,a7,a8,a9};
 call(0x150950D4u,10,args,0);
 if(descriptor!=&D_800903AC||a2||a3||a4||a5||a6!=2||a7!=256||a8!=256||a9!=3)error=1;
 p->words.w0=0xCE000000u|ordinal;p->words.w1=0x12345678u;
 if(current[15]==1){node.record.valueC+=0.25f;node.record.value10-=0.5f;node.record.state28=97;node.record.second30=255;
  D_800380A0=1.25f;D_800380A4=0.75f;D_800BE620=1280;D_800BE624=720;D_800BE9E4=7;D_800D2DA8=17;}
 return(s32)(p+1);}
__attribute__((noinline,noipa)) s32 func_15095A90(s32 output,s32 packetAddress,f32 x,f32 y,f32 divisor,s32 projected,s32 sOffset,s32 inset,s32 adjust){
 Gfx*p=(Gfx*)(u32)output;FlareDrawPacket1AB530*packet=(FlareDrawPacket1AB530*)(u32)packetAddress;
 u32 args[4]={address(p),0xF0010000u,word(x),word(y)};
 if(word(divisor)!=0x45800000u||projected||sOffset||inset||adjust)error=1;
 call(0x15095A48u,4,args,packet);p->words.w0=0xCB000000u|ordinal;p->words.w1=word(x)^word(y);
 if(current[15]==2){node.record.valueC+=1.0f;node.record.value10-=2.0f;node.record.state28=-7;node.record.second30=0;
  D_800380A0+=0.25f;D_800380A4*=0.5f;packet->animationStep++;packet->animationFrame+=2;packet->flipFlags^=16;packet->descriptor=&alternateDescriptor;}
 if(current[15]==3){D_800DDD60=0;D_800D2DA9=ordinal;return(s32)((u8*)other+ordinal*16);}
 return(s32)(p+1+(current[0]+ordinal)%2);}
__attribute__((noinline,noipa)) Gfx *func_15095A48(Gfx *output,FlareDrawPacket1AB530 *packet,f32 x,f32 y){
 return(Gfx*)(u32)func_15095A90((s32)output,(s32)packet,x,y,4096.0f,0,0,0,0);}
BODY
static u32 initial(u32 i){return(((i*19+0xB7)&255)<<24)|((((i+1)*19+0xB7)&255)<<16)|((((i+2)*19+0xB7)&255)<<8)|(((i+3)*19+0xB7)&255);}
static u32 digest(void){u32 h=stateHash(2166136261u),i;
 for(i=0;i<256;i++){h=hash(h,commands[i].words.w0);h=hash(h,commands[i].words.w1);}
 for(i=0;i<256;i++){h=hash(h,other[i].words.w0);h=hash(h,other[i].words.w1);}return h;}
static int run(void){u32 c,i;u8 *ptr,*bytes=(u8*)&node;Gfx*result;
 if(sizeof(void*)!=4||sizeof(ListRecord1AB530)!=52||sizeof(FlareDrawPacket1AB530)!=20||__builtin_offsetof(FlareDrawPacket1AB530,descriptor)!=16)return 10;
 for(c=0;c<sizeof(cases)/sizeof(cases[0]);c++){
 current=cases[c];trace=2166136261u;ordinal=error=expectedPacketSeen=0;packetIdentity=0;
 for(i=0;i<sizeof(node);i++)bytes[i]=(i*19+0xB7)&255;
 node.record.valueC=real(current[3]);node.record.value10=real(current[4]);node.record.state28=current[5];node.record.second30=current[6];
 for(i=0;i<4;i++)intensityStorage[i]=(i*19+0xB7)&255;intensityStorage[0]=current[12];
 for(i=0;i<256;i++){commands[i].words.w0=other[i].words.w0=initial(i*8);commands[i].words.w1=other[i].words.w1=initial(i*8+4);}
 D_800BE620=current[1];D_800BE624=current[2];D_800BE9E4=current[13];D_800DDD60=current[14];D_800380A0=1.0f;D_800380A4=0.5f;
 D_800D2DA8=D_800D2DA9=D_800D2DAA=D_800D2DAB=0xA5;
 ptr=current[11]==0?0:current[11]==1?intensityStorage:current[11]==2?(u8*)&node.record.state28+1:current[11]==3?(u8*)&node.record.state28:(u8*)&node.record.second30;
 result=func_1517E4A8(commands,&node.record,current[7],(s32)current[8],current[9],(s32)current[10],ptr);
 if(error||ordinal!=current[19]||trace!=current[17]||address(result)!=current[16]||digest()!=current[18])return 11;
 for(i=0;i<sizeof(node);i++)if(!((i>=12&&i<20)||(i>=40&&i<42)||i==48)&&bytes[i]!=((i*19+0xB7)&255))return 12;
 }return 0;}
'''
    return code.replace('ROWS',data).replace('BODY',body)+START,count

def run():
    where=OUT/'native';where.mkdir(exist_ok=True);valid=[];rejected={}
    def execute(name,body,opt):
        text,count=harness(body);p=where/(name+'.c');p.write_text(text);exe=p.with_suffix('')
        q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        assert q.returncode==0,q.stdout+q.stderr
        return subprocess.run([str(exe)],capture_output=True,timeout=15).returncode,count
    for opt in('-O0','-O2','-O3'):
        code,count=execute(opt[1:],BODY,opt);assert code==0,(opt,code)
        valid.append(dict(optimization=opt,cases=count,UBSan=True,strict_aliasing=True))
    controls={'wrong-distance-cutoff':BODY.replace('distance < 200000','distance < 200001'),
      'wrong-packet-alpha':BODY.replace('packet.alpha = value;','packet.animationStep = value;'),
      'wrong-brightness-numerator':BODY.replace('1760000 /','1750000 /')}
    for name,body in controls.items():
        assert body!=BODY;code,count=execute(name,body,'-O2');assert code in(11,12),(name,code);rejected[name]=code
    r=dict(valid=valid,rejected=rejected,compatible_objects=True,typed_return_wrapper_connected=True,uninitialized_packet_coordinates_unobserved=True)
    (where/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':run()
