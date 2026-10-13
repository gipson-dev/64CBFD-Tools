"""Recover both actor command channels without changing the owner profile."""
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments.game_actor_type_dispatch_candidates import compile_owner

ENTRY, ROM, WORDS = 0x15034860, 0x61D10, 405
FUNCTION, SOURCE = 'func_15034860', 'conker/src/game/generated_61D10.c'
SYMBOLS = dict(func_150ADA20=0x150ADA20, D_800BE9E4=0x800BE9E4,
    D_800C3EF0=0x800C3EF0, **{'D_%08X' % a:a for a in range(0x80097D40,0x80097D60,4)})
DECLARATIONS = '''s32 func_150ADA20(void);
f32 fabsf(f32);
#pragma intrinsic (fabsf)
extern s32 D_800BE9E4;
extern s16 D_800C3EF0;
extern f32 D_80097D40, D_80097D44, D_80097D48, D_80097D4C;
extern f32 D_80097D50, D_80097D54, D_80097D58, D_80097D5C;
'''
ORIGINAL = 's32 func_15034860() {\n    return 0;\n}'
SELECTED = '''s32 func_15034860(u8 *output, u8 *actor, s32 first, s32 second) {
    s32 suppressed;
    s32 primaryBias;
    s32 secondaryBias;
    s32 noise;
    s32 limit;
    s32 lower;
    s32 upper;
    s32 sign;
    s32 choose;
    s32 reverse;
    s32 current;
    s32 delta;
    s16 value;
    f32 scale;
    f32 magnitude;
    s32 type = actor[4];

    if (type == 0x70) {
        suppressed = 1;
    } else {
        suppressed = 0;
    }
    if (type == 0x7C) {
        primaryBias = 4;
        secondaryBias = 0;
    } else {
        primaryBias = 0;
        secondaryBias = 2;
    }
    if (type == 0x69 || type == 0x7C || type == 0x87) {
        noise = 0;
    } else {
        noise = 10;
    }
    limit = 0xFF;
    lower = 40;
    if (first != limit) {
        if (actor[0x201] == 0) {
            scale = D_80097D40;
        } else {
            scale = (f32)(u32)actor[0x201] * D_80097D44;
        }
        value = (s32)((f32)(u32)actor[0x1FE] * scale * D_80097D48);
        if (!suppressed) {
            *(s16 *)output = (u32)first * 6 + primaryBias;
            *(s16 *)(output + 2) = value;
            output += 4;
        }
        D_800C3EF0 = value;
        value = (s32)((f32)(*(s8 *)(actor + 0x202) * actor[0x1FE] / limit)
            * D_80097D4C * D_80097D50);
        if (!suppressed) {
            *(s16 *)output = (u32)first * 6 + secondaryBias;
            *(s16 *)(output + 2) = value;
            output += 4;
        }
        upper = 60;
        if (actor[4] == 0x42) {
            lower = 80;
            upper = 120;
        }
        if (actor[0x1FF] == 0) {
            *(s8 *)(actor + 0x203) = -upper;
        } else if (actor[0x1FF] == 2) {
            *(s8 *)(actor + 0x203) = upper;
            *(s8 *)(actor + 0x202) = 0;
        } else {
            if (*(s8 *)(actor + 0x203) == 0 ||
                actor[0x1FE] == 0 || actor[0x1FE] == limit) {
                *(s8 *)(actor + 0x203) =
                    (u32)func_150ADA20() % (upper - lower) + lower;
                if (actor[0x1FE] == limit) {
                    *(s8 *)(actor + 0x203) = -*(s8 *)(actor + 0x203);
                } else if (actor[0x1FE] == 0 && noise != 0) {
                    *(s8 *)(actor + 0x202) =
                        (u32)func_150ADA20() % (noise * 2) - noise;
                }
            }
        }
        value = actor[0x1FE] + *(s8 *)(actor + 0x203);
        if (value < 0) {
            value = 0;
        } else {
            value = value < 256 ? value : limit;
        }
        actor[0x1FE] = value;
        if (actor[0x1FF] == 3) {
            if (actor[0x200] >= D_800BE9E4) {
                actor[0x200] = (u32)actor[0x200] - (u32)D_800BE9E4;
            } else {
                actor[0x200] = 0;
                actor[0x1FF] = 0;
            }
        }
    }
    if (second != limit) {
        if (*(s8 *)(actor + 0x208) == 0) {
            scale = D_80097D54;
        } else {
            scale = (f32)*(s8 *)(actor + 0x208) * D_80097D58;
        }
        sign = 1;
        if (scale < 0.0f) {
            sign = -1;
        }
        magnitude = fabsf(scale);
        delta = (s32)((f32)*(s16 *)(actor + 0x204) * magnitude * D_80097D5C);
        *(s16 *)output = (u32)second * 6 + primaryBias;
        *(s16 *)(output + 2) = -delta;
        output += 4;
        choose = 0;
        reverse = 0;
        if (actor[0x206] == 0) {
            *(s8 *)(actor + 0x209) = sign > 0 ? -60 : 60;
        } else if (actor[0x206] == 2) {
            *(s8 *)(actor + 0x209) = sign > 0 ? 60 : -60;
        } else {
            delta = *(s8 *)(actor + 0x209);
            if (delta == 0) {
                choose = 1;
            } else {
                current = *(s16 *)(actor + 0x204);
                if (sign > 0) {
                    if (current < 0 && delta < 0) {
                        reverse = 1;
                    } else if (current == 0 && delta < 0) {
                        choose = 1;
                    } else if (current == limit) {
                        reverse = 1;
                        choose = 1;
                    }
                } else {
                    if (current > 0 && delta > 0) {
                        reverse = 1;
                    } else if (current == 0 && delta > 0) {
                        choose = 1;
                    } else if (current == -255) {
                        reverse = 1;
                        choose = 1;
                    }
                }
            }
        }
        if (choose) {
            *(s8 *)(actor + 0x209) = (u32)func_150ADA20() % 20 + 40;
            *(s8 *)(actor + 0x209) = *(s8 *)(actor + 0x209) * sign;
        }
        if (reverse) {
            *(s8 *)(actor + 0x209) = -*(s8 *)(actor + 0x209);
        }
        delta = *(s8 *)(actor + 0x209);
        *(s16 *)(actor + 0x204) += delta;
        current = *(s16 *)(actor + 0x204);
        if (sign > 0) {
            if (current < 0 && delta < 0) {
                *(s16 *)(actor + 0x204) = 0;
            } else if (current >= 256) {
                *(s16 *)(actor + 0x204) = limit;
            }
        } else {
            if (current > 0 && delta > 0) {
                *(s16 *)(actor + 0x204) = 0;
            } else if (current < -255) {
                *(s16 *)(actor + 0x204) = -255;
            }
        }
        if (actor[0x206] == 3) {
            if (actor[0x207] >= D_800BE9E4) {
                actor[0x207] = (u32)actor[0x207] - (u32)D_800BE9E4;
            } else {
                actor[0x207] = 0;
                actor[0x206] = 0;
            }
        }
    }
    return (s32)output;
}'''


def recovered_owner(source):
    if source.count(ORIGINAL) == 1:
        source = source.replace(ORIGINAL, SELECTED)
    elif source.count(SELECTED) != 1:
        raise ValueError('Expected the known placeholder or recovered finalizer')
    if DECLARATIONS not in source:
        source = source.replace('#include <ultra64.h>\n', '#include <ultra64.h>\n\n'+DECLARATIONS, 1)
    return source


def compile_candidate(root, out, name, body=None):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD='', DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root,out,name,SELECTED if body is None else body)


def candidates():
    yield 'selected',SELECTED
    yield 'unsigned-type',SELECTED.replace('s32 type =','u32 type =')
    yield 'byte-type',SELECTED.replace('s32 type =','u8 type =')
    yield 'u32-byte-scale',SELECTED.replace('(f32)(u32)actor[0x201]','(f32)actor[0x201]').replace(
        '(f32)(u32)actor[0x1FE]','(f32)actor[0x1FE]')
    yield 'split-tail-read',SELECTED.replace('        current = *(s16 *)(actor + 0x204);\n        delta = *(s8 *)(actor + 0x209);',
        '        delta = *(s8 *)(actor + 0x209);\n        current = *(s16 *)(actor + 0x204);')
    for qualifier in ('volatile s32','u32','volatile u32'):
        yield qualifier.replace(' ','-')+'-first',SELECTED.replace('s32 first,',qualifier+' first,')
    for original,replacement,label in (
            ('    limit = 0xFF;\n    lower = 40;','    limit = 0xFF;','late-lower'),
            ('        value = value < 256 ? value : limit;','        current = value < 256 ? value : limit;\n        value = current;','clamp-local'),
            ('type == 0x69 || type == 0x7C || type == 0x87','type != 0x69 && type != 0x7C && type != 0x87','noise-inverted')):
        body=SELECTED.replace(original,replacement)
        if label=='late-lower':
            body=body.replace('        upper = 60;','        lower = 40;\n        upper = 60;')
        if label=='noise-inverted':
            body=body.replace('        noise = 0;\n    } else {\n        noise = 10;',
                '        noise = 10;\n    } else {\n        noise = 0;')
        yield label,body
        yield label+'-volatile-first',body.replace('s32 first,','volatile s32 first,')


def main():
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-command-finalizer'
    out.mkdir(exist_ok=True)
    records=[]
    for name,body in candidates():
        record,_=compile_candidate(root,out,name,body)
        records.append(record)
        print(name,record['body_words'],hex(record['frame']),record['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
