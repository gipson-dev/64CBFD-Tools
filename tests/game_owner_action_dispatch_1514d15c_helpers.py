"""Original439-word classifier: all-path byte ABI, dynamic footprints and connected dispatch."""
from tools.experiments import game_owner_action_dispatch_1514d15c_match as target_packet
from pathlib import Path
from dataclasses import replace
import itertools,json,struct,sys
sys.path.insert(0,str(target_packet.ROOT));o=target_packet.OUT;pass
from tools.tests import game_owner_action_dispatch_1514d15c_guest as g
from tools.tests import game_owner_action_dispatch_1514d15c_classifier_abi as abi
LEVEL=0x800BE9F0;OUTPUT=0xB0000

def prepared():
 rom=(g.r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();words=list(struct.unpack_from('>439I',rom,0x179F30));memory={}
 for va,n in((0x800A59AC,187*4),(0x800A5C98,54*4),(0x800A5D70,19*4),(0x800A5DBC,10*4)):
  data=abi.at(elf,va,n);memory.update({va+i:b for i,b in enumerate(data)})
 return words,memory

def classify(memory,args,c,words=None):
 if words is None:words,_=prepared()
 model=g.Machine(words,c,memory=memory,entry=g.CLASSIFY,arguments=args).run();value=model.r[2];assert 0<=value<=7 and not model.calls
 memory.clear();memory.update(model.memory);return value

class Connected(g.Machine):
 def __init__(self,words,c,initial,helper):super().__init__(words,c,memory=initial,connected=dict(zip(range(g.CLASSIFY,g.CLASSIFY+439*4,4),helper)))

def dynamic(helper,table_memory):
 seen=set();count=0;rows=set()
 rows.update((kind,level,who)for kind,level,who in itertools.product(range(256),(0,1,29),(0,1,255)))
 rows.update((kind,level,who)for kind,level,who in itertools.product((0,1,186,255),range(-1,65),(*range(32),255)))
 rows.update((kind,level,0)for kind,level in itertools.product((156,157),range(-1,65)))
 for kind,level,who in sorted(rows):
  c=g.Case(index=0,seed=kind&3);initial=g.fixture(c);initial.update(table_memory);initial[g.owner(c)+4]=kind;initial[g.owner(c)+0x3B]=who;g.put(initial,LEVEL,level)
  for i in range(-16,28):initial[OUTPUT+i]=(i*19+0xA5)&255
  for i in range(3):g.put(initial,OUTPUT+4*i,0xFFFFFFFF)
  m=g.Machine(helper,c,memory=initial,entry=g.CLASSIFY,arguments=(g.owner(c),OUTPUT,OUTPUT+4,OUTPUT+8)).run();assert 0<=m.r[2]<=7 and not m.calls
  changes={a for a,v in m.memory.items()if initial.get(a)!=v};writes=[t for t in m.trace if t[0]=='W'];assert changes<=set(range(OUTPUT,OUTPUT+12))and all(t[2]==4 and t[1]in(OUTPUT,OUTPUT+4,OUTPUT+8)for t in writes)
  seen.update(p for p in m.visits if g.CLASSIFY<=p<g.CLASSIFY+439*4);count+=1
 controls=[];c=g.Case();initial=g.fixture(c);initial.update(table_memory);initial[g.owner(c)+4]=0;initial[g.owner(c)+0x3B]=0;g.put(initial,LEVEL,0xFFFFFFFF)
 for i in range(-16,28):initial[OUTPUT+i]=0xA5
 for i in range(3):g.put(initial,OUTPUT+4*i,0xFFFFFFFF)
 for name,at,value in(('return-bit8',436,0x34620100),('third-output-fence',(0x1514CBB8-g.CLASSIFY)//4,0xACE00004)):
  bad=list(helper);assert bad[at]!=value;bad[at]=value;m=g.Machine(bad,c,memory=initial,entry=g.CLASSIFY,arguments=(g.owner(c),OUTPUT,OUTPUT+4,OUTPUT+8)).run();writes=[t for t in m.trace if t[0]=='W'];assert m.r[2]>255 or any(t[1]not in(OUTPUT,OUTPUT+4,OUTPUT+8)or t[2]!=4 for t in writes),name;controls.append(dict(name=name,comparison_rejected=True))
 return dict(cases=count,original_words=439,executed_words=len(seen),unexecuted_offsets=[hex(p-g.CLASSIFY)for p in sorted(set(range(g.CLASSIFY,g.CLASSIFY+439*4,4))-seen)],all_returns_low3bits=True,all_writes_are_named_output_words=True,register_ABI_and_FPR_preservation=True,effective_controls=controls)

def connected(helper,table_memory):
 streams=g.streams()[:2];count=0;seen=set();rows=[(kind,level,who,index)for kind,level,who,index in itertools.product((0,1,24,100,156,157,186,187,255),(0,1,20,29,53,54,64),(0,1,3,255),(0,2))]
 for kind,level,who,index in rows:
  c=g.Case(index=index,effects=(who&1),mode=2 if who==3 else 0,seed=kind&3);initial=g.fixture(c);initial.update(table_memory);initial[g.owner(c)+4]=kind;initial[g.owner(c)+0x3B]=who;g.put(initial,LEVEL,level)
  expected=g.reference(initial,c,classifier=lambda memory,args,case:classify(memory,args,case,helper));models=[]
  for words in streams:
   m=Connected(words,c,initial,helper).run();assert(g.public(m.memory,c),m.calls,m.r[2])==expected,dict(kind=kind,level=level,who=who,index=index,actual_calls=m.calls,expected_calls=expected[1]);models.append(m);seen.update(p for p in m.visits if g.CLASSIFY<=p<g.CLASSIFY+1756)
  assert g.state(models[0])==g.state(models[1]);count+=1
 return dict(cases_per_stream=count,streams=2,original_classifier_words_executed=len(seen),actual439word_classifier_connected=True,target_public_memory_ordered_calls_and_return_equal_independent_dispatch_reference=True,reference_reuses_original_helper_instruction_model_not_an_independent_helper_semantic_recovery=True,all_literal_full_private_states_equal=True,other_services_opaque=True)

def main():
 proof=abi.main();helper,tables=prepared();d=dynamic(helper,tables);c=connected(helper,tables);q=dict(classifier_ABI=proof,dynamic_original_classifier=d,connected_target=c,helper_matching_credit=0,source_installed=target_packet.installed(),matching_credit=0,no_hardware_or_gameplay_claim=True);(o/'helpers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
