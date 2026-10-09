"""Fit complete renderer point-copy bases and nine-segment induction."""
import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

from tools.experiments import game_owner_ribbon_renderer_candidates as base
from tools.experiments import game_owner_ribbon_renderer_fitting as fitting

FITTED = fitting.SELECTED
RECORD = '''typedef struct {
    OwnerRibbonPosition32C8 position;
    u8 reserved[12];
} OwnerRibbonSample32C8;
'''
LOOP = 'for (offset = 0x18; offset != 0xF0; offset += 0x18)'


def replace_squared(body, names, declarations):
    remaining = [n for n in ('squaredX', 'squaredY', 'squaredZ') if n not in names]
    declaration = ('    f32 ' + ', '.join(remaining) + ';\n') if remaining else ''
    body = body.replace('    f32 squaredX, squaredY, squaredZ;\n', declaration + declarations)
    for name in names:
        normal = dict(squaredX='nx', squaredY='ny', squaredZ='nz')[name]
        expression = normal + ' * ' + normal
        for indent in ('        ', '    '):
            body = body.replace(indent + name + ' = ' + expression + ';\n', '')
        body = body.replace(name, '(' + expression + ')')
    return body


def point_base(body, square, loop=True):
    squares = (square,) if isinstance(square, str) else square
    body = replace_squared(body, squares, '    u8 *points;\n')
    body = body.replace('    first = *(OwnerRibbonPosition32C8 *)(actor + 0x48);',
        '    points = actor + 0x48;\n    first = *(OwnerRibbonPosition32C8 *)points;')
    body = body.replace('    second = *(OwnerRibbonPosition32C8 *)(actor + 0x60);',
        '    second = *(OwnerRibbonPosition32C8 *)(points + 0x18);')
    if loop:
        body = body.replace('actor + 0x48 + offset - 0x18', 'points + offset - 0x18').replace(
            'actor + 0x48 + offset)', 'points + offset)')
    return body


def pointer_loop(body, square_names, advance=False):
    declarations = '    u8 *previous, *point;\n'
    body = replace_squared(body, square_names, declarations)
    if advance:
        opening = 'previous = actor + 0x48;\n    point = actor + 0x60;\n    offset = 0x18;\n    do'
        body = body.replace(LOOP, opening)
        body = body.replace('        first = *(OwnerRibbonPosition32C8 *)(actor + 0x48 + offset - 0x18);',
            '        first = *(OwnerRibbonPosition32C8 *)previous;\n'
            '        offset += 0x18;\n        point += 0x18;')
        body = body.replace('actor + 0x48 + offset)', 'point - 0x18)')
        body = body.replace('    }\n    }\n    return output;',
            '        previous += 0x18;\n    } while (offset != 0xF0);\n    }\n    return output;')
    else:
        opening = ('previous = actor + 0x48;\n    point = actor + 0x60;\n'
            '    for (offset = 0x18; offset != 0xF0; offset += 0x18, previous += 0x18, point += 0x18)')
        body = body.replace(LOOP, opening).replace('actor + 0x48 + offset - 0x18', 'previous').replace(
            'actor + 0x48 + offset)', 'point)')
    return body


def typed_records(body):
    body = replace_squared(body, ('squaredZ',), '    OwnerRibbonSample32C8 *points;\n')
    body = body.replace('    first = *(OwnerRibbonPosition32C8 *)(actor + 0x48);',
        '    points = (OwnerRibbonSample32C8 *)(actor + 0x48);\n    first = points[0].position;')
    body = body.replace('    second = *(OwnerRibbonPosition32C8 *)(actor + 0x60);',
        '    second = points[1].position;')
    body = body.replace(LOOP, 'for (offset = 1; offset != 10; offset++)')
    body = body.replace('*(OwnerRibbonPosition32C8 *)(actor + 0x48 + offset - 0x18)',
        'points[offset - 1].position').replace('*(OwnerRibbonPosition32C8 *)(actor + 0x48 + offset)',
        'points[offset].position')
    return RECORD + body


def geometry_order(body, order):
    for point, indent in (('first', '    '), ('second', '        ')):
        lines = base.GEOMETRY.format(point=point).splitlines()[:6]
        assignments = {line.strip().split(' = ', 1)[0]: line.strip() for line in lines}
        before = '\n'.join(indent + assignments[name] for name in ('dx', 'dy', 'dz', 'rx', 'ry', 'rz'))
        after = '\n'.join(indent + assignments[name] for name in order)
        assert body.count(before) == 1
        body = body.replace(before, after)
    return body


def ray_first(body):
    return geometry_order(body, ('rx', 'ry', 'rz', 'dx', 'dy', 'dz'))


def aliased_scale(body, target):
    body = body.replace('f32 length, scale;', 'f32 length, squared;')
    body = body.replace('if (length == 0.0f)', 'if (squared == 0.0f)').replace(
        'length = sqrtf(length);', 'length = sqrtf(squared);')
    lines = body.splitlines(True)
    body = ''.join(line.replace('length = ', 'squared = ')
        if 'length = ' in line and 'sqrtf' not in line else line for line in lines)
    return body.replace('scale = ', target + ' = ').replace('* scale;', '* ' + target + ';')


def split_magnitude(body):
    body = body.replace('f32 squaredZ;', 'f32 squared;')
    for indent in ('        ', '    '):
        body = body.replace(indent + 'squaredZ = nz * nz;\n', '')
    body = body.replace('length = (nx * nx) + (ny * ny) + squaredZ;',
        'squared = (nx * nx) + (ny * ny) + (nz * nz);').replace(
        'if (length == 0.0f)', 'if (squared == 0.0f)').replace(
        'length = sqrtf(length);', 'length = sqrtf(squared);')
    return body


def origin_schedule(body, split=False, early_sync=False):
    if early_sync:
        line = '    origin = (OwnerRibbonPosition32C8 *)(D_800DBFF0 + view * 0x9A0 + 0x2F8);\n    sync = 1;'
        assert body.count(line) == 1
        body = body.replace(line, '    sync = 1;\n' + line.split('\n')[0])
    if split:
        line = '    origin = (OwnerRibbonPosition32C8 *)(D_800DBFF0 + view * 0x9A0 + 0x2F8);'
        assert body.count(line) == 1
        body = body.replace(line, '    origin = (OwnerRibbonPosition32C8 *)(D_800DBFF0 + view * 0x9A0);\n'
            '    origin = (OwnerRibbonPosition32C8 *)((u8 *)origin + 0x2F8);')
    return body


def named_zero(body):
    body = body.replace('f32 squaredZ;', 'f32 zero;')
    for indent in ('        ', '    '):
        body = body.replace(indent + 'squaredZ = nz * nz;\n', '')
    body = body.replace('squared = (nx * nx) + (ny * ny) + squaredZ;',
        'squared = (nx * nx) + (ny * ny) + (nz * nz);').replace(
        'if (squared == 0.0f)', 'if (squared == zero)').replace(
        'ox = 0.0f; oy = 0.0f; oz = 0.0f;', 'ox = zero; oy = zero; oz = zero;')
    return body.replace('    points = actor + 0x48;',
        '    zero = 0.0f;\n    points = actor + 0x48;')


def candidates():
    yield 'prior-fit', FITTED
    for square in ('squaredX', 'squaredY', 'squaredZ'):
        for loop in (False, True):
            body = point_base(FITTED, square, loop)
            name = 'base-' + square + ('-loop' if loop else '-initial')
            yield name, body
            yield name + '-ray-first', ray_first(body)
    for squares in (('squaredX', 'squaredY'), ('squaredX', 'squaredZ'), ('squaredY', 'squaredZ')):
        common = point_base(FITTED, squares)
        yield 'base-two-' + '-'.join(squares), common
        yield 'base-two-' + '-'.join(squares) + '-ray-first', ray_first(common)
        for advance in (False, True):
            yield 'pointers-' + '-'.join(squares) + ('-advance' if advance else '-for'), pointer_loop(
                FITTED, squares, advance)
    records = typed_records(FITTED)
    yield 'typed-records', records
    yield 'typed-records-less', records.replace('offset != 10', 'offset < 10')
    common = point_base(FITTED, ('squaredX', 'squaredY'))
    for target in ('dx', 'dy', 'dz'):
        alias = aliased_scale(common, target)
        yield 'scale-reuse-' + target, alias
        yield 'scale-reuse-' + target + '-ray-first', ray_first(alias)
    yield 'split-magnitude', split_magnitude(common)
    zero = named_zero(aliased_scale(common, 'dz'))
    yield 'named-zero', zero
    yield 'named-zero-reverse', zero.replace('if (squared == zero)', 'if (zero == squared)')
    lease = aliased_scale(common, 'dz')
    for order in (('rx', 'ry', 'rz', 'dy', 'dz', 'dx'), ('dy', 'dz', 'rx', 'ry', 'rz', 'dx'),
            ('dy', 'dz', 'rx', 'dx', 'ry', 'rz'), ('dy', 'dz', 'dx', 'rx', 'ry', 'rz'),
            ('rz', 'ry', 'rx', 'dz', 'dy', 'dx'), ('rx', 'dy', 'ry', 'dz', 'rz', 'dx')):
        yield 'scale-inputs-' + '-'.join(order), geometry_order(lease, order)
    for split, early in ((False, True), (True, False), (True, True)):
        yield 'origin-' + str(int(split)) + '-' + str(int(early)), origin_schedule(common, split, early)


SELECTED_NAME = 'scale-reuse-dz'
SELECTED = dict(candidates())[SELECTED_NAME]
FP_MAPS = ((0x288, 0x380, {26: 28, 28: 30, 30: 26}),
           (0x4CC, 0x5D4, {28: 30, 30: 28}))
FP_OFFSETS = (0x288, 0x338, 0x33C, 0x34C, 0x350, 0x358, 0x35C,
              0x58C, 0x590, 0x5A0, 0x5A4, 0x5AC, 0x5B0)


def fp_fields(word):
    op, fmt, fn = word >> 26, word >> 21 & 31, word & 63
    if op in (49, 53):
        return (), (16,)
    if op in (57, 61):
        return (16,), ()
    if op != 17:
        return (), ()
    if fmt == 0:
        return (11,), ()
    if fmt == 4:
        return (), (11,)
    if fmt == 8:
        return (), ()
    if fmt == 16:
        if fn in (0, 1, 2, 3):
            return (11, 16), (6,)
        if fn in (4, 6, 13):
            return (11,), (6,)
        if fn == 50:
            return (11, 16), ()
    raise ValueError('unsupported FP proof word0x%08X' % word)


def normalize_fp(words):
    if len(words) != 475 or words[0] != 0x27BDFEB8 or words[0x288 // 4] != 0x4480E000:
        raise ValueError('complete selected475-word/frame0x148 body required')
    result = list(words)
    for begin, end, mapping in FP_MAPS:
        for offset in range(begin, end, 4):
            reads, writes = fp_fields(words[offset // 4])
            word = words[offset // 4]
            for shift in set(reads + writes):
                register = words[offset // 4] >> shift & 31
                word = (word & ~(31 << shift)) | (mapping.get(register, register) << shift)
            result[offset // 4] = word
    offsets = tuple(i * 4 for i, (raw, new) in enumerate(zip(words, result)) if raw != new)
    if offsets != FP_OFFSETS:
        raise ValueError('stale FP allocation recipe: ' + repr(offsets))
    return result


def certify_fp(words):
    """Prove ordered FP operands agree on all1024 paths of the fixed nine-segment loop.

    GPR instructions and memory addresses stay identical. Every FP-to-GPR or
    FP-store input is checked, so GPR/memory equality is an inductive invariant.
    Fresh result tokens are permitted only after ordered inputs and op bits agree.
    The identical save/restore tail closes the callee-saved register lifetimes.
    """
    fitted = normalize_fp(words)
    for i, (raw, new) in enumerate(zip(words, fitted)):
        reads, writes = fp_fields(raw)
        mask = sum(31 << shift for shift in set(reads + writes))
        if raw & ~mask != new & ~mask or fp_fields(raw) != fp_fields(new):
            raise ValueError('non-FP-register bits changed at0x%X' % (i * 4))
    required = {0x4CC: 0x8D210000, 0x4D0: 0x25080018, 0x4D4: 0x24E70018,
                0x728: 0x1512FF68, 0x72C: 0x25290018}
    if any(words[pc // 4] != word for pc, word in required.items()):
        raise ValueError('original byte-offset/two-pointer loop required')
    if words[:0x4CC // 4].count(0x24080018) != 1 or words[:0x4CC // 4].count(0x241200F0) != 1:
        raise ValueError('original24..240 induction initialization required')
    from tools.experiments.game_owner_endpoint_quad_matching import fields
    for pc in range(0x4CC, 0x728, 4):
        _, destinations = fields(words[pc // 4])
        changed_counter = [words[pc // 4] >> shift & 31 for shift in destinations
                           if words[pc // 4] >> shift & 31 in (8, 18)]
        if changed_counter and pc != 0x4D0:
            raise ValueError('counter/limit changed unexpectedly at0x%X' % pc)
    initial = tuple(('incoming-FP', i) for i in range(32))
    pending = [(0x288, initial, initial, 0)]
    reached, paths, steps = set(), 0, 0

    def step(pc, a, b, iteration):
        nonlocal steps
        raw, new = words[pc // 4], fitted[pc // 4]
        reads, destinations = fp_fields(raw)
        for shift in reads:
            ra, rb = raw >> shift & 31, new >> shift & 31
            width = 2 if raw >> 26 == 61 else 1
            if a[ra:ra + width] != b[rb:rb + width]:
                raise ValueError('live FP operand mismatch at0x%X iteration%d' % (pc, iteration))
        a, b = list(a), list(b)
        for shift in destinations:
            ra, rb = raw >> shift & 31, new >> shift & 31
            width = 2 if raw >> 26 == 53 else 1
            for half in range(width):
                token = ('result', pc, iteration, shift, half)
                a[ra + half] = b[rb + half] = token
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
                if iteration != 9 or a != b:
                    raise ValueError('live FP state escaped the unchanged restore tail')
                paths += 1
                break
            elif op == 3 or (op == 0 and fn == 9):
                raise ValueError('unexpected call inside closed FP lifetimes')
            else:
                pc += 4
    if paths != 1024 or reached != set(range(0x288, 0x76C, 4)):
        raise ValueError('incomplete nine-segment FP path proof')
    return dict(paths=paths, loop_iterations=9, words_reached=len(reached), steps=steps,
        changed_words=len(FP_OFFSETS), ordered_operands_and_op_bits=True,
        GPR_memory_and_control_flow_unchanged=True, FP_lifetimes_closed_by_restore=True,
        not_installed=True)


def decompile(root, out):
    context = '''typedef unsigned char u8;
typedef unsigned short u16;
typedef short s16;
typedef unsigned int u32;
typedef int s32;
typedef float f32;
typedef struct { struct { s16 ob[3]; u16 flag; s16 tc[2]; u8 cn[4]; } v; } Vtx;
typedef struct { struct { u32 w0, w1; } words; } Gfx;
''' + base.TYPES + base.DECLARATIONS + '''
struct _m2c_stack_func_151B32C8 {
    u8 reserved00[0xBE];
    u8 combine, bank;
    s32 renderMode, primA, primB, primG, primR, alpha, envB, envG, envR, mode2, mode1;
    u8 reservedEC[3];
    u8 sync;
    u8 reservedF0[0x30];
    OwnerRibbonPosition32C8 *origin;
    u8 reserved124[4];
    OwnerRibbonPosition32C8 second, first;
    Vtx *cursor;
    u8 reserved144[4];
};
Gfx *func_151B32C8(Gfx *, u8 *, s16);
f32 sqrtf(f32);
'''
    path = out / 'typed-context.c'
    path.write_text(context)
    result = subprocess.run([sys.executable, str(root / 'conker/tools/mips_to_c/m2c.py'),
        '--context', str(path), '--no-cache', '--globals', 'none',
        '--reg-vars', 'f0,f2,f12,f14,f16,f18,f20,f22,f24,f28,f30,t0,t1,t2',
        '-f', base.FUNCTION, str(root / 'conker/asm/1E0560.s')],
        cwd=root, capture_output=True, text=True)
    (out / 'typed-decompiler.txt').write_text(result.stdout)
    (out / 'typed-decompiler.stderr').write_text(result.stderr)
    if result.returncode:
        raise ValueError(result.stdout + result.stderr)
    print('Reference-only typed decompiler evidence:', len(result.stdout), 'bytes', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    parser.add_argument('--decompiler', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-ribbon-renderer-induction'
    out.mkdir(parents=True, exist_ok=True)
    if args.decompiler:
        decompile(root, out)
        return
    forms = dict(candidates())
    if args.form:
        forms = {args.form: forms[args.form]}
    rows = []
    for name, body in forms.items():
        meta, words = base.compile_candidate(root, out, name, body)
        meta['source_sha256'] = hashlib.sha256(body.encode()).hexdigest()
        meta['words_sha256'] = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
        rows.append(meta)
        print(name, meta['body_words'], meta['frame'], meta['differences'], flush=True)
    (out / ((args.form or 'all') + '.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
