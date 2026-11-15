"""SDK32 execution of the complete private C against guest-qualified vectors."""
import hashlib,json,subprocess
from tools.experiments import game_motion_effect_150c2c00_recovery as s
from tools.experiments import game_radial_effect_150c29f0_recovery as packet
from tools.tests import game_motion_effect_150c2c00_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
    selected=body((s.OUT/'recovered.c').read_text(),s.NAME)
    controls=dict(threshold=('1.0f < *accumulator','2.0f < *accumulator'),motion=('x * x + z * z','x * x - z * z'),duration=('% 151U','% 150U'),color=('% 156U','% 155U'),kind=('&packet, 10','&packet, 9'),owner=('owner[0xC]','owner[0xB]'),copy=('+ 0x160','+ 0x164'),cached=(' * headingScale + headingBase',' * D_800A02DC + D_800A02D8'))
    code='#include <ultra64.h>\n#include <string.h>\n'+packet.PREAMBLE.replace('extern f32','f32')+s.PREAMBLE.replace('extern f32','f32')
    names=['D_%08X'%(g.CONST+i*4) for i in range(20)]
    arr=lambda vs:'{'+','.join('0x%Xu'%v for v in vs)+'}'
    code+='static f32 *const coefficients[20]={'+','.join('&'+n for n in names)+'};\n'
    code+=r'''
_Static_assert(sizeof(void*)==4 && sizeof(RadialEffectPacket150C29F0)==72,"SDK32 packet");
_Static_assert(__builtin_offsetof(RadialEffectPacket150C29F0,kind34)==0x34,"packet layout");
struct Owner {u8 head[40];f32 accumulator;u8 tail[84];};
static struct {u8 before[32];struct Owner record;} storage;
_Static_assert(sizeof(storage)==160,"owner backing");
static union {u8 bytes[64];f32 floats[16];} motion;
static union {u8 bytes[448];f32 floats[112];} output;
struct Event {u32 target,args[6];};
struct Packet {u8 bytes[72];};
struct Case {u32 seed,policy,outcome,mutation,dt,accumulator;u8 initial[160],final[160],motionInitial[64],motionFinal[64],outputInitial[448],outputFinal[448];u32 globals[20],selector,mark,count,emissions,copies;struct Event calls[80];struct Packet packets[8];};
static const struct Case cases[]={
'''
    values=list(g.cases())
    for c in values:
        initial=g.fixture(c);final,calls,observed,copies=g.reference(initial,c)
        assert len(calls)<=80 and len(observed)<=8
        event=lambda t,a:'{0x%Xu,%s}'%(t,arr(a))
        code+='{'+','.join((str(c.seed),str(c.policy),str(c.outcome),str(c.mutation),str(c.dt)+'U',str(c.accumulator)+'U',arr(g.data(initial,g.OWNER-32,160)),arr(final[g.OWNER-32+i] for i in range(160)),arr(g.data(initial,g.MOTION-16,64)),arr(final[g.MOTION-16+i] for i in range(64)),arr(g.data(initial,g.OUTPUT-32,448)),arr(final[g.OUTPUT-32+i] for i in range(448)),arr(g.read(final,g.CONST+4*i) for i in range(20)),str(g.read(final,g.SELECT))+'U',str(g.read(final,g.MARK))+'U',str(len(calls)),str(len(observed)),str(len(copies)),'{'+','.join(event(t,a) for t,a in calls)+'}','{'+','.join('{'+arr(p)+'}' for p,a in observed)+'}'))+'},\n'
    code+=r'''};
static const struct Case *current;static u32 index,bad,emissions,copies,mark,counts[9];
static const u32 initial[20]=COEFFICIENTS;
f32 D_800BE9A4;s32 D_80082FA4;
static f32 value(u32 u){union{u32 u;f32 f;}x;x.u=u;return x.f;}
static u32 word(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
static void be(u8*p,u32 v,u32 n){u32 i;for(i=0;i<n;i++)p[i]=(u8)(v>>(8*(n-1-i)));}
static u32 count(u32 slot){return counts[slot]++;}
static void event(u32 target,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f){
 const struct Event*v;u32 args[6]={a,b,c,d,e,f},i;
 if(index>=current->count){bad=1;return;}v=&current->calls[index++];if(v->target!=target)bad=2;
 for(i=0;i<6;i++)if(v->args[i]!=args[i])bad=3;}
static void effect(u32 target,u32 n){u32 i;mark=0x13579bdf+target+n*0x10203;
 if(!current->mutation)return;
 if(target==0x150ada68)D_80082FA4^=0x55;
 if(target==0x150484a0){motion.floats[4]=2000.f+n*100.f;motion.floats[6]=-1000.f-n*50.f;}
 if(target==0x15144c8c&&n==0)storage.record.accumulator=3.25f;
 if(target==0x15149550){storage.record.accumulator-=.25f;storage.record.head[12]^=0x55;storage.record.head[1]^=0xa3;}
 if(target==0x150484a0||target==0x15144c8c||target==0x1514373c||target==0x15149550)
  for(i=3;i<20;i++)*coefficients[i]=value(initial[i])*(n&1?1.25f:.75f);}
f32 func_150ADA68(void){u32 n=count(0);static const f32 draws[6]={0.f,.25f,.5f,.75f,1.f,-.5f};event(0x150ada68,0,0,0,0,0,0);effect(0x150ada68,n);return draws[(current->seed+n)%6];}
s32 func_150ADA20(void){u32 n=count(1);static const u32 draws[8]={0,0x80000000,0xffffffff,150,151,155,156,0x7fffffff};event(0x150ada20,0,0,0,0,0,0);effect(0x150ada20,n);return(s32)draws[(current->seed+n)%8];}
f32 *func_15144B34(s32 selector){u32 n=count(2);event(0x15144b34,(u32)selector,0,0,0,0,0);effect(0x15144b34,n);return &motion.floats[4];}
f32 func_150484A0(f32 x,f32 z){u32 n=count(3);event(0x150484a0,word(x),word(z),0,0,0,0);effect(0x150484a0,n);return .125f*(1+n);}
f32 func_15144C8C(f32 angle,f32 heading){u32 n=count(4);event(0x15144c8c,word(angle),word(heading),0,0,0,0);effect(0x15144c8c,n);return current->policy==0||(current->policy==2&&n%2==0)?.2f:.6f;}
static f32 cosine(f32 angle){u32 n=count(5);event(0x15047c00,word(angle),0,0,0,0,0);effect(0x15047c00,n);return n%2==0?.75f:-.5f;}
static f32 sine(f32 angle){u32 n=count(6);event(0x15047d60,word(angle),0,0,0,0,0);effect(0x15047d60,n);return n%2==0?.25f:-.75f;}
void func_1514373C(f32 heading,f32 radius,f32*x,f32*z){u32 n=count(7);f32 c,v;event(0x1514373c,word(heading),word(radius),0,8,0,0);effect(0x1514373c,n);c=cosine(heading);v=sine(heading);*x=radius*v;*z=radius*c;}
void *func_15149550(RadialEffectPacket150C29F0*p,u8 kind,u8 a2,s32 a3,u8 mode,s32 selector){
 u32 n=count(8),i;u8 bytes[72];const u8*raw=(const u8*)p;
 event(0x15149550,0,kind,a2,(u32)a3,mode,(u32)selector);
 if(emissions>=current->emissions){bad=4;return 0;}
 for(i=0;i<72;i++)bytes[i]=raw[i];
 for(i=0;i<32;i+=4)be(bytes+i,word(*(const f32*)(raw+i)),4);
 for(i=0x38;i<72;i+=4)be(bytes+i,word(*(const f32*)(raw+i)),4);
 for(i=0x20;i<=0x24;i+=2)be(bytes+i,*(const u16*)(raw+i),2);
 be(bytes+0x2a,p->flags2A,2);be(bytes+0x30,(u32)p->zero30,4);
 for(i=0;i<72;i++)if((i<0x35||i>=0x38)&&bytes[i]!=current->packets[emissions].bytes[i])bad=5;
 emissions++;effect(0x15149550,n);return current->outcome?(void*)(output.bytes+32):0;}
void *memcpy(void*dst,const void*src,size_t size){u32 i;u8*d=dst;const u8*p=src;
 event(0x10022ec0,0x501a0,0,(u32)size,0,0,0);if(dst!=output.bytes+32+0x160||size!=4)bad=6;
 for(i=0;i<size;i++)d[i]=p[i];copies++;return dst;}
'''.replace('COEFFICIENTS',arr(g.coefficients()))
    for name,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
        if name=='cached':text=text.replace('headingScale = D_800A02DC;','headingScale = D_800A02DC;\n            (void)headingScale; (void)headingBase;')
        if name!='selected':assert text!=selected,name
        code+='\n'+text.replace(s.NAME,'test_'+name,1)+'\n'
    code+=r'''
typedef void (*Test)(u8*);
static int check(Test test){u32 n,i;u8 bytes[448];
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){const struct Case*c=&cases[n];u8*owner=(u8*)&storage;
  current=c;index=bad=emissions=copies=mark=0;for(i=0;i<9;i++)counts[i]=0;
  for(i=0;i<160;i++)owner[i]=c->initial[i];storage.record.accumulator=value(c->accumulator);
  for(i=0;i<64;i++)motion.bytes[i]=c->motionInitial[i];
  for(i=0;i<2;i++){u32 off=16+i*8,v=((u32)c->motionInitial[off]<<24)|((u32)c->motionInitial[off+1]<<16)|((u32)c->motionInitial[off+2]<<8)|c->motionInitial[off+3];motion.floats[4+i*2]=value(v);}
  for(i=0;i<448;i++)output.bytes[i]=c->outputInitial[i];
  for(i=0;i<20;i++)*coefficients[i]=value(initial[i]);D_800BE9A4=value(c->dt);D_80082FA4=(s32)(0x80000000+c->seed);
  test((u8*)&storage.record);
  if(bad||index!=c->count||emissions!=c->emissions||copies!=c->copies||mark!=c->mark||(u32)D_80082FA4!=c->selector)return 1;
  for(i=0;i<160;i++)bytes[i]=owner[i];be(bytes+72,word(storage.record.accumulator),4);
  for(i=0;i<160;i++)if(bytes[i]!=c->final[i])return 2;
  for(i=0;i<64;i++)bytes[i]=motion.bytes[i];be(bytes+16,word(motion.floats[4]),4);be(bytes+24,word(motion.floats[6]),4);
  for(i=0;i<64;i++)if(bytes[i]!=c->motionFinal[i])return 3;
  for(i=0;i<448;i++)bytes[i]=output.bytes[i];if(copies)be(bytes+32+0x160,word(*(f32*)(output.bytes+32+0x160)),4);
  for(i=0;i<448;i++)if(bytes[i]!=c->outputFinal[i])return 4;
  for(i=0;i<20;i++)if(word(*coefficients[i])!=c->globals[i])return 5;
 }return 0;}
static int run(void){if(check(test_selected))return 1;
'''
    for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
    code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    src=s.OUT/'native.c';src.write_text(code);profiles={}
    for opt in ('-O0','-O2','-O3'):
        exe=s.OUT/('native'+opt);q=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True)
        assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.stdout,q.stderr)
        q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr)
        profiles[opt]=dict(cases=len(values),controls=len(controls),UBSan=True,sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
    report=dict(profiles=profiles,owner_bytes=160,motion_bytes=64,output_bytes=448,coefficient_words=20,packet_defined_bytes=69,packet_padding_bytes_uncredited=3,native_source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),private_uninstalled=True,exceptional_fp_not_claimed=True)
    (s.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
