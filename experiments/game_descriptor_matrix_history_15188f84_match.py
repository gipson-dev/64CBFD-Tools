"""Shift descriptor matrix history and capture the current matrix."""
from pathlib import Path
import csv,hashlib,io,json,os,struct
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_descriptor_matrix_history_15188f84_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
_verified_phase=None
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
def prepare():
 global _verified_phase
 assert hashlib.sha256(MANIFEST['selected_source'].encode()).hexdigest()==MANIFEST['selected_sha256']
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'),'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256'),'conker/retail_word_patches.us.csv':MANIFEST.get('selected_guards_sha256')}
 # Verify the complete immutable bank once per fresh suite process. Recheck
 # phase and all mutable production outputs at each later gate; native full
 # input audits also bracket adoption and the installed suites.
 if _verified_phase is not None:
  assert live==_verified_phase,'Production phase changed inside qualification'
  for n in allowed:assert sha(ROOT/n)==(allowed[n]if live else MANIFEST['inputs'][n]),n
  return live
 for n,d in MANIFEST['inputs'].items():
  f=OUT/'baseline'/n
  if f.is_file():assert sha(f)==d,('Frozen input changed',n)
  assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase input changed',n)
 _verified_phase=live
 return live
def guards(raw,normal):
 words=struct.unpack('>101I',raw[0]);out=struct.unpack('>101I',normal[0]);head=(OUT/'baseline/conker/retail_word_patches.us.csv').read_bytes();buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=next(csv.reader(io.StringIO(head.decode()))),lineterminator='\n');spec=lambda v:';'.join(k+':'+n for k,n in v)or'-'
 for i,w in enumerate(words):writer.writerow(dict(filename='generated_1B5CC0',function=FUNCTION,offset=hex(4*i),expected=hex(w),replacement=hex(out[i]),expected_relocations=spec(raw[1].get(4*i,())),replacement_relocations=spec(normal[1].get(4*i,())),note='Proved closed saved-register lifetime swap and commutative operands',insert_after='',insert_after_relocations='',omit='false'))
 suffix=buf.getvalue().encode();(OUT/'guard-suffix.csv').write_bytes(suffix);(OUT/'private-guards.csv').write_bytes(head+suffix);return sha(OUT/'private-guards.csv')

def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.tests.game_descriptor_matrix_history_15188f84_normalizer import normalize
 from tools.experiments import game_descriptor_matrix_history_15188f84_objects as objects
 prepare();w=OUT/'selected-final';before,bd=compile_owner(ROOT,w,MANIFEST['old_source'],'before');after,ad=compile_owner(ROOT,w,MANIFEST['selected_source'],'candidate')
 assert same_functions(before,after,(FUNCTION,))==14 and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
 for name,key in(('selected-owner.c','selected_source'),('body.c','body'),('declarations.c','declarations')):(w/name).write_bytes(MANIFEST[key].encode())
 assert sha(w/'selected-owner.c')==MANIFEST['selected_sha256'];raw=payload(after,FUNCTION);actual=guards(raw,normalize(*raw))
 if 'selected_guards_sha256'in MANIFEST:assert actual==MANIFEST['selected_guards_sha256']
 return objects.main()
def qualify():
 inspect_source()
 from tools.experiments import game_descriptor_matrix_history_15188f84_make as make
 from tools.experiments import game_descriptor_matrix_history_15188f84_image as image
 make.main();q=image.main()
 if 'predicted_ELF_sha256'in MANIFEST:assert q['predicted_ELF_sha256']==MANIFEST['predicted_ELF_sha256']and q['metadata_permuted_records']==MANIFEST['metadata_permuted_records']
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==(OUT/'image-qualification/linked.elf').read_bytes()
 return q
if __name__=='__main__':qualify()
