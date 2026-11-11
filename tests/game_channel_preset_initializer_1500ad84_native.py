import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_channel_preset_initializer_1500ad84_match as p
out=p.out;root=p.root
from tools.tests import game_channel_preset_initializer_1500ad84_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'selected-source.c').read_text(),'func_1500AD84')
 controls={'sentinel':('preset != 255','preset != 254'),'dec_flag':('options & 0x10','options & 0x20'),'decrement':('value--','value -= 2'),'mode_flag':('options & 0x80) ? 2 : 1','options & 0x80) ? 1 : 2'),'field_a':('entry->first','entry->second'),'field_b':('entry->second','entry->first'),'option_mask':('savedOptions & 0x7F','savedOptions & 0x3F'),'set_options_bit':('savedOptions & 0x80','savedOptions & 0x40'),'flag_one':('options & 1','options & 2'),'flag_eight':('options & 8','options & 4'),'pair':('D_800DDC20[slot * 2 + 1] = base','D_800DDC20[slot * 2 + 1] = base + 1'),'clear':('D_800BE478[slot] = 0','D_800BE478[slot] = 1')}
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u8 flags,value;u8 padding[2];s16 first,second;u8 tail[2];} ChannelPreset36680;
 ChannelPreset36680 D_80095CE0[256];u8 D_800DDBD0[16],D_800DDBE0[16],D_800DDBF0[16],D_800DDBC0[16],D_800DDC80[16],D_80095CC4[16],D_800DDC20[32];s16 D_800BE438[16][2],D_800BE478[16];s32 D_800DDC00,D_800DDC04,D_800DDC08;
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_1500AD84','test_'+key,1)+'\n'
 code+='''\nstruct Case {u32 slot,preset,flags,options,value,seed,a,b,c,key,opt,first,second,zero,pair0,pair1,mask0,mask1,mask2;};\nstatic const struct Case cases[]={\n'''
 for c in g.cases():
  e=g.reference(c,g.fixture(c));vals=[c.slot,c.preset,c.flags,c.options,c.value,c.seed,e[g.A+c.slot],e[g.B+c.slot],e[g.C+c.slot],e[g.KEY+c.slot],e[g.OPT+c.slot],g.read(e,g.VALUES+4*c.slot,2),g.read(e,g.VALUES+4*c.slot+2,2),g.read(e,g.ZERO+2*c.slot,2),e[g.PAIRS+2*c.slot],e[g.PAIRS+2*c.slot+1]]+[g.read(e,a)for a in g.MASKS];code+='{'+','.join(str(v)+'u'for v in vals)+'},\n'
 code+=r'''};
 typedef void(*T)(s32,u32,u32);
 static u8 pat(unsigned i,unsigned seed){return (i*19+seed*11+37)&255;}
 static u16 half(unsigned i,unsigned seed){return (u16)((pat(i,seed)<<8)|pat(i+1,seed));}
 static u32 word(unsigned seed){return ((u32)pat(0,seed)<<24)|((u32)pat(1,seed)<<16)|((u32)pat(2,seed)<<8)|pat(3,seed);}
 static int check(T test){unsigned n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];unsigned slot=c->slot;u32 w=word(c->seed);
  for(i=0;i<16;i++){D_800DDBD0[i]=D_800DDBE0[i]=D_800DDBF0[i]=D_800DDBC0[i]=D_800DDC80[i]=D_80095CC4[i]=pat(i,c->seed);D_800BE438[i][0]=half(4*i,c->seed);D_800BE438[i][1]=half(4*i+2,c->seed);D_800BE478[i]=half(2*i,c->seed);}
  for(i=0;i<32;i++)D_800DDC20[i]=pat(i,c->seed);D_800DDC00=D_800DDC04=D_800DDC08=w;
  D_80095CE0[c->preset].flags=c->flags;D_80095CE0[c->preset].value=c->value;D_80095CE0[c->preset].first=-12345;D_80095CE0[c->preset].second=23456;
  test(slot,c->preset,c->options);
  if(D_800DDBD0[slot]!=c->a||D_800DDBE0[slot]!=c->b||D_800DDBF0[slot]!=c->c||D_800DDBC0[slot]!=c->key||D_800DDC80[slot]!=c->opt||(u16)D_800BE438[slot][0]!=c->first||(u16)D_800BE438[slot][1]!=c->second||(u16)D_800BE478[slot]!=c->zero||D_800DDC20[slot*2]!=c->pair0||D_800DDC20[slot*2+1]!=c->pair1||(u32)D_800DDC00!=c->mask0||(u32)D_800DDC04!=c->mask1||(u32)D_800DDC08!=c->mask2)return 1;
  for(i=0;i<16;i++)if(i!=slot&&(D_800DDBD0[i]!=pat(i,c->seed)||D_800DDBE0[i]!=pat(i,c->seed)||D_800DDBF0[i]!=pat(i,c->seed)||D_800DDBC0[i]!=pat(i,c->seed)||D_800DDC80[i]!=pat(i,c->seed)||(u16)D_800BE438[i][0]!=half(4*i,c->seed)||(u16)D_800BE438[i][1]!=half(4*i+2,c->seed)||(u16)D_800BE478[i]!=half(2*i,c->seed)||D_800DDC20[2*i]!=pat(2*i,c->seed)||D_800DDC20[2*i+1]!=pat(2*i+1,c->seed)))return 2;
  }return 0;}
 static int run(void){if(check(test_selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native-screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native-screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,synthetic_256_record_backing=True,slot_range=(0,14),source_installed=False);(out/'native-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
