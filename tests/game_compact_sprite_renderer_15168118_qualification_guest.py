"""Complete three-stream leaf and independently rebased-symbol checks."""
from pathlib import Path
from dataclasses import replace
import json,sys
from tools.experiments import game_compact_sprite_renderer_15168118_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_compact_sprite_renderer_15168118_guest as g
def main():
 paths=dict(raw='selected-v2/candidate.o',padded='qualified-owner/game_1944C0.c.o',retail='original-target.o');result={};rows=g.cases()
 def check(ws,c):
  memory=g.fixture(c);g.put(memory,g.SYMS['D_800D2C9C'],0x40000);want,log,value=g.reference(memory,c);m=g.Oracle(ws,memory,c).run()
  assert(m.observations,m.r[2],g.public(m.memory))==(log,value,g.public(want)),c
  return m
 for name,p in paths.items():
  ws=g.bound_blob(*g.payload(o/p,'func_15168118'),g.SYMS);seen=set()
  for c in rows:seen.update(check(ws,c).visits)
  result[name]=dict(cases=len(rows),unexecuted=[i for i in range(len(ws))if g.ENTRY+4*i not in seen])
 original=dict(g.SYMS);runs=0
 try:
  for low in(0,0x7FFC,0x8000,0xFFFC):
   for i,n in enumerate(sorted(original)):
    if n in g.NAMES:g.SYMS[n]=0x15300000+i*0x100
    elif n in('D_800907FC','D_8009053C','D_800A6CA0','D_800A6CA4','D_800DBFF0','D_800A4AC8','D_800D2C9C'):g.SYMS[n]=0x80300000+i*0x10000+low
   g.COUNTS.clear();g.COUNTS.update(zip((g.SYMS[n]for n in g.NAMES),(11,3,3,4,8,6,2)));g.NAME.clear();g.NAME.update({g.SYMS[n]:n for n in g.NAMES})
   # Coefficients originate in the frozen image, and are remapped explicitly.
   fixture=g.fixture
   def remapped(c):
    saved={n:g.SYMS[n]for n in('D_800A6CA0','D_800A6CA4')}
    try:
     for n in saved:g.SYMS[n]=original[n]
     m=fixture(c)
    finally:g.SYMS.update(saved)
    for n,at in saved.items():v=g.get(m,original[n]);[m.pop(original[n]+i)for i in range(4)];g.put(m,at,v)
    return m
   g.fixture=remapped
   try:
    for p in paths.values():
     ws=g.bound_blob(*g.payload(o/p,'func_15168118'),g.SYMS)
     for c in(g.Case(),g.Case(flags=0x300,width=-2000,height=-500,yaw=-720.5,pitch=-30,effect=7),g.Case(flags=1,special=2,frame_table=True)):check(ws,c);runs+=1
   finally:g.fixture=fixture
 finally:
  g.SYMS.clear();g.SYMS.update(original);g.COUNTS.clear();g.COUNTS.update(zip((g.SYMS[n]for n in g.NAMES),(11,3,3,4,8,6,2)));g.NAME.clear();g.NAME.update({g.SYMS[n]:n for n in g.NAMES})
 report=dict(streams=result,guest_rebase_runs=runs,source_installed=packet.installed(),matching_credit=0,limits='Bounded helper contracts and finite f32 conversion domain. No FCSR, asynchronous or hardware rendering claim.')
 (o/'guest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
