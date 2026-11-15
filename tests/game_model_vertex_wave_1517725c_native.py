"""Native32 valid slots, full state/vertex bytes and effective semantic controls."""
import itertools,json,subprocess
from tools.tests import game_model_vertex_wave_1517725c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def main():
    rows=[];cases=[g.Case(slot=slot,angle=g.bits(angle),speed=g.bits((-2.,1.,400.)[slot%3]),mode=mode,seed=slot%8)for slot,angle,mode in itertools.product(range(11),(0.,359.5,360.,720.,-30.),(0,1,21,63))]
    cases += [g.Case(slot=i%11,seed=i,mode=i&63,outer=g.bits((-65535.75,-1.,0.,0.75,32768.75,65535.5)[i%6]),inner=g.bits((0.,-32768.75,1.5,12345.75)[i%4]))for i in range(64)]
    arr=lambda xs:'{'+','.join('0x%Xu'%g.u32(x)for x in xs)+'}'
    for c in cases:
        initial=g.fixture(c);want,calls=g.reference(initial,c);p=g.address(c)
        vectors=([initial[p+i]for i in range(56)],[want[p+i]for i in range(56)],[initial[g.VERTICES+i]for i in range(512)],[want[g.VERTICES+i]for i in range(512)],g.values(c),[g.read(want,p)for p in g.COEFFS])
        rows.append('{%d,%d,%d,'%(c.slot,c.mode,c.seed)+','.join(arr(x)for x in vectors)+',0x%Xu,0x%Xu,{'%(g.read(want,g.MODELS+c.slot*20),g.read(want,g.MARK))+','.join('{0x%Xu,0x%Xu}'%(t,a[0])for t,a in calls)+'}}')
    owner=(g.source.OUT/'selected.c').read_text();preamble=owner[:owner.index('/* Recovered routine and remaining placeholders')]
    code=preamble+r'''
_Static_assert(sizeof(VertexWave1517725C)==56,"state ABI");
_Static_assert(sizeof(Vtx)==16,"vertex ABI");
typedef union{u32 u;f32 f;}Bits;
struct Case{u32 slot,mode,seed;u8 initial[56],expected[56],vertices[512],lastVertices[512];u32 values[6],coeffs[4],model,mark,packets[6][2];};
static const struct Case cases[]={ROWS};static const struct Case*c;
VertexWave1517725C D_8008D0B0[11];Model15174BF0 D_800DDE88[11];
f32 D_800A71AC,D_800A71B0,D_800A71B4,D_800A71B8;
static Vtx vertices[32],alternate[32];static u32 calls,error,mark;
static f32 real(u32 u){Bits b;b.u=u;return b.f;}static u32 word(f32 f){Bits b;b.f=f;return b.u;}
static u32 indexByte(u32 i){return i>=24?i^3u:i;}
static f32 notify(u32 target,f32 angle){u32 stage=calls++;VertexWave1517725C*p=D_8008D0B0+c->slot;
if(stage>=6){error=1;return 0;}if(target!=c->packets[stage][0]||word(angle)!=c->packets[stage][1])error=2;
mark=target^((stage+1)*0x1020304u);
if(c->mode>>stage&1){p->phase=30.f+stage*70.f;p->amplitude=20.f+stage;p->outerRadius=32.f+stage;p->innerRadius=16.f+stage;p->speed=-1.f+stage;
D_800DDE88[c->slot].model=alternate;D_800A71AC=(stage+1)/128.f;D_800A71B0=(stage+2)/128.f;D_800A71B4=(stage+3)/128.f;D_800A71B8=(stage+4)/128.f;}
return real(c->values[stage]);}
f32 func_150AD78C(f32 f){return notify(0x150ad78c,f);}f32 func_150AD780(f32 f){return notify(0x150ad780,f);}
CANDIDATES
static void(*tests[])(u8)={TESTS};
static u32 run(void){u32 k,t,i,j,failed,killed=0;u32 coeffs[4];
for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){c=cases+k;for(t=0;t<6;t++){
calls=error=mark=0;for(i=0;i<sizeof(D_8008D0B0);i++)((u8*)D_8008D0B0)[i]=0x5a;
for(i=0;i<56;i++)((u8*)(D_8008D0B0+c->slot))[indexByte(i)]=c->initial[i];
for(i=0;i<512;i++){((u8*)vertices)[i^1u]=c->vertices[i];((u8*)alternate)[i]=0x6b;}
for(i=0;i<11;i++)D_800DDE88[i].model=vertices;
D_800A71AC=D_800A71B0=D_800A71B4=D_800A71B8=real(0x3c8efa35);
tests[t]((u8)c->slot);failed=error||calls!=6||mark!=c->mark;
for(i=0;i<56;i++)if(((u8*)(D_8008D0B0+c->slot))[indexByte(i)]!=c->expected[i])failed=1;
for(j=0;j<11;j++)if(j!=c->slot)for(i=0;i<56;i++)if(((u8*)(D_8008D0B0+j))[i]!=0x5a)failed=1;
for(i=0;i<512;i++)if(((u8*)vertices)[i^1u]!=c->lastVertices[i]||((u8*)alternate)[i]!=0x6b)failed=1;
if(D_800DDE88[c->slot].model!=(c->model==0x50000?vertices:alternate))failed=1;
coeffs[0]=word(D_800A71AC);coeffs[1]=word(D_800A71B0);coeffs[2]=word(D_800A71B4);coeffs[3]=word(D_800A71B8);
for(i=0;i<4;i++)if(coeffs[i]!=c->coeffs[i])failed=1;
if(!t&&failed)return 10+error;if(t&&failed)killed|=1u<<(t-1);
}}return killed==31?0:30;}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    body=g.source.SELECTED;controls=(body.replace('state->outerRadius *','state->innerRadius *'),body.replace('state->phase - 30.0f','state->phase - 0.0f'),body.replace('vertices[18].v.ob[1]','vertices[18].v.ob[2]'),body.replace('state->phase >= 360.0f','state->phase >= 720.0f'),body.replace('sine = func_150AD78C(angle);','sine = func_150AD780(angle);'))
    assert all(x!=body for x in controls)
    code=code.replace('ROWS',',\n'.join(rows)).replace('CANDIDATES','\n'.join(s.replace(g.source.NAME,'candidate_'+str(i))for i,s in enumerate((body,*controls)))).replace('TESTS',','.join('candidate_'+str(i)for i in range(6)))
    src=g.source.OUT/'native.c';src.write_text(code);reports=[]
    for opt in ('-O0','-O2','-O3'):
        exe=g.source.OUT/('native'+opt);p=subprocess.run([*native_command(opt),'-o',str(exe),str(src)],cwd=g.source.ROOT,capture_output=True,text=True);(g.source.OUT/('native'+opt+'-diagnostics.txt')).write_text(p.stdout+p.stderr)
        if p.returncode:raise ValueError(p.stderr[-5000:])
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode)
        reports.append(dict(optimization=opt,cases=len(cases),undefined_sanitizer=True,state_bytes=616,vertex_bytes=1024,effective_controls=5))
    (g.source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
