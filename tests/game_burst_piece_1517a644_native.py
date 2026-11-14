"""Native 32-bit initialization, helper observations and effective controls."""
from pathlib import Path
import json,os,subprocess
from tools.tests import game_burst_piece_1517a644_oracle as b
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def digest(observation):
    record,c1,c2=observation;h=2166136261
    for value in (*record,c1,c2):h=((h^value)*16777619)&0xffffffff
    return h
def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/b.source.BUILD;values=b.constants(root);body=b.source.SELECTED
    bad={'wrong_category':body.replace('(9, 0, 0xB8','(8, 0, 0xB8'),'wrong_allocation_size':body.replace('0xB8','0xB4'),'wrong_pitch':body.replace('angleX = 90','angleX = 91'),'wrong_angle_modulus':body.replace('% 360','% 359'),'wrong_floor_offset':body.replace('height + 3.0f','height + 4.0f'),'wrong_timer':body.replace('timer = 0','timer = 1')}
    assert all(v!=body for v in bad.values()) and len(set(bad.values()))==6
    selected=(out/'selected.c').read_text();a=selected.index('typedef struct {');z=selected.index('} SettleFade1517A84C;',a)+len('} SettleFade1517A84C;')
    code='#include <ultra64.h>\ns32 func_150ADA20(void);\n'+selected[a:z]+'\n'+b.source.DECLS+'\n'+'\n'.join(v.replace(b.source.NAME,'candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
    code+='\ntypedef union {u32 u;f32 f;} Bits;\ntypedef struct {u32 size,kind,x,y,z,outcome,floor,pattern,seed,mutation,n;u8 expected[184];u32 targets[7],digests[7];} Case;\nstatic const Case cases[]={\n'
    rows=[];arr=lambda xs:'{'+','.join(hex(b.u32(x))+'u' for x in xs)+'}'
    for c in b.cases():
        if c.phase or c.mutation&2:continue
        expected,calls,obs=b.reference(b.fixture(c,values),c);args=(c.size,c.kind,c.x,c.y,c.z,c.outcome,c.floor,c.pattern,c.seed,c.mutation,len(calls))
        targets=[t for t,_ in calls]+[0]*(7-len(calls));hashes=[digest(o) for _,o in obs]+[0]*(7-len(obs))
        rows.append('{'+','.join(hex(b.u32(x))+'u' for x in args)+','+arr(b.record(expected))+','+arr(targets)+','+arr(hashes)+'}')
    code+=',\n'.join(rows)+'\n};\n'+r'''
typedef char Layout[sizeof(SettleFade1517A84C)==184&&__builtin_offsetof(SettleFade1517A84C,x)==0x90&&__builtin_offsetof(SettleFade1517A84C,scale)==0xa8&&__builtin_offsetof(SettleFade1517A84C,opacity)==0xb3?1:-1];
static SettleFade1517A84C storage;static const Case*current;static u32 calls,draws,error;f32 D_800A7224,D_800A7228;
static f32 real(u32 u){Bits b;b.u=u;return b.f;}static u32 word(f32 f){Bits b;b.f=f;return b.u;}
static u32 byteIndex(u32 k){if((k>=0x90&&k<0x9c)||(k>=0xa0&&k<0xa8)||(k>=0xb0&&k<0xb2))return k^1u;if(k>=0xa8&&k<0xac)return k^3u;return k;}
static u32 targetByte(u32 k){return ((u8*)&storage)[byteIndex(k)];}
static u32 digest(void){u32 i,h=2166136261u;for(i=0;i<184;i++)h=(h^targetByte(i))*16777619u;h=(h^word(D_800A7224))*16777619u;return (h^word(D_800A7228))*16777619u;}
static u32 check(u32 target){u32 n=calls++;if(n>=current->n||n>=7){error=1;return n;}if(current->targets[n]!=target||current->digests[n]!=digest())error=1;return n;}
static void effect(u32 n,u32 target){if(current->mutation&1){D_800A7224=(n+1)*.125f;D_800A7228=((s32)n-2)*.25f;if(current->outcome)storage.retained00[0x50]^=(u8)(n+1);if(target==0x1510e82cu&&current->outcome)storage.retainedB2^=0x55;}}
void*func_15167A68(s32 category,s32 group,s32 bytes,s32 mode,u8 priority,u8 flag){u32 n=check(0x15167a68u);if(category!=9||group||bytes!=184||mode!=1||priority!=255||flag!=1)error=1;if(current->outcome){((u8*)&storage)[1]=0;((u8*)&storage)[12]=255;}effect(n,0x15167a68u);return current->outcome?&storage:0;}
void func_1510E82C(s32 a,s32 b,f32*out,s32 d,s32 e,s32 f,f32 x,f32 y,f32 z,f32 secondY,u16 flags,s32 last){u32 n=check(0x1510e82cu);if(a||b||d||e||f||flags||last||!out||word(x)!=word((f32)(s16)current->x)||word(y)!=word((f32)(s16)current->y)||word(z)!=word((f32)(s16)current->z)||word(secondY)!=word(y))error=1;*out=real(current->floor);effect(n,0x1510e82cu);}
s32 func_150ADA20(void){u32 n=check(0x150ada20u),value;if(current->pattern==0)value=0;else if(current->pattern==1)value=0xffffffffu;else value=(current->seed+draws)*1664525u+1013904223u;draws++;effect(n,0x150ada20u);return (s32)value;}
static void(*candidates[])(f32,u8,s16,s16,s32)={candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5,candidate_6};
static int run(void){u32 i,j,k,killed=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;for(j=0;j<7;j++){for(k=0;k<184;k++)((u8*)&storage)[k]=(u8)(byteIndex(k)*29+current->seed*11+0x5a);D_800A7224=real(INIT1);D_800A7228=real(INIT2);calls=draws=error=0;candidates[j](real(current->size),(u8)current->kind,(s16)current->x,(s16)current->y,(s32)current->z);if(calls!=current->n)error=1;for(k=0;k<184;k++)if(targetByte(k)!=current->expected[k])error=1;if(error){if(!j)return 10;killed|=1u<<(j-1);}}}return killed==63u?0:11;}
'''.replace('INIT1',hex(values[b.C1])+'u').replace('INIT2',hex(values[b.C2])+'u')+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    p=out/'native.c';p.write_text(code);profiles=[]
    for opt in ('-O0','-O2','-O3'):
        exe=out/('native'+opt);q=subprocess.run(native_command(opt)+['-o',str(exe),str(p)],cwd=root,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
        q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr);profiles.append(opt)
    report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,all_record_bytes_checked=184,helper_observations=True,mutable_homes_excluded=True)
    (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
