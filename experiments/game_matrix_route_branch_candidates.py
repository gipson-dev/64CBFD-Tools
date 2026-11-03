"""Fit the matrix carrier, key branch and resolver primary read lifetime."""

import argparse
import itertools
import json
from pathlib import Path

from tools.experiments import game_matrix_route_candidates as route
from tools.experiments import game_matrix_route_layout_candidates as layout


def matrix_carrier(body, kind):
    if kind == 'local':
        return body
    body = body.replace('    Mtx *matrix;\n', '    u8 *bank;\n')
    body = body.replace('(matrix = (Mtx *)actor->unk1D4)', '(bank = (u8 *)actor->unk1D4)')
    body = body.replace('(u8 *)matrix + descriptor[2] * 64', 'bank + descriptor[2] * 64')
    for expression in ('((Mtx **)(attachment + 0x3E8))[D_800BE9C0] + index',
            'lookupMatrix + *(u16 *)(descriptor + 0x20)', 'lookupMatrix',
            '*(Mtx **)(descriptor + 0x34) + D_800BE9C0'):
        body = body.replace('matrix = ' + expression + ';',
            kind + ' = (' + ('u8 *' if kind == 'descriptor' else 's32') + ')(' + expression + ');')
    body = body.replace('matrix += *(u16 *)(descriptor + 0x20);',
        kind + ' = (' + ('u8 *' if kind == 'descriptor' else 's32') + ')((Mtx *)' + kind + ' + *(u16 *)(descriptor + 0x20));')
    body = body.replace('if (matrix != 0)', 'if (' + kind + ' != 0)')
    body = body.replace('guMtxL2F(converted, matrix)', 'guMtxL2F(converted, (Mtx *)' + kind + ')')
    if kind == 'descriptor':
        body = body.replace('    s32 i;', '    s32 i;\n    u8 *sourceDescriptor;')
        body = body.replace('    if (actor == 0', '    sourceDescriptor = descriptor;\n    if (actor == 0', 1)
        body = body.replace('descriptor + 0x', 'sourceDescriptor + 0x')
        body = body.replace('descriptor[2]', 'sourceDescriptor[2]')
    return body


def key_carrier(body, kind):
    if kind == 'repeat':
        return body
    descriptor = 'sourceDescriptor' if '    u8 *sourceDescriptor;' in body else 'descriptor'
    if kind == 'index':
        body = body.replace('} else if (*(u16 *)(%s + 0x1E) != 0)' % descriptor,
            '} else if ((index = *(u16 *)(%s + 0x1E)) != 0)' % descriptor)
        return body.replace('actor, *(u16 *)(%s + 0x1E), 0)' % descriptor, 'actor, index, 0)')
    body = body.replace('    u8 *attachment;', '    u32 routeValue;')
    body = body.replace('attachment = *(u8 **)(%s + 0x48);' % descriptor,
        'routeValue = *(u32 *)(%s + 0x48);' % descriptor)
    body = body.replace('if (attachment != 0)', 'if (routeValue != 0)')
    body = body.replace('attachment[0x3F6]', '((u8 *)routeValue)[0x3F6]')
    body = body.replace('attachment + 0x3E8', '(u8 *)routeValue + 0x3E8')
    body = body.replace('} else if (*(u16 *)(%s + 0x1E) != 0)' % descriptor,
        '} else if ((routeValue = *(u16 *)(%s + 0x1E)) != 0)' % descriptor)
    return body.replace('actor, *(u16 *)(%s + 0x1E), 0)' % descriptor, 'actor, routeValue, 0)')


def candidates():
    for carrier, primary, key in itertools.product(('local', 'descriptor', 'index'), range(3),
            ('repeat', 'index', 'route')):
        body = layout.lookup_shape(layout.SELECTED, primary)
        body = matrix_carrier(body, carrier)
        body = key_carrier(body, key)
        yield 'carrier-%s-primary%d-key%s' % (carrier, primary, key), body


def phase_candidates():
    base = layout.SELECTED.replace('    struct17 **outputs;', '    u8 *bank;')
    base = base.replace('(matrix = (Mtx *)actor->unk1D4)', '(bank = (u8 *)actor->unk1D4)')
    base = base.replace('(u8 *)matrix + descriptor[2] * 64', 'bank + descriptor[2] * 64')
    base = base.replace('outputs = outputArgument;', 'actor = (struct127 *)outputArgument;')
    base = base.replace('(*outputs)->', '(*(struct17 **)actor)->')
    base = base.replace('outputs++;', 'actor = (struct127 *)((u8 *)actor + 4);')
    for primary, key, order in itertools.product(range(3), ('repeat', 'index', 'route'), range(2)):
        body = layout.lookup_shape(base, primary)
        body = key_carrier(body, key)
        if order:
            body = body.replace('    u8 *bank;\n', '').replace('    Mtx *matrix;', '    u8 *bank;\n    Mtx *matrix;')
        yield 'phase-primary%d-key%s-order%d' % (primary, key, order), body


def key_candidates():
    base = dict(phase_candidates())['phase-primary0-keyrepeat-order0']
    for kind in ('u32', 's32', 'u16', 'input', 'matrix', 'attachment'):
        body = base
        if kind in ('u32', 's32', 'u16'):
            body = body.replace('    u8 *attachment;', '    %s key;' % kind)
            body = body.replace('    attachment = *(u8 **)(descriptor + 0x48);\n', '')
            body = body.replace('if (attachment != 0)', 'if (*(u8 **)(descriptor + 0x48) != 0)')
            body = body.replace('attachment[0x3F6]', '(*(u8 **)(descriptor + 0x48))[0x3F6]')
            body = body.replace('attachment + 0x3E8', '*(u8 **)(descriptor + 0x48) + 0x3E8')
            expression, argument = 'key = *(u16 *)(descriptor + 0x1E)', 'key'
        else:
            cast = dict(input='struct17 **', matrix='Mtx *', attachment='u8 *')[kind]
            expression, argument = '%s = (%s)(u32)*(u16 *)(descriptor + 0x1E)' % (kind, cast), '(u32)' + kind
        body = body.replace('} else if (*(u16 *)(descriptor + 0x1E) != 0)',
            '} else if ((%s) != 0)' % expression)
        body = body.replace('actor, *(u16 *)(descriptor + 0x1E), 0)', 'actor, %s, 0)' % argument)
        yield 'key-binding-' + kind, body
    for kind, copy in itertools.product(('pointer', 'bytes', 'address'), (False, True)):
        body = base
        marker = '        if (*(u8 **)((u8 *)input + 0x48) != 0)'
        body = body.replace(marker, '        matrix = lookupMatrix;\n' + marker, 1)
        if not copy:
            body = body.replace('        } else {\n            matrix = lookupMatrix;\n        }', '        }')
        expression = 'lookupMatrix + *(u16 *)(descriptor + 0x20)'
        if kind == 'bytes':
            body = body.replace(expression, '(Mtx *)((u8 *)lookupMatrix + (*(u16 *)(descriptor + 0x20) << 6))')
        elif kind == 'address':
            body = body.replace(expression, '(Mtx *)((u32)lookupMatrix + (*(u16 *)(descriptor + 0x20) << 6))')
        yield 'primary-prefix-%s-copy%d' % (kind, copy), body
    for primary, kind in itertools.product(range(3), ('bytes', 'address')):
        body = layout.lookup_shape(base, primary)
        ctype = 'u8 *' if kind == 'bytes' else 'u32 '
        body = body.replace('Mtx *lookupMatrix;', ctype + 'lookupMatrix;').replace('Mtx *other;', ctype + 'other;')
        body = body.replace('&lookupMatrix, &other)', '(Mtx **)&lookupMatrix, (Mtx **)&other)')
        body = body.replace('lookupMatrix + *(u16 *)(descriptor + 0x20)',
            '(Mtx *)(lookupMatrix + (*(u16 *)(descriptor + 0x20) << 6))')
        body = body.replace('matrix = lookupMatrix;', 'matrix = (Mtx *)lookupMatrix;')
        body = body.replace('matrix += *(u16 *)(descriptor + 0x20);',
            'matrix = (Mtx *)((u8 *)matrix + (*(u16 *)(descriptor + 0x20) << 6));')
        yield 'primary-output%d-%s' % (primary, kind), body


def explicit_key_gate(body, topology, carrier):
    """Expose the retail zero-key gate without an assignment condition."""
    carrier_forms = {
        'local': ('key', 'key = *(u16 *)(descriptor + 0x1E)', 'key'),
        'register16': ('key', 'key = *(u16 *)(descriptor + 0x1E)', 'key'),
        'register32': ('key', 'key = *(u16 *)(descriptor + 0x1E)', 'key'),
        'index': ('index', 'index = *(u16 *)(descriptor + 0x1E)', 'index'),
        'input': ('input', 'input = (struct17 **)(u32)*(u16 *)(descriptor + 0x1E)',
                  '(u32)input'),
        'matrix': ('matrix', 'matrix = (Mtx *)(u32)*(u16 *)(descriptor + 0x1E)',
                   '(u32)matrix'),
        'attachment': ('attachment',
                       'attachment = (u8 *)(u32)*(u16 *)(descriptor + 0x1E)',
                       '(u32)attachment'),
    }
    condition, assignment, argument = carrier_forms[carrier]
    declarations = {
        'local': '    u16 key;\n',
        'register16': '    register u16 key;\n',
        'register32': '    register u32 key;\n',
    }
    if carrier in declarations:
        body = body.replace('    Mtx *other;\n',
            '    Mtx *other;\n' + declarations[carrier], 1)
    keyed_marker = '    } else if (*(u16 *)(descriptor + 0x1E) != 0) {\n'
    descriptor_marker = '    } else if (*(Mtx **)(descriptor + 0x34) != 0) {\n'
    common_marker = '    }\n    if (matrix != 0)'
    start = body.index(keyed_marker)
    middle = body.index(descriptor_marker, start)
    end = body.index(common_marker, middle)
    keyed = body[start + len(keyed_marker):middle]
    keyed = keyed.replace('actor, *(u16 *)(descriptor + 0x1E), 0)',
        'actor, %s, 0)' % argument, 1)
    descriptor = body[middle + len(descriptor_marker):end]
    descriptor = ('        if (*(Mtx **)(descriptor + 0x34) != 0) {\n' +
        ''.join('    ' + line if line.strip() else line
                for line in descriptor.splitlines(keepends=True)) +
        '        }\n')
    if topology == 'nested':
        new = (f'''    }} else {{
        {assignment};
        if ({condition} != 0) {{
''' + ''.join('    ' + line if line.strip() else line
              for line in keyed.splitlines(keepends=True)) + '''        } else {
''' + ''.join('    ' + line if line.strip() else line
              for line in descriptor.splitlines(keepends=True)) + '''        }
    }
''')
    else:
        new = f'''    }} else {{
        {assignment};
        if ({condition} == 0) {{
            goto descriptor_bank;
        }}
''' + keyed + '''        goto selected_matrix;
descriptor_bank:
''' + descriptor + '''    }
selected_matrix:
'''
    return body[:start] + new + body[end + len('    }\n'):]


def primary_output_alias(body, kind):
    """Keep a real alias to the resolver primary output and reread it."""
    if kind in ('direct', 'volatile_cast'):
        primary = ('lookupMatrix' if kind == 'direct' else
            '*(Mtx *volatile *)&lookupMatrix')
        body = body.replace(
            '        if (*(u8 **)((u8 *)input + 0x48) != 0) {',
            '        matrix = %s;\n' % primary +
            '        if (*(u8 **)((u8 *)input + 0x48) != 0) {', 1)
        body = body.replace(
            '            matrix = lookupMatrix + *(u16 *)(descriptor + 0x20);',
            '            matrix = %s + *(u16 *)(descriptor + 0x20);' % primary, 1)
        return body.replace(
            '        } else {\n            matrix = lookupMatrix;\n        }',
            '        }', 1)
    qualifier = 'volatile ' if kind == 'volatile' else ''
    body = body.replace('    Mtx *other;\n',
        '    Mtx *other;\n    Mtx **%sprimaryOut;\n' % qualifier, 1)
    body = body.replace(
        '        if (func_15031070((struct126 *)input, actor, &lookupMatrix, &other) == 0) {',
        '        primaryOut = &lookupMatrix;\n'
        '        if (func_15031070((struct126 *)input, actor, primaryOut, &other) == 0) {', 1)
    body = body.replace(
        '        if (*(u8 **)((u8 *)input + 0x48) != 0) {\n'
        '            matrix = lookupMatrix + *(u16 *)(descriptor + 0x20);\n'
        '        } else {\n'
        '            matrix = lookupMatrix;\n'
        '        }',
        '        matrix = *primaryOut;\n'
        '        if (*(u8 **)((u8 *)input + 0x48) != 0) {\n'
        '            matrix = *primaryOut + *(u16 *)(descriptor + 0x20);\n'
        '        }', 1)
    return body


def evidence_candidates():
    """Untested source forms isolated by the post-377-form evidence audit."""
    base = dict(phase_candidates())['phase-primary0-keyrepeat-order0']
    for gate, carrier, primary, delegated in itertools.product(
            ('nested', 'goto'),
            ('register16', 'register32', 'index', 'input', 'matrix',
             'attachment', 'local'),
            ('direct', 'volatile_cast', 'pointer'), range(2)):
        body = primary_output_alias(base, primary)
        body = explicit_key_gate(body, gate, carrier)
        if delegated:
            body = body.replace('bank + descriptor[2] * 64',
                'descriptor[2] * 64 + bank')
        yield 'evidence-gate%s-carrier%s-primary%s-delegated%d' % (
            gate, carrier, primary, delegated), body


def storage_candidates():
    base = dict(phase_candidates())['phase-primary0-keyrepeat-order0']
    for primary, representation in itertools.product(range(3), ('array', 'struct', 'union')):
        body = layout.lookup_shape(base, primary)
        if representation == 'array':
            body = body.replace('    Mtx *lookupMatrix;\n    Mtx *other;', '    Mtx *resolved[2];')
            body = body.replace('lookupMatrix', 'resolved[1]').replace('&other', '&resolved[0]')
        elif representation == 'struct':
            body = body.replace('    Mtx *lookupMatrix;\n    Mtx *other;',
                '    struct { Mtx *secondary; Mtx *primary; } resolved;')
            body = body.replace('lookupMatrix', 'resolved.primary').replace('&other', '&resolved.secondary')
        else:
            body = body.replace('    Mtx *lookupMatrix;', '    union { Mtx *pointer; u32 address; } resolved;')
            body = body.replace('lookupMatrix', 'resolved.pointer')
            body = body.replace('resolved.pointer + *(u16 *)(descriptor + 0x20)',
                '(Mtx *)(resolved.address + (*(u16 *)(descriptor + 0x20) << 6))')
        yield 'storage-primary%d-%s' % (primary, representation), body
    for primary in range(2):
        body = layout.lookup_shape(base, 1)
        body = body.replace('Mtx *lookupMatrix;', 'Mtx *volatile lookupMatrix;')
        body = body.replace('&lookupMatrix, &other)', '(Mtx **)&lookupMatrix, &other)')
        if primary:
            body = body.replace('        }\n    } else if (*(Mtx **)(descriptor + 0x34)',
                '        } else {\n            goto selected_matrix;\n        }\n    } else if (*(Mtx **)(descriptor + 0x34)', 1)
            body = body.replace('    if (matrix != 0)', 'selected_matrix:\n    if (matrix != 0)', 1)
        yield 'storage-volatile-primary-goto%d' % primary, body


def flow_candidates():
    base = dict(phase_candidates())['phase-primary0-keyrepeat-order0']
    for key, primary, topology in itertools.product(('repeat', 'input', 'local'), range(3), ('chain', 'labels')):
        body = layout.lookup_shape(base, primary)
        if key == 'input':
            body = body.replace('} else if (*(u16 *)(descriptor + 0x1E) != 0)',
                '} else if ((input = (struct17 **)(u32)*(u16 *)(descriptor + 0x1E)) != 0)')
            body = body.replace('actor, *(u16 *)(descriptor + 0x1E), 0)', 'actor, (u32)input, 0)')
        elif key == 'local':
            body = body.replace('    u8 *attachment;', '    u8 *attachment;\n    u32 key;')
            body = body.replace('} else if (*(u16 *)(descriptor + 0x1E) != 0)',
                '} else if ((key = *(u16 *)(descriptor + 0x1E)) != 0)')
            body = body.replace('actor, *(u16 *)(descriptor + 0x1E), 0)', 'actor, key, 0)')
        if topology == 'labels':
            body = body.replace(' + index;\n    } else if (', ' + index;\n        goto selected_matrix;\n    }\n    if (', 1)
            body = body.replace('    } else if (*(Mtx **)(descriptor + 0x34)',
                '        goto selected_matrix;\n    }\n    if (*(Mtx **)(descriptor + 0x34)', 1)
            body = body.replace('    if (matrix != 0)', 'selected_matrix:\n    if (matrix != 0)', 1)
        if primary:
            body = body.replace('        matrix = lookupMatrix;\n', '        matrix = (Mtx *)(u32)lookupMatrix;\n', 1)
        yield 'flow-key%s-primary%d-%s' % (key, primary, topology), body


SELECTED = dict(phase_candidates())['phase-primary0-keyrepeat-order0']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    families = dict(phases=phase_candidates, keys=key_candidates,
        storage=storage_candidates, flow=flow_candidates,
        evidence=evidence_candidates)
    group = parser.add_mutually_exclusive_group()
    for name in families:
        group.add_argument('--' + name, action='store_true')
    args = parser.parse_args()
    family = next((name for name in families if getattr(args, name)), 'carriers')
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-matrix-route-branch'
    records = []
    for name, body in families.get(family, candidates)():
        record, words = route.compile_candidate(root, out, name, body)
        try:
            record.update(layout.private_offsets(words))
        except AssertionError:
            record.update(matrix_offset=None, primary_offset=None,
                secondary_offset=None)
        record['debug'] = layout.debug_locals(out / (name + '.o'))
        records.append(record)
        offsets = [hex(record[key]) if record[key] is not None else '-'
            for key in ('matrix_offset', 'primary_offset', 'secondary_offset')]
        print(name, record['body_words'], hex(record['frame']), record['differences'],
            offsets, flush=True)
    (out / (family + '.json')).write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
