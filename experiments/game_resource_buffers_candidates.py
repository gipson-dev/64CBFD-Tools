"""Recover the complete resource-buffer sharing, copying and failure cleanup."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x15084044, 0xB14F4, 194
FUNCTION, SOURCE = 'func_15084044', 'conker/src/game/generated_AEB40.c'
ORIGINAL = 's32 func_15084044() {\n    return 0;\n}'
RECORD = '''typedef struct {
    u8 *config;
    u8 padding[0x328];
} ResourceParent15084044;
'''
DECLARATIONS = '''extern ResourceParent15084044 D_800CC0E8[];
extern u8 *D_800D19A0[];
extern u8 D_800D1F80[];
extern u16 D_800C57A0[];
void *allocate_memory(s32, s32, s32, s32);
void func_10004074(void *);
'''
SYMBOLS = dict(D_800CC0E8=0x800CC0E8, D_800D19A0=0x800D19A0,
    D_800D1F80=0x800D1F80, D_800C57A0=0x800C57A0,
    allocate_memory=0x10003C40, bcopy=0x10023A10, func_10004074=0x10004074)
SELECTED = '''s32 func_15084044(u8 *actor, s32 channel) {
    u8 *config;
    s32 mode;
    s32 identity;
    u8 *pair;
    u8 **resource;
    u8 *first;
    u8 *references;
    s32 size;
    s32 failed;
    s32 offset;
    u8 *cursor;
    u8 *created;

    pair = actor + channel * 8;
    if (actor[0x65] != 0) {
        config = D_800CC0E8[actor[0x65]].config;
    } else {
        config = *(u8 **)(actor + 0x144);
    }
    identity = (*(u8 **)(actor + 0x2C4))[channel];
    mode = 0;
    if (config != NULL) {
        mode = config[0x10] & 3;
    }
    if (identity == 0) {
        mode = 2;
    }
    resource = &D_800D19A0[identity];
    first = *(u8 **)(pair + 0x28C);
    if ((first != NULL) && (*(u8 **)(pair + 0x290) != NULL)) {
        return 0;
    }
    config = *resource;
    if (config == NULL) {
        return 0;
    }
    failed = 0;
    if (mode == 0) {
        *(u8 **)(pair + 0x28C) = *(u8 **)(pair + 0x290) = config;
        D_800D1F80[identity] += 2;
    } else if (mode == 1) {
        if ((first == NULL) || (first == config)) {
            references = &D_800D1F80[identity];
            if (*references != 0) {
                size = D_800C57A0[identity] * 16;
                created = allocate_memory(size, 1, 2, 2);
                *(u8 **)(pair + 0x28C) = created;
                if (created == NULL) {
                    failed = 1;
                } else {
                    first = *(u8 **)(pair + 0x28C);
                    if (first != NULL) {
                        bcopy(*resource, first, size);
                    } else {
                        *(u8 **)(pair + 0x28C) = *resource;
                    }
                }
            } else {
                *(u8 **)(pair + 0x28C) = *(u8 **)(pair + 0x290) = config;
                *references += 2;
            }
            first = *(u8 **)(pair + 0x28C);
        }
        *(u8 **)(pair + 0x290) = first;
    } else if (mode == 2) {
        cursor = actor + channel * 8;
        for (offset = 0; offset != 8; offset += 4, cursor += 4) {
            if ((*(u8 **)(cursor + 0x28C) == NULL) ||
                (*(u8 **)(cursor + 0x28C) == *resource) ||
                ((offset == 4) && (*(u8 **)(pair + 0x28C) == *(u8 **)(pair + 0x290)))) {
                references = &D_800D1F80[identity];
                if (*references != 0) {
                    size = D_800C57A0[identity] * 16;
                    created = allocate_memory(size, 1, 2, 2);
                    *(u8 **)(cursor + 0x28C) = created;
                    if (created == NULL) {
                        failed = 1;
                        if (offset == 4) {
                            first = *(u8 **)(pair + 0x28C);
                            if (first != *resource) {
                                func_10004074(first);
                            } else {
                                *references -= 1;
                            }
                            *(u8 **)(pair + 0x28C) = NULL;
                        }
                        break;
                    } else {
                        created = *(u8 **)(cursor + 0x28C);
                        if (created != NULL) {
                            bcopy(*resource, created, size);
                        } else {
                            *(u8 **)(cursor + 0x28C) = *resource;
                        }
                    }
                } else {
                    *(u8 **)(cursor + 0x28C) = *resource;
                    *references += 1;
                }
            }
        }
    }
    return failed;
}'''


def compile_candidate(root, out, name, body=None, profile='o2g3'):
    body = QUALIFIED if body is None else body
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=RECORD, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def install(before, body=None):
    body = QUALIFIED if body is None else body
    if before.count(ORIGINAL) != 1:
        raise ValueError('stale resource buffers owner')
    return before.replace(ORIGINAL, RECORD + DECLARATIONS + '\n' + body)


def compact_candidates():
    forms = dict(candidates())
    for name in ('merged', 'inline-refs', 'inline-resource'):
        body = forms[name]
        if name != 'inline-refs':
            body = body.replace('    u8 *references;\n', '').replace(
                '            references = &D_800D1F80[identity];\n', '').replace(
                '                references = &D_800D1F80[identity];\n', '').replace('*references', 'D_800D1F80[identity]')
        else:
            body = body.replace('    u8 *created;\n', '').replace('created', 'config')
        for spelling, cursor in (('plain', 'actor + channel * 8'),
                ('shift', 'actor + (channel << 3)'),
                ('word', '(u8 *)((u32 *)actor + channel * 2)')):
            yield name + '-' + spelling, body.replace('cursor = actor + channel * 8;', 'cursor = ' + cursor + ';')


BASE = SELECTED


def candidates():
    shaped_base = BASE
    yield 'selected', shaped_base
    yield 'merged-created', SELECTED.replace('    u8 *created;\n', '').replace('created', 'config')
    yield 'separate-config', SELECTED.replace('    u8 *config;', '    u8 *config;\n    u8 *source;').replace(
        'config = *resource;', 'source = *resource;').replace('if (config == NULL)', 'if (source == NULL)').replace(
        '= config;', '= source;').replace('first == config', 'first == source')
    for name, statement in (
            ('if-else', '    if (config != NULL) {\n        mode = config[0x10] & 3;\n    } else {\n        mode = 0;\n    }'),
            ('ternary', '    mode = config != NULL ? config[0x10] & 3 : 0;')):
        yield name, SELECTED.replace('    mode = 0;\n', '').replace(
            '    if (config != NULL) {\n        mode = config[0x10] & 3;\n    }', statement)
    yield 'scalar-size', SELECTED.replace('    u8 *created;\n', '').replace('created', 'config').replace(
        's32 size;', 'u32 size;')
    shaped = SELECTED.replace('    mode = 0;\n', '').replace(
        '    if (config != NULL) {\n        mode = config[0x10] & 3;\n    }',
        '    if (config != NULL) {\n        mode = config[0x10] & 3;\n    } else {\n        mode = 0;\n    }')
    for name, body in (
            ('merged', shaped.replace('    u8 *created;\n', '').replace('created', 'config')),
            ('inline-refs', shaped.replace('    u8 *references;\n', '').replace(
                '            references = &D_800D1F80[identity];\n', '').replace(
                '                references = &D_800D1F80[identity];\n', '').replace('*references', 'D_800D1F80[identity]')),
            ('inline-resource', shaped.replace('    u8 **resource;\n', '').replace(
                '    resource = &D_800D19A0[identity];\n', '').replace('*resource', 'D_800D19A0[identity]'))):
        yield name, body
        yield name + '-cursor-integer', body.replace('cursor = actor + channel * 8;',
            'cursor = (u8 *)(channel * 8 + (u32)actor);')
    for expression in ('(u8 *)((u32)actor + channel * 8)',
            'actor + (channel << 3)', '(u8 *)((u32 *)actor + channel * 2)',
            'actor + (u32)channel * 8'):
        yield 'cursor-%d' % len(expression), shaped.replace('cursor = actor + channel * 8;',
            'cursor = ' + expression + ';')
    for field in ('first', 'config', 'created'):
        body = shaped.replace('    u8 *' + field + ';', '    s32 ' + field + ';')
        if field == 'first':
            body = body.replace('bcopy(*resource, first, size)', 'bcopy(*resource, (void *)first, size)').replace(
                'func_10004074(first)', 'func_10004074((void *)first)').replace('first != NULL', 'first != 0').replace(
                'first == NULL', 'first == 0').replace('first == config', 'first == (s32)config').replace(
                'first != *resource', 'first != (s32)*resource').replace('= first;', '= (u8 *)first;').replace(
                'first = *(u8 **)', 'first = *(s32 *)')
        elif field == 'created':
            body = body.replace('created = allocate_memory', 'created = (s32)allocate_memory').replace(
                '= created;', '= (u8 *)created;').replace('created == NULL', 'created == 0').replace(
                'created != NULL', 'created != 0').replace('bcopy(*resource, created, size)',
                'bcopy(*resource, (void *)created, size)').replace('created = *(u8 **)', 'created = *(s32 *)')
        else:
            continue
        yield 'integer-' + field, body


QUALIFIED = dict(compact_candidates())['inline-resource-plain'].replace(
    '    u8 *created;\n', '').replace('created', 'config').replace(
    '    s32 size;\n    s32 failed;', '    s32 failed;\n    s32 size;').replace(
    '                    if (D_800D1F80[identity]', '                if (D_800D1F80[identity]')


def lifetime_candidates():
    body = QUALIFIED.replace('    u8 *config;', '    u8 *config;\n    u8 *shared;').replace(
        '    s32 offset;\n', '').replace('offset', 'channel').replace(
        '    config = D_800D19A0[identity];', '    shared = D_800D19A0[identity];').replace(
        '    if (config == NULL)', '    if (shared == NULL)').replace('= config;', '= shared;').replace(
        'first == config', 'first == shared')
    yield 'shared-channel-loop', body
    for expression in ('actor + (channel << 3)', '(u8 *)((u32 *)actor + channel * 2)',
            '(u8 *)((u32)actor + channel * 8)'):
        yield 'shared-cursor-%d'%len(expression), body.replace('cursor = actor + channel * 8;',
            'cursor = '+expression+';')


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variants', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-resource-buffers'
    records = []
    forms = [('qualified', QUALIFIED)]
    if args.variants:
        forms += list(candidates()) + list(compact_candidates()) + list(lifetime_candidates())
    for name, body in forms:
        meta, _ = compile_candidate(root, out, name, body)
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__': main()
