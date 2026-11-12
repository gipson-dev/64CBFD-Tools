import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_motion_ring_integrator_151cd674_match as p
out=p.out;root=p.root
from tools.tests import game_motion_ring_integrator_151cd674_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
 selected=body((out/'independent-selected.c').read_text(),'func_151CD674')
 controls={
  'early_count':('owner->count < 2','owner->count < 1'),
  'early_flag':('owner->flags & 8','owner->flags & 4'),
  'position_velocity':('velocity * step +','velocity * step -'),
  'position_accel':('D_800AAFC4 * (step * step)','D_800AAFC4 * step'),
  'velocity_accel':('velocity + D_800AAFC0','velocity - D_800AAFC0'),
  'retirement':('entry->position < threshold','entry->position <= threshold'),
  'count_decrement':('owner->count - 1','owner->count - 2'),
  'clamp':('entries[current].position = limit->threshold','entries[current].position = 0'),
  'publish':('owner->output = owner->source','owner->output = owner->output'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct { s32 a,b,c; } ThreeWord1FA770;
 typedef struct {f32 retained00,position,retained08,velocity;u8 retained10[12];} MotionRingEntry151CD674;
 typedef struct {u8 retained00[0x44];f32 threshold;} MotionRingLimit151CD674;
 typedef struct {u8 retained00[0x10];ThreeWord1FA770 source;u8 retained1C[2];u16 flags;u8 retained20[5];u8 capacity;u8 retained26[6];s8 count,current,end;u8 retained2F[0x25];ThreeWord1FA770 output;u8 retained60[0x34];MotionRingEntry151CD674 *entries;MotionRingLimit151CD674 *limit;} MotionRingOwner151CD674;
 _Static_assert(sizeof(MotionRingEntry151CD674)==28 && __builtin_offsetof(MotionRingOwner151CD674,entries)==0x94 && __builtin_offsetof(MotionRingOwner151CD674,limit)==0x98 && __builtin_offsetof(MotionRingOwner151CD674,output)==0x54,"layout");
 f32 D_800BE9A4,D_800AAFC0,D_800AAFC4;
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_151CD674','test_'+key,1)+'\n'
 code+='''
 struct Case {s32 cap,current,end,count,flags,answer,final_count,final_current;u32 step,position,velocity,threshold,accel,half;u32 positions[7],velocities[7],output[3];};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  e,answer=g.reference(c)
  ints=[c.cap,c.current,c.end,c.count,c.flags,answer,g.s8(e[g.OWNER+0x2c]),g.s8(e[g.OWNER+0x2d])]
  floats=[g.bits(x)for x in (c.step,c.position,c.velocity,c.threshold,c.accel,c.half)]
  positions=[g.read(e,g.RECORDS+28*i+4)if i<c.cap else 0 for i in range(7)]
  velocities=[g.read(e,g.RECORDS+28*i+12)if i<c.cap else 0 for i in range(7)]
  output=[g.read(e,g.OWNER+0x54+4*i)for i in range(3)]
  code+='{'+','.join(map(str,ints))+','+','.join('0x%Xu'%v for v in floats)+',{'+','.join('0x%Xu'%v for v in positions)+'},{'+','.join('0x%Xu'%v for v in velocities)+'},{'+','.join('0x%Xu'%v for v in output)+'}},\n'
 initial=g.fixture(g.cases()[0])
 source=[g.read(initial,g.OWNER+0x10+4*i)for i in range(3)]
 initial_output=[g.read(initial,g.OWNER+0x54+4*i)for i in range(3)]
 code+='};\nstatic const u32 source_bits[3]={'+','.join('0x%Xu'%v for v in source)+'};\nstatic const u32 output_bits[3]={'+','.join('0x%Xu'%v for v in initial_output)+'};\n'
 code+=r'''
 typedef s32(*T)(MotionRingOwner151CD674*);
 static void put_bits(f32*dst,u32 x){u8*d=(u8*)dst,*s=(u8*)&x;u32 i;for(i=0;i<4;i++)d[i]=s[i];}
 static u32 get_bits(f32*src){u32 x=0,i;u8*d=(u8*)&x,*s=(u8*)src;for(i=0;i<4;i++)d[i]=s[i];return x;}
 static void put_word(s32*dst,u32 x){u8*d=(u8*)dst,*s=(u8*)&x;u32 i;for(i=0;i<4;i++)d[i]=s[i];}
 static u32 get_word(s32*src){u32 x=0,i;u8*d=(u8*)&x,*s=(u8*)src;for(i=0;i<4;i++)d[i]=s[i];return x;}
 static int check(T test){u32 n,i,j;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];MotionRingOwner151CD674 owner;MotionRingEntry151CD674 records[7];MotionRingLimit151CD674 limit;u8 owner_before[sizeof owner],record_before[sizeof records],limit_before[sizeof limit];u8*o=(u8*)&owner,*p=(u8*)records,*l=(u8*)&limit;u32 result;
  for(i=0;i<sizeof owner;i++)o[i]=(i*19+37)&255;for(i=0;i<sizeof records;i++)p[i]=(i*13+11)&255;for(i=0;i<sizeof limit;i++)l[i]=(i*7+9)&255;
  owner.flags=c->flags;owner.capacity=c->cap;owner.count=c->count;owner.current=c->current;owner.end=c->end;owner.entries=records;owner.limit=&limit;put_bits(&limit.threshold,c->threshold);put_bits(&D_800BE9A4,c->step);put_bits(&D_800AAFC0,c->accel);put_bits(&D_800AAFC4,c->half);
  put_word(&owner.source.a,source_bits[0]);put_word(&owner.source.b,source_bits[1]);put_word(&owner.source.c,source_bits[2]);
  put_word(&owner.output.a,output_bits[0]);put_word(&owner.output.b,output_bits[1]);put_word(&owner.output.c,output_bits[2]);
  for(i=0;i<(u32)c->cap;i++){put_bits(&records[i].position,c->position);records[i].position+=(f32)i;put_bits(&records[i].velocity,c->velocity);}
  for(i=0;i<sizeof owner;i++)owner_before[i]=o[i];for(i=0;i<sizeof records;i++)record_before[i]=p[i];for(i=0;i<sizeof limit;i++)limit_before[i]=l[i];result=test(&owner);
  if(result!=(u32)c->answer||owner.count!=c->final_count||owner.current!=c->final_current)return 1;
  if(get_word(&owner.output.a)!=c->output[0]||get_word(&owner.output.b)!=c->output[1]||get_word(&owner.output.c)!=c->output[2])return 2;
  for(i=0;i<(u32)c->cap;i++)if(get_bits(&records[i].position)!=c->positions[i]||get_bits(&records[i].velocity)!=c->velocities[i])return 3;
  for(i=0;i<sizeof owner;i++)if(i!=0x2c&&i!=0x2d&&(i<0x54||i>=0x60)&&o[i]!=owner_before[i])return 4;
  for(i=0;i<sizeof records;i++){j=i%28;if((i/28>=(u32)c->cap||((j<4||j>=8)&&(j<12||j>=16)))&&p[i]!=record_before[i])return 5;}
  for(i=0;i<sizeof limit;i++)if(l[i]!=limit_before[i])return 6;
  }return 0;}
 static int run(void){int selected_result=check(test_selected);if(selected_result)return selected_result;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_151CD674_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_151CD674_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,valid_finite_disjoint_ring_storage=True,source_installed=False);(out/'native_151CD674_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
