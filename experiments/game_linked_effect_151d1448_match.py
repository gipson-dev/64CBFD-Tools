"""Direct linked-effect constructor with captured actor and packet lifetimes."""
from pathlib import Path
import hashlib,json,os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_linked_effect_151d1448_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
def prepare():
 assert hashlib.sha256(MANIFEST['selected_source'].encode()).hexdigest()==MANIFEST['selected_sha256'],'Selected source pin is not canonical LF'
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'),'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256')}
 for n,d in MANIFEST['inputs'].items():
  f=OUT/'baseline'/n
  if f.is_file():assert sha(f)==d,('Frozen input changed',n)
  assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase input changed',n)
 assert(OUT/'private-guards.csv').read_bytes()==(OUT/'baseline/conker/retail_word_patches.us.csv').read_bytes()
 return live
def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 from tools.experiments import game_linked_effect_151d1448_objects as objects
 prepare();w=OUT/'selected-final';before,bd=compile_owner(ROOT,w,MANIFEST['old_source'],'before');after,ad=compile_owner(ROOT,w,MANIFEST['selected_source'],'candidate')
 assert same_functions(before,after,(FUNCTION,))==51 and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
 for name,key in [('selected-owner.c','selected_source'),('body.c','body'),('declarations.c','declarations')]:(w/name).write_bytes(MANIFEST[key].encode())
 assert sha(w/'selected-owner.c')==MANIFEST['selected_sha256'];return objects.main()
def qualify():
 prepare();inspect_source()
 from tools.experiments import game_linked_effect_151d1448_make as make
 from tools.experiments import game_linked_effect_151d1448_image as image
 make.main();q=image.main()
 if 'predicted_ELF_sha256'in MANIFEST:assert q['predicted_ELF_sha256']==MANIFEST['predicted_ELF_sha256']and q['metadata_permuted_records']==MANIFEST['metadata_permuted_records']
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==(OUT/'image-qualification/linked.elf').read_bytes()
 return q
