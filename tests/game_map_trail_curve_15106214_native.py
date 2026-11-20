"""Native SDK32 curve checks against independently computed guest expectations."""
import json,subprocess
from tools.experiments import game_map_trail_curve_15106214_recovery as source
from tools.tests import game_map_trail_curve_15106214_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def record(m):
    return [g.read(m,g.RECORD+0x48),g.read(m,g.RECORD+0x64)]+[g.read(m,g.RECORD+0x14+4*i)for i in range(12)]

def harness(body=source.BODY):
    before,_=source.source()
    types=before.split('#include "game/map_trail.h"',1)[1].split('extern MapTrailPoint133190 D_800A5480;',1)[0]
    literal=lambda values:','.join('0x%Xu'%(v&0xFFFFFFFF)for v in values)
    rows=[]
    for c in g.cases():
        if c.phase:continue
        initial=g.fixture(c);expected,calls,snapshots=g.reference(initial,c)
        parameters=[args[0]for target,args in calls if target==g.BASIS[0]]
        snapshots=[int.from_bytes(data[i:i+4],'big')for data in snapshots for i in range(0,36,4)]
        vectors=([c.count,c.seed,c.mode,len(parameters)],record(initial),record(expected),
                 [g.read(initial,g.OUTPUT+4*i)for i in range(56)],
                 [g.read(expected,g.OUTPUT+4*i)for i in range(56)],
                 parameters+[0]*(4-len(parameters)),snapshots+[0]*(36-len(snapshots)))
        rows.append('{'+','.join('{'+literal(v)+'}'for v in vectors)+'}')
    text='#include <ultra64.h>\n#include "structs.h"\n#include "game/map_trail.h"\n'+types+source.VIEW+source.PREAMBLE+r'''
struct Case {u32 parameters[4],initial[14],expected[14],before[56],after[56],arguments[4],snapshots[36];};
static const struct Case cases[]={ROWS};
static const struct Case *current;
static struct {MapTrailRecord133190 record;MapTrailSegment133190 segments[4];u8 guard[16];} allocation;
static MapTrailRecord133190 expected;
static u32 basisCalls,frameCalls,getterCalls,error;
static f32 real(u32 w){union{u32 w;f32 f;}v;v.w=w;return v.f;}
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}
static void putWord(void*p,u32 w){u8*q=p;q[0]=w;q[1]=w>>8;q[2]=w>>16;q[3]=w>>24;}
static u32 getWord(const void*p){const u8*q=p;return(u32)q[0]|(u32)q[1]<<8|(u32)q[2]<<16|(u32)q[3]<<24;}
static void fill(void*p,u32 n){u8*q=p;u32 i;for(i=0;i<n;i++)q[i]=0xA5;}
static int equal(const void*a,const void*b,u32 n){const u8*x=a,*y=b;u32 i;for(i=0;i<n;i++)if(x[i]!=y[i])return 0;return 1;}
static void apply(MapTrailRecord133190*r,const u32*v){u32 i;r->packet.pieces=(s32)v[0];r->reciprocal=real(v[1]);
 for(i=0;i<4;i++){r->packet.points[i].x=real(v[2+i*3]);r->packet.points[i].y=real(v[3+i*3]);r->packet.points[i].z=real(v[4+i*3]);}}
MapTrailSegment133190 *func_151061E0(void*p){getterCalls++;if(p!=&allocation.record)error=1;
 if(current->parameters[2]&1)allocation.record.reciprocal=0.375f;return allocation.segments;}
static f32 weight(u32 index,f32 parameter){u32 iteration=basisCalls/8,ordinal=iteration+1;
 if(basisCalls%8!=index||iteration>=current->parameters[3]||word(parameter)!=current->arguments[iteration])error=2;
 basisCalls++;
 if(index==7&&(current->parameters[2]&1)){allocation.record.packet.points[0].x=17.f+(f32)ordinal;allocation.record.packet.points[3].y=-11.f-(f32)ordinal;}
 return(f32)((index+1)*(current->parameters[1]+1))*0.0625f+parameter*0.125f;}
f32 func_151064B4(f32 t){return weight(0,t);}f32 func_151064DC(f32 t){return weight(1,t);}
f32 func_15106510(f32 t){return weight(2,t);}f32 func_15106540(f32 t){return weight(3,t);}
f32 func_15106558(f32 t){return weight(4,t);}f32 func_15106584(f32 t){return weight(5,t);}
f32 func_151065BC(f32 t){return weight(6,t);}f32 func_151065EC(f32 t){return weight(7,t);}
s32 func_15146078(MapTrailPoint133190*t,MapTrailPoint133190*n,MapTrailPoint133190*b){
 u32 i,iteration=frameCalls,ordinal=iteration+1;u8*base=(u8*)&allocation+0x88+iteration*52;
 if(iteration>=current->parameters[3]||(void*)t!=base+16||(void*)n!=base+28||(void*)b!=base+40)error=3;
 for(i=0;i<9;i++)if(getWord(base+16+4*i)!=current->snapshots[iteration*9+i])error=4;
 putWord(&t->y,getWord(&t->y)^0x80000000);
 n->x=(f32)(ordinal+1)*0.25f;n->y=(f32)(ordinal+2)*0.25f;n->z=(f32)(ordinal+3)*0.25f;
 b->x=-(f32)(ordinal+1)*0.5f;b->y=-(f32)(ordinal+2)*0.5f;b->z=-(f32)(ordinal+3)*0.5f;
 if(current->parameters[2]&2){s32 limit=(s32)current->parameters[0];if(limit<0)limit=0;if(limit>2)limit=2;
  allocation.record.packet.pieces=limit;allocation.record.reciprocal=7.f;allocation.record.packet.points[1].x=23.f+(f32)ordinal;}
 frameCalls++;return(current->parameters[1]+ordinal)&1?0:(s32)0x80000000u;
}
BODY
static int run(void){u32 i,j;
 if(sizeof(void*)!=4||sizeof(MapTrailRecord133190)!=136||sizeof(MapTrailSegment133190)!=52||
    __builtin_offsetof(__typeof__(allocation),segments)!=136)return 10;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  current=&cases[i];fill(&allocation,sizeof(allocation));fill(&expected,sizeof(expected));
  apply(&allocation.record,current->initial);apply(&expected,current->expected);
  for(j=0;j<56;j++)putWord((u8*)&allocation+136+4*j,current->before[j]);
  basisCalls=frameCalls=getterCalls=error=0;func_15106214(&allocation.record);
  if(error||getterCalls!=1||frameCalls!=current->parameters[3]||basisCalls!=frameCalls*8)return 11;
  if(!equal(&allocation.record,&expected,sizeof(expected)))return 12;
  for(j=0;j<56;j++)if(getWord((u8*)&allocation+136+4*j)!=current->after[j])return 13;
 }
 return 0;}
'''
    return text.replace('ROWS',',\n'.join(rows)).replace('BODY',body)+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),len(rows)

def run():
    out=source.OUT/'native';out.mkdir(exist_ok=True)
    text,count=harness();path=out/'target.c';path.write_text(text)
    reports=[]
    for opt in('-O0','-O2','-O3'):
        executable=out/opt[1:]
        compiled=subprocess.run(native_command(opt)+[str(path),'-o',str(executable)],cwd=source.ROOT,capture_output=True,text=True)
        assert compiled.returncode==0,compiled.stdout+compiled.stderr
        result=subprocess.run([str(executable)],capture_output=True,timeout=15)
        assert result.returncode==0,(opt,result.returncode)
        reports.append(dict(optimization=opt,cases=count,strict_aliasing=True,UBSan=True))
    controls={'wrong-control-point':source.BODY.replace('points[2].x * b2','points[1].x * b2'),
              'missing-fallback':source.BODY.replace('if (func_15146078(tangent, normal, binormal) == 0)','if (func_15146078(tangent, normal, binormal) == 7)'),
              'uncached-step':source.BODY.replace('parameter += step;','parameter += record->reciprocal;')}
    rejected=[]
    for label,body in controls.items():
        assert body!=source.BODY
        text,_=harness(body);path=out/(label+'.c');path.write_text(text);executable=out/label
        compiled=subprocess.run(native_command('-O2')+[str(path),'-o',str(executable)],cwd=source.ROOT,capture_output=True,text=True)
        assert compiled.returncode==0,compiled.stdout+compiled.stderr
        result=subprocess.run([str(executable)],capture_output=True,timeout=15)
        assert result.returncode in(11,12,13),(label,result.returncode)
        rejected.append(label)
    (out/'receipt.json').write_text(json.dumps(dict(valid=reports,rejected=rejected),indent=2)+'\n')
    return reports
