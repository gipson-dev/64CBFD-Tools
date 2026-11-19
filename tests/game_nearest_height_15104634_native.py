"""Actual SDK32 private candidate checked against serialized independent results."""
import subprocess
from tools.experiments import game_nearest_height_15104634_recovery as source
from tools.tests import game_nearest_height_15104634_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def native_checks(out):
    rows=[];values=lambda a:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in a)+'}'
    for c in g.cases():
        if c.phase or c.mutation&24:continue
        initial=g.fixture(c);final,calls,answer,_,_=g.reference(initial,c)
        row=[values(g.fields(initial)),values(g.fields(final)),values(g.read(final,a)for a in(g.OUTPUT,g.ALT,g.BOUND)),values(calls[1][1]),
             *('0x%Xu'%(v&0xFFFFFFFF)for v in(c.x,c.z,c.target,c.out,c.bound,c.count,c.mutation,c.stages,answer))]
        rows.append('{'+','.join(row)+'},')
    harness=r'''
typedef char Layout[(sizeof(void*)==4&&sizeof(HeightCandidate131A90)==16&&__builtin_offsetof(HeightCandidate131A90,offsets)==4&&__builtin_offsetof(HeightCandidate131A90,vertices)==8)?1:-1];
typedef struct{u32 initial[280],expected[280],outputs[3],query[2],x,z,target,out,bound,count,mutation,stages,answer;} Row;
static const Row rows[]={ROWS};
typedef struct{s16 x,y,z;u8 padding[10];} Vertex;
HeightCandidate131A90 D_800D3300[40];f32 D_800A2370;
static u32 offsets[40][3];static Vertex vertices[40][4];static f32 output,alternate;
static const Row *row;static u32 called,error;
static void store(u8*p,u32 v){u32 i;for(i=0;i<4;i++)p[i]=(u8)(v>>(i*8));}
static u32 load(const u8*p){u32 i,v=0;for(i=0;i<4;i++)v|=(u32)p[i]<<(i*8);return v;}
static f32 real(u32 v){f32 f;store((u8*)&f,v);return f;}
static f32 *pointer(u32 v){return v==0x50000?&output:v==0x50020?&alternate:v==0x800A2370?&D_800A2370:0;}
static void setup(void){u32 i,j,n=0;
 for(i=0;i<40;i++){store((u8*)&D_800D3300[i].fixedHeight,row->initial[n++]);D_800D3300[i].offsets=offsets[i];D_800D3300[i].vertices=(u8*)vertices[i];D_800D3300[i].unusedC=(s32)(0xABCD1234u+i);
  for(j=0;j<3;j++){offsets[i][j]=j*16;vertices[i][j].x=(s16)row->initial[n++];vertices[i][j].y=-1234;vertices[i][j].z=(s16)row->initial[n++];}}
 output=real(0xC0A80000);alternate=real(0x42A60000);D_800A2370=real(row->bound);
}
static int equal(void){u32 i,j,n=0;
 for(i=0;i<40;i++){if(load((u8*)&D_800D3300[i].fixedHeight)!=row->expected[n++]||D_800D3300[i].offsets!=offsets[i]||D_800D3300[i].vertices!=(u8*)vertices[i]||(u32)D_800D3300[i].unusedC!=0xABCD1234u+i)return 0;
  for(j=0;j<3;j++)if((u16)vertices[i][j].x!=row->expected[n++]||(u16)vertices[i][j].z!=row->expected[n++]||offsets[i][j]!=j*16||vertices[i][j].y!=-1234)return 0;}
 return load((u8*)&output)==row->outputs[0]&&load((u8*)&alternate)==row->outputs[1]&&load((u8*)&D_800A2370)==row->outputs[2];
}
static __attribute__((noinline,noclone)) void observe(u32 stage,s32 x,s32 z){u32 i,j,flags=(row->stages>>stage&1)?row->mutation:0;
 if(called++!=stage)error=1;if(stage==0){if(x||z)error=2;}else if((u32)x!=row->query[0]||(u32)z!=row->query[1])error=3;
 if(flags&1)for(j=0;j<3;j++){s16 t=vertices[0][j].x;vertices[0][j].x=vertices[0][j].z;vertices[0][j].z=t;}
 if(flags&2)for(i=0;i<40;i++)store((u8*)&D_800D3300[i].fixedHeight,load((u8*)&D_800D3300[i].fixedHeight)^0x80000080u);
 if(flags&4)D_800A2370=real(stage?0x7FC22222:0xBF800000);
}
void func_1510F800(s32 context){observe(0,context,0);}
s32 func_150A3A70(s32 x,s32 z){observe(1,x,z);return(s32)row->count;}
static int run(void){u32 i;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){s32 answer;row=&rows[i];setup();called=error=0;
 answer=func_15104634(real(row->x),real(row->z),real(row->target),pointer(row->out));
 if(error||called!=2||answer!=(s32)row->answer||!equal())return 1;
 }return 0;}
'''.replace('ROWS','\n'.join(rows))
    changes={
      'query_coordinates':('func_150A3A70((s32)x, (s32)z)','func_150A3A70((s32)z, (s32)x)'),
      'zero_hits':('hits == 0','hits != 0'),
      'orientation':('orientation > 0.0f','orientation < 0.0f'),
      'absolute_value':('value < 0.0f','value > 0.0f'),
      'tie_order':('value < orientation ||','value <= orientation ||'),
      'height_scale':('1.0f / 256.0f','1.0f / 128.0f'),
      'query_context':('func_1510F800(0)','func_1510F800(1)'),
      'success_value':('return 1;\n}', 'return 2;\n}'),
    }
    controls={n:source.SELECTED.replace(a,b)for n,(a,b)in changes.items()};assert all(v!=source.SELECTED for v in controls.values())
    profiles=[]
    for opt in('-O0','-O2','-O3'):
        codes={}
        for name,body in[('selected',source.SELECTED),*controls.items()]:
            path=out/('native'+opt+'-'+name+'.c');exe=path.with_suffix('');path.write_text(body+harness+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
            result=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fsanitize=float-cast-overflow',str(path),'-o',str(exe)],cwd=source.ROOT,capture_output=True,text=True)
            if result.returncode or result.stdout or result.stderr:raise ValueError(result.stdout+result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=30);assert(result.returncode==0)==(name=='selected'),(opt,name,result.returncode,result.stderr[:200]);codes[name]=result.returncode
        profiles.append(dict(profile=opt,cases=len(rows),effective_source_controls=len(controls),exit_codes=codes,UBSan=True,float_cast_overflow=True,strict_aliasing=True))
    return dict(profiles=profiles,actual_selected_source=True,independent_serialized_reference=True,accepted_capacity_bounded_to_24=True,query_counts_through_39=True,
                guest_only_home_mutations_excluded=True,byte_matching_and_FCSR_hardware_claim=False)
