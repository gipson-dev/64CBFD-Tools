"""Defined SDK32 sequence objects, typed helper side effects and C controls."""
import json,subprocess
from pathlib import Path
from tools.experiments import game_sequence_direction_1501fe68_match as p
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 body=(p.out/'selected-body.c').read_text(encoding='utf-8')
 pre='''#include <ultra64.h>
typedef struct {f32 duration;u32 *items;u8 pad08[0x30];u8 *scratch;u8 pad3C[4];} SequenceRuntime49D30;
typedef struct {u8 pad00[6];u16 flag;} SequenceFrameKey49D30;
u16 *D_800C35C8[2];SequenceRuntime49D30 *D_800C3A50[2];u8 *D_800C3868[2][30];
f32 D_800969D8,D_800969DC;
static u16 rows[2][2],altrow[2];static SequenceRuntime49D30 runtimes[2][2];
static SequenceFrameKey49D30 keys[2],altkeys[2];static f32 result;
static const f32 POINTS[6]={8.f,-2.f,15.f,-3.f,4.f,1.f};
static const f32 MATRIX[12]={0.f,1.f,2.f,3.f,4.f,5.f,12.f,7.f,21.f,9.f,10.f,11.f};
static int group0,index0,frame0,count0,active0,flag0,mutation0,helper_calls,errors;
static f32 expected_time,expected_x,expected_z,answer;static u32 duration_bits=0x41200000u;
static u8 *expected_keys;
static u32 as_bits(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
static f32 as_float(u32 x){union{f32 f;u32 u;}v;v.u=x;return v.f;}
static int same(f32 a,f32 b){u32 x=as_bits(a),y=as_bits(b);return x==y||((x&0x7F800000u)==0x7F800000u&&(x&0x7FFFFFu)&&(y&0x7F800000u)==0x7F800000u&&(y&0x7FFFFFu));}
s32 func_1501F72C(s32 index,f32 time,f32 (*points)[3],s32 group,s32 *frame){int i;helper_calls++;
 if(index!=index0||group!=group0||!same(time,expected_time)||!points||!frame)errors++;
 for(i=0;i<6;i++)points[i/3][i%3]=POINTS[i];*frame=frame0;
 if(mutation0&1){D_800C35C8[group0]=altrow;D_800C3868[group0][index0]=(u8*)altkeys;}
 if(mutation0&2)D_800969DC=2.f;return 0;}
s32 func_1501FFE8(f32 (*matrix)[3],u8 *data,s32 frame,s32 count){int i;helper_calls++;
 if(data!=expected_keys||frame!=frame0||count!=count0||!matrix)errors++;
 for(i=0;i<12;i++)matrix[i/3][i%3]=MATRIX[i];return 0;}
f32 func_150484A0(f32 x,f32 z){helper_calls++;if(!same(x,expected_x)||!same(z,expected_z))errors++;if(mutation0&8)D_800969DC=.5f;return answer;}
_Static_assert(sizeof(void*)==4&&sizeof(s32)==4&&sizeof(f32)==4,"SDK ABI");
_Static_assert(sizeof(SequenceRuntime49D30)==0x40&&__builtin_offsetof(SequenceRuntime49D30,items)==4&&__builtin_offsetof(SequenceRuntime49D30,scratch)==0x38,"sequence layout");
_Static_assert(sizeof(SequenceFrameKey49D30)==8&&__builtin_offsetof(SequenceFrameKey49D30,flag)==6,"key layout");
'''
 code=pre+body+'\n'
 changes={
 'key-count-gate':('>= 2','> 2'),
 'upper-clamp':('percentage > 100.0f','percentage > 101.0f'),
 'lower-clamp':('percentage < 0.0f','percentage < -1.0f'),
 'time-scale':('* D_800969D8','* D_800969DC'),
 'key-flag':('.flag == 0','.flag != 0'),
 'point-x':('points[0][0] - points[1][0]','points[1][0] - points[0][0]'),
 'matrix-z':('matrix[2][2] - matrix[1][2]','matrix[1][2] - matrix[2][2]'),
 'output-scale':('*output = func_150484A0(x, z) * D_800969DC;','*output = func_150484A0(x, z);')}
 for i,(label,(a,b))in enumerate(changes.items()):assert body.count(a)==1,(label,a);code+=body.replace('func_1501FE68','bad%d'%i).replace(a,b)+'\n'
 code+='''static int test(void (*fn)(s32,f32,f32*,s32),int group,int index,int count,u32 pct,int flag,int mutation,int alias){
 f32 percentage=as_float(pct),clamped=percentage;volatile f32 stage;f32 *out;f32 expected,expected_scale;int i;
 group0=group;index0=index;frame0=index&1;mutation0=mutation;active0=count>=2;flag0=(mutation&1)?(flag^1):flag;count0=(mutation&1)?3:count;helper_calls=errors=0;answer=.5f;
 for(i=0;i<2;i++){D_800C35C8[i]=rows[i];D_800C3A50[i]=runtimes[i];rows[i][0]=rows[i][1]=2;altrow[i]=3;keys[i].flag=(u16)flag;altkeys[i].flag=(u16)(flag^1);}
 rows[group][index]=(u16)count;runtimes[group][index].duration=as_float(duration_bits);D_800C3868[group][index]=(u8*)keys;D_800969D8=.01f;D_800969DC=57.29577637f;result=17.f;
 out=alias==0?&result:alias==1?&D_800969DC:alias==2?&D_800969D8:&runtimes[group][index].duration;
 if(!active0)out=(f32*)0;
 if(clamped>100.f)clamped=100.f;if(clamped<0.f)clamped=0.f;stage=as_float(duration_bits)*clamped;expected_time=stage*.01f;
 expected_keys=(mutation&1)?(u8*)altkeys:(u8*)keys;
 expected_x=flag0?MATRIX[6]-MATRIX[3]:POINTS[0]-POINTS[3];expected_z=flag0?MATRIX[8]-MATRIX[5]:POINTS[2]-POINTS[5];
 expected_scale=(mutation&8)?.5f:(mutation&2)?2.f:57.29577637f;stage=answer*expected_scale;expected=stage;
 fn(index,percentage,out,group);
 if(errors)return 73;if(!active0){if(helper_calls||result!=17.f)return 73;return 0;}
 if(helper_calls!=(flag0?3:2)||!same(*out,expected))return 73;return 0;}
int run(void){static const u32 pcts[]={0,0x80000000u,0xBF000000u,0x3F800000u,0x42C80000u,0x42C90000u,0x7F800000u,0xFF800000u,0x7FC12345u};
 int group,index,count,flag,mut,alias,i,v;void (*selected)(s32,f32,f32*,s32)=func_1501FE68;
 for(group=0;group<2;group++)for(index=0;index<2;index++)for(count=0;count<4;count++)for(flag=0;flag<2;flag++)for(i=0;i<9;i++){v=test(selected,group,index,count,pcts[i],flag,0,0);if(v)return v;}
 for(flag=0;flag<2;flag++)for(mut=0;mut<16;mut++)for(alias=0;alias<4;alias++){v=test(selected,0,1,2,0x42C80000u,flag,mut,alias);if(v)return v;}
 {static const u32 durations[]={0,0x80000000u,1,0x00800000u,0x3F800000u,0xBF800000u,0x7F7FFFFFu,0x7F800000u,0xFF800000u,0x7FC12345u};for(i=0;i<10;i++)for(flag=0;flag<2;flag++){duration_bits=durations[i];v=test(selected,1,1,65535,0x42480000u,flag,0,0);if(v)return v;}duration_bits=0x41200000u;}
'''
 for i,label in enumerate(changes):code+=' {int witness=0;for(flag=0;flag<2;flag++)for(count=1;count<4;count++)for(i=0;i<9;i++){v=test(bad%d,0,1,count,pcts[i],flag,0,0);if(v==73)witness=1;else if(v)return v;}if(!witness)return %d;}\n'%(i,90+i)
 code+='return 0;}\n'+START;path=p.out/'native.c';path.write_text(code);profiles={}
 for opt in('-O0','-O2','-O3'):
  binary=p.out/('native-'+opt[1:]);cmd=native_command(opt,True)+['-fstrict-aliasing',str(path),'-o',str(binary)];result=subprocess.run(cmd,cwd=p.root,capture_output=True,text=True);assert result.returncode==0 and not result.stdout and not result.stderr,(opt,result.stdout,result.stderr[-3500:]);run=subprocess.run([str(binary)],capture_output=True);assert run.returncode==0 and not run.stdout and not run.stderr,(opt,run.returncode,run.stdout,run.stderr);profiles[opt]=dict(cases=436,UBSan=True,strict_aliasing=True,effective_completed_controls=8,SDK_layout_asserted=True)
 report=dict(profiles=profiles,finite_and_qNaN_float_cases=True,physical_stack_aliases_not_native=True,unfinished_helpers_modeled_as_typed_providers=True)
 (p.out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
