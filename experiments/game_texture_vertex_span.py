"""Private reconstruction of the selected-texture display-list vertex span."""
import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments import game_view_matrix_pass as previous
from tools.tests import view_matrix_pass_checkpoint as checkpoint

BUILD='conker/build/game-texture-vertex-span'
OWNER,FUNCTION,ENTRY,ROM,WORDS=previous.OWNER,'func_1510BF60',0x1510BF60,0x139410,339
PATHS=dict(previous.PATHS,product_assembly=previous.ASSEMBLY,
    resolver_owner='conker/src/game/generated_139FC0.c',resolver_original='conker/asm/139FC0.s')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,product_assembly=checkpoint.ASSEMBLY,
    resolver_owner='92acd2ba087d8762add65d1d93d9960a91f9cca7c544eaa695b99fa15aab23e0',
    resolver_original='bff80847aaa7145696f6e95b1a54559e67f6bcdb371482b674e6908a73198bd7')
DECLARATIONS='''extern u32 D_800B0E58[];
u32 func_1510D0EC(s32 id, s32 *extent, s32 priority, s32 retain);
'''
BODY='''/* Find the contiguous vertex span used by one texture occurrence. */
s32 func_1510BF60(Gfx *commands, s32 resource, u32 *firstVertex, s32 occurrence) {
    s32 extent;
    u32 vertexBase;
    s32 indices[12];
    s32 *indexCursor;
    s32 count;
    s32 i;
    s32 opcode;
    s32 stage;
    s32 maximum;
    s32 nested;
    s32 trimFirst;
    s32 foundVertex;
    s32 minimum;

    func_1510D0EC(resource, &extent, 3, 0);
    *firstVertex = 0;
    stage = 0;
    maximum = 0;
    nested = 0;
    trimFirst = 0;
    for (;;) {
        opcode = *(s8 *)commands;
        if (stage == 0) {
            if (opcode == -33) { return 0; }
            if (opcode == -3 && commands->words.w1 == D_800B0E58[resource]) {
                if (occurrence-- < 1) { stage++; }
            }
        } else if (stage == 1) {
            foundVertex = 0;
            while (opcode != 5 && opcode != 6 && (opcode >> 4) != 1) {
                if (opcode == 1) { foundVertex = 1; break; }
                commands++;
                opcode = *(s8 *)commands;
            }
            stage++;
            if (!foundVertex) {
                trimFirst = 1;
                while (opcode != 1) {
                    if (opcode == -3) { nested--; }
                    commands--;
                    opcode = *(s8 *)commands;
                }
            }
            commands--;
            continue;
        } else if (stage == 2) {
            if (opcode == -33) { break; }
            if (opcode == -3) {
                nested++;
                if (nested > 0) { break; }
            } else if (opcode == 1) {
                vertexBase = commands->words.w1;
                maximum = 0;
                if (*firstVertex == 0 || vertexBase < *firstVertex) {
                    *firstVertex = vertexBase;
                }
            } else if (opcode == 5 || opcode == 6 || (opcode >> 4) == 1) {
                if (opcode == 5) {
                    indices[0] = (commands->words.w0 >> 16) & 255;
                    indices[1] = (commands->words.w0 >> 8) & 255;
                    indices[2] = commands->words.w0 & 255;
                    count = 3;
                    for (indexCursor = indices; indexCursor < indices + 3; indexCursor++) {
                        *indexCursor >>= 1;
                    }
                } else if (opcode == 6) {
                    indices[0] = (commands->words.w0 >> 16) & 255;
                    indices[1] = (commands->words.w0 >> 8) & 255;
                    indices[2] = commands->words.w0 & 255;
                    indices[3] = (commands->words.w1 >> 16) & 255;
                    indices[4] = (commands->words.w1 >> 8) & 255;
                    indices[5] = commands->words.w1 & 255;
                    count = 6;
                    for (indexCursor = indices; indexCursor < indices + 6; indexCursor++) {
                        *indexCursor >>= 1;
                    }
                } else {
                    indices[0] = (commands->words.w1 >> 25) & 31;
                    indices[1] = (commands->words.w1 >> 20) & 31;
                    indices[2] = (commands->words.w1 >> 15) & 31;
                    indices[3] = (commands->words.w1 >> 10) & 31;
                    indices[4] = (commands->words.w1 >> 5) & 31;
                    indices[5] = commands->words.w1 & 31;
                    indices[6] = (commands->words.w0 >> 10) & 31;
                    indices[7] = (commands->words.w0 >> 5) & 31;
                    indices[8] = commands->words.w0 & 31;
                    indices[9] = (commands->words.w0 >> 23) & 31;
                    indices[10] = (commands->words.w0 >> 18) & 31;
                    indices[11] = ((commands->words.w1 >> 30) & 3) +
                        (((commands->words.w0 >> 15) & 7) << 2);
                    count = 12;
                }
                for (i = 0; i < count; i++) {
                    if (maximum < indices[i]) { maximum = indices[i]; }
                }
                if (nested == 0 && trimFirst) {
                    minimum = indices[0];
                    trimFirst = 0;
                    for (i = 1; i < count; i++) {
                        if (indices[i] < minimum) { minimum = indices[i]; }
                    }
                    *firstVertex += (minimum & 255) << 4;
                }
            }
        }
        commands++;
    }
    return (s32)(vertexBase + ((maximum + 1) << 4) - *firstVertex) >> 4;
}
'''


def recover(before,body=BODY):
    lo,hi=build.function_span(before,FUNCTION)
    result=before[:lo]+body.rstrip()+before[hi:]
    return result.replace('#include <ultra64.h>\n','#include <ultra64.h>\n\n'+DECLARATIONS,1)


def freeze(root,out):
    out.mkdir(exist_ok=True)
    manifest=out/'baseline.json'
    if not manifest.exists():
        data={key:(root/path).read_bytes() for key,path in PATHS.items()}
        if {key:hashlib.sha256(value).hexdigest() for key,value in data.items()}!=BASELINE:
            raise ValueError('Changed texture vertex span baseline')
        for key,value in data.items():
            (out/('before-'+key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE,indent=2)+'\n')
    if json.loads(manifest.read_text())!=BASELINE:
        raise ValueError('Modified texture vertex span manifest')
    for key,digest in BASELINE.items():
        if hashlib.sha256((out/('before-'+key)).read_bytes()).hexdigest()!=digest:
            raise ValueError('Modified immutable texture vertex span input: '+key)


def variants():
    yield 'baseline',BODY
    yield 'placeholder','s32 func_1510BF60() { return 0; }\n'
    yield 'preload-opcode',BODY.replace('    for (;;) {\n        opcode = *(s8 *)commands;',
        '    opcode = *(s8 *)commands;\n    for (;;) {').replace('        commands++;\n    }',
        '        commands++;\n        opcode = *(s8 *)commands;\n    }')
    yield 'signed-command-word',BODY.replace('opcode = *(s8 *)commands;','opcode = (s32)commands->words.w0 >> 24;')
    yield 'explicit-wrap-span',BODY.replace('((maximum + 1) << 4)','((u32)(maximum + 1) << 4)')
    end=BODY.replace('    s32 *indexCursor;','    s32 *indexCursor;\n    s32 *indexEnd;')
    for count in (3,6):
        end=end.replace('for (indexCursor = indices; indexCursor < indices + %d; indexCursor++)'%count,
            'for (indexCursor = indices, indexEnd = indexCursor + %d; indexCursor < indexEnd; indexCursor++)'%count)
    yield 'explicit-shared-end',end
    declarations=('    s32 extent;','    u32 vertexBase;','    s32 indices[12];')
    for index,order in enumerate(itertools.permutations(declarations)):
        yield 'shared-layout-'+str(index),end.replace('\n'.join(declarations),'\n'.join(order))
    integer=BODY
    for count in (3,6):
        integer=integer.replace('indexCursor < indices + %d'%count,
            '(u32)indexCursor < (u32)indices + count * sizeof(s32)')
    yield 'integer-byte-end',integer
    computed=BODY
    for count in (3,6):
        computed=computed.replace('indexCursor < indices + %d'%count,'indexCursor < indices + count')
    yield 'count-end',computed
    index=BODY.replace('    s32 *indexCursor;\n','')
    for count in (3,6):
        index=index.replace('for (indexCursor = indices; indexCursor < indices + %d; indexCursor++) {\n                        *indexCursor >>= 1;\n                    }'%count,
            'for (i = 0; i < count; i++) { indices[i] >>= 1; }')
    yield 'count-index-loop',index
    for label,text in (('shared',end),('integer',integer),('count',computed),('index',index)):
        yield label+'-span-local',text.replace('    s32 extent;','    s32 extent;\n    s32 span;').replace(
            '    return (s32)(vertexBase + ((maximum + 1) << 4) - *firstVertex) >> 4;',
            '    span = vertexBase + ((maximum + 1) << 4) - *firstVertex;\n    return span >> 4;')
        yield label+'-end-local',text.replace('    s32 extent;','    s32 extent;\n    s32 endOpcode;').replace(
            '    stage = 0;','    endOpcode = -33;\n    stage = 0;').replace('opcode == -33','opcode == endOpcode')


def negatives(body):
    return dict(
        cached_texture=body.replace('    s32 extent;','    s32 extent;\n    u32 texture = D_800B0E58[resource];').replace(
            'commands->words.w1 == D_800B0E58[resource]','commands->words.w1 == texture'),
        unchanged_occurrence=body.replace('occurrence-- < 1','occurrence < 1'),
        wrong_packed_shift=body.replace('commands->words.w1 >> 25','commands->words.w1 >> 24'),
        wrong_trim_stride=body.replace('(minimum & 255) << 4','(minimum & 255) << 3'),
        skip_previous_command=body.replace('            commands--;\n            continue;','            continue;'),
        signed_vertex_compare=body.replace('vertexBase < *firstVertex','(s32)vertexBase < (s32)*firstVertex'),
        clear_before_provider=body.replace('    func_1510D0EC(resource, &extent, 3, 0);\n    *firstVertex = 0;',
            '    *firstVertex = 0;\n    func_1510D0EC(resource, &extent, 3, 0);'))


def main():
    root=Path(__file__).resolve().parents[2]
    out=root/BUILD
    freeze(root,out)
    before=(out/'before-owner').read_text()
    retail=list(struct.unpack_from('>339I',(root/'conker/conker.us.bin').read_bytes(),ROM))
    records=[]
    for label,body in variants():
        obj,diagnostics=build.compile_owner(root,out,recover(before,body),label)
        data,functions=build.link_owner(root,out,obj,OWNER)
        info=functions[FUNCTION]
        words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
        row=dict(label=label,bytes=info['size'],frame=((0x10000-(words[0]&65535))&65535) if words[0]>>16==0x27BD else None,
            differences=sum(a!=b for a,b in zip(words,retail))+abs(len(words)-len(retail)),diagnostics=diagnostics)
        records.append(row)
        print(json.dumps(row),flush=True)
    (out/'screens.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
