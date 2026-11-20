"""SDK32 checks for sampled points, live providers and retained float outputs."""
import json,subprocess
from tools.experiments import game_map_trail_samples_15106610_recovery as source
from tools.tests import game_map_trail_samples_15106610_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def record(m):return[g.read(m,g.RECORD+0x48),g.read(m,g.RECORD+0x4C)]+[g.read(m,g.RECORD+0x14+4*i)for i in range(12)]
def harness(body=source.BODY):
    before,_=source.source()
    types=before.split('#include "game/map_trail.h"',1)[1].split('extern MapTrailPoint133190 D_800A5480;',1)[0]
    start=before.index('typedef struct {\n    f32 parameter;');end=before.index('} MapTrailSegment133190;',start)+len('} MapTrailSegment133190;')
    view=before[start:end]
    literal=lambda values:','.join('0x%Xu'%(v&0xFFFFFFFF)for v in values)
    rows=[]
    for c in g.cases():
        if c.phase:continue
        initial=g.fixture(c);expected,calls,snapshots=g.reference(initial,c)
        polar=[args for target,args in calls if target==g.POLAR]
        angles=[a[0]for a in polar];radii=[a[1]for a in polar]
        arrays=([c.count,c.seed,c.mode,c.angle,len(polar)],record(initial),record(expected),
            [g.read(initial,g.SEGMENTS+4*i)for i in range(52)],[g.read(expected,g.SEGMENTS+4*i)for i in range(52)],
            [g.read(initial,g.POINTS+4*i)for i in range(22)],[g.read(expected,g.POINTS+4*i)for i in range(22)],
            angles+[0]*(4-len(angles)),radii+[0]*(4-len(radii)),
            [v for pair in snapshots for v in pair]+[0]*(8-2*len(snapshots)))
        rows.append('{'+','.join('{'+literal(v)+'}'for v in arrays)+'}')
    text='#include <ultra64.h>\n#include "structs.h"\n#include "game/map_trail.h"\n'+types+view+'\n'+source.PREAMBLE+r'''
struct Case {u32 parameters[5],initial[14],expected[14],segmentsBefore[52],segmentsAfter[52],pointsBefore[22],pointsAfter[22],angles[4],radii[4],prior[8];};
static const struct Case cases[]={ROWS};static const struct Case*current;
static MapTrailRecord133190 record,expected;
static MapTrailSegment133190 segments[4];
static struct {MapTrailPoint133190 points[6];u8 guard[16];} output;
static f32 *retainedFirst,*retainedSecond;
static u32 getters,integers,floats,polars,error;
static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}
static void putWord(void*p,u32 w){u8*q=p;q[0]=w;q[1]=w>>8;q[2]=w>>16;q[3]=w>>24;}
static u32 getWord(const void*p){const u8*q=p;return(u32)q[0]|(u32)q[1]<<8|(u32)q[2]<<16|(u32)q[3]<<24;}
static void fill(void*p,u32 n){u8*q=p;u32 i;for(i=0;i<n;i++)q[i]=0xA5;}
static int equal(const void*a,const void*b,u32 n){const u8*x=a,*y=b;u32 i;for(i=0;i<n;i++)if(x[i]!=y[i])return 0;return 1;}
static void apply(MapTrailRecord133190*r,const u32*v){u32 i;r->packet.pieces=(s32)v[0];r->packet.width=real(v[1]);
 for(i=0;i<4;i++){r->packet.points[i].x=real(v[2+i*3]);r->packet.points[i].y=real(v[3+i*3]);r->packet.points[i].z=real(v[4+i*3]);}}
__attribute__((noipa)) MapTrailSegment133190*func_151061E0(void*r){if(r!=&record||getters++!=0)error=1;
 if(current->parameters[2]&1)record.packet.width=15.5f;return segments;}
__attribute__((noipa)) u8*func_151061EC(u8*r){if(r!=(u8*)&record||getters++!=1)error=2;
 if(current->parameters[2]&2)record.packet.points[0].x=-37.5f;return(u8*)output.points;}
__attribute__((noipa)) s32 func_150ADA20(void){
 static const u32 v[]={0,1,0xFFFFFFFF,0x80000000,0x876543FF,0xFF000080,0x7FFFFFFF,0x1234007F};
 u32 ordinal=++integers,base=(s32)current->parameters[3]<0?v[current->parameters[1]]:0xA5A50000u|current->parameters[3];
 if(getters!=2||ordinal!=floats+1||floats!=polars)error=3;
 if(current->parameters[2]&1){record.packet.width=3.25f;segments[ordinal-1].normal.x=2.f;
  if(retainedFirst){*retainedFirst=7.5f;*retainedSecond=-3.75f;}}
 return(s32)(base+(ordinal-1)*0x1000201u);
}
__attribute__((noipa)) f32 func_150ADA68(void){
 static const f32 v[]={0.f,-0.f,0.25f,0.75f,-0.5f,1.f,-1.f,2.f};u32 ordinal=++floats;
 if(ordinal!=integers||ordinal!=polars+1)error=4;
 if(current->parameters[2]&2){record.packet.width=-2.5f;segments[ordinal-1].binormal.y=11.f;
  if(retainedFirst)*retainedFirst=-9.25f;}
 return v[(current->parameters[1]+ordinal-1)%8];
}
__attribute__((noipa)) void func_15143874(s16 angle,f32 radius,f32*first,f32*second){u32 index=polars++;
 if(index>=current->parameters[4]||integers!=index+1||floats!=index+1||!first||!second||first==second)error=5;
 if((u32)angle!=current->angles[index]||word(radius)!=current->radii[index])error=6;
 if(index){if(first!=retainedFirst||second!=retainedSecond||word(*first)!=current->prior[index*2]||word(*second)!=current->prior[index*2+1])error=7;}
 if(current->parameters[2]==3){record.packet.pieces=(s32)current->parameters[0]>2?2:(s32)current->parameters[0];segments[index].position.z=13.f+(f32)(index+1);}
 *first=(f32)(angle-128)*0.125f+radius*0.25f;
 *second=(f32)(64-angle)*0.25f+radius*(-0.125f);
 retainedFirst=first;retainedSecond=second;
}
BODY
static int run(void){u32 i,j;
 if(sizeof(void*)!=4||sizeof(MapTrailRecord133190)!=136||sizeof(MapTrailSegment133190)!=52||sizeof(output)!=88)return 10;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  current=&cases[i];fill(&record,sizeof(record));fill(&expected,sizeof(expected));apply(&record,current->initial);apply(&expected,current->expected);
  for(j=0;j<52;j++)putWord((u8*)segments+j*4,current->segmentsBefore[j]);
  for(j=0;j<22;j++)putWord((u8*)&output+j*4,current->pointsBefore[j]);
  getters=integers=floats=polars=error=0;retainedFirst=retainedSecond=0;func_15106610(&record);
  if(error||getters!=2||integers!=current->parameters[4]||floats!=integers||polars!=integers)return 11;
  if(!equal(&record,&expected,sizeof(record)))return 12;
  for(j=0;j<52;j++)if(getWord((u8*)segments+j*4)!=current->segmentsAfter[j])return 13;
  for(j=0;j<22;j++)if(getWord((u8*)&output+j*4)!=current->pointsAfter[j])return 14;
 }
 return 0;
}
'''
    return text.replace('ROWS',',\n'.join(rows)).replace('BODY',body)+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),len(rows)

def run():
    out=source.OUT/'native';out.mkdir(exist_ok=True);text,count=harness();path=out/'target.c';path.write_text(text)
    reports=[]
    for opt in('-O0','-O2','-O3'):
        executable=out/opt[1:];compiled=subprocess.run(native_command(opt)+[str(path),'-o',str(executable)],cwd=source.ROOT,capture_output=True,text=True)
        assert compiled.returncode==0,compiled.stdout+compiled.stderr
        result=subprocess.run([str(executable)],capture_output=True,timeout=15);assert result.returncode==0,(opt,result.returncode)
        reports.append(dict(optimization=opt,cases=count,strict_aliasing=True,UBSan=True,retained_float_pointers=True))
    controls={'angle-width':source.BODY.replace('random & 255','random & 127'),
              'wrong-normal':source.BODY.replace('segment->normal.x * first','segment->tangent.x * first'),
              'wrong-endpoint':source.BODY.replace('record->packet.points[3]','record->packet.points[2]')}
    rejected=[]
    for label,body in controls.items():
        assert body!=source.BODY;text,_=harness(body);path=out/(label+'.c');path.write_text(text);executable=out/label
        compiled=subprocess.run(native_command('-O2')+[str(path),'-o',str(executable)],cwd=source.ROOT,capture_output=True,text=True)
        assert compiled.returncode==0,compiled.stdout+compiled.stderr
        result=subprocess.run([str(executable)],capture_output=True,timeout=15);assert result.returncode in(11,12,13,14),(label,result.returncode)
        rejected.append(label)
    (out/'receipt.json').write_text(json.dumps(dict(valid=reports,rejected=rejected),indent=2)+'\n');return reports
