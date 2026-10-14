"""Qualify the remaining linked, exact donor C without editing either checkout.

Only build fixtures are written. --prepare emits an apply_patch packet for review;
normal qualification compiles the installed source with the production headers.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import load_symbol_addrs

TARGETS = {
    'func_15008870': ('game_35D20', 48, 'Clear the selected column range in both 104-entry rows.'),
    'func_1501AF44': ('game_476D0', 87, 'Clamp rectangle edges to the current framebuffer bounds.'),
    'func_15042D94': ('game_70200', 42, 'Copy sixteen o32 variadic payload words and submit the text command.'),
    'func_1505D1C4': ('game_83300', 61, 'Initialize object slot 25 and restore the previous current-object index.'),
    'func_1506D74C': ('game_981E0', 83, 'Raise and reposition the current actor, then initialize its movement state.'),
    'func_15074980': ('game_981E0', 49, 'Set nearby actors\' chase timers using the scaled distance threshold.'),
    'func_15079228': ('game_A28B0', 46, 'Face the pointed-to path entry and consume one movement step.'),
    'func_1509B764': ('game_C8950', 43, 'Unlink and free a script node, maintaining both ends of the list.'),
    'func_150C2FCC': ('game_EF410', 48, 'Apply damping and vertical acceleration; report whether both extents remain valid.'),
    'func_15168F84': ('game_1944C0', 47, 'Return the inclusive index range for the selected group.'),
    'func_151F2E88': ('libultra/audio/game_21FC90', 727, 'Advance the stream state and emit audio commands for the requested samples.'),
    'func_151F39E4': ('libultra/audio/game_21FC90', 142, 'Update the stream volume and pan ramp, honoring output mode overrides.'),
    'func_151F3DE0': ('game_221290', 322, 'Initialize codec windows, the x^(4/3) lookup, and geometric gain tables.'),
    'func_151F42E8': ('game_221290', 788, 'Requantize one granule/channel spectrum using its gain and scalefactors.'),
    'func_151F578C': ('game_221290', 782, 'Decode MPEG-2 low-sampling-frequency scalefactors and intensity-stereo masks.'),
    'func_151F6970': ('game_221290', 110, 'Reorder short-block spectral samples, or copy the long-block spectrum.'),
    'func_151F6B28': ('game_221290', 298, 'Apply the eight butterfly rotations between adjacent long-block subbands.'),
    'func_151F8088': ('game_221290', 335, 'Synchronize and validate a frame header, then dispatch its side-info parser.'),
    'func_151F85C4': ('game_221290', 59, 'Initialize the fixed codec buffer and reject an invalid opening frame.'),
}
BUILD = 'conker/build/game-remaining-byte-exact-donors'
BASELINE_ELF = '294eba92c9b31ea335a560d67f8536a30993fc1fa429796df1c486fb532f7ddd'
ALIASES = {'gCurrentObject': 'D_800D154C', 'gCurrentObjectIndex': 'D_800C3E78', 'gObjects': 'D_800CC2D0'}


def function_span(source, name):
    # Match only definitions at column zero, then lex balanced braces while
    # ignoring comments and quoted literals. Prototypes and disabled drafts
    # cannot be mistaken for function bodies.
    matches = list(re.finditer(r'^(?:void\s*\*\s*|(?:void|s32|u32|s16|u16|f32|u8)\s+)' +
        re.escape(name) + r'\s*\([^;{}]*\)\s*\{', source, re.M))
    if len(matches) != 1:
        raise ValueError('Expected one C definition: ' + name)
    start = matches[0].start()
    opening = source.index('{', start)
    token = re.compile(r'/\*[\s\S]*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}]')
    depth = 0
    for item in token.finditer(source, opening):
        if item.group() == '{':
            depth += 1
        elif item.group() == '}':
            depth -= 1
            if depth == 0:
                return start, item.end()
    raise ValueError('Unclosed definition: ' + name)


def body(source, name):
    lo, hi = function_span(source, name)
    return source[lo:hi]


def owner_path(owner):
    return 'conker/src/' + owner + '.c'


def adapt_body(source, name):
    result = body(source, name)
    for old, new in ALIASES.items():
        result = re.sub(r'\b' + old + r'\b', new, result)
    if name == 'func_15008870':
        result = result.replace('arg0', 'mode')
    elif name == 'func_1509B764':
        result = result.replace('struct249 *arg0', 'ScriptNodeC8950 *node').replace('arg0', 'node')
        result = result.replace('D_800D2F48', 'SCRIPT_LIST_C8950')
    elif name == 'func_150C2FCC':
        result = result.replace('arg0', 'effect')
    elif name == 'func_15168F84':
        result = result.replace('arg0', 'group').replace('arg1', 'first').replace('arg2', 'last')
    return '/* ' + TARGETS[name][2] + ' */\n' + result


SCRIPT_TYPES = '''typedef struct ScriptNodeC8950 {
    u16 kind;
    u8 padding[0x16];
    struct ScriptNodeC8950 *next;
    struct ScriptNodeC8950 *prev;
} ScriptNodeC8950;
typedef struct {
    u16 length;
    u16 padding;
    ScriptNodeC8950 *unk4;
    ScriptNodeC8950 *unk8;
} ScriptListC8950;
#define SCRIPT_LIST_C8950 (*(ScriptListC8950 *)&D_800D2F48)
'''


def recovered_owner(before, donor, owner):
    result = before
    names = [name for name, (path, _, _) in TARGETS.items() if path == owner]
    for name in names:
        lo, hi = function_span(result, name)
        result = result[:lo] + adapt_body(donor, name) + result[hi:]
        prototype = body(donor, name).split('{', 1)[0].strip()
        if name == 'func_1509B764':
            prototype = prototype.replace('struct249 *arg0', 'ScriptNodeC8950 *node')
        # Remove obsolete local placeholder declarations rather than retaining
        # an incompatible return type. Add only needed forward declarations.
        result = re.sub(r'^(?:s32|void) ' + name + r'\([^;{}]*\);\n', '', result, flags=re.M)
        result = re.sub(r'/\* Non-matching C placeholders for asm/nonmatchings/' +
            re.escape(owner) + '/' + name + r'\.s\. \*/\n', '', result)
        if name in ('func_151F8088', 'func_151F85C4', 'func_151F39E4'):
            position = result.index('\n', result.index('#include')) + 1
            result = result[:position] + '\n' + prototype + ';\n' + result[position:]
    result = result.replace('// loops and loops\n', '')
    if owner == 'game_C8950':
        result = result.replace('/* Generated placeholder declarations. */', SCRIPT_TYPES + '\n/* Generated placeholder declarations. */', 1)
    elif owner == 'game_83300':
        result = result.replace('s32 func_1505F188(s32 arg0)', 's32 func_1505F188(void *arg0)')
        result = result.replace('s32 func_1505C7D8(s32 arg0, s32 arg1)', 's32 func_1505C7D8(void *arg0, s32 arg1)')
    elif owner == 'libultra/audio/game_21FC90':
        result = result.replace('/* Generated placeholder declarations. */',
            'typedef struct { u32 w0; u32 w1; } StreamAudioCommand;\n' +
            's16 _getVol();\ns16 _getRate(f32, f32, s32, void *);\n' +
            'void *func_151F85C4(s32, s32, s32);\ns32 func_151F86B0();\n\n/* Generated placeholder declarations. */', 1)
        result = result.replace('ACmdW', 'StreamAudioCommand')
        result = result.replace('D_800E0D84 = func_151F85C4(', 'D_800E0D84 = (s32)func_151F85C4(')
    elif owner == 'game_221290':
        # These declarations are private codec views, not shared ABI changes.
        preamble = donor[:function_span(donor, 'func_151F3DE0')[0]]
        preamble = preamble[:preamble.index('// Builds the analysis/synthesis')]
        preamble = preamble[preamble.index('extern f32 D_800B0C2C;'):]
        preamble = preamble.replace('s32 func_151F8960();\n', '').replace('s32 func_151F78B4();\n', '').replace('s32 func_151F6FD0();\n', '')
        # Existing unconverted functions still use the flat table view.
        preamble = preamble.replace('extern SlenTab D_800B0B0C;', '#define CODEC_SLEN_TABLE (*(SlenTab *)D_800B0B0C)')
        result = result.replace('tbl = D_800B0B0C;', 'tbl = CODEC_SLEN_TABLE;')
        position = result.index('/* Generated placeholder declarations. */')
        result = result[:position] + preamble + '\n' + result[position:]
        result = result.replace('extern s16 D_800AEB7C[];\n', '', 1)
        result = result.replace('s32 func_151F8960(void *arg0, void *arg1, s32 arg2);',
            's32 func_151F8960(void *arg0, void *arg1, s32 arg2);\ns32 func_151F6FD0();')
    # Remove superseded recovery labels immediately before the selected bodies.
    for name in names:
        role = '/* ' + TARGETS[name][2] + ' */'
        result = re.sub(r'// NON-MATCHING:[^\n]*\n(?=' + re.escape(role) + ')', '', result)
    return result


def freeze(root, out):
    paths = {'elf': 'conker/build/conker.us.elf', 'guards': 'conker/retail_word_patches.us.csv',
        'progress': 'conker/progress.csv', 'makefile': 'conker/Makefile'}
    paths.update({owner: owner_path(owner) for owner, _, _ in TARGETS.values()})
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in paths.items()}
        if hashlib.sha256(data['elf']).hexdigest() != BASELINE_ELF:
            raise ValueError('Refusing to capture a changed image as the baseline')
        for key, value in data.items():
            (out / ('before-' + key.replace('/', '_'))).write_bytes(value)
        manifest.write_text(json.dumps({key: hashlib.sha256(value).hexdigest() for key, value in data.items()}, indent=2) + '\n')
    for key, value in json.loads(manifest.read_text()).items():
        if hashlib.sha256((out / ('before-' + key.replace('/', '_'))).read_bytes()).hexdigest() != value:
            raise ValueError('Modified immutable input: ' + key)


def compile_owner(root, out, source, name, flags=('-O2', '-g3')):
    raw, processed, obj = (out / (name + suffix) for suffix in ('.c', '-processed.c', '.o'))
    raw.write_text(source)
    processor = [sys.executable, str(root / 'tools/asm-processor/asm_processor.py'), *flags,
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


def link_owner(root, out, obj, owner):
    text, functions, relocations = parse_object(obj)
    anchors = load_symbol_addrs(str(root / 'conker/symbol_addrs.us.txt'))
    symbols = subprocess.run(['mips-linux-gnu-nm', '-n', str(root / 'conker/build/conker.us.elf')],
        capture_output=True, text=True, check=True).stdout
    for line in symbols.splitlines():
        match = re.fullmatch(r'([0-9a-fA-F]+) \S (\S+)', line)
        if match and match[2] not in anchors:
            anchors[match[2]] = int(match[1], 16)
    anchors.update({name: int(name[5:], 16) for name in functions if re.fullmatch(r'func_[0-9A-F]{8}', name)})
    for entries in relocations.values():
        for _, symbol in entries:
            if re.fullmatch(r'(?:func_|D_)[0-9A-F]{8}', symbol):
                anchors[symbol] = int(symbol.split('_', 1)[1], 16)
    first = min((info['value'], name) for name, info in functions.items())[1]
    script = obj.with_suffix('.ld')
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % anchors[first])
    elf = obj.with_suffix('.elf')
    result = subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', first,
        *['--defsym=%s=0x%X' % item for item in anchors.items()],
        '-o', str(elf), str(obj)], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr)
    return sections(elf)['.text'][1], functions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    out.mkdir(exist_ok=True)
    freeze(root, out)
    owners = sorted({owner for owner, _, _ in TARGETS.values()})
    if args.prepare:
        snapshot = root / 'conker/build/alternative-source-byte-audit-20261014/snapshot'
        patches = []
        for owner in owners:
            before = (out / ('before-' + owner.replace('/', '_'))).read_text()
            donor = (snapshot / owner_path(owner)).read_text()
            recovered = recovered_owner(before, donor, owner)
            (out / ('proposed-' + owner.replace('/', '_') + '.c')).write_text(recovered)
            diff = list(difflib.unified_diff(before.splitlines(), recovered.splitlines(), n=3, lineterm=''))
            patches.append('*** Update File: ' + str(root / owner_path(owner)) + '\n' +
                '\n'.join('@@' if line.startswith('@@') else line for line in diff[2:]))
        (out / 'source.patch').write_text('*** Begin Patch\n' + '\n'.join(patches) + '\n*** End Patch\n')
    records = []
    rom = (root / 'conker/conker.us.bin').read_bytes()
    for owner in owners:
        current = (out / ('proposed-' + owner.replace('/', '_') + '.c')).read_text() if args.prepare else (root / owner_path(owner)).read_text()
        flags = ('-g',) if owner in ('game_221290', 'libultra/audio/game_21FC90') else ('-O2', '-g3')
        obj, diagnostics = compile_owner(root, out, current, 'qualified-' + owner.replace('/', '_'), flags)
        emitted, functions = link_owner(root, out, obj, owner)
        for name, (path, count, _) in TARGETS.items():
            if path != owner:
                continue
            info = functions[name]
            actual = emitted[info['value']:info['value'] + info['size']]
            address = int(name[5:], 16)
            retail = rom[address - 0x15000000 + 0x2D4B0:address - 0x15000000 + 0x2D4B0 + count * 4]
            # IDO aligns the final object function, not its retail slot.
            while len(actual) > len(retail) and actual[-4:] == b'\0\0\0\0':
                actual = actual[:-4]
            differences = sum(a != b for a, b in zip(struct.iter_unpack('>I', actual), struct.iter_unpack('>I', retail))) + abs(len(actual) - len(retail)) // 4
            record = dict(function=name, owner=owner, words=len(actual) // 4, retail_words=count,
                differences=differences, flags=flags, diagnostics=diagnostics)
            records.append(record)
            print(json.dumps({key: value for key, value in record.items() if key != 'diagnostics'}), flush=True)
    (out / 'qualification.json').write_text(json.dumps(records, indent=2) + '\n')
    if any(record['differences'] for record in records):
        raise SystemExit('At least one donor failed the strict word comparison')


if __name__ == '__main__':
    main()
