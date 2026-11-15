"""Native32 state, packets and explicit two-stage unsigned height rounding."""
import json,subprocess
from tools.tests import game_particle_state_15176b84_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def main():
    rows=[];cases=[];arr=lambda xs:'{'+','.join('0x%Xu'%g.u32(x)for x in xs)+'}'
    for c in g.cases():
        if c.alias or c.variant>10 or c.slot>11:continue
        initial=g.fixture(c);want,calls,obs,zero=g.reference(initial,c)
        if zero:continue
        p=g.address(c);cases.append(c)
        vectors=([initial[p+i]for i in range(248)],[want[p+i]for i in range(248)],[g.read(initial,g.MODELS+i*4)for i in range(55)],[g.read(want,g.MODELS+i*4)for i in range(55)],*[([m[base+i]for i in range(n)])for m in(initial,want)for base,n in((g.LIVE,12),(g.ACTIVE,16))],[g.read(initial,g.CONTROL+i*4)for i in range(11)],[g.read(want,g.CONTROL+i*4)for i in range(11)])
        packets=['{0x%Xu,%d,%s,%s}'%(t,len(a),arr((*a,*([0]*(4-len(a))))),arr(o))for(t,a),o in zip(calls,obs)]
        vals=(g.read(initial,g.STEP),g.read(want,g.STEP),g.read(want,g.MARK))
        rows.append('{%d,%d,0x%Xu,0x%Xu,%d,'%(c.mode,c.seed,g.u32(c.distance),g.u32(c.random),c.late_divisor)+','.join(arr(v)for v in vectors)+','+','.join('0x%Xu'%v for v in vals)+',%d,{'%len(calls)+','.join(packets)+'}}')
    owner=(g.source.OUT/'selected.c').read_text();preamble=owner[:owner.index('/* Recovered routine and remaining placeholders')]
    code=preamble+r'''
_Static_assert(sizeof(Particle15175390)==248,"particle ABI");
_Static_assert(sizeof(Model15174BF0)==20,"model ABI");
typedef union{u32 u;f32 f;}Bits;
struct Packet{u32 target,count,args[4];u8 record[248];};
struct Case{u32 mode,seed,distance,random;s32 divisor;u8 initial[248],expected[248];u32 models[55],lastModels[55];u8 live[12],active[16],lastLive[12],lastActive[16];u32 controls[11],lastControls[11],step,lastStep,mark,count;struct Packet packets[2];};
static const struct Case cases[]={ROWS};static const struct Case*c;
static Particle15175390 record;Gfx*D_800DDE80[55];Model15174BF0 D_800DDE84[11],D_800DDE88[11];
s32 D_800DDF78[11],D_800BE9E4;u8 D_800DDF5C[12],D_800DDF68[16];ActorPosition15176B84 D_800CC2D0;
static u32 calls,error,mark;
static f32 real(u32 u){Bits b;b.u=u;return b.f;}
static u32 indexByte(u32 i){return(i>=0x94&&i<0xa4)||(i>=0xa8&&i<0xc4)||(i>=0xc8&&i<0xd0)||(i>=0xe0&&i<0xec)?i^3u:(i>=0xd0&&i<0xe0)?i^1u:i;}
static void tableWord(u32 addr,u32 value){u32 i,j;
/* These bounded projections reproduce the guest overlap of sparse helper
   writes while each native C object stays inside its declared bounds. */
if(addr>=0x800dde80&&addr+4<=0x800ddf5c){i=(addr-0x800dde80)/4;D_800DDE80[i]=(Gfx*)value;
if(i%5==1)D_800DDE84[i/5].model=(void*)value;if(i%5==2)D_800DDE88[i/5].model=(void*)value;}
if(addr>=0x800ddf5c&&addr+4<=0x800ddf68)for(j=0;j<4;j++)D_800DDF5C[addr-0x800ddf5c+j]=(u8)(value>>(24-j*8));
if(addr>=0x800ddf68&&addr+4<=0x800ddf78)for(j=0;j<4;j++)D_800DDF68[addr-0x800ddf68+j]=(u8)(value>>(24-j*8));
if(addr>=0x800ddf78&&addr+4<=0x800ddfa4)D_800DDF78[(addr-0x800ddf78)/4]=(s32)value;
}
static u32 notify(u32 target,u32 count,const u32*a){u32 n=calls++,i,v;const struct Packet*p;
if(n>=c->count||n>=2)error=1;else{p=c->packets+n;if(p->target!=target||p->count!=count)error=2;
for(i=0;i<count;i++){v=a[i];if(target!=0x150ad960&&v==(u32)&record)v=0x50000;if(v!=p->args[i])error=3;}
for(i=0;i<248;i++)if(((u8*)&record)[indexByte(i)]!=p->record[i])error=4;}
n++;mark=target^n*0x1020304u;
if((target==0x150ad960&&(c->mode&1))||(target==0x150ada20&&(c->mode&2))){
record.variant=(c->seed+n)%4;record.slot=(c->seed+n)%12;record.state91=(c->seed+n)%6;
record.sourceY=-7+(s32)n;record.verticalRange=(s16)c->divisor;
record.position[0]=10.f+n;record.position[2]=-20.f-n;record.position[1]=3.f+n;record.groundHeight=1.f+n;}
if((target==0x1516972c||target==0x15175958)&&(c->mode&4)){record.state91=0x75;record.fieldB4=real(0x86780000u+n);}
if(c->mode&8){for(i=0;i<256;i++){tableWord(0x800dde84+i*20,0x85670000u+n*256+i);tableWord(0x800dde88+i*20,0x86780000u+n*256+i);}D_800BE9E4=(s32)n+1;}
return target==0x150ada20?c->random:target==0x150ad960?c->distance:0x87654321;
}
s32 func_150AD960(s32 a,s32 b,s32 d,s32 e){u32 args[]={(u32)a,(u32)b,(u32)d,(u32)e};return(s32)notify(0x150ad960,4,args);}
s32 func_150ADA20(void){u32 args[4]={0};return(s32)notify(0x150ada20,0,args);}
void func_1516972C(void*p){u32 args[]={(u32)p};notify(0x1516972c,1,args);}
s32 func_15175958(void*p){u32 args[]={(u32)p};return(s32)notify(0x15175958,1,args);}
CANDIDATES
static void(*tests[])(Particle15175390*)={TESTS};
static u32 run(void){u32 k,t,i,failed,killed=0;
for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){c=cases+k;for(t=0;t<6;t++){
calls=error=mark=0;for(i=0;i<248;i++)((u8*)&record)[indexByte(i)]=c->initial[i];
for(i=0;i<55;i++)D_800DDE80[i]=(Gfx*)c->models[i];
for(i=0;i<11;i++){D_800DDE84[i].model=(void*)c->models[i*5+1];D_800DDE88[i].model=(void*)c->models[i*5+2];D_800DDF78[i]=(s32)c->controls[i];}
for(i=0;i<12;i++)D_800DDF5C[i]=c->live[i];for(i=0;i<16;i++)D_800DDF68[i]=c->active[i];D_800BE9E4=(s32)c->step;
D_800CC2D0.x=-123.75f;D_800CC2D0.z=234.5f;tests[t](&record);
failed=error||calls!=c->count||mark!=c->mark||(u32)D_800BE9E4!=c->lastStep;
for(i=0;i<248;i++)if(((u8*)&record)[indexByte(i)]!=c->expected[i])failed=1;
for(i=0;i<55;i++)if((u32)D_800DDE80[i]!=c->lastModels[i])failed=1;
for(i=0;i<11;i++)if((u32)D_800DDE84[i].model!=c->lastModels[i*5+1]||(u32)D_800DDE88[i].model!=c->lastModels[i*5+2]||(u32)D_800DDF78[i]!=c->lastControls[i])failed=1;
for(i=0;i<12;i++)if(D_800DDF5C[i]!=c->lastLive[i])failed=1;for(i=0;i<16;i++)if(D_800DDF68[i]!=c->lastActive[i])failed=1;
if(!t&&failed)return 10+error;if(t&&failed)killed|=1u<<(t-1);
}}return killed==31?0:30;}
__attribute__((force_align_arg_pointer)) void _start(void){u32 status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    body=g.source.SELECTED;block='remainder = (u32)func_150ADA20() % (u32)record->verticalRange;\n                height = (s32)remainder;\n                if ((s32)remainder < 0) { height += 4294967296.0f; }\n                record->targetHeight = height + record->sourceY;'
    implicit=body.replace('    u32 remainder;\n','').replace('    f32 height;\n','').replace(block,'record->targetHeight = (f32)((u32)func_150ADA20() % (u32)record->verticalRange) + record->sourceY;')
    controls=(implicit,body.replace('position[2]) < 200','position[2]) <= 200'),body.replace('D_800DDF68[record->variant] = 1','D_800DDF68[record->variant] = 2'),body.replace('opacity = (u32)opacity -','opacity = (u32)opacity +'),body.replace('D_800DDE84[record->variant].model','D_800DDE88[record->variant].model'))
    assert block in body and all(x!=body for x in controls)
    code=code.replace('ROWS',',\n'.join(rows)).replace('CANDIDATES','\n'.join(s.replace(g.source.NAME,'candidate_'+str(i))for i,s in enumerate((body,*controls)))).replace('TESTS',','.join('candidate_'+str(i)for i in range(6)))
    src=g.source.OUT/'native.c';src.write_text(code);reports=[]
    for opt in('-O0','-O2','-O3'):
        exe=g.source.OUT/('native'+opt);p=subprocess.run([*native_command(opt),'-o',str(exe),str(src)],cwd=g.source.ROOT,capture_output=True,text=True);(g.source.OUT/('native'+opt+'-diagnostics.txt')).write_text(p.stdout+p.stderr)
        if p.returncode:raise ValueError(p.stderr[-5000:])
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode)
        reports.append(dict(optimization=opt,cases=len(cases),undefined_sanitizer=True,record_bytes=248,table_words=55,controls=11,live_bytes=12,active_bytes=16,effective_controls=5,implicit_cast_control_killed=True))
    (g.source.OUT/'native-report.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports),flush=True)
if __name__=='__main__':main()
