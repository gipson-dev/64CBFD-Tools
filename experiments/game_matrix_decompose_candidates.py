"""Recover complete matrix translation, scale, handedness and angles."""
import argparse
import csv
import io
import json
import re
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1503E5F8, 0x6BAA8, 141
FUNCTION, SOURCE = 'func_1503E5F8', 'conker/src/game/generated_6B320.c'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_6B320/func_1503E5F8.s")'
LOCAL_DECLARATIONS = '''extern f32 D_80098918;
extern f32 D_8009891C;
f32 func_150AD930(f32 *);
void func_15049148(struct17 *, f32, struct17 *);
void func_150AD8B0(f32 *, f32 *, f32 *);
f32 func_150AD900(f32 *, f32 *);
f32 func_150487E0(f32);
f32 func_150AD780(f32);
f32 func_150484A0(f32, f32);
'''
DECLARATIONS = '#include "variables.h"\n'+LOCAL_DECLARATIONS
SYMBOLS = dict(D_80098918=0x80098918, D_8009891C=0x8009891C,
    bcopy=0x10023A10, func_150AD930=0x150AD930, func_15049148=0x15049148,
    func_150AD8B0=0x150AD8B0, func_150AD900=0x150AD900,
    func_150487E0=0x150487E0, func_150AD780=0x150AD780, func_150484A0=0x150484A0)
PROFILES = dict(compiler.PROFILES, owner=('-O2','-g3'),
    compact=('-O2','-g3','-Wo,-loopunroll,0'))
BASE = '''void func_1503E5F8(f32 input[4][4], f32 *x, f32 *y, f32 *z,
    f32 *rx, f32 *ry, f32 *rz, f32 *sx, f32 *sy, f32 *sz) {
    f32 matrix[4][4];
    f32 cross[3];
    f32 (*row)[4];
    f32 length;
    f32 fallback;
    f32 angleX;
    f32 angleY;
    f32 angleZ;

    bcopy(input, matrix, sizeof(matrix));
    *x = matrix[3][0];
    *y = matrix[3][1];
    *z = matrix[3][2];
    fallback = D_80098918;
    for (row = matrix; row < matrix + 3; row++) {
        length = func_150AD930(*row);
        if (length == 0.0f) {
            length = fallback;
        }
        if (row == matrix) {
            *sx = length;
        } else if (row == matrix + 1) {
            *sy = length;
        } else {
            *sz = length;
        }
        func_15049148((struct17 *)row, 1.0f / length, (struct17 *)row);
    }
    func_150AD8B0(matrix[1], matrix[2], cross);
    if (func_150AD900(matrix[0], cross) < 0.0f) {
        *sx = -*sx;
        *sy = -*sy;
        *sz = -*sz;
        for (row = matrix; row != matrix + 3; row++) {
            (*row)[0] = -(*row)[0];
            (*row)[1] = -(*row)[1];
            (*row)[2] = -(*row)[2];
        }
    }
    angleY = func_150487E0(-matrix[0][2]);
    if (func_150AD780(angleY) != 0.0f) {
        angleX = func_150484A0(matrix[1][2], matrix[2][2]);
        angleZ = func_150484A0(matrix[0][1], matrix[0][0]);
    } else {
        angleX = func_150484A0(matrix[1][0], matrix[1][1]);
        angleZ = 0.0f;
    }
    length = D_8009891C;
    *rx = angleX * length;
    *ry = angleY * length;
    *rz = angleZ * length;
}'''
SELECTED = BASE
MIDDLE = BASE.replace('    f32 (*row)[4];','    f32 (*row)[4];\n    f32 (*middle)[4];').replace(
    '    fallback = D_80098918;','    fallback = D_80098918;\n    middle = matrix + 1;').replace('row == matrix + 1','row == middle')
ANCHORED = MIDDLE.replace('    f32 (*middle)[4];','    f32 (*middle)[4];\n    f32 (*first)[4];\n    f32 (*end)[4];').replace(
    '    middle = matrix + 1;','    first = matrix;\n    end = matrix + 3;\n    middle = matrix + 1;').replace(
    'row = matrix; row < matrix + 3','row = first; row < end').replace('row == matrix)', 'row == first)')
FACTOR = MIDDLE.replace('    length = D_8009891C;','    { f32 factor = D_8009891C;').replace(
    'angleX * length','angleX * factor').replace('angleY * length','angleY * factor').replace('angleZ * length','angleZ * factor').replace(
    '    *rz = angleZ * factor;','    *rz = angleZ * factor;\n    }')
REUSED = FACTOR.replace('    f32 (*middle)[4];\n','').replace('    middle = matrix + 1;',
    '    x = matrix[0];\n    y = matrix[3];\n    z = matrix[1];').replace(
    'row = matrix; row < matrix + 3','row = matrix; (f32 *)row < y').replace('row == matrix)', '(f32 *)row == x)').replace(
    'row == middle)', '(f32 *)row == z)')
ENDED = FACTOR.replace('f32 cross[3]','f32 cross[4]').replace('    f32 (*middle)[4];',
    '    f32 (*end)[4];\n    f32 (*middle)[4];').replace('    middle = matrix + 1;',
    '    end = matrix + 3;\n    middle = matrix + 1;').replace('row < matrix + 3','row < end')
SELECTED = FACTOR.replace('f32 cross[3]','f32 cross[4]').replace('    f32 length;',
    '    f32 length;\n    f32 factor;').replace('    { f32 factor = D_8009891C;',
    '    factor = D_8009891C;').replace('    *rz = angleZ * factor;\n    }','    *rz = angleZ * factor;')


GUARD_ROWS = [('generated_6B320', FUNCTION, offset, expected, replacement, old, new,
    'Normalize complete matrix decomposer compiler allocation and scheduling', '', '', 'false')
    for offset, expected, replacement, old, new in (
    ("0x004", "0xAFB40040", "0xAFB3003C", "-", "-"),
    ("0x008", "0xAFB3003C", "0xAFB20038", "-", "-"),
    ("0x00C", "0xAFB20038", "0xAFB10034", "-", "-"),
    ("0x010", "0xAFB10034", "0x00A08825", "-", "-"),
    ("0x014", "0x27B10080", "0x00C09025", "-", "-"),
    ("0x018", "0x00A09025", "0x00E09825", "-", "-"),
    ("0x01C", "0x00C09825", "0xAFBF004C", "-", "-"),
    ("0x020", "0x00E0A025", "0xAFB60048", "-", "-"),
    ("0x024", "0xAFBF004C", "0xAFB50044", "-", "-"),
    ("0x028", "0xAFB60048", "0xAFB40040", "-", "-"),
    ("0x02C", "0xAFB50044", "0xAFB00030", "-", "-"),
    ("0x030", "0xAFB00030", "0xF7B80028", "-", "-"),
    ("0x034", "0xF7B80028", "0xF7B60020", "-", "-"),
    ("0x038", "0xF7B60020", "0xF7B40018", "-", "-"),
    ("0x03C", "0xF7B40018", "0x27A50080", "-", "-"),
    ("0x040", "0x02202825", "0x0C000000", "-", "R_MIPS_26:bcopy"),
    ("0x044", "0x0C000000", "0x24060040", "R_MIPS_26:bcopy", "-"),
    ("0x048", "0x24060040", "0xC7A400B0", "-", "-"),
    ("0x04C", "0xC7A400B0", "0x3C013F80", "-", "-"),
    ("0x050", "0x3C010000", "0x4481B000", "R_MIPS_HI16:D_80098918", "-"),
    ("0x054", "0x4480C000", "0xE6240000", "-", "-"),
    ("0x058", "0xE6440000", "0xC7A600B4", "-", "-"),
    ("0x05C", "0xC7A600B4", "0x3C010000", "-", "R_MIPS_HI16:D_80098918"),
    ("0x060", "0x27B20090", "0x4480C000", "-", "-"),
    ("0x064", "0x02208025", "0xE6460000", "-", "-"),
    ("0x068", "0xE6660000", "0xC7A800B8", "-", "-"),
    ("0x06C", "0xC7A800B8", "0x27B200B0", "-", "-"),
    ("0x070", "0x27B300B0", "0x27B10080", "-", "-"),
    ("0x074", "0xE6880000", "0xE6680000", "-", "-"),
    ("0x078", "0xC4340000", "0x8FB400DC", "R_MIPS_LO16:D_80098918", "-"),
    ("0x07C", "0x3C013F80", "0x8FB500E0", "-", "-"),
    ("0x080", "0x4481B000", "0x8FB600E4", "-", "-"),
    ("0x084", "0x8FB400DC", "0xC4340000", "-", "R_MIPS_LO16:D_80098918"),
    ("0x088", "0x8FB500E0", "0x27B30090", "-", "-"),
    ("0x08C", "0x8FB600E4", "0x27B00080", "-", "-"),
    ("0x0BC", "0x56120004", "0x56130004", "-", "-"),
    ("0x0E4", "0x0213082B", "0x0212082B", "-", "-"),
    ("0x0F8", "0x02402025", "0x27A40090", "-", "-"),
    ("0x104", "0x02202025", "0x27A40080", "-", "-"),
    ("0x124", "0x02208025", "0x27B00080", "-", "-"),
    ("0x128", "0x46008487", "0x27A200B0", "-", "-"),
    ("0x12C", "0xE6920000", "0x46008487", "-", "-"),
    ("0x130", "0xC6A40000", "0xE6920000", "-", "-"),
    ("0x134", "0x46002187", "0xC6A40000", "-", "-"),
    ("0x138", "0xE6A60000", "0x46002187", "-", "-"),
    ("0x13C", "0xC6C80000", "0xE6A60000", "-", "-"),
    ("0x140", "0x46004287", "0xC6C80000", "-", "-"),
    ("0x144", "0xE6CA0000", "0x46004287", "-", "-"),
    ("0x148", "0xC6100000", "0xE6CA0000", "-", "-"),
    ("0x14C", "0xC6040004", "0xC6100000", "-", "-"),
    ("0x150", "0xC6080008", "0xC6040004", "-", "-"),
    ("0x154", "0x46008487", "0xC6080008", "-", "-"),
    ("0x158", "0x46002187", "0x46008487", "-", "-"),
    ("0x15C", "0x46004287", "0x46002187", "-", "-"),
    ("0x160", "0x26100010", "0x46004287", "-", "-"),
    ("0x164", "0x262E0030", "0x26100010", "-", "-"),
    ("0x170", "0x160EFFF5", "0x1602FFF6", "-", "-"),
    ("0x1DC", "0x8FAF00D0", "0x8FAE00D0", "-", "-"),
    ("0x1E4", "0xE5F00000", "0xE5D00000", "-", "-"),
    ("0x1EC", "0x8FB800D4", "0x8FAF00D4", "-", "-"),
    ("0x1F4", "0xE7120000", "0xE5F20000", "-", "-"),
    ("0x1F8", "0x8FB900D8", "0x8FB800D8", "-", "-"),
    ("0x1FC", "0xE7240000", "0xE7040000", "-", "-"),
)]


def guard_successor(data):
    rows = list(csv.DictReader(io.StringIO(data.decode('ascii'))))
    assert not any(row['function'] == FUNCTION for row in rows)
    assert data.endswith(b'\n')
    out = io.StringIO(newline='')
    csv.writer(out, lineterminator='\r\n' if data.endswith(b'\r\n') else '\n').writerows(GUARD_ROWS)
    return data+out.getvalue().encode('ascii')


def flat(body):
    body = body.replace('f32 matrix[4][4];','f32 matrix[16];').replace('f32 (*row)[4];','f32 *row;').replace(
        'f32 (*middle)[4];','f32 *middle;').replace('f32 (*first)[4];','f32 *first;').replace('f32 (*end)[4];','f32 *end;')
    body = re.sub(r'matrix\[(\d)\]\[(\d)\]',lambda m:'matrix[%d]'%(int(m[1])*4+int(m[2])),body)
    body = body.replace('matrix + 3','matrix + 12').replace('matrix + 1','matrix + 4').replace(
        'row++','row += 4').replace('func_150AD930(*row)','func_150AD930(row)').replace('(*row)[','row[').replace(
        'func_150AD8B0(matrix[1], matrix[2],','func_150AD8B0(matrix + 4, matrix + 8,').replace(
        'func_150AD900(matrix[0], cross)','func_150AD900(matrix, cross)')
    return body


def candidates():
    yield 'selected', SELECTED
    yield 'middle', MIDDLE
    yield 'anchored', ANCHORED
    yield 'ended', ENDED
    yield 'ended-negative', ENDED.replace('row != matrix + 3','row != end')
    yield 'ended-scoped', ENDED.replace('    f32 (*end)[4];\n    f32 (*middle)[4];\n','').replace(
        '    end = matrix + 3;','    { f32 (*end)[4]; f32 (*middle)[4];\n    end = matrix + 3;').replace(
        '    func_150AD8B0(matrix[1], matrix[2], cross);','    }\n    func_150AD8B0(matrix[1], matrix[2], cross);')
    workspace = FACTOR.replace('    f32 matrix[4][4];\n    f32 cross[3];',
        '    struct { f32 cross[4]; f32 matrix[4][4]; } workspace;')
    yield 'workspace', re.sub(r'\b(matrix|cross)\b',lambda m:'workspace.'+m[0],workspace).replace(
        'struct { f32 workspace.cross[4]; f32 workspace.matrix[4][4]; }','struct { f32 cross[4]; f32 matrix[4][4]; }')
    rowstruct = FACTOR.replace('    f32 matrix[4][4];','    struct Row { f32 x, y, z, w; } matrix[4];').replace(
        'f32 (*row)[4];','struct Row *row;').replace('f32 (*middle)[4];','struct Row *middle;').replace(
        'func_150AD930(*row)','func_150AD930(&row->x)').replace('func_150AD8B0(matrix[1], matrix[2],',
        'func_150AD8B0(&matrix[1].x, &matrix[2].x,').replace('func_150AD900(matrix[0],','func_150AD900(&matrix[0].x,')
    rowstruct = re.sub(r'matrix\[(\d)\]\[(\d)\]',lambda m:'matrix[%s].%s'%(m[1],('x','y','z','w')[int(m[2])]),rowstruct)
    rowstruct = re.sub(r'\(\*row\)\[(\d)\]',lambda m:'row->'+('x','y','z','w')[int(m[1])],rowstruct)
    yield 'row-struct', rowstruct
    for name,body in (('middle',FACTOR.replace('f32 cross[3]','f32 cross[4]')),('ended',ENDED)):
        yield 'names-'+name+'-arg', re.sub(r'\b(input|x|y|z|rx|ry|rz|sx|sy|sz)\b',
            lambda m:'arg'+str(('input','x','y','z','rx','ry','rz','sx','sy','sz').index(m[0])),body)
    yield 'reused-anchors', REUSED
    yield 'reused-four-cross', REUSED.replace('f32 cross[3]','f32 cross[4]')
    yield 'reused-start-four', REUSED.replace('f32 cross[3]','f32 cross[4]').replace('row = matrix; (f32 *)row < y',
        'row = (f32 (*)[4])x; (f32 *)row < y')
    for name,body in (('middle',FACTOR),('reused',REUSED)):
        body = body.replace('f32 cross[3]','f32 cross[4]')
        yield 'shape-'+name+'-matrix-last', body.replace('    f32 matrix[4][4];\n','').replace('    f32 angleZ;',
            '    f32 angleZ;\n    f32 matrix[4][4];')
        yield 'shape-'+name+'-neg-limit', body.replace('    if (func_150AD900(matrix[0], cross) < 0.0f) {',
            '    if (func_150AD900(matrix[0], cross) < 0.0f) {\n        f32 (*limit)[4] = matrix + 3;').replace(
            'row != matrix + 3','row != limit')
        yield 'shape-'+name+'-member', body.replace('    f32 matrix[4][4];','    struct { f32 values[4][4]; } storage;').replace(
            'matrix','storage.values').replace('sizeof(storage.values)','sizeof(storage)').replace(
            'bcopy(input, storage.values,','bcopy(input, &storage,')
        if name == 'middle':
            yield 'shape-'+name+'-loop-scoped', body.replace('    f32 (*middle)[4];\n','').replace(
                '    middle = matrix + 1;','    { f32 (*middle)[4] = matrix + 1;').replace(
                '    func_150AD8B0(matrix[1], matrix[2], cross);','    }\n    func_150AD8B0(matrix[1], matrix[2], cross);')
    for name,body in (('middle',FACTOR),('reused',REUSED)):
        body = body.replace('f32 cross[3]','f32 cross[4]')
        yield 'param-'+name+'-register-position', body.replace('f32 *x, f32 *y, f32 *z',
            'register f32 *x, register f32 *y, register f32 *z')
        yield 'param-'+name+'-register-all', body.replace('f32 *x','register f32 *x').replace('f32 *y','register f32 *y').replace(
            'f32 *z','register f32 *z').replace('f32 *rx','register f32 *rx').replace('f32 *ry','register f32 *ry').replace(
            'f32 *rz','register f32 *rz').replace('f32 *sx','register f32 *sx').replace('f32 *sy','register f32 *sy').replace('f32 *sz','register f32 *sz')
        yield 'param-'+name+'-void-input', body.replace('f32 input[4][4]','void *input')
        yield 'param-'+name+'-scalar-factor', body.replace('    f32 length;','    f32 length;\n    f32 factor;').replace(
            '    { f32 factor = D_8009891C;','    factor = D_8009891C;').replace('    *rz = angleZ * factor;\n    }','    *rz = angleZ * factor;')
    yield 'flat-base', flat(BASE)
    yield 'flat-middle', flat(MIDDLE)
    yield 'flat-factor', flat(FACTOR)
    yield 'flat-four-factor', flat(FACTOR.replace('f32 cross[3]','f32 cross[4]'))
    yield 'flat-anchored', flat(ANCHORED)
    yield 'middle-four-new-factor', FACTOR.replace('f32 cross[3]','f32 cross[4]')
    yield 'anchored-new-factor', ANCHORED.replace('    length = D_8009891C;','    { f32 factor = D_8009891C;').replace(
        'angleX * length','angleX * factor').replace('angleY * length','angleY * factor').replace('angleZ * length','angleZ * factor').replace(
        '    *rz = angleZ * factor;','    *rz = angleZ * factor;\n    }')
    yield 'middle-address-copy', MIDDLE.replace('bcopy(input, matrix, sizeof(matrix))','bcopy(input, &matrix[0][0], sizeof(matrix))')
    yield 'middle-address-dot', MIDDLE.replace('func_150AD900(matrix[0], cross)','func_150AD900(&matrix[0][0], cross)')
    yield 'middle-whole-dot', MIDDLE.replace('func_150AD900(matrix[0], cross)','func_150AD900((f32 *)&matrix, cross)')
    yield 'middle-four-cross', MIDDLE.replace('f32 cross[3]','f32 cross[4]')
    yield 'middle-new-factor', MIDDLE.replace('    length = D_8009891C;','    { f32 factor = D_8009891C;').replace(
        'angleX * length','angleX * factor').replace('angleY * length','angleY * factor').replace('angleZ * length','angleZ * factor').replace(
        '    *rz = angleZ * factor;','    *rz = angleZ * factor;\n    }')
    yield 'cross-last', BASE.replace('    f32 cross[3];\n','').replace('    f32 angleZ;',
        '    f32 angleZ;\n    f32 cross[3];')
    yield 'matrix-last', BASE.replace('    f32 matrix[4][4];\n','').replace('    f32 angleZ;',
        '    f32 angleZ;\n    f32 matrix[4][4];')
    yield 'row-first', BASE.replace('    f32 (*row)[4];\n','').replace('    f32 matrix[4][4];',
        '    f32 (*row)[4];\n    f32 matrix[4][4];')
    yield 'inclusive-loop', BASE.replace('row < matrix + 3','row <= matrix + 2')
    yield 'not-equal-loop', BASE.replace('row < matrix + 3','row != matrix + 3')


def compile_candidate(root,out,name,body=SELECTED,profile='owner'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS,PROFILES=PROFILES):
        return compiler.compile_candidate(root,out,name,body,profile)


def install(source):
    assert source.count(ORIGINAL) == 1 and SELECTED not in source
    assert LOCAL_DECLARATIONS.rstrip() not in source
    return source.replace(ORIGINAL,SELECTED).replace('#include "variables.h"\n',
        '#include "variables.h"\n'+LOCAL_DECLARATIONS,1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='selected')
    parser.add_argument('--profiles',action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-matrix-decompose'
    records = []
    for name,body in candidates():
        if args.filter and args.filter not in name:
            continue
        for profile in (('owner','compact','o1g3','o1') if args.profiles else ('owner',)):
            meta,_ = compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__ == '__main__':
    main()
