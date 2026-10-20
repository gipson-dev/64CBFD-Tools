"""Checked semantic C origins for the complete pickup-update instruction layout."""

import hashlib
import json
from pathlib import Path
import struct
from functools import lru_cache

import rabbitizer

from tools.experiments import game_pickup_state_update_lifetimes as prior


core, SELECTED = prior.core, prior.SELECTED
FUNCTION, ENTRY, ROM = core.FUNCTION, core.ENTRY, core.ROM
BUILD = prior.BUILD + '/layout'
RAW_SHA = 'aa2d148b4b51b725d32722cd832571aad2822a9bc68f16a97116b93a3a411f82'
BINDING_SHA = '69b8067c4b8d498971e8f9aaef8d3522e8bb230c5b88fc14698b9c56af09b978'
NORMALIZED_SHA = '5e52891e4fa104702217ed8bad51fe03490d6e4e9a3e36733887e6fdc9d1e6c2'
OUTPUT_BINDING_SHA = '56b606886944ff98d418f3fbe06c0c8b45a37623301296b76232b63fa5efda60'
RECIPE_SHA = 'b0d2527c2fe5bf8a2d80673dc0199495a2e2129173c1929cba85a2f5826ab0fc'
OMITTED = {269, 306, 308, 311, 331, 363, 394, 397, 529, 534, 616, 635, 642}
BRANCH_EXCEPTIONS = {306: 339, 310: 337, 330: 337, 361: 378, 413: 418, 416: 659}
REGISTERS = {
    46: {16: 30}, 47: {16: 23}, 48: {16: 4, 21: 2}, 49: {16: 20}, 51: {21: 4}, 52: {16: 20}, 54: {16: 3},
    56: {16: 5}, 58: {16: 3, 21: 3}, 59: {16: 5}, 61: {11: 20}, 62: {21: 5}, 63: {16: 3, 21: 5}, 66: {21: 3},
    72: {21: 3}, 80: {16: 20}, 88: {21: 2}, 93: {21: 4}, 95: {21: 5}, 128: {16: 10}, 129: {16: 10, 21: 10},
    132: {16: 11, 21: 10}, 135: {21: 11}, 138: {16: 12}, 142: {16: 12}, 145: {21: 12}, 146: {16: 14},
    147: {16: 13}, 149: {16: 13, 21: 14}, 152: {16: 15}, 153: {16: 24}, 154: {16: 25}, 155: {16: 8},
    156: {16: 15, 21: 24}, 157: {16: 8}, 158: {16: 25}, 169: {16: 10}, 170: {16: 9}, 172: {16: 9, 21: 10},
    179: {16: 11}, 180: {21: 11}, 195: {16: 13}, 196: {16: 2}, 197: {16: 2, 21: 2}, 198: {16: 13, 21: 12},
    199: {16: 3}, 200: {16: 14, 21: 2}, 203: {21: 14}, 204: {16: 3}, 213: {16: 15}, 215: {16: 24, 21: 15},
    216: {21: 24}, 240: {11: 25}, 242: {21: 25}, 253: {21: 23}, 255: {21: 30}, 273: {16: 8}, 275: {21: 8},
    284: {16: 9}, 286: {16: 10, 21: 9}, 287: {21: 10}, 310: {21: 23}, 312: {21: 30}, 334: {16: 11},
    335: {21: 11}, 341: {16: 12}, 342: {16: 12, 21: 12}, 343: {16: 14}, 344: {16: 14, 21: 14}, 345: {21: 12},
    348: {11: 13}, 349: {11: 13, 21: 13}, 350: {11: 13, 16: 13}, 351: {11: 13, 21: 13},
    352: {11: 13, 16: 13}, 353: {11: 13, 21: 13}, 354: {11: 13, 16: 13}, 355: {11: 13, 21: 13},
    356: {11: 13, 16: 13}, 357: {16: 14, 21: 13}, 358: {16: 15}, 359: {16: 10}, 360: {16: 24}, 361: {21: 15},
    362: {16: 10, 21: 10}, 363: {16: 8}, 364: {16: 25, 21: 24}, 365: {16: 8, 21: 25}, 367: {16: 9},
    369: {21: 9}, 379: {16: 10}, 381: {16: 15}, 382: {16: 2}, 383: {16: 2, 21: 2}, 384: {16: 3},
    385: {16: 5, 21: 2}, 386: {16: 3, 21: 3}, 387: {16: 5, 21: 3}, 390: {16: 3}, 392: {16: 11},
    393: {16: 11, 21: 11}, 394: {16: 1}, 396: {16: 12, 21: 11}, 397: {11: 13, 16: 12}, 398: {16: 12, 21: 1},
    399: {11: 14, 16: 13}, 400: {16: 5, 21: 14}, 402: {16: 30}, 403: {16: 1}, 404: {21: 1},
    405: {16: 15, 21: 2}, 408: {21: 15}, 409: {16: 30, 21: 30}, 415: {16: 2}, 417: {16: 2, 21: 2},
    418: {16: 24}, 419: {16: 25}, 420: {16: 8}, 421: {21: 24}, 423: {16: 12}, 424: {21: 25},
    427: {16: 8, 21: 8}, 428: {16: 11}, 429: {11: 9, 16: 8}, 430: {21: 9}, 431: {16: 9}, 432: {16: 11},
    437: {16: 12, 21: 12}, 438: {11: 13, 16: 12}, 439: {21: 13}, 440: {16: 13}, 443: {16: 15}, 444: {16: 24},
    445: {21: 15}, 446: {11: 25, 21: 24}, 447: {16: 8, 21: 25}, 448: {16: 8}, 449: {16: 9},
    450: {11: 10, 21: 9}, 451: {16: 11, 21: 10}, 452: {16: 11}, 453: {16: 12}, 454: {11: 13, 21: 12},
    455: {16: 14, 21: 13}, 457: {16: 14}, 458: {16: 15}, 459: {11: 24, 21: 15}, 460: {21: 24}, 461: {16: 25},
    462: {21: 25}, 463: {16: 8}, 464: {21: 8}, 466: {16: 9}, 467: {16: 9, 21: 9}, 468: {16: 10, 21: 9},
    469: {16: 10}, 477: {16: 12}, 478: {16: 12, 21: 12}, 479: {21: 12}, 484: {11: 13}, 485: {11: 14, 16: 13},
    486: {16: 15, 21: 14}, 487: {16: 15}, 494: {11: 13}, 500: {16: 24}, 501: {11: 25, 21: 24}, 502: {21: 25},
    504: {16: 8}, 505: {16: 8, 21: 8}, 506: {11: 9}, 507: {11: 10, 16: 9, 21: 8}, 509: {21: 10},
    519: {16: 12}, 521: {16: 12}, 524: {16: 24}, 526: {16: 25, 21: 24}, 527: {16: 25}, 530: {16: 9},
    532: {16: 9}, 541: {16: 10}, 542: {16: 9}, 544: {21: 10}, 545: {16: 11}, 546: {11: 12}, 548: {21: 11},
    549: {21: 9}, 550: {11: 12, 21: 12}, 551: {11: 12, 16: 12}, 552: {11: 12, 21: 12}, 553: {11: 12, 16: 12},
    554: {11: 12, 21: 12}, 555: {11: 12, 16: 12}, 556: {11: 12, 21: 12}, 557: {11: 12, 16: 12},
    558: {11: 3, 16: 12, 21: 30}, 559: {16: 2, 21: 3}, 560: {16: 24}, 561: {16: 25}, 562: {16: 13, 21: 2},
    563: {16: 14, 21: 13}, 564: {16: 14, 21: 2}, 565: {16: 2, 21: 3}, 566: {16: 15, 21: 2}, 567: {21: 15},
    570: {16: 24, 21: 2}, 571: {16: 25, 21: 25}, 572: {16: 8, 21: 25}, 574: {16: 8}, 577: {16: 10},
    578: {16: 14}, 579: {16: 15}, 580: {16: 11, 21: 10}, 581: {21: 11}, 583: {16: 12}, 584: {16: 12, 21: 12},
    585: {16: 13, 21: 12}, 587: {16: 13}, 588: {16: 14}, 589: {16: 24}, 590: {16: 8}, 591: {11: 9},
    592: {11: 25, 21: 24}, 593: {16: 15, 21: 25}, 594: {16: 8, 21: 9}, 596: {16: 11}, 597: {16: 10},
    598: {16: 14}, 599: {11: 12, 21: 11}, 600: {16: 10, 21: 12}, 601: {16: 14, 21: 14}, 602: {16: 13},
    603: {11: 24, 21: 14}, 604: {16: 13, 21: 24}, 605: {16: 15}, 606: {16: 15, 21: 15}, 607: {11: 8},
    608: {11: 8, 21: 8}, 609: {16: 4, 21: 15}, 611: {11: 8, 16: 8}, 612: {21: 4}, 613: {11: 8, 21: 8},
    614: {11: 8, 16: 8}, 615: {11: 8, 21: 8}, 616: {11: 8, 16: 8}, 617: {11: 8, 21: 8}, 618: {11: 8, 16: 8},
    619: {11: 9, 16: 8, 21: 30}, 620: {16: 11, 21: 9}, 621: {16: 25}, 622: {16: 10}, 623: {16: 25, 21: 11},
    624: {16: 10, 21: 10}, 625: {16: 4, 21: 10}, 627: {21: 4}, 628: {11: 12}, 629: {11: 12, 21: 12},
    630: {11: 12, 16: 12}, 631: {11: 12, 21: 12}, 632: {11: 12, 16: 12}, 633: {11: 12, 21: 12},
    634: {11: 12, 16: 12}, 635: {11: 12, 21: 12}, 636: {11: 12, 16: 12}, 637: {11: 14, 16: 12, 21: 30},
    638: {16: 2, 21: 14}, 641: {16: 4, 21: 2}, 642: {16: 4}, 645: {16: 13}, 647: {16: 13, 21: 2},
    650: {16: 24}, 652: {16: 24, 21: 2}, 655: {16: 15}, 656: {16: 15, 21: 2}, 657: {16: 2},
    658: {16: 2, 21: 2}, 659: {16: 3}, 662: {16: 3, 21: 3}, 663: {16: 3}, 664: {16: 8, 21: 2},
    665: {16: 8, 21: 3},
}


def payload(obj):
    text, functions, relocations = prior.parse_object(obj)
    item = functions[FUNCTION]
    raw = text[item['value']:item['value'] + item['size']]
    return raw, {at - item['value']: rows for at, rows in relocations.items()
        if item['value'] <= at < item['value'] + item['size']}


def normalize(raw, bindings):
    words = checked(raw, bindings)
    if recipe_signature() != RECIPE_SHA:
        raise ValueError('Pickup origin/operand recipe changed')
    order = origins()
    used = {v if isinstance(v, int) else v[1] for v in order}
    if len(order) != 681 or used != set(range(680)) - OMITTED:
        raise ValueError('Pickup instruction origins are not closed')
    positions = {v: i for i, v in enumerate(order) if isinstance(v, int)}
    for pos, item in enumerate(order):
        if not isinstance(item, int):
            positions.setdefault(item[1], pos)
    result, moved = [], {}
    for pos, item in enumerate(order):
        origin = item if isinstance(item, int) else item[1]
        word, rows, _ = form(words, bindings, item)
        gp, fp = fields(word)
        before = word
        for shift in gp:
            register = before >> shift & 31
            word = word & ~(31 << shift) | roles(origin).get(register, register) << shift
        for shift, register in REGISTERS.get(pos, {}).items():
            if shift not in (*gp, *fp) or not 0 <= register < 32:
                raise ValueError('Pickup override is not an actual typed operand')
            word = word & ~(31 << shift) | register << shift
        if branch(word):
            target = origin + 1 + ((words[origin] & 65535) - (65536 if words[origin] & 32768 else 0))
            target = BRANCH_EXCEPTIONS.get(pos, 657 if target == 656 else positions.get(target))
            if target is None or not 0 <= target < 681:
                raise ValueError('Pickup branch target has no checked origin')
            word = word & 0xFFFF0000 | ((target - pos - 1) & 65535)
        if not isinstance(item, int) and item[0] == 'delay' and (not result or not branch(result[-1])):
            raise ValueError('Pickup delay copy is not an executable branch slot')
        result.append(word)
        if rows:
            moved[pos * 4] = list(rows)
    output = struct.pack('>681I', *result)
    if hashlib.sha256(output).hexdigest() != NORMALIZED_SHA or binding_digest(moved) != OUTPUT_BINDING_SHA:
        raise ValueError('Pickup origin recipe or output bindings changed')
    return output, moved


def origins():
    return [
        *range(0, 46), 253, 251, *range(47, 235), *range(236, 243), 235,
        *range(243, 251), 46, ('swap', 252), ('delay', 46), ('swap', 254),
        *range(255, 269), ('delay', 46), *range(270, 305),
        ('ordinary', 305), ('cursor', 235), 307, 309, ('likely-swap', 310),
        ('increment', 336), ('swap', 312), *range(313, 330),
        ('likely', 330), ('increment', 336), *range(332, 346),
        *range(347, 361), 346, ('ordinary', 362), 361, *range(364, 394),
        ('selector-load', 395), ('selector-hi', 393), 406,
        *range(398, 400), ('selector-store', 403), *range(400, 403),
        552, ('selector-hi', 393), ('selector-reset', 404), 405, 409,
        *range(407, 409), 553, *range(410, 413), ('nonnull', 413), 414,
        ('null-hi', 657), ('null-jump', 413), ('null-load', 658),
        *range(415, 417), 396, *range(417, 419), ('tick-hi', 396),
        *range(419, 422), ('tick-load', 422), *range(423, 432),
        ('tick-load', 432), *range(433, 528), ('ordinary', 528), ('delay', 46),
        *range(530, 533), ('ordinary', 533), ('delay', 46), *range(535, 537),
        541, 537, *range(539, 541), 538, *range(542, 552), *range(554, 616),
        617, ('actor-load', 618), *range(619, 635), 636, ('actor-load', 637),
        *range(638, 641), ('ordinary', 641), ('delay', 46), *range(643, 656),
        *range(657, 659), 656, *range(662, 664), *range(659, 662),
        *range(664, 680),
    ]


def roles(origin):
    if 12 <= origin <= 45:
        return {5: 2, 4: 5, 23: 22, 21: 19}
    if 47 <= origin < 235:
        return {23: 22, 21: 19, 18: 17, 17: 3, 20: 18, 22: 20, 30: 21}
    if 235 <= origin < 339:
        return {23: 22, 21: 19, 20: 18, 22: 20, 30: 21, 16: 17, 18: 16, 17: 2, 19: 4}
    if 339 <= origin < 393:
        return {23: 22, 21: 19, 20: 18, 18: 16, 17: 2}
    if 393 <= origin < 667:
        return {17: 20, 18: 23, 19: 17, 20: 18, 21: 19, 22: 21, 23: 22}
    return {}


@lru_cache(maxsize=4096)
def fields(word):
    instruction = rabbitizer.Instruction(word)
    types = rabbitizer.OperandType
    gp = tuple(s for n, s in (('cpu_rs', 21), ('cpu_rt', 16), ('cpu_rd', 11))
        if instruction.hasOperandAlias(getattr(types, n)))
    fp = tuple(s for n, s in (('cpu_fs', 11), ('cpu_ft', 16), ('cpu_fd', 6))
        if instruction.hasOperandAlias(getattr(types, n)))
    return gp, fp


def branch(word):
    return word >> 26 in (1, 4, 5, 6, 7, 20, 21, 22, 23) or word >> 26 == 17 and word >> 21 & 31 == 8


def binding_digest(bindings):
    return hashlib.sha256(json.dumps(bindings, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def recipe_signature():
    return binding_digest(dict(order=origins(), roles={i: roles(i) for i in range(680)},
        registers=REGISTERS, branches=BRANCH_EXCEPTIONS, omitted=sorted(OMITTED)))


def checked(raw, bindings):
    if len(raw) != 2720 or hashlib.sha256(raw).hexdigest() != RAW_SHA:
        raise ValueError('Pickup layout raw C input changed')
    if binding_digest(bindings) != BINDING_SHA:
        raise ValueError('Pickup layout raw C bindings changed')
    return struct.unpack('>680I', raw)


def form(words, bindings, item):
    if isinstance(item, int):
        return words[item], bindings.get(item * 4, []), item
    kind, origin = item
    if kind not in ('ordinary', 'likely', 'likely-swap', 'swap', 'nonnull', 'null-jump',
            'selector-load', 'selector-store', 'selector-reset', 'tick-load', 'actor-load',
            'delay', 'cursor', 'increment', 'selector-hi', 'null-hi', 'null-load', 'tick-hi'):
        raise ValueError('Unknown pickup derived origin')
    word, binding_origin = words[origin], origin
    if kind in ('ordinary', 'likely', 'likely-swap'):
        op = word >> 26
        if op not in ((20, 21, 22) if kind == 'ordinary' else (4,)):
            raise ValueError('Pickup branch-flavor origin changed')
        word = word & 0x3FFFFFF | ((op - 16 if kind == 'ordinary' else op + 16) << 26)
    if kind in ('swap', 'likely-swap'):
        if word >> 26 not in (4, 20):
            raise ValueError('Pickup equality origin changed')
        word = word & ~((31 << 21) | (31 << 16)) | (word >> 21 & 31) << 16 | (word >> 16 & 31) << 21
    if kind == 'nonnull':
        if word >> 26 != 4:
            raise ValueError('Pickup object branch origin changed')
        word = word & 0x3FFFFFF | 5 << 26
    if kind == 'null-jump':
        word = 0x10000000
    if kind in ('selector-load', 'selector-store', 'selector-reset'):
        binding_origin = 394
    if kind == 'tick-load':
        binding_origin = 397
    if kind == 'actor-load':
        return word, [], None
    if kind == 'delay' and word != 0:
        raise ValueError('Pickup executable delay is not the original C nop')
    return word, bindings.get(binding_origin * 4, []), binding_origin


def mask(rows):
    result = 0
    for kind, _ in rows:
        if kind in ('R_MIPS_HI16', 'R_MIPS_LO16'):
            result |= 65535
        elif kind == 'R_MIPS_26':
            result |= 0x3FFFFFF
        else:
            raise ValueError('Unsupported pickup relocation')
    return result


def apply_linked(linked, raw, bindings):
    words = checked(raw, bindings)
    if len(linked) != 680:
        raise ValueError('Pickup linked C extent changed')
    for i, (before, after) in enumerate(zip(words, linked)):
        if (before ^ after) & ~mask(bindings.get(i * 4, [])):
            raise ValueError('Pickup linked C non-relocation bits changed')
    output, _ = normalize(raw, bindings)
    result = list(struct.unpack('>681I', output))
    for pos, item in enumerate(origins()):
        _, rows, binding_origin = form(words, bindings, item)
        if rows:
            bits = mask(rows)
            result[pos] = result[pos] & ~bits | linked[binding_origin] & bits
    return result


def qualify(root, output):
    obj, words, raw_report = core.compile_candidate(root, output, 'selected', SELECTED)
    raw, bindings = payload(obj)
    normalized, moved = normalize(raw, bindings)
    result = apply_linked(words, raw, bindings)
    original = prior.original(root, output)
    if (normalized, moved) != payload(original):
        raise ValueError('Pickup layout differs from independently assembled original')
    used = {v if isinstance(v, int) else v[1] for v in origins()}
    report = dict(raw=raw_report, words=681, frame=280, differences=0,
        retained_unique_origins=len(used), coalesced_origins=13,
        duplicate_origin_uses=14, derived_positions=32, bindings=77,
        normal_SHA256=NORMALIZED_SHA, experimental_byte_exact=True,
        installed=False, matching_credit=0)
    (output / 'normalized.bin').write_bytes(normalized)
    (output / 'normalized-bindings.json').write_text(json.dumps(moved, indent=2) + '\n')
    (output / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return obj, words, result, report


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
