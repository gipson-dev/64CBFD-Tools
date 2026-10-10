"""Measure the complete actor segment selector and callback-sensitive lookups."""
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1502F01C, 0x5C4CC, 146
FUNCTION = 'func_1502F01C'
SOURCE = 'conker/src/game/generated_58F80.c'
ORIGINAL = 's32 func_1502F01C() {\n    return 0;\n}'
TYPES = '''typedef struct { u32 address; u32 reserved[2]; } ActorSegmentRow58F80;
'''
DECLARATIONS = '''extern u8 D_800CC2D0[];
extern u8 *D_800D1C90[];
extern ActorSegmentRow58F80 *D_800C5338[];
u8 *func_1507E908(u8 *, s32);
'''
SYMBOLS = dict(D_800CC2D0=0x800CC2D0, D_800D1C90=0x800D1C90,
    D_800C5338=0x800C5338, func_1507E908=0x1507E908)
SELECTED = '''Gfx *func_1502F01C(Gfx *commands, s32 slot) {
    u8 *actor;
    u8 *cursor;
    u8 *pair;
    s32 index;
    u8 identity;
    s32 pairValues[2];
    u8 selected[2];
    ActorSegmentRow58F80 *rows;

    actor = (u8 *)D_800CC2D0 + (u32)slot * 0x32C;
    identity = actor[4];
    pair = NULL;
    cursor = actor;
    for (index = 0; index != 2; index++, cursor++) {
        if (cursor[0x6C] >= 10) {
            selected[index] = cursor[0x6C] - 10;
        } else {
            selected[index] = D_800D1C90[identity][index * 3 + cursor[0x6C] + 8];
            if (actor[0x6F] != 0 && pair == NULL) {
                pair = func_1507E908(actor, actor[0x6F]);
            }
            if (pair != NULL) {
                pairValues[0] = pair[0];
                pairValues[1] = pair[1];
                if (pair != NULL) {
                    if (pairValues[index] == D_800D1C90[identity][index * 3 + 10]) {
                        selected[index] = pairValues[index];
                    } else if (cursor[0x6C] == 0) {
                        selected[index] = pairValues[index];
                    }
                }
            }
        }
    }
    rows = D_800C5338[actor[4]];
    if (rows != NULL) {
        gSPSegment(commands++, 6, rows[selected[0]].address);
        gSPSegment(commands++, 7, rows[selected[1]].address);
        gSPSegment(commands++, 10, rows[actor[0x68]].address);
        gSPSegment(commands++, 11, rows[actor[0x69]].address);
    }
    return commands;
}'''


def candidates():
    yield 'selected', SELECTED
    shaped = SELECTED.replace('    s32 pairValues[2];\n    u8 selected[2];',
        '    u8 selected[2];\n    s32 pairValues[2];').replace(
        'index * 3 + 10', '((u32)index * 4 - index) + 10')
    yield 'split-index-expression', shaped
    yield 'split-index-signed', shaped.replace('((u32)index * 4 - index)', '(index * 4 - index)')
    yield 'split-index-shift', shaped.replace('((u32)index * 4 - index)', '((u32)index << 2) - index')
    yield 'table-slot-before-gate', shaped.replace('    ActorSegmentRow58F80 *rows;',
        '    ActorSegmentRow58F80 *rows;\n    u8 **table;').replace(
        '        if (cursor[0x6C] >= 10)', '        table = &D_800D1C90[identity];\n        if (cursor[0x6C] >= 10)').replace(
        'D_800D1C90[identity][', '(*table)[')
    for name, first, second in (
            ('shift-first', '((u32)index << 2) - index', 'index * 3'),
            ('shift-both', '((u32)index << 2) - index', '(u32)index * 4 - index'),
            ('sub-both', 'index * 4 - index', '((u32)index << 2) - index'),
            ('sum-first', 'index + index * 2', 'index * 3'),
            ('sum-both', 'index + index * 2', '(index * 2) + index')):
        yield name, shaped.replace('index * 3 + cursor[0x6C]', '('+first+') + cursor[0x6C]').replace(
            '((u32)index * 4 - index) + 10', '('+second+') + 10')
    for name, body in (('macro-temporary', SELECTED), ('macro-temporary-split', shaped)):
        body = body.replace('    ActorSegmentRow58F80 *rows;', '    ActorSegmentRow58F80 *rows;\n    Gfx *packet;')
        for segment, index in ((6,'selected[0]'), (7,'selected[1]'), (10,'actor[0x68]'), (11,'actor[0x69]')):
            body = body.replace('        gSPSegment(commands++, %d, rows[%s].address);'%(segment,index),
                '        packet = commands++;\n        gSPSegment(packet, %d, rows[%s].address);'%(segment,index))
        yield name, body
    yield 'typed-word-selection', shaped.replace('u8 selected[2];', 'u32 selected[2];')
    for size in (8, 12, 16, 20):
        yield 'selection-%d'%size, shaped.replace('u8 selected[2];', 'u8 selected[%d];'%size)
    yield 'index-first', SELECTED.replace('    u8 *actor;\n    u8 *cursor;\n    u8 *pair;\n    s32 index;',
        '    s32 index;\n    u8 *actor;\n    u8 *cursor;\n    u8 *pair;')
    yield 'locals-first', SELECTED.replace('    s32 pairValues[2];\n    u8 selected[2];',
        '    u8 selected[2];\n    s32 pairValues[2];')
    yield 'signed-identity', SELECTED.replace('u8 identity;', 's32 identity;')
    yield 'unsigned-index', SELECTED.replace('s32 index;', 'u32 index;')
    yield 'less-count', SELECTED.replace('index != 2', 'index < 2')
    yield 'explicit-mode', SELECTED.replace('    u8 identity;', '    u8 identity, mode;').replace(
        '        if (cursor[0x6C] >= 10)', '        mode = cursor[0x6C];\n        if (mode >= 10)').replace(
        'selected[index] = cursor[0x6C] - 10;', 'selected[index] = mode - 10;').replace(
        'index * 3 + cursor[0x6C] + 8', 'index * 3 + mode + 8')
    yield 'explicit-selector', SELECTED.replace('    u8 identity;', '    u8 identity, selector;').replace(
        '            selected[index] = D_', '            selector = actor[0x6F];\n            selected[index] = D_').replace(
        'if (actor[0x6F] != 0', 'if (selector != 0').replace('func_1507E908(actor, actor[0x6F])',
        'func_1507E908(actor, selector)')
    yield 'no-redundant-check', SELECTED.replace('                if (pair != NULL) {', '                {')
    yield 'explicit-writes', SELECTED.replace(
        '        gSPSegment(commands++, 6, rows[selected[0]].address);',
        '        commands->words.w0 = 0xDB060018;\n        commands->words.w1 = rows[selected[0]].address;\n        commands++;').replace(
        '        gSPSegment(commands++, 7, rows[selected[1]].address);',
        '        commands->words.w0 = 0xDB06001C;\n        commands->words.w1 = rows[selected[1]].address;\n        commands++;').replace(
        '        gSPSegment(commands++, 10, rows[actor[0x68]].address);',
        '        commands->words.w0 = 0xDB060028;\n        commands->words.w1 = rows[actor[0x68]].address;\n        commands++;').replace(
        '        gSPSegment(commands++, 11, rows[actor[0x69]].address);',
        '        commands->words.w0 = 0xDB06002C;\n        commands->words.w1 = rows[actor[0x69]].address;\n        commands++;')
    yield 'negative-cached-final-id', SELECTED.replace('D_800C5338[actor[4]]', 'D_800C5338[identity]')
    yield 'negative-reloaded-loop-id', SELECTED.replace('D_800D1C90[identity]', 'D_800D1C90[actor[4]]')
    yield 'negative-second-call', SELECTED.replace('pair == NULL', 'index == 0')
    yield 'negative-no-zero-override', SELECTED.replace('cursor[0x6C] == 0', '0')
    yield 'negative-first-pair-only', SELECTED.replace('pairValues[1] = pair[1];', 'pairValues[1] = pair[0];')
    yield 'negative-segment', SELECTED.replace('commands++, 11,', 'commands++, 12,')
    yield 'negative-one-iteration', SELECTED.replace('index != 2', 'index != 1').replace(
        '    rows = D_', '    selected[1] = 0;\n    rows = D_')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=TYPES, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        meta, words = compiler.compile_candidate(root, out, name, body, profile)
    frames = [(-word)&65535 for word in words if word>>16 == 0x27BD and word&0x8000]
    meta['frame'] = frames[0] if frames else 0
    return meta, words


def install(before, body=SELECTED):
    assert before.count(ORIGINAL) == 1
    declarations = TYPES + DECLARATIONS.replace('extern u8 D_800CC2D0[];\n', '')
    return before.replace('#include <ultra64.h>\n', '#include <ultra64.h>\n' + declarations, 1).replace(ORIGINAL, body)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-actor-segment-selector'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if name == 'selected' else ('o2g3',):
            meta, _ = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
