"""Native32 recovery, live RNG inputs and six effective source controls."""
import json,math,struct,subprocess
from tools.tests import game_particle_common_15175958_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def main():
    arr=lambda xs:'{'+','.join('0x%Xu'%g.u32(x)for x in xs)+'}'
    rows=[];rom=(g.ROOT/'conker/conker.us.bin').read_bytes();retail=list(struct.unpack_from('>961I',rom,0x1a2e08))
    for c in g.cases():
        if c.variant>10 or not all(math.isfinite(v)for v in(c.tilt,c.heading,c.bank,c.rate)):continue
        initial=g.fixture(c);m=g.Oracle(retail,initial,c);m.run();want=m.memory;packets=[]
        for (t,args),snapshot in zip(m.calls,m.observed):
            if t==g.ANGLE:args=args[1:]
            if t==g.FLOOR:args=args[:3]
            assert len(args)<=10
            packets.append('{0x%Xu,%d,%s,%s}'%(t,len(args),arr((*args,*([0]*(10-len(args))))),arr(snapshot)))
        assert len(packets)<=16
        vectors=([initial[g.P+i]for i in range(248)],[want[g.P+i]for i in range(248)],
                 [g.read(initial,g.base.MODELS+i*4)for i in range(55)],
                 [g.read(initial,g.base.CONTROL+i*4)for i in range(11)],
                 [initial[g.CONFIG+i]for i in range(11*56)],
                 *([x[base+i]for i in range(n)]for x in(initial,want)for base,n in((g.base.LIVE,12),(g.base.ACTIVE,16))))
        scalars=(g.read(initial,g.base.STEP),g.read(want,g.base.STEP),g.read(initial,0x800be9f0),g.read(initial,0x800c35b0),g.read(initial,0x800d2138),want[0x800c35ea],g.read(want,g.base.MARK))
        rows.append('{%d,%d,0x%Xu,0x%Xu,0x%Xu,%d,%d,'%(c.mode,c.seed,g.u32(c.distance),g.u32(c.angle),c.random,c.flags,c.late_divisor)+','.join(arr(x)for x in vectors)+','+','.join('0x%Xu'%x for x in scalars)+',%d,{'%len(packets)+','.join(packets)+'}}')
    owner=(g.OUT/'selected.c').read_text();code=owner[:owner.index('/* Recovered routine and remaining placeholders')]
    code+=r'''
_Static_assert(sizeof(Particle15175390)==248,"particle ABI");
_Static_assert(sizeof(ParticleConfig15175958)==56,"config ABI");
typedef union{u32 u;f32 f;}Bits;
static f32 real(u32 u){Bits b;b.u=u;return b.f;}
static u32 word(f32 f){Bits b;b.f=f;return b.u;}
struct Packet{u32 target,count,args[10];u8 record[248];};
struct Case{u32 mode,seed,distance,angle,random,flags;s32 lateDivisor;u8 initial[248],expected[248];u32 models[55],controls[11];u8 config[616],live[12],active[16],lastLive[12],lastActive[16];u32 step,lastStep,scene,timer,players,lastGate,mark,count;struct Packet packets[16];};
static const struct Case cases[]={ROWS};static const struct Case*c;
static Particle15175390 record;
Gfx*D_800DDE80[55];s32 D_800DDF78[11],D_800BE9E4;
u8 particleFlags[28];
__asm__(".globl D_800DDF5C\n.set D_800DDF5C,particleFlags\n.globl D_800DDF60\n.set D_800DDF60,particleFlags+4\n.globl D_800DDF68\n.set D_800DDF68,particleFlags+12");
VertexWave1517725C D_8008D0B0[11];
s32 D_800BE9F0,D_800C35B0,D_800D2138;
u8 D_800C35EA,D_800C35E8,D_800D9C10[64],D_800D9C50[64];
f32 D_800D9B20,D_800D9B1C,D_800D35E0,D_800D35E4;
CONSTANT_DEFS
static u8 surfaces[128];static u32 attributes[32];u8*D_800DBE3C;u32*D_800DBE5C;
static u32 calls,error,mark,caseIndex,debug[6];
static u32 indexByte(u32 i){
if((i>=0x92&&i<0x94)||(i>=0xa4&&i<0xa8)||(i>=0xd0&&i<0xe0)||(i>=0xee&&i<0xf0))return i^1u;
if((i>=0x94&&i<0xa4)||(i>=0xa8&&i<0xd0)||(i>=0xe0&&i<0xec))return i^3u;
return i;}
static u32 notify(u32 target,u32 count,const u32*a){u32 n=calls++,i,v;const struct Packet*p;
if(n>=c->count||n>=16)error=1;else{p=c->packets+n;if(p->target!=target||p->count!=count)error=2;
for(i=0;i<count;i++){v=a[i];if(target==0x1516972c&&v==(u32)&record)v=0x50000;
if(target==0x1510aee0&&i==0){if(v==(u32)D_800D9C10)v=0x800d9c10;if(v==(u32)D_800D9C50)v=0x800d9c50;}
if(v!=p->args[i]){error=3;debug[0]=target;debug[1]=n;debug[2]=i;debug[3]=v;debug[4]=p->args[i];}}
for(i=0;i<248;i++)if(((u8*)&record)[indexByte(i)]!=p->record[i])error=4;}
n++;if(c->mode&1){record.tilt=3.f+n;record.heading=20.f+n;record.angularRate=-2.f+n;record.fieldBC=100.f+n;
record.position[0]=10.f+n;record.position[1]=70.f+n;record.position[2]=-20.f-n;record.fieldE0=50.f+n;record.targetHeight=60.f+n;
record.slot=(c->seed+n)%12;record.variant=(c->seed+n)%4;record.state91=(c->seed+n)%4;}
if(c->mode&2){D_800BE9E4=n+1;D_800C35EA=(n&1)?0:1;}
if(c->mode&4)record.flags=(s16)(c->flags^(n&7));
if(target==0x150ada20&&(c->mode&8))record.verticalRange=(s16)c->lateDivisor;
mark=target^n;
if(target==0x150484a0||target==0x150ad78c||target==0x150ad780)return word(((n+c->seed)&1)?0.5f:-0.25f);
if(target==0x150ada20)return c->random+n*19u;
if(target==0x150ad960)return c->distance;
if(target==0x150490a8)return c->angle;
if(target==0x1000f3d0)return c->seed&1;
if(target==0x1510aee0)return(c->seed+n)&1;
if(target==0x1510f8d8)return 5;return 0;}
void func_1516972C(void*p){u32 a[]={(u32)p};notify(0x1516972c,1,a);}
s32 func_150ADA20(void){u32 a[1]={0};return(s32)notify(0x150ada20,0,a);}
s32 func_150AD960(s32 a,s32 b,s32 d,s32 e){u32 x[]={a,b,d,e};return(s32)notify(0x150ad960,4,x);}
s32 func_150490A8(struct17*p){u32 a[]={word(p->unk0),word(p->unk8)};return(s32)notify(0x150490a8,2,a);}
s32 func_1000F3D0(s32 a){u32 x[]={a};return(s32)notify(0x1000f3d0,1,x);}
void func_1000F91C(s32 a,s32 b,s32 d,s32 e,s32 f,s32 h,s32 i,s32 j,s32 k,s32 l){u32 x[]={a,b,d,e,f,h,i,j,k,l};notify(0x1000f91c,10,x);}
void func_10010F88(s32 a,s32 b,s16 d,s32 e,s32 f,s32 h,s32 i,s32 j,s32 k,s32 l){u32 x[]={a,b,(s32)d,e,f,h,i,j,k,l};notify(0x10010f88,10,x);}
s32 func_1510F8D8(s32 x,s32 y,s32 z,u8**out){u32 a[]={x,y,z};*out=(c->seed&1)?surfaces+12*(c->seed%5):0;return(s32)notify(0x1510f8d8,3,a);}
f32 func_150484A0(f32 x,f32 y){u32 a[]={word(x),word(y)};return real(notify(0x150484a0,2,a));}
f32 func_150AD78C(f32 x){u32 a[]={word(x)};return real(notify(0x150ad78c,1,a));}
f32 func_150AD780(f32 x){u32 a[]={word(x)};return real(notify(0x150ad780,1,a));}
s32 func_1510AEE0(void*p,f32 a,f32 b,f32 d,f32 e,f32 f,f32 h,f32 i,f32*j,f32*k){u32 x[]={(u32)p,word(a),word(b),word(d),word(e),word(f),word(h),word(i),(u32)j,(u32)k};return(s32)notify(0x1510aee0,10,x);}
f32 sqrtf(f32 x){f32 v;__asm__("sqrtss %1,%0":"=x"(v):"x"(x));return v;}
f32 fabsf(f32 x){return real(word(x)&0x7fffffffu);}
CANDIDATE
static u32 run(void){u32 i,k;
for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){c=cases+k;caseIndex=k;calls=error=mark=0;
for(i=0;i<248;i++)((u8*)&record)[indexByte(i)]=c->initial[i];
for(i=0;i<55;i++)D_800DDE80[i]=(Gfx*)c->models[i];
for(i=0;i<11;i++)D_800DDF78[i]=(s32)c->controls[i];
for(i=0;i<616;i++)((u8*)D_8008D0B0)[i%56<4?i:i^3u]=c->config[i];
for(i=0;i<12;i++)D_800DDF5C[i]=c->live[i];for(i=0;i<16;i++)D_800DDF68[i]=c->active[i];
D_800BE9E4=(s32)c->step;D_800BE9F0=(s32)c->scene;D_800C35B0=(s32)c->timer;D_800D2138=(s32)c->players;D_800C35EA=1;D_800C35E8=15;
D_800D9B20=D_800D9B1C=D_800D35E0=D_800D35E4=0.f;
CONSTANT_INIT
D_800DBE3C=surfaces;D_800DBE5C=attributes;for(i=0;i<32;i++)attributes[i]=i^0x12345678u;
func_15175958(&record);
if(error||calls!=c->count||mark!=c->mark||(u32)D_800BE9E4!=c->lastStep||D_800C35EA!=c->lastGate)return 10+error;
for(i=0;i<248;i++)if(((u8*)&record)[indexByte(i)]!=c->expected[i])return 20;
for(i=0;i<12;i++)if(D_800DDF5C[i]!=c->lastLive[i])return 21;for(i=0;i<16;i++)if(D_800DDF68[i]!=c->lastActive[i])return 22;
for(i=0;i<55;i++)if((u32)D_800DDE80[i]!=c->models[i])return 23;
for(i=0;i<11;i++)if((u32)D_800DDF78[i]!=c->controls[i])return 24;
for(i=0;i<616;i++)if(((u8*)D_8008D0B0)[i%56<4?i:i^3u]!=c->config[i])return 25;
}return 0;}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();if(status){u32 info[]={caseIndex,status,calls,error,debug[0],debug[1],debug[2],debug[3],debug[4]};__asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(info),"d"(sizeof(info)):"memory");}__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    constants=[(addr,w)for addr,w in g.CONSTANTS if 0x800a717c<=addr<=0x800a71a8]
    code=code.replace('CONSTANT_DEFS','\n'.join('f32 D_%08X;'%a for a,w in constants)).replace('CONSTANT_INIT','\n'.join('D_%08X=real(0x%Xu);'%(a,w)for a,w in constants))
    body=g.source.SELECTED
    controls=[body.replace('D_800DDF68[record->variant] = 1','D_800DDF68[record->variant] = 2'),
              body.replace('alpha = (s32)((u32)alpha -','alpha = (s32)((u32)alpha +'),
              body.replace('record->lifetime = config->minimumSpeed;','record->lifetime = config->minimumSpeed + 1;'),
              body.replace('D_800DDF60[record->slot] = soundRandom + 30','D_800DDF60[record->slot] = soundRandom + 31'),
              body.replace('value += 4294967296.0f','value += 2147483648.0f')]
    legacy=body.replace('        soundRandom = func_150ADA20() & 127;\n','').replace('(s16)soundRandom','(s16)(func_150ADA20() & 127)')
    controls.append(legacy);assert all(x!=body for x in controls)
    code=code.replace('ROWS',',\n'.join(rows)).replace('CANDIDATE','\n'.join(x.replace('func_15175958','candidate_'+str(i))for i,x in enumerate((body,*controls))))
    decl='static void(*tests[])(Particle15175390*)={'+','.join('candidate_'+str(i)for i in range(7))+'};\n'
    code=code.replace('static u32 run(void){u32 i,k;\nfor(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){',decl+'static u32 check(u32 k,u32 t){u32 i;\n{').replace('func_15175958(&record);','tests[t](&record);')
    needle='__attribute__((force_align_arg_pointer)) void _start'
    runner='static u32 run(void){u32 k,t,status,killed;for(t=0;t<7;t++){killed=0;for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){status=check(k,t);if(!t&&status)return status;if(t&&status){killed=1;break;}}if(t&&!killed)return 31+t;}return 0;}\n'
    code=code.replace(needle,runner+needle)

    src=g.OUT/'native-common.c';src.write_text(code);reports=[]
    for opt in('-O0','-O2','-O3'):
        exe=g.OUT/('native-common'+opt);q=subprocess.run([*native_command(opt),'-o',str(exe),str(src)],cwd=g.ROOT,capture_output=True,text=True)
        (g.OUT/('native-common'+opt+'-diagnostics.txt')).write_text(q.stdout+q.stderr)
        if q.returncode:raise ValueError(q.stderr[-6000:])
        q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,q.returncode,list(map(hex,struct.unpack('<%dI'%(len(q.stdout)//4),q.stdout))))
        reports.append(dict(optimization=opt,cases=len(rows),undefined_sanitizer=True,record_bytes=248,config_bytes=616,providers='bounded',late_slot_and_divisor=True,effective_controls=6,sequencing_control_killed=True,private=True))
    (g.OUT/'native-common-report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
