"""Native 32-bit motion/fade, canonical record bytes and six source controls."""
from pathlib import Path
import json,os,subprocess
from tools.tests import game_piece_update_1517a1ec_oracle as b
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def digest(observation):
    record,ticks=observation;h=2166136261
    for value in (*record,ticks):h=((h^value)*16777619)&0xffffffff
    return h
def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/b.source.BUILD;body=b.source.SELECTED
    bad={'wrong_y_direction':body.replace('record->y -= record->speedY','record->y += record->speedY'),'unsigned_spin':body.replace('record->angleX += record->spinX','record->angleX += (u8)record->spinX'),'wrong_gravity_mode':body.replace('motionMode == 5','motionMode == 4'),'wrong_damping_direction':body.replace('-(record->speedX < 0 ? -1 : 1)','(record->speedX < 0 ? -1 : 1)'),'wrong_fade_rate':body.replace('(u32)ticks << 2','(u32)ticks << 1'),'zero_nibble_retirement':body.replace('(packed = record->retireNibbles) != 0','(packed = record->retireNibbles) >= 0')}
    assert all(v!=body for v in bad.values()) and len(set(bad.values()))==6
    s=(out/'selected.c').read_text();a=s.index('typedef struct {');z=s.index('} SettleFade1517A84C;',a)+len('} SettleFade1517A84C;')
    code='#include <ultra64.h>\ns32 func_150ADA20(void);\nvoid func_1516972C(void*);\nextern s32 D_800BE9E4;\n'+s[a:z]+'\n'+'\n'.join(v.replace(b.source.NAME,'candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
    code+='\ntypedef struct {u32 ticks,pattern,seed,mutation,n;u8 initial[184],expected[184];u32 targets[3],digests[3];} Case;\nstatic const Case cases[]={\n'
    rows=[];arr=lambda xs:'{'+','.join(hex(b.u32(v))+'u' for v in xs)+'}'
    for c in b.cases():
        if c.layout or c.phase or c.mutation&6 or c.damping==0:continue
        initial=b.fixture(c);expected,calls,obs,zero=b.reference(initial,c);assert not zero
        values=(c.ticks,c.pattern,c.seed,c.mutation,len(calls));targets=[t for t,_ in calls]+[0]*(3-len(calls));hashes=[digest(o) for _,o in obs]+[0]*(3-len(obs))
        rows.append('{'+','.join(hex(b.u32(v))+'u' for v in values)+','+','.join(arr(v) for v in (b.packet(initial,b.RECORD),b.packet(expected,b.RECORD),targets,hashes))+'}')
    code+=',\n'.join(rows)+'\n};\n'+r'''
typedef char Layout[sizeof(SettleFade1517A84C)==184&&__builtin_offsetof(SettleFade1517A84C,motionMode)==0xac&&__builtin_offsetof(SettleFade1517A84C,dampingRange)==0xae&&__builtin_offsetof(SettleFade1517A84C,retireNibbles)==0xb2?1:-1];
static SettleFade1517A84C storage;static const Case*current;static u32 calls,draws,error;s32 D_800BE9E4;
static u32 byteIndex(u32 k){if(k>=0xa8&&k<0xac)return k^3u;if((k>=0x90&&k<0x9c)||(k>=0xa0&&k<0xa8)||(k>=0xac&&k<0xb2))return k^1u;return k;}
static u32 targetByte(u32 k){return ((u8*)&storage)[byteIndex(k)];}
static u32 digest(void){u32 i,h=2166136261u;for(i=0;i<184;i++)h=(h^targetByte(i))*16777619u;return (h^(u32)D_800BE9E4)*16777619u;}
static u32 check(u32 target){u32 n=calls++;if(n>=current->n||n>=3){error=1;return n;}if(current->targets[n]!=target||current->digests[n]!=digest())error=1;return n;}
static void effect(u32 n,u32 target){u32 i;if(target==0x1516972cu){for(i=0;i<184;i++)((u8*)&storage)[i]=0xdd;return;}if(current->mutation&1){storage.speedX=(s16)(n&1?-32768:32767);storage.speedZ=(s16)(n&1?1234:-1234);storage.dampingRange=(u16)(n*3+2);storage.timer=(u16)(storage.timer+1);storage.opacity^=0x55;storage.retireNibbles=(u8)(n&1?0x22:0x12);D_800BE9E4=(s32)((u32)D_800BE9E4^0x10203u);}}
s32 func_150ADA20(void){u32 n=check(0x150ada20u),value;if(current->pattern==0)value=0;else if(current->pattern==1)value=0xffffffffu;else value=(current->seed+draws)*1664525u+1013904223u;draws++;effect(n,0x150ada20u);return (s32)value;}
void func_1516972C(void*record){u32 n=check(0x1516972cu);if(record!=&storage)error=1;effect(n,0x1516972cu);}
static void(*candidates[])(SettleFade1517A84C*)={candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5,candidate_6};
static int run(void){u32 i,j,k,killed=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;for(j=0;j<7;j++){for(k=0;k<184;k++)((u8*)&storage)[byteIndex(k)]=current->initial[k];D_800BE9E4=(s32)current->ticks;calls=draws=error=0;candidates[j](&storage);if(calls!=current->n)error=1;for(k=0;k<184;k++)if(targetByte(k)!=current->expected[k])error=1;if(error){if(!j)return 10;killed|=1u<<(j-1);}}}return killed==63u?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    p=out/'native.c';p.write_text(code);profiles=[]
    for opt in ('-O0','-O2','-O3'):
        exe=out/('native'+opt);q=subprocess.run(native_command(opt)+['-o',str(exe),str(p)],cwd=root,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
        q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles.append(opt)
    report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,record_bytes_checked=184,helper_observations=True,zero_divisors_and_global_aliases_excluded=True)
    (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
