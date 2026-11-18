"""Independent FPR allocation relation and complete scratch-use closure."""
import hashlib
import json
from tools.experiments import game_radial_damping_151afc88_match as s
from tools.experiments.game_actor_state_tick_integration import symbol_rows, elf_slot_offset

RENAME = {4: 10, 10: 4, 6: 16, 16: 6, 8: 18, 18: 8}


def rename(word):
    op, fmt = word >> 26, word >> 21 & 31
    if op in (49, 57):
        reg = word >> 16 & 31
        return (word & ~(31 << 16)) | RENAME.get(reg, reg) << 16
    if op == 17 and fmt in (0, 4):
        reg = word >> 11 & 31
        return (word & ~(31 << 11)) | RENAME.get(reg, reg) << 11
    if op == 17 and fmt == 16:
        for shift in (16, 11, 6):
            reg = word >> shift & 31
            word = (word & ~(31 << shift)) | RENAME.get(reg, reg) << shift
        return word
    assert op == 15, hex(word)
    return word


def derive(words):
    assert words == s.PIN['bound_source_words'], 'source words or bindings changed'
    return [rename(w) if 47 <= i <= 58 else w for i, w in enumerate(words)]


def symbolic(words):
    f = [('FPR', i) for i in range(32)]
    at = None
    events, fp = [], []
    for w in words[47:59]:
        op, rs, rt, fs, fd, fn = w >> 26, w >> 21 & 31, w >> 16 & 31, w >> 11 & 31, w >> 6 & 31, w & 63
        if op == 15:
            assert rt == 1
            at = ('BITS', (w & 65535) << 16)
        elif op == 17 and rs == 4:
            assert rt == 1 and fs in RENAME
            f[fs] = at
        elif op == 49:
            assert rs == 29
            f[rt] = ('MEMORY', rs, w & 65535)
        elif op == 57:
            assert rs == 29
            events.append(('STORE', rs, w & 65535, f[rt]))
        else:
            assert op == 17 and rs == 16 and fn in (0, 2), hex(w)
            value = ('FP', fn, f[fs], f[rt])
            fp.append(value)
            f[fd] = value
    return f, events, fp


def fp_uses(word):
    op, rs, rt, fs, fd, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
    if op == 49:
        return set(), {rt}
    if op == 57:
        return {rt}, set()
    if op != 17:
        return set(), set()
    if rs == 4:
        return set(), {fs}
    if rs == 0:
        return {fs}, set()
    assert rs in (16, 20) and fn in (0, 2, 6, 7, 32), hex(word)
    return ({fs, rt} if fn in (0, 2) else {fs}), {fd}


def prove(source, retail):
    assert len(source) == len(retail) == 135
    assert all(source[i] == retail[i] for i in range(135) if not 47 <= i <= 58)
    assert [rename(w) for w in source[47:59]] == retail[47:59]
    a, stores_a, fp_a = symbolic(source)
    b, stores_b, fp_b = symbolic(retail)
    assert stores_a == stores_b and fp_a == fp_b and len(stores_a) == 3 and len(fp_a) == 2
    assert all(a[i] == b[RENAME.get(i, i)] for i in range(32))
    assert a[2] == b[2]
    pending = set(RENAME)
    elf = (s.FROZEN / 'conker/build/conker.us.elf').read_bytes()
    lookup = {row[1]: row[2][1:3] for row in symbol_rows(elf)}
    helpers = {}
    import struct
    for name in ('func_150ADA20', 'func_150ADA68'):
        entry, size = lookup[name]
        raw = elf[elf_slot_offset(elf, entry, size):elf_slot_offset(elf, entry, size) + size]
        helpers[entry] = list(struct.unpack('>' + 'I' * (size // 4), raw))
    killed = []

    def instruction(w, site):
        reads, writes = fp_uses(w)
        assert not reads & pending, ('read of differing scratch role', site, reads & pending)
        killed.extend((site, reg) for reg in sorted(writes & pending))
        pending.difference_update(writes)

    for i in range(59, 83):
        w = retail[i]
        if w >> 26 == 3:
            target = 0x10000000 | ((w & 0x3FFFFFF) << 2)
            assert target in helpers, hex(target)
            for n, hw in enumerate(helpers[target]):
                instruction(hw, ('helper', target, n))
        else:
            instruction(w, ('caller', i))
    assert not pending and {reg for _, reg in killed} == set(RENAME)
    return dict(complete_words=135, different_words=10, window=[47, 58],
                ordered_FP_operations_equal=2, position_stores_equal=3,
                scratch_roles_killed_before_use=killed,
                actual_zero_argument_helpers_checked=True,
                helper_sha256={hex(at): hashlib.sha256(struct.pack('>' + 'I' * len(ws), *ws)).hexdigest() for at, ws in helpers.items()},
                literal_fault_register_states_qualified=False)


def main(source, retail):
    report = prove(source, retail)
    controls = []
    for label, i in (('wrong-coordinate-destination', 55), ('wrong-scale-operand', 51), ('wrong-constant-register', 50)):
        bad = retail[:]
        bad[i] ^= 1 << 16
        try:
            prove(source, bad)
        except AssertionError:
            controls.append(label)
        else:
            raise AssertionError(('ineffective proof control', label))
    report['negative_controls'] = controls
    (s.OUT / 'proof-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report
