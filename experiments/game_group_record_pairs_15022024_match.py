"""Recover the grouped actor record lookup; qualify before counting a match."""
from pathlib import Path
import csv,hashlib,io,json,os,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_group_record_pairs_15022024_manifest.json').read_text());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
def prepare():
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'),'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256'),'conker/retail_word_patches.us.csv':MANIFEST.get('selected_guards_sha256')}
 for n,d in MANIFEST['inputs'].items():
  frozen=OUT/'baseline'/n
  if frozen.is_file():assert sha(frozen)==d,('Frozen input changed',n)
  assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase input changed',n)
 if (OUT/'private-guards.csv').exists():assert sha(OUT/'private-guards.csv')==MANIFEST['selected_guards_sha256']
 return live
def compile_owner(root,out,source,name,flags=('-O2','-g3')):
 """Use existing owner processing, then its production no-unroll compiler flag."""
 from tools.experiments.game_remaining_donor_candidates import compile_owner as base
 obj,diagnostics=base(root,out,source,name,flags);processed=out/(name+'-processed.c');c=root/'conker'
 includes=['.','include','include/2.0L','include/2.0L/PR','include/libc','src/libultra/os','src/libultra/audio','src/libultra/io']
 command=[str(root/'ido/ido5.3_recomp/cc'),'-c','-32','-G','0','-Xfullwarn','-Xcpluscomm','-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32','-woff','649,838',*[a for n in includes for a in('-I',n)],*flags,'-Wo,-loopunroll,0','-mips2','-o32','-o',obj.relative_to(c).as_posix(),processed.relative_to(c).as_posix()]
 assert 'GLOBAL_ASM'not in source
 q=subprocess.run(command,cwd=c,capture_output=True,text=True);diagnostics=q.stdout+q.stderr;(out/(name+'-diagnostics.txt')).write_text(diagnostics);assert q.returncode==0,diagnostics
 return obj,diagnostics
def guard_csv(raw,normalized):
 data,refs=raw;changed,bindings=normalized;words=[x[0]for x in __import__('struct').iter_unpack('>I',data)];retail=[x[0]for x in __import__('struct').iter_unpack('>I',changed)]
 head=(OUT/'baseline/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(head.decode())));buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=fields,lineterminator='\n')
 def spec(x):return '|'.join(k+':'+n for k,n in x)or'-'
 # Physical CSV positions differ from semantic operation correspondence.
 # The normalizer's ORDER/FIELDS and symbolic proof establish that mapping.
 insert={0:1,1:3,2:5,3:7,84:87,85:89}
 def position(i):return i if i==0 else 2 if i==1 else 4 if i==2 else 6 if i==3 else i+4 if i<=16 else i+2 if i<=84 else 88 if i==85 else 90
 for i,w in enumerate(words):
  j=position(i);row=dict(filename='generated_49D30',function=FUNCTION,offset=hex(i*4),expected=hex(w),replacement=hex(retail[j])if i not in(17,18)else hex(w),expected_relocations=spec(refs.get(i*4,())),replacement_relocations=spec(bindings.get(j*4,()))if i not in(17,18)else'-',note='Closed pair lookup saved roles, count exit and independent address schedule',insert_after='',insert_after_relocations='',omit='true'if i in(17,18)else'false')
  if i in insert:row.update(insert_after=hex(retail[insert[i]]),insert_after_relocations=spec(bindings.get(insert[i]*4,())))
  writer.writerow(row)
 suffix=buffer.getvalue().encode();(OUT/'guard-suffix.csv').write_bytes(suffix);(OUT/'private-guards.csv').write_bytes(head+suffix)
 return sha(OUT/'private-guards.csv')
def inspect_source():
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_selector_table_payload_match import diagnostic_rows
 from tools.experiments.game_paired_ground_constructor_match import payload
 from tools.tests.game_owner_pool import normalized_pools
 from tools.tests.game_group_record_pairs_15022024_normalizer import normalize
 from tools.experiments import game_group_record_pairs_15022024_objects as objects
 prepare();where=OUT/'selected-final';where.mkdir(exist_ok=True);before,bd=compile_owner(ROOT,where,MANIFEST['old_source'],'before');after,ad=compile_owner(ROOT,where,MANIFEST['selected_source'],'candidate')
 assert same_functions(before,after,(FUNCTION,))==56 and normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
 raw=payload(after,FUNCTION);assert hashlib.sha256(raw[0]).hexdigest()==MANIFEST['raw_sha256'];normalized=normalize(*raw)
 actual=guard_csv(raw,normalized)
 if 'selected_guards_sha256'in MANIFEST:assert actual==MANIFEST['selected_guards_sha256']
 (where/'selected-owner.c').write_text(MANIFEST['selected_source']);(where/'body.c').write_text(MANIFEST['body']);(where/'declarations.c').write_text(MANIFEST['declarations'])
 return objects.main()
def qualify():
 prepare();inspect_source()
 from tools.experiments import game_group_record_pairs_15022024_make as make
 from tools.experiments import game_group_record_pairs_15022024_image as image
 make.main();q=image.main();assert q['predicted_ELF_sha256']==MANIFEST['predicted_ELF_sha256']and q['exclusions']==0 and q['metadata_permuted_records']==MANIFEST['metadata_permuted_records']
 if installed():assert(ROOT/'conker/build/conker.us.elf').read_bytes()==(OUT/'image-qualification/linked.elf').read_bytes()
 return q
