from pathlib import Path
import json,subprocess
from tools.tests import game_actor_randomized_effect_150f97ec_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_actor_randomized_effect_150f97ec_recovery as source
OUT=source.OUT;ROOT=source.ROOT;SPEC=source.SPEC
def hashseq(values):
    h=2166136261
    for v in values:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
    return h
def rows():
    result=[]
    for c in g.cases():
        memory,trace=g.reference(g.fixture(c),c)
        h=hashseq([v for target,args,state,arrays in trace for v in(target,len(args),*args,*state,len(arrays),*arrays)])
        values=[c.seed,c.enabled,c.selector,c.priority,c.parameter,c.mode,c.phase,*c.reals,*c.integers,h,hashseq(g.snapshot(memory)),len(trace)]
        result.append('{'+','.join('0x%Xu'%v for v in values)+'}')
    return ',\n'.join(result),len(result)
def harness(body):
    data,count=rows();code='#include <ultra64.h>\n#include "structs.h"\nf32 func_150ADA68(void);\n'+SPEC['preamble']+r'''
static const u32 cases[][15]={ROWS};
static const u32 *current;static struct127 actor;
static u32 bank[4096],other[4096];
u8 D_80088B50;f32 D_800A1C48[3]={-124.0f,-8.0f,28.0f},D_800A1C54[3]={-170.0f,-8.0f,28.0f};
static struct17 *point;static struct17 **inputHome,**outputHome;
static u32 trace,ordinal,realCalls,integerCalls,error;
static u32 hash(u32 h,u32 v){return(h^v)*16777619u;}
static u32 word(f32 f){union{f32 f;u32 w;}v;v.f=f;return v.w;}
static f32 real(u32 w){union{f32 f;u32 w;}v;v.w=w;return v.f;}
static u32 at(const void*p){const u8*b=p;return b[0]|(u32)b[1]<<8|(u32)b[2]<<16|(u32)b[3]<<24;}
static void store(void*p,u32 w){u8*b=p;u32 i;for(i=0;i<4;i++)b[i]=w>>(8*i);}
static u32 address(const void*p){
 if(!p)return 0;if(p==&actor)return 0x30000u;
 if((u32)p>=(u32)bank&&(u32)p<(u32)bank+sizeof(bank))return 0x50000u+(u32)p-(u32)bank;
 if((u32)p>=(u32)other&&(u32)p<(u32)other+sizeof(other))return 0x60000u+(u32)p-(u32)other;
 if(p==D_800A1C48)return 0x800A1C48u;if(p==D_800A1C54)return 0x800A1C54u;
 error=1;return 0xDEAD0000u;}
static u32 state(u32 h){h=hash(h,at(&actor));h=hash(h,address(actor.unk1D4));return hash(h,D_80088B50);}
static void call(u32 target,u32 n,const u32*args,f32*scale){u32 i;
 ordinal++;trace=hash(hash(trace,target),n);for(i=0;i<n;i++)trace=hash(trace,args[i]);trace=state(trace);
 trace=hash(trace,scale?5:0);if(scale){for(i=0;i<2;i++)trace=hash(trace,at((u8*)scale+i*4));for(i=0;i<3;i++)trace=hash(trace,at((u8*)point+i*4));}}
static void mutate(u32 target){u32 i;
 if(current[5]==1&&target==0x150ADA68u){D_80088B50+=17;actor.unk1D4=(struct255*)other;}
 if(current[5]==2&&target==0x150ADA20u){D_80088B50=255;actor.unk1D4=0;}
 if(current[5]==3){
  for(i=0;i<3;i++)store((u8*)point+i*4,word(real(at((u8*)point+i*4))+(i+1)*0.25f));
  *inputHome=(struct17*)D_800A1C54;*outputHome=(struct17*)other;}}
__attribute__((noinline,noipa)) void func_15145EA4(struct17**in,struct17**out,u8*matrix,s32 count){
 u32 args[4]={0xF0010010u,0xF0010014u,address(matrix),(u32)count};
 if(*in!=(struct17*)D_800A1C48||count!=1)error=1;point=*out;inputHome=in;outputHome=out;
 call(0x15145EA4u,4,args,0);
 point->unk0=(f32)((s32)(current[0]%17)-8);point->unk4=((s32)(current[0]%13)-6)*0.5f;point->unk8=(f32)((s32)(current[0]%7)-3);}
__attribute__((noinline,noipa)) f32 func_150ADA68(void){call(0x150ADA68u,0,0,0);mutate(0x150ADA68u);return real(current[7+realCalls++]);}
__attribute__((noinline,noipa)) s32 func_150ADA20(void){call(0x150ADA20u,0,0,0);mutate(0x150ADA20u);return(s32)current[10+integerCalls++];}
__attribute__((noinline,noipa)) u8 *func_15102B38(u8*owner,u8 selector,f32*first,f32*second,f32*scale,s16 kind,u8 duration,f32 angle,f32*position,u8 alpha,s32 zero,s16 channel,u8 priority,s32 parameter){
 u32 args[14]={address(owner),selector,address(first),address(second),0xF0010020u,(s32)kind,duration,word(angle),0xF0010000u,alpha,zero,(s32)channel,priority,parameter};
 if(position!=(f32*)point)error=1;call(0x15102B38u,14,args,scale);store(&actor,current[0]^0x12345678u);
 if(current[5]==3){scale[0]=(f32)ordinal;scale[1]=(f32)(ordinal+1);point->unk0=-17.0f;}
 return(u8*)other;}
BODY
static int run(void){u32 i,j;u8*bytes=(u8*)&actor;
 if(sizeof(void*)!=4||sizeof(struct17)!=12||__builtin_offsetof(struct127,unk1D4)!=0x1D4)return 10;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  current=cases[i];for(j=0;j<sizeof(actor);j++)bytes[j]=0xA5;
  for(j=0;j<4096;j++)bank[j]=other[j]=0xA5A5A5A5u;
  actor.unk1D4=current[1]?(struct255*)bank:0;D_80088B50=current[2];
  trace=2166136261u;ordinal=realCalls=integerCalls=error=0;point=0;inputHome=outputHome=0;
  func_150F97EC(&actor,current[3],(s32)current[4]);
  if(error||trace!=current[12]||state(2166136261u)!=current[13]||ordinal!=current[14])return 11;
  for(j=0;j<sizeof(actor);j++)if(!(j<4||(j>=0x1D4&&j<0x1D8))&&bytes[j]!=0xA5)return 12;
  for(j=0;j<4096;j++)if(bank[j]!=0xA5A5A5A5u||other[j]!=0xA5A5A5A5u)return 13;
 }return 0;}
'''
    return code.replace('ROWS',data).replace('BODY',body)+START,count
def run():
    where=OUT/'native';where.mkdir(exist_ok=True);body=SPEC['body'];valid=[];rejected={}
    def execute(name,text,opt):
        code,count=harness(text);p=where/(name+'.c');p.write_text(code);exe=p.with_suffix('')
        q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        assert q.returncode==0,q.stdout+q.stderr
        return subprocess.run([str(exe)],capture_output=True,timeout=30).returncode,count
    for opt in('-O0','-O2','-O3'):
        code,count=execute(opt[1:],body,opt);assert code==0,(opt,code)
        valid.append(dict(optimization=opt,cases=count,strict_aliasing=True,UBSan=True))
    controls={'wrong-unit-span':body.replace('span = 1.0f;','span = 2.0f;'),
              'signed-RNG-modulo':body.replace('random[0] % 3U','(s32)random[0] % 3'),
              'wrong-final-parameter':body.replace('255, 0, -1, priority, parameter','255, 0, -1, priority, 0')}
    for name,text in controls.items():
        assert text!=body;code,_=execute(name,text,'-O2');assert code==11,(name,code);rejected[name]=code
    report=dict(valid=valid,rejected=rejected,full_typed_actor=True,complete_native_objects=True,helpers_are_bounded_providers=True,matching_credit=0)
    (OUT/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
