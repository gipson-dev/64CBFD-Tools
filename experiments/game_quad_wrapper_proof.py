"""Straight-line value proof under the rectangle caller's explicit C frame contract."""
from collections import Counter
import struct


def address(base, offset):
    if isinstance(base, tuple) and base[0] in ('stack', 'address'):
        return (*base[:-1], base[-1] + offset)
    return ('address', base, offset)


def symbolic(raw, relocations):
    """Keep ordered FP operands symbolic, without claiming FP-environment parity.

    Actor fields are valid halfwords outside the callee frame and register-home
    area. The provider observes the ten ABI words and twelve-float quad, may
    modify that quad, outgoing homes and external memory, and obeys the ABI.
    Unexposed frame/register homes and caller-saved return registers are not C
    observables. Literal private/fault parity is tested on normalized code.
    """
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    regs = [0, *(('gpr', i) for i in range(1, 32))]
    regs[29] = ('stack', 0)
    floats = [('fpr', i) for i in range(32)]
    memory, records, calls, operations = {}, [], [], []
    pending, returned = None, None

    def load(where, size):
        if where in memory:
            value, stored_size = memory[where]
            if size != stored_size:
                raise ValueError('Unsupported overlapping proof load')
            return value
        if where[0] == 'stack' and where[1] < 0:
            raise ValueError('Uninitialized private-frame proof load')
        return ('read', where, size)

    def store(where, size, value):
        if where[0] != 'stack' or not -128 <= where[1] <= 12:
            raise ValueError('Store outside the declared C frame/home contract')
        if size != 4 or where[1] & 3:
            raise ValueError('Unsupported partial proof store')
        memory[where] = value, size

    for pc, word in enumerate(words):
        op, rs, rt, rd = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31
        immediate = ((word & 65535) + 32768) % 65536 - 32768
        delay = pending
        pending = None
        if word == 0:
            signature = ('nop',)
        elif op == 9:
            regs[rt] = address(regs[rs], immediate)
            signature = ('addiu', regs[rt])
        elif op in (33, 35, 36, 49):
            where = address(regs[rs], immediate)
            size = {33: 2, 35: 4, 36: 1, 49: 4}[op]
            value = load(where, size)
            if op == 33:
                value = ('signed-halfword', value)
            if op == 49:
                floats[rt] = value
            else:
                regs[rt] = value
            signature = (op, where, value)
        elif op in (43, 57):
            where = address(regs[rs], immediate)
            value = regs[rt] if op == 43 else floats[rt]
            store(where, 4, value)
            signature = (op, where, value)
        elif op == 17:
            fs, fd = word >> 11 & 31, word >> 6 & 31
            if rs == 4:
                if word & 2047:
                    raise ValueError('Malformed MTC1 encoding')
                floats[fs] = regs[rt]
                signature = ('mtc1', floats[fs])
            elif rs == 0:
                if word & 2047:
                    raise ValueError('Malformed MFC1 encoding')
                regs[rt] = floats[fs]
                signature = ('mfc1', regs[rt])
            elif rs == 20 and rt == 0 and word & 63 == 32:
                floats[fd] = ('cvt.s.w', floats[fs])
                signature = ('fp', floats[fd])
                operations.append(floats[fd])
            elif rs == 16 and word & 63 in (0, 1):
                floats[fd] = ('add.s' if word & 63 == 0 else 'sub.s', floats[fs], floats[rt])
                signature = ('fp', floats[fd])
                operations.append(floats[fd])
            else:
                raise ValueError('Unsupported symbolic floating instruction')
        elif op == 3:
            if delay or relocations.get(pc * 4) != [('R_MIPS_26', 'func_151700D8')] or word & 0x3FFFFFF:
                raise ValueError('Unknown symbolic call binding or delay')
            regs[31] = ('wrapper-continuation',)
            pending = ('call', pc)
            signature = None
        elif op == 0 and word & 63 == 8:
            if delay or pc != len(words) - 2 or word & 0x1FFFFF != 8:
                raise ValueError('Unknown symbolic return control')
            pending = ('return', pc, regs[rs])
            signature = None
        else:
            raise ValueError('Unsupported symbolic wrapper instruction: 0x%08X' % word)
        records.append(signature)
        regs[0] = 0
        if delay:
            if pending:
                raise ValueError('Control instruction in proof delay slot')
            if delay[0] == 'call':
                stack = regs[29]
                args = tuple(regs[4:8]) + tuple(load(address(stack, i * 4), 4) for i in range(4, 10))
                quad = tuple(load(address(args[0], i * 4), 4) for i in range(12))
                call = ('call', 'func_151700D8', args, quad)
                records[delay[1]] = call
                calls.append(call)
                for i in (*range(1, 16), 24, 25, 31):
                    regs[i] = ('provider-gpr', i, call)
                for i in range(20):
                    floats[i] = ('provider-fpr', i, call)
                for where in list(memory):
                    if where[0] == 'stack' and (-128 <= where[1] < -112 or -48 <= where[1] < 0):
                        memory[where] = ('provider-memory', where, call), 4
            else:
                returned = (delay[2], tuple(regs[i] for i in (*range(16, 24), 28, 29, 30, 31)), tuple(floats[20:]))
                records[delay[1]] = ('return', returned)
        if regs[26:28] != [('gpr', 26), ('gpr', 27)]:
            raise ValueError('Reserved kernel registers changed')
    if pending or returned is None or len(calls) != 1 or set(relocations) != {words.index(next(w for w in words if w >> 26 == 3)) * 4}:
        raise ValueError('Incomplete straight-line wrapper proof')
    return dict(records=records, result=(tuple(calls), returned), floating_operations=Counter(operations))


def prove(raw, old_relocations, normalized, new_relocations):
    left, right = symbolic(raw, old_relocations), symbolic(normalized, new_relocations)
    if left['result'] != right['result'] or left['floating_operations'] != right['floating_operations']:
        raise ValueError('Wrapper C value/ABI/dependency proof failed')
    return dict(single_path=True, symbolic_10_word_call_and_12_float_quad_equal=True,
        preserved_ABI_and_return_equal=True, ordered_float_expression_multiset_equal=True,
        framed_memory_contract=True, no_raw_private_fault_or_FP_environment_equivalence_claim=True)
