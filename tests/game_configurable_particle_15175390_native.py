"""Native32 ABI, complete record bytes and helper packets versus the guest model."""
import itertools,json,subprocess
from tools.experiments import game_configurable_particle_15175390_match as source
from tools.tests import game_configurable_particle_15175390_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
UNITS=((0x92,2),(0x94,4),(0x98,4),(0x9c,4),(0xa0,4),(0xa4,2),(0xa6,2),*((a,4) for a in range(0xa8,0xc4,4)),(0xc8,4),*((a,2) for a in range(0xd0,0xe0,2)),(0xe0,4),(0xe8,4),(0xee,2))

def main():
    cases=[]
    for n,flags,state,ground,mutation,alias in itertools.product((-1,0,1,3),(0,0x10000,0x20000,0x30000,0x40,0x30040),(0,1,2),(0,1),(0,1),(False,True)):
        k=len(cases)
        cases.append(g.Case(count=n,flags=flags,state=state,ground_flags=ground,mutation=mutation,alias=alias,fail=(0,1,3)[k//2%3],type_range=(0,3)[k//3%2],model_mask=(-1,0,3)[k//5%3],base_type=(10,77,125)[k//7%3],vertical=(-1,0,1,30)[k//11%4],inner=(-5,0,5)[k//13%3],base_model=(0,2,8)[k//17%3],seed=k%7))
    for heading,base,spread in itertools.product((-400.,-15.,0.,360.,720.,2147483520.,-2147483648.),(-3.25,-0.,.8),(0.,-.5,2.)):
        cases.append(g.Case(count=1,flags=0x30003,heading=g.bits(heading),base=g.bits(base),spread=g.bits(spread),seed=len(cases)%7))
    rows=[]
    for c in cases:
        want,calls,trap=g.reference(g.fixture(c),c);assert trap is None and len(calls)<=64
        data=bytes(want[g.PARTICLES+n*256+i] for n in range(4) for i in range(248))
        quoted='"'+''.join('\\x%02x'%b for b in data)+'"'
        rows.append('{{%s},0x%Xu,%d,%d,%d,%d,%d,%s,0x%Xu,0x%Xu,{%s},0x%Xu,{%s},%d,{%s}}'%(
            ','.join('0x%Xu'%v for v in g.args(c)),c.heading,c.fail,c.alias,c.mutation,c.seed,c.ground_height,quoted,g.read(want,g.RATE),g.read(want,g.MARK),','.join('0x%Xu'%g.read(want,g.MODELS+20*i) for i in range(16)),g.u32(g.read(want,g.SCENE)-g.VIEWS),','.join(str(want[g.KINDS+i]) for i in range(4)),len(calls),','.join('{0x%Xu,%d,{%s}}'%(t,len(a),','.join('0x%Xu'%v for v in a)) for t,a in calls)))
    candidate=(source.OUT/'selected.c').read_text();preamble=candidate[:candidate.index('/* Recovered routine and remaining placeholders')]
    code=preamble+r'''
_Static_assert(sizeof(Particle15175390)==248,"particle ABI");
_Static_assert(sizeof(Model15174BF0)==20,"model stride");
_Static_assert(__builtin_offsetof(Particle15175390,sourceX)==0xD0,"source halfword ABI");
_Static_assert(__builtin_offsetof(Particle15175390,sound)==0xEE,"sound ABI");
struct Log {u32 target,count,args[11];};
struct Case {s32 args[18];u32 heading;s32 fail,alias,mutation,seed,groundHeight;u8 bytes[992];u32 rate,mark,models[16],scene;u8 kinds[4];u32 count;struct Log log[64];};
static const struct Case cases[]={ROWS};static const struct Case *c;
static Particle15175390 particles[4];
struct View {u8 prefix[0x2F8];f32 position[3];u8 suffix[0x9A0-0x304];};
static struct View views[4];static u8 surfaces[12*12];static u32 materials[12];
u8 *D_800DBFF0,*D_800DBE3C;u32 *D_800DBE5C;Model15174BF0 D_800DDE88[16];u8 D_800A7170[4];f32 D_800A7178;
static u32 callCount,randomCount,allocationCount,error,mark;
static f32 real(u32 b){union{u32 u;f32 f;}v;v.u=b;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static u32 randomWord(u32 n){static const u32 values[]={0,0xFFFFFFFF,127,31,255,65535,15,1};return c->seed%3 ? ((u32)c->seed*0x9E3779B9u+n*0x41C64E6Du)^0xA55AFF00u : values[(n-1)%8];}
static void record(u32 t,u32 n,const u32 *a){
    u32 i;const struct Log *l;
    if(callCount>=c->count){error=1;return;}l=&c->log[callCount];
    if(l->target!=t||l->count!=n)error=2;
    for(i=0;i<n;i++)if(l->args[i]!=a[i])error=3;
    callCount++;mark=t^callCount*0x1020304u;
    if(c->mutation&1){
        /* Match the independent model's double expression, then round once. */
        D_800A7178=.125+(double)callCount*.01;D_800DBFF0=(u8*)&views+0x1000;
        for(i=0;i<16;i++)D_800DDE88[i].model=(void*)(0x76540000u+callCount*256+i);
        for(i=0;i<4;i++)particles[i].flags=0x8010+callCount;
        for(i=0;i<4;i++)D_800A7170[i]=(u8)(callCount*17+i);
    }
}
f32 func_15048FC8(struct17 *v){u32 a[]={word(v->unk0),word(v->unk4),word(v->unk8)};record(0x15048FC8,3,a);return real(c->heading);}
void *func_15167A68(s32 a0,s32 a1,s32 a2,s32 a3,u8 a4,u8 a5){u32 a[]={a0,a1,a2,a3,a4,a5};record(0x15167A68,6,a);allocationCount++;return allocationCount>(u32)c->fail ? 0 : &particles[c->alias?0:allocationCount-1];}
s32 func_150ADA20(void){record(0x150ADA20,0,0);randomCount++;return (s32)randomWord(randomCount);}
u16 func_10010E78(s32 a0,s32 a1,s32 a2,s32 a3,s32 a4,s32 a5,s32 a6,s32 a7,s32 a8,s32 a9,s32 a10){u32 a[]={a0,a1,a2,a3,a4,a5,a6,a7,a8,a9,a10};record(0x10010E78,11,a);return 0x8001;}
s32 func_1510F8D8(s32 a0,s32 a1,s32 a2,u8 **out){u32 a[]={a0,a1,a2};record(0x1510F8D8,3,a);*out=D_800DBE3C+12*((s32)allocationCount-2);return c->groundHeight-(s32)allocationCount+1;}
SELECTED
static const u8 units[][2]={UNITS};
static u32 compare(void){
    u32 n,i,j,source;u8 *p;
    for(n=0;n<4;n++){p=(u8*)&particles[n];for(i=0;i<248;i++){
        source=i;for(j=0;j<sizeof(units)/sizeof(units[0]);j++)if(i>=units[j][0]&&i<units[j][0]+units[j][1]){source=2*units[j][0]+units[j][1]-1-i;break;}
        if(p[source]!=c->bytes[n*248+i])return 1;
    }}
    if(word(D_800A7178)!=c->rate||mark!=c->mark)return 2;
    for(i=0;i<16;i++)if((u32)D_800DDE88[i].model!=c->models[i])return 3;
    if((u32)D_800DBFF0-(u32)&views!=c->scene)return 4;
    for(i=0;i<4;i++)if(D_800A7170[i]!=c->kinds[i])return 5;
    return 0;
}
static u32 run(void){
    u32 k,n,i,j,at,size;u8 *p,tmp;
    for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){
        c=&cases[k];callCount=randomCount=allocationCount=error=mark=0;
        for(n=0;n<4;n++){
            p=(u8*)&particles[n];for(i=0;i<248;i++)p[i]=(u8)(i*29+c->seed*11+n+0x59);
            for(j=0;j<sizeof(units)/sizeof(units[0]);j++){at=units[j][0];size=units[j][1];for(i=0;i<size/2;i++){tmp=p[at+i];p[at+i]=p[at+size-1-i];p[at+size-1-i]=tmp;}}
        }
        D_800DBFF0=(u8*)&views;views[c->args[6]].position[0]=2.5f;views[c->args[6]].position[1]=-3.25f;views[c->args[6]].position[2]=7.75f;
        D_800A7178=.01f;D_800DBE3C=surfaces+4*12;D_800DBE5C=materials+4;
        for(i=0;i<12;i++)materials[i]=(((i-4)*0x23456789u)^0xABCDEF00u)|((c->seed&3)<<5);
        for(i=0;i<16;i++)D_800DDE88[i].model=(void*)(0x98765000u+i*0x1234);
        D_800A7170[0]=0;D_800A7170[1]=42;D_800A7170[2]=84;D_800A7170[3]=127;
        func_15175390(c->args[0],c->args[1],c->args[2],c->args[3],c->args[4],c->args[5],c->args[6],c->args[7],c->args[8],c->args[9],c->args[10],c->args[11],c->args[12],c->args[13],c->args[14],real((u32)c->args[15]),real((u32)c->args[16]),c->args[17]);
        if(error||callCount!=c->count)return 10+error;
        n=compare();if(n)return 20+n;
    }return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    code=code.replace('ROWS',',\n'.join(rows)).replace('SELECTED',body(candidate,source.NAME)).replace('UNITS',','.join('{%d,%d}'%u for u in UNITS));src=source.OUT/'native.c';src.write_text(code);reports=[]
    for opt in ('-O0','-O2','-O3'):
        exe=source.OUT/('native'+opt);p=subprocess.run([*native_command(opt),'-o',str(exe),str(src)],cwd=source.ROOT,capture_output=True,text=True)
        (source.OUT/('native'+opt+'-diagnostics.txt')).write_text(p.stdout+p.stderr)
        if p.returncode:raise ValueError(p.stderr[-5000:])
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode)
        reports.append(dict(optimization=opt,cases=len(cases),undefined_sanitizer=True,record_bytes_compared=992,model_records=16))
    for label,old,new in (('wrong-life','% 15U','% 16U'),('repeat-sound','if (i == 0)','if (i != 0)'),('wrong-material-stride',' / 12',' / 16')):
        changed=code.replace(old,new);assert changed!=code;src=source.OUT/(label+'.c');src.write_text(changed);exe=src.with_suffix('')
        p=subprocess.run([*native_command('-O2'),'-o',str(exe),str(src)],cwd=source.ROOT,capture_output=True,text=True);assert p.returncode==0,p.stderr
        p=subprocess.run([str(exe)],capture_output=True);assert 0<p.returncode<128,(label,p.returncode)
    reports.append(dict(effective_semantic_controls=3,unwritten_surface_or_fault_claim=False))
    (source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
