"""Independent semantic failures; no target fingerprint gates are consulted."""
from pathlib import Path
import importlib.util,json,sys
from tools.tests import game_inverse_motion_151a4638_proof as p
O=p.O
def main(label='v37'):
 raw,retail=p.programs(label);report=p.prove(raw,retail);controls=[]
 def run(name,words,good=False):
  try:p.prove(words,retail)
  except AssertionError as error:
   reason=str(error);assert not good and reason and not any(x in reason for x in('unsupported','unbounded','escape','BREAK')),('invalid control',name,reason)
   controls.append(dict(label=name,rejected=True,reason=reason[:700]))
  else:assert good,('ineffective control',name);controls.append(dict(label=name,passes=True))
 def modify(name,predicate,change):
  at=next(i for i,w in enumerate(raw)if predicate(w));bad=raw.copy();bad[at]=change(bad[at]);run(name,bad)
 modify('counter-modulus',lambda w:w==0x24010005,lambda w:w^1)
 modify('dispatch-byte',lambda w:w>>26==9 and w&65535==0x27,lambda w:w^1)
 modify('base-scalar',lambda w:w>>26==15 and w&65535==0x43FA,lambda w:w^1)
 modify('scale-FP-operand-order',lambda w:w>>26==17 and w>>21&31==16 and w&63==2 and w>>6&31==2,lambda w:(w&~((31<<11)|(31<<16)))|((w>>11&31)<<16)|((w>>16&31)<<11))
 modify('random-flag',lambda w:w>>26==13 and w&65535==0x40,lambda w:w^0x20)
 modify('fresh-owner-channel',lambda w:w>>26==36 and w&65535==12,lambda w:w+1)
 modify('last-signed-parameter',lambda w:w>>26==9 and w&65535==0xFFE8,lambda w:w^1)
 modify('factory-payload-extent',lambda w:w==0x2406000C,lambda w:w^4)
 modify('parameter-source-home',lambda w:w>>26==9 and w>>21&31==29 and w>>16&31==5 and w&65535==0x28,lambda w:w+4)
 assert raw[-1]==0;bad=raw.copy();bad[-1]=0xAFA0FFFC;run('return-delay-private-write',bad)
 from tools.experiments.game_composite_burst_151a3150_match import fields
 alternate=[]
 for w in raw:
  for shift,kind in fields(w):
   if kind=='g'and w>>shift&31 in(8,9):w=(w&~(31<<shift))|((17-(w>>shift&31))<<shift)
  alternate.append(w)
 run('independent-T0-T1-allocation',alternate,True)
 report.update(controls=controls,source_installed=False,c_match_credit=0);(O/'controls-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(semantic_negatives=10,positive_controls=1,passes=True)),flush=True);return report
if __name__=='__main__':main(sys.argv[1]if len(sys.argv)>1 else'v37')
