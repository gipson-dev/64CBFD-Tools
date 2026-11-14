from pathlib import Path
import importlib.util,sys,json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();out=r/'conker/build/game-group-event-choice-15023264-screen'
from tools.tests import game_group_event_choice_15023264_behavior as b
selected=(out/'selected.c').read_text();start=selected.index('/* Select the closest command event');end=selected.index('void func_150233BC',start);body=selected[start:end]
bad={
 'tie_break':body.replace('score < best','score <= best'),
 'missing_event_value':body.replace('(u8 *)event + 2','(u8 *)event + 4'),
 'wrong_default':body.replace('*(u16 *)commands == 1','*(u16 *)commands == 2'),
 'wrong_initial_best':body.replace('best = 99999','best = 99998'),
 'wrong_fallback':body.replace('        selected = 0;','        selected = 1;'),
 'wrong_loop_count':body.replace('            liveCount = D_800C363A[group];','            liveCount = 0;')
}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==len(bad)
code=r'''#include <ultra64.h>
typedef struct {u8 padding[0x14];} RecordMaximum49D30;
typedef struct {u8 padding[8];} SequenceEvent49D30;
u8 D_800C363A[2];RecordMaximum49D30 *D_800C3688[2][30];u8 *D_800C35F0[2];
s32 func_15023BB0(u8 *,s32,s32,SequenceEvent49D30 **,s32,s32,s32,s32,s32,s32,s32);
'''
code+='\n'.join(v.replace('func_15023264','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+=r'''
typedef union {u32 align;u8 bytes[256];} Storage;
typedef struct {s32 group,count,present,events,defaults,mutation;s32 scores[6];s32 values[6];s32 expected,calls;} Case;
static const Case cases[]={
'''
rows=[]
for c in b.corpus():
 _,calls,result=b.reference(b.fixture(c),c)
 rows.append('{%d,%d,%d,%d,%d,%d,{%s},{%s},0x%Xu,%d}'%(c.group,c.count,c.present,c.events,c.defaults,c.mutation,','.join(str(x) for x in c.scores),','.join(str(x) for x in c.values),result,len(calls)))
code+=',\n'.join(rows)+'\n};\n'
code+=r'''
static Storage records[2][6],events[2][6],defaults[2];static const Case *current;static s32 calls,error;
s32 func_15023BB0(u8 *commands,s32 kind,s32 index,SequenceEvent49D30 **out,s32 a,s32 d,s32 e,s32 f,s32 g,s32 h,s32 group){
 if(index<0||index>=6||commands!=records[group][index].bytes+0x18||group!=current->group||kind!=3||a||d||e||f||g||h)error=1;
 *out=(current->events&(1<<index))?(SequenceEvent49D30*)events[group][index].bytes:NULL;
 if(current->mutation==1&&index==0)D_800C363A[group]=1;
 if(current->mutation==2&&index==0)D_800C363A[group]=6;
 if(current->mutation==3&&index==1)D_800C363A[group]=0;
 calls++;return current->scores[index];
}
typedef s32 (*Candidate)(s32,s32);
'''
code+='static Candidate candidates[]={'+','.join('candidate_'+str(i) for i in range(len(bad)+1))+'};\n'
code+=r'''
static int run(void){u32 i,j,k,g,killed=0;int got;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;
  for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
   for(g=0;g<2;g++){D_800C363A[g]=g==(u32)current->group?current->count:0;D_800C35F0[g]=defaults[g].bytes;
    for(k=0;k<6;k++){
     D_800C3688[g][k]=(current->present&(1<<k))?(RecordMaximum49D30*)records[g][k].bytes:NULL;
     *(u16*)(defaults[g].bytes+8*k)=(current->defaults&(1<<k))?1:2;
     *(s16*)(events[g][k].bytes+2)=current->values[k];*(s16*)(events[g][k].bytes+4)=0;
    }
   }
   error=calls=0;got=candidates[j](current->group,0x12345678);
   if(got!=current->expected||calls!=current->calls)error=1;
   if(error){if(j==0)return 10;killed|=1u<<(j-1);}
  }
 }
 return killed==63u?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
p=out/'native-choice.c';p.write_text(code);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=out/('native-choice'+opt+alias);q=subprocess.run(native_command(opt)+[alias,'-o',str(exe),str(p)],cwd=r,capture_output=True,text=True)
  assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(exe)],cwd=r,capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr)
  profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,modeled_parser=True)
(out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
