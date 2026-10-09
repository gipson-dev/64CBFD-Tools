"""Complete ribbon copy-base screens and closed GPR temporary lifetimes."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.experiments import game_owner_ribbon_renderer_candidates as base
from tools.experiments import game_owner_ribbon_renderer_induction as induction
from tools.experiments.game_owner_endpoint_quad_matching import fields as quad_fields

SEED = induction.SELECTED
GPR_MAP = {14: 15, 15: 14, 24: 25, 25: 24}
BEGIN, END = 0x26C, 0x730


def position_pointer(body):
    body = body.replace('u8 *points;', 'OwnerRibbonPosition32C8 *points;').replace(
        'points = actor + 0x48;', 'points = (OwnerRibbonPosition32C8 *)(actor + 0x48);').replace(
        'first = *(OwnerRibbonPosition32C8 *)points;', 'first = points[0];').replace(
        'second = *(OwnerRibbonPosition32C8 *)(points + 0x18);', 'second = points[2];')
    return body.replace('(points + offset', '((u8 *)points + offset')


def candidates():
    yield 'prior-induction', SEED
    yield 'register-base', SEED.replace('u8 *points;', 'register u8 *points;')
    yield 'position-pointer', position_pointer(SEED)
    yield 'position-pointer-register', position_pointer(SEED).replace(
        'OwnerRibbonPosition32C8 *points;', 'register OwnerRibbonPosition32C8 *points;')
    record = position_pointer(SEED).replace('OwnerRibbonPosition32C8 *points;',
        'OwnerRibbonSample32C8 *points;').replace('points = (OwnerRibbonPosition32C8 *)',
        'points = (OwnerRibbonSample32C8 *)').replace('first = points[0];',
        'first = points[0].position;').replace('second = points[2];', 'second = points[1].position;')
    yield 'record-base', induction.RECORD + record
    yield 'integer-base', SEED.replace('u8 *points;', 'u32 points;').replace(
        'points = actor + 0x48;', 'points = (u32)actor + 0x48;')
    yield 'advance-and-restore', SEED.replace(
        'second = *(OwnerRibbonPosition32C8 *)(points + 0x18);',
        'points += 0x18;\n    second = *(OwnerRibbonPosition32C8 *)points;\n    points -= 0x18;')
    yield 'second-base', SEED.replace('points = actor + 0x48;', 'points = actor + 0x60;').replace(
        'first = *(OwnerRibbonPosition32C8 *)points;',
        'first = *(OwnerRibbonPosition32C8 *)(points - 0x18);').replace(
        'second = *(OwnerRibbonPosition32C8 *)(points + 0x18);',
        'second = *(OwnerRibbonPosition32C8 *)points;\n    points -= 0x18;')
    yield 'initial-offset', SEED.replace('second = *(OwnerRibbonPosition32C8 *)(points + 0x18);',
        'offset = 0x18;\n    second = *(OwnerRibbonPosition32C8 *)(points + offset);')
    for label, anchor in (('before-last-helper', '    output = func_15142FBC('),
                          ('before-first-helper', '    output = func_15142B7C('),
                          ('before-resource', '    func_151D5D60(')):
        body = SEED.replace('    points = actor + 0x48;\n', '')
        yield label, body.replace(anchor, '    points = actor + 0x48;\n' + anchor)
    for name, ctype in (('word-copies', 'u32'), ('float-copies', 'f32')):
        body = SEED
        for target, address in (('first', 'points'), ('second', 'points + 0x18')):
            line = '    ' + target + ' = *(OwnerRibbonPosition32C8 *)' + (
                address if address == 'points' else '(' + address + ')') + ';'
            replacement = '\n'.join('    *(%s *)&%s.%s = *(%s *)(%s + %d);' %
                (ctype, target, axis, ctype, address, index * 4)
                for index, axis in enumerate(('x', 'y', 'z')))
            assert body.count(line) == 1
            body = body.replace(line, replacement)
        yield name, body


SELECTED_NAME = 'before-last-helper'
SELECTED = dict(candidates())[SELECTED_NAME]


def fields(word):
    if word >> 26 == 0 and word & 63 == 9:
        return (21,), (11,)
    if word >> 26 in (53, 61):
        return (21,), ()
    return quad_fields(word)


def normalize_gpr(words):
    if len(words) != 475 or words[0] != 0x27BDFEB8:
        raise ValueError('complete selected475-word/frame0x148 body required')
    result = list(words)
    for offset in range(BEGIN, END, 4):
        reads, writes = fields(words[offset // 4])
        word = words[offset // 4]
        for shift in set(reads + writes):
            register = words[offset // 4] >> shift & 31
            word = (word & ~(31 << shift)) | (GPR_MAP.get(register, register) << shift)
        result[offset // 4] = word
    return result


def normalize(words):
    return normalize_gpr(induction.normalize_fp(words))


def certify_gpr(words):
    """Check ordered GPR inputs on the independently certified FP-normalized body.

    FP instruction fields are untouched; address/store/MTC1 operands agree.
    Fresh tokens follow identical operations with identical ordered inputs.
    Memory and FP equality are therefore inductive invariants. Caller-visible
    return and saved registers must agree after the unchanged restore tail.
    """
    induction.certify_fp(words)
    words = induction.normalize_fp(words)
    fitted = normalize_gpr(words)
    offsets = [i * 4 for i, (a, b) in enumerate(zip(words, fitted)) if a != b]
    for i, (raw, new) in enumerate(zip(words, fitted)):
        reads, writes = fields(raw)
        mask = sum(31 << shift for shift in set(reads + writes))
        if raw & ~mask != new & ~mask or fields(raw) != fields(new):
            raise ValueError('non-GPR operand bits changed at0x%X' % (i * 4))
    initial = (('zero',),) + tuple(('incoming', i) for i in range(1, 32))
    pending = [(BEGIN, initial, initial, 0)]
    reached, paths, steps = set(), 0, 0

    def step(pc, a, b, iteration):
        nonlocal steps
        raw, new = words[pc // 4], fitted[pc // 4]
        reads, destinations = fields(raw)
        for shift in reads:
            if a[raw >> shift & 31] != b[new >> shift & 31]:
                raise ValueError('live GPR operand mismatch at0x%X iteration%d' % (pc, iteration))
        a, b = list(a), list(b)
        for shift in destinations:
            ra, rb = raw >> shift & 31, new >> shift & 31
            token = ('result', pc, iteration, shift)
            if ra:
                a[ra] = token
            if rb:
                b[rb] = token
        reached.add(pc)
        steps += 1
        return tuple(a), tuple(b)

    while pending:
        pc, a, b, iteration = pending.pop()
        while pc < 0x76C:
            if pc == 0x4CC:
                iteration += 1
            word = words[pc // 4]
            op, rs, rt, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word & 63
            a, b = step(pc, a, b, iteration)
            if op in (4, 5) or (op == 17 and rs == 8):
                a, b = step(pc + 4, a, b, iteration)
                immediate = word & 65535
                target = pc + 4 + (immediate if immediate < 32768 else immediate - 65536) * 4
                if pc == 0x728:
                    pc = target if iteration < 9 else pc + 8
                elif op == 4 and rs == rt == 0:
                    pc = target
                elif op == 17 and rs == 8:
                    pending.append((target, a, b, iteration))
                    pc += 8
                else:
                    raise ValueError('unexpected control flow at0x%X' % pc)
            elif op == 0 and fn == 8:
                a, b = step(pc + 4, a, b, iteration)
                if iteration != 9 or any(a[r] != b[r] for r in (2, *range(16, 24), 29, 30, 31)):
                    raise ValueError('live GPR state escaped the unchanged restore tail')
                paths += 1
                break
            elif op == 3 or (op == 0 and fn == 9):
                raise ValueError('unexpected call inside closed GPR lifetimes')
            else:
                pc += 4
    if paths != 1024 or reached != set(range(BEGIN, 0x76C, 4)):
        raise ValueError('incomplete nine-segment GPR path proof')
    return dict(paths=paths, loop_iterations=9, words_reached=len(reached), steps=steps,
        changed_words=len(offsets), offsets=offsets, ordered_GPR_operands_and_op_bits=True,
        FP_fields_memory_order_and_control_flow_unchanged=True,
        ABI_return_and_saved_GPR_lifetimes_closed=True, input_body_FP_normalized=True,
        not_installed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    parser.add_argument('--certificate', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-ribbon-renderer-registers'
    forms = dict(candidates())
    if args.form:
        forms = {args.form: forms[args.form]}
    rows = []
    for name, body in forms.items():
        meta, words = base.compile_candidate(root, out, name, body)
        meta['source_sha256'] = hashlib.sha256(body.encode()).hexdigest()
        meta['words_sha256'] = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
        if args.certificate:
            meta['certificate'] = certify_gpr(words)
            retail = struct.unpack_from('>475I', (root / 'conker/conker.us.bin').read_bytes(), base.ROM)
            meta['normalized_differences'] = sum(a != b for a, b in zip(retail, normalize(words)))
        rows.append(meta)
        print(name, meta['body_words'], meta['frame'], meta['differences'],
              meta.get('normalized_differences', ''), flush=True)
    (out / ((args.form or 'all') + '.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
