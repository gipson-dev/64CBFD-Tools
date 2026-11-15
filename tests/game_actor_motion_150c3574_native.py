"""Compile the complete private callback under SDK32 at O0/O2/O3.

Only finite, guest-qualified vectors are claimed. Callees are explicit models.
"""
import hashlib,json,subprocess
from tools.experiments import game_actor_motion_150c3574_recovery as s
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import game_actor_motion_150c3574_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

CONTROLS={
    'state-shift':('actor[0x87] <<= 1','actor[0x87] <<= 2'),
    'speed-threshold':('0.5f < speed','1.0f < speed'),
    'backward-heading':('heading = currentHeading ^ 0x8000','heading = currentHeading ^ 0x4000'),
    'sound-limit':('volume > 28000','volume > 18000'),
    'sound-scale':('volume >>= 1','volume >>= 2'),
    'animation-scale':('animationScale *= 0.75f','animationScale *= 0.5f'),
}
def arr(values):return '{'+','.join(str(v&0xFFFFFFFF)+'U' for v in values)+'}'

def main(source_module=None):
    s=source_module or globals()['s']
    selected=body((s.OUT/'recovered.c').read_text(),s.NAME)
    cases=list(g.cases())
    code='''#include <ultra64.h>
typedef struct struct127 { u8 bytes[0x240]; } struct127;
static u8 storage[0x280] __attribute__((aligned(16)));
static u8 *actor=storage+32;
static struct127 D_800CC2D0[1];
static struct127 *D_800D154C;
static s32 D_800D1580;
static f32 D_800BE9A8;
static u32 mark;
'''+s.PREAMBLE.replace('extern f32','f32')+'''
void func_15059140(struct127 *);
void func_1506E8D8(void);
void func_1506E5FC(void);
void func_15052490(struct127 *, u16, f32, f32);
void func_100109D0(struct127 *);
s32 func_100107F8(struct127 *);
u16 func_1505A630(f32, f32, s32);
struct Event { u32 target, count, args[5]; };
struct Case { u32 seed,mutation,playing,dt,finaldt,sound,current,mark,count;u8 initial[0x280],final[0x280];struct Event calls[20]; };
static const struct Case cases[]={
'''
    for c in cases:
        initial=g.fixture(c);final,calls=g.reference(initial,c)
        assert len(calls)<=20
        events='{'+','.join('{'+str(t)+'U,'+str(len(a))+'U,'+arr(a)+'}' for t,a in calls)+'}'
        row=(str(c.seed),str(c.mutation),str(c.playing),str(g.read(initial,g.DT))+'U',str(g.read(final,g.DT))+'U',str(g.read(final,g.SOUND))+'U',str(g.read(final,g.CURRENT))+'U',str(g.read(final,g.MARK))+'U',str(len(calls)),arr(initial[g.OWNER-32+i] for i in range(0x280)),arr(final[g.OWNER-32+i] for i in range(0x280)),events)
        code+='{'+','.join(row)+'},\n'
    code+='''};
static const struct Case *current;
static u32 index,bad,counts[13];
static const u32 floats[]={FLOAT_OFFSETS};
static const u32 halves[]={HALF_OFFSETS};
static f32 value(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static u32 word(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
static u32 be(const u8*p,u32 n){u32 v=0,i;for(i=0;i<n;i++)v=v*256+p[i];return v;}
static void storebe(u8*p,u32 v,u32 n){u32 i;for(i=0;i<n;i++)p[i]=(u8)(v>>(8*(n-1-i)));}
static u32 raw(const u8*p,u32 n){u32 v=0,i;u8*q=(u8*)&v;for(i=0;i<n;i++)q[i]=p[i];return v;}
static void store(u8*p,u32 v,u32 n){u32 i;u8*q=(u8*)&v;for(i=0;i<n;i++)p[i]=q[i];}
static u32 address(const void*p){return (u32)((const u8*)p-actor)+0x30040U;}
static void event(u32 t,u32 n,u32 a,u32 b,u32 c,u32 d,u32 e){
 const struct Event*v;u32 args[5]={a,b,c,d,e},i;
 if(index>=current->count){bad=1;return;}v=&current->calls[index++];
 if(t!=v->target||n!=v->count)bad=2;
 for(i=0;i<n;i++)if(args[i]!=v->args[i])bad=3;
}
static void effect(u32 t,u32 slot){u32 n=counts[slot]++;
 mark=0x13579bdfU+t+n*0x10203U;
 if(!current->mutation)return;
 if(t==0x1505a250){*(f32*)(actor+0x164)=.75f;*(f32*)(actor+0x168)=-.5f;if(current->mutation==2)actor[0x87]^=1;}
 else if(t==0x15056b08&&current->mutation==2)actor[4]=0x25;
 else if(t==0x15059140&&current->mutation==2){*(f32*)(actor+0x14)=2.f;*(f32*)(actor+0x1c)=-3.f;D_800BE9A8=.5f;}
 else if(t==0x1506e8d8){actor[0x87]=8;*(f32*)(actor+0xbc)=7.f;*(f32*)(actor+0x148)=-9.f;}
 else if(t==0x1505a630&&current->mutation==2)*(u16*)(actor+0x7a)=0x8000;
 else if(t==0x150599c8&&current->mutation==2){*(f32*)(actor+0x28)=31.f;*(f32*)(actor+0x44)=16.f;actor[0x13d]^=1;}
 else if(t==0x100107f8&&current->mutation==2){actor[4]=0x25;*(f32*)(actor+0x44)=50.f;}
 else if((t==0x1506e5fc||t==0x1001091c)&&current->mutation==2)*(f32*)(actor+0x44)=.1f;
 else if(t==0x100109d0&&current->mutation==2)*(f32*)(actor+0x44)=.3f;
}
void func_1505A250(f32 a,f32 b,f32 c,f32*d,f32*e){event(0x1505a250,5,word(a),word(b),word(c),address(d),address(e));effect(0x1505a250,0);}
void func_1505A3A8(f32 a,void*b,f32 c,f32 d,u8 e){event(0x1505a3a8,5,word(a),address(b),word(c),word(d),e);effect(0x1505a3a8,1);}
void func_15056B08(void*a){event(0x15056b08,1,address(a),0,0,0,0);effect(0x15056b08,2);}
void func_150562FC(void*a){event(0x150562fc,1,address(a),0,0,0,0);effect(0x150562fc,3);}
void func_15059140(struct127*a){event(0x15059140,1,address(a),0,0,0,0);effect(0x15059140,4);}
void func_1506E8D8(void){event(0x1506e8d8,0,0,0,0,0,0);effect(0x1506e8d8,5);}
u16 func_1505A630(f32 a,f32 b,s32 c){static const u16 result[4]={0,0x7fff,0x8000,0xffff};event(0x1505a630,3,word(a),word(b),(u32)c,0,0);effect(0x1505a630,6);return result[current->seed%4];}
void func_150599C8(void*a,s32 b,u16 c){event(0x150599c8,3,address(a),(u32)b,c,0,0);effect(0x150599c8,7);}
void func_15052490(struct127*a,u16 b,f32 c,f32 d){event(0x15052490,4,address(a),b,word(c),word(d),0);effect(0x15052490,8);}
void func_100109D0(struct127*a){event(0x100109d0,1,address(a),0,0,0,0);effect(0x100109d0,9);}
s32 func_100107F8(struct127*a){event(0x100107f8,1,address(a),0,0,0,0);effect(0x100107f8,10);return (s32)current->playing;}
void func_1506E5FC(void){event(0x1506e5fc,0,0,0,0,0,0);effect(0x1506e5fc,11);}
void func_1001091C(struct127*a,s32 b){event(0x1001091c,2,address(a),(u32)b,0,0,0);effect(0x1001091c,12);}
f32 sqrtf(f32 x){f32 y;__asm__("sqrtss %1,%0":"=x"(y):"x"(x));return y;}
'''.replace('FLOAT_OFFSETS',','.join(map(str,g.FLOATS))).replace('HALF_OFFSETS',','.join(map(str,g.HALVES)))
    for name,text in [('selected',selected)]+[(n,selected.replace(a,b,1)) for n,(a,b) in CONTROLS.items()]:
        if name!='selected':assert text!=selected,name
        code+='\n'+text.replace(s.NAME,'test_'+name.replace('-','_'),1)+'\n'
    code+='''
typedef void (*Test)(u8*);
static int check(Test test){u32 n,i,p;u8 bytes[0x280];
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];current=c;index=bad=mark=0;
  for(i=0;i<13;i++)counts[i]=0;
  for(i=0;i<0x280;i++)storage[i]=c->initial[i];
  for(i=0;i<sizeof(floats)/sizeof(floats[0]);i++){p=32+floats[i];store(storage+p,be(c->initial+p,4),4);}
  for(i=0;i<sizeof(halves)/sizeof(halves[0]);i++){p=32+halves[i];store(storage+p,be(c->initial+p,2),2);}
  D_800BE9A8=value(c->dt);D_800D1580=0x12345678;D_800D154C=(struct127*)0x76543210;
  D_800A0320=value(0x3dcccccd);D_800A0324=value(0x3f666666);D_800A0328=value(0x3e4ccccd);D_800A032C=2500.f;D_800A0330=value(0x3e4ccccd);
  test(actor);
  if(bad||index!=c->count||mark!=c->mark||word(D_800BE9A8)!=c->finaldt||(u32)D_800D1580!=c->sound)return 1;
  p=D_800D154C==(struct127*)actor?0x30040U:D_800D154C==D_800CC2D0?0x800cc2d0U:(u32)D_800D154C;
  if(p!=c->current)return 2;
  for(i=0;i<0x280;i++)bytes[i]=storage[i];
  for(i=0;i<sizeof(floats)/sizeof(floats[0]);i++){p=32+floats[i];storebe(bytes+p,raw(storage+p,4),4);}
  for(i=0;i<sizeof(halves)/sizeof(halves[0]);i++){p=32+halves[i];storebe(bytes+p,raw(storage+p,2),2);}
  for(i=0;i<0x280;i++)if(bytes[i]!=c->final[i])return 3;
 }return 0;
}
static int run(void){if(check(test_selected))return 1;
'''
    for i,name in enumerate(CONTROLS):code+='if(!check(test_'+name.replace('-','_')+'))return '+str(20+i)+';\n'
    code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    src=s.OUT/'native.c';src.write_text(code);profiles={}
    for opt in ('-O0','-O2','-O3'):
        exe=s.OUT/('native'+opt);p=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True)
        assert p.returncode==0 and not p.stdout and not p.stderr,(opt,p.stdout,p.stderr)
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stderr)
        profiles[opt]=dict(cases=len(cases),effective_controls=len(CONTROLS),UBSan=True,sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
    report=dict(profiles=profiles,finite_only=True,owner_backing_bytes=0x280,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),installed=False,c_match_credit=0)
    (s.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
