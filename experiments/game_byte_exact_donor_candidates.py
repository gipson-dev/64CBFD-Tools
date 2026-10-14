"""Requalify three small donor bodies in the active project's ABI and headers."""
from pathlib import Path
import json
import struct
import subprocess
import sys

from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

TARGETS = {
    'func_15125628': dict(owner='game_14FF90', entry=0x15125628, rom=0x152AD8, words=26,
        body='''/* Tick the four nonzero timer bytes without wrapping zero to 255. */
void func_15125628(void) {
    s32 slot;
    for (slot = 0; slot < 4; slot++) {
        if (D_800DBFF4[slot] != 0) {
            D_800DBFF4[slot]--;
        }
    }
}'''),
    'func_1507D158': dict(owner='game_A9D90', entry=0x1507D158, rom=0xAA608, words=32,
        body='''extern u8 D_800CC40F[];
/* Submit command 3 using the selected actor's byte selector and four payload words. */
void func_1507D158(s32 actorIndex, s32 value0, s32 value1, s32 value2, s32 value3) {
    u8 selector = D_800CC40F[actorIndex * 812];
    func_1509BFB0(3, selector | 0x2000, value0, value1, value2, value3);
}'''),
    'func_151411E4': dict(owner='game_16DC80', entry=0x151411E4, rom=0x16E694, words=27,
        body='''typedef void (*ActorReleaseCallback16DC80)(struct210 *);
/* Release the attachment, decrement the live count, then dispatch the actor subtype. */
void func_151411E4(struct210 *actor) {
    struct210 *object;
    object = actor;
    if (*(vertex *volatile *)((u8 *)object + 0x154) != NULL) {
        func_1517E134(*(vertex *volatile *)((u8 *)object + 0x154), object);
    }
    *(u32 *)&D_800DC9F0 -= 1;
    ((ActorReleaseCallback16DC80)D_80089F9C[*(u8 *)((u8 *)object + 0x168)])(object);
}'''),
}


def compile_candidate(root, out, name, spec, body=None, artifact=None):
    text = '#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\n' + (body or spec['body']) + '\n'
    artifact = artifact or name
    obj, warnings = compile_owner(root, out, text, artifact)
    data, functions, relocations = parse_object(obj)
    info = functions[name]
    script = out / (artifact + '.ld')
    anchors = root / 'conker/symbol_addrs.us.txt'
    definitions = {}
    from tools.match_progress import load_symbol_addrs
    definitions.update(load_symbol_addrs(str(anchors)))
    for entries in relocations.values():
        for kind, symbol in entries:
            if symbol.startswith(('func_', 'D_')) and len(symbol) == (13 if symbol.startswith('func_') else 10):
                definitions[symbol] = int(symbol.split('_', 1)[1], 16)
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % spec['entry'])
    elf = script.with_suffix('.elf')
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', name,
        *['--defsym=%s=0x%X' % item for item in definitions.items()], '-o', str(elf), str(obj)],
        check=True, capture_output=True)
    emitted = list(struct.unpack_from('>%dI' % (info['size'] // 4), sections(elf)['.text'][1], info['value']))
    retail = list(struct.unpack_from('>%dI' % spec['words'], (root / 'conker/conker.us.bin').read_bytes(), spec['rom']))
    return dict(function=name, words=len(emitted), retail_words=len(retail), warnings=warnings,
        differences=sum(a != b for a, b in zip(emitted, retail)) + abs(len(emitted) - len(retail))), emitted


def recovered_owner(before, name):
    spec = TARGETS[name]
    body = spec['body']
    pragma = '#pragma GLOBAL_ASM("asm/nonmatchings/%s/%s.s")' % (spec['owner'], name)
    if before.count(pragma) != 1:
        raise ValueError('Expected one original assembly wrapper: ' + name)
    if name == 'func_15125628':
        start = before.index('// Decrements the four timer bytes')
        end = before.index(pragma) + len(pragma)
        return before[:start] + body + before[end:]
    if name == 'func_1507D158':
        body = body.replace('extern u8 D_800CC40F[];\n', '')
    return before.replace(pragma, body)


def compile_complete_owner(root, out, source, name):
    obj, warnings = compile_owner(root, out, source, name)
    raw = out / (name + '.c')
    result = subprocess.run([sys.executable, str(root / 'tools/asm-processor/asm_processor.py'),
        '-O2', '-g3', str(raw.relative_to(root / 'conker')), '--post-process',
        str(obj.relative_to(root / 'conker')), '--assembler',
        'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
        '--asm-prelude', str(root / 'tools/asm-processor/prelude.inc')],
        cwd=root / 'conker', capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr)
    return obj, warnings


def expected_donor_progress(before, root):
    result = before
    for name, spec in TARGETS.items():
        body = spec['body'].replace('extern u8 D_800CC40F[];\n', '')
        current = (root / ('conker/src/' + spec['owner'] + '.c')).read_text()
        if body not in current:
            continue
        matches = [line for line in result.splitlines(keepends=True) if b',' + name.encode() + b',' in line]
        if len(matches) != 1 or not matches[0].endswith((b',asm\n', b',c\n')):
            raise ValueError('Unexpected donor conversion row: ' + name)
        result = result.replace(matches[0], matches[0].replace(b',asm\n', b',c\n'))
    return result


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-byte-exact-donors'
    out.mkdir(exist_ok=True)
    records = []
    for name, spec in TARGETS.items():
        record, _ = compile_candidate(root, out, name, spec)
        records.append(record)
        print(json.dumps(record), flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
