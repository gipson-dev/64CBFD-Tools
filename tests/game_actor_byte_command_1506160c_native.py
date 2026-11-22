"""SDK32 record/union layout, native C domain and independent source controls."""
from pathlib import Path
import itertools,json,subprocess,sys
from tools.experiments import game_actor_byte_command_1506160c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_actor_byte_command_1506160c_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
BODY=packet.MANIFEST['body']
PRE=r'''#include <ultra64.h>
#include "structs.h"
#include "actor_commands.h"
#define OFF __builtin_offsetof
typedef char layout[sizeof(void*)==4&&sizeof(struct127)==0x32C&&OFF(struct127,unk7)==7&&OFF(struct127,unkE.ub[1])==15&&OFF(struct127,pad2FC)==0x2FC&&sizeof(ActorCommandGates)==4&&OFF(ActorCommandGates,word)==0&&OFF(ActorCommandGates,bytes)==0&&__alignof__(ActorCommandGates)==4?1:-1];
ActorCommandGates D_800DBFF4;
'''
HARNESS=r'''
static struct127 actor;
static int run(void){u32 row,i;for(row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
 const Row*r=&rows[row];for(i=0;i<sizeof(actor);i++)((u8*)&actor)[i]=(u8)(i*19+0xA5);
 actor.unkA=(u8)r->priority;actor.unkE.ub[1]=(u8)r->flags;actor.pad2FC[1]=(u8)r->forced;
 for(i=0;i<4;i++)D_800DBFF4.bytes[i]=(u8)r->gates[i];
 func_1506160C(&actor,r->command,r->first,r->second,r->slot);
 for(i=0;i<sizeof(actor);i++){
  u8 expected=i>=7&&i<=15?(u8)r->expected[i-7]:i==0x2FD?(u8)r->forced:(u8)(i*19+0xA5);
  if(((u8*)&actor)[i]!=expected)return 1;
 }
 for(i=0;i<4;i++)if(D_800DBFF4.bytes[i]!=(u8)r->gates[i])return 2;
 }return 0;}
'''
def vectors():
 cases=[]
 for command,slot in itertools.product(range(256),range(4)):
  cases.append(g.Case(command=command,slot=slot,priority=(command*17+slot*31)&255,flags=(command*19+slot)&255,
   forced=(command+slot)&1,gates=tuple(int(i==(command+slot)%4)for i in range(4))))
 for command,flags in itertools.product((8,9,10),range(256)):
  cases.append(g.Case(command=command,slot=flags%4,flags=flags,forced=flags&1))
 for command,priority in itertools.product(range(8),range(256)):
  cases.append(g.Case(command=command,slot=255,priority=priority,gates=(0,0,0,priority&1)))
 for command,first,second,slot in itertools.product((0xFFFFFF08,0x12340002,0x8000000A),(0x123456AB,0xFFFFFFFF),(0x876543CD,0x80000000),(0,3)):
  cases.append(g.Case(command=command,first=first,second=second,slot=slot,forced=1))
 def arr(v):return'{'+','.join('0x%Xu'%g.u32(x)for x in v)+'}'
 rows=[]
 for c in cases:
  m=g.check(g.streams()[1],c);expected=g.reference(m.initial,c);assert g.public(expected)==g.public(m.memory)
  rows.append('{%s,%s,%s}'%(','.join('0x%Xu'%g.u32(x)for x in(c.command,c.first,c.second,c.slot,c.priority,c.flags,c.forced)),arr(c.gates),arr(expected[g.ACTOR+i]for i in range(7,16))))
 text='typedef struct{u32 command,first,second,slot,priority,flags,forced,gates[4],expected[9];}Row;\nstatic const Row rows[]={'+','.join(rows)+'};\n'
 (out/'native-vectors.h').write_text(text);return len(cases)
def main():
 count=vectors();controls={
  'reject-equal-priority':BODY.replace('value < actor->unkA','value <= actor->unkA'),
  'wrong-aggregate-gate':BODY.replace('if (D_800DBFF4.word)','if (D_800DBFF4.bytes[0])'),
  'wrong-slot-gate':BODY.replace('D_800DBFF4.bytes[value]','D_800DBFF4.bytes[(value+1)&3]'),
  'wrong-force-condition':BODY.replace('actor->pad2FC[1] ||','actor->pad2FC[1] &&'),
  'wrong-high-mask':BODY.replace('mask << 4','mask << 3'),
  'wrong-selected-byte':BODY.replace('0xB + value','0xC + value'),
  'wrong-command4-default':BODY.replace('actor->unk8 = 255','actor->unk8 = 254'),
  'wrong-command6-step':BODY.replace('actor->unk9 = 8','actor->unk9 = 9'),
  'wrong-command8-reset':BODY.replace('                first = 0;','                first = 1;',1),
  'wide-command-argument':BODY.replace('u8 command','u16 command')}
 profiles={};effective=[]
 for name,body,opt in [('O0',BODY,'-O0'),('O2',BODY,'-O2'),('O3',BODY,'-O3')]+[(n,b,'-O2')for n,b in controls.items()]:
  if name in controls:assert body!=BODY,name
  path=out/('native-'+name+'.c');exe=path.with_suffix('.exe');path.write_text(PRE+'\n'+body+'\n#include "native-vectors.h"\n'+HARNESS+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
  command=native_command(opt);command[1:1]=['-I',str(out/'proposal/conker/include')]
  q=subprocess.run(command+['-fstrict-aliasing',str(path),'-o',str(exe)],capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,text=True)
  if name in controls:assert q.returncode!=0,name;effective.append(name)
  else:assert q.returncode==0 and not q.stdout and not q.stderr,(name,q.returncode,q.stderr);profiles[name]=dict(cases=count,SDK_layout=True,strict_aliasing=True,UBSan=True)
 r=dict(profiles=profiles,effective_source_controls=effective,complete_actor_and_gate_canaries=True,
  actual_union_byte_and_word_views=True,native_domain='High commands:slot0..3; low commands:any byte slot. Guest-only surrounding RDRAM accesses are excluded.',source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
