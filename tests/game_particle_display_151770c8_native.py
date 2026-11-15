"""Native32 renderer bytes and opaque matrix-helper snapshots with effective controls."""
import itertools,json,subprocess
from tools.tests import game_particle_display_151770c8_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def main():
    source=g.source;cases=[]
    for status,reject,view,page,mode in itertools.product((0,1,2,3,255),(0,1),(0,1,3),(0,1),(0,1)):
        cases.append(g.Case(state=status,reject=reject,view=view,page=page,mutation=mode,seed=len(cases)%17))
    cases.extend(g.Case(state=i,seed=i) for i in range(256))
    arr=lambda xs:'{'+','.join('0x%Xu'%g.u32(v) for v in xs)+'}'
    rows=[]
    for c in cases:
        initial=g.fixture(c);want,calls,obs,result=g.reference(initial,c)
        packets=['{0x%Xu,%d,%s,%s}'%(t,len(a),arr((*a,*([0]*(10-len(a))))),arr((*o,*([0]*(16-len(o)))))) for (t,a),o in zip(calls,obs)]
        fields=(c.state,c.reject,c.view,c.page,c.mutation,c.seed)
        rows.append('{'+','.join(str(v) for v in fields)+','+','.join(arr(v) for v in ([initial[g.RECORD+i] for i in range(248)],[want[g.RECORD+i] for i in range(248)],[g.read(initial,a) for a in g.FLOATS],[g.read(want,a) for a in g.FLOATS],[g.read(want,g.MODELS+4*i) for i in range(55)],[g.read(want,g.COMMANDS+4*i) for i in range(32)]))+',%d,0x%Xu,0x%Xu,%d,{%s}}'%(want[g.PAGE],g.read(want,g.MARK),result,len(calls),','.join(packets)))
    owner=(source.OUT/'selected.c').read_text();preamble=owner[:owner.index('/* Recovered routine and remaining placeholders')]
    code=preamble+r'''
_Static_assert(sizeof(Particle15175390)==248,"particle ABI");
_Static_assert(sizeof(Gfx)==8&&sizeof(Mtx)==64,"graphics ABI");
typedef union{u32 u;f32 f;}Bits;
struct Packet{u32 target,count,args[10],matrix[16];};
struct Case{u32 state,reject,view,page,mutation,seed;u8 initial[248],expected[248];u32 first[3],last[3],models[55],commands[32],finalPage,mark,result,count;struct Packet packets[3];};
static const struct Case cases[]={ROWS};static const struct Case*c;
static Particle15175390 record;static Gfx commands[16];
f32 D_800D9B20,D_800D35E0,D_800D35E4;u8 D_800D9C10[256],D_800BE9C0;Gfx *D_800DDE80[55];
static u32 calls,error,mark;static f32(*matrixPointer)[4];
static f32 real(u32 u){Bits b;b.u=u;return b.f;}
static u32 word(f32 f){Bits b;b.f=f;return b.u;}
static u32 canon(u32 v){u32 p=(u32)&record;if(v>=p&&v<p+248)return 0x50000u+v-p;
p=(u32)commands;if(v>=p&&v<p+128)return 0x60000u+v-p;
p=(u32)D_800D9C10;if(v>=p&&v<p+256)return 0x800d9c10u+v-p;
if(matrixPointer&&v==(u32)matrixPointer)return SCRATCH;return v;}
static u32 indexByte(u32 i){return (i>=0x98&&i<0xa4)||(i>=0xa8&&i<0xb4)?i^3u:i;}
static void setFloat(u32 i,u32 v){if(i==0)D_800D9B20=real(v);else if(i==1)D_800D35E0=real(v);else D_800D35E4=real(v);}
static u32 getFloat(u32 i){return word(i==0?D_800D9B20:i==1?D_800D35E0:D_800D35E4);}
static void notify(u32 target,u32 count,const u32*a){u32 n=calls++,i;const struct Packet*p;
if(target==0x150a8050)matrixPointer=(f32(*)[4])a[0];
if(n>=c->count||n>=3)error=1;else{p=c->packets+n;if(p->target!=target||p->count!=count)error=2;
for(i=0;i<count;i++)if(p->args[i]!=canon(a[i]))error=3;
if(target==0x150a7790)for(i=0;i<16;i++)if(p->matrix[i]!=word(matrixPointer[i/4][i%4]))error=4;}
n++;mark=target^n*0x1020304u;
if(target==0x150a8050)for(i=0;i<16;i++)matrixPointer[i/4][i%4]=real(0x3f000000u+i*0x10000u+n*0x80u);
else if(target==0x150a7790)for(i=0;i<64;i++)((u8*)a[1])[i]=(u8)(i*7+n*3+c->seed);
else if(target==0x15176df0){Gfx*p=(Gfx*)a[0];p->words.w0=0xf1000000u|n;p->words.w1=0x12340000u|n;}
if(c->mutation&1){record.state91=(c->seed+n)%4;D_800BE9C0^=1;
for(i=0;i<3;i++)record.position[i]=real(0x3f800000u+(n*8+i)*0x10000u);
record.tilt=real(0x3f800000u+(n*8+3)*0x10000u);record.heading=real(0x3f800000u+(n*8+4)*0x10000u);record.fieldB0=real(0x3f800000u+(n*8+5)*0x10000u);
for(i=0;i<55;i++)D_800DDE80[i]=(Gfx*)(0x87650000u+n*256+i);
for(i=0;i<3;i++)setFloat(i,0xbf000000u+(n*3+i)*0x10000u);}}
s32 func_1510AEE0(void*p,f32 x,f32 y,f32 z,f32 a,f32 b,f32 d,f32 e,f32*f,f32*h){u32 args[]={(u32)p,word(x),word(y),word(z),word(a),word(b),word(d),word(e),(u32)f,(u32)h};notify(0x1510aee0,10,args);return c->reject;}
void func_150A8050(f32 m[4][4],f32 x,f32 y,f32 z){u32 a[]={(u32)m,word(x),word(y),word(z)};notify(0x150a8050,4,a);}
void guMtxF2L(f32 m[4][4],Mtx*p){u32 a[]={(u32)m,(u32)p};notify(0x150a7790,2,a);}
s32 func_15176DF0(Gfx*p,Particle15175390*r,s32 view){u32 a[]={(u32)p,(u32)r,(u32)view};notify(0x15176df0,3,a);return (s32)((u32)p+8*(1+c->seed%2));}
CANDIDATES
static Gfx*(*tests[])(Gfx*,Particle15175390*,s16)={TESTS};
static u32 run(void){u32 k,t,i,failed,killed=0;Gfx*answer;
for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){c=cases+k;for(t=0;t<6;t++){
calls=error=mark=0;matrixPointer=0;
for(i=0;i<248;i++)((u8*)&record)[indexByte(i)]=c->initial[i];
for(i=0;i<32;i++)((u32*)commands)[i]=0xa5a5a5a5u;
for(i=0;i<3;i++)setFloat(i,c->first[i]);D_800BE9C0=c->page;
for(i=0;i<55;i++)D_800DDE80[i]=(Gfx*)(0x81230000u+i*0x100+c->seed);
answer=tests[t](commands,&record,(s16)c->view);failed=error||calls!=c->count||canon((u32)answer)!=c->result||D_800BE9C0!=c->finalPage||mark!=c->mark;
for(i=0;i<248;i++)if(((u8*)&record)[indexByte(i)]!=c->expected[i])failed=1;
for(i=0;i<3;i++)if(getFloat(i)!=c->last[i])failed=1;
for(i=0;i<55;i++)if((u32)D_800DDE80[i]!=c->models[i])failed=1;
for(i=0;i<32;i++)if(canon(((u32*)commands)[i])!=c->commands[i])failed=1;
if(!t&&failed)return 10+error;if(t&&failed)killed|=1u<<(t-1);
}}return killed==31?0:30;}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    body=source.SELECTED;negatives=(body.replace('4000.0f','4001.0f'),body.replace('D_800BE9C0 * 64','D_800BE9C0 * 32'),body.replace('case 0:','case 5:'),body.replace('D_800DDE80[51]','D_800DDE80[50]'),body.replace('D_800DDE80[53]','D_800DDE80[52]'))
    assert all(v!=body for v in negatives)
    candidates='\n'.join(s.replace(source.NAME,'candidate_'+str(i)) for i,s in enumerate((body,*negatives)))
    code=code.replace('ROWS',',\n'.join(rows)).replace('SCRATCH','0x%Xu'%g.scratch(g.Case())).replace('CANDIDATES',candidates).replace('TESTS',','.join('candidate_'+str(i) for i in range(6)))
    src=source.OUT/'native.c';src.write_text(code);reports=[]
    for opt in ('-O0','-O2','-O3'):
        exe=source.OUT/('native'+opt);p=subprocess.run([*native_command(opt),'-o',str(exe),str(src)],cwd=source.ROOT,capture_output=True,text=True)
        (source.OUT/('native'+opt+'-diagnostics.txt')).write_text(p.stdout+p.stderr)
        if p.returncode:raise ValueError(p.stderr[-5000:])
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode)
        reports.append(dict(optimization=opt,cases=len(cases),undefined_sanitizer=True,record_bytes=248,command_bytes=128,matrix_snapshot_words=16,effective_controls=5))
    (source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
