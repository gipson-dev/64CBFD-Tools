"""Independent reachable-instruction CFG inventory, with explicit delay slots."""
from pathlib import Path
import json
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g

def static(words):
 visited=set();processed=set();pending=[0]
 def mark(pc):assert pc%4==0 and 0<=pc<4*len(words);visited.add(pc)
 while pending:
  pc=pending.pop()
  if pc in processed:continue
  processed.add(pc);mark(pc);w=words[pc//4];op,rs,rt=w>>26,w>>21&31,w>>16&31
  floating=op==17 and rs==8
  if floating or op in(1,4,5,6,7,20,21,22,23):
   takes=(False,True)
   if not floating:
    if op in(4,5,20,21) and rs==rt:takes=(op in(4,20),)
    elif op==1 and rs==0:takes=(rt in(1,3),)
    elif op in(6,7,22,23) and rs==0:takes=(op in(6,22),)
   likely=bool(rt&2) if floating else rt in(2,3) if op==1 else op>=20
   if True in takes or not likely:mark(pc+4)
   if True in takes:pending.append(pc+4+4*(((w&65535)^32768)-32768))
   if False in takes:pending.append(pc+8)
  elif op==3:mark(pc+4);pending.append(pc+8)
  elif op==0 and w&63==8:assert rs==31;mark(pc+4)
  else:assert op!=2;pending.append(pc+4)
 return visited


def main():
 # A delay instruction may also be a normal jump target. Visited instructions
 # and processed entry PCs must be tracked separately.
 tests=(('delay-target',[0x10000000,0,0x03E00008,0],{0,4,8,12}),
        ('always-likely',[0x50000002,0,0x24020001,0x03E00008,0],{0,4,12,16}),
        ('never-likely',[0x54000002,0,0x24020001,0x03E00008,0],{0,8,12,16}))
 for name,words,expected in tests:assert static(words)==expected,(name,static(words),expected)
 report={}
 for name in('candidate','retail'):
  words=g.programs()[name];seen=static(words)
  report[name]=dict(words=len(words),reachable_words=len(seen),unreachable_offsets=[hex(pc) for pc in range(0,4*len(words),4) if pc not in seen])
 report['independent_delay_controls']=[name for name,words,expected in tests]
 (g.O/'coverage-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
