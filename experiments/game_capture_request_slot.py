"""Recover the first-free capture request and its real inline payload copy."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_view_pass_dispatch as previous
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import view_pass_dispatch_checkpoint as checkpoint
from tools.pad_generated_object import parse_object
from tools.experiments import game_record_constructor_candidates as compiler

BUILD='conker/build/game-capture-request-slot'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_1A11B0','func_151745F0',0x151745F0,0x1A1AA0,40
BASE,END=0x800DD348,0x800DD3FC
PATHS=dict(previous.PATHS,request_owner='conker/src/game/generated_1A11B0.c',
    request_original='conker/asm/1A11B0.s')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,
    request_owner='5e26a87867df8e4bbbd27ee5090c7f000b744ecbab6e054f53d911d55c8bb6f6',
    request_original='91d5b8f5d542245b976a9515019a337a34b1e2ce1e83bbd543186c1416e2553c')
TYPES='''typedef struct {
    u32 words[9];
} CapturePayload1A11B0;

typedef struct {
    f32 x, y, z;
    u8 state;
    u8 pad0D[3];
    CapturePayload1A11B0 payload;
    s8 callback;
    u8 pad35[3];
    s32 value;
} CaptureRequest1A11B0;

extern CaptureRequest1A11B0 D_800DD348[];
extern CaptureRequest1A11B0 D_800DD3FC[];
'''
BODY='''/* Queue a position and optional payload in the first unused capture record. */
s32 func_151745F0(f32 x, f32 y, f32 z, const CapturePayload1A11B0 *payload,
                 s8 callback, s32 value) {
    CaptureRequest1A11B0 *request = D_800DD348;

    do {
        if (request->state == 0) {
            request->x = x;
            request->y = y;
            request->state = 3;
            request->z = z;
            request->callback = callback;
            request->value = value;
            if (payload != NULL) {
                request->payload = *payload;
            }
            return 0;
        }
        request++;
    } while (request != D_800DD3FC);
    return 1;
}
'''
ARCHIVE_LOOP=BODY.replace('    do {','loop:\n    {').replace(
    '    } while (request != D_800DD3FC);\n    return 1;',
    '    }\n    if (request == D_800DD3FC) {\n        return 1;\n    }\n    goto loop;')


def freeze(root,out):
    out.mkdir(exist_ok=True)
    manifest=out/'baseline.json'
    if not manifest.exists():
        data={key:(root/path).read_bytes() for key,path in PATHS.items()}
        if {key:hashlib.sha256(value).hexdigest() for key,value in data.items()}!=BASELINE:
            raise ValueError('Changed capture request baseline')
        for key,value in data.items():
            (out/('before-'+key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE,indent=2)+'\n')
    if json.loads(manifest.read_text())!=BASELINE:
        raise ValueError('Modified capture request manifest')
    for key,digest in BASELINE.items():
        if hashlib.sha256((out/('before-'+key)).read_bytes()).hexdigest()!=digest:
            raise ValueError('Modified immutable capture request input: '+key)


def recover(before,body=BODY,types=TYPES):
    lo,hi=build.function_span(before,FUNCTION)
    result=before[:lo]+body.rstrip()+before[hi:]
    marker='#include <ultra64.h>\n'
    if result.count(marker)!=1 or 'CaptureRequest1A11B0' in before:
        raise ValueError('Unexpected capture request source preamble')
    return result.replace(marker,marker+'\n'+types,1)


def variants():
    yield 'typed-struct',BODY
    yield 'state-last',BODY.replace('            request->state = 3;\n','').replace(
        '            request->value = value;','            request->value = value;\n            request->state = 3;')
    yield 'while-loop',BODY.replace('    do {','    while (request != D_800DD3FC) {').replace(
        '    } while (request != D_800DD3FC);','    }')
    yield 'goto-loop',BODY.replace('    do {','loop:\n    {').replace(
        '    } while (request != D_800DD3FC);','    }\n    if (request != D_800DD3FC) {\n        goto loop;\n    }')
    yield 'archive-loop',ARCHIVE_LOOP
    yield 'archive-constless',ARCHIVE_LOOP.replace('const CapturePayload1A11B0 *payload','CapturePayload1A11B0 *payload')
    yield 'archive-loop-state-last',ARCHIVE_LOOP.replace('            request->state = 3;\n','').replace(
        '            request->value = value;','            request->value = value;\n            request->state = 3;')


def schedule_variants():
    for label,locals,stores in (
            ('preload-all','f32 zCopy = z;\n    s8 callbackCopy = callback;\n    s32 valueCopy = value;',
                (('request->z = z','request->z = zCopy'),('request->callback = callback','request->callback = callbackCopy'),
                 ('request->value = value','request->value = valueCopy'))),
            ('preload-z','f32 zCopy = z;',(('request->z = z','request->z = zCopy'),)),
            ('preload-tail','s8 callbackCopy = callback;\n    s32 valueCopy = value;',
                (('request->callback = callback','request->callback = callbackCopy'),('request->value = value','request->value = valueCopy')))):
        body=ARCHIVE_LOOP.replace('        if (request->state == 0) {',
            '        if (request->state == 0) {\n            '+locals)
        for old,new in stores:
            body=body.replace(old,new)
        yield label,body
    yield 'for-goto',ARCHIVE_LOOP.replace('CaptureRequest1A11B0 *request = D_800DD348;',
        'CaptureRequest1A11B0 *request;\n    request = D_800DD348;')
    for order in (('z','callback','value','x','y','state'),('x','y','z','state','callback','value'),
            ('x','y','z','callback','state','value'),('x','y','z','callback','value','state'),
            ('z','x','y','state','callback','value'),('callback','value','z','x','y','state')):
        start=ARCHIVE_LOOP.index('            request->x = x;')
        end=ARCHIVE_LOOP.index('            if (payload != NULL)')
        stores=''.join('            request->%s = %s;\n'%(name,'3' if name=='state' else name) for name in order)
        yield 'order-'+'-'.join(order),ARCHIVE_LOOP[:start]+stores+ARCHIVE_LOOP[end:]


def address_variants():
    for label,body in [('original-order',ARCHIVE_LOOP),*list(schedule_variants())[4:7]]:
        for pointer in ('u8','char'):
            current=body.replace('CaptureRequest1A11B0 *request = D_800DD348;',
                pointer+' *request = ('+pointer+' *)D_800DD348;')
            for field,kind,offset in (('x','f32',0),('y','f32',4),('z','f32',8),('state','u8',12),
                    ('payload','CapturePayload1A11B0',16),('callback','s8',52),('value','s32',56)):
                current=current.replace('request->'+field,'(*('+kind+' *)(request + 0x%X))'%offset)
            current=current.replace('request++;','request += 0x3C;').replace(
                'request == D_800DD3FC','request == ('+pointer+' *)D_800DD3FC')
            yield label+'-'+pointer,current


def interface_variants():
    best=dict(schedule_variants())['order-x-y-z-state-callback-value']
    for label,body in (('archive',ARCHIVE_LOOP),('ordered',best)):
        yield label+'-void-payload',body.replace('const CapturePayload1A11B0 *payload','const void *payload').replace(
            'request->payload = *payload','request->payload = *(const CapturePayload1A11B0 *)payload')
        yield label+'-end-local',body.replace('CaptureRequest1A11B0 *request = D_800DD348;',
            'CaptureRequest1A11B0 *end = D_800DD3FC;\n    CaptureRequest1A11B0 *request = D_800DD348;').replace(
                'request == D_800DD3FC','request == end')
        yield label+'-request-end-local',body.replace('CaptureRequest1A11B0 *request = D_800DD348;',
            'CaptureRequest1A11B0 *request = D_800DD348;\n    CaptureRequest1A11B0 *end = D_800DD3FC;').replace(
                'request == D_800DD3FC','request == end')
        yield label+'-signed-value',body.replace('s32 value','u32 value')
    yield 'ordered-forever',best.replace('loop:\n    {','    for (;;) {').replace(
        '    }\n    if (request == D_800DD3FC) {\n        return 1;\n    }\n    goto loop;',
        '        if (request == D_800DD3FC) {\n            return 1;\n        }\n    }')


def return_variants():
    body=dict(schedule_variants())['order-x-y-z-state-callback-value']
    yield 'shared-result',body.replace('    CaptureRequest1A11B0 *request = D_800DD348;',
        '    s32 result;\n    CaptureRequest1A11B0 *request = D_800DD348;').replace(
        '            return 0;','            result = 0;\n            goto done;').replace(
        '        return 1;','        result = 1;\n        goto done;').replace('    goto loop;','    goto loop;\ndone:\n    return result;')
    yield 'success-label',body.replace('            return 0;','            goto success;').replace(
        '    goto loop;','    goto loop;\nsuccess:\n    return 0;')
    yield 'default-result',body.replace('    CaptureRequest1A11B0 *request = D_800DD348;',
        '    s32 result = 1;\n    CaptureRequest1A11B0 *request = D_800DD348;').replace(
        '            return 0;','            result = 0;\n            goto done;').replace(
        '        return 1;','        goto done;').replace('    goto loop;','    goto loop;\ndone:\n    return result;')
    for pointer in ('u32','s32'):
        current=dict(address_variants())['order-x-y-z-state-callback-value-u8'].replace(
            'u8 *request = (u8 *)D_800DD348;',pointer+' request = ('+pointer+')D_800DD348;').replace(
            'request == (u8 *)D_800DD3FC','request == ('+pointer+')D_800DD3FC')
        yield 'integer-cursor-'+pointer,current


SELECTED=dict(schedule_variants())['order-x-y-z-state-callback-value']


def archive_draft(root):
    path=root/'../Another Source/CBFD-Recompiled/conker/conker/src/game/game_1A11B0.c'
    if hashlib.sha256(path.read_bytes()).hexdigest()!='ea8d7f14f995b088ae0fa96dcb415d9a56cbb57581482d192863deeedee12791':
        raise ValueError('Changed capture request archive source')
    return build.body(path.read_text(),FUNCTION)


def measure(root,out,label,body=BODY,flags=('-O2','-g3'),types=TYPES):
    freeze(root,out)
    obj,diagnostics=build.compile_owner(root,out,recover((out/'before-request_owner').read_text(),body,types),label,flags)
    data,functions=build.link_owner(root,out,obj,OWNER)
    f=functions[FUNCTION]
    emitted=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=list(struct.unpack_from('>40I',(root/'conker/conker.us.bin').read_bytes(),ROM))
    # Report the actual body and the separately proven final retail alignment NOP.
    complete=emitted+([0] if len(emitted)==39 and truth[-1]==0 else [])
    row=dict(label=label,body_words=len(emitted),slot_words=len(complete),
        differences=sum(a!=b for a,b in zip(complete,truth))+abs(len(complete)-40),
        flags=list(flags),diagnostics=diagnostics,
        differing_words=[(i*4,hex(a),hex(b)) for i,(a,b) in enumerate(zip(complete,truth)) if a!=b])
    return obj,complete,row


def qualify(root,out):
    if archive_draft(root).count('M2C_MEMCPY_ALIGNED')!=1:
        raise ValueError('Unexpected capture request pseudo-operation')
    obj,words,row=measure(root,out,'qualified',SELECTED)
    if row['differences']!=22 or row['body_words']!=39 or words[-1]!=0 or row['diagnostics']:
        raise ValueError('Unexpected capture request reconstruction: '+repr(row))
    row.update(strict_full_slot=False,installable=False,leaf_frame_bytes=0,retail_alignment_nops=1)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def profile_screens(root,out):
    freeze(root,out)
    rows=[]
    profiles=dict(no_unroll=('-O2','-g3','-Wo,-loopunroll,0'),o2=('-O2',),o1g3=('-O1','-g3'))
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD=TYPES,DECLARATIONS='',SYMBOLS={'D_800DD348':BASE,'D_800DD3FC':END},PROFILES=profiles):
        for label,body in (('do',BODY),('goto',ARCHIVE_LOOP),('ordered',dict(schedule_variants())['order-x-y-z-state-callback-value'])):
            for profile in profiles:
                row,_=compiler.compile_candidate(root,out,label+'-'+profile,body,profile)
                row.pop('frame')
                raw,functions,_=parse_object(out/(label+'-'+profile+'.o'))
                first=struct.unpack_from('>I',raw,functions[FUNCTION]['value'])[0]
                row['frame_bytes']=(-first)&65535 if first>>16==0x27BD else 0
                row['isolated_profile_control']=True
                rows.append(row)
                print(json.dumps(row),flush=True)
    (out/'profile-screens.json').write_text(json.dumps(rows,indent=2)+'\n')


def layout_screens(root,out):
    rows=[]
    for label,body in (('original',ARCHIVE_LOOP),('ordered',dict(schedule_variants())['order-x-y-z-state-callback-value'])):
        for kind in ('u8','void *','CaptureRequest1A11B0'):
            types=TYPES.replace('extern CaptureRequest1A11B0 D_800DD348[];',
                'extern '+kind+' D_800DD348;').replace('extern CaptureRequest1A11B0 D_800DD3FC[];',
                    'extern '+kind+' D_800DD3FC;')
            current=body.replace('request = D_800DD348','request = (CaptureRequest1A11B0 *)&D_800DD348').replace(
                'request == D_800DD3FC','request == (CaptureRequest1A11B0 *)&D_800DD3FC')
            _,_,row=measure(root,out,label+'-scalar-'+kind.replace(' *','p'),current,types=types)
            rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k!='differing_words'}),flush=True)
    (out/'layout-screens.json').write_text(json.dumps(rows,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schedules',action='store_true')
    parser.add_argument('--addresses',action='store_true')
    parser.add_argument('--interfaces',action='store_true')
    parser.add_argument('--profiles',action='store_true')
    parser.add_argument('--layouts',action='store_true')
    parser.add_argument('--returns',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/BUILD
    if args.profiles:
        profile_screens(root,out)
        return
    if args.layouts:
        layout_screens(root,out)
        return
    rows=[]
    forms=return_variants() if args.returns else interface_variants() if args.interfaces else address_variants() if args.addresses else schedule_variants() if args.schedules else variants()
    for label,body in forms:
        _,_,row=measure(root,out,label,body)
        rows.append(row)
        print(json.dumps({key:value for key,value in row.items() if key!='differing_words'}),flush=True)
    filename='return-screens.json' if args.returns else 'interface-screens.json' if args.interfaces else 'address-screens.json' if args.addresses else 'schedule-screens.json' if args.schedules else 'screens.json'
    (out/filename).write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    main()
