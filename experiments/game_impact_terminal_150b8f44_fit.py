"""Uninstalled source-field fit with explicit finite-value relation and receipt reuse."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments import game_impact_terminal_150b8f44_screen as s
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_impact_terminal_150b8f44_normalizer as normalizer
ROOT=s.ROOT;PACKET=s.PACKET;STAGE=PACKET/'adoption-relation'
OUT=Path(os.environ.get('CBFD_IMPACT_FIT_WORK',STAGE/'preview')).resolve();assert OUT.is_relative_to(ROOT/'conker/build')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def check_inputs():
 count=s.check_inputs();extra=json.loads((STAGE/'dependency-baseline/fingerprints.json').read_text())
 for name,h in extra.items():assert sha(ROOT/name)==h and sha(STAGE/'dependency-baseline'/name)==h,name
 return count+len(extra)

def reuse_semantic_receipts():
 tasks={name.removeprefix('tools/'):h for name,h in json.loads((STAGE/'dependency-baseline/fingerprints.json').read_text()).items()}
 reports=[]
 for label in('primary','sibling'):
  row=json.loads((PACKET/'qualification'/(label+'-suite.json')).read_text());assert row['passes']and row['tests']==4 and not row['skips']and row['task_sha256']==tasks
  for name,value in row['imports'].items():assert sha(ROOT/'tools'/name)==value['sha256'],name
  reports.append(dict(configuration=label,unchanged_tests_reused=4,imported_tool_files=row['imported_tool_files']))
 return reports

def prepare():
 check_inputs();reused=reuse_semantic_receipts();s.OUT=OUT;state=s.prepare()
 raw,refs=payload(OUT/'candidate.o',s.NAME);truth,trefs=payload(OUT/'original.o',s.NAME)
 words=list(struct.unpack('>390I',raw));derived,bindings=normalizer.derive(words,refs)
 assert(struct.pack('>391I',*derived),bindings)==(truth,trefs)
 assert bound_blob(struct.pack('>391I',*derived),bindings,s.symbols())==state['retail_words']
 (OUT/'fit-report.json').write_text(json.dumps(dict(passes=True,source_words=390,derived_words=391,source_frame=416,retail_frame=416,source_load_clones=1,zero_coalescence_to_nop=1,source_instructions_omitted=0,complete_bindings_match=True,semantic_receipts_reused=reused,frozen_inputs=check_inputs(),source_installed=False,c_match_credit=0),indent=2)+'\n')
 return state

def input_corruptions():
 raw,refs=payload(OUT/'candidate.o',s.NAME);words=list(struct.unpack('>390I',raw));count=0
 for i in range(390):
  bad=words[:];bad[i]^=1
  try:normalizer.derive(bad,refs)
  except AssertionError:count+=1
  else:raise AssertionError(('source word accepted',i))
 for offset in refs:
  bad={**refs,offset:[(refs[offset][0][0],'wrong_symbol')]}
  try:normalizer.derive(words,bad)
  except AssertionError:count+=1
  else:raise AssertionError(('source binding accepted',offset))
 report=dict(passes=True,effective_source_word_and_binding_corruptions=count,source_words=390,source_bindings=len(refs),source_installed=False,c_match_credit=0)
 (OUT/'fit-input-controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
