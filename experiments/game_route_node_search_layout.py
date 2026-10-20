"""Checked route-search lifetime allocation and source-origin scheduling."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path
import struct

import rabbitizer

from tools.experiments import game_route_node_search_start_home as prior


core, SELECTED = prior.core, prior.SELECTED
FUNCTION, ENTRY, ROM, WORDS = prior.FUNCTION, prior.ENTRY, prior.ROM, prior.WORDS
BUILD = prior.BUILD + '/layout'
RAW_SHA, BINDING_SHA = prior.RAW_SHA, prior.BINDING_SHA
NORMALIZED_SHA = '65230441b56e2b5e7a8d7835537454d69ac450452e2268ffecc546a58f35fdf7'
OMITTED = {122, 282, 286, 339, 450}
BRANCH_TARGETS = {87: 83, 108: 146, 121: 147, 338: 445, 449: 454}
# Short-lived load/arithmetic results and the split next/current value copies.
OVERRIDES = {
    ('edge-zero-early', 92): {11: 16},
    81: {11: 15}, 82: {21: 15, 11: 3}, 83: {16: 24}, 86: {16: 3},
    85: {21: 24, 16: 24}, 88: {16: 24}, 89: {16: 25},
    90: {21: 25, 16: 25}, 91: {11: 15}, 93: {21: 15, 16: 25}, 100: {16: 25},
    101: {16: 7}, 104: {21: 11, 16: 7}, ('edge-copy', 101): {21: 7},
    114: {16: 15}, 116: {16: 15}, 123: {16: 25}, 124: {21: 25},
    128: {16: 24}, 130: {16: 24}, 131: {16: 24}, 132: {16: 15},
    134: {16: 15}, 135: {16: 15}, 136: {16: 25}, 138: {16: 25}, 139: {16: 25},
    144: {16: 7}, 145: {16: 25}, 147: {16: 7, 11: 14}, 152: {21: 14},
    149: {16: 25, 11: 14}, 150: {21: 14}, 153: {16: 25}, 154: {16: 24},
    155: {16: 14}, 156: {21: 24, 16: 25, 11: 15}, 157: {16: 24}, 158: {16: 15},
    159: {16: 15}, 160: {21: 14, 16: 24, 11: 25}, 162: {16: 25}, 163: {16: 14},
    165: {21: 15, 16: 14, 11: 24}, 166: {16: 24}, 176: {16: 15},
    178: {16: 15, 11: 14}, 179: {16: 15}, 180: {16: 14, 11: 24},
    181: {21: 24, 11: 25}, 182: {16: 15, 11: 14}, 183: {16: 14, 11: 24},
    184: {21: 24, 16: 25}, 196: {16: 15}, 197: {16: 15}, 200: {11: 14},
    201: {16: 14, 11: 25}, 202: {21: 25}, 212: {16: 24}, 213: {16: 24},
    216: {11: 15}, 217: {16: 15, 11: 14}, 218: {21: 14}, 226: {11: 25},
    227: {16: 25, 11: 24}, 228: {21: 24}, 236: {11: 15},
    237: {16: 15, 11: 14}, 238: {21: 14}, 246: {11: 25},
    247: {16: 25, 11: 24}, 248: {21: 24}, 257: {16: 11},
    258: {16: 15}, 260: {16: 15}, 283: {16: 8}, 305: {16: 8},
    326: {16: 24}, 327: {16: 16, 11: 15}, 328: {16: 16, 11: 25},
    329: {16: 15, 11: 14}, ('current-copy', 266): {21: 16},
    330: {21: 25, 16: 24}, 331: {21: 14}, 335: {16: 3}, 337: {16: 15},
    338: {21: 3}, ('neighbor-copy', 335): {21: 3}, 340: {21: 3, 16: 15},
    353: {21: 3}, 364: {21: 3}, 368: {21: 3}, 372: {21: 3}, 376: {21: 3},
    414: {11: 3}, 416: {21: 3}, 421: {11: 3}, 438: {21: 3},
    440: {11: 3}, 442: {16: 3}, 447: {16: 11},
}


def origins():
    # Coalesce the duplicate frontier store, count reloads and delayed literals.
    order = [0, 20, 1, 3, 4, 5, 6, 17, 8, 9, 10, 12, 11, 13, 14, 15,
        7, 16, 18, 19, 2, *range(21, 79), ('edge-zero-early', 92), 80, 81, 82,
        84, 83, 86, 85, 87, 88, 92, 89, 90, 91, 97, 93, 94, 79, 95, 96,
        98, 99, 100, 101, 102, 105, 104, ('edge-copy', 101), 106, 103, 107,
        *range(108, 122), ('table-home-delay', 151), *range(123, 144),
        151, 144, 145, 146, 147, 152, 149, 150, 153, 154, 155, 148,
        *range(156, 258), 259, 258, 260, 261, 262, *range(263, 282),
        283, 284, 285, *range(287, 330), ('current-copy', 266),
        *range(330, 339), ('neighbor-copy', 335), 340, 341, 346, 342, 343,
        345, 344, *range(347, 450), 454, 451, 452, 453, *range(455, 467),
        469, 468, 467, *range(470, 539)]
    kept = [x for x in order if isinstance(x, int)]
    if len(order) != 539 or len(set(kept)) != 534 or set(kept) != set(range(539)) - OMITTED:
        raise ValueError(('Route layout origins are not closed', len(order), len(set(kept))))
    return order


@lru_cache(maxsize=4096)
def fields(word):
    instruction = rabbitizer.Instruction(word)
    operands = rabbitizer.OperandType
    gp = tuple(shift for name, shift in (('cpu_rs', 21), ('cpu_rt', 16), ('cpu_rd', 11))
               if instruction.hasOperandAlias(getattr(operands, name)))
    fp = tuple(shift for name, shift in (('cpu_fs', 11), ('cpu_ft', 16), ('cpu_fd', 6))
               if instruction.hasOperandAlias(getattr(operands, name)))
    return gp, fp


def form(words, item):
    if not isinstance(item, int):
        kind, origin = item
        if kind == 'table-home-delay':
            return words[origin]
        if kind == 'edge-zero-early':
            return words[origin]
        result = words[origin] >> 16 & 31
        dest = {'edge-copy': 3, 'current-copy': 10, 'neighbor-copy': 8}[kind]
        return result << 21 | dest << 11 | 37
    word = words[item]
    if item == 258:
        # selected == count-1 becomes count == selected+1, without narrowing.
        return word & 0xFC1F0000 | (words[257] >> 21 & 31) << 21 | 1
    if item == 260:
        return word & ~(31 << 21) | (words[258] >> 21 & 31) << 21
    if item == 262:
        count = words[258] >> 21 & 31
        return 9 << 26 | count << 21 | count << 16 | 65535
    if item in (338, 449):
        return word & 0x03FFFFFF | 4 << 26
    return word


def allocation(item):
    if not isinstance(item, int):
        return {}
    if item < 78:
        if item in (1, 2, 7, 8, 15, 16, 17, 18, 19, 20):
            return {}
        return {16: 17, 17: 19, 18: 22, 30: 18, 10: 12}
    if item < 101:
        return {16: 17, 17: 19, 18: 22, 30: 18, 10: 12, 11: 13,
                9: 11, 12: 21, 19: 20, 20: 16, 21: 22}
    if item < 187:
        return {16: 17, 19: 20, 20: 16, 21: 22, 30: 15,
                10: 12, 11: 13, 12: 21, 9: 11, 8: 9, 3: 4, 7: 8, 4: 3}
    if item < 257:
        return {10: 12, 9: 11, 21: 22, 6: 8, 8: 6, 22: 23}
    if item < 307:
        return {10: 12, 18: 16, 14: 15, 15: 24, 24: 25, 25: 14}
    if item < 326:
        return {18: 16, 22: 23, 30: 3, 4: 8, 11: 13, 24: 25, 15: 24}
    if item < 447:
        return {10: 12, 21: 22, 18: 10, 17: 21, 19: 20, 20: 16,
                23: 30, 4: 8, 3: 4, 16: 17, 8: 9, 12: 31, 13: 18,
                31: 19, 9: 11, 11: 13}
    if item < 527:
        return {22: 23, 18: 21, 19: 18, 20: 19, 21: 20, 23: 22}
    return {}


def _transform(raw, bindings):
    source, relative = prior.normalize(raw, bindings)
    words = struct.unpack('>539I', source)
    order = origins()
    positions = {item: i for i, item in enumerate(order) if isinstance(item, int)}
    output, moved = [], {}
    for at, item in enumerate(order):
        word = form(words, item)
        gp = allocation(item)
        original = word
        for shift in fields(word)[0]:
            register = original >> shift & 31
            word = word & ~(31 << shift) | gp.get(register, register) << shift
        for shift, register in OVERRIDES.get(item, {}).items():
            if shift not in fields(word)[0] + fields(word)[1]:
                raise ValueError('Not a route layout register field')
            word = word & ~(31 << shift) | register << shift
        if isinstance(item, int) and prior.is_branch(words[item]):
            target = item + 1 + prior.signed16(words[item] & 65535)
            if item in BRANCH_TARGETS:
                target = BRANCH_TARGETS[item]
            elif target in positions:
                target = positions[target]
            else:
                raise ValueError('Route branch targets an omitted origin')
            if not -32768 <= target - at - 1 <= 32767:
                raise ValueError('Route layout branch displacement overflow')
            word = word & 0xFFFF0000 | ((target - at - 1) & 65535)
        output.append(word)
        if isinstance(item, int) and item * 4 in relative:
            moved[at * 4] = relative[item * 4]
    if len(output) != 539 or sum(map(len, moved.values())) != 14:
        raise ValueError('Route layout extent/bindings changed')
    return struct.pack('>539I', *output), moved


def normalize(raw, bindings):
    output, moved = _transform(raw, bindings)
    if hashlib.sha256(output).hexdigest() != NORMALIZED_SHA:
        raise ValueError('Route layout recipe/output changed')
    return output, moved


def apply_linked(words, raw, bindings):
    output, _ = normalize(raw, bindings)
    normalized = list(struct.unpack('>539I', output))
    # The predecessor verifies every source bit outside its relocation fields.
    source = prior.apply_linked(words, raw, bindings)
    _, relative = prior.normalize(raw, bindings)
    positions = {item: i for i, item in enumerate(origins()) if isinstance(item, int)}
    for at, rows in relative.items():
        mask = 0
        for kind, _ in rows:
            if kind in ('R_MIPS_HI16', 'R_MIPS_LO16'):
                mask |= 65535
            elif kind == 'R_MIPS_26':
                mask |= 0x3FFFFFF
            else:
                raise ValueError('Unsupported route layout binding')
        target = positions[at // 4]
        normalized[target] = normalized[target] & ~mask | source[at // 4] & mask
    return normalized


def original(root, output):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context = type('RouteOriginalContext', (), dict(root=root, out=output))
    return ViewListSetupTests.original.__func__(context, 'original-route-search',
        (root / 'conker/asm/B3020.s').read_text(), FUNCTION)


def qualify(root, output):
    obj, raw_words, row = core.compile_candidate(root, output, 'selected-True', SELECTED, True)
    raw, bindings = core.payload(obj)
    normalized, moved = normalize(raw, bindings)
    words = apply_linked(raw_words, raw, bindings)
    truth = list(struct.unpack_from('>539I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if words != truth:
        raise ValueError('Route layout is not literal retail')
    compound = [prior.origins()[x] if isinstance(x, int) else x for x in origins()]
    report = dict(raw_words=535, words=539, frame=1536, raw_differences=row['differences'],
        differences=0, retained_raw_origins=sum(isinstance(x, int) for x in compound),
        derived_instructions=sum(not isinstance(x, int) for x in compound),
        omitted_raw_instructions=5, bindings=14, normalized_SHA256=NORMALIZED_SHA,
        experimental_byte_exact=True, installed=False, matching_credit=0)
    (output / 'normalized.bin').write_bytes(normalized)
    (output / 'normalized-bindings.json').write_text(json.dumps(moved, indent=2) + '\n')
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return obj, raw_words, words, report


def main():
    from tools.experiments import game_route_node_search_integration as integration
    root = Path(__file__).resolve().parents[2]
    with integration.fixture_context(root):
        print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))


if __name__ == '__main__':
    main()
