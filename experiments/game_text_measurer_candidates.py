"""Recover the complete three-output text measure with live font metadata."""
import argparse
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x150428D4, 0x6FD84, 219
FUNCTION, SOURCE = 'func_150428D4', 'conker/src/game/generated_6E770.c'
ORIGINAL = 's32 func_150428D4() {\n    return 0;\n}'
DECLARATIONS = '''extern u8 *D_80085994;
extern f32 D_800380A0;
extern f32 D_800380A4;
s32 func_15042C40(u8);
void func_150415E0(s32, s32 *, s32 *, f32 *, s32 *, f32 *);
'''
SYMBOLS = dict(D_80085994=0x80085994,D_800380A0=0x800380A0,D_800380A4=0x800380A4,
    func_15042C40=0x15042C40,func_150415E0=0x150415E0)
PROFILES = dict(compiler.PROFILES,owner=('-O2','-g3','-Wo,-loopunroll,0'))
BASE = '''void func_150428D4(u8 *text, s32 *width, s32 *height, s32 *baseline) {
    s32 lineHeight;
    s32 maximumWidth;
    u8 *cursor;
    u8 glyph;
    s32 useFont;
    s32 glyphWidth;
    s32 glyphHeight;
    f32 glyphBaseline;
    s32 mode;
    f32 factor;
    s32 extent;

    if (text != NULL) {
        *width = 0;
        *height = 0;
        *baseline = 0;
        maximumWidth = 0;
        lineHeight = 0;
        if (*text == 0) {
            *height = (s32)((u32)*height + 12);
        }
        cursor = text;
        if (*text != 0) {
            do {
                if (*cursor == 0xBC) {
                    cursor += 2;
                } else {
                    glyph = func_15042C40(*cursor);
                    useFont = 0;
                    if (glyph == 0x60) {
                        *width = (s32)((u32)*width + 4);
                        if (lineHeight < 12) {
                            lineHeight = 12;
                        }
                    } else if (glyph < 0xA1 || glyph >= 0xA8) {
                        if (glyph >= 0xA8 && glyph < 0x100) {
                            func_150415E0(glyph, &glyphWidth, &glyphHeight,
                                &glyphBaseline, &mode, &factor);
                            *width = (s32)((f32)*width + (f32)glyphWidth * factor);
                            extent = (s32)((f32)(s32)((f32)glyphHeight * factor) - glyphBaseline) + 1;
                            if (lineHeight < extent) {
                                lineHeight = extent;
                            }
                            if ((f32)*baseline < glyphBaseline) {
                                *baseline = (s32)glyphBaseline;
                            }
                        } else if (glyph < 0xA1) {
                            if (*cursor == 0xA) {
                                if (maximumWidth < *width) {
                                    maximumWidth = *width;
                                }
                                *width = 0;
                                if (lineHeight < 12) {
                                    lineHeight = 12;
                                }
                                *height = (s32)((u32)*height + (u32)lineHeight);
                                lineHeight = 0;
                            } else {
                                useFont = 1;
                            }
                        }
                    }
                    cursor++;
                    if (useFont) {
                        *width = (s32)((u32)*width + D_80085994[glyph * 4] +
                            D_80085994[glyph * 4 + 2] - 1);
                        extent = D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1];
                        if (extent >= lineHeight) {
                            lineHeight = extent;
                        }
                    }
                }
            } while (*cursor != 0);
        }
        if (*width < maximumWidth) {
            *width = maximumWidth;
        }
        *height = (s32)((u32)*height + (u32)lineHeight);
        *width = (s32)((f32)*width * D_800380A0);
        *height = (s32)((f32)*height * D_800380A4);
        *baseline = (s32)((f32)*baseline * D_800380A0);
    }
}'''
SELECTED=BASE

M2C_LIFETIMES = '''void func_150428D4(u8 *text, s32 *width, s32 *height, s32 *baseline) {
    s32 savedFont;
    s32 glyphWidth;
    s32 glyphHeight;
    f32 glyphBaseline;
    s32 mode;
    f32 factor;
    s32 fontHeight;
    s32 glyph;
    s32 result;
    s32 extent;
    s32 previousWidth;
    s32 classification;
    s32 offset;
    s32 lineHeight;
    s32 maximumWidth;
    s32 useFont;
    u8 *cursor;
    u8 current;
    u8 command;
    u8 *row;
    u8 *heightRow;

    if (text != NULL) {
        *width = 0;
        *height = 0;
        *baseline = 0;
        maximumWidth = 0;
        lineHeight = 0;
        if (*text == 0) *height = (s32)((u32)*height + 12);
        cursor = text;
        if (*text != 0) {
            current = *cursor;
            command = current;
            do {
                if (command == 0xBC) {
                    cursor += 2;
                } else {
                    result = func_15042C40(current);
                    classification = result & 0xFF;
                    glyph = result & 0xFF;
                    useFont = 0;
                    if (classification == 0x60) {
                        *width = (s32)((u32)*width + 4);
                        if (lineHeight < 12) lineHeight = 12;
                    } else if (classification < 0xA1 || classification >= 0xA8) {
                        if (classification >= 0xA8 && classification < 0x100) {
                            savedFont = 0;
                            func_150415E0(glyph, &glyphWidth, &glyphHeight, &glyphBaseline, &mode, &factor);
                            useFont = savedFont;
                            *width = (s32)((f32)*width + (f32)glyphWidth * factor);
                            extent = (s32)((f32)(s32)((f32)glyphHeight * factor) - glyphBaseline) + 1;
                            if (lineHeight < extent) lineHeight = extent;
                            if ((f32)*baseline < glyphBaseline) *baseline = (s32)glyphBaseline;
                        } else if (classification < 0xA1) {
                            if (*cursor == 0xA) {
                                previousWidth = *width;
                                if (maximumWidth < previousWidth) maximumWidth = previousWidth;
                                *width = 0;
                                if (lineHeight < 12) lineHeight = 12;
                                *height = (s32)((u32)*height + (u32)lineHeight);
                                lineHeight = 0;
                            } else useFont = 1;
                        }
                    }
                    cursor++;
                    if (useFont != 0) {
                        offset = glyph * 4;
                        row = D_80085994 + offset;
                        *width = (s32)((u32)*width + row[0] + row[2] - 1);
                        heightRow = D_80085994 + offset;
                        fontHeight = heightRow[3] + heightRow[1];
                        if (fontHeight >= lineHeight) lineHeight = fontHeight;
                    }
                }
                current = *cursor;
                command = current;
            } while (current != 0);
        }
        if (*width < maximumWidth) *width = maximumWidth;
        *height = (s32)((u32)*height + (u32)lineHeight);
        *width = (s32)((f32)*width * D_800380A0);
        *height = (s32)((f32)*height * D_800380A4);
        *baseline = (s32)((f32)*baseline * D_800380A0);
    }
}'''


def candidates():
    yield 'selected',SELECTED
    indexed=BASE.replace('    u8 *cursor;', '    s32 index;').replace('        cursor = text;',
        '        index = 0;').replace('        if (*text != 0) {','        if (text[index] != 0) {').replace(
        '*cursor','text[index]').replace('cursor += 2','index += 2').replace('cursor++','index++')
    yield 'indexed-late',indexed
    early=indexed.replace('        index = 0;\n','').replace('        if (*text == 0) {',
        '        index = 0;\n        if (*text == 0) {')
    yield 'indexed-early',early
    control=BASE.split('                    useFont = 0;\n',1)[1].split('                    cursor++;',1)[0]
    expression='''                    useFont = glyph == 0x60 ?
                        (*width = (s32)((u32)*width + 4),
                         lineHeight = lineHeight < 12 ? 12 : lineHeight, 0) :
                        (glyph < 0xA1 || glyph >= 0xA8) ?
                            (glyph >= 0xA8 && glyph < 0x100) ?
                                (func_150415E0(glyph, &glyphWidth, &glyphHeight,
                                    &glyphBaseline, &mode, &factor),
                                 *width = (s32)((f32)*width + (f32)glyphWidth * factor),
                                 extent = (s32)((f32)(s32)((f32)glyphHeight * factor) - glyphBaseline) + 1,
                                 lineHeight = lineHeight < extent ? extent : lineHeight,
                                 (f32)*baseline < glyphBaseline ? (*baseline = (s32)glyphBaseline) : 0, 0) :
                            glyph < 0xA1 ?
                                *cursor == 0xA ?
                                    (maximumWidth = maximumWidth < *width ? *width : maximumWidth,
                                     *width = 0, lineHeight = lineHeight < 12 ? 12 : lineHeight,
                                     *height = (s32)((u32)*height + (u32)lineHeight), lineHeight = 0, 0) : 1 : 0 : 0;
'''
    ternary=BASE.replace('                    useFont = 0;\n'+control,expression)
    yield 'ternary-flag-pointer',ternary
    ternary_indexed=ternary.replace('    u8 *cursor;', '    s32 index;').replace('        cursor = text;',
        '        index = 0;').replace('        if (*text != 0) {','        if (text[index] != 0) {').replace(
        '*cursor','text[index]').replace('cursor += 2','index += 2').replace('cursor++','index++')
    ternary_indexed=ternary_indexed.replace('        index = 0;\n','').replace('        if (*text == 0) {',
        '        index = 0;\n        if (*text == 0) {').replace('    s32 extent;',
        '    s32 extent;\n    u8 **fontAddress = &D_80085994;').replace('D_80085994[glyph *','(*fontAddress)[glyph *')
    yield 'ternary-flag-indexed-remat',ternary_indexed
    for name,body in (('clear',BASE),('indexed',early)):
        byte='*cursor' if name=='clear' else 'text[index]'
        reused_flag=body.replace('glyph = func_15042C40('+byte+');',
            'useFont = func_15042C40('+byte+');\n                    glyph = (u8)useFont;')
        yield 'reuse-result-flag-'+name,reused_flag
        yield 'reuse-result-flag-'+name+'-remat',reused_flag.replace('    s32 extent;',
            '    s32 extent;\n    u8 **fontAddress = &D_80085994;').replace('D_80085994[glyph *','(*fontAddress)[glyph *')
        font_address=body.replace('    s32 extent;', '    s32 extent;\n    u8 **fontAddress = &D_80085994;').replace(
            'D_80085994[glyph *', '(*fontAddress)[glyph *')
        yield 'rematerialize-'+name+'-font-address',font_address
        if name=='indexed':
            pointer_flag=font_address.replace('s32 useFont;', 'void *useFont;').replace('useFont = 0;',
                'useFont = NULL;').replace('useFont = 1;', 'useFont = (void *)1;')
            yield 'pointer-flag-indexed',pointer_flag
            yield 'pointer-flag-indexed-const',pointer_flag.replace('void *useFont;', 'const void *useFont;')
            yield 'pointer-flag-indexed-register',pointer_flag.replace('void *useFont;', 'register void *useFont;')
            local=font_address.replace('    s32 useFont;\n','').replace(
                '                    useFont = 0;', '                    {\n                    s32 useFont = 0;').replace(
                '                }\n            } while (text[index] != 0);',
                '                    }\n                }\n            } while (text[index] != 0);')
            yield 'plain-flag-scope-after-normalize',local
            yield 'plain-flag-scope-before-normalize',local.replace(
                '                    glyph = func_15042C40(text[index]);\n                    {\n                    s32 useFont = 0;',
                '                    {\n                    s32 useFont = 0;\n                    glyph = func_15042C40(text[index]);')
            for kind in ('u8','register s32'):
                yield 'plain-flag-scope-'+kind.replace(' ','_'),local.replace('s32 useFont = 0;',kind+' useFont = 0;')
            eligibility=font_address.replace('                    useFont = 0;',
                '                    useFont = glyph != 0x60 && glyph < 0xA1 && text[index] != 0xA;').replace(
                '                            } else {\n                                useFont = 1;\n                            }',
                '                            }')
            yield 'eligibility-logical',eligibility
            yield 'eligibility-ternary',eligibility.replace(
                'glyph != 0x60 && glyph < 0xA1 && text[index] != 0xA',
                'glyph != 0x60 && glyph < 0xA1 ? text[index] != 0xA : 0')
            yield 'eligibility-negated',eligibility.replace(
                'glyph != 0x60 && glyph < 0xA1 && text[index] != 0xA',
                '!(glyph == 0x60 || glyph >= 0xA1 || text[index] == 0xA)')
            for mask in range(1,4):
                temp=font_address
                if mask&1:
                    temp=temp.replace('    u8 glyph;', '    s32 result;\n    s32 classification;\n    s32 glyph;').replace(
                        'glyph = func_15042C40(text[index]);',
                        'result = func_15042C40(text[index]);\n                    classification = result & 0xFF;\n                    glyph = result & 0xFF;')
                    for op in ('== 0x60','< 0xA1','>= 0xA8','< 0x100'):
                        temp=temp.replace('glyph '+op,'classification '+op)
                if mask&2:
                    temp=temp.replace('    s32 extent;', '    s32 extent;\n    u8 current;\n    u8 command;').replace(
                        '            do {', '            current = text[index];\n            command = current;\n            do {').replace(
                        'text[index] == 0xBC', 'command == 0xBC').replace('func_15042C40(text[index])','func_15042C40(current)').replace(
                        '            } while (text[index] != 0);',
                        '                current = text[index];\n                command = current;\n            } while (current != 0);')
                yield 'promotion-lifetimes-'+str(mask),temp
        for kind in ('u8','s8','u16','s16'):
            yield 'flag-width-'+name+'-'+kind,font_address.replace('s32 useFont;',kind+' useFont;')
        yield 'rematerialize-'+name+'-font-address-block',font_address.replace(
            '    u8 **fontAddress = &D_80085994;\n','').replace(
            '                    if (useFont) {', '                    if (useFont) {\n                        u8 **fontAddress = &D_80085994;')
        yield 'grouped-'+name+'-normalize-flag',body.replace(
            'glyph = func_15042C40('+('*cursor' if name=='clear' else 'text[index]')+');\n                    useFont = 0;',
            'glyph = func_15042C40('+('*cursor' if name=='clear' else 'text[index]')+'), useFont = 0;')
        yield 'grouped-'+name+'-all',body.replace(';\n','; ')
    for name,body in (('late',indexed),('early',early)):
        yield 'indexed-'+name+'-unsigned',body.replace('s32 index;', 'u32 index;')
        yield 'indexed-'+name+'-integer-glyph',body.replace('u8 glyph;', 's32 glyph;').replace(
            'glyph = func_','glyph = (u8)func_')
        yield 'indexed-'+name+'-while',body.replace('        if (text[index] != 0) {\n            do {',
            '        while (text[index] != 0) {').replace('            } while (text[index] != 0);\n        }',
            '        }')
    extended='(s32)((f32)(s32)((f32)glyphHeight * factor) - glyphBaseline) + 1'
    ordinary='D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1]'
    inline=BASE.replace('    s32 extent;\n','').replace(
        '                            extent = '+extended+';\n                            if (lineHeight < extent) {\n                                lineHeight = extent;',
        '                            if (lineHeight < ('+extended+')) {\n                                lineHeight = '+extended+';').replace(
        '                        extent = '+ordinary+';\n                        if (extent >= lineHeight) {\n                            lineHeight = extent;',
        '                        if (('+ordinary+') >= lineHeight) {\n                            lineHeight = '+ordinary+';')
    yield 'inline-extents',inline
    yield 'split-extents',BASE.replace('    s32 extent;', '    s32 extendedHeight;\n    s32 ordinaryHeight;').replace(
        'extent', 'extendedHeight').replace('extendedHeight = '+ordinary, 'ordinaryHeight = '+ordinary).replace(
        'if (extendedHeight >= lineHeight)', 'if (ordinaryHeight >= lineHeight)').replace(
        'lineHeight = extendedHeight;\n                        }', 'lineHeight = ordinaryHeight;\n                        }')
    moved=BASE.replace('    s32 extent;\n','').replace('    s32 useFont;', '    s32 extent;\n    s32 useFont;')
    yield 'extent-before-outputs',moved
    yield 'unsigned-compound-font',BASE.replace('''                        *width = (s32)((u32)*width + D_80085994[glyph * 4] +
                            D_80085994[glyph * 4 + 2] - 1);''','''                        *(u32 *)width += D_80085994[glyph * 4] + D_80085994[glyph * 4 + 2] - 1;''')
    reused=BASE.replace('u8 *text,','u32 textAddress,').replace('    u8 glyph;\n','').replace(
        'if (text != NULL)', 'if (textAddress != 0)').replace('*text', '*((u8 *)textAddress)').replace(
        'cursor = text;', 'cursor = (u8 *)textAddress;').replace('glyph = func_15042C40(*cursor);',
        'textAddress = (u8)func_15042C40(*cursor);').replace('glyph ==','textAddress ==').replace(
        'glyph <','textAddress <').replace('glyph >=','textAddress >=').replace('func_150415E0(glyph,','func_150415E0(textAddress,').replace(
        '[glyph *','[textAddress *')
    yield 'reuse-address-parameter',reused
    signed=reused.replace('u32 textAddress,','s32 textAddress,')
    yield 'reuse-signed-parameter',signed
    typed=signed.replace('s32 textAddress,','u8 *text,').replace(
        'textAddress = (u8)func_15042C40(*cursor);', 'text = (u8 *)(u32)(u8)func_15042C40(*cursor);').replace(
        '*((u8 *)textAddress)', '*text').replace('cursor = (u8 *)textAddress;', 'cursor = text;').replace(
        'if (textAddress != 0)', 'if (text != NULL)').replace('textAddress', '(s32)text')
    yield 'reuse-typed-parameter',typed
    for name,body in (('signed',signed),('typed',typed)):
        byte='*((u8 *)textAddress)' if name=='signed' else '*text'
        cursor='cursor = (u8 *)textAddress;' if name=='signed' else 'cursor = text;'
        for early in (False,True):
            changed=body.replace(cursor,'glyph = 0;\n        '+cursor[:-1]+' + glyph;').replace(
                '    s32 lineHeight;', '    s32 glyph;\n    s32 lineHeight;')
            if not early:
                changed=changed.replace(cursor[:-1]+' + glyph;\n        if ('+byte+' != 0) {',
                    'if ('+byte+' != 0) {\n            '+cursor[:-1]+' + glyph;')
            yield 'reuse-'+name+'-index-'+('early' if early else 'late'),changed
    yield 'reuse-address-local',reused.replace('u32 textAddress,','u8 *text,').replace(
        '    s32 lineHeight;', '    u32 textAddress = (u32)text;\n    s32 lineHeight;')
    for name,choices in (
            ('flag',('s32 useFont;',)),('glyph',('u8 glyph;',)),
            ('cursor',('u8 *cursor;',)),('parameters',('u8 *text,','s32 *width,','s32 *height,','s32 *baseline)')),
            ('locals',('s32 lineHeight;','s32 maximumWidth;','u8 *cursor;','u8 glyph;','s32 useFont;','s32 extent;')),
            ('all',('u8 *text,','s32 *width,','s32 *height,','s32 *baseline)','s32 lineHeight;','s32 maximumWidth;',
                'u8 *cursor;','u8 glyph;','s32 useFont;','s32 extent;'))):
        body=BASE
        for choice in choices:body=body.replace(choice,'register '+choice)
        yield 'register-'+name,body
    loop=BASE.replace('        if (*text != 0) {\n            do {','        while (*cursor != 0) {').replace(
        '            } while (*cursor != 0);\n        }','        }')
    yield 'while-cursor',loop
    yield 'for-cursor',loop.replace('        cursor = text;\n        while (*cursor != 0) {',
        '        for (cursor = text; *cursor != 0;) {')
    yield 'while-cursor-early',loop.replace('        cursor = text;\n','').replace(
        '    if (text != NULL) {', '    cursor = text;\n    if (text != NULL) {')
    yield 'while-byte-cache',loop.replace('    s32 extent;', '    s32 extent;\n    u8 current;').replace(
        '        while (*cursor != 0) {','        while ((current = *cursor) != 0) {').replace(
        'if (*cursor == 0xBC)','if (current == 0xBC)').replace('func_15042C40(*cursor)','func_15042C40(current)')
    escape='''                if (*cursor == 0xBC) {
                    cursor += 2;
                } else {'''
    continued=loop.replace(escape,'''                if (*cursor == 0xBC) {
                    cursor += 2;
                    continue;
                }
                {''')
    yield 'while-escape-continue',continued
    yield 'while-escape-continue-block-flag',continued.replace('    s32 useFont;\n','').replace(
        '                {\n                    glyph','                {\n                    s32 useFont;\n                    glyph')
    last=BASE.replace('        cursor = text;\n        if (*text != 0) {\n            do {',
        '        cursor = text;\n        while (1) {\n            if (*cursor == 0) break;').replace(
        '            } while (*cursor != 0);\n        }','        }')
    yield 'while-break',last
    yield 'while-break-continue',last.replace(escape,'''                if (*cursor == 0xBC) {
                    cursor += 2;
                    continue;
                }
                {''')
    head=BASE.replace('        cursor = text;\n        if (*text != 0) {\n            do {',
        '        cursor = text;\n        goto check;\n        {\n            do {').replace(
        '            } while (*cursor != 0);','check:\n                if (*cursor == 0) break;\n            } while (1);')
    yield 'jump-to-check',head
    yield 'm2c-lifetimes',M2C_LIFETIMES
    yield 'signed-sums',BASE.replace('(s32)((u32)*height + 12)','*height + 12').replace(
        '(s32)((u32)*width + 4)','*width + 4').replace('(s32)((u32)*height + (u32)lineHeight)',
        '*height + lineHeight').replace('(s32)((u32)*width + D_80085994[glyph * 4] +\n                            D_80085994[glyph * 4 + 2] - 1)',
        '*width + D_80085994[glyph * 4] + D_80085994[glyph * 4 + 2] - 1')
    yield 'integer-glyph',BASE.replace('u8 glyph;', 's32 glyph;').replace('glyph = func_', 'glyph = (u8)func_')
    yield 'height-first',BASE.replace('    s32 lineHeight;\n    s32 maximumWidth;', '    s32 maximumWidth;\n    s32 lineHeight;')
    start=BASE.replace('        cursor = text;', '        glyph = 0;\n        cursor = text + glyph;')
    yield 'initial-index',start
    yield 'initial-index-late',start.replace('        cursor = text + glyph;\n        if (*text != 0) {',
        '        if (*text != 0) {\n            cursor = text + glyph;')
    yield 'initial-index-late-integer',start.replace('        cursor = text + glyph;\n        if (*text != 0) {',
        '        if (*text != 0) {\n            cursor = text + glyph;').replace('u8 glyph;', 's32 glyph;').replace('glyph = func_', 'glyph = (u8)func_')
    yield 'array-pointer',BASE.replace('D_80085994[glyph * 4', 'D_80085994[0][glyph * 4')
    yield 'integer-flag-first',BASE.replace('    s32 useFont;', '    s32 useFont;').replace(
        '                    glyph = func_15042C40(*cursor);\n                    useFont = 0;',
        '                    useFont = 0;\n                    glyph = func_15042C40(*cursor);')
    yield 'volatile-flag',BASE.replace('s32 useFont;', 'volatile s32 useFont;')
    yield 'table-row-local',BASE.replace('    s32 extent;', '    s32 extent;\n    u8 *row;').replace(
        '                        *width = (s32)((u32)*width + D_80085994[glyph * 4] +\n                            D_80085994[glyph * 4 + 2] - 1);\n                        extent = D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1];',
        '                        row = D_80085994 + glyph * 4;\n                        *width = (s32)((u32)*width + row[0] + row[2] - 1);\n                        row = D_80085994 + glyph * 4;\n                        extent = row[3] + row[1];')
    yield 'block-flag',BASE.replace('    s32 useFont;\n','').replace('                } else {\n                    glyph',
        '                } else {\n                    s32 useFont;\n                    glyph')
    phase=BASE.replace('    s32 useFont;\n','').replace(
        '                    useFont = 0;', '                    {\n                    s32 useFont = 0;').replace(
        '                }\n            } while (*cursor != 0);', '                    }\n                }\n            } while (*cursor != 0);')
    yield 'post-call-flag-scope',phase
    yield 'post-call-flag-scope-index',phase.replace('        cursor = text;\n        if (*text != 0) {',
        '        glyph = 0;\n        if (*text != 0) {\n            cursor = text + glyph;')
    state=BASE
    for line in ('    s32 useFont;\n','    s32 glyphWidth;\n','    s32 glyphHeight;\n',
            '    f32 glyphBaseline;\n','    s32 mode;\n','    f32 factor;\n'):
        state=state.replace(line,'')
    state=state.replace('    s32 extent;', '''    s32 extent;
    struct { f32 factor; s32 mode; f32 baseline; s32 height, width, useFont; } metrics;''')
    for old,new in (('glyphWidth','metrics.width'),('glyphHeight','metrics.height'),('glyphBaseline','metrics.baseline'),
            ('useFont','metrics.useFont'),('&mode','&metrics.mode'),('&factor','&metrics.factor'),(' * factor',' * metrics.factor')):
        state=state.replace(old,new)
    state=state.replace('width, metrics.useFont;', 'width, useFont;')
    yield 'metrics-state',state
    yield 'metrics-state-initial-index',state.replace('        cursor = text;\n        if (*text != 0) {',
        '        glyph = 0;\n        if (*text != 0) {\n            cursor = text + glyph;')
    state_index=state.replace('    u8 *cursor;', '    s32 index;').replace('        cursor = text;',
        '        index = 0;').replace('        if (*text != 0) {','        if (text[index] != 0) {').replace(
        '*cursor','text[index]').replace('cursor += 2','index += 2').replace('cursor++','index++')
    state_index=state_index.replace('        index = 0;\n','').replace('        if (*text == 0) {',
        '        index = 0;\n        if (*text == 0) {')
    yield 'metrics-state-indexed-early',state_index
    captured=state_index.replace('metrics.useFont','useFont').replace('    s32 extent;',
        '    s32 extent;\n    s32 useFont;').replace('                            func_150415E0(',
        '                            metrics.useFont = useFont;\n                            func_150415E0(').replace(
        '                            *width = (s32)((f32)*width',
        '                            useFont = metrics.useFont;\n                            *width = (s32)((f32)*width')
    yield 'metrics-call-flag',captured
    split=captured.replace('s32 extent;', 's32 extent;\n    s32 fontHeight;').replace(
        'extent = D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1];',
        'fontHeight = D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1];').replace(
        'if (extent >= lineHeight)', 'if (fontHeight >= lineHeight)').replace(
        'lineHeight = extent;\n                        }', 'lineHeight = fontHeight;\n                        }')
    yield 'metrics-call-flag-split-before',split
    yield 'metrics-call-flag-split-after',split.replace('    s32 fontHeight;\n','').replace(
        'width, useFont; } metrics;', 'width, useFont; } metrics;\n    s32 fontHeight;')
    for position in ('before-record','after-record','after-address'):
        changed=captured.replace('    s32 useFont;\n','')
        changed=changed.replace('D_80085994[glyph *','(*fontAddress)[glyph *')
        marker='    struct {' if position=='before-record' else 'width, useFont; } metrics;'
        if position=='before-record':
            changed=changed.replace(marker,'    u8 **fontAddress = &D_80085994;\n    s32 useFont;\n'+marker)
        else:
            declarations='\n    s32 useFont;\n    u8 **fontAddress = &D_80085994;' if position=='after-record' else \
                '\n    u8 **fontAddress = &D_80085994;\n    s32 useFont;'
            changed=changed.replace(marker,marker+declarations)
        yield 'capture-declaration-'+position,changed
        if position=='after-record':
            for kind in ('u8','u16','s8','s16'):
                yield 'capture-subword-'+kind,changed.replace('    s32 useFont;', '    '+kind+' useFont;')
            yield 'capture-normalize-extent',changed.replace(
                '                    glyph = func_15042C40(text[index]);\n                    useFont = 0;',
                '                    extent = func_15042C40(text[index]);\n                    useFont = 0;\n                    glyph = (u8)extent;')
            merged=changed.replace('    s32 useFont;', '    s32 useFont;\n    s32 capturedFont;').replace(
                '                            useFont = metrics.useFont;', '                            capturedFont = metrics.useFont;').replace(
                '                        } else if (glyph < 0xA1) {',
                '                            useFont = capturedFont;\n                        } else if (glyph < 0xA1) {')
            yield 'capture-post-call-merge',merged
            yield 'capture-post-call-merge-comma',merged.replace(
                '                            capturedFont = metrics.useFont;\n                            *width',
                '                            capturedFont = metrics.useFont,\n                            *width')
            reused_merge=merged.replace('    s32 capturedFont;\n','').replace('    s32 index;',
                '    s32 index;\n    u8 *cursor;').replace('text[index]','*cursor').replace(
                'index += 2;', 'cursor += 2;').replace('index++;','cursor++;').replace(
                '        if (*cursor != 0) {', '        cursor = text + index;\n        if (*text != 0) {').replace(
                'capturedFont', 'index')
            yield 'capture-post-call-reuse-index',reused_merge
            yield 'capture-constant-spill',changed.replace('metrics.useFont = useFont;', 'metrics.useFont = 0;')
            yield 'capture-automatic-spill',changed.replace('                            metrics.useFont = useFont;\n','').replace(
                '                            useFont = metrics.useFont;\n','')
            yield 'capture-widened-glyph',changed.replace('u8 glyph;', 'u32 glyph;').replace(
                'glyph = func_15042C40(text[index]);', 'glyph = (u8)func_15042C40(text[index]);')
            for declaration in ('u8 glyph;', 's32 index;', 's32 *height,'):
                yield 'capture-priority-'+declaration.split()[1].strip(';*,'),changed.replace(
                    declaration, 'register '+declaration)
            for kind in ('s32','u32'):
                yield 'capture-call-promotion-'+kind,changed.replace('func_150415E0(glyph,',
                    'func_150415E0(('+kind+')glyph,')
            dispatch='''                    if (glyph == 0x60) {
                        *width = (s32)((u32)*width + 4);
                        if (lineHeight < 12) lineHeight = 12;
                        goto glyph_done;
                    }
                    if (glyph >= 0xA1 && glyph < 0xA8) goto glyph_done;
                    if (glyph >= 0xA8 && glyph < 0x100) {
                        metrics.useFont = useFont;
                        func_150415E0(glyph, &metrics.width, &metrics.height,
                            &metrics.baseline, &metrics.mode, &metrics.factor);
                        useFont = metrics.useFont;
                        *width = (s32)((f32)*width + (f32)metrics.width * metrics.factor);
                        extent = (s32)((f32)(s32)((f32)metrics.height * metrics.factor) - metrics.baseline) + 1;
                        if (lineHeight < extent) lineHeight = extent;
                        if ((f32)*baseline < metrics.baseline) *baseline = (s32)metrics.baseline;
                        goto glyph_done;
                    }
                    if (glyph < 0xA1) {
                        if (text[index] == 0xA) {
                            if (maximumWidth < *width) maximumWidth = *width;
                            *width = 0;
                            if (lineHeight < 12) lineHeight = 12;
                            *height = (s32)((u32)*height + (u32)lineHeight);
                            lineHeight = 0;
                        } else useFont = 1;
                    }
glyph_done:
'''
            start=changed.index('                    if (glyph == 0x60) {')
            end=changed.index('                    index++;',start)
            flat=changed[:start]+dispatch+changed[end:]
            yield 'capture-flat-dispatch',flat
            yield 'capture-flat-automatic',flat.replace('                        metrics.useFont = useFont;\n','').replace(
                '                        useFont = metrics.useFont;\n','')
            late_flag=flat.replace('                    useFont = 0;\n','').replace(
                '                        goto glyph_done;\n                    }\n                    if (glyph >= 0xA1',
                '                        useFont = 0;\n                        goto glyph_done;\n                    }\n                    if (glyph >= 0xA1').replace(
                'if (glyph >= 0xA1 && glyph < 0xA8) goto glyph_done;',
                'if (glyph >= 0xA1 && glyph < 0xA8) { useFont = 0; goto glyph_done; }').replace(
                'metrics.useFont = useFont;', 'metrics.useFont = 0;').replace(
                '                            lineHeight = 0;\n                        } else useFont = 1;',
                '                            lineHeight = 0;\n                            useFont = 0;\n                        } else useFont = 1;').replace(
                '                    }\nglyph_done:', '                    } else useFont = 0;\nglyph_done:')
            yield 'capture-flat-late-flag',late_flag
            local_dispatch='''                    if (glyph == 0x60) {
                        *width = (s32)((u32)*width + 4);
                        if (lineHeight < 12) lineHeight = 12;
                        goto glyph_skip;
                    }
                    if (glyph >= 0xA1 && glyph < 0xA8) goto glyph_skip;
                    if (glyph >= 0xA8 && glyph < 0x100) {
                        metrics.useFont = 0;
                        func_150415E0(glyph, &metrics.width, &metrics.height,
                            &metrics.baseline, &metrics.mode, &metrics.factor);
                        useFont = metrics.useFont;
                        *width = (s32)((f32)*width + (f32)metrics.width * metrics.factor);
                        extent = (s32)((f32)(s32)((f32)metrics.height * metrics.factor) - metrics.baseline) + 1;
                        if (lineHeight < extent) lineHeight = extent;
                        if ((f32)*baseline < metrics.baseline) *baseline = (s32)metrics.baseline;
                        if (useFont) goto glyph_font;
                        goto glyph_skip;
                    }
                    if (glyph < 0xA1) {
                        if (text[index] == 0xA) {
                            if (maximumWidth < *width) maximumWidth = *width;
                            *width = 0;
                            if (lineHeight < 12) lineHeight = 12;
                            *height = (s32)((u32)*height + (u32)lineHeight);
                            lineHeight = 0;
                        } else goto glyph_font;
                    }
                    goto glyph_skip;
glyph_font:
                    index++;
                    *width = (s32)((u32)*width + (*fontAddress)[glyph * 4] +
                        (*fontAddress)[glyph * 4 + 2] - 1);
                    extent = (*fontAddress)[glyph * 4 + 3] + (*fontAddress)[glyph * 4 + 1];
                    if (extent >= lineHeight) lineHeight = extent;
                    goto glyph_next;
glyph_skip:
                    index++;
glyph_next:
                    ;
'''
            end=changed.index('                }\n            } while (text[index] != 0);',start)
            local=changed[:start].replace('                    useFont = 0;\n','')+local_dispatch+changed[end:]
            yield 'capture-local-dispatch',local
            shared=local_dispatch.split('glyph_font:\n',1)[0].replace(
                '                        if (useFont) goto glyph_font;\n                        goto glyph_skip;',
                '                        goto glyph_done;')+'''glyph_font:
                    useFont = 1;
                    goto glyph_done;
glyph_skip:
                    useFont = 0;
glyph_done:
'''
            footer=changed[changed.index('                    index++;',start):end]
            yield 'capture-shared-flag-exit',changed[:start].replace('                    useFont = 0;\n','')+shared+footer+changed[end:]
            reused_local=local.replace('    u8 glyph;\n','').replace('    s32 extent;',
                '    u8 *base = text;\n    s32 extent;').replace('text[index]','base[index]').replace(
                'glyph = func_15042C40(base[index]);', 'text = (u8 *)(u32)(u8)func_15042C40(base[index]);')
            for op in ('== 0x60','< 0xA1','>= 0xA1','>= 0xA8','< 0xA8','< 0x100'):
                reused_local=reused_local.replace('glyph '+op,'(s32)text '+op)
            reused_local=reused_local.replace('func_150415E0(glyph,','func_150415E0((s32)text,').replace(
                '[glyph *','[(s32)text *')
            yield 'capture-local-reuse-typed',reused_local
            deferred=reused_local.replace('    u8 *base = text;', '    u8 *base;')
            for marker in ('        *baseline = 0;', '        index = 0;'):
                yield 'capture-local-reuse-at-'+('outputs' if 'baseline' in marker else 'index'),deferred.replace(
                    marker,marker+'\n        base = text;')
            numeric=reused_local.replace('u8 *text,', 'u32 text,').replace('u8 *base = text;',
                'u8 *base = (u8 *)text;').replace('text != NULL', 'text != 0').replace(
                'if (*text == 0)', 'if (*((u8 *)text) == 0)').replace(
                'text = (u8 *)(u32)(u8)func_', 'text = (u8)func_').replace('(s32)text','text')
            yield 'capture-local-reuse-address',numeric
            yield 'capture-local-reuse-address-index',numeric.replace('u8 *base = (u8 *)text;',
                'u8 *base;').replace('        index = 0;', '        index = 0;\n        base = (u8 *)text;')
            for mask in range(1,4):
                callbacks=changed
                if mask&1:
                    callbacks=callbacks.replace('    s32 extent;',
                        '    s32 extent;\n    s32 (*normalize)(u8) = func_15042C40;').replace(
                        'glyph = func_15042C40(', 'glyph = normalize(')
                if mask&2:
                    callbacks=callbacks.replace('    s32 extent;',
                        '    s32 extent;\n    void (*measure)(s32,s32 *,s32 *,f32 *,s32 *,f32 *) = func_150415E0;').replace(
                        '                            func_150415E0(', '                            measure(')
                yield 'callback-lifetimes-'+str(mask),callbacks
            branched=changed.replace('                    useFont = 0;\n','').replace(
                '                    if (glyph == 0x60) {', '                    if (glyph == 0x60) {\n                        useFont = 0;').replace(
                'metrics.useFont = useFont;', 'metrics.useFont = 0;').replace(
                '                            if (text[index] == 0xA) {',
                '                            if (text[index] == 0xA) {\n                                useFont = 0;').replace(
                '                        }\n                    }\n                    index++;',
                '                        } else {\n                            useFont = 0;\n                        }\n                    } else {\n                        useFont = 0;\n                    }\n                    index++;')
            yield 'flag-branches-captured',branched
            for prefix,spill_body in (('capture',changed),('flag-branches',branched)):
                volatile_spill=spill_body.replace('s32 height, width, useFont; } metrics;',
                    's32 height, width; volatile s32 useFont; } metrics;')
                yield prefix+'-volatile-spill',volatile_spill
                parameter_glyph=spill_body.replace('    u8 glyph;\n', '').replace(
                    '    s32 index;', '    s32 index;\n    u8 *cursor;').replace(
                    '        if (text[index] != 0) {',
                    '        cursor = text + index;\n        if (*text != 0) {').replace(
                    'text[index]', '*cursor').replace('index += 2;', 'cursor += 2;').replace(
                    'index++;', 'cursor++;').replace('glyph = func_15042C40(*cursor);',
                    'text = (u8 *)(u32)(u8)func_15042C40(*cursor);')
                for comparison in ('== 0x60', '< 0xA1', '>= 0xA8', '< 0x100'):
                    parameter_glyph=parameter_glyph.replace('glyph '+comparison,
                        '(s32)text '+comparison)
                parameter_glyph=parameter_glyph.replace('func_150415E0(glyph,',
                    'func_150415E0((s32)text,').replace('[glyph *', '[(s32)text *')
                yield prefix+'-parameter-glyph',parameter_glyph
                union_flag=spill_body.replace('    s32 useFont;\n',
                    '    union { s32 prepared, restored; } fontFlag;\n').replace(
                    'useFont = metrics.useFont;', 'fontFlag.restored = metrics.useFont;').replace(
                    'metrics.useFont = useFont;', 'metrics.useFont = fontFlag.prepared;').replace(
                    'if (useFont)', 'if (fontFlag.restored)').replace('useFont = 0;',
                    'fontFlag.prepared = 0;').replace('useFont = 1;', 'fontFlag.prepared = 1;').replace(
                    'metrics.fontFlag.prepared', 'metrics.useFont')
                yield prefix+'-union-flag',union_flag
            font_record=branched.replace('    s32 lineHeight;',
                '    typedef struct { u8 left, top, right, bottom; } FontGlyph;\n    s32 lineHeight;')
            for suffix,member in (('', 'left'),(' + 1','top'),(' + 2','right'),(' + 3','bottom')):
                font_record=font_record.replace('(*fontAddress)[glyph * 4'+suffix+']',
                    '((FontGlyph *)*fontAddress)[glyph].'+member)
            yield 'flag-branches-font-record',font_record
            cast_font=branched
            for suffix in ('',' + 2'):
                cast_font=cast_font.replace('(*fontAddress)[glyph * 4'+suffix+']',
                    '(u32)(*fontAddress)[glyph * 4'+suffix+']')
            yield 'flag-branches-font-casts',cast_font
            font_reads='''                        u8 *row;
                        s32 currentWidth;
                        u8 left, right, bottom, top;

                        row = *fontAddress + glyph * 4;
                        currentWidth = *(volatile s32 *)width;
                        left = *(volatile u8 *)(row + 0);
                        right = *(volatile u8 *)(row + 2);
                        *width = (s32)((u32)currentWidth + left + right - 1);
                        row = *fontAddress + glyph * 4;
                        bottom = *(volatile u8 *)(row + 3);
                        top = *(volatile u8 *)(row + 1);
                        extent = bottom + top;'''
            font_expression='''                        *width = (s32)((u32)*width + (*fontAddress)[glyph * 4] +
                            (*fontAddress)[glyph * 4 + 2] - 1);
                        extent = (*fontAddress)[glyph * 4 + 3] + (*fontAddress)[glyph * 4 + 1];'''
            ordered=branched.replace(font_expression,font_reads)
            yield 'flag-branches-font-read-order',ordered
            yield 'flag-branches-font-read-temporaries',ordered.replace('volatile ','')
            declarations='''                        u8 *row;
                        s32 currentWidth;
                        u8 left, right, bottom, top;

'''
            yield 'flag-branches-font-read-outer',ordered.replace(declarations,'').replace(
                '    u8 **fontAddress = &D_80085994;',
                '    u8 **fontAddress = &D_80085994;\n    u8 *row;\n    s32 currentWidth;\n    u8 left, right, bottom, top;')
            reuse_reads='''                        row = *fontAddress + glyph * 4;
                        useFont = *width;
                        left = row[0];
                        right = row[2];
                        *width = (s32)((u32)useFont + left + right - 1);
                        row = *fontAddress + glyph * 4;
                        extent = row[3];
                        left = row[1];
                        extent = extent + left;'''
            yield 'flag-branches-font-reuse',branched.replace(font_expression,reuse_reads).replace(
                '    u8 **fontAddress = &D_80085994;',
                '    u8 **fontAddress = &D_80085994;\n    u8 *row;\n    u8 left, right;')
            automatic=changed.replace(font_expression,reuse_reads).replace(
                '    u8 **fontAddress = &D_80085994;',
                '    u8 **fontAddress = &D_80085994;\n    u8 *row;\n    u8 left, right;').replace(
                '                            metrics.useFont = useFont;\n','').replace(
                '                            useFont = metrics.useFont;\n','')
            yield 'capture-font-automatic-six',automatic
            yield 'capture-font-automatic-five',automatic.replace('width, useFont; } metrics;', 'width; } metrics;')
            compact_reads='''                        index = glyph * 4;
                        text = *fontAddress + index;
                        useFont = *width;
                        glyph = text[0];
                        extent = text[2];
                        *width = (s32)((u32)useFont + glyph + extent - 1);
                        text = *fontAddress + index;
                        extent = text[3];
                        glyph = text[1];
                        extent = extent + glyph;'''
            compact=branched.replace(font_expression,compact_reads).replace('    s32 index;',
                '    s32 index;\n    u8 *cursor;').replace('text[index]','*cursor').replace(
                'index += 2;', 'cursor += 2;').replace('                    index++;','                    cursor++;').replace(
                '        if (*cursor != 0) {', '        cursor = text + index;\n        if (*text != 0) {')
            yield 'flag-branches-font-reuse-inputs',compact
            unified=compact.replace('    u8 glyph;\n','').replace('    u8 *cursor;', '    u8 *cursor;\n    u32 character;').replace(
                'glyph = func_15042C40(*cursor);','character = (u8)func_15042C40(*cursor);').replace('glyph','character')
            yield 'flag-branches-font-reuse-wide',unified
            parameter_reads='''                        index = (s32)text * 4;
                        text = *fontAddress + index;
                        useFont = *width;
                        extent = text[0];
                        useFont = (s32)((u32)useFont + (u32)extent);
                        extent = text[2];
                        *width = (s32)((u32)useFont + (u32)extent - 1);
                        text = *fontAddress + index;
                        useFont = text[3];
                        extent = text[1];
                        extent = useFont + extent;'''
            parameter=branched.replace(font_expression,parameter_reads).replace('    u8 glyph;\n','').replace(
                '    s32 index;', '    s32 index;\n    u8 *cursor;').replace('text[index]','*cursor').replace(
                'index += 2;', 'cursor += 2;').replace('                    index++;','                    cursor++;').replace(
                '        if (*cursor != 0) {', '        cursor = text + index;\n        if (*text != 0) {').replace(
                'glyph = func_15042C40(*cursor);', 'text = (u8 *)(u32)(u8)func_15042C40(*cursor);')
            for op in ('== 0x60','< 0xA1','>= 0xA8','< 0x100'):
                parameter=parameter.replace('glyph '+op,'(s32)text '+op)
            parameter=parameter.replace('func_150415E0(glyph,', 'func_150415E0((s32)text,')
            yield 'flag-branches-font-reuse-parameter',parameter
            yield 'flag-branches-no-impossible-zero',branched.replace(
                '                        } else {\n                            useFont = 0;\n                        }\n                    } else {',
                '                        }\n                    } else {')
            for tag,source in (('capture',changed),('branches',branched)):
                switched=source.replace('                    if (glyph == 0x60) {',
                    '                    switch (glyph) {\n                    case 0x60:').replace(
                    '                    } else if (glyph < 0xA1 || glyph >= 0xA8) {',
                    '                        break;\n                    default:\n                    if (glyph < 0xA1 || glyph >= 0xA8) {').replace(
                    '                    }\n                    index++;',
                    '                    }\n                    break;\n                    }\n                    index++;')
                yield 'flag-switch-'+tag,switched
            aggregate=changed.replace('    s32 useFont;\n','').replace('    u8 **fontAddress = &D_80085994;',
                '    u8 **fontAddress = &D_80085994;\n    struct { s32 value; } fontFlag;')
            aggregate=aggregate.replace('width, useFont;', 'width, savedFlag;').replace(
                'metrics.useFont','metrics.savedFlag').replace('useFont','fontFlag.value').replace(
                'metrics.savedFlag','metrics.useFont').replace('width, savedFlag;', 'width, useFont;')
            yield 'capture-aggregate-flag',aggregate
            yield 'capture-array-flag',aggregate.replace('struct { s32 value; } fontFlag;',
                's32 fontFlag[1];').replace('fontFlag.value','fontFlag[0]')
            for kind in ('s32','u32'):
                yield 'capture-bitfield-word-'+kind,aggregate.replace(
                    'struct { s32 value; } fontFlag;',
                    'struct { '+kind+' value : 32; } fontFlag;')
            for tag,declaration in (('mutable','s32 *flagAddress'),('const','s32 *const flagAddress')):
                pointer_flag=aggregate.replace('struct { s32 value; } fontFlag;',
                    's32 flagValue;\n    '+declaration+' = &flagValue;').replace(
                    'fontFlag.value','(*flagAddress)')
                yield 'capture-addressed-flag-'+tag,pointer_flag
            inline_start=changed.index('    if (text != NULL) {')
            inline_tail=changed[inline_start:].replace('metrics.useFont','metrics.savedFlag')
            for tag,access in (('direct','(*(&useFont))'),
                    ('void-cast','(*(s32 *)(void *)&useFont)')):
                inline_flag=changed[:inline_start]+inline_tail.replace('useFont',access).replace(
                    'metrics.savedFlag','metrics.useFont')
                yield 'capture-inline-address-'+tag,inline_flag
            yield 'capture-reset-in-condition',changed.replace('                    useFont = 0;\n','').replace(
                'if (glyph == 0x60)', 'if ((useFont = 0, glyph) == 0x60)')
            yield 'capture-reset-call-expression',changed.replace(
                'glyph = func_15042C40(text[index]);\n                    useFont = 0;',
                'glyph = func_15042C40(text[index]), useFont = 0;')
            yield 'capture-enum-flag',changed.replace('    s32 useFont;\n',
                '    enum { FONT_SKIP = 0, FONT_USE = 1 } useFont;\n')
            for kind in ('s64','u64'):
                wide_flag=changed.replace('    s32 useFont;\n', '    '+kind+' useFont;\n')
                if kind=='u64':
                    wide_flag=wide_flag.replace('useFont = metrics.useFont;',
                        'useFont = (u32)metrics.useFont;')
                yield 'capture-wide-flag-'+kind,wide_flag
            expression_dispatch='''                    useFont = glyph == 0x60 ?
                        (*width = (s32)((u32)*width + 4),
                         lineHeight = lineHeight < 12 ? 12 : lineHeight, 0) :
                        (glyph < 0xA1 || glyph >= 0xA8) ?
                        ((glyph >= 0xA8 && glyph < 0x100) ?
                            (metrics.useFont = 0,
                             func_150415E0(glyph, &metrics.width, &metrics.height,
                                 &metrics.baseline, &metrics.mode, &metrics.factor),
                             capturedFont = metrics.useFont,
                             *width = (s32)((f32)*width + (f32)metrics.width * metrics.factor),
                             extent = (s32)((f32)(s32)((f32)metrics.height * metrics.factor) - metrics.baseline) + 1,
                             lineHeight = lineHeight < extent ? extent : lineHeight,
                             (f32)*baseline < metrics.baseline ?
                                 (*baseline = (s32)metrics.baseline) : 0,
                             capturedFont) :
                         glyph < 0xA1 ?
                            (text[index] == 0xA ?
                                (maximumWidth = maximumWidth < *width ? *width : maximumWidth,
                                 *width = 0,
                                 lineHeight = lineHeight < 12 ? 12 : lineHeight,
                                 *height = (s32)((u32)*height + (u32)lineHeight),
                                 lineHeight = 0, 0) : 1) : 0) : 0;
'''
            expression_start=changed.index('                    useFont = 0;')
            expression_end=changed.index('                    index++;',expression_start)
            expression_body=changed[:expression_start]+expression_dispatch+changed[expression_end:]
            expression_body=expression_body.replace('    s32 useFont;\n',
                '    s32 useFont;\n    s32 capturedFont;\n')
            yield 'capture-conditional-result',expression_body
            effect_dispatch=expression_dispatch.replace(
                'lineHeight = lineHeight < 12 ? 12 : lineHeight',
                'lineHeight < 12 ? (lineHeight = 12) : 0').replace(
                'lineHeight = lineHeight < extent ? extent : lineHeight',
                'lineHeight < extent ? (lineHeight = extent) : 0').replace(
                'maximumWidth = maximumWidth < *width ? *width : maximumWidth',
                'maximumWidth < *width ? (maximumWidth = *width) : 0')
            yield 'capture-conditional-effects',expression_body.replace(expression_dispatch,effect_dispatch)
            for tag,dispatch in (('result',expression_dispatch),('effects',effect_dispatch)):
                predicate=dispatch.removeprefix('                    useFont = ').rstrip().removesuffix(';')
                direct_body=expression_body.replace('    s32 useFont;\n','').replace(
                    expression_dispatch+'                    index++;\n                    if (useFont) {',
                    '                    if ('+predicate+') {\n                        index++;').replace(
                    '                    }\n                }\n            } while (text[index] != 0);',
                    '                    } else {\n                        index++;\n                    }\n                }\n            } while (text[index] != 0);')
                yield 'capture-direct-condition-'+tag,direct_body
            yield 'flag-branches-post-call-merge',branched.replace('    s32 useFont;',
                '    s32 useFont;\n    s32 capturedFont;').replace('                            useFont = metrics.useFont;',
                '                            capturedFont = metrics.useFont;').replace('                        } else if (glyph < 0xA1) {',
                '                            useFont = capturedFont;\n                        } else if (glyph < 0xA1) {')
            yield 'flag-branches-captured-after-space',branched.replace(
                '                        useFont = 0;\n                        *width', '                        *width').replace(
                '                        }\n                    } else if (glyph',
                '                        }\n                        useFont = 0;\n                    } else if (glyph')
            plain=branched.replace('                            metrics.useFont = 0;\n','').replace(
                '                            useFont = metrics.useFont;', '                            useFont = 0;')
            yield 'flag-branches-after-call',plain
            yield 'flag-branches-before-call',plain.replace('                            useFont = 0;\n','',1).replace(
                '                            func_150415E0(', '                            useFont = 0;\n                            func_150415E0(')
            for kind in ('u32','register s32','register u32','register volatile s32'):
                yield 'flag-scope-'+kind.replace(' ','_'),changed.replace('    s32 useFont;', '    '+kind+' useFont;')
            yield 'flag-scope-explicit-condition',changed.replace('if (useFont)', 'if (useFont != 0)')
            yield 'flag-scope-boolean-reload',changed.replace('useFont = metrics.useFont;',
                'useFont = metrics.useFont != 0;')
            scoped=changed.replace('    s32 useFont;\n','').replace(
                '                    useFont = 0;', '                    {\n                    s32 useFont = 0;').replace(
                '                }\n            } while (text[index] != 0);',
                '                    }\n                }\n            } while (text[index] != 0);')
            yield 'flag-scope-post-normalize',scoped
            yield 'flag-scope-post-normalize-unsigned',scoped.replace('s32 useFont = 0;', 'u32 useFont = 0;')
            yield 'flag-scope-post-normalize-register',scoped.replace('s32 useFont = 0;', 'register s32 useFont = 0;')
            reused=changed.replace('    u8 glyph;\n','').replace('    s32 extent;',
                '    u8 *base = text;\n    s32 extent;').replace('text[index]','base[index]').replace(
                'glyph = func_15042C40(base[index]);', 'text = (u8 *)(u32)(u8)func_15042C40(base[index]);')
            for op in ('== 0x60','< 0xA1','>= 0xA8','< 0x100'):
                reused=reused.replace('glyph '+op,'(s32)text '+op)
            reused=reused.replace('func_150415E0(glyph,','func_150415E0((s32)text,').replace('[glyph *','[(s32)text *')
            yield 'capture-reuse-typed-parameter',reused
    state_split=state_index.replace('s32 extent;',
        's32 extent;\n    s32 fontHeight;').replace(
        'extent = D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1];',
        'fontHeight = D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1];').replace(
        'if (extent >= lineHeight)', 'if (fontHeight >= lineHeight)').replace(
        'lineHeight = extent;\n                        }', 'lineHeight = fontHeight;\n                        }')
    yield 'metrics-state-indexed-early-split',state_split
    for name,body in (('state',state_index),('state-split',state_split),('captured',captured)):
        remat=body.replace('    s32 extent;', '    u8 **fontAddress = &D_80085994;\n    s32 extent;').replace(
            'D_80085994[glyph *','(*fontAddress)[glyph *')
        yield 'remat-metrics-'+name+'-before',remat
        yield 'remat-metrics-'+name+'-after',remat.replace('    u8 **fontAddress = &D_80085994;\n','').replace(
            'width, useFont; } metrics;', 'width, useFont; } metrics;\n    u8 **fontAddress = &D_80085994;')
    fields=BASE
    for suffix,name in (('', 'left'),(' + 1','top'),(' + 2','right'),(' + 3','bottom')):
        fields=fields.replace('D_80085994[glyph * 4'+suffix+']','D_80085994[glyph].'+name)
    yield 'record-fields',fields
    integer_address=BASE
    for suffix,index in (('',0),(' + 1',1),(' + 2',2),(' + 3',3)):
        integer_address=integer_address.replace('D_80085994[glyph * 4'+suffix+']',
            '((u8 *)(D_80085994 + (u32)glyph * 4))['+str(index)+']')
    yield 'integer-font-address',integer_address
    yield 'volatile-text',BASE.replace('u8 *text','volatile u8 *text').replace('u8 *cursor;', 'volatile u8 *cursor;')
    yield 'volatile-text-index',BASE.replace('u8 *text','volatile u8 *text').replace('u8 *cursor;', 'volatile u8 *cursor;').replace(
        '        cursor = text;\n        if (*text != 0) {', '        glyph = 0;\n        if (*text != 0) {\n            cursor = text + glyph;')
    for mask in range(16):
        body=BASE
        if mask&1:
            body=body.replace('    s32 useFont;', '    s32 useFont;\n    s32 savedFont;').replace(
                '                            func_150415E0(', '                            savedFont = useFont;\n                            func_150415E0(').replace(
                '                            *width = (s32)((f32)*width', '                            useFont = savedFont;\n                            *width = (s32)((f32)*width')
        if mask&2:
            body=body.replace('    u8 glyph;', '    s32 glyph;\n    s32 result;\n    s32 classification;').replace(
                '                    glyph = func_15042C40(*cursor);', '                    result = func_15042C40(*cursor);\n                    classification = result & 0xFF;\n                    glyph = result & 0xFF;')
            for op in ('== 0x60','< 0xA1','>= 0xA8','< 0x100'):
                body=body.replace('glyph '+op, 'classification '+op)
        if mask&4:
            body=body.replace('    s32 extent;', '    s32 extent;\n    s32 offset;\n    u8 *row;').replace(
                '                        *width = (s32)((u32)*width + D_80085994[glyph * 4] +\n                            D_80085994[glyph * 4 + 2] - 1);\n                        extent = D_80085994[glyph * 4 + 3] + D_80085994[glyph * 4 + 1];',
                '                        offset = glyph * 4;\n                        row = D_80085994 + offset;\n                        *width = (s32)((u32)*width + row[0] + row[2] - 1);\n                        row = D_80085994 + offset;\n                        extent = row[3] + row[1];')
        if mask&8:
            body=body.replace('    s32 extent;', '    s32 extent;\n    u8 current;\n    u8 command;').replace(
                '        if (*text != 0) {\n            do {', '        if (*text != 0) {\n            current = *cursor;\n            command = current;\n            do {').replace(
                'if (*cursor == 0xBC)', 'if (command == 0xBC)').replace('func_15042C40(*cursor)', 'func_15042C40(current)').replace(
                '            } while (*cursor != 0);', '                current = *cursor;\n                command = current;\n            } while (current != 0);')
        yield 'lifetimes-'+str(mask),body


def compile_candidate(root,out,name,body=SELECTED,profile='owner',declarations=DECLARATIONS):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=declarations,SYMBOLS=SYMBOLS,PROFILES=PROFILES):
        meta,words=compiler.compile_candidate(root,out,name,body,profile)
    frames=[(-w)&65535 for w in words if w&0xFFFF0000==0x27BD0000 and w&0x8000]
    meta['frame']=frames[0] if frames else 0
    return meta,words


def trace_ugen(root,out,name,body):
    meta,_=compile_candidate(root,out,name+'-baseline',body)
    obj=out/(name+'-trace.o')
    obj.unlink(missing_ok=True)
    command=['ido/ido5.3_recomp/cc','-c','-32','-G','0','-Xfullwarn','-Xcpluscomm',
        '-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-mips2','-o32',
        '-I','conker/include','-I','conker/include/2.0L','-I','conker/include/2.0L/PR',
        '-I','conker/include/libc','-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32',
        *PROFILES['owner'],'-Wc,-d','-o',str(obj.relative_to(root)),
        str((out/(name+'-baseline.c')).relative_to(root))]
    result=subprocess.run(command,cwd=root,capture_output=True,text=True)
    log=result.stdout+result.stderr
    (out/(name+'-ugen.txt')).write_text(log)
    record=dict(name=name,exit_code=result.returncode,bytes=len(log.encode()),baseline=meta,code_unchanged=False)
    receipt=out/(name+'-trace.json')
    receipt.write_text(json.dumps(record,indent=2)+'\n')
    if result.returncode or not log or not obj.is_file():
        raise ValueError('UGEN trace failed, empty or missing object: '+name)
    baseline=out/(name+'-baseline.o')
    before,after=compiler.sections(baseline),compiler.sections(obj)
    if compiler.parse_object(baseline)!=compiler.parse_object(obj) or any(
            before.get(section)!=after.get(section) for section in ('.rodata','.data')):
        raise ValueError('UGEN diagnostic changed code, relocations or pools: '+name)
    record['code_unchanged']=True
    receipt.write_text(json.dumps(record,indent=2)+'\n')
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='selected')
    parser.add_argument('--profiles',action='store_true')
    parser.add_argument('--allocation',action='store_true')
    parser.add_argument('--allocation-pairs',action='store_true')
    parser.add_argument('--trace-ugen',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-text-measurer';records=[]
    for name,body in candidates():
        if args.filter and args.filter not in name:continue
        if args.trace_ugen:
            trace=root/'conker/build/game-text-measurer-ugen-trace-20261012';trace.mkdir(exist_ok=True)
            record=trace_ugen(root,trace,name,body)
            print(name,'trace exit',record['exit_code'],'bytes',record['bytes'],flush=True)
            continue
        for profile in (('owner','o2g3','o2','o1g3','o1') if args.profiles else ('owner',)):
            declarations=DECLARATIONS.replace('extern u8 *D_80085994;', 'extern u8 *D_80085994[1];') if name=='array-pointer' else DECLARATIONS
            if name=='record-fields':
                declarations=declarations.replace('extern u8 *D_80085994;',
                    'typedef struct { u8 left, top, right, bottom; } GlyphMetrics;\nextern GlyphMetrics *D_80085994;')
            if name=='integer-font-address':declarations=declarations.replace('extern u8 *D_80085994;', 'extern u32 D_80085994;')
            meta,_=compile_candidate(root,out,name+'-'+profile,body,profile,declarations);records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],meta['pool_bytes'],flush=True)
        if args.allocation:
            for option in ('no_const_in_reg','do_opt_saved_regs','norlodrstropt','nordstore','noprecolor','noheurAB','no_r23','nogenvreg','docopy'):
                profile='allocation-'+option
                with patch.dict(PROFILES,{profile:PROFILES['owner']+('-Wo,-'+option,)}):
                    meta,_=compile_candidate(root,out,name+'-'+profile,body,profile,declarations)
                records.append(meta)
                print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],meta['pool_bytes'],flush=True)
        if args.allocation_pairs:
            for options in (('no_const_in_reg','do_opt_saved_regs'),('no_const_in_reg','no_r23'),
                    ('no_const_in_reg','noprecolor')):
                profile='allocation-'+'-'.join(options)
                with patch.dict(PROFILES,{profile:PROFILES['owner']+tuple('-Wo,-'+opt for opt in options)}):
                    meta,_=compile_candidate(root,out,name+'-'+profile,body,profile,declarations)
                records.append(meta)
                print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],meta['pool_bytes'],flush=True)
    if not args.trace_ugen:
        (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
