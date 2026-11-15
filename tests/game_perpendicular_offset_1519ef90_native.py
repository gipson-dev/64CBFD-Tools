"""Native32 typed-object checks; guest-only aliases/mode-home writes excluded."""
import itertools,json,subprocess
from tools.experiments import game_perpendicular_offset_1519ef90_recovery as s
from tools.tests import game_perpendicular_offset_1519ef90_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def source():
    corpus=[c for c in g.finite_cases() if c.alias==0 and not c.effects&2]
    corpus += [g.Case(dx=0,dz=0,heading=h,mode=m) for h,m in itertools.product(range(256),(6,7))]
    rows=[]
    for c in corpus:
        result,m,calls=g.reference(g.fixture(c),c)
        expected=[g.read(m,g.OUTPUT+4*i) for i in range(3)]
        if not c.present:expected=[0xA5A5A5A5]*3
        callrows=['{%d,0x%Xu}'%(t,a[0]) for t,a in calls]+['{0,0}']*(3-len(calls))
        values=[c.dx,c.dz,c.height,c.offset,c.mode,c.present,c.heading,c.effects,result,len(calls)]
        rows.append('{'+','.join('0x%Xu'%(x&0xffffffff) for x in values)+',{'+','.join('0x%Xu'%x for x in expected)+'},{'+','.join(callrows)+'}}')
    table=[g.helper_data()[1][s.symbols()['D_8009A220']+4*i] for i in range(65)]
    prefix='''#include <ultra64.h>
#include "structs.h"
'''+s.PIN['declarations']+'''
f32 D_800A8CE0, D_800A8CE4;
typedef struct {u32 dx,dz,height,offset,mode,present,heading,effects,want,count,out[3],calls[3][2];} NativeCase;
static struct127 actor;
static SideState1519EF90 state,otherState;
typedef struct {SideState1519EF90 *state;u8 retained04[0x1C];f32 reference[3];} NativeRecord;
static NativeRecord record;
static f32 output[3];
static const NativeCase *current;
static u32 ordinal,calls[3][2];
static f32 number(u32 word){union {u32 u;f32 f;} v;v.u=word;return v.f;}
static u32 word(f32 number){union {u32 u;f32 f;} v;v.f=number;return v.u;}
f32 fabsf(f32 x){return number(word(x)&0x7FFFFFFFu);}
f32 sqrtf(f32 x){f32 y;__asm__("sqrtss %1,%0":"=x"(y):"x"(x));return y;}
typedef char actor_position_check[__builtin_offsetof(struct127,x_position)==0x14?1:-1];
typedef char actor_height_check[__builtin_offsetof(struct127,unk118)==0x118?1:-1];
typedef char actor_attachment_check[__builtin_offsetof(struct127,unk1D4)==0x1D4?1:-1];
typedef char state_parameter_check[__builtin_offsetof(SideState1519EF90,parameters)==0x58?1:-1];
typedef char record_reference_check[__builtin_offsetof(NativeRecord,reference)==0x20?1:-1];
static void effects(u32 n){
 if(current->effects&1){actor.x_position=10.f+n;actor.y_position=20.f+n;actor.z_position=-15.f-n;actor.unk118=-9600.f+n;state.parameters.offset=3.f+n;record.state=&otherState;state.actor=0;}
}
s32 func_15143E08(struct127 *p){
 u32 n=ordinal++,result=((p->unk7A>>8)+64)&255;
 if(n>=3)__builtin_trap();calls[n][0]=0x15143E08;calls[n][1]=p==&actor?0x32000:0;
 effects(n);return result;
}
'''
    prefix+='static const u32 table[65]={'+','.join('0x%Xu'%x for x in table)+'};\n'
    prefix+='''f32 func_151423D8(u8 a){
 u32 n=ordinal++,index=(a&64)?64-(a&63):(a&63),value=table[index];
 if(n>=3)__builtin_trap();calls[n][0]=0x151423D8;calls[n][1]=a;
 if((a&192)!=0&&(a&192)!=192)value^=0x80000000u;
 if(current->effects&4)value=n==1?0x3E800000:0xBF400000;
 effects(n);return number(value);
}
'''
    body=s.PIN['source']
    harness='static const NativeCase corpus[]={\n'+',\n'.join(rows)+'\n};\n'
    harness+='''static int run(void){
 for(u32 i=0;i<sizeof(corpus)/sizeof(corpus[0]);i++){
  const NativeCase *c=&corpus[i];current=c;ordinal=0;
  record.state=&state;record.reference[0]=record.reference[1]=0.f;
  state.actor=&actor;state.parameters.offset=number(c->offset);
  actor.x_position=number(c->dx);actor.z_position=number(c->dz);actor.y_position=12.5f;actor.unk118=number(c->height);actor.unk7A=((c->heading-64)&255)<<8;actor.unk1D4=c->present?(struct255 *)&actor:0;
  for(u32 j=0;j<3;j++)output[j]=number(0xA5A5A5A5);
  D_800A8CE0=number(0x38D1B717);D_800A8CE4=number(0xC6147000);
  if((u32)func_1519EF90((u8 *)&record,c->mode,output)!=c->want||ordinal!=c->count)return 41;
  for(u32 j=0;j<3;j++)if(word(output[j])!=c->out[j])return 42;
  for(u32 j=0;j<ordinal;j++)if(calls[j][0]!=c->calls[j][0]||calls[j][1]!=c->calls[j][1])return 43;
 }
 return 0;
}
'''
    return prefix+body+'\n'+harness+START,len(corpus)

def main():
    text,count=source();path=s.OUT/'native.c';path.write_text(text);profiles=[];controls=0
    mutants={
        'gate':text.replace('if (*(void **)(actor + 0x1D4) == 0)','if (*(void **)(actor + 0x1D4) != 0)'),
        'mode':text.replace('if (mode == 6)','if (mode == 7)'),
        'direction':text.replace('offset * tangentX','offset * (tangentX + tangentZ)'),
        'height':text.replace('*(f32 *)(actor + 0x118) < D_800A8CE4','*(f32 *)(actor + 0x118) > D_800A8CE4')}
    for label,wrong in mutants.items():assert wrong!=text,label
    for opt in ('-O0','-O2','-O3'):
        for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
            exe=s.OUT/('native'+opt+alias);p=subprocess.run(native_command(opt)+['-mstackrealign',alias,'-o',str(exe),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
            q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr)
            profiles.append(opt+alias)
        for label,wrong in mutants.items():
            bad=s.OUT/('native-control-'+label+'.c');bad.write_text(wrong);exe=bad.with_suffix('')
            p=subprocess.run(native_command(opt)+['-mstackrealign','-o',str(exe),str(bad)],capture_output=True,text=True);assert p.returncode==0,p.stderr
            assert subprocess.run([str(exe)],capture_output=True).returncode in(41,42,43),label;controls+=1
    report=dict(cases_per_profile=count,profiles=profiles,effective_source_controls=controls,UBSan=True,
                actual_typed_actor_and_state=True,guest_only_output_aliases_and_mode_home_mutation=True)
    (s.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
