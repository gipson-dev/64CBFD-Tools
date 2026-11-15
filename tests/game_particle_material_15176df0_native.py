"""Native32 records, palettes, matrices and captured shade across the material call."""
import itertools,json,subprocess
from tools.tests import game_particle_material_15176df0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def main():
    source=g.source;cases=[];relations=((0,0),(0,255),(1,42),(40,84),(84,42),(127,127),(255,1),(255,255))
    for present,enabled,relation,step,mode in itertools.product((0,1),(0,1),relations,(0,1,17,-1,0x3fffffff,0x40000000,0x80000000),(0,1)):
        k=len(cases);cases.append(g.Case(variant=k%4,present=present,enabled=enabled,current=relation[0],target=relation[1],step=step,scale=(0,0x80000000,0xbf800000,0x3f000000,0x7f7fffff)[k%5],page=k&1,mutation=mode,seed=k%17))
    cases.extend(g.Case(variant=i%4,current=i,target=255-i,step=11,seed=i) for i in range(256))
    arr=lambda xs:'{'+','.join('0x%Xu'%g.u32(x) for x in xs)+'}'
    rows=[]
    for c in cases:
        initial=g.fixture(c);want,calls,obs,result=g.reference(initial,c);assert len(calls)<=5
        packets=['{0x%Xu,%d,%s,%s}'%(t,len(a),arr((*a,*([0]*(4-len(a))))),arr((*o,*([0]*(32-len(o)))))) for (t,a),o in zip(calls,obs)]
        vectors=([initial[g.RECORD+i] for i in range(248)],[want[g.RECORD+i] for i in range(248)], [initial[g.KINDS+i] for i in range(4)],[want[g.KINDS+i] for i in range(4)], [g.read(initial,g.MODELS+i*20) for i in range(4)],[g.read(initial,g.LISTS+i*20) for i in range(4)],[g.read(initial,g.CONTROL+i*4) for i in range(4)],[g.read(want,g.MODELS+i*20) for i in range(4)],[g.read(want,g.LISTS+i*20) for i in range(4)])
        values=(g.read(initial,g.STEP),g.read(want,g.STEP),c.page,want[g.PAGE],g.read(want,g.MARK),result,len(calls))
        rows.append('{%d,%d,%d,'%(c.seed,c.mutation,c.view)+','.join(arr(v) for v in vectors)+','+','.join('0x%Xu'%v for v in values)+','+arr(g.read(want,g.COMMANDS+i*4) for i in range(64))+',{'+','.join(packets)+'}}')
    owner=(source.OUT/'selected.c').read_text();preamble=owner[:owner.index('/* Recovered routine and remaining placeholders')]
    code=preamble+r'''
_Static_assert(sizeof(Particle15175390)==248,"particle ABI");
typedef union{u32 u;f32 f;}Bits;
struct Packet{u32 target,count,args[4],snapshot[32];};
struct Case{u32 seed,mutation,view;u8 initial[248],expected[248],firstKinds[4],lastKinds[4];u32 firstModels[4],firstLists[4],controls[4],lastModels[4],lastLists[4],firstStep,lastStep,firstPage,lastPage,mark,result,count,commands[64];struct Packet packets[5];};
static const struct Case cases[]={ROWS};static const struct Case*c;
static Particle15175390 record;static Gfx commands[32];
Gfx *D_800DDE80[55],*D_800DDE8C[55];s32 D_800DDF78[4],D_800BE9E4;u8 D_800A7170[4],D_800BE9C0;
static u32 calls,error,mark;static f32(*firstMatrix)[4],(*secondMatrix)[4];static u8*syncPointer;
static f32 real(u32 u){Bits b;b.u=u;return b.f;}static u32 word(f32 f){Bits b;b.f=f;return b.u;}
static u32 canon(u32 v){u32 p=(u32)&record;if(v>=p&&v<p+248)return 0x50000u+v-p;
p=(u32)commands;if(v>=p&&v<p+256)return 0x60000u+v-p;
if(firstMatrix&&v==(u32)firstMatrix)return FIRST;
if(secondMatrix&&v==(u32)secondMatrix)return SECOND;
if(syncPointer&&v==(u32)syncPointer)return 0x72000;return v;}
static u32 indexByte(u32 i){return (i>=0x94&&i<0xa4)||(i>=0xa8&&i<0xb4)||(i>=0xc0&&i<0xc4)||(i>=0xe8&&i<0xec)?i^3u:i;}
static void notify(u32 t,u32 count,const u32*a){u32 n=calls++,i,j,left[16],right[16];const struct Packet*p;
if(t==0x150a8050){if(!n)firstMatrix=(f32(*)[4])a[0];else secondMatrix=(f32(*)[4])a[0];}
if(t==0x15142fbc)syncPointer=(u8*)a[3];
if(n>=c->count||n>=5)error=1;else{p=c->packets+n;if(p->target!=t||p->count!=count)error=2;
for(i=0;i<count;i++)if(p->args[i]!=canon(a[i]))error=3;
if(t==0x150a7a48)for(j=0;j<2;j++)for(i=0;i<16;i++)if(p->snapshot[j*16+i]!=word(((f32(*)[4])a[j])[i/4][i%4]))error=4;
if(t==0x150a7790)for(i=0;i<16;i++)if(p->snapshot[i]!=word(((f32(*)[4])a[0])[i/4][i%4]))error=5;
if(t==0x15142fbc&&*syncPointer!=0)error=6;}
n++;mark=t^n*0x1020304u;
if(t==0x150a8050)for(i=0;i<16;i++)((f32(*)[4])a[0])[i/4][i%4]=real(0x3e800000u|((a[1+i%3]+i*0x1111u+n*256)&0x7fffffu));
else if(t==0x150a7a48){
for(i=0;i<16;i++){left[i]=word(((f32(*)[4])a[0])[i/4][i%4]);right[i]=word(((f32(*)[4])a[1])[i/4][i%4]);}
for(i=0;i<16;i++)((f32(*)[4])a[2])[i/4][i%4]=real(0x3e000000u|((left[i]^right[(i+5)%16])&0x7fffffu));}
else if(t==0x150a7790)for(i=0;i<64;i++)((u8*)a[1])[i]=(u8)(i*7+n*3+c->seed);
else if(t==0x15142fbc){Gfx*p=(Gfx*)a[0];p->words.w0=0xf1000000u|n;p->words.w1=0x12340000u|n;*syncPointer=0x5a;}
if(c->mutation&1){D_800BE9C0^=1;record.variant=(c->seed+n)%4;record.surfaceKind=(c->seed+n*17)&255;record.stateF0=(c->seed+n*31)&255;record.state91=1+(c->seed+n)%3;
for(i=0;i<3;i++)record.position[i]=real(0x3f800000u+(n*8+i)*0x10000u);
record.tilt=real(0x3f800000u+(n*8+3)*0x10000u);record.heading=real(0x3f800000u+(n*8+4)*0x10000u);record.fieldB0=real(0x3f800000u+(n*8+5)*0x10000u);
record.model=(void*)(0x84560000u+n);record.scale=real((u32[]){0xbf000000,0x3e800000,0x40000000}[n%3]);record.surfaceFlags=(n&3)<<5;
for(i=0;i<4;i++){D_800DDE80[i*5]=(Gfx*)(0x85670000u+n*256+i);D_800DDE8C[i*5]=(Gfx*)(0x86780000u+n*256+i);D_800A7170[i]=(n*17+i*31)&255;}D_800BE9E4=n+1;}
}
void func_150A8050(f32 m[4][4],f32 x,f32 y,f32 z){u32 a[]={(u32)m,word(x),word(y),word(z)};notify(0x150a8050,4,a);}
void func_150A7A48(f32 l[4][4],f32 r[4][4],f32 out[4][4]){u32 a[]={(u32)l,(u32)r,(u32)out};notify(0x150a7a48,3,a);}
void guMtxF2L(f32 m[4][4],Mtx*p){u32 a[]={(u32)m,(u32)p};notify(0x150a7790,2,a);}
Gfx*func_15142FBC(Gfx*p,u32 mode,u32 kind,u8*sync){u32 a[]={(u32)p,mode,kind,(u32)sync};notify(0x15142fbc,4,a);return (Gfx*)((u8*)p+8*(1+c->seed%2));}
CANDIDATES
static Gfx*(*tests[])(Gfx*,Particle15175390*,s16)={TESTS};
static u32 run(void){u32 k,t,i,failed,killed=0;Gfx*answer;
for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){c=cases+k;for(t=0;t<6;t++){
calls=error=mark=0;firstMatrix=secondMatrix=0;syncPointer=0;
for(i=0;i<248;i++)((u8*)&record)[indexByte(i)]=c->initial[i];
for(i=0;i<64;i++)((u32*)commands)[i]=0xa5a5a5a5u;
for(i=0;i<55;i++)D_800DDE80[i]=D_800DDE8C[i]=(Gfx*)0x5a5a5a5au;
for(i=0;i<4;i++){D_800DDE80[i*5]=(Gfx*)c->firstModels[i];D_800DDE8C[i*5]=(Gfx*)c->firstLists[i];D_800DDF78[i]=(s32)c->controls[i];D_800A7170[i]=c->firstKinds[i];}
D_800BE9C0=c->firstPage;D_800BE9E4=(s32)c->firstStep;
answer=tests[t](commands,&record,(s16)c->view);failed=error||calls!=c->count||canon((u32)answer)!=c->result||D_800BE9C0!=c->lastPage||(u32)D_800BE9E4!=c->lastStep||mark!=c->mark;
for(i=0;i<248;i++)if(((u8*)&record)[indexByte(i)]!=c->expected[i])failed=1;
for(i=0;i<4;i++)if(D_800A7170[i]!=c->lastKinds[i]||(u32)D_800DDE80[i*5]!=c->lastModels[i]||(u32)D_800DDE8C[i*5]!=c->lastLists[i])failed=1;
for(i=0;i<64;i++)if(canon(((u32*)commands)[i])!=c->commands[i])failed=1;
if(!t&&failed)return 10+error;if(t&&failed)killed|=1u<<(t-1);
}}return killed==31?0:30;}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    body=source.SELECTED;controls=(body.replace('if (value < 0) { value = 0; }','if (value < target) { value = target; }'),body.replace('matrix[2][2] *= record->scale;','matrix[2][2] *= 1.0f;'),body.replace('func_150A7A48(tilt, matrix, matrix);','func_150A7A48(matrix, tilt, matrix);'),body.replace('record->stateF0','record->variant'),body.replace('D_800DDE8C[record->variant * 5]','D_800DDE8C[record->variant * 4]'))
    assert all(x!=body for x in controls)
    code=code.replace('ROWS',',\n'.join(rows)).replace('FIRST','0x%Xu'%g.matrices(g.home(g.Case()))[0]).replace('SECOND','0x%Xu'%g.matrices(g.home(g.Case()))[1]).replace('CANDIDATES','\n'.join(s.replace(source.NAME,'candidate_'+str(i)) for i,s in enumerate((body,*controls)))).replace('TESTS',','.join('candidate_'+str(i) for i in range(6)))
    src=source.OUT/'native.c';src.write_text(code);reports=[]
    for opt in ('-O0','-O2','-O3'):
        exe=source.OUT/('native'+opt);p=subprocess.run([*native_command(opt),'-o',str(exe),str(src)],cwd=source.ROOT,capture_output=True,text=True);(source.OUT/('native'+opt+'-diagnostics.txt')).write_text(p.stdout+p.stderr)
        if p.returncode:raise ValueError(p.stderr[-5000:])
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode)
        reports.append(dict(optimization=opt,cases=len(cases),undefined_sanitizer=True,record_bytes=248,command_bytes=256,matrix_snapshots=True,effective_controls=5))
    (source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
