"""Recover the packed-record intensity/extent/RGB callback against retail."""
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_packed_coordinate_expression_fit as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import packed_coordinate_match_checkpoint as checkpoint

BUILD = 'conker/build/game-packed-color-callback'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516E8CC', 0x1516E8CC, 0x19BD7C, 248
PATHS = dict(previous.PATHS, table_original='conker/asm/data/24B8C0.rodata.s',
    data_config='conker/conker.us.yaml')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    table_original='2f80072f25446241d36ad865a4a17126cfd5501df8bdd26f2bb01d12fc3f72ed',
    data_config='d31a14128e74793a2cc5fcb7ca3a65abefc7cafe01528268b0e0af76f94bff1f')
SELECTED = '''/* Fade intensity, grow both extents and interpolate the selected RGB ramp. */
s32 func_1516E8CC(u8 *record) {
    s32 value = record[0x1F];
    s32 phase;
    s32 index;
    u8 *time;
    u8 *color;
    f32 weight;
    f32 complement;

    if (record[0x24] != 0) {
        if (value != 0xFF) {
            value = (s32)((u32)value + ((u32)D_800BE9E4 << 5));
            if (value >= 0x100) {
                value = 0xFF;
            }
            record[0x1F] = value;
        }
    } else if (value != 0) {
        value = (s32)((u32)value - ((u32)D_800BE9E4 << 4));
        if (value < 0) {
            value = 0;
        }
        record[0x1F] = value;
    }
    if (record[0x24] == 0 && value == 0) {
        return 1;
    }
    value = (s32)((u32)(s32)*(s16 *)(record + 0x14) + (u32)D_800BE9E4 * 10);
    *(s16 *)(record + 0x16) = value;
    *(s16 *)(record + 0x14) = value;
    if (record[0x24] == 0) {
        phase = record[0x24] + (record[0x1F] >> 5);
    } else {
        phase = record[0x24] + 8;
    }
    for (index = record[0x26], time = D_800A6E00 + index;
         index < record[0x26] + 8; index++, time++) {
        if (phase >= *time) {
            weight = (f32)(phase - *time) / (f32)(time[-1] - *time);
            complement = 1.0f - weight;
            color = D_800A6E0C + index * 3;
            record[0x1C] = (u32)((f32)(u32)color[-3] * weight + (f32)(u32)color[0] * complement);
            record[0x1D] = (u32)((f32)(u32)color[-2] * weight + (f32)(u32)color[1] * complement);
            record[0x1E] = (u32)((f32)(u32)color[-1] * weight + (f32)(u32)color[2] * complement);
            break;
        }
    }
    return 0;
}
'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        actual = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if actual != BASELINE:
            raise ValueError('Changed packed-color predecessor: ' + repr({k: v for k, v in actual.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed packed-color baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed packed-color fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516E8CC() {\n    return 0;\n}':
        raise ValueError('Unknown packed-color placeholder')
    body = before[:lo] + selected.rstrip() + before[hi:]
    return body.replace('extern s32 D_800BE9E4;',
        'extern s32 D_800BE9E4;\nextern u8 D_800A6E00[];\nextern u8 D_800A6E0C[];', 1)


def measure(root, out, label, selected=SELECTED, no_unroll=False):
    freeze(root, out)
    run = build.subprocess.run
    def profile(command, *args, **kwargs):
        if no_unroll and str(command[0]).endswith('/ido5.3_recomp/cc'):
            command = [*command, '-Wo,-loopunroll,0']
        return run(command, *args, **kwargs)
    with patch.object(build.subprocess, 'run', profile):
        obj, diagnostics = build.compile_owner(root, out,
            recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, fs = build.link_owner(root, out, obj, OWNER)
    f = fs[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b)
            for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def candidates():
    loop = '''    index = record[0x26];
    if (index < record[0x26] + 8) {
        time = D_800A6E00 + index;
loop:
        if (phase >= *time) {'''
    explicit = SELECTED.replace('''    for (index = record[0x26], time = D_800A6E00 + index;
         index < record[0x26] + 8; index++, time++) {
        if (phase >= *time) {''', loop).replace('''            break;
        }
    }
    return 0;''', '''        } else {
            index++;
            time++;
            if (index < record[0x26] + 8) {
                goto loop;
            }
        }
    }
    return 0;''')
    operands = explicit.replace('    f32 weight;', '    u32 previous;\n    u32 current;\n    f32 weight;')
    for channel, offset in ((0x1C, 0), (0x1D, 1), (0x1E, 2)):
        expr = '(u32)((f32)(u32)color[%d] * weight + (f32)(u32)color[%d] * complement)' % (offset - 3, offset)
        operands = operands.replace('            record[0x%X] = ' % channel + expr + ';',
            '            previous = (u32)color[%d];\n            current = (u32)color[%d];\n' % (offset - 3, offset) +
            '            record[0x%X] = (u32)((f32)previous * weight + (f32)current * complement);' % channel)
    duplicate = operands.replace('''        }
    }
    return 0;
}''', '''        }
        return 0;
    }
    return 0;
}''')
    return {'initial': SELECTED, 'goto': explicit, 'integer-operands': operands,
        'duplicate-return': duplicate}


def require_direct_match(row):
    if (row['words'], row['differences'], row['diagnostics']) != (WORDS, 0, ''):
        raise ValueError('Packed-color callback is not a direct match')


def main():
    root = Path.cwd()
    rows = []
    for label, body in candidates().items():
        for no_unroll in (False, True):
            name = label + ('-no-unroll' if no_unroll else '')
            row = measure(root, root / BUILD, name, body, no_unroll)[-1]
            row['profile'] = ['-O2', '-g3'] + (['-Wo,-loopunroll,0'] if no_unroll else [])
            row['installable'] = (row['words'], row['differences'], row['diagnostics']) == (WORDS, 0, '')
            rows.append(row)
            print(json.dumps({k: row[k] for k in ('label', 'words', 'differences', 'diagnostics', 'installable')}), flush=True)
    (root / BUILD / 'screen.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
