"""Recover the signed glyph-cell rectangle and typed string caller."""
import argparse
import csv
import io
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x15041508, 0x6E9B8, 54
FUNCTION, SOURCE = 'func_15041508', 'conker/src/game/generated_6E770.c'
PROTOTYPE = 's32 func_15041508(s32 arg0, u8 *arg1, s32 arg2, s32 arg3);'
TYPED_PROTOTYPE = 'Gfx *func_15041508(Gfx *, s32, s32, s32);'
ORIGINAL = '''s32 func_15041508(s32 arg0, u8 *arg1, s32 arg2, s32 arg3) {
    return 0;
}'''
CALLER_ENTRY, CALLER_ROM, CALLER_WORDS = 0x150413FC, 0x6E8AC, 33
CALLER_FUNCTION = 'func_150413FC'
CALLER_ORIGINAL = '''s32 func_150413FC(s32 arg0, u8 *arg1, s32 arg2, u8 *arg3) {
    s32 result;
    s32 value;
    u8 *commands;
    u8 *row;

    result = arg0;
    value = arg2;
    commands = arg3;
    row = arg1;

    while (*commands != 0) {
        result = func_15041508(result, row, value, func_15041480(*commands));
        commands++;
        row += 8;
    }
    return result;
}'''
CALLER_SELECTED = '''Gfx *func_150413FC(Gfx *displayList, s32 x, s32 y, u8 *text) {
    Gfx *result;
    s32 value;
    u8 *commands;
    u32 xCursor;

    result = displayList;
    value = y;
    commands = text;
    xCursor = x;

    while (*commands != 0) {
        result = func_15041508(result, xCursor, value, func_15041480(*commands));
        commands++;
        xCursor += 8;
    }
    return result;
}'''
PROFILES = dict(compiler.PROFILES, owner=('-O2','-g3','-Wo,-loopunroll,0'))
SYMBOLS = {}
CALLER_SYMBOLS = dict(func_15041480=0x15041480,func_15041508=ENTRY)
DECLARATIONS = 's32 func_15041480(u8);\n'+TYPED_PROTOTYPE+'\n'
BASE = '''Gfx *func_15041508(Gfx *displayList, s32 x, s32 y, s32 glyph) {
    gSPTextureRectangle(displayList++,
        (u32)x << 2, (u32)y << 2, ((u32)x + 8) << 2, ((u32)y + 12) << 2,
        G_TX_RENDERTILE, ((u32)(glyph % 8) * 8) << 5,
        ((u32)((glyph - (glyph % 8)) / 8) * 12) << 5, 0x400, 0x400);
    return displayList;
}'''
SELECTED = BASE

GUARD_ROWS = [('generated_6E770', FUNCTION, offset, expected, replacement, '-', '-',
    'Normalize glyph rectangle three-register allocation cycle', '', '', 'false')
    for offset, expected, replacement in (
        ('0x034','0x00801825','0x00804025'),
        ('0x044','0xAC6E0004','0xAD0E0004'),
        ('0x048','0xAC6F0000','0xAD0F0000'),
        ('0x050','0x00804025','0x00804825'),
        ('0x058','0xAD0F0000','0xAD2F0000'),
        ('0x064','0x30E90007','0x30E30007'),
        ('0x068','0x11200002','0x10600002'),
        ('0x070','0x2529FFF8','0x2463FFF8'),
        ('0x074','0x00E95823','0x00E35823'),
        ('0x078','0x0009C0C0','0x0003C0C0'),
        ('0x0AC','0xAD0D0004','0xAD2D0004'),
    )]


def guard_successor(data):
    rows = list(csv.DictReader(io.StringIO(data.decode('ascii'))))
    assert not any(row['function'] == FUNCTION for row in rows)
    assert data.endswith(b'\n')
    stream = io.StringIO(newline='')
    csv.writer(stream,lineterminator='\r\n' if data.endswith(b'\r\n') else '\n').writerows(GUARD_ROWS)
    return data+stream.getvalue().encode('ascii')


def candidates():
    yield 'selected', SELECTED
    yield 'legacy-signed-shifts', BASE.replace('(u32)x','x').replace('(u32)y','y').replace(
        '((u32)(glyph % 8) * 8)', '((glyph % 8) * 8)').replace(
        '((u32)((glyph - (glyph % 8)) / 8) * 12)', '(((glyph - (glyph % 8)) / 8) * 12)')
    yield 'scalar-s-multiply', BASE.replace('((u32)(glyph % 8) * 8) << 5','(u32)((glyph % 8) * 8) << 5')
    yield 'scalar-t-multiply', BASE.replace('((u32)((glyph - (glyph % 8)) / 8) * 12) << 5',
        '(u32)(((glyph - (glyph % 8)) / 8) * 12) << 5')
    yield 'direct-quotient', BASE.replace('(glyph - (glyph % 8)) / 8','glyph / 8')
    yield 'arg-names', BASE.replace('displayList','arg0').replace('s32 x','s32 arg1').replace(
        's32 y','s32 arg2').replace('s32 glyph','s32 arg3').replace('(u32)x','(u32)arg1').replace(
        '(u32)y','(u32)arg2').replace('glyph %','arg3 %').replace('glyph -','arg3 -')
    yield 'local-cursor', BASE.replace('    gSPTextureRectangle(displayList++,',
        '    Gfx *cursor = displayList;\n    gSPTextureRectangle(cursor++,').replace(
        '    return displayList;', '    return cursor;')
    yield 'register-arguments', BASE.replace('Gfx *displayList, s32 x, s32 y, s32 glyph',
        'register Gfx *displayList, register s32 x, register s32 y, register s32 glyph')
    yield 'unsigned-coordinates', BASE.replace('s32 x, s32 y','u32 x, u32 y')
    yield 'integer-return', BASE.replace('Gfx *func_15041508','s32 func_15041508').replace(
        '    return displayList;', '    return (s32)displayList;')


def compile_candidate(root,out,name,body=SELECTED,profile='owner',caller=False):
    declarations = DECLARATIONS if caller else ''
    if caller and body == CALLER_ORIGINAL:
        declarations = 's32 func_15041480(u8);\n'+PROTOTYPE+'\n'
    with patch.multiple(compiler,ENTRY=CALLER_ENTRY if caller else ENTRY,
            ROM=CALLER_ROM if caller else ROM,WORDS=CALLER_WORDS if caller else WORDS,
            FUNCTION=CALLER_FUNCTION if caller else FUNCTION,RECORD='',DECLARATIONS=declarations,
            SYMBOLS=CALLER_SYMBOLS if caller else SYMBOLS,PROFILES=PROFILES):
        meta,words = compiler.compile_candidate(root,out,name,body,profile)
    frames = [(-word)&65535 for word in words if word&0xFFFF0000 == 0x27BD0000 and word&0x8000]
    assert len(frames) <= 1
    meta['frame'] = frames[0] if frames else 0
    return meta,words


def install(source):
    for original in (PROTOTYPE,ORIGINAL,CALLER_ORIGINAL):
        assert source.count(original) == 1
    assert SELECTED not in source and CALLER_SELECTED not in source
    return source.replace(PROTOTYPE,TYPED_PROTOTYPE).replace(
        ORIGINAL,SELECTED).replace(CALLER_ORIGINAL,CALLER_SELECTED)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='selected')
    parser.add_argument('--profiles',action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-glyph-rectangle'
    records = []
    for name,body in candidates():
        if args.filter and args.filter not in name:
            continue
        for profile in (('owner','o2g3','o1g3','o1') if args.profiles else ('owner',)):
            meta,_ = compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    for name,body in (('caller-before',CALLER_ORIGINAL),('caller-after',CALLER_SELECTED)):
        meta,_ = compile_candidate(root,out,name,body,caller=True)
        records.append(meta)
        print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__ == '__main__':
    main()
