"""Check all non-null query-table callback definitions use the common ABI."""
import re,struct
from tools.experiments import game_camera_query_150be850_match as packet
from tools.experiments.game_actor_state_tick_integration import symbol_rows

def run(proposals):
 root=packet.ROOT;asm=(root/'conker/asm/data/22BEF0.rodata.s').read_text();part=asm.split('dlabel D_80088498\n',1)[1].split('enddlabel D_80088498',1)[0]
 entries=re.findall(r'\.word\s+(func_\w+|0x\w+)',part);assert len(entries)==15 and entries[12]=='0x00000000'
 elf=(root/'conker/build/conker.us.elf').read_bytes();lookup={v[1]:v[2][1] for v in symbol_rows(elf)};rom=(root/'conker/conker.us.bin').read_bytes();assert tuple(0 if x.startswith('0x') else lookup[x] for x in entries)==struct.unpack_from('>15I',rom,0x22cf58)
 count=0
 for name in entries:
  if name.startswith('0x'):continue
  hits=[]
  for owner,(_,source) in proposals.items():
   hits.extend((owner,m.group(1)) for m in re.finditer(r'(?m)^s32\s+'+name+r'\s*\(([^;{}]*)\)\s*\{',source))
  assert len(hits)==1,(name,hits)
  params=hits[0][1].split(',');assert len(params)==3 and all(re.fullmatch(r'\s*s32\s+\w+\s*',p) for p in params[:2]) and re.fullmatch(r'\s*s32\s*\*\s*\w+\s*',params[2]),(name,hits)
  count+=1
 assert count==14
 print('all 14 non-null retail query-table targets use compatible three-argument definitions')
