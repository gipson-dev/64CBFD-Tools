"""Checked actor-tick source origins and frame roles; never installs guards."""

import argparse
import collections
import csv
import hashlib
import io
import json
import struct
from pathlib import Path

from tools.experiments import game_actor_state_tick_draw as source
from tools.experiments.game_actor_state_tick_spills import is_branch, signed16


BUILD = source.BUILD + '/match'
RAW_SHA = source.RAW_SHA256
BINDING_SHA = '449c7456ea2d4a9f6df7e195bbe27a810b6d08ececef40ca52232167582f4a49'
NORMALIZED_SHA = 'a7b81de694c806ad2ca87ce823c3ebc8bfeb6ec23f432ecddaafdc7ec33d1fff'
SLOTS = {0xA4: 0x84, 0xFC: 0x60, 0x9C: 0x5C, 0x70: 0x7C, 0x68: 0x74,
         0x60: 0x6C, 0x5C: 0x68, 0x58: 0x64, 0x114: 0x8C}
MEMORY = (32, 33, 35, 36, 37, 40, 41, 43, 49, 53, 57, 61)
REMOVED = {390, 398, 422}
SCHEDULE = {
    78: [79, 81, 84, 87, 88, 90, 91, 83, 78, 103, 82, 92, 80, 93, 95, 100, 96, 97, 94, 99, 101, 102, 98, 85, 104, 105, 106, 108, 86],
    108: [109, 110, 111, 112, 114, 89, 113],
    228: [229, 230, 228],
    236: [237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 236],
    423: [428, 423, 424, 425, 426, 427],
    524: [525, 524],
    549: [551],
    551: [549],
}
REGISTERS = {
    25: {16: 5}, 44: {16: 2}, 45: {16: 3},
    46: {21: 5}, 50: {16: 2}, 51: {16: 3},
    54: {16: 5}, 73: {16: 13}, 74: {11: 12},
    75: {11: 12, 21: 12}, 76: {11: 12, 16: 12}, 77: {11: 12, 21: 12},
    79: {11: 12, 16: 12}, 81: {11: 12, 21: 12}, 84: {11: 12, 16: 12},
    87: {11: 12, 21: 12}, 88: {16: 13}, 90: {16: 13, 21: 13},
    91: {11: 12, 16: 12}, 83: {16: 14}, 78: {11: 19, 16: 13, 21: 12},
    103: {16: 12}, 82: {16: 25}, 92: {11: 11, 16: 16, 21: 10},
    93: {11: 15, 21: 14}, 95: {16: 11}, 100: {16: 13},
    96: {16: 24}, 97: {16: 15}, 94: {11: 3, 21: 12},
    99: {11: 10, 21: 25}, 102: {16: 15}, 98: {16: 10},
    85: {16: 10}, 104: {16: 25}, 105: {21: 11},
    106: {11: 14, 21: 13}, 108: {11: 23, 21: 24}, 86: {16: 11},
    107: {16: 25, 21: 25}, 110: {11: 24, 21: 15}, 111: {16: 24},
    114: {16: 25}, 89: {16: 11}, 113: {16: 14},
    116: {11: 22, 21: 10}, 228: {11: 13}, 239: {16: 12},
    253: {16: 4}, 254: {16: 14}, 255: {16: 4},
    256: {11: 15, 16: 4}, 275: {16: 4}, 276: {21: 4},
    277: {16: 10}, 283: {16: 10}, 294: {21: 4},
    323: {11: 6}, 324: {16: 10}, 326: {6: 8, 16: 6},
    330: {11: 8}, 334: {6: 6}, 337: {16: 6},
    339: {11: 8}, 340: {16: 16}, 342: {6: 10, 16: 8},
    346: {11: 10}, 349: {16: 4}, 350: {21: 4},
    353: {11: 25, 16: 4}, 354: {11: 25, 16: 4, 21: 25}, 355: {11: 25, 16: 25},
    356: {11: 25, 16: 4, 21: 25}, 357: {11: 25, 16: 25}, 358: {11: 25, 16: 4, 21: 25},
    359: {11: 25, 16: 25}, 360: {11: 25, 16: 4, 21: 25}, 361: {11: 25, 16: 25},
    'actor-bias': {21: 25}, 362: {11: 3}, 363: {21: 3},
    364: {16: 6}, 365: {16: 13}, 366: {6: 8, 16: 6},
    367: {21: 13}, 369: {6: 10, 11: 8}, 370: {16: 10},
    372: {16: 6}, 373: {21: 3}, 374: {16: 14},
    375: {6: 8, 16: 6}, 376: {21: 14}, 377: {16: 10},
    378: {11: 8}, 379: {11: 10}, 381: {16: 3},
    382: {16: 3, 21: 3}, 383: {16: 15}, 384: {16: 24},
    386: {11: 24, 16: 3, 21: 24}, 387: {16: 24, 21: 24}, 388: {16: 2, 21: 15},
    288: {11: 6}, 389: {16: 11}, 391: {16: 2, 21: 24},
    394: {21: 15}, 395: {16: 25}, 396: {16: 11},
    397: {16: 3}, 399: {16: 3, 21: 3}, 400: {16: 2, 21: 25},
    401: {21: 2}, 403: {16: 10}, 404: {21: 10},
    405: {11: 12, 16: 3}, 406: {16: 6}, 407: {11: 12, 16: 3},
    408: {16: 12}, 413: {16: 13}, 414: {21: 13},
    424: {11: 15}, 425: {11: 11, 16: 15, 21: 3}, 426: {16: 11},
    427: {16: 25}, 429: {21: 25}, 430: {16: 8},
    431: {16: 10}, 432: {11: 12, 16: 8, 21: 10}, 433: {11: 13, 16: 12},
    434: {16: 13, 21: 8}, 436: {16: 15}, 437: {16: 24},
    438: {21: 15}, 439: {16: 11}, 440: {21: 24},
    441: {16: 11}, 442: {16: 25}, 445: {16: 25},
    447: {16: 10}, 448: {16: 12, 21: 10}, 450: {21: 12},
    451: {16: 13}, 453: {16: 13}, 454: {21: 13},
    456: {16: 10}, 458: {11: 15}, 459: {21: 15},
    460: {16: 11}, 461: {11: 25, 21: 11}, 463: {21: 25},
    466: {16: 10}, 467: {16: 10, 21: 10}, 468: {6: 6},
    469: {16: 12}, 470: {11: 12, 16: 10, 21: 12}, 471: {16: 12, 21: 12},
    472: {6: 8, 11: 6}, 473: {11: 8}, 475: {21: 12},
    477: {16: 10}, 483: {16: 10}, 484: {16: 15},
    486: {11: 11, 21: 15}, 488: {21: 11}, 489: {16: 10},
    490: {16: 25}, 491: {11: 13, 21: 10}, 492: {16: 25, 21: 13},
    500: {16: 12}, 501: {11: 15}, 503: {16: 12, 21: 15},
    505: {11: 11}, 506: {21: 11}, 507: {16: 10},
    508: {21: 10}, 509: {16: 2}, 510: {16: 25},
    513: {16: 13, 21: 25}, 514: {21: 13}, 515: {16: 2},
    517: {16: 12}, 519: {11: 12, 21: 12}, 520: {16: 12, 21: 12},
    521: {11: 15, 16: 12}, 522: {16: 15}, 523: {16: 2},
    525: {16: 3, 21: 2}, 524: {16: 11, 21: 2}, 526: {21: 3},
    527: {16: 11}, 529: {16: 25}, 530: {16: 13, 21: 25},
    531: {21: 13}, 532: {16: 24}, 533: {16: 14},
    534: {16: 12}, 535: {21: 14}, 536: {16: 15},
    537: {16: 12, 21: 15}, 538: {16: 24}, 539: {16: 25},
    540: {16: 11, 21: 24}, 541: {21: 11}, 544: {21: 25},
    545: {21: 13}, 546: {16: 12}, 547: {16: 14},
    548: {16: 14, 21: 12}, 550: {16: 11}, 549: {16: 25},
    552: {16: 14}, 554: {16: 24, 21: 15}, 555: {21: 11},
    556: {16: 13, 21: 25}, 557: {16: 13}, 559: {16: 24},
    560: {16: 14}, 563: {16: 12}, 566: {16: 12},
    570: {11: 10}, 571: {16: 15}, 572: {11: 10},
    574: {21: 15}, 576: {16: 24}, 577: {21: 24},
    581: {16: 11}, 586: {16: 11}, 589: {21: 11},
    595: {16: 6}, 598: {6: 8, 16: 6}, 599: {6: 10, 11: 8},
    600: {11: 10}, 602: {11: 25}, 604: {21: 25},
    605: {16: 2}, 606: {16: 2, 21: 2}, 607: {16: 8},
    608: {16: 8, 21: 8}, 609: {21: 2}, 610: {11: 3},
    615: {16: 13, 21: 8}, 616: {21: 13}, 617: {16: 3, 21: 3},
    618: {21: 3}, 619: {16: 11}, 620: {16: 3},
    622: {11: 25, 21: 11}, 623: {16: 13, 21: 25}, 624: {16: 14},
    628: {11: 12}, 629: {16: 12, 21: 14}, 631: {21: 13},
    632: {16: 10}, 633: {6: 6}, 634: {11: 14},
    635: {16: 14}, 636: {11: 10}, 637: {16: 8},
    638: {16: 3}, 639: {6: 8, 11: 6}, 643: {11: 8},
    651: {21: 13}, 656: {16: 2}, 657: {16: 2, 21: 2},
    658: {16: 3}, 659: {16: 8}, 660: {16: 3, 21: 3},
    661: {16: 3, 21: 2}, 663: {16: 8, 21: 8},
}
# Entries move to the start of each rescheduled basic block.
BRANCH_TARGETS = {404: 393, 508: 525, 514: 525, 541: 551, 543: 551}


def fields(word):
    # Keep the established operand rules local, outside the executable research import chain.
    op, rs, fn = word >> 26, word >> 21 & 31, word & 63
    if op == 0:
        if fn in (0, 3):
            return (16, 11), ()
        if fn in (4, 33, 35, 36, 37, 42):
            return (21, 16, 11), ()
        if fn == 8:
            return (21,), ()
        if fn == 13:
            return (), ()
        if fn == 18:
            return (11,), ()
        if fn in (25, 26):
            return (21, 16), ()
    if op in (1, 6, 7):
        return (21,), ()
    if op in (4, 5, 9, 10, 12, 13, 20, 21, 32, 33, 35, 36, 37, 40, 41, 43):
        return (21, 16), ()
    if op == 15:
        return (16,), ()
    if op == 3:
        return (), ()
    if op in (49, 53, 57, 61):
        return (21,), (16,)
    if op == 17:
        if rs in (0, 4):
            return (16,), (11,)
        if rs == 8:
            return (), ()
        if rs == 16:
            if fn in (0, 1, 2):
                return (), (16, 11, 6)
            if fn == 13:
                return (), (11, 6)
            if fn == 60:
                return (), (16, 11)
        if rs == 20 and fn == 32:
            return (), (11, 6)
    raise ValueError('Unsupported actor-tick operand metadata: %08X' % word)


def relocate(raw, bindings, symbols):
    words = list(struct.unpack('>%dI' % (len(raw) // 4), raw))
    for at, entries in bindings.items():
        if len(entries) != 1:
            raise ValueError('Unknown actor-tick relocation group')
        kind, name = entries[0]
        value = symbols[name]
        if kind == 'R_MIPS_HI16':
            words[at // 4] = words[at // 4] & 0xFFFF0000 | ((value + 0x8000) >> 16) & 65535
        elif kind == 'R_MIPS_LO16':
            words[at // 4] = words[at // 4] & 0xFFFF0000 | value & 65535
        elif kind == 'R_MIPS_26':
            if value & 3 or value >> 28 != source.prior.prior.prior.ENTRY >> 28:
                raise ValueError('Invalid actor-tick call rebase')
            words[at // 4] = words[at // 4] & 0xFC000000 | (value >> 2) & 0x3FFFFFF
        else:
            raise ValueError('Unknown actor-tick relocation kind')
    return words


def origins():
    order = [i for i in range(678) if i not in REMOVED]
    order[50:54] = [53, 50, 51, 52]
    order.remove(288)
    order.insert(order.index(289), ('action-delay', 292))
    order.insert(order.index(362), ('actor-bias', 361))
    order.insert(order.index(389), 288)
    order.remove(393)
    order.insert(order.index(394), ('timer-delay', 292))
    order.insert(order.index(408), 393)
    for start, items in SCHEDULE.items():
        order[start:start + len(items)] = items
    kept = [item for item in order if isinstance(item, int)]
    if len(order) != 678 or len(kept) != 675 or set(kept) != set(range(678)) - REMOVED:
        raise ValueError('Actor-tick source origins are not closed')
    return order


def form(words, item):
    old = item[1] if isinstance(item, tuple) else item
    word = words[old]
    if isinstance(item, tuple):
        if item[0] == 'actor-bias':
            register = word >> 11 & 31
            bias = signed16(words[363] & 65535) - 0x14
            word = 9 << 26 | register << 21 | register << 16 | (bias & 65535)
        elif item[0] in ('action-delay', 'timer-delay'):
            if word != 0:
                raise ValueError('Actor-tick delay origin is not a no-op')
        else:
            raise ValueError('Unknown derived actor-tick instruction')
    else:
        if word >> 26 in MEMORY and word >> 21 & 31 == 29 and word & 65535 in SLOTS:
            word = word & 0xFFFF0000 | SLOTS[word & 65535]
        if old == 395:
            word = word & 0xFFFF0000 | 0x7C
        if old in (363, 373):
            word = word & 0xFFFF0000 | (0x14 if old == 363 else 0x1C)
        if old == 485:
            word = word & 0xFFFF0000 | 0xFFCE
    key = item[0] if isinstance(item, tuple) else item
    for shift, value in REGISTERS.get(key, {}).items():
        if shift not in fields(word)[0] + fields(word)[1]:
            raise ValueError('Not an actor-tick operand field')
        word = word & ~(31 << shift) | value << shift
    return word


def recipe(raw, bindings):
    encoded = json.dumps(sorted(bindings.items()), separators=(',', ':')).encode()
    if len(raw) != 2712 or hashlib.sha256(raw).hexdigest() != RAW_SHA or (
            hashlib.sha256(encoded).hexdigest() != BINDING_SHA):
        raise ValueError('Unknown actor-tick source words/bindings')
    words, order = struct.unpack('>678I', raw), origins()
    if {i: words[i] for i in REMOVED} != {390: 0x0012C880, 398: 0x01795021, 422: 0x02A03025}:
        raise ValueError('Unknown actor-tick scaled index/address/result copy')
    if words[395] != 0x8FAB00C4 or words[362] != 0x014C2021:
        raise ValueError('Unknown actor-tick cached/folded address')
    destination = {item: i for i, item in enumerate(order)}
    destination[678] = 678
    result, moved = [], {}
    for i, item in enumerate(order):
        word = form(words, item)
        if isinstance(item, int):
            if is_branch(words[item]):
                target = BRANCH_TARGETS.get(item, item + 1 + signed16(words[item] & 65535))
                if target not in destination:
                    raise ValueError('Actor-tick branch targets an omitted origin')
                word = word & 0xFFFF0000 | ((destination[target] - i - 1) & 65535)
            if item * 4 in bindings:
                moved[i * 4] = bindings[item * 4]
        result.append(word)
    return struct.pack('>678I', *result), moved


def normalize(raw, bindings):
    result, moved = recipe(raw, bindings)
    if hashlib.sha256(result).hexdigest() != NORMALIZED_SHA or sum(map(len, moved.values())) != 62:
        raise ValueError('Actor-tick instruction-origin recipe changed')
    return result, moved


def private_guards(before, raw, bindings):
    normalized, moved = normalize(raw, bindings)
    old, new = struct.unpack('>678I', raw), struct.unpack('>678I', normalized)
    reader = csv.DictReader(io.StringIO(before.decode()))
    if not before.endswith(b'\n') or any(row['filename'] == 'generated_B3020' and
            row['function'] == 'func_1508A6FC' for row in reader):
        raise ValueError('Unknown actor-tick guard predecessor')
    spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
    rows = []
    for i, (a, b) in enumerate(zip(old, new)):
        at = i * 4
        if a == b and bindings.get(at) == moved.get(at):
            continue
        rows.append(dict(filename='generated_B3020', function='func_1508A6FC', offset='0x%X' % at,
            expected='0x%08X' % a, replacement='0x%08X' % b,
            expected_relocations=spec(bindings.get(at, [])), replacement_relocations=spec(moved.get(at, [])),
            note='Normalize checked actor-tick source origins, frame roles and scheduling',
            insert_after='', insert_after_relocations='', omit='false'))
    stream = io.StringIO(newline='')
    csv.DictWriter(stream, fieldnames=reader.fieldnames,
                   lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before + stream.getvalue().encode()


def anchors(bindings):
    return {name: int(name.rsplit('_', 1)[1], 16)
            for entries in bindings.values() for _, name in entries}


def qualify(root, output):
    source.prior.prior.prior.freeze(root, output)
    row, linked = source.compile_candidate(root, output, 'selected', source.SELECTED)
    raw, bindings = source.prior.prior.prior.payload(output / 'selected.o')
    normalized, moved = normalize(raw, bindings)
    symbols = anchors(bindings)
    if relocate(raw, bindings, symbols) != list(linked):
        raise ValueError('Actor-tick independent source relocation differs')
    words = relocate(normalized, moved, symbols)
    truth = struct.unpack_from('>678I', (root / 'conker/conker.us.bin').read_bytes(),
                               source.prior.prior.prior.ROM)
    if words != list(truth):
        raise ValueError('Actor-tick origin recipe does not match retail')
    original = struct.unpack('>678I', raw)
    memory_origins = [i for i, w in enumerate(original) if w >> 26 in MEMORY]
    if any(origins().count(i) != 1 for i in memory_origins):
        raise ValueError('Actor-tick memory origin lost or duplicated')
    report = dict(raw_words=678, words=678, frame=288, raw_differences=row['aligned_differences'],
        differences=0, retained_origins=675, derived_forms=3, omitted_pure_instructions=3,
        retained_memory_instructions=len(memory_origins), output_bindings=sum(map(len, moved.values())),
        raw_sha256=RAW_SHA, normalized_sha256=NORMALIZED_SHA, installed=False, matching_credit=0)
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'normalized.bin').write_bytes(normalized)
    (output / 'normalized-bindings.json').write_text(json.dumps(moved, indent=2) + '\n')
    return report, list(linked), words


def shape(word):
    gp, fp = fields(word)
    masked = word
    for shift in gp + fp:
        masked &= ~(31 << shift)
    if is_branch(word):
        masked &= 0xFFFF0000
    return masked, tuple((word >> shift & 31) == 0 for shift in gp), word >> 21 & 31 == 29


def propose(root, output):
    source.prior.prior.prior.freeze(root, output)
    row, linked = source.compile_candidate(root, output, 'selected', source.SELECTED)
    truth = struct.unpack_from('>678I', (root / 'conker/conker.us.bin').read_bytes(),
                               source.prior.prior.prior.ROM)
    order = origins()
    formed = [form(linked, item) for item in order]
    available = collections.defaultdict(collections.deque)
    for item, word in zip(order, formed):
        available[shape(word)].append(item)
    proposal, missing = [], []
    for i, word in enumerate(truth):
        key = shape(word)
        if not available[key]:
            missing.append((i, '%08X' % word, key))
            proposal.append(None)
        else:
            proposal.append(available[key].popleft())
    unused = [item for queue in available.values() for item in queue]
    report = dict(source=row['raw_sha256'], missing=missing, unused=unused, origins=proposal)
    (output / 'origin-proposal.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--propose', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.propose:
        report = propose(root, root / BUILD)
        print(json.dumps({k: v for k, v in report.items() if k != 'origins'}, indent=2))
    else:
        print(json.dumps(qualify(root, root / BUILD)[0], indent=2))


if __name__ == '__main__':
    main()
