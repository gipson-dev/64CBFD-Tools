"""Native32 actor-ID lookup, complete table immutability and seven controls."""
from pathlib import Path
import json,subprocess
from tools.tests.game_active_actor_id_lookup_oracle import cases
r=o=None
import sys
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
q=sys.modules[__name__]
def native_harness(selected):
 pre='#include <ultra64.h>\ntypedef s8 int8_t;\ntypedef struct {s32 interaction_state;u8 id;u8 alternate;u8 tail[0x326];} struct127;\n_Static_assert(sizeof(void*)==4,"native32");\n_Static_assert(sizeof(struct127)==0x32C,"stride");\n_Static_assert(__builtin_offsetof(struct127,id)==4,"id");\nstruct127 D_800CC2D0[26];\nstatic void fill(void*p,u8 value,u32 n){u8*b=p;u32 i;for(i=0;i<n;i++)b[i]=value;}\nstatic void copy(void*p,const void*q,u32 n){u8*b=p;const u8*a=q;u32 i;for(i=0;i<n;i++)b[i]=a[i];}\nstatic int different(const void*p,const void*q,u32 n){const u8*b=p,*a=q;u32 i;for(i=0;i<n;i++)if(b[i]!=a[i])return 1;return 0;}\n'
 rows=['{%d,%d,%d,0x%Xu,%d}'%(c.key,c.slot,c.second,c.state,c.pattern)for c in q.cases()]
 return pre+'\n'+selected+'\n'+'''
static struct { s32 key,slot,second; u32 state; int pattern; } cases[]={
'''+',\n'.join(rows)+r'''};
static int run(void) {
 unsigned n; int i,j; struct127 before[26]; struct127 *expected,*result;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++) {
  fill(D_800CC2D0,0xA5,sizeof(D_800CC2D0));
  for(i=0;i<26;i++) {D_800CC2D0[i].interaction_state=cases[n].pattern ? 1 : 0;D_800CC2D0[i].id=(u8)(cases[n].key+1u);D_800CC2D0[i].alternate=(u8)(cases[n].key+2u);}
  for(j=0;j<2;j++) {i=j ? cases[n].second : cases[n].slot;if(i>=0) {D_800CC2D0[i].interaction_state=(s32)cases[n].state;D_800CC2D0[i].id=(u8)cases[n].key;}}
  expected=NULL;for(i=0;i<25;i++)if(D_800CC2D0[i].interaction_state && (s32)D_800CC2D0[i].id==cases[n].key) {expected=&D_800CC2D0[i];break;}
  copy(before,D_800CC2D0,sizeof(before));result=func_1505F0AC(cases[n].key);
  if(result!=expected || different(before,D_800CC2D0,sizeof(before))) return 1;
 }
 return 0;
}
'''

def controls(selected):
 return {
 'reserved-slot':selected.replace('index < 25','index < 26'),
 'skip-first-slot':selected.replace('actor = D_800CC2D0','actor = D_800CC2D0 + 1').replace('index = 0','index = 1'),
 'ignore-active-word':selected.replace('actor->interaction_state != 0','1'),
 'signed-key-byte':selected.replace('actor->id == id','(int8_t)actor->id == id'),
 'narrow-key-argument':selected.replace('s32 id','u8 id'),
 'wrong-key-field':selected.replace('actor->id','actor->alternate'),
 'always-null':selected.replace('return actor;','return NULL;')}

def run_native(selected):
 report={};bad=controls(selected)
 for label,source in [('selected',selected),*bad.items()]:
  assert label=='selected'or source!=selected,label
  for profile in (('O0','O2','O3')if label=='selected'else('O2',)):
   p=o/('native-'+label+'-'+profile);p.with_suffix('.c').write_text(native_harness(source)+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'));command=native_command('-'+profile)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)];result=subprocess.run(command,capture_output=True,text=True);assert result.returncode==0 and not result.stdout and not result.stderr,result.stderr
   run=subprocess.run([str(p)],capture_output=True,text=True);assert run.returncode==(0 if label=='selected'else 1),(label,run.returncode,run.stdout,run.stderr);assert 'runtime error:'not in run.stderr
   report[label+'-'+profile]=dict(exit=run.returncode,stdout=run.stdout,stderr=run.stderr)
 return dict(cases=len(q.cases()),profiles=report,negative_controls=len(bad),UBSan=True)


def qualify(root,output,selected):
 global r,o
 r,o=root,output
 report=run_native(selected)
 (o/'private-native-runtime.json').write_text(json.dumps(report,indent=2)+'\n')
 return report
