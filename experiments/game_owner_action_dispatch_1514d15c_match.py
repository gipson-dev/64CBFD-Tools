"""Direct 109-word owner action dispatcher and qualified byte-return interface."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_owner_action_dispatch_1514d15c_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x1514D15C;ROM=0x17A60C;WORDS=109
r=ROOT;o=OUT;b=o/'baseline';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_local_vector_transform_15117da4_match import restore_labels,assembly as _assembly
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
def assembly(data,refs,name=FUNCTION):return _assembly(data,refs,name)
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
_CHECKED=False
def prepare():
 global _CHECKED
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['guards_sha256']}
 for n,d in MANIFEST['inputs'].items():
  if not _CHECKED and(OUT/'baseline'/n).is_file():assert sha(OUT/'baseline'/n)==d,('Frozen',n)
  if not _CHECKED or n in allowed:assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase',n)
 assert sha(ROOT/'conker/retail_word_patches.us.csv')==(MANIFEST['guards_sha256'] if live else MANIFEST['inputs']['conker/retail_word_patches.us.csv']);_CHECKED=True;return live



fn=FUNCTION;owner=MANIFEST["filename"]

def compile_owner(root, out, source, name, flags=('-O2', '-g3')):
    raw, processed, obj = (out / (name + suffix) for suffix in ('.c', '-processed.c', '.o'))
    raw.write_text(source)
    processor = [sys.executable, str(TOOLROOT / 'asm-processor/asm_processor.py'), *flags,
        str(raw.relative_to(root / 'conker'))]
    preprocess = subprocess.run(processor, cwd=root / 'conker', capture_output=True, text=True, check=True)
    if preprocess.stderr:
        raise ValueError(preprocess.stderr)
    processed.write_text(preprocess.stdout)
    includes = ['.', 'include', 'include/2.0L', 'include/2.0L/PR', 'include/libc',
        'src/libultra/os', 'src/libultra/audio', 'src/libultra/io']
    command = [str(root / 'ido/ido5.3_recomp/cc'), '-c', '-32', '-G', '0', '-Xfullwarn', '-Xcpluscomm',
        '-signed', '-nostdinc', '-non_shared', '-Wab,-r4300_mul', '-D_LANGUAGE_C', '-D_FINALROM',
        '-DF3DEX_GBI_2', '-D_MIPS_SZLONG=32', '-woff', '649,838',
        *[flag for path in includes for flag in ('-I', path)], *flags, '-mips2', '-o32',
        '-o', str(obj.relative_to(root / 'conker')), str(processed.relative_to(root / 'conker'))]
    result = subprocess.run(command, cwd=root / 'conker', capture_output=True, text=True)
    diagnostics = result.stdout + result.stderr
    (out / (name + '-diagnostics.txt')).write_text(diagnostics)
    if result.returncode:
        raise ValueError(diagnostics)
    subprocess.run([*processor, '--post-process', str(obj.relative_to(root / 'conker')),
        '--assembler', 'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
        '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=root / 'conker',
        capture_output=True, text=True, check=True)
    return obj, diagnostics
def assemble(text,p):
 s=p.with_suffix('.s');s.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(p),str(s)],capture_output=True,text=True);assert q.returncode==0,q.stderr

def objects():
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original);assemble(original,o/'original-target.o');(o/'semantic-source.c').write_text(MANIFEST['selected_source'])
 prepare();source=MANIFEST['selected_source'];assert sha(o/'semantic-source.c')=='1b9ec115b87a7d8607b6f64d75e9680b80c3f8632134e78b12b3eddbb2abe7a9';(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes())
 before,old_diag=compile_owner(r,o,(b/'conker/src/game/generated_179F30.c').read_text(),'before-owner');new,diag=compile_owner(r,o,source,'selected-owner');assert diagnostic_rows(old_diag)==diagnostic_rows(diag);assert sum(diagnostic_rows(diag).values())==4
 assert same_functions(before,new,(fn,))==77 and normalized_pools(before)==normalized_pools(new)
 raw,refs=payload(new,fn);truth,tr=payload(o/'original-target.o',fn);assert raw==truth and refs==tr and len(raw)==436 and len(refs)==22 and int.from_bytes(raw[:4],'big')==0x27BDFFB8
 guards=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in guards.decode();(o/'selected-guards.csv').write_bytes(guards);(o/'guard-additions.csv').write_bytes(b'')
 assemble(assembly(truth,tr,fn),o/'normalized-target.o');where=o/'qualified-owner';where.mkdir(exist_ok=True);outputs=[]
 for mode,obj in [('before',before),('selected',new)]:
  for kind in('generic','generated'):
   text=restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt',owner,word_patches_path=b/'conker/retail_word_patches.us.csv',rodata_symbol='jtbl_800A5E20'),b/'conker/asm/179F30.s')if kind=='generic'else pg.emit_padded_assembly(obj,b/'conker/asm/179F30.s',filename=owner,word_patches_path=b/'conker/retail_word_patches.us.csv',rodata_symbol='jtbl_800A5E20');path=where/(mode+'-'+kind+'.o');assemble(text,path)
   if mode=='before':assert path.read_bytes()==(b/'conker/build/src/game/generated_179F30.c.o').read_bytes()
   else:
    assert payload(path,fn)==(truth,tr)and same_functions(where/('before-'+kind+'.o'),path,(fn,))==77 and normalized_pools(where/('before-'+kind+'.o'))==normalized_pools(path);outputs.append(path)
 assert outputs[0].read_bytes()==outputs[1].read_bytes()
 q=dict(words=109,normalized_words=109,retail_slot_words=109,frame=72,guards=0,insertions=0,omissions=0,raw_binding_positions=22,normalized_byte_exact=True,raw_byte_exact=True,raw_neighbors=77,C_definitions=78,retained_GLOBAL_ASM=0,both_complete_padders_equal=True,both_before_objects_equal_frozen=True,source_sha256=sha(o/'selected-owner.c'),padded_sha256=sha(outputs[0]),entire_guard_file_unchanged=True,new_diagnostics=0,existing_diagnostics=4,classifier_return_type_ABI_only_raw_body_unchanged=True,semantic_qualification_complete=False,source_installed=installed(),matching_credit=0)
 (o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
