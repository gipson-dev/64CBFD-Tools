"""Recover the actor preset constructor, callback ABI and complete o32 byte word."""
from pathlib import Path
import csv,hashlib,io,json,os,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_actor_preset_constructor_15196438_manifest.json').read_text());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
def prepare():
 live=installed();allowed={**MANIFEST['selected_source_hashes'],MANIFEST['object']:MANIFEST.get('padded_sha256'),'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256'),'conker/retail_word_patches.us.csv':MANIFEST.get('selected_guards_sha256')}
 if live:
  from tools.experiments.game_actor_preset_constructor_15196438_debugger import audit
  checked=audit();allowed[checked['object']]=checked['after_sha256']
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
 # Physical CSV positions differ from semantic operation correspondence.
 # The normalizer's ORDER/FIELDS and symbolic proof establish that mapping.
 def position(i):return i
 for i,w in enumerate(words):
  j=position(i);row=dict(filename='generated_1C2C60',function=FUNCTION,offset=hex(i*4),expected=hex(w),replacement=hex(retail[j]),expected_relocations=spec(refs.get(i*4,())),replacement_relocations=spec(bindings.get(j*4,())),note='Closed preset-field schedule, payload/selector roles and unsigned-byte outgoing ABI word',insert_after='',insert_after_relocations='',omit='false')
  writer.writerow(row)
 suffix=buffer.getvalue().encode();(OUT/'guard-suffix.csv').write_bytes(suffix);(OUT/'private-guards.csv').write_bytes(head+suffix)
 return sha(OUT/'private-guards.csv')
def inspect_source():
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.tests.game_owner_pool import normalized_pools
 from tools.tests.game_actor_preset_constructor_15196438_normalizer import normalize
 from tools.experiments import game_actor_preset_constructor_15196438_objects as objects
 prepare();where=OUT/'selected-final';where.mkdir(exist_ok=True);before,bd=compile_owner(ROOT,where,MANIFEST['old_source'],'before');after,ad=compile_owner(ROOT,where,MANIFEST['selected_source'],'candidate')
 assert same_functions(before,after,(FUNCTION,))==68 and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
 raw=payload(after,FUNCTION);assert hashlib.sha256(raw[0]).hexdigest()==MANIFEST['raw_sha256'];normalized=normalize(*raw)
 actual=guard_csv(raw,normalized)
 if 'selected_guards_sha256'in MANIFEST:assert actual==MANIFEST['selected_guards_sha256']
 (where/'selected-owner.c').write_text(MANIFEST['selected_source']);(where/'body.c').write_text(MANIFEST['body']);(where/'declarations.c').write_text(MANIFEST['declarations'])
 return objects.main()
def qualify():
 prepare();inspect_source()
 from tools.experiments import game_actor_preset_constructor_15196438_abi as abi
 abi.main()
 from tools.experiments import game_actor_preset_constructor_15196438_debugger as debugger
 debugger.main()
 from tools.experiments import game_actor_preset_constructor_15196438_make as make
 from tools.experiments import game_actor_preset_constructor_15196438_image as image
 make.main();q=image.main();assert q['predicted_ELF_sha256']==MANIFEST['predicted_ELF_sha256']and q['exclusions']==0 and q['metadata_permuted_records']==MANIFEST['metadata_permuted_records']
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==(OUT/'image-qualification/linked.elf').read_bytes()
 return q
