"""Bounded current/donor profile screens for the selected-view render pass."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_actor_mode_flags as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_function_isolation import compile_one
from tools.tests import actor_mode_flags_checkpoint as checkpoint

BUILD='conker/build/game-view-pass-dispatch'
OWNER,FUNCTION,ENTRY,ROM,WORDS='game_45B80','func_15019464',0x15019464,0x46914,79
PATHS=dict(previous.PATHS,dispatch_owner='conker/src/game_45B80.c',
    dispatch_original='conker/asm/nonmatchings/game_45B80/func_15019464.s')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,
    dispatch_owner='b773c30f274b9369a8190a8f5755198b71ecdb2d4ad16020b9c6b0053561a2c7',
    dispatch_original='4b703c5c8d6d94e04c2a7e9709c31bf1a1ea3f6ef39fbef06c93ed32151140de')
PROFILES=dict(o2g3=('-O2','-g3'),o2=('-O2',),o1g3=('-O1','-g3'),o1=('-O1',))
POINTER_BODY='''/* Set up the selected view and append its enabled render passes. */
Gfx *func_15019464(Gfx *commands, s16 view) {
    func_1510B958(view);
    gSPViewport(commands++, (D_800BE628 + (view * 0x180) + (D_800BE9C0 * 0x10) + 0x40));
    commands = (Gfx *)func_1501A490((s32)commands, view, 0, 0, 0, 0);
    if (D_800BEAC0 != 0) {
        return commands;
    }
    if (D_80084480 != 0) {
        return commands;
    }
    commands = (Gfx *)func_1510FEA0((s32)commands, D_800BE9F0);
    if (func_1517EFAC(view) != 0 || (D_800D18A0 & (1 << view)) != 0) {
        return commands;
    }
    commands = (Gfx *)func_1515D6D0((s32)commands, view);
    commands = func_1510B9D0(commands, view);
    return commands;
}
'''
SELECTED=POINTER_BODY.replace('(view * 0x180)','((u32)view * 0x180)').replace('(1 << view)','(1U << view)')
CALLEES=dict(select=0x1510B958,initial=0x1501A490,transform=0x1510FEA0,
    query=0x1517EFAC,overlay=0x1515D6D0,final=0x1510B9D0)
GLOBALS=dict(base=0x800BE628,page=0x800BE9C0,disabled=0x800BEAC0,
    blocked=0x80084480,kind=0x800BE9F0,mask=0x800D18A0)


def freeze(root,out):
    out.mkdir(exist_ok=True)
    manifest=out/'baseline.json'
    if not manifest.exists():
        data={key:(root/path).read_bytes() for key,path in PATHS.items()}
        if {key:hashlib.sha256(value).hexdigest() for key,value in data.items()}!=BASELINE:
            raise ValueError('Changed view pass dispatch baseline')
        for key,value in data.items():
            (out/('before-'+key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE,indent=2)+'\n')
    if json.loads(manifest.read_text())!=BASELINE:
        raise ValueError('Modified view pass dispatch manifest')
    for key,digest in BASELINE.items():
        if hashlib.sha256((out/('before-'+key)).read_bytes()).hexdigest()!=digest:
            raise ValueError('Modified immutable view pass dispatch input: '+key)


def donor(root):
    path=root/'conker/build/alternative-source-byte-audit-20261014/commented-c-compile-profile-qualified.json'
    rows=json.loads(path.read_text())['definitions']
    row=next(row for row in rows if row['function']==FUNCTION and row['variant']==0)
    expected='00b10acdf8f711c9a092633873616409627bcc7fe0f9f7d42384099a7d59a061'
    archive=root/'../Another Source/CBFD-Recompiled/conker/conker'/row['path']
    if row['source_sha256']!=expected or hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:
        raise ValueError('Changed view pass dispatch archive source')
    return row['body']


def variants(root,out):
    current=build.body((out/'before-dispatch_owner').read_text(),FUNCTION)
    yield 'current',current
    archived=donor(root)
    yield 'donor',archived
    yield 'donor-typed-tail',archived.replace('func_1510B9D0(temp_s0, arg1)',
        '(s32)func_1510B9D0((Gfx *)temp_s0, arg1)')
    yield 'pointer-cursor',POINTER_BODY


def recover(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    result=before[:lo]+body.rstrip()+before[hi:]
    return result.replace('/* Non-matching C placeholders for asm/nonmatchings/'+OWNER+'/'+FUNCTION+'.s. */\n','')


def index_variants():
    for label,expression in (('factor-three','((view * 3) << 7)'),
            ('shift-subtract','(((view << 2) - view) << 7)'),
            ('unsigned-scale','((u32)view * 0x180)'),
            ('unsigned-factor-three','(((u32)view * 3) << 7)'),
            ('page-shift','(view * 0x180)'),
            ('sizeof-view','(view * (s32)0x180)')):
        body=POINTER_BODY.replace('(view * 0x180)',expression)
        if label=='page-shift':
            body=body.replace('(D_800BE9C0 * 0x10)','(D_800BE9C0 << 4)')
        yield label,body


def shift_variants():
    body=dict(index_variants())['unsigned-scale']
    yield 'unsigned-shift',SELECTED
    yield 'masked-shift',body.replace('(1 << view)','(1U << (view & 31))')


def isolated_owner(root,out,label,body,flags):
    text=recover((out/'before-dispatch_owner').read_text(),body)
    if 'GLOBAL_ASM' in text:
        raise ValueError('Private isolated screen requires pure C input')
    path=out/(label+'-input.c')
    path.write_text(text)
    item=dict(path=str(path.relative_to(root/'conker')),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        function=FUNCTION,compiler_flags=list(flags),c_only=True)
    isolated=compile_one(root,root/'conker',out,item)
    if isolated['status']!='object_compiled':
        raise ValueError('Private isolated profile failed: '+repr(isolated))
    return Path(isolated['object']),Path(isolated['diagnostics_file']).read_text()


def measure(root,out,label,body,flags=('-O2','-g3')):
    freeze(root,out)
    text=recover((out/'before-dispatch_owner').read_text(),body)
    if tuple(flags)==('-O1','-g3'):
        obj,diagnostics=isolated_owner(root,out,label,body,flags)
    else:
        obj,diagnostics=build.compile_owner(root,out,text,label,flags)
    data,functions=build.link_owner(root,out,obj,OWNER)
    f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=list(struct.unpack_from('>79I',(root/'conker/conker.us.bin').read_bytes(),ROM))
    row=dict(label=label,words=len(words),frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-len(truth)),
        flags=list(flags),diagnostics=diagnostics,isolated_profile=tuple(flags)==('-O1','-g3'),
        differing_words=[(i*4,hex(a),hex(b)) for i,(a,b) in enumerate(zip(words,truth)) if a!=b])
    return row,words,obj


def qualify(root,out):
    row,words,obj=measure(root,out,'qualified',SELECTED)
    if row['words']!=WORDS or row['frame']!=40 or row['differences']:
        raise ValueError('Selected-view pass is not byte exact')
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index-forms',action='store_true')
    parser.add_argument('--shift-forms',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/BUILD
    freeze(root,out)
    rows=[]
    forms=shift_variants() if args.shift_forms else index_variants() if args.index_forms else variants(root,out)
    for label,body in forms:
        for profile,flags in (dict(o2g3=PROFILES['o2g3']) if args.index_forms or args.shift_forms else PROFILES).items():
            row,_,_=measure(root,out,label+'-'+profile,body,flags)
            rows.append(row)
            print(json.dumps({key:value for key,value in row.items() if key not in ('differing_words','diagnostics')},
                default=str),flush=True)
    filename='shift-screens.json' if args.shift_forms else 'index-screens.json' if args.index_forms else 'screens.json'
    (out/filename).write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    main()
