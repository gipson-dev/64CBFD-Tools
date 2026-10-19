"""Closed route-update core through finalizer; ranking/return are not emitted."""
import hashlib
import struct

from tools.experiments import game_route_actor_update_prefix_layout as prefix

source = prefix.source
BUILD = 'conker/build/game-route-actor-update-core-layout'
WORDS = 490
EXITS = {481: 490, 482: 491, 583: 593}
GP = {
    259: {16: 18}, 260: {16: 18}, 261: {16: 18}, 273: {18: 16}, 274: {18: 16},
    275: {18: 16, 24: 15}, 276: {15: 24}, 279: {15: 24, 24: 15}, 285: {16: 18},
    296: {13: 14}, 297: {14: 24}, 299: {13: 14}, 302: {16: 18}, 303: {14: 24},
    311: {16: 18}, 312: {14: 15}, 315: {14: 15, 15: 25}, 317: {13: 24}, 318: {25: 14},
    321: {25: 14}, 322: {15: 25, 24: 14}, 323: {13: 24, 24: 14, 15: 14},
    324: {15: 14, 13: 24}, 326: {13: 24}, 328: {14: 15, 13: 14}, 329: {25: 24},
    331: {15: 25}, 333: {15: 25}, 334: {13: 14, 24: 25}, 335: {25: 24, 24: 25, 13: 25},
    336: {13: 25, 25: 24}, 337: {15: 14}, 338: {25: 24, 15: 14}, 340: {14: 15},
    341: {15: 24}, 343: {13: 14}, 345: {13: 14}, 346: {24: 14},
    347: {15: 24, 24: 14, 25: 14}, 348: {25: 14, 15: 24}, 349: {13: 25},
    350: {15: 24, 13: 25}, 351: {24: 14}, 352: {24: 14}, 355: {14: 15},
    361: {14: 15}, 371: {13: 24}, 375: {13: 24}, 376: {15: 14}, 377: {15: 14},
    379: {24: 15}, 430: {18: 16}, 431: {18: 16}, 451: {18: 16}, 452: {18: 16},
    454: {24: 15}, 455: {14: 25}, 457: {24: 15}, 458: {14: 25}, 462: {25: 24},
    463: {25: 14}, 464: {25: 24}, 466: {13: 15}, 467: {25: 14}, 468: {24: 25},
    469: {13: 15, 24: 25, 14: 24}, 470: {25: 14, 14: 24, 13: 25}, 471: {13: 25},
    472: {15: 14}, 473: {24: 15}, 474: {15: 14}, 476: {24: 15, 15: 14, 14: 24},
    477: {14: 24}, 480: {15: 24}, 483: {13: 15}, 485: {13: 15, 24: 14},
    486: {24: 14}, 487: {15: 24},
}
FP = {
    244: {4: 6}, 246: {4: 6}, 286: {6: 4}, 288: {16: 6}, 289: {6: 4},
    290: {16: 6, 18: 8}, 291: {18: 8}, 298: {8: 4}, 299: {4: 10}, 301: {4: 10, 8: 4},
    303: {10: 8}, 305: {10: 8}, 306: {18: 4}, 308: {16: 10},
    309: {16: 10, 18: 4, 4: 6}, 310: {4: 6}, 314: {6: 4}, 318: {6: 4},
    330: {16: 6}, 331: {16: 6}, 339: {18: 8}, 342: {18: 8}, 352: {8: 10},
    354: {8: 10}, 359: {10: 8}, 361: {10: 8}, 366: {16: 4}, 368: {16: 4},
    373: {18: 10}, 375: {18: 10}, 380: {4: 6}, 386: {4: 6}, 397: {24: 22},
    400: {24: 22}, 415: {22: 16}, 416: {6: 4}, 417: {22: 16}, 418: {6: 4},
    420: {16: 6}, 422: {16: 6}, 424: {24: 22}, 428: {24: 22, 2: 18}, 429: {4: 10},
    432: {2: 18, 6: 4, 18: 8}, 433: {10: 4}, 434: {2: 18, 4: 10, 8: 6},
    436: {10: 4, 18: 8, 16: 10}, 437: {6: 4}, 438: {18: 8}, 439: {8: 6},
    440: {6: 4, 8: 6}, 441: {16: 10}, 442: {18: 8, 6: 4},
    444: {22: 16, 8: 6, 16: 8}, 445: {16: 8, 6: 4, 4: 6}, 446: {4: 6, 18: 4},
    447: {2: 18, 18: 4}, 450: {6: 10}, 453: {6: 10},
}
NORMALIZED_SHA = '7de4ac5fc8a5304db19e9e7d8ed3a730ecd51ebbd8be08f40596df48417cbb12'


def origins():
    # Common cast entry now owns the actor load. The Y read instead occupies
    # the active branch's delay slot or the mutually exclusive cosine path.
    order = list(range(244, 285)) + [312] + list(range(286, 311))
    order += [312, 311, 313, 316, 314, 315, 317, 322, 319, 323,
        ('cast-store', 322), 318, 320, 321, ('cast-load', 322), 324,
        325, 326, 327, 328, 332, 333, ('cast-store', 332), 329, 330, 331,
        ('cast-load', 332), 334, 335, 336, 337, 338, 342, 343,
        ('cast-store', 342), 339, 340, 341, ('cast-load', 342), 344]
    order += list(range(345, 370)) + [370, 372, 371, 444]
    order += list(range(373, 391))
    order += [392, 393, 397, ('start-z-save', 391), 394, 396, 395]
    order += list(range(398, 408))
    # Spill the existing start-Z carrier; replace the unreachable raw440
    # fallback with issue-spacing slots tied to actual source multiply pairs.
    order += [('start-z-load', 391), 408, 409, 410, ('hazard', 410, 412), 412, 411,
        413, 414, 415, 416, 417, 427, 419, 420, 422, 423, 424, 421, 426,
        ('hazard', 426, 428), 428, 425, 429, 431, 430, 433, 432,
        ('hazard', 432, 434), 434, 435, 436, 437, 438, 439, 418, 441, 442, 443]
    order += [444, 445, 446, 447, 448, 449, 450, 451, 452, 457, 454, 455,
        456, 458, 453, 460, 461] + list(range(462, 481))
    if len(order) != WORDS - prefix.WORDS:
        raise ValueError('Changed source-derived core extent')
    return order


def fields(word):
    op, fmt, fn = word >> 26, word >> 21 & 31, word & 63
    if op in (22, 23):
        return (21,), ()
    if op == 0 and fn in (4, 36):
        return (21, 16, 11), ()
    if op == 17 and (fmt == 16 and fn in (13, 33) or fmt == 17 and fn == 32):
        return (), (11, 6)
    if op == 17 and fmt == 17 and fn == 2:
        return (), (16, 11, 6)
    return prefix.fields(word)


def derived(words, origin):
    kind, old = origin[:2]
    word = words[old]
    if kind in ('cast-store', 'cast-load'):
        if word >> 26 != 17 or word >> 21 & 31 != 0:
            raise ValueError('Unknown converted-coordinate carrier')
        return (43 if kind == 'cast-store' else 35) << 26 | 29 << 21 | (word >> 16 & 31) << 16 | 0x48
    if kind in ('start-z-save', 'start-z-load'):
        if word >> 26 != 17 or word >> 21 & 31 != 16 or word & 63 != 6:
            raise ValueError('Unknown start-Z carrier')
        register = word >> (11 if kind == 'start-z-save' else 6) & 31
        return (57 if kind == 'start-z-save' else 49) << 26 | 29 << 21 | register << 16 | 0x1C0
    if kind == 'hazard':
        right = origin[2]
        # Each source pair already has one intervening issue slot; its old
        # store/add/NOP now has a different job in the closed retail schedule.
        if right != old + 2 or any(words[i] >> 26 != 17 or words[i] >> 21 & 31 != 16 or words[i] & 63 != 2
                for i in (old, right)):
            raise ValueError('Unknown multiply issue-spacing pair')
        return 0
    raise ValueError('Unknown core operation derivation')


def swap(word, left, right):
    return word & ~((31 << left) | (31 << right)) | (word >> left & 31) << right | (word >> right & 31) << left


def normalize(raw, bindings):
    first, moved = prefix.normalize(raw, bindings)
    words = list(struct.unpack('>594I', raw))
    order = origins()
    destination = {old: new for new, old in enumerate(order, prefix.WORDS) if isinstance(old, int)}
    destination.update(EXITS)
    result = list(struct.unpack('>244I', first))
    for new, origin in enumerate(order, prefix.WORDS):
        old = origin if isinstance(origin, int) else None
        word = words[old] if old is not None else derived(words, origin)
        op, rs = word >> 26, word >> 21 & 31
        if old is not None and (op in (4, 5, 6, 7, 20, 21, 22, 23) or op == 17 and rs == 8):
            target = old + 1 + (((word & 65535) ^ 32768) - 32768)
            if target not in destination:
                raise ValueError('Unknown core branch destination')
            entry = {371: 455, 284: 312, 417: 450}.get(old, destination[target])
            word = word & 0xFFFF0000 | (entry - new - 1) & 65535
        if old == 417:
            if op != 17 or rs != 8 or word >> 16 & 31 != 2:
                raise ValueError('Unknown projection branch-likely lowering')
            word &= ~(2 << 16)
        if old in (471, 478):
            if op != 35 or rs != 29 or word & 65535 != 0x54:
                raise ValueError('Unknown finalizer offset home')
            word = word & 0xFFFF0000 | 0x68
        if old == 460:
            mask = words[459]
            if mask >> 26 != 12 or mask & 65535 != 31 or word >> 21 & 31 != mask >> 16 & 31:
                raise ValueError('Unknown redundant variable-shift mask')
            word = word & ~(31 << 21) | (mask >> 21 & 31) << 21
        if new in (301, 309):
            if op != 17 or rs != 16 or word & 63 != 0:
                raise ValueError('Unknown commutative coordinate sum')
            word = swap(word, 16, 11)
        if new == 470:
            if op or word & 63 != 36:
                raise ValueError('Unknown commutative active-mask test')
            word = swap(word, 21, 16)
        for shifts, rename in zip(fields(word), (GP.get(new, {}), FP.get(new, {}))):
            original = word
            if not set(rename) <= {word >> shift & 31 for shift in shifts} or any(not 0 <= value < 32 for value in rename.values()):
                raise ValueError('Unknown core register recipe')
            for shift in shifts:
                reg = original >> shift & 31
                word = word & ~(31 << shift) | rename.get(reg, reg) << shift
        result.append(word)
    for at, entries in bindings.items():
        if prefix.WORDS <= at // 4 < 481:
            if at // 4 not in destination:
                raise ValueError('Removed core symbol binding')
            moved[destination[at // 4] * 4] = entries
    normalized = struct.pack('>%dI' % WORDS, *result)
    if hashlib.sha256(normalized).hexdigest() != NORMALIZED_SHA:
        raise ValueError('Changed source-derived core layout')
    return normalized, moved


def relocate(raw, bindings, anchors):
    return prefix.relocate(raw, bindings, anchors)
