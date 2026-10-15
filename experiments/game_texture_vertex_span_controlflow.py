"""Complete control-flow fits of the recovered-home texture vertex scanner."""
import argparse
import json
import itertools
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_texture_vertex_span_fit as fit
from tools.experiments import game_text_measurer_candidates as standalone
from tools.experiments import game_texture_vertex_span as source

BUILD=fit.BUILD+'/controlflow'


def variants():
    body=fit.HOMES
    yield 'homes',body
    yield 'while',body.replace('    for (;;) {','    while (1) {',1)
    do=body.replace('    for (;;) {','    do {',1).replace('        commands++;\n    }',
        '        commands++;\n    } while (1);')
    yield 'do',do
    guarded=body.replace('        } else if (stage == 1) {',
        '            commands++;\n            continue;\n        }\n        if (stage == 1) {').replace(
        '        } else if (stage == 2) {','        }\n        if (stage == 2) {')
    yield 'guarded-states',guarded
    yield 'guarded-states-while',guarded.replace('    for (;;) {','    while (1) {',1)
    yield 'for-increment',body.replace('    for (;;) {','    for (;; commands++) {',1).replace(
        '            commands--;\n            continue;','            commands -= 2;\n            continue;').replace(
        '        commands++;\n    }','    }')
    preload=body.replace('    for (;;) {\n        opcode = *(s8 *)commands;',
        '    opcode = *(s8 *)commands;\n    for (;;) {').replace(
        '            commands--;\n            continue;',
        '            commands--;\n            opcode = *(s8 *)commands;\n            continue;').replace(
        '        commands++;\n    }','        commands++;\n        opcode = *(s8 *)commands;\n    }')
    yield 'preloaded-opcode',preload
    yield 'preloaded-opcode-while',preload.replace('    for (;;) {','    while (1) {',1)
    for label,text in (('homes',body),('guarded',guarded),('do',do)):
        yield label+'-explicit-entry-goto',text.replace('    for (;;) {',
            '    goto scan;\n    for (;;) {\nscan:',1).replace('    do {','    goto scan;\n    do {\nscan:',1)
        yield label+'-negative-state-tests',text.replace('if (stage == 0)',
            'if (!stage)').replace('if (stage == 1)','if (stage - 1 == 0)').replace(
            'if (stage == 2)','if (stage - 2 == 0)')
    increment=body.replace('                if (occurrence-- < 1) { stage++; }',
        '                if (occurrence < 1) { stage++; }\n                occurrence--;')
    yield 'explicit-occurrence-update',increment
    yield 'explicit-stage-values',body.replace('if (occurrence-- < 1) { stage++; }',
        'if (occurrence-- < 1) { stage = 1; }').replace('            stage++;','            stage = 2;')


def exit_type_variants():
    body=fit.HOMES
    local='            if (opcode == -33) { return 0; }\n'
    for label,condition in (('opcode-first','opcode == -33 && stage == 0'),
            ('stage-first','stage == 0 && opcode == -33')):
        text=body.replace(local,'').replace('        opcode = *(s8 *)commands;\n',
            '        opcode = *(s8 *)commands;\n        if ('+condition+') { return 0; }\n',1)
        yield label+'-empty-exit',text
        yield label+'-empty-exit-unsigned-constant',text.replace('opcode == -33','(u32)opcode == 0xFFFFFFDFu')
    joined=body.replace(local,'').replace('            if (opcode == -33) { break; }\n','').replace(
        '        opcode = *(s8 *)commands;\n','''        opcode = *(s8 *)commands;
        if (opcode == -33 && stage != 1) {
            if (stage == 0) { return 0; }
            if (stage == 2) { break; }
        }
''',1)
    yield 'joined-end-exit',joined
    yield 'joined-end-exit-unsigned-constant',joined.replace('opcode == -33','(u32)opcode == 0xFFFFFFDFu')
    yield 'unsigned-end-constant',body.replace('opcode == -33','(u32)opcode == 0xFFFFFFDFu')
    yield 'signed-byte-opcode',body.replace('    s32 opcode;','    s8 opcode;')
    yield 'unsigned-opcode-signed-nibble',body.replace('    s32 opcode;','    u32 opcode;').replace(
        '(opcode >> 4)','((s32)opcode >> 4)')


def gpr_variants():
    body=fit.HOMES
    for name in ('maximum','count','stage','minimum','nested','opcode'):
        yield 'register-'+name,body.replace('    s32 '+name+';','    register s32 '+name+';')
    yield 'register-max-count',body.replace('    s32 maximum;','    register s32 maximum;').replace(
        '    s32 count;','    register s32 count;')
    maximum=body.replace('maximum < indices[i]','indices[i] > maximum')
    minimum=body.replace('indices[i] < minimum','minimum > indices[i]')
    yield 'reversed-maximum-comparison',maximum
    yield 'reversed-minimum-comparison',minimum
    yield 'reversed-both-comparisons',maximum.replace('indices[i] < minimum','minimum > indices[i]')
    max_value=body.replace('                    if (maximum < indices[i]) { maximum = indices[i]; }',
        '                    opcode = indices[i];\n                    if (maximum < opcode) { maximum = opcode; }')
    min_value=body.replace('                        if (indices[i] < minimum) { minimum = indices[i]; }',
        '                        opcode = indices[i];\n                        if (opcode < minimum) { minimum = opcode; }')
    yield 'reuse-opcode-for-maximum',max_value
    yield 'reuse-opcode-for-minimum',min_value
    yield 'reuse-opcode-for-both',max_value.replace(
        '                        if (indices[i] < minimum) { minimum = indices[i]; }',
        '                        opcode = indices[i];\n                        if (opcode < minimum) { minimum = opcode; }')


def loop_variants():
    for shift_do,max_do,min_do,count_first in itertools.product((False,True),repeat=4):
        body=fit.HOMES
        if shift_do:
            for count in (3,6):
                before='''                    for (indexCursor = indices, indexEnd = indexCursor + %d; indexCursor < indexEnd; indexCursor++) {
                        *indexCursor >>= 1;
                    }'''%count
                after='''                    indexCursor = indices;
                    indexEnd = indexCursor + %d;
                    do {
                        *indexCursor >>= 1;
                        indexCursor++;
                    } while (indexCursor < indexEnd);'''%count
                assert before in body
                body=body.replace(before,after)
        if max_do:
            body=body.replace('''                for (i = 0; i < count; i++) {
                    if (maximum < indices[i]) { maximum = indices[i]; }
                }''','''                i = 0;
                if (count > 0) {
                    do {
                        if (maximum < indices[i]) { maximum = indices[i]; }
                        i++;
                    } while (i < count);
                }''')
        if min_do:
            body=body.replace('''                    for (i = 1; i < count; i++) {
                        if (indices[i] < minimum) { minimum = indices[i]; }
                    }''','''                    i = 1;
                    if (count > 1) {
                        do {
                            if (indices[i] < minimum) { minimum = indices[i]; }
                            i++;
                        } while (i < count);
                    }''')
        if count_first:
            for count in (3,6,12):
                body=body.replace('                    count = %d;\n'%count,'')
            body=body.replace('                if (opcode == 5) {',
                '                if (opcode == 5) {\n                    count = 3;').replace(
                '                } else if (opcode == 6) {','                } else if (opcode == 6) {\n                    count = 6;').replace(
                '                } else {\n                    indices[0] = (commands->words.w1 >> 25)',
                '                } else {\n                    count = 12;\n                    indices[0] = (commands->words.w1 >> 25)')
        yield 'loops-%d%d%d%d'%(shift_do,max_do,min_do,count_first),body


MAXIMUM_LOOP='''                i = 0;
                if (count > 0) {
                    minimum = count & 3;
                    if (minimum != 0) {
                        indexCursor = indices;
                        do {
                            opcode = *indexCursor;
                            i++;
                            if (maximum < opcode) { maximum = opcode; }
                            indexCursor++;
                        } while (minimum != i);
                        if (i == count) { goto maximum_done; }
                    }
                    indexEnd = indices + count;
                    indexCursor = indices + i;
                    do {
                        opcode = indexCursor[0];
                        if (maximum < opcode) { maximum = opcode; }
                        opcode = indexCursor[1];
                        if (maximum < opcode) { maximum = opcode; }
                        opcode = indexCursor[2];
                        if (maximum < opcode) { maximum = opcode; }
                        opcode = indexCursor[3];
                        indexCursor += 4;
                        if (maximum < opcode) { maximum = opcode; }
                    } while (indexCursor != indexEnd);
                }
maximum_done:;'''
MINIMUM_LOOP='''                    i = 1;
                    if (count >= 2) {
                        foundVertex = (count - 1) & 3;
                        if (foundVertex != 0) {
                            indexCursor = indices + i;
                            do {
                                opcode = *indexCursor;
                                i++;
                                if (opcode < minimum) { minimum = opcode; }
                                indexCursor++;
                            } while (foundVertex + 1 != i);
                            if (i == count) { goto minimum_done; }
                        }
                        indexCursor = indices + i;
                        indexEnd = indices + count;
                        do {
                            opcode = indexCursor[0];
                            if (opcode < minimum) { minimum = opcode; }
                            opcode = indexCursor[1];
                            if (opcode < minimum) { minimum = opcode; }
                            opcode = indexCursor[2];
                            if (opcode < minimum) { minimum = opcode; }
                            opcode = indexCursor[3];
                            indexCursor += 4;
                            if (opcode < minimum) { minimum = opcode; }
                        } while (indexCursor != indexEnd);
                    }
minimum_done:;'''


def unrolled_variants():
    maximum='''                for (i = 0; i < count; i++) {
                    if (maximum < indices[i]) { maximum = indices[i]; }
                }'''
    minimum='''                    for (i = 1; i < count; i++) {
                        if (indices[i] < minimum) { minimum = indices[i]; }
                    }'''
    for max_loop,min_loop in ((True,False),(False,True),(True,True)):
        body=fit.HOMES
        if max_loop:
            body=body.replace(maximum,MAXIMUM_LOOP)
        if min_loop:
            body=body.replace(minimum,MINIMUM_LOOP)
        yield 'explicit-four-way-%d%d'%(max_loop,min_loop),body


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--exit-types',action='store_true')
    group.add_argument('--gpr-shapes',action='store_true')
    group.add_argument('--loops',action='store_true')
    group.add_argument('--unrolled',action='store_true')
    parser.add_argument('--no-unroll',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/BUILD
    out.mkdir(exist_ok=True)
    rows=[]
    forms=unrolled_variants() if args.unrolled else loop_variants() if args.loops else gpr_variants() if args.gpr_shapes else exit_type_variants() if args.exit_types else variants()
    for label,body in forms:
        if args.no_unroll:
            label+='-no-unroll'
            profiles=dict(standalone.PROFILES,owner=('-O2','-g3','-Wo,-loopunroll,0'))
            with patch.multiple(standalone,ENTRY=source.ENTRY,ROM=source.ROM,WORDS=source.WORDS,
                    FUNCTION=source.FUNCTION,SYMBOLS=dict(D_800B0E58=0x800B0E58,func_1510D0EC=0x1510D0EC),
                    PROFILES=profiles):
                row,words=standalone.compile_candidate(root,out,label,body,declarations=source.DECLARATIONS)
            row.update(label=label,bytes=len(words)*4,private_profile=list(profiles['owner']))
        else:
            row,words,_=fit.measure(root,out,label,body)
        row['setup_words']=[hex(w) for w in words[15:25]]
        rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k!='diff_offsets'}),flush=True)
    filename='unrolled-screens.json' if args.unrolled else 'loop-screens.json' if args.loops else 'gpr-screens.json' if args.gpr_shapes else 'exit-type-screens.json' if args.exit_types else 'screens.json'
    if args.no_unroll:
        filename='private-no-unroll-'+filename
    (out/filename).write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    main()
