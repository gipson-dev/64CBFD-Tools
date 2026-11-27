"""Literal classifier streams, ordered independent reference, aliases and cuts."""
from tools.experiments import game_owner_action_classifier_1514ca80_match as target_packet
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,sys
sys.path.insert(0,str(target_packet.ROOT))
from tools.tests import game_owner_action_dispatch_1514d15c_guest as g
from tools.tests.game_owner_action_dispatch_1514d15c_classifier_abi import at
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
r=target_packet.ROOT;o=target_packet.OUT;ENTRY=0x1514CA80;LEVEL=0x800BE9F0;OUTPUT=0xB0000;fn='func_1514CA80'
THIRD={94:25,154:24,16:23,46:23,127:22,153:21,137:20,186:20,173:17,134:18,82:19,95:27,107:16,148:14,37:26,146:15,159:13,160:13,147:12,141:11,0:0,1:0,2:0,3:0,4:0,150:0,8:2,10:3,41:4,42:4,83:5,119:6,71:7,40:8,123:9,18:10}
SECOND={43:21,29:20,0:16,44:17,35:15,47:18,53:19,40:14,27:10,30:11,38:12,28:13,14:7,4:6,7:5,12:3,2:0,10:1,6:2,16:4,20:8,23:9}
NESTED={2:{9:0,7:1,14:2,15:2,23:2,25:2,13:3},10:{6:0,7:1,8:2,9:3,10:4,11:5,12:6,13:7,15:8},14:{8:0,1:1}}
ALIASES=((OUTPUT,OUTPUT+4,OUTPUT+8),(OUTPUT,OUTPUT,OUTPUT),(OUTPUT,OUTPUT+4,LEVEL),(OUTPUT,LEVEL,OUTPUT+8),(LEVEL,OUTPUT+4,OUTPUT+8),(OUTPUT,g.BASE+4,OUTPUT+8),(OUTPUT,g.BASE+0x38,OUTPUT+8),(OUTPUT,OUTPUT+4,g.BASE+4),(OUTPUT,OUTPUT+4,g.BASE+0x38))
@dataclass(frozen=True)
class Case:
 kind:int=0
 level:int=0
 who:int=1
 alias:int=0
 seed:int=0
 phase:int=0
def fixture(c):
 base=g.Case(seed=c.seed,phase=c.phase);m=g.fixture(base);m[g.BASE+4]=c.kind;m[g.BASE+0x3B]=c.who;g.put(m,LEVEL,c.level)
 for i in range(-16,28):m[OUTPUT+i]=(i*19+c.seed*11+0xA5)&255
 for i in range(3):g.put(m,OUTPUT+4*i,0xFFFFFFFF)
 return m
def reference(initial,c,args):
 m=dict(initial);owner,first,second,third=args;flags=0;kind=m[owner+4]
 if kind in THIRD:g.put(m,third,THIRD[kind]);flags=4
 level=g.read(m,LEVEL)
 if level in SECOND:
  g.put(m,second,SECOND[level]);flags|=2;value=None
  if level==43:
   if m[owner+4]in(156,157):value=0
  elif level in NESTED:value=NESTED[level].get(m[owner+0x3B])
  elif level not in(12,6):
   wanted={29:9,7:16,16:6,20:16}.get(level,1)
   if m[owner+0x3B]==wanted:value=0
  if value is not None:g.put(m,first,value);flags|=1
 return m,flags
def streams():
 symbols=dict(D_800BE9F0=LEVEL,jtbl_800A59AC=0x800A59AC,jtbl_800A5C98=0x800A5C98,jtbl_800A5D70=0x800A5D70,jtbl_800A5DBC=0x800A5DBC);symbols['.rodata']=symbols['jtbl_800A59AC']
 paths=['original-target.o','selected-owner.o','normalized-target.o','qualified-owner/selected-generic.o','qualified-owner/selected-generated.o'];out=[bound_blob(*payload(o/p,fn),symbols)for p in paths];assert all(v==out[0]for v in out)and len(out[0])==439;return out
def table_memory():
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();m={}
 for start,end in [(0x800A59AC,0x800A5C98),(0x800A5C98,0x800A5D70),(0x800A5D70,0x800A5DBC),(0x800A5DBC,0x800A5DE4)]:
  data=at(elf,start,end-start);m.update({start+i:b for i,b in enumerate(data)})
 return m
def model(words,c,initial,args):return g.Machine(words,g.Case(seed=c.seed,phase=c.phase),memory=initial,entry=ENTRY,arguments=args)
class ComparisonError(AssertionError):pass
def check(words,c,initial,args):
 m=model(words,c,initial,args).run();expected=reference(initial,c,args)
 if(m.memory,m.r[2])!=expected or m.calls:raise ComparisonError(str(c))
 assert 0<=m.r[2]<=7 and all(m.r[i]==m.before[i]for i in (*range(16,24),28,29,30,31))and m.f==m.before_f
 return m
def cases():
 rows=set(itertools.product(range(256),(0,1,29),(0,1,255)))
 rows.update(itertools.product((0,1,186,255),range(-1,65),(*range(32),255)))
 rows.update((kind,level,0)for kind,level in itertools.product((156,157),range(-1,65)))
 out=[Case(kind,level,who,seed=kind&3,phase=8*(who&1))for kind,level,who in sorted(rows)]
 out.extend(Case(kind,level,who,alias=alias,seed=who&3)for kind,level,who,alias in itertools.product((0,94,153,156,157,255),(-1,0,2,10,14,29,43,53,54),(1,8,9,15,16,25,255),range(1,len(ALIASES))))
 return out
def main():
 ws=streams();tables=table_memory();rows=cases();seen=set()
 for c in rows:
  initial=fixture(c);initial.update(tables);args=(g.BASE,*ALIASES[c.alias]);models=[check(words,c,initial,args)for words in ws];assert all(g.state(m)==g.state(models[0])for m in models[1:]);seen.update(models[0].visits)
 assert len(seen)==439,(len(seen),[hex(p-ENTRY)for p in sorted(set(range(ENTRY,ENTRY+1756,4))-seen)])
 cuts=0
 for c in (Case(),Case(kind=255,level=-1),Case(kind=94,level=0,alias=2),Case(kind=156,level=43),Case(level=2,who=25),Case(level=10,who=15)):
  initial=fixture(c);initial.update(tables);args=(g.BASE,*ALIASES[c.alias]);full=model(ws[0],c,initial,args).run()
  for cut in range(full.all_accesses):
   ms=[]
   for words in ws:
    m=model(words,c,initial,args);m.cut=cut
    try:m.run();raise AssertionError('Missing fired cut')
    except AccessBoundary:ms.append(m)
   assert all(g.state(m)==g.state(ms[0])for m in ms[1:]);cuts+=1
 unused=0
 for c,args in [(Case(kind=255,level=-1),(g.BASE,0,0,0)),(Case(kind=0,level=-1),(g.BASE,0,0,OUTPUT+8))]:
  initial=fixture(c);initial.update(tables)
  for words in ws:check(words,c,initial,args);unused+=1
 controls=[]
 for name,offset,word,c in [('signed-owner-kind',0,0x808E0004,Case(kind=153,level=-1)),('third-output-pointer',0x138,0xACC00000,Case(level=-1)),('return-bit3',0x6D0,0x34620008,Case())]:
  bad=list(ws[0]);assert bad[offset//4]!=word;bad[offset//4]=word;initial=fixture(c);initial.update(tables);args=(g.BASE,*ALIASES[c.alias])
  try:check(bad,c,initial,args)
  except ComparisonError:controls.append(dict(name=name,comparison_rejected=True))
  else:raise AssertionError('Ineffective control '+name)
 q=dict(cases_per_stream=len(rows),streams=5,executed_words=len(seen),fault_prefix_quintuples=cuts,alias_pointer_patterns=len(ALIASES),literal_full_private_states_equal=True,independent_ordered_reference_memory_and_return_equal=True,callee_saved_FPR_and_frame_preserved=True,unused_null_output_checks=unused,effective_controls=controls,source_installed=target_packet.installed(),matching_credit=0);(o/'guest.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
