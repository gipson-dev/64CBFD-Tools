"""Effective instruction controls for the unnormalized whole-function relation."""
from pathlib import Path
import importlib.util,json,sys
from tools.tests import game_attached_emission_151a4a38_proof as p
O=p.O
def main(label='v11'):
 raw,retail=p.programs(label);report=p.prove(raw,retail);controls=[]
 def run(name,words,good=False):
  try:p.prove(words,retail)
  except AssertionError as error:
   reason=str(error);assert not good and reason and not any(x in reason for x in('unsupported','unbounded','escape','BREAK')),('invalid control',name,reason)
   controls.append(dict(label=name,rejected=True,reason=reason[:700]))
  else:assert good,('ineffective control',name);controls.append(dict(label=name,passes=True))
 def modify(name,predicate,change):
  at=next(i for i,w in enumerate(raw)if predicate(w));bad=raw.copy();bad[at]=change(bad[at]);run(name,bad)
 modify('excluded-actor-type',lambda w:w==0x24010008,lambda w:w^1)
 modify('invalid-owner-retirement',lambda w:w==0xA20B000D,lambda w:0)
 modify('source-generation-byte',lambda w:w==0x9068003B,lambda w:w+1)
 modify('accumulator-add',lambda w:w==0x46085400,lambda w:w|1)
 modify('matrix-stride',lambda w:w==0x00095180,lambda w:w^(1<<6))
 modify('angle-bias',lambda w:w==0x2719FFC0,lambda w:w+1)
 modify('base-scalar',lambda w:w==0x3C014396,lambda w:w^1)
 modify('random-flag',lambda w:w>>26==13 and w&65535==0x40,lambda w:w^0x20)
 modify('fresh-owner-channel',lambda w:w==0x9206000C,lambda w:w+1)
 modify('dispatch-selector',lambda w:w==0x240500FF,lambda w:w^1)
 from tools.experiments.game_composite_burst_151a3150_match import fields
 alternate=[]
 for index,w in enumerate(raw):
  for shift,kind in fields(w):
   if 0xE8<=index*4<0x294 and kind=='g'and w>>shift&31 in(8,9):w=(w&~(31<<shift))|((17-(w>>shift&31))<<shift)
  alternate.append(w)
 run('independent-hot-region-T0-T1-allocation',alternate,True)
 report.update(controls=controls,source_installed=False,c_match_credit=0);(O/'controls-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(semantic_negatives=10,positive_controls=1,passes=True)),flush=True);return report
if __name__=='__main__':main(sys.argv[1]if len(sys.argv)>1 else'v11')
