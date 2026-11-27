"""Complete accepted 109-word dispatcher connected to the complete classifier."""
from tools.experiments import game_owner_action_classifier_1514ca80_match as target_packet
from pathlib import Path
import array,hashlib,itertools,json,re,struct,subprocess,sys
sys.path.insert(0,str(target_packet.ROOT));o=target_packet.OUT;pass
from tools.tests import game_owner_action_classifier_1514ca80_guest as leaf
from tools.tests import game_owner_action_dispatch_1514d15c_guest as g
from tools.tests.game_owner_action_dispatch_1514d15c_classifier_abi import at
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
r=target_packet.ROOT;PARENT=0x1514D15C
class Connected(g.Machine):
 def __init__(self,words,c,initial,child):super().__init__(words,c,memory=initial,entry=PARENT,connected=dict(zip(range(leaf.ENTRY,leaf.ENTRY+1756,4),child)))
def main():
 rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();blob=at(elf,PARENT,436);assert blob==rom[0x17A60C:0x17A7C0]
 asm=(o/'baseline/conker/asm/179F30.s').read_text().split('glabel func_1514D15C\n',1)[1].split('endlabel func_1514D15C',1)[0];assert bytes.fromhex(''.join(re.findall(r'/\*\s*[0-9A-F]+\s+[0-9A-F]+\s+([0-9A-F]{8})\s*\*/',asm)))==blob
 path=o/'original-parent.s';path.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel func_1514D15C\n'+asm+'endlabel func_1514D15C\n.size func_1514D15C,.-func_1514D15C\n');q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path.with_suffix('.o')),str(path)],capture_output=True,text=True);assert q.returncode==0,q.stderr
 raw,refs=payload(path.with_suffix('.o'),'func_1514D15C');actual={n:int(n.split('_',1)[1],16)for rows in refs.values()for _,n in rows};assert struct.pack('>109I',*bound_blob(raw,refs,actual))==blob;original=bound_blob(raw,refs,g.symbols())
 for p in ['before-owner.o','selected-owner.o','qualified-owner/selected-generic.o','qualified-owner/selected-generated.o']:assert bound_blob(*payload(o/p,'func_1514D15C'),g.symbols())==original
 parents=[original,bound_blob(*payload(o/'qualified-owner/selected-generic.o','func_1514D15C'),g.symbols())];children=leaf.streams()[::2][:2];assert len(children)==2
 tables=leaf.table_memory();rows=[]
 for kind,level,who,index in itertools.product((0,1,24,100,156,157,186,187,255),(-1,0,1,20,29,53,54),(0,1,3,255),(-2,0,3)):
  rows.append((kind,level,who,g.Case(index=index,effects=who&1,mode=2 if who==3 else 0,seed=kind&3)))
 rows.extend([(0,0,1,g.Case(gate=1)),(255,1,0,g.Case(effects=0)),(0,0,1,g.Case(effects=2,enable=1)),(255,0,1,g.Case(selectors=(0,0,0),absent=1)),(0,0,1,g.Case(selectors=(0,0,0),absent=1))])
 seen_parent=set();seen_child=set();runs=0
 def service(memory,args,case):
  result,value=leaf.reference(memory,None,args);memory.clear();memory.update(result);return value
 for kind,level,who,c in rows:
  initial=g.fixture(c);initial.update(tables);initial[g.owner(c)+4]=kind;initial[g.owner(c)+0x3B]=who;g.put(initial,leaf.LEVEL,level);expected=g.reference(initial,c,classifier=service);models=[]
  for parent,child in itertools.product(parents,children):
   m=Connected(parent,c,initial,child).run();assert(g.public(m.memory,c),m.calls,m.r[2])==expected,(kind,level,who,str(c));models.append(m);seen_parent.update(p for p in m.visits if PARENT<=p<PARENT+436);seen_child.update(p for p in m.visits if leaf.ENTRY<=p<leaf.ENTRY+1756);runs+=1
  assert all(g.state(m)==g.state(models[0])for m in models[1:])
 assert len(seen_parent)==109,(len(seen_parent),[hex(p-PARENT)for p in sorted(set(range(PARENT,PARENT+436,4))-seen_parent)])
 # This path returns first=1. The wrong-home control therefore makes its
 # unintended final row lookup remain mapped and reject by comparison.
 controls=[];c=g.Case();initial=g.fixture(c);initial.update(tables);initial[g.owner(c)+4]=0;initial[g.owner(c)+0x3B]=7;g.put(initial,leaf.LEVEL,2);normal=Connected(original,c,initial,children[0]).run()
 call=[i for i,w in enumerate(original)if w>>26==3 and((w&0x3FFFFFF)<<2|0x10000000)==leaf.ENTRY];assert len(call)==1
 for name,index,word in [('skipped-classifier',call[0],0x00001025),('wrong-first-output-home',0xB4//4,0x27A50040)]:
  bad=list(original);assert bad[index]!=word;bad[index]=word;m=Connected(bad,c,initial,children[0]).run();assert g.state(m)!=g.state(normal),name;controls.append(dict(name=name,full_state_comparison_rejected=True))
 words=array.array('I');words.frombytes(rom[:len(rom)//4*4]);
 if sys.byteorder=='little':words.byteswap()
 direct=[hex(4*i)for i,w in enumerate(words)if w>>26 in(2,3)and(w&0x3FFFFFF)*4==(leaf.ENTRY&0x0FFFFFFF)];literal=[hex(4*i)for i,w in enumerate(words)if w==leaf.ENTRY];assert direct==['0x17a6c8']and literal==[],(direct,literal)
 q=dict(original_parent='func_1514D15C',original_parent_words_pinned=109,original_parent_words_executed=len(seen_parent),complete_parent_execution=True,complete_classifier_words=439,connected_classifier_words_executed=len(seen_child),cases_per_stream=len(rows),parent_streams=2,child_streams=2,connected_runs=runs,full_private_states_equal=True,independent_classifier_and_dispatch_references_equal=True,other_services_opaque=True,parent_retained_exact_and_uncredited=True,unfinished_grandparent_not_executed_or_credited=True,direct_ROM_call_patterns=direct,aligned_ROM_literals=literal,effective_controls=controls,original_parent_sha256=hashlib.sha256(blob).hexdigest(),source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
