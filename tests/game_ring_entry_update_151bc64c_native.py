import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_ring_entry_update_151bc64c_match as p
out=p.out;root=p.root
from tools.tests import game_ring_entry_update_151bc64c_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-selected.c').read_text(),'func_151BC64C')
 controls={
  'early_count':('count < 2','count < 1'),
  'early_flag':('owner->flags & 8','owner->flags & 4'),
  'expiry':('timer < 0','timer <= 0'),
  'fade_gate':('timer < 10','timer < 9'),
  'fade_scale':('timer * 25','timer * 24'),
  'tick_direction':(' - (u32)D_800BE9E4',' + (u32)D_800BE9E4'),
  'count_decrement':('owner->count - 1','owner->count - 2'),
  'publish_gate':('owner->count > 0','owner->count >= 0'),
  'publish_source':('entries[current].values','entries[0].values'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct { f32 first,second,third; } RingValues151BC64C;
 typedef struct { RingValues151BC64C values;s16 timer;u8 fade,retained0F;u32 retained10; } RingEntry151BC64C;
 typedef struct {u8 retained00[0x1E];u16 flags;u8 retained20[5];u8 capacity;u8 retained26[6];s8 count,current,end;u8 retained2F[0x25];RingValues151BC64C output;u8 retained60[0x34];RingEntry151BC64C *entries;} RingOwner151BC64C;
 _Static_assert(sizeof(RingEntry151BC64C)==20 && __builtin_offsetof(RingOwner151BC64C,entries)==0x94 && __builtin_offsetof(RingOwner151BC64C,output)==0x54,"layout");
 s32 D_800BE9E4;
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_151BC64C','test_'+key,1)+'\n'
 code+='''
 struct Case {s32 cap,current,end,count,flags,timer,tick,answer,final_count,final_current; s16 timers[7];u8 fades[7];u32 output[3];};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  e,answer=g.reference(c);initial=g.fixture(c)
  timers=[g.s16(g.read(e,g.RECORDS+20*i+12,2))if i<c.cap else 0 for i in range(7)]
  fades=[e[g.RECORDS+20*i+14]if i<c.cap else 0 for i in range(7)]
  vals=[c.cap,c.current,c.end,c.count,c.flags,c.timer,c.tick,answer,g.s8(e[g.OWNER+0x2c]),g.s8(e[g.OWNER+0x2d])]
  output=[g.read(e,g.OWNER+0x54+4*i)for i in range(3)]
  code+='{'+','.join(map(str,vals))+',{'+','.join(map(str,timers))+'},{'+','.join(map(str,fades))+'},{'+','.join('0x%Xu'%v for v in output)+'}},\n'
 initial=g.fixture(g.Case(7,0,0,0,0,0,0));values=[g.read(initial,g.RECORDS+20*i+4*j)for i in range(7)for j in range(3)];initial_output=[g.read(initial,g.OWNER+0x54+4*i)for i in range(3)]
 code+='};\nstatic const u32 initial_values[21]={'+','.join('0x%Xu'%v for v in values)+'};\nstatic const u32 initial_output[3]={'+','.join('0x%Xu'%v for v in initial_output)+'};\n'
 code+=r'''
 typedef s32(*T)(RingOwner151BC64C*);
 static void put_bits(f32*dst,u32 x){u8*d=(u8*)dst,*s=(u8*)&x;u32 i;for(i=0;i<4;i++)d[i]=s[i];}
 static u32 get_bits(f32*src){u32 x=0,i;u8*d=(u8*)&x,*s=(u8*)src;for(i=0;i<4;i++)d[i]=s[i];return x;}
 static int check(T test){u32 n,i,j;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];RingOwner151BC64C owner;RingEntry151BC64C records[7];u8 owner_before[sizeof owner],record_before[sizeof records];u8*o=(u8*)&owner,*p=(u8*)records;u32 result;
  for(i=0;i<sizeof owner;i++)o[i]=(i*19+37)&255;for(i=0;i<sizeof records;i++)p[i]=(i*13+11)&255;
  owner.flags=c->flags;owner.capacity=c->cap;owner.count=c->count;owner.current=c->current;owner.end=c->end;owner.entries=records;put_bits(&owner.output.first,initial_output[0]);put_bits(&owner.output.second,initial_output[1]);put_bits(&owner.output.third,initial_output[2]);
  for(i=0;i<7;i++){put_bits(&records[i].values.first,initial_values[3*i]);put_bits(&records[i].values.second,initial_values[3*i+1]);put_bits(&records[i].values.third,initial_values[3*i+2]);}
  for(i=0;i<(u32)c->cap;i++){records[i].timer=c->timer;records[i].fade=(i*42+33)&255;}
  for(i=0;i<sizeof owner;i++)owner_before[i]=o[i];for(i=0;i<sizeof records;i++)record_before[i]=p[i];D_800BE9E4=c->tick;result=test(&owner);
  if(result!=(u32)c->answer||owner.count!=c->final_count||owner.current!=c->final_current)return 1;
  if(get_bits(&owner.output.first)!=c->output[0]||get_bits(&owner.output.second)!=c->output[1]||get_bits(&owner.output.third)!=c->output[2])return 2;
  for(i=0;i<(u32)c->cap;i++)if(records[i].timer!=c->timers[i]||records[i].fade!=c->fades[i])return 3;
  for(i=0;i<sizeof owner;i++)if(i!=0x2c&&i!=0x2d&&(i<0x54||i>=0x60)&&o[i]!=owner_before[i])return 4;
  for(i=0;i<sizeof records;i++){j=i%20;if((i/20>=(u32)c->cap||(j!=12&&j!=13&&j!=14))&&p[i]!=record_before[i])return 5;}
  }return 0;}
 static int run(void){int selected_result=check(test_selected);if(selected_result)return selected_result;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_151BC64C_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_151BC64C_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,valid_disjoint_ring_storage=True,source_installed=False);(out/'native_151BC64C_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
