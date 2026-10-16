"""Recover the final actor-effect switch in the 19E040 owner with real callee ABIs."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_rectangle_preset_dispatch as previous
from tools.tests import rectangle_preset_dispatch_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-actor-effect-dispatch'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19E040', 'func_15171BF4', 0x15171BF4, 0x19F0A4, 43
BODY_WORDS, SOUND, FIRST, SECOND, THIRD = 42, 0x10010154, 0x150AEEB0, 0x150BD740, 0x150CDBB0
PATHS = dict(previous.PATHS, actor_effect_first_owner='conker/src/game/generated_DC360.c',
    actor_effect_first_original='conker/asm/DC360.s', actor_effect_second_owner='conker/src/game/generated_E8C10.c',
    actor_effect_second_original='conker/asm/E8C10.s', actor_effect_third_owner='conker/src/game/generated_FB060.c',
    actor_effect_third_original='conker/asm/FB060.s', actor_effect_sound_original='conker/asm/nonmatchings/init_EB00/func_10010154.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    actor_effect_first_owner='8bcac902487f7fdcfea7bf947b6d04fce1530ceb3a3bfc90c23fd423fc8a182e',
    actor_effect_first_original='d2e9ce44982d4d2b3c76f8dee4b69453bbdcaf159a17958278738fbe872ab657',
    actor_effect_second_owner='657facc8a5ee26977f0f68db29c5b5e105052fdf1afd5693d259a8d0ccae826f',
    actor_effect_second_original='33c8abd1513e96b11b6f4495dc4d1ae1048482ca374b79bcd344c47a14d7c1a1',
    actor_effect_third_owner='f7ab58988c2f67f4d68378b81a66cd7bb7b7cad8a55e663db1afaf5dcec7a4d7',
    actor_effect_third_original='0f515694ae8d23226be0c57cc100462aa4d5ec5b759ad7848a49f2635090b2bf',
    actor_effect_sound_original='bcd2d9ba2cb0e985990ec16c3db64cd4ac8e1c29dd7c9671616cd5f1a0d7d54d')
build, POOL_ANCHOR, POOL = previous.build, previous.POOL_ANCHOR, previous.POOL
DECLARATIONS = '''void func_150AEEB0(u8 *actor, u8 flags);
void func_150BD740(u8 *actor, u8 flags, s32 mode);
void func_150CDBB0(u8 *actor, u8 flags, s32 mode);
s32 func_10010154(u16 sound, void *actor, u16 volume, s16 minimum, u16 maximum);

'''
INITIAL = '''/* Dispatch actor-specific effects; play the paired sound after the first effect. */
void func_15171BF4(u8 *actor, s32 flags) {
    flags &= 255;
    switch (actor[4]) {
        case 0x13:
        case 0x23:
            func_150AEEB0(actor, flags);
            func_10010154(0x69, actor, 0x7D00, 200, 2000);
            break;
        case 0x1E:
            func_150BD740(actor, flags, 1);
            break;
        case 0x54:
            func_150CDBB0(actor, flags, 1);
            break;
    }
}
'''
SELECTED = INITIAL.replace('s32 flags)', 'u8 flags)').replace('    flags &= 255;\n', '')
RAW_SHA256 = 'e79b7e5b12f85c709d0c21c3ecc05916859a2ee81e623346ce15947664b25f54'
RELOCATIONS = {80: [('R_MIPS_26', 'func_150AEEB0')], 108: [('R_MIPS_26', 'func_10010154')],
    124: [('R_MIPS_26', 'func_150BD740')], 140: [('R_MIPS_26', 'func_150CDBB0')]}


def freeze(root, out):
    with patch.multiple(previous, PATHS=PATHS, BASELINE=BASELINE):
        previous.freeze(root, out)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15171BF4() {\n    return 0;\n}':
        raise ValueError('Unknown actor-effect predecessor')
    marker = 'extern s32 D_800BE9F0;'
    header = '/* Non-matching placeholders for the text-only asm slice asm/19E040.s. */'
    if before.count(marker) != 1 or before.count(header) != 1:
        raise ValueError('Unknown actor-effect declaration/header anchors')
    result = before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]
    return result.replace(marker, DECLARATIONS+marker, 1).replace(header,
        '/* C reconstructions for the text-only asm slice asm/19E040.s. */', 1)


def measure(root, out, label='selected', selected=None):
    with patch.multiple(previous, recovered_owner=recovered_owner, BASELINE=BASELINE,
            FUNCTION=FUNCTION, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, PATHS=PATHS):
        return previous.measure(root, out, label, SELECTED if selected is None else selected)


def checked_object(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value']+f['size']]
    relative = {a-f['value']: v for a, v in rel.items() if f['value'] <= a < f['value']+f['size']}
    pools = {n: d for n, (_, d) in sections(obj).items()
        if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d}
    if f['size'] != 168 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relative != RELOCATIONS or pools != {'.rodata': POOL}:
        raise ValueError('Unknown actor-effect compiler words, bindings or pool')
    return raw, relative


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    checked_object(obj)
    truth = list(struct.unpack_from('>43I', (out / 'before-retail_rom').read_bytes(), ROM))
    if (row['words'], row['frame'], row['differences'], row['diagnostics']) != (42, 40, 1, '') or words != truth[:42] or truth[42] != 0:
        raise ValueError('Actor effect is not a direct body plus terminal padding match')
    if (','+FUNCTION+',').encode() in (out / 'before-guards').read_bytes():
        raise ValueError('Actor effect must not acquire instruction guards')
    row = dict(row, body_words=42, words=43, differences=0, terminal_padding_words=1, target_guards=0)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2)+'\n')
    return obj, out / 'qualified-padded.o', words+[0], row


def slot_expected_image(before, rom):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown actor-effect predecessor ELF')
    row = next(r for r in symbol_rows(before) if r[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown actor-effect predecessor extent')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 172)
    result[at:at+172] = rom[ROM:ROM+172]
    struct.pack_into('>I', result, row[0]+8, 168)
    return bytes(result)


def expected_inputs(root, out):
    return dict(elf=slot_expected_image((out / 'before-elf').read_bytes(), (out / 'before-retail_rom').read_bytes()),
        edge_wrapper_owner=recovered_owner((out / 'before-edge_wrapper_owner').read_text()).encode())


def prelink_prediction(root, out):
    core = previous.previous.previous
    with patch.multiple(core, PATHS=PATHS, BASELINE=BASELINE, qualify=qualify,
            slot_expected_image=slot_expected_image, serialize_symbols=lambda data: data):
        row = core.prelink_prediction(root, out)
    hashes = {k: hashlib.sha256(v).hexdigest() for k, v in expected_inputs(root, out).items()}
    initial = out / 'initial-prediction.json'
    if not initial.exists():
        if {k: hashlib.sha256((root / p).read_bytes()).hexdigest() for k, p in PATHS.items()} != BASELINE:
            raise ValueError('Actor-effect prediction must precede installation')
        initial.write_text(json.dumps(hashes, indent=2)+'\n')
    if json.loads(initial.read_text()) != hashes:
        raise ValueError('Changed actor-effect initial prediction')
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--prelink', action='store_true')
    args = parser.parse_args()
    row = prelink_prediction(args.root, args.root / BUILD) if args.prelink else qualify(args.root, args.root / BUILD)[3]
    print(json.dumps(row, indent=2))


if __name__ == '__main__':
    main()
