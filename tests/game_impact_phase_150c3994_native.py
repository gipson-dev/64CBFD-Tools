"""SDK32 callback plus the matched C constructor, against guest-qualified cases."""
import hashlib,json,subprocess
from tools.experiments import game_impact_phase_150c3994_match as s
from tools.experiments import game_type07_parameter_record_match as factory
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import game_impact_phase_150c3994_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

CONTROLS={
    'state':('== 20','== 19'),
    'initial-phase':('actor[0x83] == 0','actor[0x83] == 1'),
    'counter-limit':('actor[0x83] >= 11','actor[0x83] >= 12'),
    'sound-threshold':('20.0f <','21.0f <'),
    'heading-offset':(' + 16384)',' + 8192)'),
    'damping':('*= D_800A0334','*= 1.0f'),
    'constructor-width':('2000, 1000, 400, 200','2000, 1000, 401, 200'),
    'flag-clear':('&= 0xFFFF7FFF','&= 0xFFFFBFFF'),
}
def arr(values):return '{'+','.join(str(v&0xFFFFFFFF)+'U' for v in values)+'}'

def main():
    selected=body((s.OUT/'recovered.c').read_text(),s.NAME)
    constructor=body((s.OUT/'production-baseline'/factory.SOURCE).read_text(),factory.FUNCTION)
    assert constructor==body(factory.SELECTED,factory.FUNCTION)
    values=list(g.cases())
    code='''#include <ultra64.h>
typedef struct struct127 struct127;
static u8 storage[0x340] __attribute__((aligned(16)));
static u8 output[192] __attribute__((aligned(16)));
static u8 *actor=storage+32;
static u32 mark;
'''+s.PREAMBLE.replace('extern f32','f32')+'''
void func_15059140(struct127 *);
s32 func_150C3D5C(u8 *);
void func_15060F28(struct127 *,s32);
void func_10010630(u16,struct127 *,s32,s16,u16);
s32 func_10010344(u16,void *,s32,s16,u16);
struct Event {u32 target,count,args[16];};
struct Case {u32 seed,mutation,outcome,mark,count,success;u8 initial[0x340],final[0x340],outputInitial[192],outputFinal[192];struct Event calls[20];};
static const struct Case cases[]={
'''
    for c in values:
        initial=g.fixture(c);final,calls,allocated=g.reference(initial,c);assert len(calls)<=20
        events='{'+','.join('{'+str(t)+'U,'+str(len(a))+'U,'+arr(a)+'}' for t,a in calls)+'}'
        row=(str(c.seed),str(c.mutation),str(c.outcome),str(g.read(final,g.MARK))+'U',str(len(calls)),str(sum(1<<((p-g.OUTPUT)//64) for p in allocated)),arr(initial[g.OWNER-32+i] for i in range(0x340)),arr(final[g.OWNER-32+i] for i in range(0x340)),arr(initial[g.OUTPUT-32+i] for i in range(192)),arr(final[g.OUTPUT-32+i] for i in range(192)),events)
        code+='{'+','.join(row)+'},\n'
    code+='''};
static const struct Case *current;
static u32 index,bad,success,counts[10];
static const u32 floats[]={FLOAT_OFFSETS};
static const u32 words[]={WORD_OFFSETS};
static const u32 halves[]={HALF_OFFSETS};
static f32 value(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static u32 word(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
static u32 be(const u8*p,u32 n){u32 v=0,i;for(i=0;i<n;i++)v=v*256+p[i];return v;}
static void storebe(u8*p,u32 v,u32 n){u32 i;for(i=0;i<n;i++)p[i]=(u8)(v>>(8*(n-1-i)));}
static u32 raw(const u8*p,u32 n){u32 v=0,i;u8*q=(u8*)&v;for(i=0;i<n;i++)q[i]=p[i];return v;}
static void store(u8*p,u32 v,u32 n){u32 i;u8*q=(u8*)&v;for(i=0;i<n;i++)p[i]=q[i];}
static u32 address(const void*p){return (u32)((const u8*)p-actor)+0x30040U;}
static void event(u32 t,u32 n,const u32*args){const struct Event*v;u32 i;
 if(index>=current->count){bad=1;return;}v=&current->calls[index++];if(t!=v->target||n!=v->count)bad=2;
 for(i=0;i<n;i++)if(args[i]!=v->args[i])bad=3;
}
static u32 effect(u32 t,u32 slot){u32 n=counts[slot]++;
 mark=0x13579bdfU+t+n*0x10203U;
 if(!current->mutation)return n;
 if(t==0x15167a68){if(current->mutation==1)*(s32*)(actor+0x2e4)=1;else actor[0x83]=0;}
 else if(t==0x15188810){*(s32*)(actor+0x2e4)=0;if(current->mutation==2)actor[0x83]=0;}
 else if(t==0x10010630){if(current->mutation==2)actor[0x83]=0;}
 else if(t==0x150c1660){*(f32*)(actor+0x14)=17.f;*(f32*)(actor+0x18)=-25.f;*(f32*)(actor+0x1c)=35.f;}
 else if(t==0x1506ac8c){actor[0x83]=255;*(u32*)(actor+0xf8)=0x80000000U;}
 else if(t==0x10010344){static const u8 phases[3]={9,20,255};actor[0x83]=phases[current->seed%3];*(u32*)(actor+0xf8)=0x12340000;}
 else if(t==0x15059140){*(f32*)(actor+0x148)=-5.f;*(f32*)(actor+0xb8)=13.f;if(current->mutation==2){*(f32*)(actor+0x28)=0.f;actor[0x107]=1;}}
 else if(t==0x150c3d5c)actor[0xd0]^=0x55;
 else if(t==0x15060f28)actor[0xd0]^=0xa3;
 return n;
}
void *func_15167A68(s32 a,s32 b,s32 c,s32 d,u8 e,u8 f){u32 n,i;u8*p;
 event(0x15167a68,6,(u32[]){(u32)a,(u32)b,(u32)c,(u32)d,e,f});n=effect(0x15167a68,1);
 if(n>=2){bad=4;return 0;}if(!(current->outcome==1||(current->outcome==2&&n%2==0)))return 0;
 p=output+32+64*n;for(i=0;i<44;i++)p[i]=(u8)(i*19+current->seed*7+n*23+0x31);success|=1U<<n;return p;
}
'''.replace('FLOAT_OFFSETS',','.join(map(str,g.FLOATS))).replace('WORD_OFFSETS',','.join(map(str,g.WORDS))).replace('HALF_OFFSETS',','.join(map(str,g.HALVES)))
    code+=factory.DECLARATIONS+constructor.replace('func_151B9BF0','constructor_impl',1)+'\n'
    code+='''
_Static_assert(sizeof(Type07ParameterRecord)==44,"record layout");
void func_151B9BF0(s32 a,s32 b,s16 c,s16 d,s16 e,s16 f,s16 h,s16 i,s16 j,s16 k,s16 l,s16 m,s16 n,u32 v,u8 view,s32 context){
 event(0x151b9bf0,16,(u32[]){(u32)a,(u32)b,(u32)c,(u32)d,(u32)e,(u32)f,(u32)h,(u32)i,(u32)j,(u32)k,(u32)l,(u32)m,(u32)n,v,view,(u32)context});
 constructor_impl(a,b,c,d,e,f,h,i,j,k,l,m,n,v,view,context);
}
void func_15188810(u8*a,s32 b,s32 c){event(0x15188810,3,(u32[]){address(a),(u32)b,(u32)c});effect(0x15188810,2);}
void func_10010630(u16 a,struct127*b,s32 c,s16 d,u16 e){event(0x10010630,5,(u32[]){a,address(b),(u32)c,(u32)d,e});effect(0x10010630,3);}
void func_150C1660(f32 a,f32 b,f32 c,u8 d){event(0x150c1660,4,(u32[]){word(a),word(b),word(c),d});effect(0x150c1660,4);}
void func_1506AC8C(void*a,s32 b,s32 c){event(0x1506ac8c,3,(u32[]){address(a),(u32)b,(u32)c});effect(0x1506ac8c,5);}
s32 func_10010344(u16 a,void*b,s32 c,s16 d,u16 e){event(0x10010344,5,(u32[]){a,address(b),(u32)c,(u32)d,e});effect(0x10010344,6);return(s32)0xd00d0000U;}
void func_15059140(struct127*a){event(0x15059140,1,(u32[]){address(a)});effect(0x15059140,7);}
s32 func_150C3D5C(u8*a){event(0x150c3d5c,1,(u32[]){address(a)});effect(0x150c3d5c,8);return(s32)0xd00d0000U;}
void func_15060F28(struct127*a,s32 b){event(0x15060f28,2,(u32[]){address(a),(u32)b});effect(0x15060f28,9);}
'''
    for name,text in [('selected',selected)]+[(n,selected.replace(a,b,1)) for n,(a,b) in CONTROLS.items()]:
        if name!='selected':assert text!=selected,name
        code+='\n'+text.replace(s.NAME,'test_'+name.replace('-','_'),1)+'\n'
    code+='''
typedef void (*Test)(u8*);
static int check(Test test){u32 n,i,j,p;u8 bytes[0x340];
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];current=c;index=bad=success=mark=0;
  for(i=0;i<10;i++)counts[i]=0;
  for(i=0;i<0x340;i++)storage[i]=c->initial[i];
  for(i=0;i<192;i++)output[i]=c->outputInitial[i];
  for(i=0;i<sizeof(floats)/sizeof(floats[0]);i++){p=32+floats[i];store(storage+p,be(c->initial+p,4),4);}
  for(i=0;i<sizeof(words)/sizeof(words[0]);i++){p=32+words[i];store(storage+p,be(c->initial+p,4),4);}
  for(i=0;i<sizeof(halves)/sizeof(halves[0]);i++){p=32+halves[i];store(storage+p,be(c->initial+p,2),2);}
  D_800A0334=value(0x3f75c28f);
  test(actor);
  if(bad||index!=c->count||mark!=c->mark||success!=c->success)return 1;
  for(i=0;i<0x340;i++)bytes[i]=storage[i];
  for(i=0;i<sizeof(floats)/sizeof(floats[0]);i++){p=32+floats[i];storebe(bytes+p,raw(storage+p,4),4);}
  for(i=0;i<sizeof(words)/sizeof(words[0]);i++){p=32+words[i];storebe(bytes+p,raw(storage+p,4),4);}
  for(i=0;i<sizeof(halves)/sizeof(halves[0]);i++){p=32+halves[i];storebe(bytes+p,raw(storage+p,2),2);}
  for(i=0;i<0x340;i++)if(bytes[i]!=c->final[i])return 2;
  for(i=0;i<192;i++)bytes[i]=output[i];
  for(j=0;j<2;j++)if(success&(1U<<j)){
   p=32+64*j;storebe(bytes+p+16,raw(output+p+16,4),4);
   for(i=0;i<11;i++)storebe(bytes+p+22+2*i,raw(output+p+22+2*i,2),2);
  }
  for(i=0;i<192;i++)if(bytes[i]!=c->outputFinal[i])return 3;
 }return 0;
}
static int run(void){if(check(test_selected))return 1;
'''
    for i,name in enumerate(CONTROLS):code+='if(!check(test_'+name.replace('-','_')+'))return '+str(20+i)+';\n'
    code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    src=s.OUT/'native.c';src.write_text(code);profiles={}
    for opt in ('-O0','-O2','-O3'):
        exe=s.OUT/('native'+opt);p=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True)
        assert p.returncode==0 and not p.stdout and not p.stderr,(opt,p.stdout,p.stderr)
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stderr)
        profiles[opt]=dict(cases=len(values),effective_controls=len(CONTROLS),UBSan=True,sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
    report=dict(profiles=profiles,finite_only=True,owner_bytes=0x340,output_bytes=192,constructor='matched C implementation',source_sha256=hashlib.sha256(src.read_bytes()).hexdigest())
    (s.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
