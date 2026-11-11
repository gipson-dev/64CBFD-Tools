import json,struct
from tools.experiments import game_startup_initializer_1500e470_match as p
n=p
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');fixed,freferences=n.normalize(raw,refs);checks=0
 for i in range(84):
  wrong=bytearray(raw);wrong[4*i+3]^=1
  try:n.normalize(bytes(wrong),refs)
  except ValueError:checks+=1
  else:raise AssertionError(('raw corruption accepted',i))
 for at in refs:
  wrong={k:list(v) for k,v in refs.items()};wrong.pop(at)
  try:n.normalize(raw,wrong)
  except ValueError:checks+=1
  else:raise AssertionError(('relocation deletion accepted',at))
 for row in n.PIN['differences']:
  mutated=dict(row);mutated['raw']='00000000';old=n.PIN['differences'];n.PIN['differences']=[mutated if r is row else r for r in old]
  try:n.normalize(raw,refs)
  except AssertionError:checks+=1
  else:raise AssertionError(('guard corruption accepted',row['index']))
  finally:n.PIN['differences']=old
 report=dict(rejected_corruptions=checks,raw_words=84,relocation_sites=len(refs),guards=5,source_installed=False);(p.out/'guard-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
