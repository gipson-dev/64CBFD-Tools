"""Native 32-bit bounded float checks and negative controls."""
import itertools,subprocess
from tools.experiments import game_effect_intensity_151c7038_match as match
from tools.tests import game_effect_intensity_151c7038_oracle as d
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests.game_actor_intensity_byte_oracle import float32
from tools.tests.game_animation_timeline_oracle import floating
from tools.tests.test_game_point_transform_match import read

def run(state):
    root=match.ROOT;p=match.OUT
    prefix=match.MANIFEST['declarations'];func=match.MANIFEST['body']
    changes={'wrong_kind':('0xE9','0xE8'),'wrong_bit':('0x20000','0x40000'),
             'wrong_scale':('35.0f','34.0f'),'wrong_ceiling':('255.0f','254.0f'),
             'wrong_min':('intensity = 0.0f','intensity = 1.0f'),
             'ignore_helper':('func_15142A5C((s32 *)effect) != 0','1')}
    fixtures=[];retail=d.words(state['retail'])
    for kind,value,flag,answer,mutation in itertools.product((0xe9,0xe8),(0,0x3f800000,0x41000000,0xbf800000,0x3dcccccd,0x7f7fffff),(0,0xffffffff),(0,1),(0,1,2,3)):
     c=d.Case(0,kind,value,flag,answer,mutation,0);mem=d.fixture(c);mem[d.OWNER+0x70]=173;m=d.Machine(retail,c,mem).run();expected_flag=read(m.memory,d.OWNER+0x60);expected_byte=m.memory[d.OWNER+0x70];expected_kind=read(m.memory,d.EFFECT+0x84,2);expected_scale=read(m.memory,d.EFFECT+0x4c);expected_alt=int(read(m.memory,d.OWNER+0x7c)==d.ALT);active=kind==0xe9
     if active:
      q=2.0 if mutation&1 else floating(value);q=float32(q*35.0);q=min(255.0,max(0.0,q));checkbyte=int(q);checkflag=(0x80705030 if mutation&2 else flag);checkflag=(checkflag|0x20000) if answer else (checkflag&~0x20000)
     else:checkbyte=173;checkflag=flag
     assert (expected_byte,expected_flag,m.r[2])==(checkbyte,checkflag,int(active)),(c,expected_byte,checkbyte)
     fixtures.append((kind,value,flag,answer,mutation,int(active),expected_flag,expected_byte,expected_kind,expected_scale,expected_alt,int(active)))
    header='#include <ultra64.h>\n'+prefix+'''
    typedef struct {u32 kind,value,flags,answer,mutation,result,outflags,outbyte,outkind,outscale,outalt,calls;} Fixture;
    static Owner151C7038 owner;static Effect151C7038 effect,alt;static const Fixture *current;static u32 calls,bad;
    s32 func_15142A5C(s32 *p) {calls++;if ((void*)p != (void*)&effect) bad=1;if(current->mutation & 1){effect.scale=2.0f;effect.kind=0x1234;}if(current->mutation & 2){owner.flags=0x80705030;owner.effect=&alt;}return current->answer;}
    static f32 asfloat(u32 u){union{u32 u;f32 f;}x;x.u=u;return x.f;}
    static u32 asbits(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
    '''
    bodies=func.replace('s32 func_151C7038(','s32 test_selected(')
    for name,(a,b) in changes.items():
     assert a in func; bodies+='\n'+func.replace('s32 func_151C7038(','s32 test_'+name+'(').replace(a,b)
    rows=',\n'.join('{'+','.join(str(x)+'u' for x in row)+'}' for row in fixtures)
    harness='\nstatic const Fixture fixtures[]={\n'+rows+'\n};\n'
    harness+='''typedef s32 (*Update)(Owner151C7038 *);
    static int check(Update fn){u32 i;for(i=0;i<COUNT;i++){const Fixture *f=&fixtures[i];s32 result;current=f;calls=bad=0;owner.flags=f->flags;owner.intensity=173;owner.effect=&effect;effect.kind=f->kind;effect.scale=asfloat(f->value);result=fn(&owner);if(bad||calls!=f->calls||(u32)result!=f->result||owner.flags!=f->outflags||owner.intensity!=f->outbyte||effect.kind!=f->outkind||asbits(effect.scale)!=f->outscale||(owner.effect==&alt)!=f->outalt)return 1;}return 0;}
    static int run(void){if(check(test_selected))return 10;
    '''.replace('COUNT',str(len(fixtures)))
    for i,name in enumerate(changes):harness+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
    harness+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    file=p/'native.c';file.write_text(header+bodies+harness)
    reports={}
    for opt in ('-O0','-O2','-O3'):
     exe=p/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(file),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0,(r.stdout,r.stderr);r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);reports[opt]={'cases':len(fixtures),'negative_controls':len(changes),'ubsan':True}
    return {'profiles':reports,'nan_domain':'guest-only'}
