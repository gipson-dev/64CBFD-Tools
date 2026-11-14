from pathlib import Path
import sys,json,subprocess,itertools
from tools.tests import game_particle_constructor_15174bf0_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
UNITS=((0x92,2),(0x94,4),(0x98,4),(0x9c,4),(0xa0,4),(0xa4,2),(0xa6,2),*( (a,4) for a in range(0xa8,0xc4,4)),(0xc8,4),(0xe8,4),(0xee,2))
def digest(m):
    data=[m[g.PARTICLES+n*256+i] for n in range(4) for i in range(248)]
    for a in (g.RATE,g.MARK,g.MODELS,g.MODELS+20,g.SCENE):
        value=g.read(m,a)-(g.VIEWS if a==g.SCENE else 0)
        data.extend((value>>shift)&255 for shift in (24,16,8,0))
    data.extend(m[g.KINDS+i] for i in range(4));v=2166136261
    for b in data:v=g.u32((v^b)*16777619)
    return v
def main():
    cases=[]
    for n,fail,flags,mutation,null,alias in itertools.product((-1,0,1,3),(0,1,3),(0,1,0x80000001),(0,1),(False,True),(False,True)):
        cases.append(g.Case(count=n,fail=fail,flags=flags,mutation=mutation,null_surface=null,alias=alias,seed=len(cases)%7))
    for angle,base,spread in itertools.product((-400.,-15.,0.,360.,720.,2147483520.,-2147483648.),(-3.25,-0.,.8),(0.,-.5,2.)):
        cases.append(g.Case(heading=g.bits(angle),base=g.bits(base),spread=g.bits(spread),seed=len(cases)%7,alias=bool(len(cases)&1)))
    rows=[]
    for c in cases:
        want,calls,valid=g.reference(g.fixture(c),c);assert valid
        rows.append('{{%s},0x%Xu,%d,%d,%d,%d,%d,0x%Xu,%d,{%s}}'%(
            ','.join('0x%Xu'%a for a in g.args(c)),c.heading,c.fail,c.null_surface,c.alias,c.mutation,c.seed,digest(want),len(calls),
            ','.join('{0x%Xu,%d,{%s}}'%(t,len(a),','.join('0x%Xu'%v for v in a)) for t,a in calls)))
    candidate=(g.source.OUT/'selected.c').read_text();preamble=candidate[:candidate.index('/* Recovered routine and remaining placeholders')]
    selected=body(candidate,g.source.NAME)
    code=preamble+r'''
_Static_assert(sizeof(Particle15174BF0)==248,"particle ABI");
struct Log {u32 target,count,args[11];};
struct Case {s32 args[9];u32 heading; s32 fail,nullSurface,alias,mutation,seed;u32 digest,count;struct Log log[48];};
static const struct Case cases[]={ROWS};static const struct Case *c;
static Particle15174BF0 particles[4];
struct View {u8 prefix[0x2F8];f32 position[3];u8 suffix[0x9A0-0x304];};
static struct View views[4];static u8 surfaces[12*12];static u32 materials[12];
u8 *D_800DBFF0,*D_800DBE3C;u32 *D_800DBE5C;Model15174BF0 D_800DDE88[2];u8 D_800A7170[4];f32 D_800A7174;
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
        D_800A7174=.125f+callCount*.01f;D_800DBFF0=(u8*)&views+0x1000;
        for(i=0;i<2;i++)D_800DDE88[i].model=(void*)(0x76540000u+callCount*256+i);
        for(i=0;i<4;i++)particles[i].flags=0x8010+callCount;
        for(i=0;i<4;i++)D_800A7170[i]=(u8)(callCount*17+i);
    }
}
f32 func_15048FC8(struct17 *v){u32 a[]={word(v->unk0),word(v->unk4),word(v->unk8)};record(0x15048FC8,3,a);return real(c->heading);}
void *func_15167A68(s32 a0,s32 a1,s32 a2,s32 a3,u8 a4,u8 a5){u32 a[]={a0,a1,a2,a3,a4,a5};record(0x15167A68,6,a);allocationCount++;return allocationCount>(u32)c->fail ? 0 : &particles[c->alias?0:allocationCount-1];}
u32 func_150ADA20(void){record(0x150ADA20,0,0);randomCount++;return randomWord(randomCount);}
u16 func_10010E78(s32 a0,s32 a1,s32 a2,s32 a3,s32 a4,s32 a5,s32 a6,s32 a7,s32 a8,s32 a9,s32 a10){u32 a[]={a0,a1,a2,a3,a4,a5,a6,a7,a8,a9,a10};record(0x10010E78,11,a);return 0x8001;}
s32 func_1510F8D8(s32 a0,s32 a1,s32 a2,u8 **out){u32 a[]={a0,a1,a2};record(0x1510F8D8,3,a);*out=c->nullSurface?0:D_800DBE3C+12*((s32)allocationCount-2);return -7-(s32)allocationCount;}
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
    hashWord(&h,word(D_800A7174));hashWord(&h,mark);for(i=0;i<2;i++)hashWord(&h,(u32)D_800DDE88[i].model);
    hashWord(&h,(u32)D_800DBFF0-(u32)&views);for(i=0;i<4;i++)hashByte(&h,D_800A7170[i]);return h;
}
static u32 run(void){
    u32 k,n,i,j,at,size;u8 *p,tmp;
    for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){
        c=&cases[k];callCount=randomCount=allocationCount=error=mark=0;
        for(n=0;n<4;n++){
            p=(u8*)&particles[n];for(i=0;i<248;i++)p[i]=(u8)(i*29+c->seed*11+n+0x59);
            for(j=0;j<sizeof(units)/sizeof(units[0]);j++){at=units[j][0];size=units[j][1];for(i=0;i<size/2;i++){tmp=p[at+i];p[at+i]=p[at+size-1-i];p[at+size-1-i]=tmp;}}
        }
        D_800DBFF0=(u8*)&views;views[c->args[5]].position[0]=2.5f;views[c->args[5]].position[1]=-3.25f;views[c->args[5]].position[2]=7.75f;
        D_800A7174=.01f;D_800DBE3C=surfaces+4*12;D_800DBE5C=materials+4;
        for(i=0;i<12;i++)materials[i]=(((i-4)*0x23456789u)^0xABCDEF00u)|((c->seed&3)<<5);
        for(i=0;i<2;i++)D_800DDE88[i].model=(void*)(0x98765430u+i*0x1234);
        D_800A7170[0]=0;D_800A7170[1]=42;D_800A7170[2]=84;D_800A7170[3]=127;
        func_15174BF0(c->args[0],c->args[1],c->args[2],c->args[3],c->args[4],c->args[5],real((u32)c->args[6]),real((u32)c->args[7]),c->args[8]);
        if(error||callCount!=c->count||digest()!=c->digest)return 10+error;
    }return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    code=code.replace('ROWS',',\n'.join(rows)).replace('SELECTED',selected).replace('UNITS',','.join('{%d,%d}'%u for u in UNITS))
    src=g.source.OUT/'native.c';src.write_text(code);reports=[]
    for opt in ('-O0','-O2','-O3'):
        exe=g.source.OUT/('native'+opt);p=subprocess.run([*native_command(opt),'-o',str(exe),str(src)],cwd=g.source.ROOT,capture_output=True,text=True)
        (g.source.OUT/('native'+opt+'-diagnostics.txt')).write_text(p.stdout+p.stderr)
        if p.returncode:raise ValueError(p.stderr[-5000:])
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode)
        reports.append(dict(optimization=opt,cases=len(cases),undefined_sanitizer=True))
    for label,old,new in (('wrong-life','% 15U','% 16U'),('repeat-sound','if (i == 0)','if (i != 0)'),('wrong-material-stride',' / 12',' / 16')):
        changed=code.replace(old,new);assert changed!=code;src=g.source.OUT/(label+'.c');src.write_text(changed);exe=src.with_suffix('')
        p=subprocess.run([*native_command('-O2'),'-o',str(exe),str(src)],cwd=g.source.ROOT,capture_output=True,text=True);assert p.returncode==0,p.stderr
        p=subprocess.run([str(exe)],capture_output=True);assert 0<p.returncode<128,(label,p.returncode)
    reports.append(dict(effective_semantic_controls=3));(g.source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
