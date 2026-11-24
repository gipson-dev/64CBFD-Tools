"""Scene-list render pass; preserve captured links and live provider state."""
from pathlib import Path
import csv,hashlib,io,json,os,struct
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_scene_node_render_15030e08_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
def prepare():
 assert hashlib.sha256(MANIFEST['selected_source'].encode()).hexdigest()==MANIFEST['selected_sha256']
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'),'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256'),'conker/retail_word_patches.us.csv':MANIFEST.get('selected_guards_sha256')}
 for n,d in MANIFEST['inputs'].items():
  f=OUT/'baseline'/n
  if f.is_file():assert sha(f)==d,('Frozen input changed',n)
  assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase input changed',n)
 return live
def guards(raw,normal):
 words=struct.unpack('>100I',raw[0]);out=struct.unpack('>99I',normal[0]);head=(OUT/'baseline/conker/retail_word_patches.us.csv').read_bytes();buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=next(csv.reader(io.StringIO(head.decode()))),lineterminator='\n');spec=lambda v:'|'.join(k+':'+n for k,n in v)or'-'
 for i,w in enumerate(words):
  dst=i if i<31 else i-1
  writer.writerow(dict(filename='generated_5D2C0',function=FUNCTION,offset=hex(4*i),expected=hex(w),replacement=hex(w if i==31 else out[dst]),expected_relocations=spec(raw[1].get(4*i,())),replacement_relocations=spec(raw[1].get(4*i,())if i==31 else normal[1].get(4*dst,())),note='Proved redundant shift-mask elimination and closed temporary-register rename',insert_after='',insert_after_relocations='',omit='true'if i==31 else'false'))
 suffix=buf.getvalue().encode();(OUT/'guard-suffix.csv').write_bytes(suffix);(OUT/'private-guards.csv').write_bytes(head+suffix);return sha(OUT/'private-guards.csv')

def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.tests.game_scene_node_render_15030e08_normalizer import normalize
 from tools.experiments import game_scene_node_render_15030e08_objects as objects
 prepare();w=OUT/'selected-final';before,bd=compile_owner(ROOT,w,MANIFEST['old_source'],'before');after,ad=compile_owner(ROOT,w,MANIFEST['selected_source'],'candidate')
 assert same_functions(before,after,(FUNCTION,))==39 and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
 for name,key in(('selected-owner.c','selected_source'),('body.c','body'),('declarations.c','declarations')):(w/name).write_bytes(MANIFEST[key].encode())
 assert sha(w/'selected-owner.c')==MANIFEST['selected_sha256'];raw=payload(after,FUNCTION);actual=guards(raw,normalize(*raw))
 if 'selected_guards_sha256'in MANIFEST:assert actual==MANIFEST['selected_guards_sha256']
 return objects.main()
def qualify():
 prepare();inspect_source()
 from tools.experiments import game_scene_node_render_15030e08_make as make
 from tools.experiments import game_scene_node_render_15030e08_image as image
 make.main();q=image.main()
 if 'predicted_ELF_sha256'in MANIFEST:assert q['predicted_ELF_sha256']==MANIFEST['predicted_ELF_sha256']and q['metadata_permuted_records']==MANIFEST['metadata_permuted_records']
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==(OUT/'image-qualification/linked.elf').read_bytes()
 return q
if __name__=='__main__':qualify()
