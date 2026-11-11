import json,struct
from tools.experiments import game_channel_preset_initializer_1500ad84_match as p
n=p
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');fixed,freferences=n.normalize(raw,refs);checks=0
 for i in range(97):
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
  except ValueError:checks+=1
  else:raise AssertionError(('guard corruption accepted',row['index']))
  finally:n.PIN['rows']=old
 for row in n.PIN['rows']:
  if row['expected_relocations']!=row['replacement_relocations']:
   old=row['replacement_relocations'];row['replacement_relocations']=[['R_MIPS_HI16','bad_symbol']]
   try:n.normalize(raw,refs)
   except ValueError:checks+=1
   else:raise AssertionError(('replacement binding corruption accepted',row['index']))
   finally:row['replacement_relocations']=old
 report=dict(rejected_corruptions=checks,raw_words=97,relocation_sites=len(refs),guards=62,source_installed=False);(p.out/'guard-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
