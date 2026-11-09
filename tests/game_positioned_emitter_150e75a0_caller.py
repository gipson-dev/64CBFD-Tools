"""All literal call sites and the two recovered same-owner callers."""
import json,struct,sys
from pathlib import Path
from tools.experiments.game_positioned_emitter_150e75a0_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.match_progress import load_elf_functions
from tools.experiments.game_remaining_donor_candidates import body
ENTRY=0x150E75A0
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();jal=0x0C000000|((ENTRY>>2)&0x3FFFFFF);sites=[];pointers=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',rom[:len(rom)&~3])):
  if w==jal:sites.append(i*4)
  if w==ENTRY:pointers.append(i*4)
 fs,_,addresses=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');callers={}
 for name,words in fs.items():
  found=[addresses[name]+i*4 for i,w in enumerate(words)if w==jal]
  if found:callers[name]=found
 assert set(callers)=={'func_150E7290','func_150E7C9C'}and len(sites)==2 and not pointers,(callers,sites,pointers)
 ordered=sorted((at,name)for name,at in addresses.items());retail_callers={}
 for at in sites:
  pc=at-0x2D4B0+0x15000000;owner=max((va,n)for va,n in ordered if va<=pc)[1];retail_callers.setdefault(owner,[]).append(pc)
 assert set(retail_callers)==set(callers)
 source=(out/'final-owner.c').read_text()
 for name in callers:assert body(source,name).count('func_150E75A0(')==1
 windows=[]
 for at in sites:
  ws=list(struct.unpack_from('>12I',rom,at-24));windows.append(dict(ROM=hex(at),PC=hex(at-0x2D4B0+0x15000000),words=ws))
 report=dict(linked_callers=callers,retail_callers=retail_callers,literal_call_ROMs=sites,literal_address_values=pointers,windows=windows,connected_native_dispatcher='func_150E7290',other_caller_raw_body_and_linked_body_unchanged=True,complete_caller_guest_or_hardware_claimed=False)
 (out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
