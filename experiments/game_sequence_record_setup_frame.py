"""Bounded source-lifetime screens for the complete, uninstalled record setup."""
import argparse
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_sequence_record_setup as source
from tools.tests import game_sequence_record_setup_oracle as model

BUILD = 'conker/build/game-sequence-record-setup-frame'
WITNESS_ENTRY = 0x16010000


def change(body, old, new, count=1):
    if body.count(old) != count:
        raise ValueError('Unknown setup source shape: ' + old)
    return body.replace(old, new)


def capacity_bytes(body):
    body = change(body, '    s32 bytes;\n', '')
    body = change(body, '    bytes = capacity * 2;', '    capacity *= 2;', 2)
    body = change(body, 'allocate_memory(bytes,', 'allocate_memory(capacity,', 2)
    for name in ('fallback', 'preferred'):
        body = change(body, 'bzero(*%s, bytes)' % name, 'bzero(*%s, capacity)' % name)
    return body


def scoped_allocation(body):
    return change(change(body, '    void *allocated;\n', ''),
        '            if (entries != 0) {',
        '            if (entries != 0) {\n                void *allocated;')


def registered(body, names):
    prefix, rest = body.split('    status = &D_800C35EA[slot];', 1)
    for name in names:
        lines = [line for line in prefix.splitlines() if line.endswith(name + ';')]
        if len(lines) != 1:
            raise ValueError('Unknown setup declaration: ' + name)
        prefix = change(prefix, lines[0], '    register ' + lines[0].strip())
    return prefix + '    status = &D_800C35EA[slot];' + rest


CELLS = (
    ('enabled', 'u16 **', 'D_800C35C8'),
    ('fallback', 'u16 **', 'D_800C35D0'),
    ('preferred', 'u16 **', 'D_800C35D8'),
    ('auxiliary', 'u8 ***', 'D_800C35E0'),
    ('runtime', 'SequenceRuntime49D30 **', 'D_800C3A50'),
)


def cell_expression(body, name, ctype, symbol):
    expression = '%s[slot]' % symbol
    body = change(body, '    %s%s;\n' % (ctype, name), '')
    body = change(body, '    %s = &%s;\n' % (name, expression), '')
    body = body.replace('(*%s)' % name, '(' + expression + ')')
    body = body.replace('*%s = ' % name, expression + ' = ')
    body = body.replace('*%s,' % name, expression + ',')
    return body


def all_cells(body):
    for cell in CELLS:
        body = cell_expression(body, *cell)
    return body


def inline_status(body):
    body = change(change(body, '    u8 *status;\n', ''),
        '    status = &D_800C35EA[slot];\n', '')
    return body.replace('*status', 'D_800C35EA[slot]')


def expression_forms():
    body = source.SELECTED
    for cell in CELLS:
        yield 'cell-' + cell[0], cell_expression(body, *cell)
    body = all_cells(body)
    yield 'all-cell-expressions', body
    yield 'all-cells-capacity-bytes', all_cells(capacity_bytes(source.SELECTED))
    yield 'all-cells-and-status', inline_status(body)


def block_change(body, start, end, transform):
    if body.count(start) != 1 or body.count(end) != 1:
        raise ValueError('Unknown setup block: ' + start)
    lo = body.index(start)
    hi = body.index(end, lo)
    return body[:lo] + transform(body[lo:hi]) + body[hi:]


def indexed_rows(body):
    for declaration in ('    u8 **pointers;\n',
            '    RecordMaximum49D30 **preferredPointers;\n'):
        body = change(body, declaration, '')
    body = change(body, '        pointers = &D_800C3960[slot][0];\n', '')
    body = change(body, '            *pointers = (void *)allocate_memory(0x10, 1, 0, 0);',
        '            D_800C3960[slot][i] = (void *)allocate_memory(0x10, 1, 0, 0);')
    body = change(body, '            pointers++;\n', '')
    def group(text, symbol, name, cast=''):
        text = change(text, '        %s = &%s[slot][0];\n' % (name, symbol), '')
        return change(text, '*%s++ = %sdescriptor->data' % (name, cast),
            '%s[slot][i] = %sdescriptor->data' % (symbol, cast))
    body = block_change(body, '    D_800C363A[slot] = header->activeCount;',
        '    D_800C35F0[slot]', lambda text: group(text, 'D_800C3868', 'pointers'))
    body = block_change(body, '    if (header->fallbackCount > 0) {',
        '    if (header->preferredCount > 0) {',
        lambda text: group(text, 'D_800C3778', 'pointers'))
    return block_change(body, '    if (header->preferredCount > 0) {',
        '    if (header->auxiliaryCount > 0) {',
        lambda text: group(text, 'D_800C3688', 'preferredPointers', '(RecordMaximum49D30 *)'))


def indexed_descriptors(body):
    body = change(body, '    SequenceDescriptor49D30 *descriptor;\n', '')
    def group(text, initializer, index):
        text = change(text, '        descriptor = bundle + %s;\n' % initializer, '')
        text = change(text, '            descriptor++;\n', '')
        return text.replace('descriptor->', 'bundle[%s].' % index)
    for start, end, initializer, index in (
            ('    cursor = 1;', '    capacity = header->fallbackCount;', '1', 'i + 1'),
            ('    D_800C363A[slot] = header->activeCount;', '    D_800C35F0[slot]', '1', 'i + 1'),
            ('    if (header->fallbackCount > 0) {', '    if (header->preferredCount > 0) {', 'cursor', 'cursor'),
            ('    if (header->preferredCount > 0) {', '    if (header->auxiliaryCount > 0) {', 'cursor', 'cursor'),
            ('    if (header->auxiliaryCount > 0) {', '    if (hook != 0)', 'cursor', 'cursor + i')):
        body = block_change(body, start, end,
            lambda text, initial=initializer, subscript=index: group(text, initial, subscript))
    return body


def inline_entries(body):
    body = change(body, '    u16 entries;\n', '')
    body = change(body, '            entries = (D_800C35C8[slot])[i];\n', '')
    body = change(body, 'if (entries != 0)', 'if ((D_800C35C8[slot])[i] != 0)')
    return change(body, 'allocate_memory(entries * 4,', 'allocate_memory((D_800C35C8[slot])[i] * 4,')


def indexed_forms():
    body = all_cells(source.SELECTED)
    yield 'indexed-rows', indexed_rows(body)
    yield 'indexed-descriptors', indexed_descriptors(body)
    body = indexed_descriptors(indexed_rows(body))
    yield 'indexed-rows-descriptors', body
    body = indexed_descriptors(indexed_rows(all_cells(capacity_bytes(source.SELECTED))))
    yield 'indexed-capacity', body
    body = inline_entries(body)
    yield 'indexed-capacity-entries', body
    body = inline_status(body)
    yield 'indexed-no-status', body
    yield 'indexed-word-state', change(body, '    u8 state;', '    s32 state;')


def indexed_body():
    return dict(indexed_forms())['indexed-word-state']


def canonical_loops(body):
    for field, count in (('activeCount',5),('fallbackCount',1),
            ('preferredCount',1),('auxiliaryCount',1)):
        body = change(body, '    if (header->%s > 0) {\n        do {\n' % field,
            '    for (i = 0; i < header->%s; i++) {\n' % field, count)
        body = change(body, '        } while (i < header->%s);\n        i = 0;\n    }' % field,
            '    }', count)
    body = change(body, '            i++;\n', '', 8)
    body = change(body, '    i = 0;\n', '')
    return change(body,
        '    if (D_800C363A[slot] > 0) {\n        do { func_15020388(i, slot); i++; } while (i < D_800C363A[slot]);\n    }',
        '    for (i = 0; i < D_800C363A[slot]; i++) {\n        func_15020388(i, slot);\n    }')


def loop_forms():
    body = canonical_loops(indexed_body())
    yield 'canonical-for-loops', body
    full_total = change(body, '    u16 total;', '    s32 total;')
    full_total = change(full_total, 'allocate_memory(total * 12,', 'allocate_memory((u16)total * 12,')
    yield 'canonical-word-total', full_total
    global_total = change(body, '    u16 total;\n', '')
    global_total = change(global_total, '    total = func_1501CFF8(slot);\n    D_800C3C9A = (s16)total;',
        '    D_800C3C9A = func_1501CFF8(slot);')
    global_total = change(global_total, 'allocate_memory(total * 12,', 'allocate_memory((u16)D_800C3C9A * 12,')
    yield 'canonical-global-total', global_total
    inline_state = change(body, '    s32 state;\n', '')
    inline_state = change(inline_state, '    state = D_800C35EA[slot];\n', '')
    inline_state = inline_state.replace('state == 1', 'D_800C35EA[slot] == 1').replace(
        'state != 2', 'D_800C35EA[slot] != 2')
    yield 'canonical-inline-state', inline_state
    reuse = change(body, '    void *allocated;\n', '')
    reuse = change(reuse, 'allocated = (void *)allocate_memory(', 'capacity = allocate_memory(', 2)
    reuse = change(reuse, ' = allocated;', ' = (void *)capacity;', 2)
    yield 'canonical-allocation-carrier', reuse


def global_total(body):
    body = change(body, '    u16 total;\n', '')
    body = change(body, '    total = func_1501CFF8(slot);\n    D_800C3C9A = (s16)total;',
        '    D_800C3C9A = func_1501CFF8(slot);')
    return change(body, 'allocate_memory(total * 12,', 'allocate_memory((u16)D_800C3C9A * 12,')


def allocation_carrier(body):
    body = change(body, '    void *allocated;\n', '')
    body = change(body, 'allocated = (void *)allocate_memory(', 'capacity = allocate_memory(', 2)
    return change(body, ' = allocated;', ' = (void *)capacity;', 2)


def cursor_descriptors(body):
    body = block_change(body, '    cursor = 1;', '    capacity = header->fallbackCount;',
        lambda text: change(text, 'bundle[i + 1]', 'bundle[cursor + i]'))
    return block_change(body, '    D_800C363A[slot] = header->activeCount;',
        '    D_800C35F0[slot]',
        lambda text: change(text, 'bundle[i + 1]', 'bundle[cursor]', 2))


def retail_forms():
    body = dict(loop_forms())['canonical-global-total']
    yield 'cursor-descriptors', cursor_descriptors(body)
    separate = inline_status(inline_entries(indexed_descriptors(indexed_rows(all_cells(source.SELECTED)))))
    separate = change(separate, '    u8 state;', '    s32 state;')
    separate = allocation_carrier(global_total(canonical_loops(separate)))
    yield 'separate-bytes', separate
    separate = cursor_descriptors(separate)
    yield 'separate-bytes-cursors', separate
    status = change(separate, '    s32 state;\n', '    u8 *status;\n')
    status = change(status, '    state = D_800C35EA[slot];\n', '')
    status = status.replace('D_800C35EA[slot]', '*status').replace(
        'state == 1', '*status == 1').replace('state != 2', '*status != 2')
    status = change(status, '\n    if (*status == 1',
        '\n    status = &D_800C35EA[slot];\n    if (*status == 1')
    yield 'status-pointer', status


def initialized_cursors(body, first=False, second=False, step=False):
    if first:
        body = block_change(body, '    cursor = 1;', '    capacity = header->fallbackCount;',
            lambda text: change(change(text, '    cursor = 1;\n', ''),
                'for (i = 0; i < header->activeCount; i++)',
                'for (i = 0, cursor = 1; i < header->activeCount; i++)'))
    if second:
        def rewrite(text):
            text = change(text, 'for (i = 0; i < header->activeCount; i++)',
                'for (i = 0, cursor = 1; i < header->activeCount; %s)' %
                ('i++, cursor++' if step else 'i++'))
            return change(text, '            cursor++;\n', '') if step else text
        body = block_change(body, '    D_800C363A[slot] = header->activeCount;',
            '    D_800C35F0[slot]', rewrite)
    return body


def cursor_forms():
    body = dict(retail_forms())['separate-bytes-cursors']
    yield 'first-for-init', initialized_cursors(body, first=True)
    yield 'second-for-init', initialized_cursors(body, second=True)
    yield 'both-for-inits', initialized_cursors(body, first=True, second=True)
    yield 'both-for-init-step', initialized_cursors(body, first=True, second=True, step=True)


def explicit_offsets(body):
    body = change(body, '    s32 i;', '    s32 i;\n    s32 offset;')
    for symbol in ('D_800C35C8', 'D_800C35D0', 'D_800C35D8'):
        body = body.replace('(%s[slot])[i]' % symbol,
            '*(u16 *)((u8 *)%s[slot] + offset)' % symbol)
    body = body.replace('(D_800C35E0[slot])[i]',
        '*(u8 **)((u8 *)D_800C35E0[slot] + offset)')
    parts = body.split('    for (')
    result = parts[0]
    changed = 0
    for part in parts[1:]:
        loop, rest = part.split('\n    }', 1)
        if '+ offset)' in loop:
            step = 4 if '*(u8 **)' in loop else 2
            loop = change(loop, 'i = 0;', 'i = 0, offset = 0;')
            loop = change(loop, '; i++) {', '; i++, offset += %d) {' % step)
            changed += 1
        result += '    for (' + loop + '\n    }' + rest
    if changed != 7:
        raise ValueError('Unknown setup offset loops')
    return result


def offset_forms():
    body = dict(retail_forms())['separate-bytes-cursors']
    yield 'explicit-byte-offsets', explicit_offsets(body)


def state_carrier(body, name):
    body = change(body, '    s32 state;\n', '')
    body = change(body, '    s32 %s;\n' % name, '')
    body = change(body, '    SequenceDescriptor49D30 *bundle;',
        '    s32 %s;\n    SequenceDescriptor49D30 *bundle;' % name)
    body = change(body, '    state = D_800C35EA[slot];',
        '    %s = D_800C35EA[slot];' % name)
    return body.replace('state == 1', name + ' == 1').replace('state != 2', name + ' != 2')


def flag_carrier(body, name, early, late):
    if early:
        body = change(body, '        if (D_800C35EA[slot] != 0) D_800C35C5 = 0;\n        else D_800C35C5 = 1;',
            '        %s = 1;\n        if (D_800C35EA[slot] != 0) D_800C35C5 = 0;\n        else D_800C35C5 = %s;' % (name, name))
    if late:
        body = change(body, '    D_800C35EA[slot] = 1;\n    D_800C3638 = 1;',
            '    %s = 1;\n    D_800C35EA[slot] = %s;\n    D_800C3638 = %s;' % (name, name, name))
    return body


def carrier_forms():
    initial = dict(retail_forms())['separate-bytes-cursors']
    for name in ('i', 'capacity'):
        body = state_carrier(initial, name)
        yield 'state-as-' + name, body
        yield name + '-early-flag', flag_carrier(body, name, True, False)
        yield name + '-both-flags', flag_carrier(body, name, True, True)


def prefill_expression(body, first, second):
    body = block_change(body, '    cursor = 1;', '    capacity = header->fallbackCount;',
        lambda text: change(text, 'bundle[cursor + i]', first))
    return block_change(body, '    D_800C363A[slot] = header->activeCount;',
        '    D_800C35F0[slot]', lambda text: change(text, 'bundle[cursor]', second, 2))


def address_forms():
    body = dict(carrier_forms())['capacity-both-flags']
    yield 'pointer-prefills', prefill_expression(body, '(bundle + cursor)[i]', '(bundle + 1)[i]')
    yield 'literal-prefills', prefill_expression(body, '(bundle + 1)[i]', '(bundle + 1)[i]')
    yield 'reordered-prefills', prefill_expression(body, 'bundle[i + cursor]', 'bundle[i + 1]')
    later = prefill_expression(body, 'bundle[i + 1]', '(bundle + 1)[i]')
    later = change(later, '    cursor = 1;\n', '')
    later = change(later, '    capacity = header->fallbackCount;',
        '    cursor = 1;\n    capacity = header->fallbackCount;')
    yield 'post-prefill-cursor', later


def descriptor_prefills(body, first='1', second='1'):
    body = change(body, '    s32 i;',
        '    SequenceDescriptor49D30 *descriptor;\n    s32 i;')
    def group(text, expression, initializer):
        text = change(text, 'for (i = 0; i < header->activeCount; i++)',
            'for (i = 0, descriptor = bundle + %s; i < header->activeCount; i++, descriptor++)' % initializer)
        return text.replace(expression + '.', 'descriptor->')
    body = block_change(body, '    cursor = 1;', '    capacity = header->fallbackCount;',
        lambda text: group(text, 'bundle[cursor + i]', first))
    return block_change(body, '    D_800C363A[slot] = header->activeCount;',
        '    D_800C35F0[slot]', lambda text: group(text, 'bundle[cursor]', second))


def descriptor_forms():
    body = dict(retail_forms())['cursor-descriptors']
    body = flag_carrier(state_carrier(allocation_carrier(body), 'capacity'), 'capacity', True, True)
    yield 'descriptor-literals', descriptor_prefills(body)
    yield 'descriptor-first-cursor', descriptor_prefills(body, first='cursor')
    yield 'descriptor-both-cursors', descriptor_prefills(body, first='cursor', second='cursor')
    body = dict(carrier_forms())['capacity-both-flags']
    yield 'descriptor-separate-bytes', descriptor_prefills(body)


def guarded_loop(body, first, second):
    def rewrite(text):
        text = change(text, '    for (i = 0; i < header->activeCount; i++) {\n',
            '    i = 0;\n    if (header->activeCount > 0) {\n        do {\n')
        return change(text, '\n    }\n',
            '\n            i++;\n        } while (i < header->activeCount);\n        i = 0;\n    }\n')
    if first:
        body = block_change(body, '    cursor = 1;', '    capacity = header->fallbackCount;', rewrite)
    if second:
        body = block_change(body, '    D_800C363A[slot] = header->activeCount;',
            '    D_800C35F0[slot]', rewrite)
    return body


def guarded_forms():
    body = dict(carrier_forms())['capacity-both-flags']
    yield 'first-guarded-loop', guarded_loop(body, True, False)
    yield 'second-guarded-loop', guarded_loop(body, False, True)
    yield 'both-guarded-loops', guarded_loop(body, True, True)


def independent_prefill(body, comma=False):
    def rewrite(text):
        text = change(text, 'bundle[cursor + i]', 'bundle[cursor]')
        text = change(text, 'for (i = 0; i < header->activeCount; i++)',
            'for (i = 0; i < header->activeCount; i++, cursor++)')
        if comma:
            text = change(text, '    cursor = 1;\n', '')
            text = change(text, 'for (i = 0;', 'for (i = 0, cursor = 1;')
        return text + '    cursor = 1;\n'
    return block_change(body, '    cursor = 1;', '    capacity = header->fallbackCount;', rewrite)


def independent_forms():
    body = dict(carrier_forms())['capacity-both-flags']
    yield 'independent-prefill-cursor', independent_prefill(body)
    yield 'independent-prefill-comma', independent_prefill(body, True)


def word_descriptor(body, union=False):
    def rewrite(text):
        text = change(text, 'for (i = 0; i < header->activeCount; i++)',
            'for (i = 0, capacity = (s32)(bundle + 1); i < header->activeCount; i++, capacity += 8)')
        return change(text, 'bundle[cursor].', '((SequenceDescriptor49D30 *)capacity)->', 2)
    body = block_change(body, '    D_800C363A[slot] = header->activeCount;',
        '    D_800C35F0[slot]', rewrite)
    if union:
        body = change(body, '    s32 capacity;',
            '    union { s32 number; SequenceDescriptor49D30 *descriptor; } capacity;')
        prefix, tail = body.split('\n\n    ', 1)
        tail = re.sub(r'\bcapacity\b', 'capacity.number', tail)
        tail = change(tail, 'capacity.number = (s32)(bundle + 1)',
            'capacity.descriptor = bundle + 1')
        tail = change(tail, 'capacity.number += 8', 'capacity.descriptor++')
        tail = change(tail, '((SequenceDescriptor49D30 *)capacity.number)->',
            'capacity.descriptor->', 2)
        body = prefix + '\n\n    ' + tail
    return body


def descriptor_carrier_forms():
    body = dict(independent_forms())['independent-prefill-cursor']
    yield 'word-descriptor-cursor', word_descriptor(body)
    yield 'union-descriptor-cursor', word_descriptor(body, True)


def declaration_forms():
    body = source.SELECTED
    yield 'state-word', change(body, '    u8 state;', '    s32 state;')
    yield 'entries-word', change(body, '    u16 entries;', '    s32 entries;')
    yield 'capacity-bytes', capacity_bytes(body)
    yield 'scoped-allocation', scoped_allocation(body)
    yield 'register-bundle', registered(body, ('bundle',))
    names = ('status', 'state', 'bundle', 'descriptor', 'header', 'enabled',
        'fallback', 'preferred', 'auxiliary', 'runtime', 'pointers',
        'preferredPointers', 'i', 'cursor', 'capacity', 'bytes', 'allocated',
        'total', 'entries')
    yield 'register-locals', registered(body, names)


def named_word(body):
    body = re.sub(r'\bcapacity\b', 'value', body)
    return change(body, '    value = D_800C35EA[slot];',
        '    /* Retail reuses this word for status, sizes, allocation results and flags. */\n'
        '    value = D_800C35EA[slot];')


FITTED = named_word(dict(carrier_forms())['capacity-both-flags'])
PREHEADER = named_word(dict(independent_forms())['independent-prefill-cursor'])
GROUPS = dict(declarations=declaration_forms, expressions=expression_forms,
    indexed=indexed_forms, loops=loop_forms, retail=retail_forms,
    cursors=cursor_forms, offsets=offset_forms, carriers=carrier_forms,
    addresses=address_forms, descriptors=descriptor_forms,
    guarded=guarded_forms, independent=independent_forms,
    descriptor_carriers=descriptor_carrier_forms)


def forms(group):
    if group == 'selected':
        yield 'fitted', FITTED
        yield 'preheader', PREHEADER
    elif group == 'all':
        for factory in GROUPS.values():
            yield from factory()
        yield from forms('selected')
    else:
        yield from GROUPS[group]()


def run(root, out, label, body):
    obj, words, row = source.measure(root, out, label, body)
    truth = struct.unpack_from('>473I', (out / 'before-retail_rom').read_bytes(), source.ROM)
    # Oversized screens must not shadow the real next-function provider address.
    if WITNESS_ENTRY >> 28 != source.ENTRY >> 28 or any(
            WITNESS_ENTRY <= target < WITNESS_ENTRY + len(words) * 4
            for target in model.ARITIES):
        raise ValueError('Unknown private witness placement')
    for fixture in (model.fixture(), model.fixture(mode=63)):
        reference = model.Reference(*fixture).run()
        actual = model.SetupOracle(words, *fixture, reference.allocations,
            entry=WITNESS_ENTRY).run()
        if (model.public(actual.memory), actual.calls, actual.provider.snapshots,
                actual.provider.fired) != (model.public(reference.memory),
                reference.calls, reference.snapshots, reference.fired):
            raise ValueError('Failed bounded setup witness: ' + label)
    row.update(save_words_match=words[1:11] == list(truth[1:11]),
        stack_offsets=sorted({w & 65535 for w in words
            if w >> 26 in (32,33,35,36,37,40,41,43) and w >> 21 & 31 == 29}),
        two_public_witnesses_only=True, witness_entry=WITNESS_ENTRY,
        no_installation_or_matching_credit=True)
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter', default='')
    parser.add_argument('--group', choices=('selected','all',*GROUPS), default='selected')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    for label, body in forms(args.group):
        if args.filter and args.filter not in label:
            continue
        row = run(root, root / BUILD, label, body)
        print(json.dumps({k: row[k] for k in ('label', 'words', 'frame',
            'differences', 'raw_sha256', 'save_words_match', 'stack_offsets')}), flush=True)
