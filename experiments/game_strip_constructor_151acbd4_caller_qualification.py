"""Private complete-caller qualification with exact prior-evidence reuse."""
from pathlib import Path
import hashlib,json,os
from tools.experiments import game_strip_constructor_151acbd4_ordered as semantic
ROOT=semantic.ROOT;PACKET=semantic.PACKET;QUALIFICATION=PACKET/'caller-final-qualification';FROZEN=PACKET/'caller-final-baseline'
OUT=Path(os.environ.get('CBFD_STRIP_CALLER_WORK',str(QUALIFICATION/'qualification-primary')))
assert OUT.resolve().is_relative_to((ROOT/'conker/build').resolve())
NAME,SOURCE,ENTRY,ROM,SIZE=semantic.NAME,semantic.SOURCE,semantic.ENTRY,semantic.ROM,semantic.SIZE
PRIOR_CHECKPOINT_SHA256='0aa24e92bcd59e3df208b4dcede731c389e350365d728ea276ec377e33238596'
def check_inputs():
 inputs=json.loads((FROZEN/'fingerprints.json').read_text())['inputs']
 for name,h in inputs.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 return len(inputs)
def reused_evidence():
 p=PACKET/'ordered-qualification';file=p/'committed-checkpoint.json'
 assert hashlib.sha256(file.read_bytes()).hexdigest()==PRIOR_CHECKPOINT_SHA256
 checkpoint=json.loads(file.read_text());assert checkpoint['complete_provider_return_relation_proved'] and not checkpoint['source_installed'] and checkpoint['c_match_credit']==0
 for name,h in checkpoint['receipts'].items():assert hashlib.sha256((p/name.replace('\\','/')).read_bytes()).hexdigest()==h,name
 semantic.check_inputs();report=dict(prior_checkpoint_sha256=PRIOR_CHECKPOINT_SHA256,unchanged_prior_inputs=1486,prior_ordered_semantic_gates_reused=True,fresh_semantic_suite_claimed=False,source_installed=False,c_match_credit=0)
 (OUT/'reused-evidence.json').write_text(json.dumps(report,indent=2)+'\n');return report
def compile_and_check():
 check_inputs();semantic.OUT=OUT;words=semantic.compile_and_check();reused_evidence();check_inputs();return words
