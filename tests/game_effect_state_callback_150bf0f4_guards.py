import json,struct
from tools.experiments import game_effect_state_callback_150bf0f4_match as p
n=p
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');fixed,freferences=n.normalize(raw,refs);checks=0
 for i in range(73):
  wrong=bytearray(raw);wrong[4*i+3]^=1
  try:n.normalize(bytes(wrong),refs)
  except ValueError:checks+=1
  else:raise AssertionError(('raw corruption accepted',i))
 for at in refs:
  wrong={k:list(v) for k,v in refs.items()};wrong.pop(at)
  try:n.normalize(raw,wrong)
  except ValueError:checks+=1
  else:raise AssertionError(('relocation deletion accepted',at))
 for row in n.PIN['rows']:
  mutated=dict(row);mutated['expected']='00000000';old=n.PIN['rows'];n.PIN['rows']=[mutated if r is row else r for r in old]
  try:n.normalize(raw,refs)
  except AssertionError:checks+=1
  else:raise AssertionError(('guard corruption accepted',row['index']))
  finally:n.PIN['rows']=old
 entry=next(row for row in n.PIN['rows'] if row['index']==56);old=entry['insert_after'];entry['insert_after']='00000000'
 try:n.normalize(raw,refs)
 except ValueError:checks+=1
 else:raise AssertionError('branch insertion corruption accepted')
 finally:entry['insert_after']=old
 report=dict(rejected_corruptions=checks,raw_words=73,relocation_sites=len(refs),guards=28,source_installed=False);(p.out/'guard-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
