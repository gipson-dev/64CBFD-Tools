import itertools,json,subprocess,sys
from pathlib import Path
from tools.experiments import game_sorted_record_insert_150241b4_match as p
out=p.out;root=p.root
from tools.tests import game_sorted_record_insert_150241b4_oracle as g
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=body((out/'independent-nounroll.c').read_text(),'func_150241B4')
 controls={
  'capacity':('size >= D_800C3C9A','size > D_800C3C9A'),
  'stable_order':('entries[i].unk4 >= priority','entries[i].unk4 > priority'),
  'shift_fields':('entries[i + 1] = entries[i]','entries[i + 1].unk4 = entries[i].unk4'),
  'shift_start':('i >= index','i > index'),
  'tag':('entries[index].unk8 = tag','entries[index].unk8 = parameter'),
  'parameter':('entries[index].unkA = parameter','entries[index].unkA = tag'),
  'priority':('entries[index].unk4 = priority','entries[index].unk4 = value'),
  'helper_arg':('func_15024130(size, context)','func_15024130(size, value)'),
  'reset':('*count = 0','*count = 1'),
  'increment':('*count = *count + 1','*count = *count + 2'),
  'value':('entries[index].unk0 = value','entries[index].unk0 = context'),
 }
 code=r'''#include <ultra64.h>
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {s32 unk0,unk4;u8 unk8,pad9;u16 unkA;} Struct15024130;
 _Static_assert(sizeof(Struct15024130)==12,"record layout");
 u16 D_800C3C9A;static s32 helper_count,helper_context,helper_calls,do_mutation;static s32 *active_count;static Struct15024130 *active_entries;
 void func_15024130(s32 count,s32 context){helper_count=count;helper_context=context;helper_calls++;if(do_mutation){active_entries[0].unk4=0x12345678;*active_count=99;}}
 '''
 for key,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if key!='selected':assert text!=selected,key
  code+='\n'+text.replace('func_150241B4','test_'+key,1)+'\n'
 code+='''
 struct Case {s32 size,cap,priority,tag,parameter,pattern,mutate,expected_count,expected_calls;Struct15024130 expected[10];};
 static const struct Case cases[]={
 '''
 cases=g.cases()
 for c in cases:
  m,calls=g.reference(c);records=[]
  for i in range(10):
   p=g.TABLE+12*i;records.append('{0x%Xu,0x%Xu,%u,%u,%u}'%(g.read(m,p),g.read(m,p+4),m[p+8],m[p+9],g.read(m,p+10,2)))
  parameter=c.parameter if c.parameter<0x80000000 else c.parameter-0x100000000
  code+='{'+','.join(map(str,(c.size,c.capacity,c.priority,c.tag,parameter,c.pattern,c.mutate,g.read(m,g.COUNT),len(calls))))+',{'+','.join(records)+'}},\n'
 code+=r'''};
 typedef void(*T)(Struct15024130*,s32*,s32,s32,s32,s32,s32);
 static int check(T test){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];Struct15024130 entries[10];s32 count=c->size;
  for(i=0;i<10;i++){static const s32 duplicates[10]={-4,-4,-1,-1,0,0,7,7,10,10};entries[i].unk0=0x12000000+i;entries[i].unk4=c->pattern==0?(s32)i*3-9:(c->pattern==1?0:duplicates[i]);entries[i].unk8=(i*17+3)&255;entries[i].pad9=0xA5;entries[i].unkA=0x8000+i;}
  D_800C3C9A=c->cap;helper_calls=0;helper_count=helper_context=0;do_mutation=c->mutate;active_entries=entries;active_count=&count;test(entries,&count,0x89abcdef,c->tag,c->parameter,c->priority,0x13572468);
  if(count!=c->expected_count||helper_calls!=c->expected_calls)return 1;
  if(helper_calls&&(helper_count!=c->size||helper_context!=0x13572468))return 2;
  for(i=0;i<10;i++)if(entries[i].unk0!=c->expected[i].unk0||entries[i].unk4!=c->expected[i].unk4||entries[i].unk8!=c->expected[i].unk8||entries[i].pad9!=c->expected[i].pad9||entries[i].unkA!=c->expected[i].unkA)return 3;
  }return 0;}
 static int run(void){int v=check(test_selected);if(v)return v;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=out/'native_150241B4_screen.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native_150241B4_screen'+opt);v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
  v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(cases),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,valid_disjoint_sorted_storage=True,source_installed=False);(out/'native_150241B4_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
