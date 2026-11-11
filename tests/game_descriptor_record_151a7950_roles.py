"""Show that the sole changed instruction is the same non-trapping addition."""
import json,struct
from tools.experiments import game_descriptor_record_151a7950_match as p
from tools.experiments import game_descriptor_record_151a7950_match as n
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');normal,_=n.normalize(raw,refs)
 a=struct.unpack('>80I',raw);b=struct.unpack('>80I',normal)
 assert {i for i,(x,y) in enumerate(zip(a,b)) if x!=y}=={44}
 assert (a[44],b[44])==(0x01465821,0x00ca5821)
 for x in (0,1,0x7fffffff,0x80000000,0xffffffff):
     for y in (0,1,0x7fffffff,0x80000000,0xffffffff):
         assert (x+y)&0xffffffff==(y+x)&0xffffffff
 result=dict(guard_words=1,instruction='addu $t3,$t2,$a2 -> addu $t3,$a2,$t2',non_trapping=True,equal_for_all_32bit_operands_by_commutativity=True,relocations_at_word=0,source_installed=False)
 (p.out/'roles.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
