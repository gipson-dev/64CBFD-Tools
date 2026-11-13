"""Native32 checks for finite values, with independent arithmetic and controls."""
import itertools,subprocess,math
from tools.experiments import game_owner_velocity_150d6cc4_match as packet
from tools.tests import game_owner_velocity_150d6cc4_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.game_actor_intensity_byte_oracle import float32
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import read

def run(state):
    root=packet.ROOT;p=packet.OUT;decl=packet.MANIFEST['declarations'];fn=packet.MANIFEST['body']
    controls={'identity':('target[0x3B]','target[0x3A]'),'gravity':('owner + 0x64','owner + 0x68'),'factor':('link->factor','1.0f'),'acceleration':('D_800BE9A8','D_800BE9A4'),'copy':('func_150D6C98((f32 *)target, (f32 *)(owner + 0x40));',';'),'scale':('func_15131958((f32 *)(owner + 0x58), link->factor);',';'),'half':('0.5f','1.0f'),'dest':('owner + 0x4C','owner + 0x70')}
    retail=g.words(state['retail']);rows=[]
    for word,identity,factor,count,dt,mutation,vector in itertools.product((0,1),(0,1),(0x3f000000,0x3fa00000),(0,1,2),(0x3e800000,0xbe800000),(0,1,2,3),(0,1)):
     case=g.Case(0,word,identity,factor,count,dt,mutation,vector);initial=g.fixture(case);g.put(initial,g.OWNER+0x68,0x3f800000);m=g.Machine(retail,case,initial).run();active=bool(word and identity);outs=[read(m.memory,g.OWNER+i)for i in (0x40,0x44,0x48,0x4c,0x50,0x54,0x58,0x5c,0x60)];outdt=read(m.memory,g.DT);outacc=read(m.memory,g.ACCEL)
     if active:
      old=[1.0,2.0,3.0]if not vector else[-1.0,.5,4.0];f=floating(factor);d=floating(dt);pos=[10.0,20.0,30.0];acc=.5
      if mutation&1:old[0]=3.0;f=.5;d=.5
      vel=old[:];vel[1]=float32(vel[1]+float32(2.0*d))
      for _ in range(count):vel=[float32(v*f)for v in vel]
      if mutation&2:d=1.0;acc=1.0;pos[0]=50.0
      for i in range(3):
       diff=float32(float32(vel[i]-old[i])*acc);linear=float32(old[i]*d);curve=float32(float32(float32(diff*d)*d)*.5);pos[i]=float32(pos[i]+float32(linear+curve))
      assert outs[:3]==[bits(1.),bits(62.),bits(3.)] and outs[3:6]==[bits(x)for x in pos] and outs[6:9]==[bits(x)for x in vel],case
      assert m.r[2]==1 and outdt==bits(d) and outacc==bits(acc),case
     else:assert m.r[2]==0
     rows.append((word,identity,factor,count,dt,mutation,vector,int(active),*outs,outdt,outacc))
    head='#include <ultra64.h>\n'+decl+'''\nstatic u8 owner[512] __attribute__((aligned(8)));static u8 target[256] __attribute__((aligned(8)));static u32 calls,mutation,count;f32 D_800BE9A4,D_800BE9A8;
    static f32 asfloat(u32 u){union{u32 u;f32 f;}x;x.u=u;return x.f;}static u32 asbits(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
    void func_150D6C98(f32 *a,f32 *b){calls++;b[0]=a[5];b[1]=a[6]+60.0f;b[2]=a[7];if(mutation&1){*(u32*)(owner+0xb0)=0x3f000000u;*(u32*)(owner+0x58)=0x40400000u;D_800BE9A4=0.5f;}}
    void func_15131958(f32 *a,f32 f){u32 i;calls++;for(i=0;i<count;i++){a[0]*=f;a[1]*=f;a[2]*=f;}if(mutation&2){D_800BE9A4=1.0f;D_800BE9A8=1.0f;*(u32*)(owner+0x4c)=0x42480000u;}}
    '''
    bodies=fn.replace('s32 func_150D6CC4(','s32 test_selected(')
    for name,(a,b)in controls.items():
     assert a in fn;bodies+='\n'+fn.replace('s32 func_150D6CC4(','s32 test_'+name+'(').replace(a,b)
    entries=',\n'.join('{'+','.join(str(x)+'u'for x in row)+'}'for row in rows)
    harness='''
    typedef struct {u32 word,identity,factor,count,dt,mutation,vector,result,out40,out44,out48,out4c,out50,out54,out58,out5c,out60,outdt,outacc;} Fixture;
    static const Fixture fixtures[]={
    '''+entries+'''\n};
    typedef s32 (*Update)(u8 *,void *);
    static int check(Update fn){u32 n,i,j;for(n=0;n<COUNT;n++){const Fixture*f=&fixtures[n];u8 saved[256];s32 result;for(i=0;i<512;i++)owner[i]=(u8)(i*29+0x59);for(i=0;i<256;i++)target[i]=(u8)(i*29+0x59);*(u8**)(owner+0xa8)=target;owner[0xac]=0x41;*(u32*)target=f->word;target[0x3b]=f->identity?0x41:0x42;*(u32*)(owner+0xb0)=f->factor;*(u32*)(owner+0x4c)=0x41200000u;*(u32*)(owner+0x50)=0x41a00000u;*(u32*)(owner+0x54)=0x41f00000u;*(u32*)(owner+0x58)=f->vector?0xbf800000u:0x3f800000u;*(u32*)(owner+0x5c)=f->vector?0x3f000000u:0x40000000u;*(u32*)(owner+0x60)=f->vector?0x40800000u:0x40400000u;*(u32*)(owner+0x64)=0x40000000u;*(u32*)(owner+0x68)=0x3f800000u;*(u32*)(target+0x14)=0x3f800000u;*(u32*)(target+0x18)=0x40000000u;*(u32*)(target+0x1c)=0x40400000u;D_800BE9A4=asfloat(f->dt);D_800BE9A8=.5f;count=f->count;mutation=f->mutation;for(i=0;i<256;i++)saved[i]=target[i];calls=0;result=fn(owner,(void*)0x12345678u);if((u32)result!=f->result||calls!=2*f->result||*(u8**)(owner+0xa8)!=target||owner[0xac]!=0x41||asbits(D_800BE9A4)!=f->outdt||asbits(D_800BE9A8)!=f->outacc)return 1;
    {const u32 offsets[9]={0x40,0x44,0x48,0x4c,0x50,0x54,0x58,0x5c,0x60};const u32 expected[9]={f->out40,f->out44,f->out48,f->out4c,f->out50,f->out54,f->out58,f->out5c,f->out60};for(j=0;j<9;j++){if(j>=3||f->result){if(*(u32*)(owner+offsets[j])!=expected[j])return 2;}else for(i=0;i<4;i++)if(owner[offsets[j]+i]!=(u8)((offsets[j]+i)*29+0x59))return 3;}}
    if(*(u32*)(owner+0xb0)!=(f->result&&(f->mutation&1)?0x3f000000u:f->factor)||*(u32*)(owner+0x64)!=0x40000000u||*(u32*)(owner+0x68)!=0x3f800000u)return 4;for(i=0;i<256;i++)if(target[i]!=saved[i])return 5;for(i=0;i<512;i++){if((i>=0x40&&i<0x6c)||(i>=0xa8&&i<0xad)||(i>=0xb0&&i<0xb4))continue;if(owner[i]!=(u8)(i*29+0x59))return 6;}}return 0;}
    static int run(void){if(check(test_selected))return 10;
    '''.replace('COUNT',str(len(rows)))
    for i,name in enumerate(controls):harness+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
    harness+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    file=p/'native.c';file.write_text(head+bodies+harness)
    reports={}
    for opt in('-O0','-O2','-O3'):
     exe=p/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(file),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0,(r.stdout,r.stderr);r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);reports[opt]={'cases':len(rows),'negative_controls':len(controls),'ubsan':True}
    return {'profiles':reports,'float_domain':'finite test values'}
