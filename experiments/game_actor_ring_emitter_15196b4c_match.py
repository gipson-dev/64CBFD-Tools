"""Recover the ring update and typed callback boundaries with closed guards."""
from pathlib import Path
import csv,hashlib,io,json,os,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_actor_ring_emitter_15196b4c_manifest.json').read_text());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
def prepare():
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'),'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256'),'conker/retail_word_patches.us.csv':MANIFEST.get('selected_guards_sha256')}
 for n,d in MANIFEST['inputs'].items():
  frozen=OUT/'baseline'/n
  if frozen.is_file():assert sha(frozen)==d,('Frozen input changed',n)
  assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase input changed',n)
 if (OUT/'private-guards.csv').exists()and 'selected_guards_sha256'in MANIFEST:assert sha(OUT/'private-guards.csv')==MANIFEST['selected_guards_sha256']
 return live
from tools.experiments.game_remaining_donor_candidates import compile_owner
def guard_csv(raw,normalized):
 data,refs=raw;changed,bindings=normalized;words=[x[0]for x in __import__('struct').iter_unpack('>I',data)];retail=[x[0]for x in __import__('struct').iter_unpack('>I',changed)]
 head=(OUT/'baseline/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(head.decode())));buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=fields,lineterminator='\n')
 def spec(x):return '|'.join(k+':'+n for k,n in x)or'-'
 # Physical CSV slots consume every expected source word, including the
 # four allocation surplus rows. The independent projection relates values.
 for i,w in enumerate(words):
  omit=i>=len(retail);row=dict(filename='generated_1C2C60',function=FUNCTION,offset=hex(i*4),expected=hex(w),replacement='0x0'if omit else hex(retail[i]),expected_relocations=spec(refs.get(i*4,())),replacement_relocations='-'if omit else spec(bindings.get(i*4,())),note='Closed actor ring emitter allocation and quiet FP schedule; independent whole transfer',insert_after='',insert_after_relocations='',omit='true'if omit else'false');writer.writerow(row)
 suffix=buffer.getvalue().encode();(OUT/'guard-suffix.csv').write_bytes(suffix);(OUT/'private-guards.csv').write_bytes(head+suffix)
 return sha(OUT/'private-guards.csv')
def inspect_source():
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.tests.game_owner_pool import normalized_pools
 from tools.tests.game_actor_ring_emitter_15196b4c_normalizer import normalize
 from tools.experiments import game_actor_ring_emitter_15196b4c_objects as objects
 prepare();where=OUT/'selected-final';where.mkdir(exist_ok=True);before,bd=compile_owner(ROOT,where,MANIFEST['old_source'],'before');after,ad=compile_owner(ROOT,where,MANIFEST['selected_source'],'candidate')
 assert same_functions(before,after,(FUNCTION,*MANIFEST['helper_names']))==66 and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
 raw=payload(after,FUNCTION);assert hashlib.sha256(raw[0]).hexdigest()==MANIFEST['raw_sha256'];normalized=normalize(*raw)
 actual=guard_csv(raw,normalized)
 if 'selected_guards_sha256'in MANIFEST:assert actual==MANIFEST['selected_guards_sha256']
 (where/'selected-owner.c').write_text(MANIFEST['selected_source']);(where/'body.c').write_text(MANIFEST['body']);(where/'declarations.c').write_text(MANIFEST['declarations'])
 from tools.experiments import game_actor_ring_emitter_15196b4c_abi as abi
 abi.main()
 return objects.main()
def qualify():
 prepare();inspect_source()
 from tools.experiments import game_actor_ring_emitter_15196b4c_abi as abi
 abi.main()
 from tools.experiments import game_actor_ring_emitter_15196b4c_make as make
 from tools.experiments import game_actor_ring_emitter_15196b4c_image as image
 make.main();q=image.main();assert q['predicted_ELF_sha256']==MANIFEST['predicted_ELF_sha256']and q['exclusions']==0 and q['metadata_permuted_records']==MANIFEST['metadata_permuted_records']
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==(OUT/'image-qualification/linked.elf').read_bytes()
 return q
