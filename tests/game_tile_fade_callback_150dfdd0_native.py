import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_tile_fade_callback_150dfdd0_match as p
out=p.out;root=p.root
from tools.tests import game_tile_fade_callback_150dfdd0_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-selected.c').read_text(),'func_150DFDD0')
 controls={
  'active_gate':('fade->active != 0','fade->active == 0'),
  'state':('owner->state = 2','owner->state = 3'),
  'decrement':('fade->remaining -= D_800BE9A4','fade->remaining += D_800BE9A4'),
  'threshold':('fade->remaining < 0.0f','fade->remaining <= 0.0f'),
  'clear':('fade->active = 0','fade->active = 1'),
  'progress':('1.0f - fade->scale * fade->remaining','1.0f + fade->scale * fade->remaining'),
  'list_gate':('command != NULL','command != NULL && fade->active == 0'),
  'scan':('(command->word0 >> 24) != 0xF2','(command->word0 >> 24) != 0xE7'),
  'division':(' & 0xFFF) / 3',' & 0xFFF) / 2'),
  'wrap':('tileOffset += 64','tileOffset += 63'),
  'position':('500.0f * progress','499.0f * progress'),
  'mask':('(tileOffset & 0xFFF)','(tileOffset & 0xFFE)'),
  'result':('return 1;','return 0;'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u32 word0,word1;} TileCommand150DFDD0;
 typedef struct {TileCommand150DFDD0 *commands;} TileModel150DFDD0;
 typedef struct {u8 reserved00[0x13];u8 state;u8 reserved14[0x10];TileModel150DFDD0 *model;} TileOwner150DFDD0;
 typedef struct {u8 reserved00[0x2D8];f32 remaining,scale;u8 reserved2E0[0xC];s32 active;} TileFade150DFDD0;
 _Static_assert(__builtin_offsetof(TileOwner150DFDD0,state)==0x13 && __builtin_offsetof(TileOwner150DFDD0,model)==0x24 && __builtin_offsetof(TileFade150DFDD0,remaining)==0x2d8 && __builtin_offsetof(TileFade150DFDD0,active)==0x2ec,"layout");
 f32 D_800BE9A4;
 struct Case {s32 active;u32 remaining,tick,scale;s32 has_list,index,field,null_model;u32 out_remaining;s32 out_active,out_state,answer;u32 out_word;};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  m,answer=g.reference(c);v=[c.active,g.bits(c.remaining),g.bits(c.tick),g.bits(c.scale),c.has_list,c.index,c.field,c.null_model,g.read(m,g.FADE+0x2d8),g.read(m,g.FADE+0x2ec),m[g.OWNER+0x13],answer,g.read(m,g.COMMAND+8*c.index)]
  code+='{'+','.join('0x%Xu'%x if i in (1,2,3,8,12) else str(x) for i,x in enumerate(v))+'},\n'
 code+=r'''};
 static void put_bits(f32*dst,u32 x){u8*d=(u8*)dst,*s=(u8*)&x;u32 i;for(i=0;i<4;i++)d[i]=s[i];}
 static u32 get_bits(const f32*src){u32 x=0,i;u8*d=(u8*)&x;const u8*s=(const u8*)src;for(i=0;i<4;i++)d[i]=s[i];return x;}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_150DFDD0','test_'+key,1)+'\n'
 code+=r'''
 typedef s32(*T)(TileOwner150DFDD0*,TileFade150DFDD0*);
 static int check(T test,int control){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];TileOwner150DFDD0 owner;TileFade150DFDD0 fade;TileModel150DFDD0 model;TileCommand150DFDD0 cmds[8];u8 before_owner[sizeof owner],before_fade[sizeof fade];u8*o=(u8*)&owner,*f=(u8*)&fade;s32 answer;
  if(control&&c->null_model)continue;
  for(i=0;i<sizeof owner;i++)o[i]=(i*13+11)&255;for(i=0;i<sizeof fade;i++)f[i]=(i*13+11)&255;
  owner.model=c->null_model?NULL:&model;model.commands=c->has_list?cmds:NULL;put_bits(&fade.remaining,c->remaining);put_bits(&fade.scale,c->scale);fade.active=c->active;put_bits(&D_800BE9A4,c->tick);
  for(i=0;i<8;i++){cmds[i].word0=i==(u32)c->index?(0xf2000000u|((u32)c->field<<12)|0x765u):(0xe7000000u|(i<<12)|0x321u);cmds[i].word1=0x12345600u+i;}
  for(i=0;i<sizeof owner;i++)before_owner[i]=o[i];for(i=0;i<sizeof fade;i++)before_fade[i]=f[i];answer=test(&owner,&fade);
  if(answer!=c->answer||owner.state!=c->out_state||get_bits(&fade.remaining)!=c->out_remaining||fade.active!=c->out_active||get_bits(&D_800BE9A4)!=c->tick)return 1;
  for(i=0;i<8;i++){u32 expected=i==(u32)c->index?c->out_word:(0xe7000000u|(i<<12)|0x321u);if(cmds[i].word0!=expected||cmds[i].word1!=0x12345600u+i)return 2;}
  for(i=0;i<sizeof owner;i++)if(i!=0x13&&o[i]!=before_owner[i])return 3;
  for(i=0;i<sizeof fade;i++)if((i<0x2d8||i>=0x2dc)&&(i<0x2ec||i>=0x2f0)&&f[i]!=before_fade[i])return 4;
  }return 0;}
 static int run(void){int v=check(test_selected,0);if(v)return v;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+',1))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_150DFDD0_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_150DFDD0_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,valid_finite_inputs_and_terminated_lists=True,source_installed=False);(out/'native_150DFDD0_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
