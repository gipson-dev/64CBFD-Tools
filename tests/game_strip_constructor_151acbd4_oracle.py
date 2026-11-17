"""Complete constructor outputs for raw, both padded and installed streams."""
import json,struct
from tools.tests.game_strip_constructor_151acbd4_private_oracle import *
from tools.experiments import game_strip_constructor_151acbd4_recovery as source
R,P,ENTRY=source.ROOT,source.OUT,source.ENTRY
def programs():
 result={'retail':list(struct.unpack('>360I',(P/'retail.bin').read_bytes()))}
 for label,file in [('raw','v63.o'),('strict','strip-constructor-padded-strict.o'),('layout','strip-constructor-padded-layout.o')]:
  raw,refs=payload(P/file,source.NAME);result[label]=bound_blob(raw,refs,SYMS)
 if source.installed():
  from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
  image=(R/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(image,ENTRY,1440);body=image[at:at+1440];assert body==(P/'retail.bin').read_bytes();result['production']=list(struct.unpack('>360I',body))
 return result
def main():
 code=programs();seen={label:set()for label in code};count=0
 for c in cases():
  for label,words in code.items():seen[label].update(verify(words,c).visits)
  count+=1
 report=dict(cases_per_stream=count,streams=list(code),words_visited={k:len(v)for k,v in seen.items()},all_initialized_public_bytes_compared=True,public_disjoint_from_stack=True,source_installed=source.installed(),c_match_credit=0)
 (P/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
