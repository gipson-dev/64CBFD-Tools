"""Finite native32 projection and matrix/shared-output aliases under O0/O2/O3."""
import json,struct,subprocess
from tools.tests import game_projection_bounds_1510aee0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def main():
    arr=lambda xs:'{'+','.join('0x%Xu'%v for v in xs)+'}';rows=[]
    for initial,args,phase,native in g.corpus():
        if not native:continue
        answer,want,depth=g.model(initial,args,phase)
        if answer==0 and depth==0 and any(args[-2:]):continue
        rows.append('{'+','.join((arr([g.read(initial,g.MATRIX+i*4)for i in range(16)]),arr(args[1:8]),arr(args[8:]),arr([g.read(initial,g.OUTPUT+i*4)for i in range(4)]),arr([g.read(want,g.MATRIX+i*4)for i in range(16)]),arr([g.read(want,g.OUTPUT+i*4)for i in range(4)]),str(answer)))+'}')
    body=g.source.SELECTED
    controls=(body.replace('depth < nearPlane','depth <= nearPlane'),body.replace('farPlane < depth','farPlane <= depth'),body.replace('1.0f - horizontal / depth','1.0f + horizontal / depth'),body.replace('component = matrix[0][1] * x','component = matrix[0][0] * x'),body.replace('1.0f - vertical / depth','1.0f + vertical / depth'))
    assert all(x!=body for x in controls)
    code=r'''
#include <ultra64.h>
typedef union{u32 u;f32 f;}Bits;
static f32 real(u32 u){Bits b;b.u=u;return b.f;}static u32 word(f32 f){Bits b;b.f=f;return b.u;}
f32 fabsf(f32 f){return real(word(f)&0x7fffffffu);}
CANDIDATES
static s32(*tests[])(f32[4][4],f32,f32,f32,f32,f32,f32,f32,f32*,f32*)={TESTS};
struct Case{u32 matrix[16],args[7],pointers[2],output[4],lastMatrix[16],lastOutput[4],answer;};
static const struct Case cases[]={ROWS};static f32 matrix[4][4],output[4];static u32 caseIndex;
static f32*pointer(u32 p){u32 i;if(!p)return 0;if(p>=0x30000u&&p<0x30040u){i=(p-0x30000u)/4;return &matrix[i/4][i%4];}return output+(p-0x50000u)/4;}
static u32 run(void){u32 k,t,i,failed,killed=0;const struct Case*c;s32 answer;
for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){caseIndex=k;c=cases+k;for(t=0;t<6;t++){
for(i=0;i<16;i++)matrix[i/4][i%4]=real(c->matrix[i]);for(i=0;i<4;i++)output[i]=real(c->output[i]);
answer=tests[t](matrix,real(c->args[0]),real(c->args[1]),real(c->args[2]),real(c->args[3]),real(c->args[4]),real(c->args[5]),real(c->args[6]),pointer(c->pointers[0]),pointer(c->pointers[1]));
failed=(u32)answer!=c->answer;for(i=0;i<16;i++)if(word(matrix[i/4][i%4])!=c->lastMatrix[i])failed=1;for(i=0;i<4;i++)if(word(output[i])!=c->lastOutput[i])failed=1;
if(!t&&failed)return 10;if(t&&failed)killed|=1u<<(t-1);
}}return killed==31?0:30;}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();if(status){u32 data[]={status,caseIndex};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(data),"d"(sizeof(data)):"memory");}__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    code=code.replace('ROWS',',\n'.join(rows)).replace('CANDIDATES','\n'.join(x.replace(g.source.NAME,'candidate_'+str(i))for i,x in enumerate((body,*controls)))).replace('TESTS',','.join('candidate_'+str(i)for i in range(6)))
    src=g.source.OUT/'native.c';src.write_text(code);reports=[]
    for opt in('-O0','-O2','-O3'):
        exe=g.source.OUT/('native'+opt);q=subprocess.run([*native_command(opt),'-o',str(exe),str(src)],cwd=g.source.ROOT,capture_output=True,text=True);(g.source.OUT/('native'+opt+'-diagnostics.txt')).write_text(q.stdout+q.stderr)
        if q.returncode:raise ValueError(q.stderr[-5000:])
        q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout.hex())
        reports.append(dict(optimization=opt,cases=len(rows),undefined_sanitizer=True,matrix_words=16,output_words=4,effective_controls=5,finite_nonzero_output_divisors=True))
    (g.source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
