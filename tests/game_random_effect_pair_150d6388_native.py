"""Native32 finite RNG samples, float arguments and negative controls."""
import itertools,subprocess
from tools.experiments import game_random_effect_pair_150d6388_match as packet
from tools.tests import game_random_effect_pair_150d6388_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run(state):
    root=packet.ROOT;p=packet.OUT;decl=packet.MANIFEST['declarations']
    names=tuple(packet.MANIFEST['targets']);fn={name:packet.MANIFEST['targets'][name]['body'] for name in names}
    controls={'a_scale':(names[0],'first * 4.0f','first * 3.0f'),'a_offset':(names[0],'+ 15.0f','+ 14.0f'),'a_mod':(names[0],'% 56U','% 55U'),'a_base':(names[0],'+ 200U','+ 201U'),'a_constant':(names[0],'1.3745700120925903f','1.0f'),'a_selector':(names[0],'0.0f, selector, context','0.0f, 0, context'),'a_context':(names[0],'0.0f, selector, context','0.0f, selector, 0'),'b_scale':(names[1],'first * 3.0f','first * 4.0f'),'b_second':(names[1],'second * D_800A0AB0','second * D_800A0AB4'),'b_offset':(names[1],'+ D_800A0AB4','+ D_800A0AB0'),'b_third':(names[1],'third * 50.0f','third * 49.0f'),'b_height':(names[1],'+ 100.0f','+ 99.0f'),'b_selector':(names[1],'selector, context','0, context')}
    floatsets=((0,0x3e800000,0x3f000000),(0x3e800000,0x3f000000,0x3f400000),(0x3f800000,0xbf800000,0x40000000),(0xbf800000,0x3f800000,0x3e800000));integers=(0,1,55,56,0x80000000,0xffffffff);cases=[]
    for name in names:
     for selector in range(256):cases.append((name,g.Case(selector=0x12340000|selector,context=0x87654321,floats=floatsets[selector%4],integer=integers[selector%6],mutation=selector%2)))
     for selector,fs,integer,mutation in itertools.product((0,1,127,255),floatsets,integers,(0,1)):cases.append((name,g.Case(selector=0x12340000|selector,context=0x87654321,floats=fs,integer=integer,mutation=mutation)))
    rows=[]
    for name,c in cases:
     _,calls,_=g.reference(g.fixture(c),name,c);assert calls[-1][0] in(g.A,g.B);args=list(calls[-1][1]);args+=([0]*(7-len(args)));rows.append((int(name==names[1]),c.selector,c.context,*c.floats,c.integer,c.mutation,*args))
    head='#include <ultra64.h>\n'+decl+'''\ntypedef struct {u32 which,selector,context,f0,f1,f2,integer,mutation,a0,a1,a2,a3,a4,a5,a6;} Fixture;
    static const Fixture *current;static u32 step,calls,fi,kinds[4],arguments[7];f32 D_800A0AB0,D_800A0AB4;
    static f32 asfloat(u32 u){union{u32 u;f32 f;}x;x.u=u;return x.f;}static u32 asbits(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
    static void change(void){step++;if(current->mutation&1){D_800A0AB0=(f32)step*.25f;D_800A0AB4=(f32)step;}}
    f32 func_150ADA68(void){u32 v=fi==0?current->f0:fi==1?current->f1:current->f2;fi++;kinds[calls++]=1;change();return asfloat(v);}
    s32 func_150ADA20(void){kinds[calls++]=2;change();return (s32)current->integer;}
    void *func_151541B8(f32 *p,f32 a,f32 b,f32 c,f32 d,u8 e,s32 f){kinds[calls++]=3;arguments[0]=(u32)p;arguments[1]=asbits(a);arguments[2]=asbits(b);arguments[3]=asbits(c);arguments[4]=asbits(d);arguments[5]=e;arguments[6]=(u32)f;return (void*)1;}
    void *func_15154884(f32 *p,f32 a,f32 b,f32 c,u8 e,s32 f){kinds[calls++]=4;arguments[0]=(u32)p;arguments[1]=asbits(a);arguments[2]=asbits(b);arguments[3]=asbits(c);arguments[4]=e;arguments[5]=(u32)f;arguments[6]=0;return (void*)1;}
    '''
    bodies='\n'.join(fn[n].replace('void '+n+'(','void selected_'+n+'(')for n in names)
    for key,(name,a,b)in controls.items():assert a in fn[name];bodies+='\n'+fn[name].replace('void '+name+'(','void test_'+key+'(').replace(a,b)
    entries=',\n'.join('{'+','.join(str(x)+'u'for x in row)+'}'for row in rows)
    harness='''\nstatic const Fixture fixtures[]={\n'''+entries+'''\n};
    typedef void (*Update)(f32 *,u8,s32);
    static int check(Update left,Update right){u32 n,i;for(n=0;n<COUNT;n++){const Fixture*f=&fixtures[n];const u32 expected[7]={f->a0,f->a1,f->a2,f->a3,f->a4,f->a5,f->a6};current=f;step=calls=fi=0;D_800A0AB0=2.0f;D_800A0AB4=-1.0f;for(i=0;i<7;i++)arguments[i]=0;if(f->which)right((f32*)0x30000u,(u8)f->selector,(s32)f->context);else left((f32*)0x30000u,(u8)f->selector,(s32)f->context);if(f->which){if(calls!=4||kinds[0]!=1||kinds[1]!=1||kinds[2]!=1||kinds[3]!=4)return 1;}else if(calls!=3||kinds[0]!=1||kinds[1]!=2||kinds[2]!=3)return 2;for(i=0;i<7;i++)if(arguments[i]!=expected[i])return 3;}return 0;}
    static int run(void){if(check(selected_func_150D6388,selected_func_150D6434))return 10;
    '''.replace('COUNT',str(len(rows)))
    for i,(key,(name,a,b))in enumerate(controls.items()):
     left='test_'+key if name==names[0]else'selected_func_150D6388';right='test_'+key if name==names[1]else'selected_func_150D6434';harness+='if(!check('+left+','+right+'))return '+str(20+i)+';\n'
    harness+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    file=p/'native.c';file.write_text(head+bodies+harness)
    reports={}
    for opt in('-O0','-O2','-O3'):
     exe=p/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(file),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0,(r.stdout,r.stderr);r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);reports[opt]={'cases':len(rows),'negative_controls':len(controls),'ubsan':True}
    return {'profiles':reports,'float_domain':'finite samples'}
