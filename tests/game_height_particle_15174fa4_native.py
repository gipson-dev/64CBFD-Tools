"""Native32 record bytes and call packets against the independent guest model."""
import itertools,json,subprocess
from tools.tests import game_height_particle_15174fa4_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
UNITS=((0x92,2),(0x94,4),(0x98,4),(0x9c,4),(0xa0,4),(0xa4,2),(0xa6,2),*((a,4) for a in range(0xa8,0xd0,4)),(0xd0,2),(0xd4,2),(0xd6,2),(0xdc,2),(0xe0,4),(0xe4,4),(0xe8,4))
def digest(m):
    data=[m[g.PARTICLES+n*256+i] for n in range(4) for i in range(248)]
    for a in (*(g.HEIGHTS+i for i in range(192)),*(g.MODEL+i for i in range(4)),*(g.MARK+i for i in range(4))):data.append(m[a])
    v=2166136261
    for b in data:v=g.u32((v^b)*16777619)
    return v
def main():
    cases=[]
    for n,fail,elevated,hits,mutation,alias in itertools.product((-1,0,1,3),(0,1,3),(0,1),(0,-1,1,5,9),(0,1),(False,True)):
        cases.append(g.Case(count=n,fail=fail,elevated=elevated,hits=hits,mutation=mutation,alias=alias,seed=len(cases)%7,width=(1,128,-1,-2147483648)[len(cases)%4]))
    for width,base,spread in itertools.product((2,3,1024),(-3.25,-0.,.8),(0.,-.5,2.)):
        cases.append(g.Case(width=width,base=g.bits(base),spread=g.bits(spread),elevated=len(cases)&1,seed=len(cases)%7))
    rows=[]
    for c in cases:
        want,calls,trap=g.reference(g.fixture(c),c);assert not trap
        rows.append('{{%s},%d,%d,%d,%d,%d,0x%Xu,%d,{%s}}'%(','.join('0x%Xu'%v for v in g.args(c)),c.fail,c.hits,c.alias,c.mutation,c.seed,digest(want),len(calls),','.join('{0x%Xu,%d,{%s}}'%(t,len(a),','.join('0x%Xu'%v for v in a)) for t,a in calls)))
    candidate=(g.source.OUT/'selected.c').read_text();preamble=candidate[:candidate.index('/* Recovered routine and remaining placeholders')];selected=body(candidate,g.source.NAME)
    code=preamble+r'''
_Static_assert(sizeof(Particle15174FA4)==248,"particle ABI");
_Static_assert(sizeof(Height15174FA4)==16,"height stride");
struct Log {u32 target,count,args[6];};
struct Case {s32 args[10];s32 fail,hits,alias,mutation,seed;u32 digest,count;struct Log log[48];};
static const struct Case cases[]={ROWS};static const struct Case *c;
static Particle15174FA4 particles[4];Height15174FA4 D_800D3300[12];void *D_800DDF14;
static u32 callCount,randomCount,allocationCount,error,mark;
static f32 real(u32 b){union{u32 u;f32 f;}v;v.u=b;return v.f;}
static u32 randomWord(u32 n){static const u32 values[]={0,0xFFFFFFFF,127,31,255,65535,15,1};return c->seed%3 ? ((u32)c->seed*0x9E3779B9u+n*0x41C64E6Du)^0xA55AFF00u : values[(n-1)%8];}
static u32 heightWord(u32 n){static const s32 values[]={2147483647,-1,-257,0,(-2147483647-1),0x12345678,-256,256,257};return (u32)values[(n+(u32)c->seed)%9];}
static void record(u32 t,u32 n,const u32 *a){
    u32 i;const struct Log *l;
    if(callCount>=c->count){error=1;return;}l=&c->log[callCount];
    if(l->target!=t||l->count!=n)error=2;
    for(i=0;i<n;i++)if(l->args[i]!=a[i])error=3;
    callCount++;mark=t^callCount*0x1020304u;
    if(c->mutation&1){
        D_800DDF14=(void*)(0x76540000u+callCount*256);
        for(i=0;i<4;i++)particles[i].flags=0x8010+callCount;
        for(i=0;i<12;i++)D_800D3300[i].fixedHeight=heightWord(i)+callCount*0x101;
    }
}
void func_1510F800(s32 context){u32 a[]={context};record(0x1510F800,1,a);}
void *func_15167A68(s32 a0,s32 a1,s32 a2,s32 a3,u8 a4,u8 a5){u32 a[]={a0,a1,a2,a3,a4,a5};record(0x15167A68,6,a);allocationCount++;return allocationCount>(u32)c->fail ? 0 : &particles[c->alias?0:allocationCount-1];}
u32 func_150ADA20(void){record(0x150ADA20,0,0);randomCount++;return randomWord(randomCount);}
s32 func_150A3A70(s32 x,s32 z){u32 a[]={x,z};record(0x150A3A70,2,a);return c->hits;}
void func_1516979C(struct102 *r){u32 a[]={0x50000u+(u32)((Particle15174FA4*)r-particles)*256};record(0x1516979C,1,a);}
SELECTED
static const u8 units[][2]={UNITS};
static void hashByte(u32 *h,u8 b){*h=(*h^b)*16777619u;}
static void hashWord(u32 *h,u32 w){s32 i;for(i=24;i>=0;i-=8)hashByte(h,w>>i);}
static u32 digest(void){
    u32 h=2166136261u,n,i,j,source;u8 *p;
    for(n=0;n<4;n++){p=(u8*)&particles[n];for(i=0;i<248;i++){
        source=i;for(j=0;j<sizeof(units)/sizeof(units[0]);j++)if(i>=units[j][0]&&i<units[j][0]+units[j][1]){source=2*units[j][0]+units[j][1]-1-i;break;}
        hashByte(&h,p[source]);
    }}
    for(n=0;n<12;n++){hashWord(&h,(u32)D_800D3300[n].fixedHeight);for(i=0;i<3;i++)hashWord(&h,D_800D3300[n].retained04[i]);}
    hashWord(&h,(u32)D_800DDF14);hashWord(&h,mark);return h;
}
static u32 run(void){
    u32 k,n,i,j,at,size;u8 *p,tmp;
    for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){
        c=&cases[k];callCount=randomCount=allocationCount=error=mark=0;
        for(n=0;n<4;n++){
            p=(u8*)&particles[n];for(i=0;i<248;i++)p[i]=(u8)(i*29+c->seed*11+n+0x59);
            for(j=0;j<sizeof(units)/sizeof(units[0]);j++){at=units[j][0];size=units[j][1];for(i=0;i<size/2;i++){tmp=p[at+i];p[at+i]=p[at+size-1-i];p[at+size-1-i]=tmp;}}
        }
        for(n=0;n<12;n++){D_800D3300[n].fixedHeight=heightWord(n);for(i=0;i<3;i++)D_800D3300[n].retained04[i]=0xABCDEF00u+n*4+i+1;}
        D_800DDF14=(void*)0x98765430u;
        func_15174FA4(c->args[0],c->args[1],c->args[2],c->args[3],c->args[4],c->args[5],c->args[6],c->args[7],real((u32)c->args[8]),real((u32)c->args[9]));
        if(error||callCount!=c->count||digest()!=c->digest)return 10+error;
    }return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    code=code.replace('ROWS',',\n'.join(rows)).replace('SELECTED',selected).replace('UNITS',','.join('{%d,%d}'%u for u in UNITS));src=g.source.OUT/'native.c';src.write_text(code);reports=[]
    for opt in ('-O0','-O2','-O3'):
        exe=g.source.OUT/('native'+opt);p=subprocess.run([*native_command(opt),'-o',str(exe),str(src)],cwd=g.source.ROOT,capture_output=True,text=True);(g.source.OUT/('native'+opt+'-diagnostics.txt')).write_text(p.stdout+p.stderr)
        if p.returncode:raise ValueError(p.stderr[-5000:])
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode)
        reports.append(dict(optimization=opt,cases=len(cases),undefined_sanitizer=True))
    for label,old,new in (('wrong-minimum',' < lowest',' > lowest'),('wrong-mode','if (elevated == 0)','if (elevated != 0)'),('wrong-height-shift','lowest >>= 8','lowest >>= 7')):
        changed=code.replace(old,new);assert changed!=code;src=g.source.OUT/(label+'.c');src.write_text(changed);exe=src.with_suffix('')
        p=subprocess.run([*native_command('-O2'),'-o',str(exe),str(src)],cwd=g.source.ROOT,capture_output=True,text=True);assert p.returncode==0,p.stderr
        p=subprocess.run([str(exe)],capture_output=True);assert 0<p.returncode<128,(label,p.returncode)
    reports.append(dict(effective_semantic_controls=3));(g.source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
