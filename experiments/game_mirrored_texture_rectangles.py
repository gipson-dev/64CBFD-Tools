"""Recover four mirrored SDK texture rectangles around the projected center."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_clipped_rectangle as previous
from tools.tests import clipped_rectangle_checkpoint as checkpoint
from tools.experiments.game_view_list_setup import compile_owner
from tools.experiments.game_graphics_task_submit import same_functions
from tools.experiments import game_overlay_projection as projection
from tools.pad_generated_object import parse_object

BUILD='conker/build/game-mirrored-texture-rectangles'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_1AC2F0','func_1517FB9C',0x1517FB9C,0x1AD04C,633
PATHS=dict(previous.PATHS)
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER)
build=previous.build
INITIAL='''/* Append four mirrored texture rectangles around the projected center. */
Gfx *func_1517FB9C(Gfx *commands, s32 size, s32 textureSize, f32 offsetX, f32 offsetY, s32 view) {
    f32 centerX;
    f32 centerY;
    f32 positiveX;
    f32 positiveY;
    f32 negativeX;
    f32 negativeY;
    u16 step;

    centerX = OVERLAY_VIEWS_1AC2F0[view].extentX + D_800DDDE8[view][0];
    centerY = OVERLAY_VIEWS_1AC2F0[view].extentY + D_800DDDE8[view][1];
    positiveX = centerX + offsetX;
    positiveY = centerY + offsetY;
    step = (u32)(((f32)textureSize / (f32)size) * 1024.0f);
    gSPScisTextureRectangle(commands++,
        (s32)positiveX * 4, (s32)positiveY * 4,
        (s32)(positiveX + size) * 4, (s32)(positiveY + size) * 4, 0,
        ((s32)(positiveX * 32.0f) & 31) + textureSize * 32,
        ((s32)(positiveY * 32.0f) & 31) + textureSize * 32,
        -step, -step);
    negativeX = centerX - offsetX;
    negativeY = centerY - offsetY;
    gSPScisTextureRectangle(commands++,
        (s32)(negativeX - size) * 4, (s32)(negativeY - size) * 4,
        (s32)negativeX * 4, (s32)negativeY * 4, 0,
        31 - ((s32)((negativeX - size) * 32.0f) & 31),
        31 - ((s32)((negativeY - size) * 32.0f) & 31),
        step, step);
    gSPScisTextureRectangle(commands++,
        (s32)positiveX * 4, (s32)(negativeY - size) * 4,
        (s32)(positiveX + size) * 4, (s32)negativeY * 4, 0,
        ((s32)(positiveX * 32.0f) & 31) + textureSize * 32,
        31 - ((s32)((negativeY - size) * 32.0f) & 31),
        -step, step);
    gSPScisTextureRectangle(commands++,
        (s32)(negativeX - size) * 4, (s32)positiveY * 4,
        (s32)negativeX * 4, (s32)(positiveY + size) * 4, 0,
        31 - ((s32)((negativeX - size) * 32.0f) & 31),
        ((s32)(positiveY * 32.0f) & 31) + textureSize * 32,
        step, -step);
    return commands;
}'''


def forms():
    record=INITIAL.replace('    f32 centerX;','    OverlayViewport1AC2F0 *record;\n    f32 centerX;').replace(
        '    centerX = OVERLAY_VIEWS_1AC2F0[view].extentX',
        '    record = &OVERLAY_VIEWS_1AC2F0[view];\n    centerX = record->extentX').replace(
        'OVERLAY_VIEWS_1AC2F0[view].extentY','record->extentY')
    span=record.replace('    u16 step;','    u16 step;\n    f32 span;').replace('    positiveX =',
        '    span = size;\n    positiveX =',1).replace('(f32)size','span').replace('+ size','+ span').replace('- size','- span')
    reverse=span.replace('record->extentX + D_800DDDE8[view][0]','D_800DDDE8[view][0] + record->extentX').replace(
        'record->extentY + D_800DDDE8[view][1]','D_800DDDE8[view][1] + record->extentY')
    for label,base in (('record',record),('span',span)):
        yield 'width-'+label+'-s16-step',base.replace('u16 step;','s16 step;')
        yield 'width-'+label+'-word-u16-cast',base.replace('u16 step;','u32 step;').replace('step = (u32)','step = (u16)(u32)')
        yield 'width-'+label+'-decl-y-first',base.replace('    f32 positiveX;\n    f32 positiveY;',
            '    f32 positiveY;\n    f32 positiveX;')
        yield 'width-'+label+'-size-left-y-first',base.replace('    positiveX = centerX + offsetX;\n    positiveY = centerY + offsetY;',
            '    positiveY = centerY + offsetY;\n    positiveX = centerX + offsetX;').replace(
            '(positiveX + '+('span' if label=='span' else 'size')+')','('+('span' if label=='span' else 'size')+' + positiveX)').replace(
            '(positiveY + '+('span' if label=='span' else 'size')+')','('+('span' if label=='span' else 'size')+' + positiveY)')
    for label,base in (('record',record),('span',span)):
        yield 'float-order-'+label+'-register-y',base.replace('f32 offsetY,','register f32 offsetY,')
        alias=base.replace('    f32 centerX;','    f32 yOffset;\n    f32 centerX;').replace(
            '    record =','    yOffset = offsetY;\n    record =',1).replace('centerY + offsetY','centerY + yOffset').replace('centerY - offsetY','centerY - yOffset')
        yield 'float-order-'+label+'-alias-y',alias
        yield 'float-order-'+label+'-centers-first',base.replace(
            '    centerX = record->extentX + D_800DDDE8[view][0];\n    centerY = record->extentY + D_800DDDE8[view][1];',
            '    centerX = record->extentX;\n    centerY = record->extentY;\n    centerX += D_800DDDE8[view][0];\n    centerY += D_800DDDE8[view][1];')
        yield 'float-order-'+label+'-cached-projection',base.replace('    f32 centerX;', '    f32 *projected;\n    f32 centerX;').replace(
            '    centerX =','    projected = D_800DDDE8[view];\n    centerX =',1).replace('D_800DDDE8[view][0]','projected[0]').replace('D_800DDDE8[view][1]','projected[1]')
    for label,base in (('record',record),('span',span)):
        yield 'shape-'+label+'-x-array',base.replace('f32 positiveX;','f32 positiveX[1];').replace(
            'positiveX =','positiveX[0] =').replace('(s32)positiveX','(s32)positiveX[0]').replace(
            '(positiveX +','(positiveX[0] +').replace('(positiveX *','(positiveX[0] *')
        points=base.replace('    f32 positiveX;\n    f32 positiveY;\n    f32 negativeX;\n    f32 negativeY;', '    f32 points[4];')
        for i,name in enumerate(('positiveX','positiveY','negativeX','negativeY')):points=points.replace(name,'points[%d]'%i)
        yield 'shape-'+label+'-point-array',points
        phases=base.replace('    u16 step;','    u16 step;\n    s32 phaseX, phaseY;').replace(
            '    gSPScisTextureRectangle(commands++,\n        (s32)(negativeX',
            '    phaseX = (s32)((negativeX - '+('span' if label=='span' else 'size')+') * 32.0f) & 31;\n'
            '    phaseY = (s32)((negativeY - '+('span' if label=='span' else 'size')+') * 32.0f) & 31;\n'
            '    gSPScisTextureRectangle(commands++,\n        (s32)(negativeX',1)
        for axis in ('X','Y'):
            phases=phases.replace('((s32)((negative'+axis+' - '+('span' if label=='span' else 'size')+') * 32.0f) & 31)','phase'+axis)
        yield 'shape-'+label+'-negative-phases',phases
    for label,base in (('span',span),('reverse-span',reverse)):
        yield label,base
        split=base.replace('    u16 step;','    s32 step;\n    s32 negativeStep;').replace(
            'step = (u32)(((f32)textureSize / span) * 1024.0f);',
            'step = (u32)(((f32)textureSize / span) * 1024.0f) & 0xFFFF;\n    negativeStep = -step;').replace('-step,','negativeStep,').replace(', -step);',', negativeStep);')
        yield label+'-split-step',split
        for suffix,body in (('u16',base),('split',split)):
            cached=body.replace('    f32 negativeY;','    f32 negativeY;\n    f32 farNegativeX;\n    f32 farNegativeY;').replace(
                '    negativeY = centerY - offsetY;',
                '    negativeY = centerY - offsetY;\n    farNegativeX = negativeX - span;\n    farNegativeY = negativeY - span;')
            cached=cached.replace('(negativeX - span)','farNegativeX').replace('(negativeY - span)','farNegativeY')
            yield label+'-cached-negative-'+suffix,cached
    for prefix,base in (('record',record),('ordinary',INITIAL)):
        yield prefix,base
        for mode,body in (('u32-step',base.replace('u16 step;','u32 step;').replace(
                'step = (u32)(((f32)textureSize / (f32)size) * 1024.0f);',
                'step = (u32)(((f32)textureSize / (f32)size) * 1024.0f) & 0xFFFF;')),
                ('s32-step',base.replace('u16 step;','s32 step;').replace(
                'step = (u32)(((f32)textureSize / (f32)size) * 1024.0f);',
                'step = (u32)(((f32)textureSize / (f32)size) * 1024.0f) & 0xFFFF;'))):
            yield prefix+'-'+mode,body
            yield prefix+'-'+mode+'-y-first',body.replace('    positiveX = centerX + offsetX;\n    positiveY = centerY + offsetY;',
                '    positiveY = centerY + offsetY;\n    positiveX = centerX + offsetX;')
        yield prefix+'-y-first',base.replace('    positiveX = centerX + offsetX;\n    positiveY = centerY + offsetY;',
            '    positiveY = centerY + offsetY;\n    positiveX = centerX + offsetX;')


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Unknown mirrored texture input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed mirrored texture fixture: '+key)


def recovered_owner(before,body=None):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1517FB9C() {\n    return 0;\n}':raise ValueError('Unknown mirrored texture placeholder')
    return before[:lo]+(SELECTED if body is None else body)+before[hi:]


def parts(obj):
    data,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:v for a,v in relocations.items() if f['value']<=a<f['value']+f['size']}


def measure(root,out,label,body):
    freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner((out/'before-color_owner').read_text(),body),label)
    data,functions=build.link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    wanted=list(struct.unpack_from('>633I',(out/'before-retail_rom').read_bytes(),ROM));raw,bindings=parts(obj)
    row=dict(label=label,words=len(words),differences=sum(a!=b for a,b in zip(words,wanted))+abs(len(words)-633),
        frame=(-words[0]&65535) if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


SELECTED=dict(forms())['record']
RAW_SHA='95fe7a5372fc506f0c5ccf7035f020cd419705cdf4ef250cfa601b104e8b6a8f'
BINDINGS={24:[('R_MIPS_HI16','D_800BE628')],28:[('R_MIPS_LO16','D_800BE628')],
    48:[('R_MIPS_HI16','D_800DDDE8')],52:[('R_MIPS_LO16','D_800DDDE8')]}


def checked_parts(data,bindings,pool):
    if len(data)!=2504 or hashlib.sha256(data).hexdigest()!=RAW_SHA or bindings!=BINDINGS or pool!=projection.POOL:
        raise ValueError('Unknown complete mirrored candidate words, bindings or inherited pool')


def candidate(root,out):
    obj,words,row=measure(root,out,'candidate',SELECTED)
    checked_parts(*parts(obj),projection.sections(obj)['.rodata'][1])
    if (row['words'],row['differences'],row['frame'],row['diagnostics'])!=(626,604,216,''):
        raise ValueError('Changed mirrored texture diagnostic candidate')
    old,diagnostics=compile_owner(root,out,(out/'before-color_owner').read_text(),'owner-before')
    if diagnostics:raise ValueError('Mirrored texture predecessor diagnostics')
    neighbors=same_functions(old,obj,(FUNCTION,))
    pools=lambda path:{n:d for n,(_,d) in projection.sections(path).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):raise ValueError('Mirrored candidate changed owner pools')
    padded=projection.padded_object(root,out,obj,'candidate');old_padded=projection.padded_object(root,out,old,'owner-before')
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:raise ValueError('Padded mirrored neighbor changed')
    data,functions=build.link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    emitted=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    if emitted!=words:raise ValueError('Normal padder changed the diagnostic candidate')
    row.update(unchanged_raw_padded_neighbors=neighbors,inherited_pool_unchanged=True,
        installed=False,byte_exact=False,matching_credit=False,new_guards=0)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n');return obj,padded,words,row


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--screens',action='store_true');parser.add_argument('--filter',default='');parser.add_argument('--candidate',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.screens:
        for label,body in forms():
            if args.filter in label:print(json.dumps(measure(root,root/BUILD,label,body)[-1]),flush=True)
    elif args.candidate:print(json.dumps(candidate(root,root/BUILD)[-1],indent=2),flush=True)
    else:print(json.dumps(measure(root,root/BUILD,'initial',INITIAL)[-1],indent=2),flush=True)
