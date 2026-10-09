"""Complete owner ribbon setup source fitting and closed scheduling windows."""
import argparse
import csv
import io
import json
import struct
from collections import Counter
from pathlib import Path

from tools.experiments import game_owner_ribbon_renderer_candidates as base
from tools.experiments import game_owner_ribbon_renderer_registers as registers
from tools.pad_generated_object import parse_object

SEED = registers.SELECTED
MODE = 'renderMode | 0x80000 | D_800D2C9C | 0x2CA0'
PAIR = 'D_800A4AC8[bank * 2 + 1] | D_800A4AC8[bank * 2]'


def candidates():
    for reverse in (False, True):
        body = SEED.replace(PAIR, 'D_800A4AC8[bank * 2] | D_800A4AC8[bank * 2 + 1]') if reverse else SEED
        label = 'reverse-table' if reverse else 'prior-shared-base'
        yield label, body
        for local in ('offset', 'mode1', 'renderMode', 'textureT', 'graphicsMode'):
            assignment = '    %s = renderMode | 0x80000 | D_800D2C9C;\n' % local
            variant = body.replace('    output = func_15142FBC(', assignment + '    output = func_15142FBC(')
            variant = variant.replace(MODE, local + ' | 0x2CA0')
            if local == 'graphicsMode':
                variant = variant.replace('f32 squaredZ;', 'u32 graphicsMode;').replace(
                    '    squaredZ = nz * nz;\n', '').replace('squaredZ', '(nz * nz)')
            yield label + '-mode-' + local, variant


SELECTED_NAME = 'prior-shared-base'
_selected = dict(candidates())[SELECTED_NAME]
_prefix, _allocated = _selected.split('    if (cursor != NULL) {\n', 1)
_work, _tail = _allocated.rsplit('    }\n    return output;', 1)
_work = _work.replace('        nz = dx * ry - rx * dy;\n    squaredZ = nz * nz;\n'
    '    squared = (nx * nx) + (ny * ny) + squaredZ;',
    '        nz = dx * ry - rx * dy;\n        squaredZ = nz * nz;\n'
    '        squared = (nx * nx) + (ny * ny) + squaredZ;')
SELECTED = _prefix + '    if (cursor != NULL) {\n' + ''.join(
    ('    ' + line if line.strip() else line) for line in _work.splitlines(True)) + '    }\n    return output;' + _tail

PERMUTATIONS = (
    (0xCC, (0xD0, 0xCC, 0x108, 0xDC, 0xD8, 0xD4, 0xE4, 0xE0,
        0xEC, 0xE8, 0xF4, 0xF0, 0xFC, 0xF8, 0x104, 0x100,
        0x110, 0x10C, 0x118, 0x114, 0x120, 0x11C, 0x128, 0x124)),
    (0x234, (0x234, 0x240, 0x238, 0x23C, 0x244, 0x248, 0x24C, 0x250, 0x258, 0x254)),
    (0x26C, (0x274, 0x278, 0x284, 0x294, 0x26C, 0x270, 0x288, 0x27C, 0x280, 0x28C, 0x290)),
    (0x2B8, (0x2BC, 0x2C0, 0x2B8)),
)
GPR_EDITS = {
    0x234: ((11, 5, 24),),
    0x238: ((11, 5, 25),),
    0x23C: ((16, 25, 24),),
    0x240: ((16, 24, 5), (21, 5, 25)),
    0x244: ((16, 24, 25),),
    0x248: ((16, 24, 25), (21, 24, 25)),
    0x24C: ((11, 15, 14), (16, 25, 24)),
    0x250: ((21, 15, 14), (16, 24, 25)),
    0x254: ((16, 25, 15),),
    0x258: ((16, 14, 24),),
    0x268: ((21, 14, 15), (16, 25, 24)),
}


def schedule(words):
    result = list(words)
    for begin, sources in PERMUTATIONS:
        if sorted(sources) != list(range(begin, begin + len(sources) * 4, 4)):
            raise ValueError('scheduling window must be a complete instruction permutation')
        for index, source in enumerate(sources):
            result[begin // 4 + index] = words[source // 4]
    for offset, edits in GPR_EDITS.items():
        reads, writes = registers.fields(result[offset // 4])
        for shift, expected, replacement in edits:
            if shift not in reads + writes or result[offset // 4] >> shift & 31 != expected:
                raise ValueError('stale setup operand recipe at0x%X' % offset)
            result[offset // 4] = (result[offset // 4] & ~(31 << shift)) | (replacement << shift)
    return result


def normalize(words):
    return schedule(registers.normalize(words))


def add(a, b):
    if isinstance(a, int) and isinstance(b, int):
        return (a + b) & 0xFFFFFFFF
    if a == 0:
        return b
    if b == 0:
        return a
    if isinstance(b, int) and isinstance(a, tuple) and a[0] == 'add-constant':
        return add(a[1], (a[2] + b) & 0xFFFFFFFF)
    if isinstance(a, int):
        return add(b, a)
    if isinstance(b, int):
        return ('add-constant', a, b)
    return ('add', *sorted((a, b), key=repr))


def bit_or(a, b):
    values = []
    for value in (a, b):
        values.extend(value[1:] if isinstance(value, tuple) and value[0] == 'or' else (value,))
    constant = 0
    for value in values:
        if isinstance(value, int):
            constant |= value
    values = [value for value in values if not isinstance(value, int)]
    if constant:
        values.append(constant)
    unique = sorted(set(values), key=repr)
    return 0 if not unique else unique[0] if len(unique) == 1 else ('or', *unique)


def private_offset(address):
    if address == ('private-SP',):
        return 0
    if isinstance(address, tuple) and address[0] == 'add-constant' and address[1] == ('private-SP',):
        return address[2]
    return None


def execute_window(words, begin, end, stores, call=False):
    """Symbolically execute only the closed setup operations actually present.

    Incoming nonprivate objects and this invocation's private frame are disjoint.
    No public writes or intervening callbacks are permitted. Reads are ordinary
    nonvolatile loads; their multiset and private final bytes must agree.
    """
    gp = [0] + [('incoming-GPR', i) for i in range(1, 32)]
    gp[29] = ('private-SP',)
    fp = [('incoming-FP', i) for i in range(32)]
    memory, reads, public_writes, calls = {}, [], [], []

    def load(address, size):
        reads.append((address, size))
        offset = private_offset(address)
        if offset is not None and any(offset + i in memory for i in range(size)):
            chunks = [memory.get(offset + i) for i in range(size)]
            if any(chunk is None for chunk in chunks):
                raise ValueError('partially initialized overlapping private read')
            value = chunks[0][0]
            if chunks != [(value, size, i) for i in range(size)]:
                raise ValueError('unproved mixed private read')
            return value
        return ('load', size, address)

    for pc in range(begin, end, 4):
        word = words[pc // 4]
        op, rs, rt, rd, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word & 63
        imm = word & 65535
        signed = imm if imm < 32768 else imm - 65536
        if word == 0:
            continue
        if op == 0 and fn in (0, 33, 37):
            if fn == 0:
                amount = word >> 6 & 31
                value = (gp[rt] << amount) & 0xFFFFFFFF if isinstance(gp[rt], int) else ('shift-left', gp[rt], amount)
            else:
                value = add(gp[rs], gp[rt]) if fn == 33 else bit_or(gp[rs], gp[rt])
            if rd:
                gp[rd] = value
        elif op in (9, 13, 15):
            value = add(gp[rs], signed & 0xFFFFFFFF) if op == 9 else (
                bit_or(gp[rs], imm) if op == 13 else imm << 16)
            if rt:
                gp[rt] = value
        elif op in (35, 36, 49):
            value = load(add(gp[rs], signed & 0xFFFFFFFF), 1 if op == 36 else 4)
            if op == 49:
                fp[rt] = value
            elif rt:
                gp[rt] = value
        elif op in (40, 43):
            address, size = add(gp[rs], signed & 0xFFFFFFFF), 1 if op == 40 else 4
            offset = private_offset(address)
            if offset is None or any(offset + i not in stores for i in range(size)):
                raise ValueError('public or unauthorized private write at0x%X' % pc)
            for index in range(size):
                memory[offset + index] = (gp[rt], size, index)
        elif op == 17 and rs == 4:
            fp[rd] = gp[rt]
        elif op == 3 and call and pc == end - 8:
            gp[31] = ('return-PC', pc + 8)
            calls.append(word)
        else:
            raise ValueError('unexpected closed-window operation at0x%X' % pc)
    live = (4, 5, 6, 7, *range(16, 24), 29, 30, 31) if call else tuple(range(32))
    return tuple(gp[i] for i in live), tuple(fp), memory, Counter(reads), public_writes, calls


def certify(words):
    allocation = registers.certify_gpr(words)
    raw, fitted = registers.normalize(words), normalize(words)
    windows = ((0xCC, 0x12C, set(range(0x10, 0x38)) | {0xEF}, False),
               (0x234, 0x26C, set(), True),
               (0x26C, 0x2B4, set(range(0x128, 0x140)), False),
               (0x2B8, 0x2C4, set(), False))
    receipts = []
    for begin, end, stores, call in windows:
        a = execute_window(raw, begin, end, stores, call)
        b = execute_window(fitted, begin, end, stores, call)
        if a != b:
            raise ValueError('closed-window state/read/ABI mismatch at0x%X' % begin)
        receipts.append(dict(begin=begin, end=end, words=(end - begin) // 4,
            private_final_bytes=len(a[2]), reads=sum(a[3].values()), helper_boundary=call,
            live_GPR_FP_and_memory_equal=True, read_multiset_equal=True, no_public_writes=True))
    offsets = [i * 4 for i, (a, b) in enumerate(zip(words, fitted)) if a != b]
    return dict(allocation=allocation, scheduling_windows=receipts, changed_words=len(offsets),
        offsets=offsets, private_frame_disjoint_from_incoming_objects=True,
        ordinary_nonvolatile_read_reordering_only=True, no_literal_retail_lookup=True)


def guard_rows(obj):
    text, functions, relocations = parse_object(obj)
    function = functions[base.FUNCTION]
    words = list(struct.unpack_from('>475I', text, function['value']))
    proof, fitted = certify(words), normalize(words)
    rows = []
    for offset in proof['offsets']:
        uses = relocations.get(function['value'] + offset, [])
        spec = ';'.join(kind + ':' + name for kind, name in uses) or '-'
        rows.append(dict(filename='generated_1E0560', function=base.FUNCTION, offset='0x%X' % offset,
            expected='0x%08X' % words[offset // 4], replacement='0x%08X' % fitted[offset // 4],
            expected_relocations=spec, replacement_relocations=spec,
            note='Normalize certified owner ribbon closed allocation and setup scheduling',
            insert_after='', insert_after_relocations='', omit='false'))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--form')
    parser.add_argument('--certificate', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-ribbon-renderer-scheduling'
    forms = dict(candidates())
    if args.form:
        forms = {args.form: forms[args.form]}
    rows = []
    for name, body in forms.items():
        meta, words = base.compile_candidate(root, out, name, body)
        try:
            fitted = registers.normalize(words)
            retail = struct.unpack_from('>475I', (root / 'conker/conker.us.bin').read_bytes(), base.ROM)
            meta['allocation_normalized_differences'] = sum(a != b for a, b in zip(fitted, retail))
        except ValueError as error:
            meta['allocation_recipe_rejected'] = str(error)
        rows.append(meta)
        if args.certificate:
            meta['certificate'] = certify(words)
            meta['complete_normalized_differences'] = sum(a != b for a, b in zip(normalize(words), retail))
            guards = guard_rows(out / (name + '.o'))
            stream = io.StringIO()
            csv.DictWriter(stream, fieldnames=list(guards[0]), lineterminator='\n').writerows(guards)
            (out / 'guards.csv').write_text(stream.getvalue())
            print('complete_normalized_differences', meta['complete_normalized_differences'], flush=True)
        print(name, meta['body_words'], meta['frame'], meta['differences'],
            meta.get('allocation_normalized_differences', meta.get('allocation_recipe_rejected')), flush=True)
    (out / ((args.form or 'all') + '.json')).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
