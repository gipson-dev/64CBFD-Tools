"""Screen the complete codec input refill under its existing retail-g profile."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build

BUILD = 'conker/build/game-codec-input-refill'
FUNCTION, OWNER, WORDS = 'func_151F7F60', 'game_221290', 74
BASELINE_ELF = 'bbc201571e311a6946d21093d697b0fd7c18134e861f0e162922d4952416792f'
BASELINE = dict(elf=BASELINE_ELF,
    owner='6902258a64fae5f49c0759102b1ce2d452a8e6d27b9b80efcaeaeb31377e27f8',
    makefile='0119037edc3851385ba315698fc671b615dec5b8ceac3ea080a47d4df31d758d',
    guards='017f3dca900383d0ca54117457c3610c87557b8d234ac33542838ae1730c9102',
    progress='b7d6d464014d793ad67a1b6e39e5c4e51a29dfe87e1f5c3e8c109201d3cb2c02')
GUARD_ROWS = 'game_221290,func_151F7F60,0x8C,0x018A2821,0x014C2821,-,-,Normalize commutative codec input refill callback buffer address addition,,,false\n'
BODY = '''/* Refill the codec input window, compacting bytes and padding a short read. */
s32 func_151F7F60(void *decoder) {
    s32 shiftBytes = 0x1000;
    s32 bytesRead;

    if (*(s32 *)((char *)decoder + 0x3F88) + *(s32 *)((char *)decoder + 0x201C) >= 0x1FFC) {
        bcopy((char *)decoder + shiftBytes + 0x1C, (char *)decoder + 0x1C, shiftBytes);
        *(s32 *)((char *)decoder + 0x201C) -= shiftBytes;
        *(s32 *)((char *)decoder + 0x2020) -= shiftBytes << 3;
    }

    bytesRead = ((func_151F6FD0_ReadFunc)(*(s32 *)((char *)decoder + 4)))(
        *(s32 *)decoder,
        (char *)decoder + *(s32 *)((char *)decoder + 0x201C) + 0x1C,
        *(s32 *)((char *)decoder + 0x3F88),
        -1);

    if (bytesRead < *(s32 *)((char *)decoder + 0x3F88)) {
        bzero((char *)decoder + bytesRead + 0x1C, *(s32 *)((char *)decoder + 0x3F88) - bytesRead);
    }

    *(s32 *)((char *)decoder + 0x18) += *(s32 *)((char *)decoder + 0x3F88);
    *(s32 *)((char *)decoder + 0x201C) += *(s32 *)((char *)decoder + 0x3F88);

    return *(s32 *)((char *)decoder + 0x201C) - *(s32 *)((char *)decoder + 0x3F88);
}'''
ADDRESS = '(char *)decoder + *(s32 *)((char *)decoder + 0x201C) + 0x1C'


def recover(before, body=BODY):
    lo, hi = build.function_span(before, FUNCTION)
    result = before[:lo] + body + before[hi:]
    result = result.replace('s32 func_151F7F60();\n', '')
    result = result.replace('s32 func_151F8088(void *arg0, s32 arg1);',
        's32 func_151F8088(void *arg0, s32 arg1);\ns32 func_151F7F60(void *decoder);', 1)
    return result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_221290/func_151F7F60.s. */\n', '')


def recover_makefile(before):
    old = 'func_151F6970 func_151F6B28 func_151F8088 func_151F85C4'
    if before.count(old) != 1:
        raise ValueError('Expected one codec-g function list')
    return before.replace(old, 'func_151F6970 func_151F6B28 func_151F7F60 func_151F8088 func_151F85C4').replace(
        '# neighbors in this splat owner. Select only these seven functions from -g.',
        '# neighbors in this splat owner. Select only these eight functions from -g.')


def freeze(root, out):
    paths = {'elf': 'conker/build/conker.us.elf', 'owner': 'conker/src/game_221290.c',
        'makefile': 'conker/Makefile', 'guards': 'conker/retail_word_patches.us.csv', 'progress': 'conker/progress.csv'}
    manifest = out / 'baseline.json'
    if not manifest.exists():
        values = {key: (root / path).read_bytes() for key, path in paths.items()}
        if {key: hashlib.sha256(data).hexdigest() for key, data in values.items()} != BASELINE:
            raise ValueError('Refusing to capture a changed image baseline')
        for key, data in values.items():
            (out / ('before-' + key)).write_bytes(data)
        manifest.write_text(json.dumps({key: hashlib.sha256(data).hexdigest() for key, data in values.items()}, indent=2) + '\n')
    pins = json.loads(manifest.read_text())
    if pins != BASELINE:
        raise ValueError('Changed refill baseline manifest')
    for key, digest in pins.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed immutable refill input: ' + key)


def candidates():
    yield 'donor', BODY
    replacements = {
        'integer-u32': '(void *)((u32)decoder + *(s32 *)((char *)decoder + 0x201C) + 0x1C)',
        'integer-s32': '(void *)((s32)decoder + *(s32 *)((char *)decoder + 0x201C) + 0x1C)',
        'integer-u32-both': '(void *)((u32)decoder + *(u32 *)((char *)decoder + 0x201C) + 0x1C)',
        'index': '&((char *)decoder)[*(s32 *)((char *)decoder + 0x201C) + 0x1C]',
        'offset-first': '*(s32 *)((char *)decoder + 0x201C) + (char *)decoder + 0x1C',
        'subtract-negative': '(char *)decoder - -*(s32 *)((char *)decoder + 0x201C) + 0x1C',
    }
    for label, address in replacements.items():
        yield label, BODY.replace(ADDRESS, address)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    out.mkdir(exist_ok=True)
    freeze(root, out)
    before = (out / 'before-owner').read_text()
    rom = (root / 'conker/conker.us.bin').read_bytes()
    truth = list(struct.unpack_from('>74I', rom, 0x225410))
    results = []
    for label, body in candidates():
        obj, diagnostics = build.compile_owner(root, out, recover(before, body), label, ('-g',))
        text, functions = build.link_owner(root, out, obj, OWNER)
        info = functions[FUNCTION]
        actual = list(struct.unpack('>%dI' % (info['size'] // 4), text[info['value']:info['value'] + info['size']]))
        if len(actual) > WORDS and not any(actual[WORDS:]):
            actual = actual[:WORDS]
        differences = [(i, a, b) for i, (a, b) in enumerate(zip(actual, truth)) if a != b]
        record = dict(label=label, words=len(actual), differences=differences,
            length_delta=len(actual) - WORDS, diagnostics=diagnostics)
        print(json.dumps({key: value for key, value in record.items() if key != 'diagnostics'}), flush=True)
        results.append(record)
    (out / 'candidates.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
