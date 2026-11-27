"""Frozen source/ABI packet for the two-packet owner callback, func_1514D64C."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
TOOLROOT=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
MANIFEST=json.loads(Path(__file__).with_name('game_owner_packet_pair_1514d64c_manifest.json').read_bytes())
OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];OWNER=MANIFEST['filename']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
_CHECKED=False
def installed():
 value=sha(ROOT/MANIFEST['source'])
 assert value in (MANIFEST['inputs'][MANIFEST['source']],MANIFEST['selected_sha256']),('Unknown source',value)
 return value==MANIFEST['selected_sha256']
def prepare():
 global _CHECKED
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['guards_sha256']}
 for n,d in MANIFEST['inputs'].items():
  path=TOOLROOT/n[6:] if n.startswith('tools/') else ROOT/n
  if not _CHECKED and (OUT/'baseline'/n).is_file():assert sha(OUT/'baseline'/n)==d,('Frozen',n)
  if not _CHECKED or n in allowed:assert sha(path)==(allowed[n] if live and n in allowed else d),('Phase',n)
 for n,d in MANIFEST['task_files'].items():assert sha(TOOLROOT/n)==d,('Task file',n)
 OUT.mkdir(parents=True,exist_ok=True)
 source=OUT/'selected-source.c'
 if not source.exists():source.write_text(MANIFEST['selected_source'])
 assert sha(source)==MANIFEST['selected_sha256']
 _CHECKED=True;return live
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
