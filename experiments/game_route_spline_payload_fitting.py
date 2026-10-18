"""Fit the same complete spline payload, retaining the qualified recovery points."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_route_spline_payload_recovery as source
from tools.experiments.game_actor_classifier_candidates import sections

BUILD='conker/build/game-route-spline-payload-fitting'
RAW_SHA='f1c17b8f044c3d950100bf4b530cf11a41e1bbb8630f85219914d3dde0711ded'
JOINT_SHA='a048f871640fe3d03e7fb09e74f72a91817cd83cc7e8030cf16d91d50499c2e7'
BINDINGS={k:v for k,v in source.BINDINGS.items() if k not in (540,544)}
BINDINGS.update({548:[('R_MIPS_HI16','.rodata')],584:[('R_MIPS_LO16','.rodata')]})
JOINT_BINDINGS={k+(4 if k<528 else 12):v for k,v in BINDINGS.items()}


def literal_scale(body):
    result=body.replace('    f64 angleScale;\n','').replace('            angleScale = D_8009DA18;\n','')
    if result==body or result.count(' * angleScale')!=1:raise ValueError('Unknown named angle factor')
    return result.replace(' * angleScale',' * 0.01745')


def forms():
    front=source.front_floats(source.SELECTED)
    literal=literal_scale(front)
    small=literal_scale(source.inline_previous(source.SELECTED))
    return {'literal-front':literal,'literal-initial':literal_scale(source.SELECTED),
        'literal-inline':small,'literal-inline-fields':source.fields(small),
        'literal-inline-expressions':source.expressions(small),
        'literal-inline-all':source.expressions(source.fields(small))}


def object_cursor(body,byte_cursor=False):
    old='    object = *(u8 **)(actor + 0x318);'
    if body.count(old)!=1 or body.count('    u8 *object;\n')!=1:raise ValueError('Unknown object capture')
    result=body.replace('    u8 *object;\n','').replace(old,'    xCursor = (f32 *)*(u8 **)(actor + 0x318);')
    result=result.replace('if (object != 0)','if (xCursor != 0)').replace('object[0x23D]','((u8 *)xCursor)[0x23D]')
    if byte_cursor:
        result=result.replace('    f32 *xCursor;','    u8 *xCursor;').replace('(f32 *)*(u8 **)','*(u8 **)')
        result=result.replace('xCursor = x;','xCursor = (u8 *)x;').replace('                xCursor++;','                xCursor += 4;')
        result=result.replace('xCursor[-1]','*(f32 *)(xCursor - 4)').replace('xCursor[-2]','*(f32 *)(xCursor - 8)')
        result=result.replace('                    *xCursor =','                    *(f32 *)xCursor =')
        result=result.replace('func_15086CBC(id, xCursor,','func_15086CBC(id, (f32 *)xCursor,')
    return result


def lifetime_forms():
    base=literal_scale(source.inline_previous(source.SELECTED))
    return {'object-x-float':object_cursor(base),'object-x-byte':object_cursor(base,True),
        'object-x-float-fields':object_cursor(source.fields(base)),
        'object-x-byte-fields':object_cursor(source.fields(base),True),
        'object-x-float-expressions':object_cursor(source.expressions(base)),
        'object-x-byte-expressions':object_cursor(source.expressions(base),True)}


def front_cursors(body):
    names=('phase','xCursor','yCursor','zCursor','targetXCursor','targetYCursor','targetZCursor')
    lines=[];result=body
    for name in names:
        matches=list(re.finditer(r'^    [^;{}\n]*\b'+name+r';\n',result,re.M))
        if len(matches)!=1:raise ValueError('Unknown cursor declaration: '+name)
        line=matches[0].group();lines.append(line);result=result.replace(line,'',1)
    return result.replace('    f32 x[4];',''.join(lines)+'    f32 x[4];',1)


def register_previous(body):
    result=body
    for name in ('previousX','previousY','previousZ','previousTargetX','previousTargetY','previousTargetZ'):
        text='    f32 '+name+';'
        if result.count(text)!=1:raise ValueError('Unknown previous coordinate')
        result=result.replace(text,'    register f32 '+name+';')
    return result


def allocation_forms():
    small=literal_scale(source.inline_previous(source.SELECTED))
    full=literal_scale(source.SELECTED)
    return {'front-cursors-byte':front_cursors(object_cursor(small,True)),
        'front-cursors-float':front_cursors(object_cursor(small)),
        'register-previous':register_previous(full),
        'register-object-byte':register_previous(object_cursor(full,True)),
        'register-object-float':register_previous(object_cursor(full)),
        'register-front-cursors':front_cursors(register_previous(object_cursor(full,True)))}


def selected():return front_cursors(object_cursor(literal_scale(source.inline_previous(source.SELECTED)),True))


def integer_capture(body):
    old='    xCursor = *(u8 **)(actor + 0x318);\n    if (xCursor != 0) {'
    new='    i = *(s32 *)(actor + 0x318);\n    if (i != 0) {\n        xCursor = (u8 *)(u32)i;'
    if body.count(old)!=1:raise ValueError('Unknown cursor capture')
    return body.replace(old,new)


def node_capture(body):
    old='    xCursor = *(u8 **)(actor + 0x318);\n    if (xCursor != 0) {'
    new='    node = *(u8 **)(actor + 0x318);\n    if (node != 0) {\n        xCursor = node;'
    if body.count(old)!=1:raise ValueError('Unknown cursor capture')
    return body.replace(old,new)


def phase_ids(body):
    result=source.direct_phase(body)
    for name in ('id','next'):
        old='    u8 '+name+';'
        if result.count(old)!=1:raise ValueError('Unknown phase byte local')
        result=result.replace(old,'    s32 '+name+';')
    return result


def capture_forms():
    base=selected()
    return {'integer-capture':integer_capture(base),'phase-ids':phase_ids(base),'node-capture':node_capture(base),
        'phase-node':phase_ids(node_capture(base)),'phase-integer':phase_ids(integer_capture(base))}


def phase_index(body):
    first=body.index('            if (phase >= 1.0f) {');last=body.index('            previousValid = 0;',first)
    return body[:first]+re.sub(r'\bid\b','i',body[first:last])+body[last:]


def shift_forms():
    base=selected();index=phase_index(base)
    return {'phase-direct':source.direct_phase(base),'phase-index':index,
        'phase-index-direct':source.direct_phase(index),
        'phase-index-next':index.replace('    u8 next;','    s32 next;'),
        'phase-index-expressions':source.expressions(base),
        'phase-index-node':phase_index(node_capture(base))}


def phase_carriers(body):
    # These existing integer lifetimes do not overlap the later four-point loop.
    first=body.index('            if (phase >= 1.0f) {');last=body.index('            previousValid = 0;',first)
    part=re.sub(r'\bid\b','previousValid',body[first:last])
    part=re.sub(r'\bnext\b','i',part)
    return body[:first]+part+body[last:]


def carrier_forms():
    base=phase_carriers(selected())
    return {'phase-carriers':base,'phase-carriers-direct':source.direct_phase(base),
        'phase-carriers-node':node_capture(base),'phase-carriers-node-direct':source.direct_phase(node_capture(base))}


def joint_selected():return source.direct_phase(phase_carriers(node_capture(selected())))


def link_literal(root,out,obj):
    pools=sections(obj)
    if pools['.rodata'][1]!=bytes.fromhex('3f91de69ad42c3ca0000000000000000'):
        raise ValueError('Unknown spline heading literal pool')
    run=subprocess.run;commands=[]
    def mapped(argv,**kwargs):
        if argv[0]=='mips-linux-gnu-ld':
            script=Path(argv[argv.index('-T')+1]);text=script.read_text()
            if text.count(' } }\n')!=1:raise ValueError('Unknown private owner linker script')
            script.write_text(text.replace(' } }\n',' } .rodata 0x8009DA18 : SUBALIGN(4) { *(.rodata) } }\n'))
            commands.append(argv)
        return run(argv,**kwargs)
    with patch.object(subprocess,'run',side_effect=mapped):
        data,functions=source.prior.prior.link_owner(root,out,obj,source.OWNER)
    if len(commands)!=1:raise ValueError('Unexpected literal link invocation')
    linked=sections(obj.with_suffix('.elf'))
    if linked['.rodata']!=(0x8009DA18,pools['.rodata'][1]):raise ValueError('Changed linked literal pool')
    f=functions[source.FUNCTION]
    return list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))


def checked(obj,joint=False):
    text,functions,relocations=source.parse_object(obj);f=functions[source.FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in relocations.items() if f['value']<=at<f['value']+f['size']}
    if (len(raw)!=(1220 if joint else 1208) or hashlib.sha256(raw).hexdigest()!=(JOINT_SHA if joint else RAW_SHA)
            or bindings!=(JOINT_BINDINGS if joint else BINDINGS)):
        raise ValueError('Unknown frame-correct spline payload source or bindings')
    return raw,bindings


def qualify(root,out,joint=False):
    label='joint-qualified' if joint else 'frame-qualified'
    obj,_,row=source.measure(root,out,label,joint_selected() if joint else selected());checked(obj,joint)
    words=link_literal(root,out,obj)
    truth=struct.unpack_from('>305I',(root/'conker/conker.us.bin').read_bytes(),source.ROM)
    row['differences']=sum(i>=len(words) or words[i]!=v for i,v in enumerate(truth))
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def screen(root,out):
    result=[]
    for name,body in dict(forms(),**lifetime_forms(),**allocation_forms(),**capture_forms(),**shift_forms(),**carrier_forms()).items():
        obj,words,row=source.measure(root,out,name,body)
        values={k:row[k] for k in ('words','frame','differences','raw_sha256')}
        values['generic_link_differences']=values.pop('differences')
        result.append(dict(name=name,**values));print(json.dumps(result[-1]),flush=True)
    (out/'screens.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group();group.add_argument('--qualify',action='store_true');group.add_argument('--joint',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    if args.qualify or args.joint:print(json.dumps(qualify(root,out,args.joint)[2],indent=2))
    else:screen(root,out)
