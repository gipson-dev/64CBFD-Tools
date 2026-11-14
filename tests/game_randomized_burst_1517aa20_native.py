"""Native 32-bit semantic C and five effective source controls, with UBSan."""
from pathlib import Path
import json,os,subprocess
from tools.experiments import game_randomized_burst_1517aa20_match as source
from tools.tests import game_randomized_burst_1517aa20_oracle as b
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD;body=source.SELECTED
    bad={'wrong_offset_mask':body.replace('dx = func_150ADA20() & 63','dx = func_150ADA20() & 31'),'wrong_size_half':body.replace('size *= 0.5f','size *= 1.0f'),'wrong_variant_bit':body.replace('kind & 1','kind & 2'),'wrong_y':body.replace('y = yArgument','y = yArgument + 1'),'early_loop_exit':body.replace('i < count','i < count - 1')}
    assert all(v!=body for v in bad.values()) and len(set(bad.values()))==5
    code='#include <ultra64.h>\ns32 func_150ADA20(void);\ns32 func_1517A644(f32,u8,s16,s16,s32);\n'+'\n'.join(v.replace(source.NAME,'candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
    code+='\ntypedef union {u32 u; f32 f;} Bits;\ntypedef struct {u32 size,x,y,z,count,pattern,seed,n;u32 expected[3][5];} Case;\nstatic const Case cases[]={\n'
    rows=[]
    for c in b.cases():
        if c.phase:continue
        _,calls=b.reference(b.fixture(c),c);emits=[a for t,a in calls if t==b.EMIT]
        args=(c.size,c.x,c.y,c.z,c.count,c.pattern,c.seed,len(emits));values=emits+[(0,)*5]*(3-len(emits))
        arr=lambda xs:'{'+','.join(hex(b.u32(x))+'u' for x in xs)+'}'
        rows.append('{'+','.join(hex(b.u32(x))+'u' for x in args)+','+'{'+','.join(arr(v) for v in values)+'}}')
    code+=',\n'.join(rows)+'\n};\n'+r'''
static const Case *current;static u32 draws,emits,error;
static f32 real(u32 u){Bits b;b.u=u;return b.f;}static u32 word(f32 f){Bits b;b.f=f;return b.u;}
s32 func_150ADA20(void){u32 value;if(current->pattern==0)value=0;else if(current->pattern==1)value=0xffffffffu;else if(current->pattern==2)value=(current->seed+draws)*1664525u+1013904223u;else value=current->seed+draws*31u;draws++;return (s32)value;}
s32 func_1517A644(f32 size,u8 kind,s16 x,s16 y,s32 z){u32 i,actual[5];actual[0]=word(size);actual[1]=kind;actual[2]=(u32)(s32)x;actual[3]=(u32)(s32)y;actual[4]=(u32)z;if(emits>=current->n||emits>=3){error=1;return 0;}for(i=0;i<5;i++)if(actual[i]!=current->expected[emits][i])error=1;emits++;return (s32)0x87654321u;}
static void (*candidates[])(f32,s32,s32,s32,s32)={candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5};
static int run(void){u32 i,j,killed=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;for(j=0;j<6;j++){draws=emits=error=0;candidates[j](real(current->size),(s32)current->x,(s32)current->y,(s32)current->z,(s32)current->count);if(draws!=4u*current->n||emits!=current->n)error=1;if(error){if(!j)return 10;killed|=1u<<(j-1);}}}return killed==31?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    p=out/'native.c';p.write_text(code);profiles=[]
    for opt in ('-O0','-O2','-O3'):
        exe=out/('native'+opt);q=subprocess.run(native_command(opt)+['-o',str(exe),str(p)],cwd=root,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
        q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles.append(opt)
    report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,random_and_emitter_modeled=True,finite_conversion_domain=True)
    (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
