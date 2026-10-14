"""Qualify exact additional-source routines rescued by individual isolation."""
import hashlib
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_remaining_donor_candidates as build

BUILD = 'conker/build/game-isolated-byte-exact-donors'
BASELINE_ELF = '24cfbd09520fff37430e861e393647d6aa3ebffe1c85286b937cdf7276b3e2de'
TARGETS = {
    'func_150F0938': dict(owner='generated_11C2B0', words=59, body='''/* Submit the two preset descriptors through the common 16-argument helper. */
void func_150F0938(s32 context) {
    func_15160A58(context, 0x25, (s32)&D_800A1674, 2, 0x12C, 4, 0, 0xFF, 0, 0xFF, 0, -1, 0, 0, 0xFF, 1);
    func_15160A58(context, 2, (s32)&D_800A1680, 2, 0x12C, 0xD, 0xFF, 0xFF, 0xFF, 0xFF, 0, -1, 0, 0, 0xFF, 1);
}'''),
    'func_150B003C': dict(owner='generated_DC6B0', words=22, body='''/* Select the command pair, with the extra setup call in category 6. */
void func_150B003C(s32 unused) {
    if (D_800BE9F0 == 6) {
        func_15179008(0);
        func_150AF200(0xE2, 0xE1U);
        return;
    }
    func_150AF200(0xDF, 0xDEU);
}'''),
}
EXTRA = {
    'generated_11C2B0': 'extern s32 D_800A1674;\nextern s32 D_800A1680;\n'
        's32 func_15160A58(s32, s32, s32, s32, s32, s32, s32, s32, s32, s32, s32, s32, s32, s32, s32, s32);\n',
    'generated_DC6B0': 'extern s32 D_800BE9F0;\ns32 func_150AF200(s32, u8);\ns32 func_15179008(s32);\n',
}


def path(owner):
    return 'conker/src/game/' + owner + '.c'


def recover(before, owner):
    result = before
    for name, spec in TARGETS.items():
        if spec['owner'] != owner:
            continue
        pragma = re.compile(r'#pragma GLOBAL_ASM\("asm/nonmatchings/[^"\n]+/' + name + r'\.s"\)')
        if pragma.search(result):
            result = pragma.sub(lambda match: spec['body'], result, count=1)
        else:
            lo, hi = build.function_span(result, name)
            result = result[:lo] + spec['body'] + result[hi:]
    if owner in EXTRA:
        position = result.index('\n') + 1
        result = result[:position] + EXTRA[owner] + result[position:]
    return result


def freeze(root, out):
    paths = {owner: path(owner) for owner in {spec['owner'] for spec in TARGETS.values()}}
    paths.update(elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv',
        progress='conker/progress.csv', makefile='conker/Makefile')
    manifest = out / 'baseline.json'
    pins = json.loads(manifest.read_text()) if manifest.exists() else {}
    missing = set(paths) - set(pins)
    if missing:
        if hashlib.sha256((root / paths['elf']).read_bytes()).hexdigest() != BASELINE_ELF:
            raise ValueError('Refusing to extend a changed baseline')
        for key in sorted(missing):
            data = (root / paths[key]).read_bytes()
            (out / ('before-' + key)).write_bytes(data)
            pins[key] = hashlib.sha256(data).hexdigest()
        manifest.write_text(json.dumps(pins, indent=2) + '\n')
    if pins['elf'] != BASELINE_ELF:
        raise ValueError('Unexpected image baseline')
    for key, digest in pins.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed immutable input: ' + key)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    out.mkdir(exist_ok=True)
    freeze(root, out)
    rom = (root / 'conker/conker.us.bin').read_bytes()
    records = []
    for owner in sorted({spec['owner'] for spec in TARGETS.values()}):
        before = (out / ('before-' + owner)).read_text()
        after = recover(before, owner)
        obj, diagnostics = build.compile_owner(root, out, after, owner)
        emitted, functions = build.link_owner(root, out, obj, owner)
        for name, spec in TARGETS.items():
            if spec['owner'] != owner:
                continue
            info = functions[name]
            raw = emitted[info['value']:info['value'] + info['size']]
            actual = list(struct.unpack('>%dI' % (len(raw) // 4), raw))
            truth = list(struct.unpack_from('>%dI' % spec['words'], rom, int(name[5:], 16) - 0x15000000 + 0x2D4B0))
            if len(actual) > len(truth) and not any(actual[len(truth):]):
                actual = actual[:len(truth)]
            exact = actual == truth[:len(actual)] and not any(truth[len(actual):])
            record = dict(function=name, owner=owner, raw_words=len(actual), retail_words=len(truth),
                exact_content=exact, omitted_alignment_nops=len(truth)-len(actual) if exact else None,
                diagnostics=diagnostics)
            print(json.dumps({key:value for key,value in record.items() if key != 'diagnostics'}), flush=True)
            records.append(record)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')
    if not all(row['exact_content'] for row in records):
        raise SystemExit('At least one active-owner candidate is not exact')


if __name__ == '__main__':
    main()
