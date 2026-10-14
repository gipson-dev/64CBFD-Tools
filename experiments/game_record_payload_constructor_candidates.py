"""Qualify the structure-copy constructor against the complete active owner."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build

BUILD = 'conker/build/game-record-payload-constructor'
FUNCTION, OWNER, WORDS, ENTRY, ROM = 'func_1513C350', 'game_169510', 103, 0x1513C350, 0x169800
PATHS = {
    'elf': 'conker/build/conker.us.elf', 'owner': 'conker/src/game_169510.c',
    'progress': 'conker/progress.csv', 'makefile': 'conker/Makefile',
    'guards': 'conker/retail_word_patches.us.csv',
    'functions': 'conker/include/functions.h', 'structs': 'conker/include/structs.h',
    'variables': 'conker/include/variables.h',
    'original': 'conker/asm/nonmatchings/game_169510/func_1513C350.s',
}
BASELINE = {
    'elf': 'c9ff4e7ec28882546f87fb159a96b0c0e1c2b8fac6de4eb58725d91eef78a3bd',
    'owner': '1dec97c1f46d7814f8f0f009232e323c5cb1fd6e1fa9e490042646156c87e0f8',
    'progress': 'b7d6d464014d793ad67a1b6e39e5c4e51a29dfe87e1f5c3e8c109201d3cb2c02',
    'makefile': '838070597f76ea2f7182c158dfb6710946cfcabcb5435e994f93cdb99340e313',
    'guards': '25d0c541e1bd0ea1d537439e8ba4234ad629ee9c5405025cc0408d99f28e5b9a',
    'functions': '2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81',
    'structs': '081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'variables': '1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8',
    'original': '0e880e2b7b188beee29c41b8606540f01d91e9262f70973fa5ce81a7ed365fde',
}
BODY = '''/* Allocate a record, initialize its resources, and copy an optional three-word payload. */
struct210 *func_1513C350(struct210 *descriptor, s32 table, u8 tag80, u8 tag81,
                       u8 variant, s32 resourceCount, s32 userValue,
                       struct167 *payload, s32 extraBytes, u8 channel, s32 context) {
    extern void *func_15167A68(s32, s32, s32, s32, u8, u8);
    extern u8 *func_1515D480(s32);
    extern u8 *func_1515D440(void);
    struct210 *record;
    u8 category;
    s32 i;

    if (table == 0) {
        table = (s32)&D_800A4AA0;
    }
    if (descriptor->unk0 & 0x40000) {
        category = 0x4A;
    } else {
        category = 0x1B;
    }
    record = func_15167A68(category, context, extraBytes + 0xB0, 1, channel, 1);
    if (record == NULL) {
        return NULL;
    }
    memcpy(&record->unk18.i.unk0, descriptor, 0x28);
    func_1513FFF4((u8 *)&record->unk40, record->unk1E, variant);
    func_151400D0((u8 *)&record->unk40, (u8 *)table);
    record->unk80 = tag80;
    record->unk81 = tag81;
    record->unk84 = resourceCount;
    record->unk10 = 1;
    record->unk14 = 0;
    record->unkA0 = userValue;
    for (i = 0; i < 4; i++) {
        record->unk8C[i] = 0;
    }

    record->unk9C = 0;
    if (resourceCount) {
        for (i = 0; i <= D_80082FA0; i++) {
            record->unk8C[i] = (s32)func_1515D480(resourceCount);
        }
        record->unk9C = (s32)func_1515D440();
    }
    if (payload) {
        *(struct167 *)record->unkA4 = *payload;
    }
    return record;
}'''


def recover(before, body=BODY):
    marker = '#pragma GLOBAL_ASM("asm/nonmatchings/game_169510/func_1513C350.s")'
    if before.count(marker) != 1:
        raise ValueError('Expected one original constructor assembly selection')
    start = before.index(marker)
    end = before.index('\nstruct210 *func_1513C4EC(', start)
    prefix = before[:start]
    label = '/* Non-matching C placeholders for asm/nonmatchings/game_169510/func_1513C350.s. */\n'
    if not prefix.endswith(label):
        raise ValueError('Expected original constructor recovery label')
    return prefix[:-len(label)] + '\n\n' + body + '\n' + before[end:]


def expected_progress(before):
    rows = [line for line in before.splitlines(keepends=True) if b',func_1513C350,' in line]
    if len(rows) != 1 or not rows[0].endswith(b',asm\n'):
        raise ValueError('Expected one original constructor assembly row')
    return before.replace(rows[0], rows[0].replace(b',asm\n', b',c\n'))


def freeze(root, out):
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Refusing to capture changed constructor inputs')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified constructor baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable constructor input: ' + key)


def variants():
    yield 'selected', BODY
    yield 'aggregate-address', BODY.replace('(struct167 *)record->unkA4', '(struct167 *)&record->unkA4[0]')
    yield 'scalar-fields', BODY.replace('*(struct167 *)record->unkA4 = *payload;',
        'record->unkA4[0] = payload->unk0;\n        record->unkA4[1] = payload->unk4;\n        record->unkA4[2] = payload->unk8;')
    yield 'memcpy', BODY.replace('*(struct167 *)record->unkA4 = *payload;', 'memcpy(record->unkA4, payload, sizeof(*payload));')


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    out.mkdir(exist_ok=True)
    freeze(root, out)
    before = (out / 'before-owner').read_text()
    truth = list(struct.unpack_from('>103I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    rows = []
    for label, body in variants():
        obj, diagnostics = build.compile_owner(root, out, recover(before, body), label)
        data, functions = build.link_owner(root, out, obj, OWNER)
        info = functions[FUNCTION]
        words = list(struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value']))
        row = dict(label=label, words=len(words), differences=[(i, a, b) for i, (a, b) in enumerate(zip(words, truth)) if a != b],
            warnings=diagnostics.count('cfe: Warning'), flags=['-O2', '-g3'])
        rows.append(row)
        print(json.dumps(row), flush=True)
    (out / 'candidates.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
