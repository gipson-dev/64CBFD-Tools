"""Source-derived correction-loop prefix only; no executable tail or installation."""
import hashlib
import struct

from tools.experiments import game_route_actor_update_storage as source
from tools.experiments import game_route_projection_layout_normalizer as projection

BUILD = 'conker/build/game-route-actor-update-prefix-layout'
WORDS = 244
EXITS = {244: 244, 373: 380, 583: 593}
GP = {
    15: {14: 24}, 18: {14: 24}, 19: {14: 24}, 23: {24: 25}, 24: {13: 24}, 25: {13: 24},
    26: {24: 25, 25: 14}, 27: {25: 14, 24: 25}, 28: {25: 14}, 29: {25: 14, 24: 25},
    30: {25: 14}, 31: {25: 14, 24: 25}, 32: {25: 14}, 33: {25: 14, 24: 25}, 34: {25: 14},
    35: {25: 14, 13: 24, 14: 15}, 36: {14: 15}, 37: {14: 15}, 39: {24: 14}, 41: {14: 15},
    45: {15: 25}, 48: {15: 25}, 81: {24: 14}, 83: {25: 24}, 86: {25: 24}, 201: {13: 15},
    202: {13: 15}, 208: {25: 24}, 212: {15: 14}, 215: {15: 14}, 217: {13: 25},
    220: {25: 15}, 223: {25: 15}, 227: {25: 15}, 235: {13: 25},
}
FP = {
    37: {4: 8}, 40: {4: 8}, 41: {6: 10}, 44: {6: 10}, 55: {8: 4}, 58: {8: 4, 10: 6},
    59: {16: 8}, 61: {16: 8, 10: 6}, 71: {18: 10}, 73: {18: 10}, 76: {18: 10},
    94: {16: 4}, 96: {16: 4}, 97: {18: 6}, 99: {4: 8}, 101: {4: 8, 18: 6},
    115: {6: 10}, 116: {10: 6}, 117: {14: 16}, 118: {6: 10, 8: 4}, 120: {10: 6, 16: 8},
    121: {16: 8, 8: 4}, 122: {18: 4}, 125: {18: 4}, 126: {6: 10, 4: 8}, 128: {10: 6, 8: 4},
    129: {4: 8}, 130: {8: 4}, 131: {4: 8}, 132: {16: 10}, 133: {16: 10}, 134: {18: 6},
    135: {10: 8}, 136: {18: 6, 6: 4}, 138: {10: 8, 14: 16, 8: 10}, 139: {8: 10, 6: 4},
    141: {18: 6, 16: 10}, 144: {10: 8, 8: 4}, 145: {4: 6}, 148: {8: 4, 16: 10, 18: 8},
    149: {18: 8}, 150: {16: 8}, 151: {4: 6}, 161: {6: 4}, 163: {6: 4}, 166: {16: 8},
    168: {16: 8}, 174: {8: 6}, 175: {18: 10}, 181: {18: 10, 8: 6, 0: 2}, 182: {0: 2},
    185: {0: 2}, 186: {0: 2}, 188: {0: 2}, 191: {0: 2, 10: 8}, 192: {0: 2},
    193: {0: 2, 10: 8}, 195: {10: 8}, 197: {14: 18}, 198: {14: 18}, 211: {14: 18},
    213: {14: 18}, 221: {16: 10}, 222: {4: 8}, 226: {16: 10, 8: 4}, 227: {18: 6},
    230: {4: 6, 18: 8}, 231: {16: 6}, 232: {8: 4, 6: 8}, 233: {8: 10},
    234: {16: 6, 6: 8, 18: 4}, 236: {14: 18, 18: 4, 4: 12}, 237: {16: 4},
    238: {8: 10, 4: 12, 10: 8}, 239: {16: 4, 10: 8, 18: 10}, 241: {18: 10},
}
NORMALIZED_SHA = '4ae1b781680bacb0f1c751c0dbf2028ae828e16e5344759945b12e9d8ca12c80'


def origins():
    order = list(range(WORDS))
    order[43:61] = [58, 44, 45, 46, 47, 48, 49, 43, 50, 51, 52, 53, 54, 59, 55, 57, 56, 60]
    order[120:124] = [121, 123, 120, 122]
    order[136:146] = [137, 138, 139, 140, 136, 141, 142, 144, 145, 143]
    order[149:151] = [150, 149]
    order[194], order[197] = 197, 194
    order[198], order[199] = 199, 198
    order[224:232] = [225, 228, 226, 224, 230, 231, 229, 227]
    if sorted(order) != list(range(WORDS)):
        raise ValueError('Changed correction-loop operation permutation')
    return order


def fields(word):
    op, fmt, fn = word >> 26, word >> 21 & 31, word & 63
    if op in (53, 61):
        return (21,), (16,)
    if op == 10:
        return (21, 16), ()
    if op == 0 and fn in (3,):
        return (16, 11), ()
    if op == 0 and fn in (35,):
        return (21, 16, 11), ()
    if op == 17 and fmt == 0:
        return (16,), (11,)
    if op == 17 and fmt == 16 and fn == 7:
        return (), (11, 6)
    return projection.fields(word)


def normalize(raw, bindings):
    source.check_payload(raw, bindings)
    words = list(struct.unpack('>594I', raw))
    order = origins()
    destination = {old: new for new, old in enumerate(order)}
    destination.update(EXITS)
    result = []
    for new, old in enumerate(order):
        word = words[old]
        if old == 152:
            # The C call-save already carries this error; preserve its earlier
            # value in F18 across both the advance and selection calls.
            saved = words[194]
            if word != 0 or saved >> 26 != 57 or saved >> 21 & 31 != 29 or saved & 65535 != 0x1A8:
                raise ValueError('Unknown signed-error snapshot')
            word = 17 << 26 | 16 << 21 | (saved >> 16 & 31) << 11 | 18 << 6 | 6
        op, rs = word >> 26, word >> 21 & 31
        if op in (4, 5, 6, 7, 20, 21) or op == 17 and rs == 8:
            target = old + 1 + (((word & 65535) ^ 32768) - 32768)
            if target not in destination:
                raise ValueError('Unknown correction-loop branch destination')
            # The step-clamp join labels the block, not its moved call-save.
            entry = 194 if target == 194 else destination[target]
            word = word & 0xFFFF0000 | (entry - new - 1) & 65535
        if old in (21, 211, 213):
            expected, recovered = (0x54, 0x68) if old == 21 else (0x160, 0x1A8)
            if rs != 29 or word & 65535 != expected:
                raise ValueError('Unknown correction-loop scalar home')
            word = word & 0xFFFF0000 | recovered
        if old == 22:
            if op or word & 63 != 33:
                raise ValueError('Unknown commutative record-address sum')
            word = word & ~((31 << 21) | (31 << 16)) | (word >> 21 & 31) << 16 | (word >> 16 & 31) << 21
        for shifts, rename in zip(fields(word), (GP.get(new, {}), FP.get(new, {}))):
            original = word
            if not set(rename) <= {word >> shift & 31 for shift in shifts} or any(not 0 <= v < 32 for v in rename.values()):
                raise ValueError('Unknown correction-loop register recipe')
            for shift in shifts:
                reg = original >> shift & 31
                word = word & ~(31 << shift) | rename.get(reg, reg) << shift
        result.append(word)
    moved = {destination[at // 4] * 4: entries for at, entries in bindings.items() if at // 4 < WORDS}
    normalized = struct.pack('>%dI' % WORDS, *result)
    if hashlib.sha256(normalized).hexdigest() != NORMALIZED_SHA:
        raise ValueError('Changed correction-loop layout recipe')
    return normalized, moved


def relocate(raw, bindings, anchors):
    return projection.relocate(raw, bindings, anchors)
