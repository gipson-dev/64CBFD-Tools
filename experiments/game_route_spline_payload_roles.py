"""Recover spline payload source lifetimes without replacing qualified points."""
import argparse
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_route_spline_payload_fitting as fit

BUILD='conker/build/game-route-spline-payload-roles'
CURSORS=('xCursor','yCursor','zCursor','targetXCursor','targetYCursor','targetZCursor')
PREVIOUS=('previousX','previousY','previousZ','previousTargetX','previousTargetY','previousTargetZ')


def cursor_capture(cursor,temporary=False):
    if cursor not in CURSORS:raise ValueError('Unknown cursor')
    body=fit.literal_scale(fit.source.inline_previous(fit.source.SELECTED))
    body=body.replace('    u8 *object;\n','').replace('    f32 *'+cursor+';','    u8 *'+cursor+';')
    body=body.replace('    object = *(u8 **)(actor + 0x318);','    '+cursor+' = *(u8 **)(actor + 0x318);')
    body=body.replace('if (object != 0)','if ('+cursor+' != 0)').replace('object[0x23D]',cursor+'[0x23D]')
    body=body.replace(cursor+' = '+cursor[:-6]+';',cursor+' = (u8 *)'+cursor[:-6]+';')
    body=body.replace(cursor+'++;',cursor+' += 4;')
    if cursor=='targetZCursor':body=body.replace('targetZCursor != targetZ + 4','targetZCursor != (u8 *)(targetZ + 4)')
    body=body.replace(cursor+'[-1]','*(f32 *)('+cursor+' - 4)').replace(cursor+'[-2]','*(f32 *)('+cursor+' - 8)')
    body=body.replace('                    *'+cursor+' =','                    *(f32 *)'+cursor+' =')
    body=re.sub(r'(?<=[,\n])([ \t]*)'+cursor+r'(?=[,)])',r'\1(f32 *)'+cursor,body)
    if temporary:
        old='    '+cursor+' = *(u8 **)(actor + 0x318);\n    if ('+cursor+' != 0) {'
        if body.count(old)!=1:raise ValueError('Unknown temporary capture')
        body=body.replace(old,'    node = *(u8 **)(actor + 0x318);\n    if (node != 0) {\n        '+cursor+' = node;')
    return fit.source.direct_phase(fit.phase_carriers(fit.front_cursors(body)))


def capture_forms():
    return {cursor+('-node' if temporary else '-direct'):cursor_capture(cursor,temporary)
        for cursor in CURSORS for temporary in (False,True)}


def move_declarations(body,names,start,end):
    result=body;declarations=[]
    for name in names:
        matches=list(re.finditer(r'^    (?:s32|u8|f32|f64) (?:\*)?'+name+';\n',result,re.M))
        if len(matches)!=1:raise ValueError('Unknown scoped declaration '+name)
        text=matches[0][0];declarations.append(text);result=result.replace(text,'',1)
    first=result.index(start);last=result.index(end,first)
    inside=''.join('    '+line for line in result[first:last].splitlines(True))
    return result[:first]+'            {\n'+''.join('            '+d for d in declarations)+inside+'            }\n'+result[last:]


def scoped_previous(body):
    result=body;declarations=[]
    for name in PREVIOUS:
        text='    f32 '+name+';\n'
        if result.count(text)!=1:raise ValueError('Unknown previous-coordinate declaration')
        declarations.append('                    f32 '+name+';\n');result=result.replace(text,'',1)
    marker='                } else {\n                    previousX ='
    if result.count(marker)!=1:raise ValueError('Unknown extrapolation branch')
    return result.replace(marker,'                } else {\n'+''.join(declarations)+'                    previousX =')


def scoped_forms():
    base=fit.literal_scale(fit.source.SELECTED)
    base=fit.front_cursors(base)
    base=scoped_previous(base)
    first='            if (*(s8 *)(record + 0x49) == 0) {'
    last='            *(f32 *)(record + 0x34) += D_8009DA10'
    scoped=move_declarations(base,('routeClass','node'),first,last)
    phase_first='            phase = *(f32 *)(record + 0x34);\n            if (phase >= 1.0f) {'
    phase_last='            previousValid = 0;'
    phase=move_declarations(scoped,('old',),phase_first,phase_last)
    return {'scope-previous':base,'scope-initializer':scoped,'scope-initializer-phase':phase,
        'scope-initializer-index':move_declarations(scoped,('i',),first,last)}


def separate_forms():
    base=fit.front_cursors(fit.literal_scale(fit.source.inline_previous(fit.source.SELECTED)))
    fields=fit.source.fields(base)
    indexed=fit.source.front_floats(fit.literal_scale(fit.source.indexed(fit.source.SELECTED)))
    return {'separate-fields':fields,'separate-fields-phase':fit.source.direct_phase(fit.phase_carriers(fields)),
        'separate-indexed':indexed,'separate-indexed-direct':fit.source.direct_phase(indexed)}


def measure(root,out,name,body):
    obj,_,row=fit.source.measure(root,out,name,body)
    words=fit.link_literal(root,out,obj)
    truth=struct.unpack_from('>305I',(root/'conker/conker.us.bin').read_bytes(),fit.source.ROM)
    row['differences']=sum(i>=len(words) or i>=len(truth) or words[i]!=truth[i]
        for i in range(max(len(words),len(truth))))
    row['saved_FP_pairs']=sum(w>>26==61 for w in words)
    row['homes']={w>>16&31:((w&65535)^32768)-32768-row['frame'] for w in words
        if w>>26==9 and w>>21&31==29 and w>>16&31 in range(16,24)}
    row['first_different_word']=next((i for i,(a,b) in enumerate(zip(words,truth)) if a!=b),None)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def screen(root,out,which):
    forms={'captures':capture_forms,'scopes':scoped_forms,'separate':separate_forms}[which]();rows=[]
    for name,body in forms.items():
        _,_,row=measure(root,out,name,body)
        row={k:row[k] for k in ('words','frame','differences','raw_sha256','saved_FP_pairs','first_different_word','homes')}
        rows.append(dict(name=name,**row));print(json.dumps(rows[-1]),flush=True)
    (out/(which+'.json')).write_text(json.dumps(rows,indent=2)+'\n');return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--family',choices=('captures','scopes','separate'),default='captures')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2];screen(root,root/BUILD,args.family)
