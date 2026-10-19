"""Complete source-derived route-update layout; never installs or reads retail."""
import hashlib
import csv
import io
import struct

from tools.experiments import game_route_actor_update_core_layout as core

source = core.source
BUILD = 'conker/build/game-route-actor-update-layout'
WORDS = 604
CURRENT, NEXT = 8, 5
GP = {
    490:{15:24},491:{15:24},493:{18:16,11:13},494:{6:8},495:{7:12},496:{11:13},
    497:{11:13,9:11},500:{8:1},501:{12:9},502:{4:2},503:{4:2},504:{12:9},505:{8:1},
    506:{3:7},507:{5:6},509:{7:4},510:{3:7,6:8},511:{4:2,14:15},512:{4:2},
    514:{14:15},515:{6:5},516:{3:7},518:{10:1},520:{5:6},521:{4:2,2:3},
    522:{7:4,2:3},523:{4:2,13:3},524:{2:3},525:{5:6},530:{5:6},531:{4:2,13:3},
    532:{25:14},533:{4:2},534:{13:3,25:14,15:25},535:{12:9,15:25,14:24},
    536:{14:24},537:{6:8,11:13},538:{5:6},539:{10:1},541:{5:6},542:{6:8,11:13},
    544:{5:6},545:{6:8},546:{8:9},547:{9:11},548:{16:10},549:{7:6},551:{4:6},
    552:{4:6},553:{6:5,25:14},554:{8:9,6:8,3:7},556:{7:12,25:14,5:3},557:{8:9,3:2},
    560:{3:2,2:15},561:{5:3},562:{3:7,13:4},563:{3:7,2:15},564:{4:6},565:{16:10},
    566:{5:3},567:{3:2,13:4},569:{9:11},572:{4:6},573:{6:8},574:{16:10},576:{11:13},
    577:{3:7},579:{3:7,14:24},580:{15:25},581:{15:25},582:{14:24,13:15},
    583:{13:15,14:24},584:{13:15},585:{15:25,13:15,25:14},586:{25:14,2:5},
    587:{18:16},588:{2:5,6:8},590:{2:8},592:{3:7},
}
FP = {
    499:{0:2},505:{8:0},512:{4:6},514:{16:4},517:{16:4,10:8},
    519:{10:8,4:6,18:10},520:{18:10},525:{18:4},526:{16:8},527:{0:2,16:8},
    528:{8:0,4:6},529:{4:6,18:4,6:8},530:{6:8},538:{16:10},539:{8:4},
    540:{8:4,16:10,10:6},541:{10:6},551:{0:2},552:{18:8},555:{18:8,0:2},
    561:{4:10},564:{4:10},566:{0:2},
}
NORMALIZED_SHA = 'c7b3b9a07d1f1b8b68009e746f053f981a367e86e36234d0e5a2559db55a291c'


def origins():
    return [481,482,483,484,487,538,488,489,490,494,493,491,485,486,497,
        ('constant',515,493,495),498,499,('next-init',504),500,501,502,503,
        ('next-copy',504),505,504,507,508,492,509,510,511,512,513,514,516,517,
        518,519,520,521,522,523,524,526,527,528,506,530,
        ('constant',531,492,496),532,533,506,534,535,
        536,537,540,539,538,('next-init',558),542,543,544,545,546,547,
        ('next-id-pointer',545),548,('next-copy',549),550,552,551,553,555,557,
        556,554,('next-copy',558),('sort-less',559),('next-increment',558),
        ('sort-test',559),560,561,562,529,566,565,('next-init',574),
        568,569,570,571,572,573,575,576,577,578,('next-increment',574),580,581,579,
        *range(583,594)]


def derived(words, origin):
    kind, old = origin[:2]
    word = words[old]
    if kind == 'constant':
        hi, lo = words[origin[2]], words[origin[3]]
        base = word >> 21 & 31
        if word >> 26 != 49 or word & 65535 or hi >> 26 != 15 or hi >> 16 & 31 != base or (
                lo >> 26 != 9 or lo >> 21 & 31 != base or lo >> 16 & 31 != base):
            raise ValueError('Unknown folded score-constant address')
        return word & 0xFFFF0000 | lo & 65535
    if kind in ('next-init','next-copy','next-increment'):
        if word >> 26 != 9 or word & 65535 != 1:
            raise ValueError('Unknown bounded current/next induction')
        if kind == 'next-init':
            return word & 0xFC00FFFF | NEXT << 16
        if kind == 'next-copy':
            return NEXT << 21 | CURRENT << 11 | 37
        return word & 0xFC00FFFF | NEXT << 21 | NEXT << 16
    if kind == 'next-id-pointer':
        if word >> 26 or word & 63 != 33:
            raise ValueError('Unknown adjacent-ID address pair')
        return word & ~(31 << 16) | NEXT << 16
    if kind == 'sort-less':
        if word >> 26 != 5:
            raise ValueError('Unknown bounded sort termination predicate')
        return CURRENT << 21 | (word >> 16 & 31) << 16 | 1 << 11 | 42
    if kind == 'sort-test':
        if word >> 26 != 5:
            raise ValueError('Unknown bounded sort branch')
        return word & 0xFC00FFFF | 1 << 21
    raise ValueError('Unknown complete route-layout derivation')


def normalize(raw, bindings):
    first, moved = core.normalize(raw, bindings)
    words = list(struct.unpack('>594I',raw))
    order = origins()
    if len(order) != WORDS - core.WORDS:
        raise ValueError('Changed route ranking/return extent')
    destination = {old:new for new,old in enumerate(order,core.WORDS) if isinstance(old,int)}
    destination[559] = 569
    result = list(struct.unpack('>490I',first))
    for new,origin in enumerate(order,core.WORDS):
        old = origin if isinstance(origin,int) else origin[1]
        word = words[old] if isinstance(origin,int) else derived(words,origin)
        op,rs = word >> 26, word >> 21 & 31
        if op in (4,5,6,7,20,21,22,23) or op == 17 and rs == 8:
            target = old + 1 + (((word & 65535)^32768)-32768)
            if target not in destination:
                raise ValueError('Unknown ranking/return branch destination')
            entry = {566:593,581:579}.get(old,destination[target])
            word = word & 0xFFFF0000 | (entry-new-1)&65535
        if new == 490:
            if op != 35 or rs != 29 or word & 65535 != 0x54:
                raise ValueError('Unknown rank-entry offset home')
            word = word & 0xFFFF0000 | 0x68
        if new == 534:
            mask = words[525]
            if mask >> 26 != 12 or mask & 65535 != 31 or rs != mask >> 16 & 31:
                raise ValueError('Unknown ranking variable-shift mask')
            word = word & ~(31 << 21) | (mask >> 21 & 31) << 21
        if new in (519,535):
            if new == 519 and (op != 17 or rs != 16 or word & 63 != 0) or (
                    new == 535 and (op or word & 63 != 36)):
                raise ValueError('Unknown commutative ranking sum/mask')
            word = core.swap(word,16,11) if new == 519 else core.swap(word,21,16)
        if new == 536:
            if op != 4:
                raise ValueError('Unknown score-mask join')
            word = word & 0x03FFFFFF | 20 << 26
        if new in (574,576,591):
            if op not in (20,21,22):
                raise ValueError('Unknown shared rank/sort join')
            word = word & 0x03FFFFFF | (op-16) << 26
        if new == 576:
            # No calls occur during ranking; COUNT is disjoint from all score,
            # ID and rank stores in the declared public/private arena.
            word = word & ~(31 << 21) | (words[484] >> 16 & 31) << 21
        if new in (560,561,566,567):
            offset = 1 if new in (560,567) else 4
            if word & 65535 != offset:
                raise ValueError('Unknown adjacent-element displacement')
            word &= 0xFFFF0000
        for shifts,rename in zip(core.fields(word),(GP.get(new,{}),FP.get(new,{}))):
            original = word
            if not set(rename) <= {word >> shift & 31 for shift in shifts} or any(not 0 <= v < 32 for v in rename.values()):
                raise ValueError('Unknown ranking register recipe')
            for shift in shifts:
                reg = original >> shift & 31
                word = word & ~(31 << shift) | rename.get(reg,reg) << shift
        result.append(word)
    # These LO16 bindings move from the eliminated ADDIU into the folded load.
    destination.update({495:505,496:539})
    for at,entries in bindings.items():
        if at//4 >= 481:
            if at//4 not in destination:
                raise ValueError('Lost ranking symbol binding')
            moved[destination[at//4]*4] = entries
    normalized = struct.pack('>604I',*result)
    if hashlib.sha256(normalized).hexdigest() != NORMALIZED_SHA:
        raise ValueError('Changed complete route-update layout')
    return normalized,moved


def relocate(raw,bindings,anchors):
    return core.relocate(raw,bindings,anchors)


def private_guards(before,raw,bindings):
    normalized,moved = normalize(raw,bindings)
    reader = csv.DictReader(io.StringIO(before.decode()))
    owner,function = source.source.OWNER,source.source.FUNCTION
    if any(row['filename']==owner and row['function']==function for row in reader):
        raise ValueError('Route-update guards already present')
    if not before.endswith(b'\n'):
        raise ValueError('Unterminated original guard prefix')
    # Ten output operations occupy insert fields; every compact source word
    # still has its own expected-word and expected-relocation guard.
    inserted = {321,325,333,337,345,349,379,415,443,569}
    old = struct.unpack('>594I',raw)
    new = struct.unpack('>604I',normalized)
    spec = lambda entries:';'.join(kind+':'+name for kind,name in entries) or '-'
    rows,destination = [],0
    for i,word in enumerate(old):
        row = dict(filename=owner,function=function,offset='0x%X'%(i*4),
            expected='0x%08X'%word,replacement='0x%08X'%new[destination],
            expected_relocations=spec(bindings.get(i*4,[])),
            replacement_relocations=spec(moved.get(destination*4,[])),
            note='Normalize source-derived route update output word %d; closed complete layout'%destination,
            insert_after='',insert_after_relocations='',omit='false')
        destination += 1
        if destination in inserted:
            row['insert_after'] = '0x%08X'%new[destination]
            row['insert_after_relocations'] = spec(moved.get(destination*4,[]))
            row['note'] += '; insert derived output word %d'%destination
            destination += 1
        rows.append(row)
    if destination != 604 or sum(bool(row['insert_after']) for row in rows) != 10:
        raise ValueError('Changed guarded route-update stream expansion')
    output = io.StringIO(newline='')
    csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n').writerows(rows)
    return before+output.getvalue().encode()
