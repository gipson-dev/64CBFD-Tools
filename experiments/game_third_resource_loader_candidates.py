"""Screen source shapes for the lazy third loader; none is qualified direct C."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY,ROM,WORDS=0x1503D774,0x6AC24,36
FUNCTION,SOURCE='func_1503D774','conker/src/game/generated_6A3D0.c'
DECLARATIONS='''#include "structs.h"
extern struct124 *D_800D1C90[];
void *func_1502B6BC(s32 *, s32, s32 *, s32, ...);
'''
SYMBOLS=dict(D_800D1C90=0x800D1C90,func_1502B6BC=0x1502B6BC)
PROFILES=dict(compiler.PROFILES,owner=('-O2','-g3','-Wo,-loopunroll,0'),retail=('-O2','-g3'))
ORIGINAL='''s32 func_1503D774(s32 arg0, s32 arg1) {
    s32 output;
    struct124 **slot = &D_800D1C90[arg0];
    void *loaded;

    if (*slot != NULL) {
        return 0;
    }

    loaded = func_1502B6BC(&output, 2, 0, 2, 0x11, arg0);
    if (loaded == 0) {
        *slot = NULL;
        return 2;
    }

    *slot = (struct124 *)loaded;
    *slot = *(struct124 **)loaded;
    return 0;
}'''


def candidates():
    yield 'banked',ORIGINAL
    declarations=('    s32 output;','    struct124 **slot = &D_800D1C90[arg0];','    void *loaded;')
    for kind in ('void *','struct124 *','struct124 **','u32 *','u8 *'):
        for index,order in enumerate(itertools.permutations(declarations)):
            body=ORIGINAL.replace('\n'.join(declarations),'\n'.join(order)).replace('void *loaded;',kind+'loaded;')
            yield 'typed-'+kind.replace(' ','').replace('*','p')+'-layout-'+str(index),body
    yield 'returned-slot',ORIGINAL.replace('void *loaded;', 'struct124 **loaded;').replace(
        '*slot = *(struct124 **)loaded;', '*slot = *loaded;')
    yield 'direct-slot-request',ORIGINAL.replace('    void *loaded;\n','').replace(
        '    loaded = func_1502B6BC', '    *slot = func_1502B6BC').replace(
        'if (loaded == 0)','if (*slot == NULL)').replace('    *slot = (struct124 *)loaded;\n','').replace(
        '*(struct124 **)loaded','*(struct124 **)*slot')
    yield 'return-expression',ORIGINAL.replace('    *slot = *(struct124 **)loaded;\n    return 0;',
        '    return (*slot = *(struct124 **)loaded, 0);')
    success=ORIGINAL.replace('    if (loaded == 0) {\n        *slot = NULL;\n        return 2;\n    }\n\n'
        '    *slot = (struct124 *)loaded;\n    *slot = *(struct124 **)loaded;\n    return 0;',
        '    if (loaded != NULL) {\n        *slot = (struct124 *)loaded;\n        *slot = *(struct124 **)loaded;\n'
        '        return 0;\n    }\n    *slot = NULL;\n    return 2;')
    yield 'success-first',success
    for kind in ('register void *','register struct124 *','register struct124 **'):
        yield 'success-'+kind.replace(' ','').replace('*','p'),success.replace('void *loaded;',kind+'loaded;')
    yield 'slot-read-success',success.replace('*(struct124 **)loaded','*(struct124 **)*slot')
    assigned=ORIGINAL.replace('loaded = func_1502B6BC','*slot = loaded = func_1502B6BC').replace(
        '        *slot = NULL;\n','').replace('    *slot = (struct124 *)loaded;\n','')
    yield 'publish-request',assigned
    yield 'status-argument',success.replace('        return 0;\n    }\n    *slot = NULL;\n    return 2;',
        '        arg1 = 0;\n    } else {\n        *slot = NULL;\n        arg1 = 2;\n    }\n    return arg1;')
    for body_name,body in (('success',success),('banked',ORIGINAL)):
        yield body_name+'-goto',body.replace('return 0;','goto done;').replace('\n}', '\ndone:\n    return 0;\n}')
        yield body_name+'-register-slot',body.replace('struct124 **slot','register struct124 **slot')
        yield body_name+'-integer-loaded',body.replace('void *loaded;','s32 loaded;').replace(
            'loaded = func_1502B6BC','loaded = (s32)func_1502B6BC')
    yield 'status-join',ORIGINAL.replace('    void *loaded;', '    void *loaded;\n    s32 status;').replace(
        '        return 2;\n    }\n\n    *slot = (struct124 *)loaded;\n    *slot = *(struct124 **)loaded;\n    return 0;',
        '        status = 2;\n    } else {\n        *slot = (struct124 *)loaded;\n        *slot = *(struct124 **)loaded;\n'
        '        status = 0;\n    }\n    return status;')
    yield 'failure-goto',ORIGINAL.replace('        return 2;','        goto failure;').replace(
        '\n}', '\nfailure:\n    return 2;\n}')
    yield 'cached-slot-value',ORIGINAL.replace('*(struct124 **)loaded','*(struct124 **)*slot')
    yield 'test-published-local',ORIGINAL.replace('if (loaded == 0)','if ((struct124 *)loaded == NULL)')
    for size in ('s32 output[2];','u64 output;','struct { s32 unused; s32 value; } output;'):
        yield 'output-'+str(len(size)),ORIGINAL.replace('s32 output;',size).replace('&output,',
            'output + 1,' if '[' in size else '&output.value,' if 'struct' in size else '(s32 *)&output + 1,')
    for location in range(4):
        parts=list(declarations);parts.insert(location,'    s32 unused;')
        yield 'unused-declaration-'+str(location),ORIGINAL.replace('\n'.join(declarations),'\n'.join(parts))
    inline=ORIGINAL.replace('    loaded = func_1502B6BC(&output, 2, 0, 2, 0x11, arg0);\n    if (loaded == 0)',
        '    if ((loaded = func_1502B6BC(&output, 2, 0, 2, 0x11, arg0)) == NULL)')
    yield 'inline-condition',inline
    yield 'negative-inverted-result-gate',ORIGINAL.replace('loaded == 0','loaded != NULL')
    for expression in ('!loaded','(s32)loaded == 0','loaded == NULL','!!loaded == 0'):
        yield 'gate-'+expression.replace(' ','').replace('*','p'),ORIGINAL.replace('loaded == 0',expression)
    nested=ORIGINAL.replace('    void *loaded;\n','').replace(
        '    loaded = func_1502B6BC', '    {\n    void *loaded;\n    loaded = func_1502B6BC').replace(
        '\n}', '\n    }\n}')
    yield 'nested-local',nested
    yield 'constant-status',ORIGINAL.replace('    void *loaded;', '    void *loaded;\n    s32 status = 0;').replace(
        'return 0;', 'return status;')
    yield 'value-spill',ORIGINAL.replace('void *loaded;', 'volatile void *loaded;')
    yield 'volatile-pointer',ORIGINAL.replace('void *loaded;', 'void *volatile loaded;')
    yield 'null-else',ORIGINAL.replace('    *slot = (struct124 *)loaded;', '    else {\n    *slot = (struct124 *)loaded;').replace(
        '\n}', '\n    }\n}')
    labelled=ORIGINAL.replace('    if (loaded == 0) {\n        *slot = NULL;\n        return 2;\n    }',
        '    if (loaded != NULL) {\n        goto loaded_block;\n    }\n    *slot = NULL;\n    return 2;\nloaded_block:')
    yield 'labelled-success',labelled
    yield 'labelled-success-void',labelled.replace('return 2;', 'arg1 = 2;\n    goto done;').replace(
        '    return 0;\n}', '    arg1 = 0;\ndone:\n    return arg1;\n}')
    for first,second in (('==','!='),('!=','==')):
        yield 'two-conditions-'+first,ORIGINAL.replace('loaded == 0','loaded '+first+' NULL').replace(
            '        return 2;\n    }', '    }').replace('    *slot = (struct124 *)loaded;',
            '    if (loaded '+second+' NULL) {\n    *slot = (struct124 *)loaded;').replace(
            '    return 0;\n}', '    }\n    return loaded == NULL ? 2 : 0;\n}')
    outer=ORIGINAL.replace('    if (*slot != NULL) {\n        return 0;\n    }\n\n',
        '    if (*slot == NULL) {\n').replace('    return 0;\n}', '    }\n    return 0;\n}')
    yield 'outer-null',outer
    yield 'outer-null-else',outer.replace('    *slot = (struct124 *)loaded;', '    else {\n    *slot = (struct124 *)loaded;').replace(
        '    }\n    return 0;\n}', '    }\n    }\n    return 0;\n}')
    yield 'failure-comma',ORIGINAL.replace('        *slot = NULL;\n        return 2;', '        return (*slot = NULL, 2);')
    yield 'return-arg0',ORIGINAL.replace('    return 0;\n}', '    arg0 = 0;\n    return arg0;\n}')
    integer=ORIGINAL.replace('struct124 **slot = &D_800D1C90[arg0];',
        'u32 *slot = (u32 *)&D_800D1C90[arg0];').replace('void *loaded;','u32 loaded;').replace(
        '*slot != NULL','*slot != 0').replace('loaded = func_1502B6BC','loaded = (u32)func_1502B6BC').replace(
        '*slot = NULL','*slot = 0').replace('*slot = (struct124 *)loaded','*slot = loaded').replace(
        '*(struct124 **)loaded','*(u32 *)loaded')
    yield 'integer-slot',integer
    yield 'integer-slot-published',integer.replace('    loaded = (u32)func_1502B6BC','    *slot = loaded = (u32)func_1502B6BC')
    yield 'integer-slot-cached',integer.replace('*(u32 *)loaded','*(u32 *)*slot')
    yield 'incoming-loaded',ORIGINAL.replace('    void *loaded;\n','').replace('loaded = func_1502B6BC',
        'arg0 = (s32)func_1502B6BC').replace('loaded == 0','arg0 == 0').replace(
        '(struct124 *)loaded','(struct124 *)arg0').replace('*(struct124 **)loaded','*(struct124 **)arg0')
    reuse=labelled.replace('    return 2;\nloaded_block:', '    loaded = (void *)2;\n    goto done;\nloaded_block:').replace(
        '    return 0;\n}', '    loaded = NULL;\ndone:\n    return (s32)loaded;\n}')
    yield 'result-status-reuse',reuse
    yield 'result-status-reuse-integer',reuse.replace('void *loaded;','s32 loaded;').replace(
        'loaded = func_1502B6BC','loaded = (s32)func_1502B6BC').replace('loaded != NULL','loaded != 0').replace(
        'loaded = (void *)2','loaded = 2').replace('loaded = NULL','loaded = 0')
    yield 'result-status-reuse-register',reuse.replace('void *loaded;','register void *loaded;')


def compile_candidate(root,out,name,body=ORIGINAL,profile='owner'):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS,PROFILES=PROFILES):
        meta,words=compiler.compile_candidate(root,out,name,body,profile)
    frames=[(-word)&65535 for word in words if word&0xFFFF0000==0x27BD0000 and word&0x8000]
    meta['frame']=frames[0] if frames else 0
    return meta,words


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='banked');parser.add_argument('--profiles',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-third-resource-loader';records=[]
    for name,body in candidates():
        if args.filter and args.filter not in name: continue
        for profile in ('owner','retail') if args.profiles else ('owner',):
            meta,words=compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta);print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
