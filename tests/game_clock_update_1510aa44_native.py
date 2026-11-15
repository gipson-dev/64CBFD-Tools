"""Finite native32 clock, live provider mutations and complete chime packets."""
import json,subprocess
from tools.tests import game_clock_update_1510aa44_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def main():
    arr=lambda xs:'{'+','.join('0x%Xu'%(v&0xffffffff)for v in xs)+'}';rows=[]
    words=lambda m,p:[g.read(m,p+i*4)for i in range(g.LENGTH//4)]
    for initial,args,native in g.corpus():
        if not native:continue
        want,calls,snapshots=g.model(initial,args);snapshot=[int.from_bytes(snapshots[0][i:i+4],'big')for i in range(0,g.LENGTH,4)]if snapshots else[0]*68
        rows.append('{'+','.join((arr(words(initial,g.OWNER)),arr([g.read(initial,g.SEED),g.read(initial,g.STEP)]),str(args[1]),arr(words(want,g.OWNER)),arr([g.read(want,g.SEED),g.read(want,g.STEP)]),str(len(calls)),arr(snapshot)))+'}')
    body=g.source.SELECTED
    changes=(('% 43200U','% 43201U'),('* 180U','* 181U'),('>= 2592000','>= 2591999'),('minute / 15','minute / 14'),('0x4CC','0x4CB'),('- 1U','+ 1U'),('minute * 6.0f','minute * 5.0f'))
    candidates=(body,*[body.replace(a,b)for a,b in changes]);assert all(c!=body for c in candidates[1:])
    code=r'''
#include <ultra64.h>
typedef union{u32 words[68];f32 floats[68];u8 bytes[272];}Record;
static Record record; s32 D_800BE3E4,D_800BE9E4;
static u32 mode,callCount,bad,snapshot[68];
s32 func_15114D24(u8 *p,s32 id,s32 volume,s16 pitch,s16 distance,s32 flags){
u32 i;callCount++;if(p!=record.bytes||id!=0x4cc||volume!=32767||pitch!=200||distance!=1000||flags!=12)bad=1;
for(i=0;i<68;i++)snapshot[i]=record.words[i];
if(mode&1){record.words[15]=0xabcdef01u;record.words[31]=17;record.words[32]=99;record.words[26]=0x3f000000u;record.words[66]=0x3f800000u;record.words[42]=0x40000000u;record.words[2]=0x40400000u;}
if(mode&2){D_800BE3E4=-1;D_800BE9E4=(s32)0x80000000u;}return (s32)0xa5000002u;}
CANDIDATES
static void(*tests[])(u8*)={TESTS};
struct Case{u32 before[68],globals[2],mode,after[68],lastGlobals[2],calls,snapshot[68];};
static const struct Case cases[]={ROWS};static u32 caseIndex;
static u32 run(void){u32 k,t,i,failed,killed=0;const struct Case*c;
for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){caseIndex=k;c=cases+k;for(t=0;t<8;t++){
for(i=0;i<68;i++){record.words[i]=c->before[i];snapshot[i]=0;}D_800BE3E4=(s32)c->globals[0];D_800BE9E4=(s32)c->globals[1];mode=c->mode;bad=callCount=0;
tests[t](record.bytes);failed=bad||callCount!=c->calls||(u32)D_800BE3E4!=c->lastGlobals[0]||(u32)D_800BE9E4!=c->lastGlobals[1];
for(i=0;i<68;i++)if(record.words[i]!=c->after[i]||snapshot[i]!=c->snapshot[i])failed=1;
if(!t&&failed)return 10;if(t&&failed)killed|=1u<<(t-1);
}}return killed==127?0:30;}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();if(status){u32 data[]={status,caseIndex};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(data),"d"(sizeof(data)):"memory");}__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    code=code.replace('CANDIDATES','\n'.join(c.replace(g.source.NAME,'candidate_'+str(i))for i,c in enumerate(candidates))).replace('TESTS',','.join('candidate_'+str(i)for i in range(8))).replace('ROWS',',\n'.join(rows))
    src=g.source.OUT/'native.c';src.write_text(code);reports=[]
    for opt in('-O0','-O2','-O3'):
        exe=g.source.OUT/('native'+opt);p=subprocess.run([*native_command(opt),'-o',str(exe),str(src)],cwd=g.source.ROOT,capture_output=True,text=True);(g.source.OUT/('native'+opt+'-diagnostics.txt')).write_text(p.stdout+p.stderr)
        assert p.returncode==0,p.stderr[-5000:]
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stdout.hex())
        reports.append(dict(optimization=opt,cases=len(rows),effective_controls=7,whole_record_bytes=272,full_chime_snapshots=True,undefined_sanitizer=True,guest_private_aliases_claimed=False))
    (g.source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
