"""Initialize menu opacity, captured flags and transition state."""
from pathlib import Path
import csv,hashlib,io,json,os,struct
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_menu_fade_renderer_151e09dc_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
_IMMUTABLE_CHECKED=False
def prepare():
 global _IMMUTABLE_CHECKED
 assert hashlib.sha256(MANIFEST['selected_source'].encode()).hexdigest()==MANIFEST['selected_sha256']
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'),'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256'),'conker/retail_word_patches.us.csv':MANIFEST.get('selected_guards_sha256')}
 for n,d in MANIFEST['inputs'].items():
  if not _IMMUTABLE_CHECKED:
   f=OUT/'baseline'/n
   if f.is_file():assert sha(f)==d,('Frozen input changed',n)
  if not _IMMUTABLE_CHECKED or n in allowed:assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase input changed',n)
 _IMMUTABLE_CHECKED=True
 return live

def guards(raw,normal):
 assert raw==normal
 head=(OUT/'baseline/conker/retail_word_patches.us.csv').read_bytes()
 (OUT/'guard-suffix.csv').write_bytes(b'');(OUT/'private-guards.csv').write_bytes(head)
 return sha(OUT/'private-guards.csv')


def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.tests.game_menu_fade_renderer_151e09dc_normalizer import normalize
 from tools.experiments import game_menu_fade_renderer_151e09dc_objects as objects
 prepare();w=OUT/'selected-final';before,bd=compile_owner(ROOT,w,MANIFEST['old_source'],'before');after,ad=compile_owner(ROOT,w,MANIFEST['selected_source'],'candidate')
 assert payload(after,MANIFEST['abi_helper'])==(bytes.fromhex(MANIFEST['abi_helper_hex']),{})
 assert same_functions(before,after,(FUNCTION,MANIFEST['abi_helper']))==58 and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
 for name,key in(('selected-owner.c','selected_source'),('body.c','body'),('declarations.c','declarations')):(w/name).write_bytes(MANIFEST[key].encode())
 assert sha(w/'selected-owner.c')==MANIFEST['selected_sha256'];raw=payload(after,FUNCTION);actual=guards(raw,normalize(*raw))
 if 'selected_guards_sha256'in MANIFEST:assert actual==MANIFEST['selected_guards_sha256']
 return objects.main()
def qualify():
 inspect_source()
 from tools.experiments import game_menu_fade_renderer_151e09dc_make as make
 from tools.experiments import game_menu_fade_renderer_151e09dc_image as image
 make.main();q=image.main()
 if 'predicted_ELF_sha256'in MANIFEST:assert q['predicted_ELF_sha256']==MANIFEST['predicted_ELF_sha256']and q['metadata_permuted_records']==MANIFEST['metadata_permuted_records']
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==(OUT/'image-qualification/linked.elf').read_bytes()
 return q
if __name__=='__main__':qualify()
