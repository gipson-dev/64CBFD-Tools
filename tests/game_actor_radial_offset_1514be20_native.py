import itertools,json,subprocess,sys
from pathlib import Path
from tools.experiments import game_actor_radial_offset_1514be20_match as p
out=p.out;root=p.root
from tools.tests import game_actor_radial_offset_1514be20_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-selected.c').read_text(),'func_1514BE20')
 controls={
  'height':('*(f32 *)(actor + 0x38) + 100.0f','*(f32 *)(actor + 0x38) + 99.0f'),
  'fraction':('* fraction;','* 0.0f;'),
  'direction_x':('interpolated.unk0 - target.unk0','interpolated.unk0 + target.unk0'),
  'direction_y':('interpolated.unk4 - *(f32 *)(actor + 0x38)','interpolated.unk4 + *(f32 *)(actor + 0x38)'),
  'direction_z':('interpolated.unk8 - target.unk8','interpolated.unk8 + target.unk8'),
  'helper_alias':('(&direction, &direction, &length, &reciprocal)','(&direction, &target, &length, &reciprocal)'),
  'output_scale':('direction.unk0 * 100.0f','direction.unk0 * 99.0f'),
  'zero_result':('= *(struct17 *)(actor + 0x34);','= target;'),
  'return':('return normalized;','return 0;'),
 }
 cases=[g.Case(*c) for c in itertools.product((-100.,0.,200.),(-100.,0.,200.),(-100.,0.,200.),(0.,.5,1.,2.),(0,1))]
 code=r'''#include <ultra64.h>
 #include "structs.h"
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u8 pad00[0x34]; f32 origin[3],position[3];u8 pad4c[0x110]; f32 fraction;u8 tail[0x20];} Actor;
 _Static_assert(__builtin_offsetof(Actor,origin)==0x34 && __builtin_offsetof(Actor,position)==0x40 && __builtin_offsetof(Actor,fraction)==0x15c,"actor layout");
 struct Case {u32 initial[7],sample[3],result[3];s32 outcome;};
 static const struct Case cases[]={
 '''
 for c in cases:
  m=g.fixture(c);sample,expected=g.reference(c);initial=[g.read(m,g.ACTOR+x)for x in (0x34,0x38,0x3c,0x40,0x44,0x48,0x15c)];final=[g.read(expected,g.ACTOR+0x40+4*i)for i in range(3)]
  arr=lambda xs:'{'+','.join('0x%Xu'%v for v in xs)+'}'
  code+='{'+arr(initial)+','+arr(sample)+','+arr(final)+','+str(c.outcome)+'},\n'
 code+=r'''};
 static const struct Case *current;static int calls,bad;
 static void put_bits(f32*dst,u32 x){u8*d=(u8*)dst,*s=(u8*)&x;u32 i;for(i=0;i<4;i++)d[i]=s[i];}
 static u32 get_bits(const f32*src){u32 x=0,i;u8*d=(u8*)&x;const u8*s=(const u8*)src;for(i=0;i<4;i++)d[i]=s[i];return x;}
 s32 func_15145128(struct17 *a,struct17 *b,f32 *length,f32 *reciprocal){
  calls++;if(a!=b||!length||!reciprocal)bad=1;
  if(get_bits(&a->unk0)!=current->sample[0]||get_bits(&a->unk4)!=current->sample[1]||get_bits(&a->unk8)!=current->sample[2])bad=1;
  if(current->outcome){b->unk0=.5f;b->unk4=-.25f;b->unk8=.75f;*length=100.f;*reciprocal=.01f;}return current->outcome;
 }
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_1514BE20','test_'+key,1)+'\n'
 code+=r'''
 typedef s32(*T)(u8*);
 static int check(T test){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];Actor actor;u8 before[sizeof actor];u8*p=(u8*)&actor;s32 ret;
  for(i=0;i<sizeof actor;i++)p[i]=(i*19+37)&255;
  for(i=0;i<3;i++){put_bits(&actor.origin[i],c->initial[i]);put_bits(&actor.position[i],c->initial[i+3]);}put_bits(&actor.fraction,c->initial[6]);
  for(i=0;i<sizeof actor;i++)before[i]=p[i];current=c;calls=bad=0;ret=test((u8*)&actor);
  if(bad||calls!=1||ret!=c->outcome)return 1;
  for(i=0;i<3;i++)if(get_bits(&actor.position[i])!=c->result[i])return 2;
  for(i=0;i<sizeof actor;i++)if((i<0x40||i>=0x4c)&&p[i]!=before[i])return 3;
  }return 0;}
 static int run(void){int v=check(test_selected);if(v)return v;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_1514BE20_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_1514BE20_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(cases),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helper='modeled',valid_finite_actor_layout=True,source_installed=False);(out/'native_1514BE20_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
