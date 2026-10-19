"""Recover the route actor event transition without editing production inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_route_actor_update_integration as previous
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_route_projection_integration import compile_profile
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-route-actor-event'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_B3020', 'func_1508802C', 0x1508802C, 0xB54DC, 51
SOURCE = 'conker/src/game/generated_B3020.c'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_B3020/func_1508802C.s")'
INPUTS = dict(previous.INPUTS, **previous.AFTER)
INPUTS['conker/asm/nonmatchings/generated_B3020/func_1508802C.s'] = 'b39962df8e9c69c8b1dcbcdc966f800629b4f766272de49077016e09d6a9781c'

DECLARATIONS = '''extern u8 D_800CC2D0[];
extern u16 D_800D18A0;
extern u8 *D_800D154C;
extern s8 D_800C3E78;
extern s32 func_1507BB28(s32, s32);
'''
SELECTED = '''/* Start an unblocked actor event and mark its route record active. */
s32 func_1508802C(u8 *record, u8 *actor, s32 reason) {
    u8 *state;
    s32 slot;

    state = *(u8 **)(actor + 0x31C);
    if (state[0x120] != 0) {
        return 1;
    }
    slot = (s32)((u32)actor - (u32)D_800CC2D0) / 0x32C;
    if (D_800D18A0 & (1U << slot)) {
        return 1;
    }
    state[0x84] = 1;
    *(s32 *)actor = 0xC;
    actor[0x232] = reason;
    D_800D154C = actor;
    D_800C3E78 = *(s8 *)(record + 0x31);
    *(s32 *)(actor + 0x218) = func_1507BB28(0, reason);
    *(u16 *)(actor + 0x21C) = 0;
    actor[0x125] = 0xFF;
    record[0x30] = 2;
    return 0;
}
'''
MASKED = SELECTED.replace('1U << slot', '1U << (slot & 31)')


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, digest in INPUTS.items():
        leaf = out / ('before-' + name.replace('/', '_'))
        if not leaf.exists():
            data = (root / name).read_bytes()
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError('Unknown event-transition predecessor: ' + name)
            leaf.write_bytes(data)
        data = leaf.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Changed immutable event-transition input: ' + name)
        result[name] = data
    return result


def recovered_owner(before, body=SELECTED):
    old = '    extern void func_1508802C(u8 *, u8 *, s32);'
    if before.count(ORIGINAL) != 1 or before.count(old) != 1:
        raise ValueError('Unknown event-transition assembly/declaration baseline')
    return before.replace(old, old.replace('void', 's32')).replace(
        ORIGINAL, DECLARATIONS + '\n' + body.rstrip())


def payload(obj):
    text, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    words = list(struct.unpack('>%dI' % (len(raw) // 4), raw))
    end = max(i for i, word in enumerate(words) if word == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero event-transition alignment tail')
    bindings = {at - f['value']: entries for at, entries in relocations.items()
                if f['value'] <= at < f['value'] + end * 4}
    return raw[:end * 4], bindings


def compile_candidate(root, out, name='selected', body=SELECTED, whole=False, normal=False):
    values = freeze(root, out)
    source = recovered_owner(values[SOURCE].decode(), body) if whole else (
        '#include <ultra64.h>\n' + DECLARATIONS + '\n' + body)
    obj, diagnostics = compile_profile(root, out, source, name, normal)
    image, functions = link_owner(root, out, obj, OWNER)
    raw, bindings = payload(obj)
    at = functions[FUNCTION]['value']
    code = image[at:at + len(raw)]
    words = struct.unpack('>%dI' % (len(code) // 4), code)
    truth = struct.unpack_from('>%dI' % WORDS, values['conker/conker.us.bin'], ROM)
    row = dict(name=name, words=len(words), frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, raw_SHA256=hashlib.sha256(raw).hexdigest(), bindings=bindings)
    (out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, list(words), row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--whole', action='store_true')
    parser.add_argument('--screens', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    forms = [('masked', MASKED), ('slot-domain', SELECTED)] if args.screens else [('selected', SELECTED)]
    for name, body in forms:
        _, _, row = compile_candidate(root, root / BUILD, name, body, whole=args.whole)
        print(json.dumps(row, indent=2), flush=True)


if __name__ == '__main__':
    main()
