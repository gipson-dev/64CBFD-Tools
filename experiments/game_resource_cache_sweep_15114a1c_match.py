"""Resource cache sweep: ordinary live globals, typed no-return caller ABI."""
from pathlib import Path
import csv,hashlib,io,json,os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_resource_cache_sweep_15114a1c_manifest.json').read_text());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
def prepare():
 assert hashlib.sha256(MANIFEST['selected_caller_source'].encode()).hexdigest()==MANIFEST['selected_caller_sha256'],'Caller source pin is not canonical LF'
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['caller_source']:MANIFEST['selected_caller_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'),'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256'),'conker/retail_word_patches.us.csv':MANIFEST.get('selected_guards_sha256')}
 for n,d in MANIFEST['inputs'].items():
  f=OUT/'baseline'/n
  if f.is_file():assert sha(f)==d,('Frozen input changed',n)
  assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase input changed',n)
 return live
def guards(raw,normal):
 import struct
 words=struct.unpack('>92I',raw[0]);out=struct.unpack('>94I',normal[0]);head=(OUT/'baseline/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(head.decode())));buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n');spec=lambda v:'|'.join(k+':'+n for k,n in v)or'-'
 for i,w in enumerate(words):
  j=i+int(i>=7)+int(i>=85);row=dict(filename='generated_13D350',function=FUNCTION,offset=hex(4*i),expected=hex(w),replacement=hex(out[j]),expected_relocations=spec(raw[1].get(4*i,())),replacement_relocations=spec(normal[1].get(4*j,())),note='Proved cache sweep live roles, callee-save frame and JAL delay move',insert_after='',insert_after_relocations='',omit='false')
  if i in(6,84):row.update(insert_after=hex(out[j+1]),insert_after_relocations='-')
  writer.writerow(row)
 suffix=buf.getvalue().encode();(OUT/'guard-suffix.csv').write_bytes(suffix);(OUT/'private-guards.csv').write_bytes(head+suffix);return sha(OUT/'private-guards.csv')
def inspect_source():
 from tools.experiments.game_remaining_donor_candidates import compile_owner
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.tests.game_owner_pool import normalized_pools
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.tests.game_resource_cache_sweep_15114a1c_normalizer import normalize
 from tools.experiments import game_resource_cache_sweep_15114a1c_objects as objects
 prepare();w=OUT/'selected-final';w.mkdir(exist_ok=True);before,bd=compile_owner(ROOT,w,MANIFEST['old_source'],'before');after,ad=compile_owner(ROOT,w,MANIFEST['selected_source'],'candidate')
 assert same_functions(before,after,(FUNCTION,))==33 and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
 for key,label in [('old_caller_source','caller-before'),('selected_caller_source','caller-after')]:compile_owner(ROOT,w,MANIFEST[key],label)
 from tools.pad_generated_object import parse_object
 from tools.experiments.game_texture_registration_15195dd4_objects import assemble
 from tools import pad_c_object as pc
 assert parse_object(w/'caller-before.o')==parse_object(w/'caller-after.o')and same_functions(w/'caller-before.o',w/'caller-after.o',())==16 and normalized_pools(w/'caller-before.o')==normalized_pools(w/'caller-after.o'),'Prototype repair changed caller code, bindings or pools'
 for label in('before','after'):
  f=w/('caller-'+label+'-padded.o');assemble(pc.emit_padded_assembly(w/('caller-'+label+'.o'),OUT/'baseline/conker/retail_layout.us.txt','game_45B80',word_patches_path=OUT/'baseline/conker/retail_word_patches.us.csv'),f)
  assert f.read_bytes()==(OUT/'baseline'/MANIFEST['caller_object']).read_bytes(),'Caller production object changed'
 raw=payload(after,FUNCTION);normal=normalize(*raw);actual=guards(raw,normal)
 if 'selected_guards_sha256'in MANIFEST:assert actual==MANIFEST['selected_guards_sha256']
 for n,key in [('selected-owner.c','selected_source'),('body.c','body'),('caller.c','selected_caller_source')]: (w/n).write_text(MANIFEST[key])
 return objects.main()
def qualify():
 prepare();inspect_source()
 from tools.experiments import game_resource_cache_sweep_15114a1c_make as make
 from tools.experiments import game_resource_cache_sweep_15114a1c_image as image
 make.main();q=image.main()
 if 'predicted_ELF_sha256'in MANIFEST:assert q['predicted_ELF_sha256']==MANIFEST['predicted_ELF_sha256']and q['metadata_permuted_records']==MANIFEST['metadata_permuted_records']
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==(OUT/'image-qualification/linked.elf').read_bytes()
 return q
