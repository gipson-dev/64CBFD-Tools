"""Discriminate packed RGB callback control-flow and compiler-profile hypotheses."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_packed_color_callback as source
from tools.experiments.game_actor_classifier_candidates import PROFILES

BUILD = 'conker/build/game-packed-color-control-fit'


def measure(root, out, label, body, flags=('-O2', '-g3')):
    compile_owner = source.build.compile_owner
    def compile_profile(root, out, text, name):
        run = source.build.subprocess.run
        def compiler_flags(command, *args, **kwargs):
            if str(command[0]).endswith('/ido5.3_recomp/cc'):
                if command.count('-O2') != 1 or command.count('-g3') != 1:
                    raise ValueError('Unknown normal compiler profile')
                command = [arg for arg in command if arg not in ('-O2', '-g3')] + list(flags)
            return run(command, *args, **kwargs)
        # The source is pure C; retain the supported production asm-processor mode.
        with patch.object(source.build.subprocess, 'run', compiler_flags):
            return compile_owner(root, out, text, name)
    with patch.object(source.build, 'compile_owner', compile_profile):
        obj, words, row = source.measure(root, out, label, body)
    row['profile'] = list(flags)
    row['installable'] = (row['words'], row['differences'], row['diagnostics']) == (source.WORDS, 0, '')
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


SELECTED = '''/* Fade intensity, grow both extents and interpolate the selected RGB ramp.
 * Five guards retain the start register; two preserve the unreachable return. */
s32 func_1516E8CC(u8 *record) {
    u8 *color = record;
    s32 value = record[0x1F];
    s32 phase;
    u8 *time = record;
    s32 start;
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
    value = *(s16 *)(record + 0x14);
    value = (s32)((u32)value + (u32)D_800BE9E4 * 10);
    *(s16 *)(record + 0x16) = value;
    *(s16 *)(record + 0x14) = value;
    phase = record[0x24];
    if (record[0x24] == 0) {
        phase += record[0x1F] >> 5;
    } else {
        phase += 8;
    }
    start = time[0x26];
    value = start;
    if (start < start + 8) {
        time = D_800A6E00 + start;
        do {
            if (phase >= *time) {
                weight = (f32)(phase - *time) / (f32)(time[-1] - *time);
                complement = 1.0f - weight;
                color = D_800A6E0C + value * 3;
                record[0x1C] = (u32)((f32)(u32)color[0] * complement + (f32)(u32)color[-3] * weight);
                record[0x1D] = (u32)((f32)(u32)color[1] * complement + (f32)(u32)color[-2] * weight);
                record[0x1E] = (u32)((f32)(u32)color[2] * complement + (f32)(u32)color[-1] * weight);
                break;
            }
            value++;
            time++;
        } while (value < color[0x26] + 8);
    }
    return 0;
}
'''

def candidates():
    cursor = SELECTED.replace('u8 *time = record;', 'u8 *time;').replace('start = time[0x26]', 'start = record[0x26]')
    forward = SELECTED
    for channel, offset in ((0x1C, 0), (0x1D, 1), (0x1E, 2)):
        right = '(f32)(u32)color[%d] * complement' % offset
        left = '(f32)(u32)color[%d] * weight' % (offset - 3)
        forward = forward.replace(right + ' + ' + left, left + ' + ' + right)
    return {'selected': SELECTED, 'uninitialized-cursor': cursor, 'forward-sum': forward}


def main():
    root = Path.cwd()
    out = root / BUILD
    rows = []
    for name, body in candidates().items():
        for profile in ('o2g3', 'o2', 'o1g3'):
            label = name + '-' + profile
            row = measure(root, out, label, body, PROFILES[profile])[-1]
            rows.append(row)
            print(json.dumps({key: row[key] for key in ('label', 'words', 'differences', 'diagnostics', 'installable')}), flush=True)
    (out / 'profile-screen.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
