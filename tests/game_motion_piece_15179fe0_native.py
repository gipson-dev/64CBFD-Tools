"""Native 32-bit constructor ABI, all record bytes and six effective controls."""
from pathlib import Path
import json,os,subprocess
from tools.tests import game_motion_piece_15179fe0_oracle as b
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def digest(observation):
    record,factor=observation;h=2166136261
    for value in (*record,factor):h=((h^value)*16777619)&0xffffffff
    return h
def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/b.source.BUILD;factor=b.factor(root);body=b.source.SELECTED
    bad={'wrong_allocation_size':body.replace('0xB8','0xB4'),'wrong_initial_step':body.replace('* 4','* 2'),'wrong_mode':body.replace('mode == 5','mode == 4'),'wrong_velocity_center':body.replace('(movementRange >> 1)','(movementRange >> 2)'),'wrong_spin_field':body.replace('record->spinY =','record->spinX ='),'wrong_scale_mask':body.replace('& 127','& 63')}
    assert all(v!=body for v in bad.values()) and len(set(bad.values()))==6
    s=(out/'selected.c').read_text();a=s.index('typedef struct {');z=s.index('} SettleFade1517A84C;',a)+len('} SettleFade1517A84C;')
    code='#include <ultra64.h>\ns32 func_150ADA20(void);\nvoid*func_15167A68(s32,s32,s32,s32,u8,u8);\nextern f32 D_800A7220;\n'+s[a:z]+'\n'+'\n'.join(v.replace(b.source.NAME,'candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
    code+='\ntypedef union{u32 u;f32 f;}Bits;\ntypedef struct{u32 args[11];u32 outcome,pattern,seed,mutation,n;u8 expected[184];u32 targets[7],digests[7];}Case;\nstatic const Case cases[]={\n'
    rows=[];arr=lambda xs:'{'+','.join(hex(b.u32(v))+'u' for v in xs)+'}'
    for c in b.cases():
        if c.phase or c.mutation&2 or not(c.movement&255) or not(c.spin&255):continue
        expected,calls,obs,zero=b.reference(b.fixture(c,factor),c);assert zero is None
        values=(c.outcome,c.pattern,c.seed,c.mutation,len(calls));targets=[t for t,_ in calls]+[0]*(7-len(calls));hashes=[digest(o) for _,o in obs]+[0]*(7-len(obs))
        rows.append('{'+arr(b.args(c))+','+','.join(hex(b.u32(v))+'u' for v in values)+','+','.join(arr(v) for v in (b.packet(expected),targets,hashes))+'}')
    code+=',\n'.join(rows)+'\n};\n'+r'''
typedef char Layout[sizeof(SettleFade1517A84C)==184&&__builtin_offsetof(SettleFade1517A84C,scale)==0xa8&&__builtin_offsetof(SettleFade1517A84C,motionMode)==0xac&&__builtin_offsetof(SettleFade1517A84C,dampingRange)==0xae?1:-1];
static SettleFade1517A84C storage;static const Case*current;static u32 calls,draws,error;f32 D_800A7220;
static f32 real(u32 u){Bits b;b.u=u;return b.f;}static u32 word(f32 f){Bits b;b.f=f;return b.u;}
static u32 byteIndex(u32 k){if(k>=0xa8&&k<0xac)return k^3u;if((k>=0x90&&k<0x9c)||(k>=0xa0&&k<0xa8)||(k>=0xac&&k<0xb2))return k^1u;return k;}
static u32 targetByte(u32 k){return ((u8*)&storage)[byteIndex(k)];}
static u32 digest(void){u32 i,h=2166136261u;for(i=0;i<184;i++)h=(h^targetByte(i))*16777619u;return (h^word(D_800A7220))*16777619u;}
static u32 check(u32 target){u32 n=calls++;if(n>=current->n||n>=7){error=1;return n;}if(current->targets[n]!=target||current->digests[n]!=digest())error=1;return n;}
static void effect(u32 target,u32 n){if(current->mutation&1){D_800A7220=(n+1)*.125f;if(current->outcome){storage.retained00[0x50]^=(u8)(n+1);if(target==0x150ada20u){storage.x=(s16)(storage.x+1);storage.y=(s16)(storage.y-1);storage.z=(s16)(storage.z+2);storage.speedX=(s16)(32767-(s32)n);storage.speedY=(s16)(n&1?-3:5);storage.speedZ=(s16)(-1234+(s32)n);storage.spinX=(s8)(0x80u|n);}}}}
void*func_15167A68(s32 category,s32 group,s32 bytes,s32 mode,u8 priority,u8 flag){u32 n=check(0x15167a68u);if((u32)category!=current->args[10]||group||bytes!=184||mode!=1||priority!=255||flag!=1)error=1;if(current->outcome){((u8*)&storage)[1]=0;((u8*)&storage)[12]=255;}effect(0x15167a68u,n);return current->outcome?&storage:0;}
s32 func_150ADA20(void){u32 n=check(0x150ada20u),value;if(current->pattern==0)value=0;else if(current->pattern==1)value=0xffffffffu;else value=(current->seed+draws)*1664525u+1013904223u;draws++;effect(0x150ada20u,n);return (s32)value;}
static void(*candidates[])(u8,s16,s16,s16,s8,u16,u16,u8,u8,u8,s32)={candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5,candidate_6};
static int run(void){u32 i,j,k,killed=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;for(j=0;j<7;j++){for(k=0;k<184;k++)((u8*)&storage)[byteIndex(k)]=(u8)(k*29+current->seed*11+0x5a);D_800A7220=real(INITIAL);calls=draws=error=0;candidates[j]((u8)current->args[0],(s16)current->args[1],(s16)current->args[2],(s16)current->args[3],(s8)current->args[4],(u16)current->args[5],(u16)current->args[6],(u8)current->args[7],(u8)current->args[8],(u8)current->args[9],(s32)current->args[10]);if(calls!=current->n)error=1;for(k=0;k<184;k++)if(targetByte(k)!=current->expected[k])error=1;if(error){if(!j)return 10;killed|=1u<<(j-1);}}}return killed==63u?0:11;}
'''.replace('INITIAL',hex(factor)+'u')+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    p=out/'native.c';p.write_text(code);profiles=[]
    for opt in ('-O0','-O2','-O3'):
        exe=out/('native'+opt);q=subprocess.run(native_command(opt)+['-o',str(exe),str(p)],cwd=root,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
        q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles.append(opt)
    report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,record_bytes_checked=184,helper_observations=True,incoming_home_mutations_and_zero_ranges_excluded=True)
    (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
