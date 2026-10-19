"""Experimental actor-tick spill normalization, not a production match recipe."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.experiments import game_actor_state_tick_homes as prior


BUILD = prior.BUILD + '/spills'
SOURCE_SHA = prior.RAW_SHA256
BINDING_SHA = 'de007437c08a045267c571e223bb4c45df02245cf85fcd88de8db809d2660627'
NORMALIZED_SHA = '0752133c823e166b2ab230f03e59b5665d10ca099ccb676b93b0a8acd9f3f9d9'
SLOTS = {0xA4: 0x84, 0xA0: 0x60, 0x9C: 0x5C, 0x74: 0x7C, 0x6C: 0x74,
         0x60: 0x6C, 0x5C: 0x68, 0x50: 0x54, 0x58: 0x64, 0x80: 0x104, 0x114: 0x8C}
MEMORY = (32, 33, 35, 36, 37, 40, 41, 43, 49, 53, 57, 61)


def is_branch(word):
    return word >> 26 in (1, 4, 5, 6, 7, 20, 21, 22, 23) or word >> 26 == 17 and word >> 21 & 31 == 8


def signed16(value):
    return value if value < 32768 else value - 65536


def origins():
    # Keep the cached row pointer, and materialize the folded actor displacement.
    order = [*range(364), ('actor-bias', 363), *range(364, 399), *range(400, 678)]
    kept = [i for i in order if isinstance(i, int)]
    if len(order) != 678 or len(set(kept)) != 677 or set(kept) != set(range(678)) - {399}:
        raise ValueError('Actor-tick spill origins are not closed')
    return order


def _transform(raw, bindings):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError('Stale actor-tick spill source words')
    encoded = json.dumps(sorted((at, entries) for at, entries in bindings.items()), separators=(',', ':')).encode()
    if hashlib.sha256(encoded).hexdigest() != BINDING_SHA:
        raise ValueError('Stale actor-tick spill source bindings')
    words = list(struct.unpack('>678I', raw))
    if words[396] != 0x8FAB00C4 or words[399] != 0x01736821:
        raise ValueError('Unknown timer table/offset rematerialization')
    if words[363] != 0x01F82021 or words[364] != 0xC484F9BC or words[374] != 0xC484F9C4:
        raise ValueError('Unknown folded actor address expression')
    if is_branch(words[398]) or bindings.get(399 * 4):
        raise ValueError('Cannot omit an actor-tick delay/binding word')
    order = origins()
    positions = {item: i for i, item in enumerate(order) if isinstance(item, int)}
    positions[678] = 678
    for i, word in enumerate(words[:-1]):
        if is_branch(word) or word >> 26 in (2, 3) or word & 0xFC00003F in (8, 9):
            if i not in positions or positions.get(i + 1) != positions[i] + 1:
                raise ValueError('Actor-tick normalization separates a delay slot')
    output, moved = [], {}
    for at, item in enumerate(order):
        if not isinstance(item, int):
            base = words[item[1]] >> 11 & 31
            output.append(9 << 26 | base << 21 | base << 16 | ((-0x658) & 65535))
            continue
        word = words[item]
        op, rs, immediate = word >> 26, word >> 21 & 31, word & 65535
        if op in MEMORY and rs == 29 and immediate in SLOTS:
            word = word & 0xFFFF0000 | SLOTS[immediate]
        if item == 396:
            # Source already saved this exact row pointer before any provider.
            word = 35 << 26 | 29 << 21 | 13 << 16 | 0x7C
        if item in (364, 374):
            word = word & 0xFFFF0000 | (0x14 if item == 364 else 0x1C)
        if is_branch(words[item]):
            target = item + 1 + signed16(words[item] & 65535)
            if target not in positions:
                raise ValueError('Actor-tick branch targets an omitted/unowned word')
            displacement = positions[target] - at - 1
            if not -32768 <= displacement <= 32767:
                raise ValueError('Actor-tick normalized branch overflow')
            word = word & 0xFFFF0000 | (displacement & 65535)
        if op == 2:
            raise ValueError('Unqualified absolute actor-tick jump')
        output.append(word)
        if item * 4 in bindings:
            moved[at * 4] = bindings[item * 4]
    if len(output) != 678 or sum(map(len, moved.values())) != 62:
        raise ValueError('Actor-tick spill extent/binding ownership changed')
    return struct.pack('>678I', *output), moved


def normalize(raw, bindings):
    output, moved = _transform(raw, bindings)
    if hashlib.sha256(output).hexdigest() != NORMALIZED_SHA:
        raise ValueError('Actor-tick spill recipe/output changed')
    return output, moved


def apply_linked(words, raw, bindings):
    output, _ = normalize(raw, bindings)
    normalized = list(struct.unpack('>678I', output))
    source = struct.unpack('>678I', raw)
    if len(words) != 678:
        raise ValueError('Unknown linked actor-tick source extent')
    positions = {item: i for i, item in enumerate(origins()) if isinstance(item, int)}
    for i, (before, linked) in enumerate(zip(source, words)):
        mask = 0
        for kind, _ in bindings.get(i * 4, ()):
            if kind in ('R_MIPS_HI16', 'R_MIPS_LO16'):
                mask |= 0xFFFF
            elif kind == 'R_MIPS_26':
                mask |= 0x3FFFFFF
            else:
                raise ValueError('Unsupported actor-tick spill binding')
        if (before ^ linked) & ~mask:
            raise ValueError('Linked actor-tick source changed outside its binding fields')
        if mask:
            at = positions[i]
            normalized[at] = normalized[at] & ~mask | linked & mask
    return normalized


def qualify(root, output):
    prior.prior.prior.freeze(root, output)
    row, linked = prior.compile_candidate(root, output, 'source', prior.SELECTED)
    raw, bindings = prior.prior.prior.payload(output / 'source.o')
    normalized, moved = normalize(raw, bindings)
    words = apply_linked(linked, raw, bindings)
    truth = struct.unpack_from('>678I', (root / 'conker/conker.us.bin').read_bytes(), prior.prior.prior.ROM)
    report = dict(words=678, frame=288, retained_origins=677, omitted_pure_adds=1,
        derived_pointer_biases=1, output_bindings=sum(map(len, moved.values())),
        mapped_private_slots=len(SLOTS), real_word_differences=sum(x != y for x, y in zip(words, truth)),
        raw_sha256=row['raw_sha256'], normalized_sha256=hashlib.sha256(normalized).hexdigest(),
        installed=False, matching_credit=0, complete_private_equivalence=False)
    (output / 'normalized.bin').write_bytes(normalized)
    (output / 'normalized-bindings.json').write_text(json.dumps(moved, indent=2) + '\n')
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report, linked, words


def cached_timer(body, kind):
    body = body.replace('timers[slot]', '*(s32 *)context')
    body = prior.prior.replace(body, '*(s32 *)((u8 *)timers + offset)',
        '*(s32 *)(u32)context' if kind == 'roundtrip' else '*(s32 *)context')
    assignment = '                context = (u8 *)timers + offset;\n'
    if kind == 'word':
        body = prior.prior.replace(body, '    u8 *context;', '    u32 context;')
        body = prior.prior.replace(body, '    context = (u8 *)D_800D23B0;',
                                  '    context = (u32)D_800D23B0;')
        assignment = '                context = (u32)timers + offset;\n'
    body = prior.prior.replace(body, '                idle = 1;', assignment + '                idle = 1;')
    return body


def forms():
    return [('cached-timer-' + kind, cached_timer(prior.SELECTED, kind))
            for kind in ('byte', 'roundtrip', 'word')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names', nargs='*')
    parser.add_argument('--normalize', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    prior.prior.prior.freeze(root, output)
    if args.normalize:
        print(json.dumps(qualify(root, output)[0], indent=2))
        return
    candidates = forms()
    if args.names:
        if not set(args.names) <= dict(candidates).keys():
            parser.error('unknown actor-tick spill candidate')
        candidates = [(n, b) for n, b in candidates if n in args.names]
    for name, body in candidates:
        row, _ = prior.compile_candidate(root, output, name, body)
        print(json.dumps({k: row[k] for k in ('name', 'body_words', 'frame', 'aligned_differences',
                                             'raw_sha256', 'matched_homes', 'diagnostics')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
