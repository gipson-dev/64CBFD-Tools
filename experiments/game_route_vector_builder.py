"""Recover four route control points with ordered signed-coordinate interpolation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from unittest.mock import patch

from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.experiments.game_record_heading_clamp import compile_owner
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.pad_generated_object import parse_object
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools

BUILD='conker/build/game-route-vector-builder'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_15088F30',0x15088F30,0xB63E0,83
INPUTS={
    'conker/src/game/generated_B3020.c':'ce0cf9b5504e5b41b267c09d69c3bdc9ed2f24533ed7de0dd68935bd678f467f',
    'conker/build/conker.us.elf':'a5c5541dc8f6863ebefac2896237ce0bc39a88e3893711c35cd0393fd851ecd7',
    'conker/retail_word_patches.us.csv':'eb4dc7f42da17c278c908b8e5ab721c4b420edd2210b4a691c343b8aa0fcfd42',
    'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/B3020.s':'26ef139d5592329ed22f9287267c13fefadf7f17290bc5ef1085cbe20e80b187',
    'conker/Makefile':'840897f11d9fea8109c4e67c57e927efa6e1686de2b399fec2c9025828b92d49',
    'conker/symbol_addrs.us.txt':'d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    'conker/include/structs.h':'081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'conker/include/2.0L/PR/sched.h':'40a7e05e5e774a3cbc015d44bb8225f469937de178bfe84cd1de9ef3c5ff7572',
    'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'ido/ido5.3_recomp/cfe':'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9',
    'ido/ido5.3_recomp/uopt':'23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ido/ido5.3_recomp/ugen':'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d',
}
INITIAL='''/* Build four control points, using the first type-four route neighbor. */
void func_15088F30(u8 *record, f32 *x, f32 *y, f32 *z) {
    u8 *cursor = record;
    u8 *table;
    u8 *route;
    u8 *other;
    s32 slot = 0;
    s32 id;
    s32 candidate;
    s32 i;
    s32 currentX;
    s32 nextX;
    f32 speed;
    f32 deltaX;
    f32 deltaZ;

    do {
        id = cursor[0x2B];
        cursor++;
        if (id != 0xFF) {
            table = D_800D2350;
            route = table + id * 0x10;
            other = route;
            for (i = 0; i < 5; i++) {
                candidate = route[i + 9];
                if (candidate != 0xFF && table[candidate * 0x10 + 0xE] == 4) {
                    other = table + candidate * 0x10;
                    break;
                }
            }
            currentX = *(s16 *)(route + 0);
            nextX = *(s16 *)(other + 0);
            speed = *(f32 *)record;
            deltaX = (f32)(nextX - currentX);
            deltaZ = (f32)(*(s16 *)(other + 4) - *(s16 *)(route + 4));
            *x = (f32)currentX + deltaX * speed;
            *y = (f32)*(s16 *)(route + 2);
            *z = (f32)*(s16 *)(route + 4) + deltaZ * *(f32 *)record;
        } else {
            *x = (f32)(slot * 64);
            *y = 0.0f;
            *z = 0.0f;
        }
        slot++;
        x++;
        y++;
        z++;
    } while (slot != 4);
}
'''
RECONSTRUCTED='''/* Build four control points, using the first type-four route neighbor. */
void func_15088F30(u8 *record, f32 *xOutput, f32 *yOutput, f32 *zOutput) {
    f32 *x;
    f32 *y;
    f32 *z;
    u8 *cursor;
    s16 currentX;
    s32 i;
    s32 slot;
    u8 id;
    u8 candidate;
    void *route;
    void *other;

    slot = 0;
    cursor = record;
    x = xOutput;
    y = yOutput;
    z = zOutput;
    do {
        id = cursor[0x2B];
        cursor++;
        if (id != 0xFF) {
            i = 0;
            route = id * 0x10 + D_800D2350;
            other = route;
            do {
                candidate = *((u8 *)route + i + 9);
                if (candidate != 0xFF && *(u8 *)(D_800D2350 + candidate * 0x10 + 0xE) == 4) {
                    other = candidate * 0x10 + D_800D2350;
                    i = 5;
                }
                i++;
            } while (i < 5);
            currentX = *(s16 *)route;
            *x = (f32)currentX + (f32)(*(s16 *)other - currentX) * *(f32 *)record;
            *y = (f32)*(s16 *)((u8 *)route + 2);
            *z = (f32)*(s16 *)((u8 *)route + 4) +
                (f32)(*(s16 *)((u8 *)other + 4) - *(s16 *)((u8 *)route + 4)) * *(f32 *)record;
        } else {
            *x = (f32)(slot << 6);
            *y = 0.0f;
            *z = 0.0f;
        }
        slot++;
        x++;
        y++;
        z++;
    } while (slot != 4);
}
'''
raw_read,raw_text=Path.read_bytes,Path.read_text


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15088F30() {\n    return 0;\n}':raise ValueError('Unknown route vector placeholder')
    text=before[:lo]+body.rstrip()+before[hi:]
    declaration='    extern s32 func_15088F30();'
    if text.count(declaration)!=1:raise ValueError('Unknown route vector caller declaration')
    signature=re.search(r'^(void|s32) func_15088F30\((u8|void|f32) \*record,',body,re.M)
    if not signature:raise ValueError('Unknown vector interface candidate')
    result,first=signature.groups()
    text=text.replace(declaration,'    extern '+result+' func_15088F30('+first+' *, f32 *, f32 *, f32 *);')
    if first=='f32':text=text.replace('func_15088F30(record, x, y, z);','func_15088F30((f32 *)record, x, y, z);')
    return text


def forms():
    yield 'reconstructed',RECONSTRUCTED
    yield 'reconstructed-char',RECONSTRUCTED.replace('void *route;','u8 *route;').replace('void *other;','u8 *other;')
    yield 'initial',INITIAL
    assigned=INITIAL.replace('                    break;','                    i = 5;')
    yield 'assigned-exit',assigned
    for label,body in (('break',INITIAL),('assigned',assigned)):
        yield label+'-split-gates',body.replace('                if (candidate != 0xFF && table[candidate * 0x10 + 0xE] == 4) {',
            '                if (candidate != 0xFF) {\n                    if (table[candidate * 0x10 + 0xE] == 4) {').replace(
            '                    break;\n                }','                    break;\n                    }\n                }').replace(
            '                    i = 5;\n                }','                    i = 5;\n                    }\n                }')
        yield label+'-pointer-loop',body.replace('    s32 currentX;', '    u8 *neighbor;\n    s32 currentX;').replace(
            '            for (i = 0; i < 5; i++) {', '            neighbor = route;\n            for (i = 0; i < 5; i++, neighbor++) {').replace(
            'candidate = route[i + 9];','candidate = neighbor[9];')
        yield label+'-do-loop',body.replace('            for (i = 0; i < 5; i++) {',
            '            i = 0;\n            do {').replace('            currentX =',
            '            currentX =',1).replace('            }\n            currentX =',
            '                i++;\n            } while (i < 5);\n            currentX =')
    yield 'direct-next-x',assigned.replace('    s32 nextX;\n','').replace('            nextX = *(s16 *)(other + 0);\n','').replace(
        '            speed = *(f32 *)record;\n            deltaX = (f32)(nextX - currentX);',
        '            deltaX = (f32)(*(s16 *)(other + 0) - currentX);\n            speed = *(f32 *)record;')
    base=assigned.replace('    f32 speed;','    f32 baseX;\n    f32 speed;').replace(
        '            deltaX = (f32)(nextX - currentX);','            baseX = (f32)currentX;\n            deltaX = (f32)(nextX - currentX);').replace(
        '*x = (f32)currentX +','*x = baseX +')
    for label,body in (('base-x',base),('base-x-before-speed',base.replace('            speed = *(f32 *)record;\n            baseX = (f32)currentX;',
            '            baseX = (f32)currentX;\n            speed = *(f32 *)record;'))):
        yield label,body
        yield label+'-integer-other',body.replace('other = table + candidate * 0x10;',
            'other = (u8 *)((s32)table + candidate * 0x10);')
        yield label+'-half-other',body.replace('other = table + candidate * 0x10;',
            'other = (u8 *)((s16 *)table + candidate * 8);')
        yield label+'-float-base-z',body.replace('    f32 baseX;','    f32 baseZ;\n    f32 baseX;').replace(
            '            *z = (f32)*(s16 *)(route + 4) + deltaZ * *(f32 *)record;',
            '            baseZ = (f32)*(s16 *)(route + 4);\n            *z = baseZ + deltaZ * *(f32 *)record;')
    for label,body in (('assigned',assigned),('base',base)):
        for kind,form in (
                ('slot-first',body.replace('    u8 *cursor = record;\n','').replace('    s32 slot = 0;',
                    '    s32 slot = 0;\n    u8 *cursor = record;')),
                ('explicit-inits',body.replace('    u8 *cursor = record;','    u8 *cursor;').replace('    s32 slot = 0;','    s32 slot;').replace(
                    '    do {\n','    slot = 0;\n    cursor = record;\n    do {\n',1)),
                ('reverse-explicit',body.replace('    u8 *cursor = record;','    u8 *cursor;').replace('    s32 slot = 0;','    s32 slot;').replace(
                    '    do {\n','    cursor = record;\n    slot = 0;\n    do {\n',1))):
            yield label+'-'+kind,form
    expressions=assigned.replace('    s32 currentX;\n','').replace('    s32 nextX;\n','').replace('    f32 speed;\n','').replace(
        '''            currentX = *(s16 *)(route + 0);
            nextX = *(s16 *)(other + 0);
            speed = *(f32 *)record;
            deltaX = (f32)(nextX - currentX);''',
        '            deltaX = (f32)(*(s16 *)(other + 0) - *(s16 *)(route + 0));').replace(
        '            *x = (f32)currentX + deltaX * speed;',
        '            *x = (f32)*(s16 *)(route + 0) + deltaX * *(f32 *)record;')
    yield 'expressions',expressions
    yield 'expressions-slot-first',expressions.replace('    u8 *cursor = record;\n','').replace('    s32 slot = 0;',
        '    s32 slot = 0;\n    u8 *cursor = record;')
    early=expressions.replace('    f32 deltaX;','    f32 baseX;\n    f32 deltaX;').replace(
        '            deltaX = (f32)', '            baseX = (f32)*(s16 *)(route + 0);\n            deltaX = (f32)',1).replace(
        '*x = (f32)*(s16 *)(route + 0) +','*x = baseX +')
    yield 'early-base-load',early
    yield 'early-base-slot-first',early.replace('    u8 *cursor = record;\n','').replace('    s32 slot = 0;',
        '    s32 slot = 0;\n    u8 *cursor = record;')
    for label,body in (('assigned',assigned),('base',base),('expressions',expressions),('early',early)):
        yield 'word-return-'+label,body.replace('void func_15088F30','s32 func_15088F30').replace(
            '    } while (slot != 4);','    } while (slot != 4);\n    return slot;')
        typed=body.replace('    u8 *table;\n    u8 *route;\n    u8 *other;',
            '''    typedef struct {
        s16 x, y, z;
        u8 reserved[3];
        u8 neighbors[5];
        u8 type;
        u8 kind;
    } RouteVector;
    RouteVector *table;
    RouteVector *route;
    RouteVector *other;''').replace('table = D_800D2350;','table = (RouteVector *)D_800D2350;').replace(
            'route = table + id * 0x10;','route = table + id;').replace('candidate = route[i + 9];','candidate = route->neighbors[i];').replace(
            'table[candidate * 0x10 + 0xE]','table[candidate].type').replace('other = table + candidate * 0x10;','other = table + candidate;')
        for field,off in (('x','0'),('y','2'),('z','4')):
            for pointer in ('route','other'):typed=typed.replace('*(s16 *)('+pointer+' + '+off+')',pointer+'->'+field)
        yield 'typed-'+label,typed
    for label,body in (('assigned',assigned),('base',base)):
        for variable in ('id','candidate','slot','i'):
            for dtype in ('u8','u32'):
                yield label+'-'+variable+'-'+dtype,body.replace('    s32 '+variable+';', '    '+dtype+' '+variable+';').replace(
                    '    s32 '+variable+' = 0;','    '+dtype+' '+variable+' = 0;')
    inline=assigned.replace('    s32 nextX;\n','').replace('    f32 speed;\n','').replace('    f32 deltaX;\n','').replace('    f32 deltaZ;\n','').replace(
        '''            nextX = *(s16 *)(other + 0);
            speed = *(f32 *)record;
            deltaX = (f32)(nextX - currentX);
            deltaZ = (f32)(*(s16 *)(other + 4) - *(s16 *)(route + 4));
            *x = (f32)currentX + deltaX * speed;''',
        '            *x = (f32)currentX + (f32)(*(s16 *)(other + 0) - currentX) * *(f32 *)record;').replace(
        '*z = (f32)*(s16 *)(route + 4) + deltaZ * *(f32 *)record;',
        '*z = (f32)*(s16 *)(route + 4) + (f32)(*(s16 *)(other + 4) - *(s16 *)(route + 4)) * *(f32 *)record;')
    for label,body in (('assigned',assigned),('base',base),('inline',inline)):
        yield 'inline-'+label,body
        local=body.replace('f32 *x, f32 *y, f32 *z)', 'f32 *xOutput, f32 *yOutput, f32 *zOutput)').replace(
            '    u8 *cursor = record;', '    f32 *x;\n    f32 *y;\n    f32 *z;\n    u8 *cursor;').replace(
            '    s32 slot = 0;','    s32 slot;').replace('    do {\n',
            '    slot = 0;\n    cursor = record;\n    x = xOutput;\n    y = yOutput;\n    z = zOutput;\n    do {\n',1)
        yield 'local-outputs-'+label,local
        yield 'local-outputs-'+label+'-byte-ids',local.replace('    s32 id;','    u8 id;').replace('    s32 candidate;','    u8 candidate;').replace(
            '    s32 currentX;', '    s16 currentX;')
    for label,body in (('assigned',assigned),('inline',inline)):
        direct=body.replace('    u8 *table;\n','').replace('            table = D_800D2350;\n','').replace('table +','D_800D2350 +').replace(
            'table[candidate * 0x10 + 0xE]','D_800D2350[candidate * 0x10 + 0xE]')
        for order,form in (('pointer-first',direct),('integer-first',direct.replace('D_800D2350 + id * 0x10','id * 0x10 + D_800D2350').replace(
                'D_800D2350 + candidate * 0x10','candidate * 0x10 + D_800D2350'))):
            yield 'globals-'+label+'-'+order,form
            yield 'globals-'+label+'-'+order+'-bytes',form.replace('    s32 id;','    u8 id;').replace('    s32 candidate;','    u8 candidate;').replace(
                '    s32 currentX;', '    s16 currentX;')
    for label,body in (('assigned',assigned),('base',base),('inline',inline)):
        indexed=body.replace('        x++;\n','').replace('        y++;\n','').replace('        z++;\n','')
        for axis in ('x','y','z'):indexed=indexed.replace('*'+axis+' =',axis+'[slot] =')
        yield 'indexed-output-'+label,indexed
        indexed=indexed.replace('    u8 *cursor = record;\n','').replace('        id = cursor[0x2B];\n        cursor++;',
            '        id = record[0x2B + slot];')
        yield 'indexed-all-'+label,indexed
        yield 'indexed-all-'+label+'-bytes',indexed.replace('    s32 id;','    u8 id;').replace('    s32 candidate;','    u8 candidate;').replace(
            '    s32 currentX;','    s16 currentX;')
    for label,body in (('assigned',assigned),('base',base),('inline',inline)):
        yield label+'-short-x',body.replace('    s32 currentX;','    s16 currentX;').replace('    s32 nextX;','    s16 nextX;')
        yield label+'-shared-byte',body.replace('    s32 candidate;\n','').replace('candidate','id')
        yield label+'-register-outputs',body.replace('f32 *x, f32 *y, f32 *z)',
            'register f32 *x, register f32 *y, register f32 *z)')
        for pointer in ('void','f32'):
            converted=body.replace('u8 *record,',pointer+' *record,').replace('u8 *cursor = record;',
                'u8 *cursor = (u8 *)record;')
            yield label+'-record-'+pointer,converted
    for label,body in (('assigned',assigned),('base',base)):
        for cast,expression in (('byte','(u8)candidate'),('half','(u16)candidate'),('unsigned','(u32)candidate'),
                ('mask-byte','(candidate & 0xFF)'),('mask-half','(candidate & 0xFFFF)')):
            yield label+'-other-'+cast,body.replace('other = table + candidate * 0x10;',
                'other = table + ('+expression+') * 0x10;')
        index=body.replace('    u8 *other;', '    s32 chosen;').replace('other = route;', 'chosen = id;').replace(
            'other = table + candidate * 0x10;', 'chosen = candidate;').replace(
            '*(s16 *)(other + 0)', '*(s16 *)(table + chosen * 0x10)').replace(
            '*(s16 *)(other + 4)', '*(s16 *)(table + chosen * 0x10 + 4)')
        yield label+'-chosen-index',index
    for label,body in (('assigned',assigned),('inline',inline)):
        transport=body.replace('f32 *x, f32 *y, f32 *z)', 'f32 *xOutput, f32 *yOutput, f32 *zOutput)').replace(
            '    u8 *cursor = record;', '    u32 x = (u32)xOutput;\n    u32 y = (u32)yOutput;\n    u32 z = (u32)zOutput;\n    u8 *cursor = record;')
        for axis in ('x','y','z'):transport=transport.replace('*'+axis+' =','*(f32 *)'+axis+' =').replace('        '+axis+'++;','        '+axis+' += 4;')
        yield 'word-output-'+label,transport
        yield 'word-all-'+label,transport.replace('    u8 *cursor = record;', '    u32 cursor = (u32)record;').replace(
            'id = cursor[0x2B];', 'id = *(u8 *)(cursor + 0x2B);')
    for mul_x in (False,True):
        for add_x in (False,True):
            for mul_z in (False,True):
                for add_z in (False,True):
                    body=assigned
                    x_product='speed * deltaX' if mul_x else 'deltaX * speed'
                    z_product='*(f32 *)record * deltaZ' if mul_z else 'deltaZ * *(f32 *)record'
                    x_base='(f32)currentX';z_base='(f32)*(s16 *)(route + 4)'
                    body=body.replace('*x = (f32)currentX + deltaX * speed;',
                        '*x = '+(x_product+' + '+x_base if add_x else x_base+' + '+x_product)+';').replace(
                        '*z = (f32)*(s16 *)(route + 4) + deltaZ * *(f32 *)record;',
                        '*z = '+(z_product+' + '+z_base if add_z else z_base+' + '+z_product)+';')
                    yield 'operands-'+''.join(str(int(v)) for v in (mul_x,add_x,mul_z,add_z)),body
    for label,body in (('assigned',assigned),('inline',inline),('reconstructed',RECONSTRUCTED)):
        for register in ('','register '):
            named=body.replace('    do {\n', '    do {\n',1).replace(
                '    u8 *cursor', '    '+register+'u8 **tableSource = &D_800D2350;\n    '+register+'s32 pointCount = 4;\n    u8 *cursor',1)
            named=named.replace('table = D_800D2350;', 'table = *tableSource;').replace(
                'id * 0x10 + D_800D2350','id * 0x10 + *tableSource').replace(
                'candidate * 0x10 + D_800D2350','candidate * 0x10 + *tableSource').replace(
                '*(u8 *)(D_800D2350 + candidate * 0x10 + 0xE)', '*(u8 *)(*tableSource + candidate * 0x10 + 0xE)').replace(
                '== 4)', '== pointCount)').replace('slot != 4','slot != pointCount')
            yield 'named-invariants-'+label+('-register' if register else ''),named
    captured=RECONSTRUCTED.replace('    void *route;','    u8 *table;\n    void *route;').replace(
        '            i = 0;','            table = D_800D2350;\n            i = 0;').replace(
        'id * 0x10 + D_800D2350','id * 0x10 + table').replace(
        'candidate * 0x10 + D_800D2350','candidate * 0x10 + table').replace(
        '*(u8 *)(D_800D2350 + candidate * 0x10 + 0xE)','*(u8 *)(table + candidate * 0x10 + 0xE)')
    for label,body in (('captured',captured),('direct',RECONSTRUCTED)):
        for z_first in (False,True):
            form=body
            if z_first:form=form.replace('    s16 currentX;','    f32 deltaZ;\n    s16 currentX;').replace(
                '            *x =','            deltaZ = (f32)(*(s16 *)((u8 *)other + 4) - *(s16 *)((u8 *)route + 4));\n            *x =',1).replace(
                '(f32)(*(s16 *)((u8 *)other + 4) - *(s16 *)((u8 *)route + 4)) * *(f32 *)record;',
                'deltaZ * *(f32 *)record;')
            yield 'reconstructed-'+label+('-z-first' if z_first else ''),form


def measure(root,out,label='selected',body=None):
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>83I',values['conker/conker.us.bin'],ROM)
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    row=dict(words=len(words),diagnostics=diagnostics,frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        different=[(i,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        saved=[(w>>16&31,w&65535) for w in words if w>>26==43 and w>>21&31==29],
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


SELECTED=dict(forms())['assigned-exit']
MODEL_SHA='83c683a0d268e3df6320b192ca130970b42d7de2d7dd837ae616d717e9999374'


def checked_model(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    if len(raw)!=332 or hashlib.sha256(raw).hexdigest()!=MODEL_SHA or bindings!={
            28:[('R_MIPS_HI16','D_800D2350')],44:[('R_MIPS_LO16','D_800D2350')]}:
        raise ValueError('Unknown non-installable vector model or bindings')
    return raw,bindings


def require_retail_stack_contract(words):
    """Necessary shape gate only, not a complete matching or installation gate."""
    saved=[(w>>16&31,w&65535) for w in words if w>>26==43 and w>>21&31==29]
    if len(words)!=83 or words[0]!=0x27BDFFF0 or saved!=[(17,12),(16,8)]:
        raise ValueError('Vector model is not installable: retail requires S1/SP0xC and S0/SP8 only')


def qualify_model(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified-model');checked_model(obj)
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if diagnostics or row['diagnostics'] or row['differences']!=76 or row['frame']!=16 or row['words']!=83 or row['neighbors']!=72 or \
            normalized_pools(before)!=normalized_pools(obj):raise ValueError('Changed vector model/owner evidence')
    try:require_retail_stack_contract(words)
    except ValueError:row['installable']=False
    else:raise ValueError('The recorded three-save model unexpectedly passed the retail stack gate')
    (out/'model-audit.json').write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forms',action='store_true');args=parser.parse_args()
    if args.forms:
        for name,body in forms():
            row=measure(root,root/BUILD,name,body)[2]
            print(json.dumps({k:row[k] for k in ('words','frame','differences','raw_sha256','diagnostics')}|{'name':name}),flush=True)
    else:print(json.dumps(qualify_model(root,root/BUILD)[2],indent=2))
