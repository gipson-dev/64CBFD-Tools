"""Actual typed SDK32 callback with independent field and child-call snapshots."""
import subprocess
from tools.experiments import game_tank_camera_15104520_match as match
from tools.tests import game_tank_camera_15104520_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def native_checks(out):
    rows=[];values=lambda a:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in a)+'}'
    for c in g.cases():
        if c.phase or c.subject not in(g.ACTOR,g.OTHER):continue
        initial=g.fixture(c);final,calls,snaps=g.reference(initial,c)
        rows.append('{'+','.join([values(g.fields(initial)),values(g.fields(final)),values(snaps[0]if snaps else(0,)*11),
                                  str(len(calls))+'u',str(c.mutation)+'u'])+'},')
    harness=r'''
typedef char Layout[(sizeof(void*)==4&&sizeof(TankCamera1319D0)==0x700&&sizeof(struct127)==0x32C&&
 __builtin_offsetof(TankCamera1319D0,verticalOffset)==0x190&&__builtin_offsetof(TankCamera1319D0,distance348)==0x348&&
 __builtin_offsetof(TankCamera1319D0,distance34C)==0x34C&&__builtin_offsetof(TankCamera1319D0,currentDistance)==0x370&&
 __builtin_offsetof(TankCamera1319D0,desiredDistance)==0x374&&__builtin_offsetof(TankCamera1319D0,subject)==0x3D0&&
 __builtin_offsetof(TankCamera1319D0,transition)==0x3E8&&__builtin_offsetof(TankCamera1319D0,mode)==0x6C8&&
 __builtin_offsetof(TankCamera1319D0,override)==0x6FC&&__builtin_offsetof(struct127,xz_velocity)==0x3C)?1:-1];
typedef struct {u32 initial[11],expected[11],before[11],calls,mutation;} Row;
static const Row rows[]={ROWS};
static const Row *row;static TankCamera1319D0 camera;static struct127 actor,other;static u32 called,error;
static const u32 offsets[9]={0x190,0x348,0x34C,0x370,0x374,0x3D0,0x3E8,0x6C8,0x6FC};
static void store(u8*p,u32 v){u32 i;for(i=0;i<4;i++)p[i]=(u8)(v>>(i*8));}
static u32 load(const u8*p){u32 i,v=0;for(i=0;i<4;i++)v|=(u32)p[i]<<(i*8);return v;}
static u32 word(f32 f){return load((const u8*)&f);}
static struct127 *pointer(u32 v){return v==0x70000?&actor:v==0x80000?&other:0;}
static void setup(const u32*v){u32 i;for(i=0;i<sizeof(camera);i++)((u8*)&camera)[i]=(u8)(i*29+0x5A);
 for(i=0;i<9;i++){if(i==5)camera.subject=pointer(v[i]);else if(i==6)camera.transition=(u8)v[i];else store((u8*)&camera+offsets[i],v[i]);}
 store((u8*)&actor+0x3C,v[9]);store((u8*)&other+0x3C,v[10]);}
static int equal(const u32*v){u32 i;
 for(i=0;i<9;i++){u32 value=i==6?camera.transition:load((u8*)&camera+offsets[i]);u32 wanted=i==5?(u32)pointer(v[i]):v[i];if(value!=wanted)return 0;}
 return load((u8*)&actor+0x3C)==v[9]&&load((u8*)&other+0x3C)==v[10];}
void __attribute__((noinline,noclone)) func_15128774(TankCamera1319D0*c,struct127*s){
 if(c!=&camera||s!=pointer(row->before[5])||called++||!row->calls||!equal(row->before)){error=1;return;}
 if(row->mutation&1){store((u8*)&camera+0x374,word(-31.25f));store((u8*)&camera+0x370,word(92.5f));}
 if(row->mutation&2){camera.override=0xFEDCBA98;camera.mode=0x87654321;camera.transition=255;}
 if(row->mutation&4){camera.subject=&other;store((u8*)&actor+0x3C,word(27.25f));store((u8*)&other+0x3C,word(-6.5f));}
}
static int run(void){u32 i;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
 row=&rows[i];setup(row->initial);called=error=0;func_15104520(&camera);
 if(error||called!=row->calls||!equal(row->expected))return 1;
 }return 0;}
'''.replace('ROWS','\n'.join(rows))
    changes={
        'default_gate':('camera->override != 0 || camera->mode == 0','camera->override != 0 && camera->mode == 0'),
        'distance_default':('117.0f','118.0f'),
        'desired_default':('370.0f','371.0f'),
        'speed_threshold':('xz_velocity < 50.0f','xz_velocity < 49.0f'),
        'transition_gate':('camera->transition == 0','camera->transition != 0'),
        'half_factor':('half = 0.5f','half = 0.25f'),
        'strict_gap':('half * desired < camera->currentDistance','half * desired <= camera->currentDistance'),
        'child_subject':('func_15128774(camera, subject);','func_15128774(camera, NULL);'),
    }
    controls={n:match.SELECTED.replace(a,b)for n,(a,b)in changes.items()};assert all(body!=match.SELECTED for body in controls.values())
    profiles=[]
    for opt in('-O0','-O2','-O3'):
        for name,body in[('selected',match.SELECTED),*controls.items()]:
            source=out/('native'+opt+'-'+name+'.c');exe=source.with_suffix('');source.write_text(body+harness+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
            result=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fsanitize=float-cast-overflow',str(source),'-o',str(exe)],cwd=match.ROOT,capture_output=True,text=True)
            if result.returncode or result.stdout or result.stderr:raise ValueError(result.stdout+result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=30);assert result.returncode==(0 if name=='selected'else 1),(opt,name,result.returncode,result.stderr[:200])
        profiles.append(dict(profile=opt,cases=len(rows),effective_source_controls=len(controls),UBSan=True,float_cast_overflow=True,strict_aliasing=True))
    return dict(profiles=profiles,actual_selected_source=True,independent_serialized_reference=True,typed_camera_and_actor_objects=True,
                guest_only_cross_type_aliases_excluded=True,FCSR_hardware_claim=False)
