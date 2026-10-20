"""Recover route start spill and initial read order with checked C origins.

This is partial post-compile layout qualification, not a production match.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_route_node_search_captures as prior
from tools.experiments.game_actor_state_tick_spills import is_branch, signed16


core = prior.core
BUILD = prior.BUILD + '/start-home'
FUNCTION, ENTRY, ROM, WORDS = prior.FUNCTION, prior.ENTRY, prior.ROM, prior.WORDS
SELECTED = prior.SELECTED
RAW_SHA, BINDING_SHA = prior.RAW_SHA, prior.BINDING_SHA
NORMALIZED_SHA = '8b56fc62945059f660315733aeec17aec682bbed9e2b9d7f1552b40c14a3bfb4'
INSERT_BEFORE = {95: ('start-save', 12), 145: ('parent-start', 148),
                 307: ('path-start', 311), 334: ('edge-start', 336)}


def origins():
    order = []
    for i in range(535):
        if i in INSERT_BEFORE:
            order.append(INSERT_BEFORE[i])
        if i == 150:
            order.extend((151, 152, 150))
        elif i not in (151, 152):
            order.append(i)
    kept = [i for i in order if isinstance(i, int)]
    if len(order) != 539 or sorted(kept) != list(range(535)):
        raise ValueError('Unknown route start spill origins')
    return order


def _transform(raw, bindings):
    mapped, original_bindings = prior.normalize(raw, bindings)
    words = list(struct.unpack('>535I', mapped))
    for i, word in {12: 0x0080F025, 148: 0xA1FE0000, 311: 0x125E0008,
                    336: 0x109E0067, 150: 0x858E0000, 151: 0x03381021,
                    152: 0x844F0000}.items():
        if words[i] != word:
            raise ValueError('Unknown route incoming start value/use')
    if any(w >> 26 in prior.MEMORY and w >> 21 & 31 == 29 and w & 65535 == 0x600
           for w in words):
        raise ValueError('Route incoming start home is occupied')
    order = origins()
    positions = {item: i for i, item in enumerate(order) if isinstance(item, int)}
    targets = dict(positions)
    for i in INSERT_BEFORE:
        targets[i] -= 1
    targets[535] = 539
    for i, word in enumerate(words[:-1]):
        if is_branch(word) or word >> 26 in (2, 3) or word & 0xFC00003F in (8, 9):
            if positions[i + 1] != positions[i] + 1:
                raise ValueError('Route start spill separates a delay slot')
    output, moved = [], {}
    for at, item in enumerate(order):
        if not isinstance(item, int):
            # Materialize the source's real start lifetime, not unused filler.
            register = words[12] >> 11 & 31
            op = 43 if item[0] == 'start-save' else 35
            output.append(op << 26 | 29 << 21 | register << 16 | 0x600)
            continue
        word = words[item]
        if is_branch(word):
            target = item + 1 + signed16(word & 65535)
            if target in (150, 151, 152):
                raise ValueError('Route branch enters the reordered coordinate capture')
            if target not in targets:
                raise ValueError('Route branch leaves its source origins')
            displacement = targets[target] - at - 1
            if not -32768 <= displacement <= 32767:
                raise ValueError('Route start spill branch overflow')
            word = word & 0xFFFF0000 | (displacement & 65535)
        if word >> 26 == 2:
            raise ValueError('Unqualified absolute route jump')
        output.append(word)
        if item * 4 in original_bindings:
            moved[at * 4] = original_bindings[item * 4]
    if len(output) != 539 or sum(map(len, moved.values())) != 14:
        raise ValueError('Route start spill extent/bindings changed')
    return struct.pack('>539I', *output), moved


def normalize(raw, bindings):
    output, moved = _transform(raw, bindings)
    if hashlib.sha256(output).hexdigest() != NORMALIZED_SHA:
        raise ValueError('Route start spill recipe/output changed')
    return output, moved


def apply_linked(words, raw, bindings):
    output, _ = normalize(raw, bindings)
    normalized = list(struct.unpack('>539I', output))
    source = struct.unpack('>535I', raw)
    if len(words) != 535:
        raise ValueError('Unknown route start linked source extent')
    positions = {item: i for i, item in enumerate(origins()) if isinstance(item, int)}
    for i, (before, linked) in enumerate(zip(source, words)):
        mask = 0
        for kind, _ in bindings.get(i * 4, ()):
            if kind in ('R_MIPS_HI16', 'R_MIPS_LO16'):
                mask |= 0xFFFF
            elif kind == 'R_MIPS_26':
                mask |= 0x3FFFFFF
            else:
                raise ValueError('Unsupported route start spill binding')
        if (before ^ linked) & ~mask:
            raise ValueError('Linked route start source changed outside binding fields')
        at = positions[i]
        normalized[at] = normalized[at] & ~mask | linked & mask
    return normalized


def qualify(root, output):
    obj, raw_words, row = core.compile_candidate(root, output, 'selected-True', SELECTED, True)
    raw, bindings = core.payload(obj)
    normalized, moved = normalize(raw, bindings)
    words = apply_linked(raw_words, raw, bindings)
    truth = struct.unpack_from('>539I', (root / 'conker/conker.us.bin').read_bytes(), ROM)
    report = dict(raw_words=535, words=539, frame=1536, raw_differences=row['differences'],
        differences=sum(x != y for x, y in zip(words, truth)), retained_origins=535,
        start_spill_instructions=4, initial_coordinate_schedule_origins=3,
        omitted_instructions=0, bindings=14,
        normalized_SHA256=hashlib.sha256(normalized).hexdigest(), installed=False,
        partial_layout=True, matching_credit=0)
    (output / 'normalized.bin').write_bytes(normalized)
    (output / 'normalized-bindings.json').write_text(json.dumps(moved, indent=2) + '\n')
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return obj, raw_words, words, report


def captured_start(carrier='current', placement='nodes', typed_store=False):
    body = prior.SELECTED
    marker = '    D_80087298 ='
    head, code = body.split(marker, 1)
    early, late = (marker + code).split('    nodes = D_800D2350;', 1)
    early = re.sub(r'\bstart\b', carrier, early)
    if carrier == 'originalStart':
        head = head.replace('    u8 *nodes;', '    s32 originalStart;\n    u8 *nodes;', 1)
    early = '    ' + carrier + ' = start;\n' + early
    late = '    nodes = D_800D2350;' + late
    late = re.sub(r'\bstart\b', '(*(s32 *)&start)', late)
    store = ('    (*(s32 *)&start)' if typed_store else '    start') + ' = ' + carrier + ';\n'
    if placement == 'costs':
        early = early.replace('    if (D_80087290 > 0) {', store + '    if (D_80087290 > 0) {', 1)
    elif placement == 'nodes':
        late = store + late
    else:
        raise ValueError('Unknown start-home store placement')
    return head + early + late


def candidates():
    yield 'predecessor', prior.SELECTED
    for carrier in ('current', 'next', 'previous', 'originalStart'):
        for placement in ('nodes', 'costs'):
            yield carrier + '-' + placement, captured_start(carrier, placement)
    yield 'current-typed-store', captured_start(typed_store=True)


def describe(words):
    frame = (-words[0]) & 65535
    stack = [(i, hex(w), w & 65535) for i, w in enumerate(words)
             if w >> 21 & 31 == 29]
    return dict(start_home=[(i, w) for i, w, offset in stack
                           if offset == frame and int(w, 16) >> 26 in prior.MEMORY],
        avoid_home=[(i, w) for i, w, offset in stack
                    if offset == frame + 16 and int(w, 16) >> 26 in prior.MEMORY],
        frame_addresses=[(i, w, offset) for i, w, offset in stack
                         if int(w, 16) >> 26 == 9],
        F2_saves=[(i, w, offset) for i, w, offset in stack
                  if int(w, 16) >> 26 == 57 and int(w, 16) >> 16 & 31 == 2])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--names', nargs='*')
    parser.add_argument('--normalize', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.normalize:
        print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
        return
    forms = dict(candidates())
    if args.names is not None and not set(args.names) <= forms.keys():
        parser.error('Unknown start-home candidate')
    reports = []
    for name, body in forms.items():
        if args.names is None or name in args.names:
            _, words, row = core.compile_candidate(root, root / BUILD, name, body, True)
            row.update(name=name, **describe(words))
            reports.append(row)
            print(json.dumps(row), flush=True)
    (root / BUILD / 'screens.json').write_text(json.dumps(reports, indent=2) + '\n')


if __name__ == '__main__':
    main()
