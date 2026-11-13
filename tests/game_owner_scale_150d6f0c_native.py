"""Native32 checks over defined float conversions, plus negative controls."""
import itertools,subprocess,math
from tools.experiments import game_owner_scale_150d6f0c_match as packet
from tools.tests import game_owner_scale_150d6f0c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.game_actor_intensity_byte_oracle import float32
from tools.tests.game_animation_timeline_oracle import floating
from tools.tests.test_game_point_transform_match import read

def run(state):
    root=packet.ROOT;p=packet.OUT;decl=packet.MANIFEST['declarations'];fn=packet.MANIFEST['body']
    controls={'identity':('target[0x3B]','target[0x3A]'),'size':('sqrtf(link->elapsed) * link->scale','sqrtf(link->elapsed) * 1.0f'),'decay':('link->decay * time * time','0.0f * time * time'),'advance':('link->elapsed += D_800BE9A4','link->elapsed += 0.0f'),'limit':('link->limit < link->elapsed','link->limit <= link->elapsed'),'helper':('func_150D6C98((f32 *)target, (f32 *)(owner + 0x40));',';'),'alpha_dest':('owner[0x2B]','owner[0x2A]'),'size_dest':('owner + 0x3C','owner + 0x34')}
    retail=g.words(state['retail']);rows=[]
    for word,match,elapsed,alpha,decay,mutation in itertools.product((0,1),(0,1),(0,0x3e800000,0x3f800000,0x40700000,0x40800000,0x41100000),(0x42800000,0x42c80000),(0,0x3f800000),(0,1,2,3)):
     active=bool(word and match);t=4.0 if mutation&1 and active else floating(elapsed);av=80.0 if mutation&1 and active else floating(alpha);dv=1.0 if mutation&2 and active else floating(decay)
     tmp=float32(float32(dv*t)*t);converted=float32(av-tmp)
     if active and (not math.isfinite(converted) or not 0<=converted<2**32):continue
     c=g.Case(0,word,match,elapsed,alpha,decay,mutation,0);mem=g.fixture(c);m=g.Machine(retail,c,mem).run();expected=[read(m.memory,g.OWNER+i)for i in (0x38,0x3c,0x40,0x44,0x48,0xb0,0xb4,0xb8,0xbc,0xc0)]
     if active:
      scale=0.5 if mutation&2 else 2.0;size=float32(math.sqrt(t)*scale);updated=float32(t+0.25)
      assert floating(expected[0])==size and floating(expected[1])==size and floating(expected[5])==updated
      assert m.memory[g.OWNER+0x2b]==(int(converted)&255) and m.r[2]==int(not (4.0<updated))
     else:assert m.r[2]==0
     rows.append((word,match,elapsed,alpha,decay,mutation,int(active),m.r[2],m.memory[g.OWNER+0x2b],*expected))
    head='#include <ultra64.h>\n'+decl+'''\nstatic u8 owner[512] __attribute__((aligned(8)));static u8 target[256] __attribute__((aligned(8)));static u32 calls;static u32 mutation;f32 D_800BE9A4=0.25f;
    f32 sqrtf(f32 x){f32 y;__asm__ volatile("sqrtss %1, %0":"=x"(y):"x"(x));return y;}
    void func_150D6C98(f32 *a,f32 *b){calls++;b[0]=a[5];b[1]=a[6]+60.0f;b[2]=a[7];if(mutation&1){*(u32*)(owner+0xb0)=0x40800000u;*(u32*)(owner+0xbc)=0x42a00000u;}if(mutation&2){*(u32*)(owner+0xb8)=0x3f000000u;*(u32*)(owner+0xc0)=0x3f800000u;}}
    '''
    bodies=fn.replace('s32 func_150D6F0C(','s32 test_selected(')
    for name,(a,b) in controls.items():
     assert a in fn; bodies+='\n'+fn.replace('s32 func_150D6F0C(','s32 test_'+name+'(').replace(a,b)
    entries=',\n'.join('{'+','.join(str(x)+'u'for x in row)+'}'for row in rows)
    harness='''
    typedef struct {u32 word,match,elapsed,alpha,decay,mutation,active,result,outbyte,out38,out3c,out40,out44,out48,outb0,outb4,outb8,outbc,outc0;} Fixture;
    static const Fixture fixtures[]={
    '''+entries+'''\n};
    typedef s32 (*Update)(u8 *,void *);
    static int check(Update fn){u32 n,i,j;for(n=0;n<COUNT;n++){const Fixture*f=&fixtures[n];u8 saved[256];s32 result;for(i=0;i<512;i++)owner[i]=(u8)(i*29+0x59);for(i=0;i<256;i++)target[i]=(u8)(i*29+0x59);*(u8**)(owner+0xa8)=target;owner[0xac]=0x41;*(u32*)target=f->word;target[0x3b]=f->match?0x41:0x42;*(u32*)(owner+0xb0)=f->elapsed;*(u32*)(owner+0xb4)=0x40800000u;*(u32*)(owner+0xb8)=0x40000000u;*(u32*)(owner+0xbc)=f->alpha;*(u32*)(owner+0xc0)=f->decay;*(u32*)(target+0x14)=0x3f800000u;*(u32*)(target+0x18)=0x40000000u;*(u32*)(target+0x1c)=0x40400000u;for(i=0;i<256;i++)saved[i]=target[i];calls=0;mutation=f->mutation;result=fn(owner,(void *)0x12345678u);if((u32)result!=f->result||calls!=f->active||owner[0x2b]!=f->outbyte||*(u8**)(owner+0xa8)!=target||owner[0xac]!=0x41)return 1;
    {const u32 offsets[5]={0x38,0x3c,0x40,0x44,0x48};const u32 expected[5]={f->out38,f->out3c,f->out40,f->out44,f->out48};for(j=0;j<5;j++){if(f->active){if(*(u32*)(owner+offsets[j])!=expected[j])return 2;}else for(i=0;i<4;i++)if(owner[offsets[j]+i]!=(u8)((offsets[j]+i)*29+0x59))return 3;}}
    if(*(u32*)(owner+0xb0)!=f->outb0||*(u32*)(owner+0xb4)!=f->outb4||*(u32*)(owner+0xb8)!=f->outb8||*(u32*)(owner+0xbc)!=f->outbc||*(u32*)(owner+0xc0)!=f->outc0)return 4;
    for(i=0;i<256;i++)if(target[i]!=saved[i])return 5;for(i=0;i<512;i++){if(i==0x2b||(i>=0x38&&i<0x4c)||(i>=0xa8&&i<0xad)||(i>=0xb0&&i<0xc4))continue;if(owner[i]!=(u8)(i*29+0x59))return 6;}}return 0;}
    static int run(void){if(check(test_selected))return 10;
    '''.replace('COUNT',str(len(rows)))
    for i,name in enumerate(controls):harness+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
    harness+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    file=p/'native.c';file.write_text(head+bodies+harness)
    reports={}
    for opt in('-O0','-O2','-O3'):
     exe=p/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(file),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0,(r.stdout,r.stderr);r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);reports[opt]={'cases':len(rows),'negative_controls':len(controls),'ubsan':True}
    return {'profiles':reports,'float_domain':'nonnegative sqrt and representable u32 conversion'}
