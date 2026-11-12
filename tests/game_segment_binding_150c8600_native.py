import json,subprocess,sys
from pathlib import Path
from tools.experiments import game_segment_binding_150c8600_match as p
out=p.out;root=p.root
from tools.tests import game_segment_binding_150c8600_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 source=(out/'independent-selected.c').read_text();start=source.index('Gfx *func_150C8600(');selected=source[start:source.index('\n}',start)+2]
 controls={
  'choice_shift':('entry->choice >> 8','entry->choice >> 7'),
  'low_clamp':('if (choice < 0) choice = 0','if (choice < 0) choice = 1'),
  'high_clamp':('if (choice >= 5) choice = 4','if (choice >= 5) choice = 3'),
  'group_gate':('entry->group >= 2','entry->group >= 1'),
  'group_reset':('entry->group = 0','entry->group = 1'),
  'dynamic_groups':('groups[entry->group][choice]','(index == 0 ? groups[entry->group][choice] : D_80088810[entry->group][choice])'),
  'choice_index':('groups[entry->group][choice]','groups[entry->group][0]'),
  'count':('index < 10','index < 9'),
  'mode':('&extent, 3, 0','&extent, 2, 0'),
  'segment':('index + 1, address','index + 2, address'),
  'address':('index + 1, address','index + 1, address ^ 1'),
  'return':('return cursor;','return cursor - 1;'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u8 group,reserved01;s8 marker;u8 reserved03;s16 choice,previous,next;} SegmentEntry150C8600;
 _Static_assert(sizeof(SegmentEntry150C8600)==10 && __builtin_offsetof(SegmentEntry150C8600,choice)==4,"entry layout");
 s32 D_800BE4E0;static s32 group0[5],group1[5];s32 *D_80088810[2];static SegmentEntry150C8600 A[10],B[10];
 struct Case {s32 choice,pattern,switch_at,swap_tables;u8 groups_a[10],groups_b[10];u32 resources[10],words[20];s32 expected_b;};
 static const struct Case cases[]={
 '''
 for c in g.cases():
  m,calls,_=g.reference(c);vals=[c.choice,c.pattern,c.switch,c.swap_tables];ga=[m[g.A+10*i]for i in range(10)];gb=[m[g.B+10*i]for i in range(10)];resources=[x[0]for x in calls];words=[g.read(m,g.CURSOR+4*i)for i in range(20)];arr=lambda xs:'{'+','.join('0x%Xu'%v for v in xs)+'}'
  code+='{'+','.join(map(str,vals))+','+arr(ga)+','+arr(gb)+','+arr(resources)+','+arr(words)+','+str(int(g.read(m,g.RECORDS)==g.B))+'},\n'
 code+=r'''};
 static const struct Case *current;static s32 calls,bad;
 u32 func_1510D0EC(s32 resource,s32 *extent,s32 mode,s32 flags){s32 i=calls++;if(i>=10||!extent||mode!=3||flags!=0){bad=1;return 0;}if((u32)resource!=current->resources[i])bad=1;*extent=0x12340000+i;if(i==current->switch_at)D_800BE4E0=(s32)B;if(i==0&&current->swap_tables){D_80088810[0]=group1;D_80088810[1]=group0;}return 0xa0000000u|(((u32)resource&0xffff)<<4)|((u32)i&15);}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1) for n,(a,b) in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_150C8600','test_'+key,1)+'\n'
 code+=r'''
 typedef Gfx*(*T)(Gfx*);
 static int check(T test){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];Gfx output[12],*end;u8 before_a[sizeof A],before_b[sizeof B];u8*a=(u8*)A,*b=(u8*)B;
  for(i=0;i<sizeof A;i++){a[i]=(i*13+11)&255;b[i]=(i*13+11)&255;}
  for(i=0;i<5;i++){group0[i]=0x100+i;group1[i]=0x200+i;}D_80088810[0]=group0;D_80088810[1]=group1;D_800BE4E0=(s32)A;
  for(i=0;i<10;i++){u8 x=(i+c->pattern)%4,y=(i+c->pattern+1)%4;A[i].group=x==3?255:x;B[i].group=y==3?255:y;A[i].choice=B[i].choice=c->choice;}
  for(i=0;i<sizeof A;i++){before_a[i]=a[i];before_b[i]=b[i];}for(i=0;i<12;i++){output[i].words.w0=0xaaaaaaaa;output[i].words.w1=0xbbbbbbbb;}
  current=c;calls=bad=0;end=test(output);if(bad||calls!=10||end!=output+10||D_800BE4E0!=(s32)(c->expected_b?B:A))return 1;
  if(D_80088810[0]!=(c->swap_tables?group1:group0)||D_80088810[1]!=(c->swap_tables?group0:group1))return 2;
  for(i=0;i<10;i++)if(A[i].group!=c->groups_a[i]||B[i].group!=c->groups_b[i]||output[i].words.w0!=c->words[2*i]||output[i].words.w1!=c->words[2*i+1])return 3;
  for(i=0;i<sizeof A;i++)if(i%10!=0&&(a[i]!=before_a[i]||b[i]!=before_b[i]))return 4;
  for(i=10;i<12;i++)if(output[i].words.w0!=0xaaaaaaaa||output[i].words.w1!=0xbbbbbbbb)return 5;
  }return 0;}
 static int run(void){int v=check(test_selected);if(v)return v;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_150C8600_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_150C8600_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(g.cases()),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helper='modeled with record and table-pointer mutations',valid_disjoint_records_and_output=True,source_installed=False);(out/'native_150C8600_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
