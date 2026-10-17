"""Recover the complete signed viewport-clipped SDK fill-rectangle leaf."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_overlay_projection as previous
from tools.tests import overlay_projection_checkpoint as checkpoint
from tools.experiments.game_view_list_setup import compile_owner
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object

BUILD='conker/build/game-clipped-rectangle'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_1AC2F0','func_1517F9F4',0x1517F9F4,0x1ACEA4,106
PATHS=dict(previous.PATHS)
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER)
build=previous.build
INITIAL='''/* Sort and clip signed endpoints, then append one fill rectangle. */
Gfx *func_1517F9F4(Gfx *commands, s32 left, s32 top, s32 right, s32 bottom, s32 view) {
    s32 swap;
    OverlayViewport1AC2F0 *record;
    s32 clipLeft, clipTop, clipBottom, clipRight;
    s32 x0, y0, x1, y1;

    if (right < left) {
        swap = left;
        left = right;
        right = swap;
    }
    if (bottom < top) {
        swap = top;
        top = bottom;
        bottom = swap;
    }
    record = &OVERLAY_VIEWS_1AC2F0[view];
    clipLeft = (s32)record->left;
    clipTop = (s32)record->top;
    clipBottom = (s32)record->bottom;
    clipRight = (s32)record->right;
    if (top >= clipBottom || clipTop >= bottom || left >= clipRight || clipLeft >= right) {
        return commands;
    }
    x0 = left < clipLeft ? clipLeft : clipRight < left ? clipRight : left;
    y0 = top < clipTop ? clipTop : clipBottom < top ? clipBottom : top;
    x1 = right < clipLeft ? clipLeft : clipRight < right ? clipRight : right;
    y1 = bottom < clipTop ? clipTop : clipBottom < bottom ? clipBottom : bottom;
    gDPFillRectangle(commands++, x0, y0, x1, y1);
    return commands;
}'''


def forms():
    reordered=INITIAL.replace('    clipBottom = (s32)record->bottom;\n    clipRight = (s32)record->right;',
        '    clipRight = (s32)record->right;\n    clipBottom = (s32)record->bottom;')
    for prefix,body in (('casts',reordered),('original-casts',INITIAL)):
        yield prefix,body
        shared=body.replace('    s32 x0, y0, x1, y1;','    s32 x0, y0, x1, y1;\n    s32 clipped;')
        for name in ('x0','y0','x1','y1'):
            start=shared.index('    '+name+' = ');end=shared.index(';',start)+1
            shared=shared[:start]+shared[start:end].replace(name+' =','clipped =',1)+'\n    '+name+' = clipped;'+shared[end:]
        yield prefix+'-ternary-shared',shared
        parameters=shared.replace('    s32 x0, y0, x1, y1;\n','').replace(
            'x0','left').replace('y0','top').replace('x1','right').replace('y1','bottom')
        yield prefix+'-ternary-shared-parameters',parameters
        yield prefix+'-reuse-swap-bound',parameters.replace('clipLeft, ','').replace('clipLeft','swap')
        yield prefix+'-reuse-swap-result',parameters.replace('    s32 clipped;\n','').replace('clipped','swap')
        yield prefix+'-register-shared',shared.replace('s32 clipped;','register s32 clipped;')
        yield prefix+'-register-bounds',shared.replace('s32 clipLeft,','register s32 clipLeft,')
        yield prefix+'-parameter-result',body.replace('    s32 x0, y0, x1, y1;','').replace('x0','left').replace(
            'y0','top').replace('x1','right').replace('y1','bottom')
    yield 'decl-right-before-bottom',INITIAL.replace('clipLeft, clipTop, clipBottom, clipRight','clipLeft, clipTop, clipRight, clipBottom')
    for named,body in (('ordinary',INITIAL),('right-first',INITIAL.replace('clipLeft, clipTop, clipBottom, clipRight','clipLeft, clipTop, clipRight, clipBottom'))):
        for output,value,lower,upper in (('x0','left','clipLeft','clipRight'),('y0','top','clipTop','clipBottom'),
                ('x1','right','clipLeft','clipRight'),('y1','bottom','clipTop','clipBottom')):
            old='    %s = %s < %s ? %s : %s < %s ? %s : %s;'%(output,value,lower,lower,upper,value,upper,value)
            new='''    if (%s < %s) {
        %s = %s;
    } else {
        swap = %s;
        if (%s < %s) {
            swap = %s;
        }
        %s = swap;
    }'''%(value,lower,output,lower,value,upper,value,upper,output)
            body=body.replace(old,new)
        yield named+'-explicit-ifs',body
        yield named+'-shared-result',body.replace('    s32 x0, y0, x1, y1;','    s32 x0, y0, x1, y1;\n    s32 clipped;').replace(
            '        x0 =','        clipped =').replace('        y0 =','        clipped =').replace('        x1 =','        clipped =').replace(
            '        y1 =','        clipped =').replace('    }\n    if (top <','    }\n    x0 = clipped;\n    if (top <').replace(
            '    }\n    if (right <','    }\n    y0 = clipped;\n    if (right <').replace('    }\n    if (bottom < clipTop)',
            '    }\n    x1 = clipped;\n    if (bottom < clipTop)').replace('    gDPFillRectangle','    y1 = clipped;\n    gDPFillRectangle')


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import clipped_rectangle_checkpoint as installed
            data=installed.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Unknown clipped rectangle input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed clipped rectangle fixture: '+key)


def recovered_owner(before,body=None):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1517F9F4() {\n    return 0;\n}':raise ValueError('Unknown clipped rectangle placeholder')
    return before[:lo]+(SELECTED if body is None else body)+before[hi:]


def parts(obj):
    data,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in relocations.items() if f['value']<=a<f['value']+f['size']}


def measure(root,out,label,body):
    freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner((out/'before-color_owner').read_text(),body),label)
    data,functions=build.link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    wanted=list(struct.unpack_from('>106I',(out/'before-retail_rom').read_bytes(),ROM))
    raw,bindings=parts(obj)
    row=dict(label=label,words=len(words),differences=sum(a!=b for a,b in zip(words,wanted))+abs(len(words)-106),
        frame=(-words[0]&65535) if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


SELECTED=dict(forms())['casts-reuse-swap-bound'].replace('swap','scratch').replace(
    '    scratch = (s32)record->left;', '    /* Sorting scratch now holds the left clip bound. */\n    scratch = (s32)record->left;')
RAW_SHA='ed394c8a4cb392c4df81808c9ed0b032a8c877efacae38bcd922ea6762b21b0b'
BINDINGS={52:[('R_MIPS_HI16','D_800BE628')],56:[('R_MIPS_LO16','D_800BE628')]}


def checked_parts(data,bindings,pool):
    if len(data)!=424 or hashlib.sha256(data).hexdigest()!=RAW_SHA or bindings!=BINDINGS or pool!=previous.POOL:
        raise ValueError('Unknown complete clipped rectangle words, bindings or inherited pool')


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified',SELECTED)
    checked_parts(*parts(obj),previous.sections(obj)['.rodata'][1])
    if (row['words'],row['differences'],row['frame'],row['diagnostics'])!=(106,0,0,''):
        raise ValueError('Clipped rectangle is not a complete direct match')
    old,diagnostics=compile_owner(root,out,(out/'before-color_owner').read_text(),'owner-before')
    if diagnostics:raise ValueError('Clipped rectangle predecessor diagnostics')
    neighbors=same_functions(old,obj,(FUNCTION,))
    pools=lambda path:{n:d for n,(_,d) in previous.sections(path).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):raise ValueError('Clipped rectangle changed owner pools')
    padded=previous.padded_object(root,out,obj,'qualified');old_padded=previous.padded_object(root,out,old,'owner-before')
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:raise ValueError('Padded clipped rectangle neighbor changed')
    data,functions=build.link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=424 or data[f['value']:f['value']+424]!=(out/'before-retail_rom').read_bytes()[ROM:ROM+424]:
        raise ValueError('Padded clipped rectangle differs')
    row.update(direct=True,new_guards=0,unchanged_raw_padded_neighbors=neighbors,inherited_pool_unchanged=True)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n');return obj,padded,words,row


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--screens',action='store_true');parser.add_argument('--filter',default='');parser.add_argument('--qualify',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.screens:
        for label,body in forms():
            if args.filter in label:print(json.dumps(measure(root,root/BUILD,label,body)[-1]),flush=True)
    elif args.qualify:print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
    else:print(json.dumps(measure(root,root/BUILD,'initial',INITIAL)[-1],indent=2),flush=True)
