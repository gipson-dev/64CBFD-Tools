import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_scaled_vertex_radius_15004aac_match as p
out=p.out;root=p.root
from tools.tests import game_scaled_vertex_radius_15004aac_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'selected-source.c').read_text(),'func_15004AAC')
 controls={'count':('i < record->count','i + 1 < record->count'),'x':('record->vertices[i].x * record->sx','record->vertices[i].x * record->sy'),'y':('record->vertices[i].y * record->sy','record->vertices[i].y * record->sz'),'z':('vz * record->sz','vz * record->sx'),'initial':('s32 maximum = 0','s32 maximum = 1'),'write':('record->maximum = radius','record->maximum = radius + 1'),'small':('D_800BE2A0++','D_800BE2A0 += 2'),'first':('D_800BE2A2++','D_800BE2A2 += 2'),'fits':('D_800BE2A4++','D_800BE2A4 += 2'),'compare':('record->radius < radius || record->maximum < radius','record->radius < radius && record->maximum < radius')}
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {s16 x,y,z;u8 pad[10];} BoundsVertex;
 typedef struct {u8 pad0[0x16];u16 count;u8 pad18[0x10];BoundsVertex *vertices;f32 sx,sy,sz;u8 pad38[0x18];u16 radius,maximum;} BoundsRecord;
 u16 D_800BE2A0,D_800BE2A2,D_800BE2A4;
 f32 sqrtf(f32 x){__asm__("sqrtss %1,%0":"=x"(x):"x"(x));return x;}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_15004AAC','test_'+key,1)+'\n'
 code+='typedef void(*T)(BoundsRecord*,s32);\nstatic int check(T test){\n'
 for c in g.cases():
  m=g.fixture(c);e=g.reference(c,m);verts=','.join('{%d,%d,%d,{0}}'%v for v in c.vertices) or '{0,0,0,{0}}';scales=','.join(str(x)+'f' for x in c.scales)
  expected=[g.read(e,g.RECORD+0x50,2),g.read(e,g.RECORD+0x52,2)]+[g.read(e,g.COUNTERS+2*i,2) for i in range(3)]
  init=65535 if c.seed else 17
  code+=('{BoundsVertex v[]={%s}; BoundsRecord b={0}; b.count=%d;b.vertices=v; b.sx=%s;b.sy=%s;b.sz=%s;b.radius=%d;b.maximum=%d;D_800BE2A0=%d;D_800BE2A2=%d;D_800BE2A4=%d;test(&b,0x12345678);if(b.radius!=%d||b.maximum!=%d||D_800BE2A0!=%d||D_800BE2A2!=%d||D_800BE2A4!=%d)return 1;}\n'% (verts,len(c.vertices),*scales.split(','),c.radius,c.maximum,init,init if c.seed else 18,init if c.seed else 19,*expected))
 code+='return 0;}\nstatic int run(void){if(check(test_selected))return 10;\n'
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native-screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native-screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,finite_valid_nonaliased_input_only=True,source_installed=False);(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
