"""Check the two debris scheduling regions and its unescaped six-byte staging home."""
from collections import Counter


def address(base, offset):
    if isinstance(base, tuple) and base[0] in ('frame', 'actor', 'vector', 'global', 'kinds'):
        return (*base[:-1], base[-1] + offset)
    return ('address', base, offset)


def narrowed(value, width):
    return value & ((1 << width) - 1) if isinstance(value, int) else ('low', width, value)


def evaluate(words, relocations, start, end, kind_home, initialization):
    regs = [0, *(('gpr', i) for i in range(1, 32))]
    floats = [('fpr', i) for i in range(32)]
    regs[29], regs[14], regs[2], regs[16] = ('frame', 0), ('actor', 0), ('asset-return',), ('kind-word',)
    regs[18] = ('vector', 0)
    floats[0], floats[2] = 0, 0x3F800000
    if not initialization:
        for register, name in ((20, 'coefficient'), (22, 'velocity-rng-scale'), (24, 'spin-rng-scale'),
                (26, 'origin-x'), (28, 'origin-y'), (30, 'origin-z')):
            floats[register] = ('saved', name)
    memory, reads, operations, records = {}, [], [], []

    def where(rs, immediate, at, mode):
        entries = relocations.get(at * 4, [])
        if entries:
            if len(entries) != 1 or entries[0][0] != 'R_MIPS_LO16':
                raise ValueError('Unknown debris proof low binding')
            symbol = entries[0][1]
            if regs[rs] != ('high', symbol):
                raise ValueError('Debris proof lost a high/low dependency')
            return ('global', symbol, immediate)
        target = address(regs[rs], immediate)
        if mode == 'pointer' and target == ('frame', kind_home):
            return ('kinds', 0)
        return target

    def load(target, size):
        reads.append((target, size))
        if target in memory:
            if memory[target][0] != size:
                raise ValueError('Overlapping debris proof access')
            return memory[target][1]
        if target[0] == 'frame' and not 0x120 <= target[1] < 0x138:
            raise ValueError('Unexpected private-frame debris proof load')
        return ('read', target, size)

    for at in range(start, end):
        word = words[at]
        op, rs, rt, fs, fd = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31
        immediate = ((word & 65535) + 32768) % 65536 - 32768
        if op == 15:
            entries = relocations.get(at * 4, [])
            if entries:
                if len(entries) != 1 or entries[0][0] != 'R_MIPS_HI16':
                    raise ValueError('Unknown debris proof high binding')
                if immediate:
                    raise ValueError('Unsupported debris proof high addend')
                regs[rt] = ('high', entries[0][1])
            else:
                regs[rt] = word << 16 & 0xFFFFFFFF
            signature = ('lui', regs[rt])
        elif op == 9:
            regs[rt] = immediate & 0xFFFFFFFF if rs == 0 else where(rs, immediate, at, 'pointer')
            signature = ('addiu', regs[rt])
        elif op in (12,):
            regs[rt] = ('and', regs[rs], word & 65535)
            signature = ('andi', regs[rt])
        elif op in (33, 36, 49):
            target = where(rs, immediate, at, 'load')
            size = 2 if op == 33 else 1 if op == 36 else 4
            value = load(target, size)
            if op == 33:
                value = ('sign16', value)
            elif op == 36:
                value = ('zero8', value)
            if op == 49:
                floats[rt] = value
            else:
                regs[rt] = value
            signature = ('load', op, target, value)
        elif op in (40, 43, 57):
            target = where(rs, immediate, at, 'store')
            if target[0] != 'frame' or not 0xBC <= target[1] < 0x11C:
                raise ValueError('Debris store escaped the packet object')
            value = floats[rt] if op == 57 else narrowed(regs[rt], 8 if op == 40 else 32)
            size = 1 if op == 40 else 4
            memory[target] = size, value
            signature = ('store', op, target, value)
        elif op == 0 and word & 63 == 37 and rt == 0:
            regs[fs] = regs[rs]
            signature = ('move', regs[fs])
        elif op == 17:
            fn = word & 63
            if rs == 4:
                floats[fs] = regs[rt]
                signature = ('mtc1', floats[fs])
            elif rs == 20 and rt == 0 and fn == 32:
                floats[fd] = ('cvt.s.w', floats[fs])
                operations.append(floats[fd])
                signature = ('fp', floats[fd])
            elif rs == 16 and fn in (0, 2):
                floats[fd] = ('add.s' if fn == 0 else 'mul.s', floats[fs], floats[rt])
                operations.append(floats[fd])
                signature = ('fp', floats[fd])
            elif rs == 16 and rt == 0 and fn == 5:
                floats[fd] = ('abs.s', floats[fs])
                operations.append(floats[fd])
                signature = ('fp', floats[fd])
            else:
                raise ValueError('Unsupported debris proof FP operation')
        elif op == 3 and at == 112 and not word & 0x3FFFFFF and relocations.get(at * 4) == [('R_MIPS_26', 'func_150ADA20')]:
            regs[31] = ('return-to', 114)
            signature = ('zero-argument-rng',)
        else:
            raise ValueError('Unsupported debris proof instruction at %d: %08X' % (at, word))
        regs[0] = 0
        records.append(signature)
    live = tuple(regs[i] for i in (*range(16, 24), 28, 29, 30, 31))
    return dict(live=live, saved_floats=tuple(floats[20:]), memory=memory,
        reads=Counter(reads), floating_operations=Counter(operations), records=Counter(records))


def prove(raw, old_rel, normalized, new_rel):
    if len(raw) != 205 or len(normalized) != 205:
        raise ValueError('Unknown debris proof extent')
    regions = set(range(24, 74)) | set(range(92, 114))
    if any(a != b for i, (a, b) in enumerate(zip(raw, normalized)) if i not in regions):
        raise ValueError('Debris transformation escaped the two checked regions')
    if old_rel.get(360) != new_rel.get(360) or old_rel.get(448) != new_rel.get(448):
        raise ValueError('Debris provider boundary moved')
    for initialization, start, end in ((True, 24, 74), (False, 92, 114)):
        left = evaluate(raw, old_rel, start, end, 0x94, initialization)
        right = evaluate(normalized, new_rel, start, end, 0x9C, initialization)
        if left != right:
            raise ValueError('Debris value/operation graph differs: ' + repr({key: (left[key], right[key]) for key in left if left[key] != right[key]}))
    return dict(two_regions_checked=True, every_ordered_FP_expression_and_operation_retained=True,
        live_saved_roles_and_packet_writes_equal=True, packet_frame_home_0xBC_unchanged=True,
        unescaped_six_byte_kind_home_0x94_to_0x9C=True, loop_and_all_nine_call_boundaries_unchanged=True,
        ordinary_disjoint_actor_table_and_frame_memory_contract=True,
        no_raw_private_fault_order_FP_environment_or_native_indeterminate_byte_claim=True)
