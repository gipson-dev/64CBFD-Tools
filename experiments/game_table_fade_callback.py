"""Recover four exact local table copies and a full-word fade/extent callback."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_counter_preset_match as previous
from tools.tests import counter_preset_match_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-table-fade-recovery'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516F024', 0x1516F024, 0x19C4D4, 103
TABLES, TABLE_ROM, STEP = 0x8008CBC4, 0x231684, 0x800BE9E4
MOVE, SCALE = 0x1516F864, 0x1516F94C
PATHS = dict(previous.PATHS)
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER)
build = previous.build
DECLARATIONS = '''typedef struct ByteTable11_19A8B0 {
    u8 values[11];
} ByteTable11_19A8B0;

extern ByteTable11_19A8B0 D_8008CBC4;
extern ByteTable11_19A8B0 D_8008CBD0;
extern ByteTable11_19A8B0 D_8008CBDC;
extern ByteTable11_19A8B0 D_8008CBE8;
void func_1516F864(u8 *record);
void func_1516F94C(u8 *record, u32 scale);

'''
SELECTED = '''/* Snapshot the preset tables, fade a full word, then update motion and size. */
s32 func_1516F024(u8 *record) {
    ByteTable11_19A8B0 scales = D_8008CBC4;
    ByteTable11_19A8B0 growth = D_8008CBD0;
    ByteTable11_19A8B0 limits = D_8008CBDC;
    ByteTable11_19A8B0 fades = D_8008CBE8;
    s32 index = record[0x2C];
    s32 value = record[0x1F];
    s32 limit;
    s32 extent;

    if (record[0x24] != 0) {
        limit = limits.values[index];
        if (value != limit) {
            value = (s32)((u32)value + ((u32)D_800BE9E4 << 4));
            if (value > limit) {
                value = limit;
            }
            record[0x1F] = value;
        }
    } else if (value != 0) {
        value = (s32)((u32)value - (u32)D_800BE9E4 * fades.values[index]);
        if (value < 0) {
            value = 0;
        }
        record[0x1F] = value;
    }
    if (record[0x24] == 0 && value == 0) {
        return 1;
    }
    func_1516F864(record);
    extent = (s32)((u32)*(s16 *)(record + 0x14) + (u32)D_800BE9E4 * growth.values[index]);
    *(s16 *)(record + 0x16) = extent;
    *(s16 *)(record + 0x14) = extent;
    if (index == 3) {
        *(s16 *)(record + 0x18) = 0x64;
    }
    func_1516F94C(record, scales.values[index]);
    return 0;
}
'''


INITIAL = SELECTED


def candidates():
    early_index = INITIAL.replace('    ByteTable11_19A8B0 scales', '    s32 index;\n    ByteTable11_19A8B0 scales', 1).replace(
        '    s32 index = record[0x2C];\n    s32 value = record[0x1F];', '    s32 value;').replace(
        '    s32 extent;\n', '    s32 extent;\n\n    index = record[0x2C];\n    value = record[0x1F];\n', 1)
    literals = INITIAL
    table_bytes = bytes.fromhex('fafaebebfafadcd2d2dcd200100707071408282828141400ffffffffbeaa78c83c78c80008020a01080aff0a02ff0a00')
    for index, (local, symbol) in enumerate(zip(('scales', 'growth', 'limits', 'fades'), ('D_8008CBC4', 'D_8008CBD0', 'D_8008CBDC', 'D_8008CBE8'))):
        values = ', '.join('0x%02X' % b for b in table_bytes[index * 12:index * 12 + 11])
        literals = literals.replace('ByteTable11_19A8B0 %s = %s;' % (local, symbol), 'u8 %s[11] = {%s};' % (local, values)).replace(local + '.values[', local + '[')
    active = INITIAL.replace('    s32 index = record[0x2C];', '    u8 active = record[0x24];\n    s32 index = record[0x2C];').replace('    if (record[0x24] != 0)', '    if (active != 0)')
    return dict(initial=INITIAL, early_index=early_index, literal_arrays=literals,
        active_snapshot=active, active_half_extent=active.replace('s32 extent;', 's16 extent;'),
        unsigned_index=INITIAL.replace('s32 index =', 'u32 index ='),
        byte_index=INITIAL.replace('s32 index =', 'u8 index ='),
        half_extent=INITIAL.replace('s32 extent;', 's16 extent;'),
        early_index_half_extent=early_index.replace('s32 extent;', 's16 extent;'),
        early_values=early_index.replace('    s32 index;', '    s32 index;\n    s32 value;\n    s16 extent;').replace(
            '    s32 value;\n    s32 limit;\n    s32 extent;', '    s32 limit;'))


def layouts():
    result = {}
    for order in (('value', 'extent', 'index'), ('extent', 'value', 'index'),
            ('value', 'index', 'extent'), ('index', 'extent', 'value'),
            ('value', 'extent', 'limit', 'index'), ('extent', 'limit', 'value', 'index')):
        for half in (False, True):
            body = INITIAL.replace('    s32 index = record[0x2C];\n    s32 value = record[0x1F];\n    s32 limit;\n    s32 extent;',
                '\n'.join('    s32 ' + name + ';' for name in ('index', 'value', 'limit', 'extent') if name not in order) +
                '\n\n    index = record[0x2C];\n    value = record[0x1F];')
            declarations = '\n'.join('    %s %s;' % ('s16' if half and name == 'extent' else 's32', name) for name in order)
            body = body.replace('    ByteTable11_19A8B0 scales', declarations + '\n    ByteTable11_19A8B0 scales', 1)
            result['_'.join(order) + ('_half' if half else '_word')] = body
    return result


SELECTED = layouts()['value_extent_index_word']


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed table-fade predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed table-fade baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed table-fade fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516F024() {\n    return 0;\n}':
        raise ValueError('Unknown table-fade placeholder')
    return (before[:lo] + selected.rstrip() + before[hi:]).replace('extern s32 D_800BE9E4;',
        DECLARATIONS + 'extern s32 D_800BE9E4;', 1)


def measure(root, out, label, selected=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>103I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, frame=(0x10000 - (words[0] & 65535)) & 65535,
        different_words=[(index * 4, '0x%08X' % actual, '0x%08X' % expected)
            for index, (actual, expected) in enumerate(zip(words, truth)) if actual != expected])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    if (row['words'], row['differences'], row['diagnostics']) != (103, 0, ''):
        raise ValueError('Table fade is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != 412 or list(struct.unpack_from('>103I', data, f['value'])) != words:
        raise ValueError('Table-fade production padding differs')
    return obj, padded, words, row


def recover(root, out):
    obj, words, row = measure(root, out, 'recovered')
    if (row['words'], row['differences'], row['frame'], row['diagnostics']) != (103, 19, 96, ''):
        raise ValueError('Changed table-fade recovery: ' + repr(row))
    row.update(installable=False, retail_frame=104, new_guards=0,
        reason='Eight-byte frame and incoming-home gap plus two register/scheduling groups remain')
    (out / 'recovery.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualify', action='store_true')
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--layouts', action='store_true')
    args = parser.parse_args()
    root = Path.cwd()
    if args.screen or args.layouts:
        for name, body in (layouts() if args.layouts else candidates()).items():
            row = measure(root, root / BUILD, name, body)[-1]
            print(json.dumps({k:row[k] for k in ('label', 'words', 'differences', 'frame', 'diagnostics')}), flush=True)
        return
    action = qualify if args.qualify else recover
    print(json.dumps(action(root, root / BUILD)[-1], indent=2))


if __name__ == '__main__':
    main()
