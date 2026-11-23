"""Direct texture registration, retaining retail's early missing-search behavior."""
from pathlib import Path
import hashlib,json,os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_texture_registration_15195dd4_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
def prepare():
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'), 'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256')}
 for n,d in MANIFEST['inputs'].items():
  frozen=OUT/'baseline'/n
  if frozen.exists():assert sha(frozen)==d,('Frozen input changed',n)
  assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase input changed',n)
 assert (OUT/'private-guards.csv').read_bytes()==(OUT/'baseline/conker/retail_word_patches.us.csv').read_bytes()
 return live
def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 from tools.experiments import game_texture_registration_15195dd4_objects as objects
 prepare();where=OUT/'selected-final';before,bd=compile_owner(ROOT,where,MANIFEST['old_source'],'before',('-O2','-g3'));after,ad=compile_owner(ROOT,where,MANIFEST['selected_source'],'candidate',('-O2','-g3'))
 assert same_functions(before,after,(FUNCTION,))==68 and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
 (where/'selected-owner.c').write_text(MANIFEST['selected_source']);(where/'body.c').write_text(MANIFEST['body'])
 q=objects.main();assert q['direct_byte_exact']and q['neighbors']==68 and q['guards']==0
 if 'raw_sha256'in MANIFEST:assert sha(OUT/'qualified-owner/generated_1C2C60.c.o')==MANIFEST['padded_sha256']
 return q
def qualify():
 prepare();inspect_source()
 from tools.experiments import game_texture_registration_15195dd4_make as make
 from tools.experiments import game_texture_registration_15195dd4_image as image
 make.main();q=image.main();assert q['predicted_ELF_sha256']==MANIFEST['predicted_ELF_sha256']and q['exclusions']==0 and q['metadata_permuted_records']==MANIFEST['metadata_permuted_records']
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==(OUT/'image-qualification/linked.elf').read_bytes()
 return q
