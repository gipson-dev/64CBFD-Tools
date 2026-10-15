"""Match the paired factory/event routine through repeated narrowed expressions."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_paired_record_event as previous
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD = 'conker/build/game-paired-record-event-match'
OWNER, FUNCTION, ENTRY, ROM, WORDS = previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS
CALLEE, EVENT, CALLBACK = previous.CALLEE, previous.EVENT, previous.CALLBACK
PATHS, BASELINE, build, freeze = previous.PATHS, previous.BASELINE, previous.build, previous.freeze
SELECTED = '''s32 func_1000EBC4(struct00 *arg0, s32 arg1, s32 arg2, s32 arg3);
u16 func_1000FA64(u16 arg0, s16 arg1, s16 arg2, s16 arg3, s32 arg4,
                 u16 arg5, s16 arg6, s32 arg7, void *arg8,
                 s32 arg9, s32 argA, s32 argB);

/* Submit two preset-13 records, then event 7 with the live full-word context.
 * Slots 12..14 are unused, but retain the caller's arg15/arg16 positions.
 * Repeated narrowed expressions preserve IDO's shared values and spill homes. */
void func_1516F548(s32 arg0, s32 arg1, s32 arg2, s32 arg3,
                   s32 arg4, s32 arg5, s32 arg6, s32 arg7,
                   s32 arg8, s32 arg9, s32 arg10, s32 arg11,
                   s32 arg12, s32 arg13, s32 arg14, s32 arg15, s32 arg16) {
    func_1516D99C(
        (s16)arg0, (s16)arg1, (s16)arg2, 13, 0, 0x67, 0x17, 13,
        0, 0, 0x12, 0, 2, (u8)arg4, 0, (u8)arg6,
        0, 0, 0, arg10, 0, 0, 0, 0, 0, 0, 0,
        (s16)((s32)((u32)arg7 << 12) / 4096),
        (s16)((s32)((u32)arg7 << 12) / 4096),
        (s16)((s32)((u32)arg8 << 12) / 4096),
        (s16)((s32)((u32)arg8 << 12) / 4096),
        (u16)arg3, (u8)arg9, 20, 255, 16, (s16)arg5,
        200, 1, 0, 0, 1, 0, 0, 0, 0, 0, (u8)arg15, arg16);
    func_1516D99C(
        (s16)arg0, (s16)arg1, (s16)arg2, 13, 0, 0x67, 0x17, 13,
        0, 0, 0x12, 0, 2, (u8)arg4, 0, (u8)arg6,
        0, 0, 0, arg11, 0, 0, 0, 0, 0, 0, 0,
        (s16)((s32)((u32)arg7 << 12) / 4096),
        (s16)((s32)((u32)arg7 << 12) / 4096),
        (s16)((s32)((u32)arg8 << 12) / 4096),
        (s16)((s32)((u32)arg8 << 12) / 4096),
        (u16)arg3, (u8)arg9, 20, 255, 16, (s16)arg5,
        200, 1, 6, 0, 1, 0, 0, 0, 0, 0, (u8)(&arg15)[0], arg16);
    func_1000FA64(7, (s16)arg0, (s16)arg1, (s16)arg2,
                 0x36B0, 1000, 100, (s32)func_1000EBC4, (void *)arg3, 0, 0, 0);
}
'''


def recovered_owner(before):
    return previous.recovered_owner(before, SELECTED)


def measure(root, out, label='qualified', selected=None):
    return previous.measure(root, out, label, SELECTED if selected is None else selected)


def qualify(root, out):
    obj, words, row = measure(root, out)
    if (row['words'], row['differences'], row['frame'], row['diagnostics']) != (199, 0, 248, ''):
        raise ValueError('Paired-event C is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != 796 or list(struct.unpack_from('>199I', data, f['value'])) != words:
        raise ValueError('Paired-event production padding differs')
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown paired-event predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown paired-event predecessor symbol')
    result = bytearray(before)
    offset = elf_slot_offset(before, ENTRY, 796)
    result[offset:offset + 796] = rom[ROM:ROM + 796]
    struct.pack_into('>I', result, row[0] + 8, 796)
    return bytes(result)


def expected_inputs(root, out):
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        preset_owner=recovered_owner((out / 'before-preset_owner').read_text()).encode())


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
