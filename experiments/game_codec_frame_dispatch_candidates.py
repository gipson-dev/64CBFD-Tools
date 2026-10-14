"""Qualify the frame dispatcher draft against retail code and active interfaces."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build

BUILD = 'conker/build/game-codec-frame-dispatch'
FUNCTION, OWNER, WORDS, RAW_WORDS = 'func_151F86B0', 'game_221290', 112, 109
GUARDS = ((0xDC, 0x01485821, 0x010A5821), (0x10C, 0x8FAA012C, 0x8FA8012C),
    (0x110, 0x8FA80024, 0x8FAA0024), (0x118, 0x8D590004, 0x8D190004),
    (0x124, 0x8D440000, 0x8D040000), (0x12C, 0x010B2821, 0x014B2821))
GUARD_ROWS = ''.join('game_221290,func_151F86B0,0x%X,0x%08X,0x%08X,-,-,Normalize codec frame dispatch commutative addition and closed metadata-call register allocation,,,false\n' % row for row in GUARDS)
BASELINE = {
    'elf': 'a89a94186b0a4d2c0eedf36f927980489aa4e13783a642baf221de4760d11f18',
    'owner': 'd4ff5335ad0b03f85a580edd24cd6ab0ab2d6f01220d14a16c3ea6c8438cfa45',
    'makefile': 'e773e5d536287a688d5c265bc6e82f667cd2e1d24e0f1747ebc47bbdb4de449c',
    'guards': '0154601eeb05171a8af1c2ce21e4d322b0ec338142d6c0a38ea7c4bd8dd8ca24',
    'progress': 'b7d6d464014d793ad67a1b6e39e5c4e51a29dfe87e1f5c3e8c109201d3cb2c02',
}
BODY = '''/* Advance frame decoding, publish its buffers, and dispatch optional metadata. */
s32 func_151F86B0(void *decoder, void **outputBuffer, s32 *bufferCount) {
    void *context;
    s32 decoded;
    u8 metadata[0x100];
    s32 index;

    context = decoder;
    *(s32 *)((char *)context + 0x3BA0) += 1;
    if (*(s32 *)((char *)context + 0x3BA0) >= 6) {
        *(s32 *)((char *)context + 0x3BA0) = 0;
    }

    if (func_151F8088(context, *(s32 *)((char *)context + 0x8474)) == 0) {
        D_800E0E04 = 3;
        return 0;
    }

    *(s32 *)((char *)context + 0x8474) = -1;
    decoded = ((s32 (*)(void *))(*(s32 *)((char *)context + 0x8478)))(context);
    if (decoded == 0) {
        goto end;
    }

    *outputBuffer = (char *)context + *(s32 *)((char *)context + 0x3BA0) * 1160 + 0x2070;
    *bufferCount = *(s32 *)((char *)context + 0x3F8C);

    if (*(s32 *)((char *)context + 0x3BC8) != 0) {
        index = 0;
        do {
            if (((func_151F6FD0_ReadFunc)(*(s32 *)((char *)context + 4)))(
                    *(s32 *)context, &metadata[index], 1, -1) == 0) {
                break;
            }
        } while (metadata[index++]);

        if (D_800E0E00 != 0) {
            ((void (*)(s32, char *, s32))D_800E0E00)(0, (char *)metadata, strlen((char *)metadata) + 1);
        }
    }

end:
    return decoded;
}'''


def recover(before, body=BODY):
    lo, hi = build.function_span(before, FUNCTION)
    result = before[:lo] + body + before[hi:]
    result = result.replace('s32 func_151F86B0();\n', '')
    start, _ = build.function_span(body, FUNCTION)
    prototype = body[start:].split('{', 1)[0].strip() + ';'
    result = result.replace('s32 func_151F7F60(void *decoder);',
        's32 func_151F7F60(void *decoder);\n' + prototype, 1)
    return result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_221290/func_151F86B0.s. */\n', '')


def recover_makefile(before):
    old = 'func_151F7F60 func_151F8088 func_151F85C4\n'
    if before.count(old) != 1:
        raise ValueError('Expected one codec-g list')
    return before.replace(old, old.rstrip('\n') + ' func_151F86B0\n').replace(
        '# neighbors in this splat owner. Select only these eight functions from -g.',
        '# neighbors in this splat owner. Select only these nine functions from -g.')


def freeze(root, out):
    paths = {'elf': 'conker/build/conker.us.elf', 'owner': 'conker/src/game_221290.c',
        'makefile': 'conker/Makefile', 'guards': 'conker/retail_word_patches.us.csv', 'progress': 'conker/progress.csv'}
    manifest = out / 'baseline.json'
    if not manifest.exists():
        values = {key: (root / path).read_bytes() for key, path in paths.items()}
        if {key: hashlib.sha256(data).hexdigest() for key, data in values.items()} != BASELINE:
            raise ValueError('Refusing to capture changed frame-dispatch inputs')
        for key, data in values.items():
            (out / ('before-' + key)).write_bytes(data)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    pins = json.loads(manifest.read_text())
    if pins != BASELINE:
        raise ValueError('Changed frame-dispatch baseline manifest')
    for key, digest in pins.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed immutable frame-dispatch input: ' + key)


def candidates():
    yield 'typed', BODY
    declarations = '    void *context;\n    s32 decoded;\n    u8 metadata[0x100];\n    s32 index;'
    yield 'index-before-array', BODY.replace(declarations,
        '    void *context;\n    s32 decoded;\n    s32 index;\n    u8 metadata[0x100];')
    yield 'raw-outputs', BODY.replace('void **outputBuffer, s32 *bufferCount', 'void *outputBuffer, void *bufferCount').replace(
        '*outputBuffer = (char *)context', '*(s32 *)outputBuffer = (s32)((char *)context').replace(
        '* 1160 + 0x2070;', '* 1160 + 0x2070);').replace('*bufferCount = ', '*(s32 *)bufferCount = ')
    read = '((func_151F6FD0_ReadFunc)(*(s32 *)((char *)context + 4)))(\n                    *(s32 *)context, &metadata[index], 1, -1)'
    alternatives = {
        'pointer-reader': '((s32 (*)(void *, u8 *, s32, s32))(*(void **)((char *)context + 4)))(\n                    *(void **)context, &metadata[index], 1, -1)',
        'read-offset': '((func_151F6FD0_ReadFunc)(*(s32 *)((char *)context + 4)))(\n                    *(s32 *)context, metadata + index, 1, -1)',
        'read-offset-first': '((func_151F6FD0_ReadFunc)(*(s32 *)((char *)context + 4)))(\n                    *(s32 *)context, index + metadata, 1, -1)',
        'read-integer-offset': '((func_151F6FD0_ReadFunc)(*(s32 *)((char *)context + 4)))(\n                    *(s32 *)context, (void *)((u32)metadata + index), 1, -1)',
        'read-cast-index': '((func_151F6FD0_ReadFunc)(*(s32 *)((char *)context + 4)))(\n                    *(s32 *)context, metadata + (u32)index, 1, -1)',
    }
    for label, text in alternatives.items():
        yield label, BODY.replace(read, text)
    output = '(char *)context + *(s32 *)((char *)context + 0x3BA0) * 1160 + 0x2070'
    yield 'output-integer', BODY.replace(output, '(void *)((u32)context + *(s32 *)((char *)context + 0x3BA0) * 1160 + 0x2070)')
    yield 'output-offset-first', BODY.replace(output, '*(s32 *)((char *)context + 0x3BA0) * 1160 + (char *)context + 0x2070')


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    out.mkdir(exist_ok=True)
    freeze(root, out)
    before = (out / 'before-owner').read_text()
    rom = (root / 'conker/conker.us.bin').read_bytes()
    truth = list(struct.unpack_from('>112I', rom, 0x225B60))
    results = []
    for label, body in candidates():
        obj, warnings = build.compile_owner(root, out, recover(before, body), label, ('-g',))
        text, functions = build.link_owner(root, out, obj, OWNER)
        info = functions[FUNCTION]
        words = list(struct.unpack_from('>%dI' % (info['size'] // 4), text, info['value']))
        detail = dict(label=label, words=len(words), differences=[(i, a, b) for i, (a, b) in enumerate(zip(words, truth)) if a != b],
            retail_alignment_nops=WORDS-len(words) if words == truth[:len(words)] and not any(truth[len(words):]) else None,
            compiler_warnings=warnings.count('cfe: Warning'))
        print(json.dumps(detail), flush=True)
        results.append(detail)
    (out / 'candidates.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
