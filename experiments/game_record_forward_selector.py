"""Recover the nearest strictly forward record's actor and output pair."""
import argparse
from contextlib import contextmanager
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.experiments.game_record_heading_clamp import compile_owner
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.pad_generated_object import parse_object
from tools.pad_generated_object import emit_padded_assembly
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-record-forward-selector'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_150883B0',0x150883B0,0xB5860,107
TABLE,COUNT,ACTORS,LIMIT=0x800872A0,0x800D2398,0x800CC2D0,0x8009DA00
INPUTS={
    'conker/src/game/generated_B3020.c':'eaee25d9babb94f5ae8ba8f6ffa9476c9118ff81749c5ef74b626a1bbf2ec208',
    'conker/build/conker.us.elf':'40f55fff85c81f794705962d4e5311ff4ad2bcdf29dbc5462036515135b00eb2',
    'conker/retail_word_patches.us.csv':'5beb07aa1970717fe8fcb1aef89c3381dc51ceb30cc35f0cc7ce9ee24edbc91a',
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
    'conker/src/game_77AD0.c':'13a6c3e9988e846027f06a092eac6935e65b86043268af16f6678db83ffe01e8',
    'conker/asm/nonmatchings/game_77AD0/func_150538CC.s':'8eae20dabdb030db3b808c35bc6cb63c94963662a754437e5d3d79f9dfecc79a',
}
SELECTED='''/* Select the nearest strictly forward actor, optionally restricted by record tag. */
u8 *func_150883B0(s32 recordIndex, s32 direction, f32 *outValue, s32 *outTag) {
    extern f32 D_8009DA00;
    u8 *table = D_800872A0;
    u8 *record;
    u8 *actor;
    u8 *selected;
    s32 i;
    s8 tag;
    s8 excluded;
    f32 sign;
    f32 x;
    f32 z;
    f32 bias;
    f32 minimum;
    f32 distance;

    if (table == 0) {
        return 0;
    }
    record = table + recordIndex * 0x84;
    if (direction >= 0) {
        sign = -1.0f;
    } else {
        sign = 1.0f;
    }
    actor = D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C;
    x = *(f32 *)(record + 0x0C) * sign;
    z = *(f32 *)(record + 0x10) * sign;
    tag = *(s8 *)(record + 0x2F);
    excluded = *(u8 *)(actor + 0x124) - 1;
    bias = -(x * *(f32 *)(actor + 0x14) + z * *(f32 *)(actor + 0x1C));
    minimum = D_8009DA00;
    selected = 0;
    for (i = 0; i < D_800D2398; i++) {
        record = D_800872A0 + i * 0x84;
        if (*(s8 *)(record + 0x31) != excluded &&
            (tag == 0 || *(s8 *)(record + 0x2F) == tag)) {
            actor = D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C;
            distance = x * *(f32 *)(actor + 0x14) + z * *(f32 *)(actor + 0x1C) + bias;
            if (0.0f < distance && distance < minimum) {
                minimum = distance;
                *outValue = *(f32 *)record;
                *outTag = *(s8 *)(record + 0x2F);
                selected = D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C;
            }
        }
    }
    return selected;
}
'''
INITIAL=SELECTED
raw_read,raw_text=Path.read_bytes,Path.read_text


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150883B0() {\n    return 0;\n}':
        raise ValueError('Unknown forward selector placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def forms():
    yield 'initial',INITIAL
    yield 'wide-tag',INITIAL.replace('    s8 tag;','    s32 tag;')
    yield 'wide-excluded',INITIAL.replace('    s8 excluded;','    s32 excluded;').replace(
        'excluded = *(u8 *)(actor + 0x124) - 1;', 'excluded = (s8)(*(u8 *)(actor + 0x124) - 1);')
    yield 'cached-count',INITIAL.replace('    s32 i;', '    s32 i;\n    s32 count;').replace(
        '    tag = ', '    count = D_800D2398;\n    tag = ',1).replace(
        'i < D_800D2398', 'i < count').replace(
        '                selected = D_', '                count = D_800D2398;\n                selected = D_')
    inline=INITIAL.replace('    f32 bias;\n','').replace(
        '    bias = -(x * *(f32 *)(actor + 0x14) + z * *(f32 *)(actor + 0x1C));\n','').replace(
        '    u8 *selected;','    u8 *selected;\n    u8 *origin;').replace(
        '    tag = *(s8 *)(record + 0x2F);','    origin = actor;\n    tag = *(s8 *)(record + 0x2F);').replace(
        ' + bias;', ' + -(x * *(f32 *)(origin + 0x14) + z * *(f32 *)(origin + 0x1C));')
    yield 'inline',inline
    explicit=inline.replace('    s32 i;', '    s32 i;\n    s32 offset;').replace(
        '    for (i = 0; i < D_800D2398; i++) {',
        '    i = 0;\n    if (D_800D2398 > 0) {\n        offset = 0;\n        do {\n        i++;').replace(
        'D_800872A0 + i * 0x84;', 'D_800872A0 + offset;').replace(
        '    }\n    return selected;', '        offset += 0x84;\n        } while (i < D_800D2398);\n    }\n    return selected;')
    yield 'inline-do',explicit
    reordered=explicit.replace('    actor = D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C;\n','',1).replace(
        '    origin = actor;\n    tag = *(s8 *)(record + 0x2F);',
        '    tag = *(s8 *)(record + 0x2F);\n    actor = D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C;\n    origin = actor;')
    yield 'inline-do-reordered',reordered
    yield 'inline-do-reordered-dynamic-exclude',reordered.replace('    s8 excluded;\n','').replace(
        '    excluded = *(u8 *)(actor + 0x124) - 1;\n','').replace(
        '!= excluded', '!= (s8)(*(u8 *)(origin + 0x124) - 1)')
    yield 'inline-do-indexed',reordered.replace('    s32 offset;\n','').replace(
        '        offset = 0;\n','').replace('        i++;\n','').replace(
        'D_800872A0 + offset;', 'D_800872A0 + i * 0x84;').replace(
        '        offset += 0x84;', '        i++;')
    coords=INITIAL.replace('    f32 x;', '    f32 actorX;\n    f32 actorZ;\n    f32 x;').replace(
        '    tag = *(s8 *)(record + 0x2F);',
        '    tag = *(s8 *)(record + 0x2F);\n    actorX = *(f32 *)(actor + 0x14);\n    actorZ = *(f32 *)(actor + 0x1C);').replace(
        '    bias = -(x * *(f32 *)(actor + 0x14) + z * *(f32 *)(actor + 0x1C));',
        '    bias = -(x * actorX + z * actorZ);').replace(
        '            distance = x * *(f32 *)(actor + 0x14) + z * *(f32 *)(actor + 0x1C) + bias;',
        '            actorX = *(f32 *)(actor + 0x14);\n            actorZ = *(f32 *)(actor + 0x1C);\n            distance = x * actorX + z * actorZ + bias;')
    yield 'coordinate-locals',coords
    for name,decls in (
        ('coords-first','    f32 actorX;\n    f32 actorZ;\n    f32 sign;\n    f32 x;\n    f32 z;\n    f32 bias;\n    f32 minimum;\n    f32 distance;'),
        ('coords-last','    f32 sign;\n    f32 x;\n    f32 z;\n    f32 bias;\n    f32 minimum;\n    f32 distance;\n    f32 actorX;\n    f32 actorZ;'),
        ('distance-first','    f32 distance;\n    f32 x;\n    f32 z;\n    f32 sign;\n    f32 minimum;\n    f32 actorX;\n    f32 actorZ;\n    f32 bias;')):
        lo=coords.index('    f32 sign;');hi=coords.index('\n\n    if (table')
        yield name,coords[:lo]+decls+coords[hi:]
    yield 'coordinate-reads-first',coords.replace('    x = *(f32 *)(record + 0x0C) * sign;\n    z = *(f32 *)(record + 0x10) * sign;\n','').replace(
        '    actorZ = *(f32 *)(actor + 0x1C);','    actorZ = *(f32 *)(actor + 0x1C);\n    x = *(f32 *)(record + 0x0C) * sign;\n    z = *(f32 *)(record + 0x10) * sign;',1)
    yield 'coordinate-actor-later',coords.replace('    actor = D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C;\n','',1).replace(
        '    tag = *(s8 *)(record + 0x2F);','    tag = *(s8 *)(record + 0x2F);\n    actor = D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C;',1)
    yield 'coordinate-locals-do',coords.replace('    s32 i;', '    s32 i;\n    s32 offset;').replace(
        '    for (i = 0; i < D_800D2398; i++) {',
        '    i = 0;\n    if (D_800D2398 > 0) {\n        offset = 0;\n        do {\n        i++;').replace(
        'D_800872A0 + i * 0x84;', 'D_800872A0 + offset;').replace(
        '    }\n    return selected;', '        offset += 0x84;\n        } while (i < D_800D2398);\n    }\n    return selected;')
    reads_first=coords.replace('    x = *(f32 *)(record + 0x0C) * sign;\n    z = *(f32 *)(record + 0x10) * sign;\n','').replace(
        '    actorZ = *(f32 *)(actor + 0x1C);','    actorZ = *(f32 *)(actor + 0x1C);\n    x = *(f32 *)(record + 0x0C) * sign;\n    z = *(f32 *)(record + 0x10) * sign;',1)
    reuse=reads_first.replace('    s8 tag;\n','').replace('tag = *(s8 *)','direction = *(s8 *)').replace(
        '(tag == 0 || *(s8 *)(record + 0x2F) == tag)', '(direction == 0 || *(s8 *)(record + 0x2F) == direction)')
    yield 'reuse-direction',reuse
    yield 'reuse-direction-commuted',reuse.replace('D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C',
        '*(s8 *)(record + 0x31) * 0x32C + D_800CC2D0')
    for before in ('    excluded = ', '    bias = ', '    minimum = '):
        yield 'select-before-'+before.strip().split()[0],reuse.replace('    selected = 0;\n','').replace(
            before,'    selected = 0;\n'+before,1)


SELECTED=dict(forms())['select-before-excluded']
RAW_SHA='d1222b5cfa28fa22a0982acda75f77034daf94e5a1cdc328fcd733a74fe0a76f'
AFTER={
    'conker/build/conker.us.elf':'963b19f2f16d695e93aa85ac2b1a8aaaff08f865f3af843c0f0e736d43a806d4',
    'conker/src/game/generated_B3020.c':'478b47b1e70f3b49c9b45f8b2d5dd1a9e22570ac871e71f03318a64d553ebcb8',
    'conker/retail_word_patches.us.csv':'dcdd24364339be141dc68c91756fb2450414e06b736d863109a81f80628b2a35',
}


def measure(root,out,label='selected',body=None):
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>107I',values['conker/conker.us.bin'],ROM)
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    row=dict(words=len(words),diagnostics=diagnostics,frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        different=[(i,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def renamed(word,roles):
    op,rs=word>>26,(word>>21)&31
    fields=([21,16,11] if op==0 else
        [21,16] if op in (9,32,35,36,43,4,5,20,21) else
        [21] if op in (1,6,49,57) else
        [16] if op==15 or (op==17 and rs in (0,4)) else [])
    if not fields and op!=17:raise ValueError('Unknown forward selector rename opcode')
    for shift in fields:
        r=(word>>shift)&31;word=(word&~(31<<shift))|(roles.get(r,r)<<shift)
    return word


def normalized(words):
    if len(words)!=107:raise ValueError('Forward selector requires all 107 words')
    result=list(words)
    # Argument registers die before these actor/counter roles begin; all FPRs stay fixed.
    for i in range(26,100):
        result[i]=renamed(result[i],{12:13,13:12,10:9,6:4,8:6,9:8,4:10})
    # The original own-record V1 dies before the loop's row/id V0/V1 roles start.
    for i in range(58,97):result[i]=renamed(result[i],{2:3,3:2})
    for i in (39,69,95):
        w=result[i]
        if w>>26 or w&63!=33:raise ValueError('Expected commutative actor address addition')
        result[i]=(w&~(1023<<16))|(((w>>16)&31)<<21)|(((w>>21)&31)<<16)
    return result


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    expected={12:[('R_MIPS_HI16','D_800872A0')],16:[('R_MIPS_LO16','D_800872A0')],
        124:[('R_MIPS_HI16','D_800CC2D0')],128:[('R_MIPS_LO16','D_800CC2D0')],
        136:[('R_MIPS_HI16','D_800D2398')],140:[('R_MIPS_LO16','D_800D2398')],
        144:[('R_MIPS_HI16','D_8009DA00')],196:[('R_MIPS_LO16','D_8009DA00')],
        344:[('R_MIPS_HI16','D_800D2398')],368:[('R_MIPS_LO16','D_800D2398')]}
    if len(raw)!=428 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown forward selector body or ten bindings')
    return raw,bindings


def owner_guards(raw,bindings):
    words=list(struct.unpack('>107I',raw));fixed=normalized(words);rows=[]
    for i,(a,b) in enumerate(zip(words,fixed)):
        if a==b:continue
        binding=';'.join(kind+':'+name for kind,name in bindings.get(i*4,[])) or '-'
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
            replacement='0x%08X'%b,expected_relocations=binding,replacement_relocations=binding,
            note='Normalize forward selector register roles and commutative actor addresses',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=37:raise ValueError('Expected thirty-seven forward selector guards')
    return rows


def recovered_guards(before,raw,bindings):
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):
        raise ValueError('Preexisting forward selector guards')
    if not before.endswith(b'\n'):raise ValueError('Guard prefix lacks line terminator')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=reader.fieldnames,lineterminator='\r\n')
    writer.writerows(owner_guards(raw,bindings));return before+out.getvalue().encode()


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified');raw,bindings=checked_object(obj)
    truth=list(struct.unpack_from('>107I',values['conker/conker.us.bin'],ROM))
    if normalized(words)!=truth:raise ValueError('Forward selector role normalization differs from retail')
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if row['diagnostics'] or diagnostics or row['differences']!=37 or normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed forward selector diagnostics/shape/pools')
    guards=out/'qualified-guards.csv';guards.write_bytes(recovered_guards(values['conker/retail_word_patches.us.csv'],raw,bindings))
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/B3020.s',filename=OWNER,word_patches_path=guards))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=428 or data[f['value']:f['value']+428]!=values['conker/conker.us.bin'][ROM:ROM+428]:
        raise ValueError('Padded forward selector differs from retail')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected forward selector linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,428)
    if image[at:at+428]!=values['conker/conker.us.bin'][ROM:ROM+428]:raise ValueError('Forward selector prediction slot mismatch')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Forward selector prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_B3020.c':recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':raw_read(out/'qualified-guards.csv')}
    for p,data in [*expected.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else 'after-owner' if p.endswith('.c') else 'after-guards' if p.endswith('.csv') else p)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first forward selector successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=107,
        raw_differences=37,guards=37,frame=32,functions=len(a),neighbors=row['neighbors'],bytes=len(image))
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n');return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner' if p.endswith('.c') else 'after-guards')) for p in AFTER}
    if not values or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed exact forward selector successor')
    return values


@contextmanager
def checkpoint_context():
    with patch.multiple(checkpoint,INPUTS=INPUTS,AFTER=AFTER,expected_inputs=expected_inputs):yield


def verify(root,out,installed=False):
    with checkpoint_context():return checkpoint.verify(root,out,installed)


@contextmanager
def historical_view(root,out):
    with checkpoint_context(),checkpoint.historical_view(root,out):yield


def audit(root,out):
    verify(root,out,True)
    from tools.match_progress import load_elf_functions
    from tools.tests.test_game_one_shot_timer_match import canonical_symbols,symbol_rows
    from tools.check_game_data_layout import audit_layout
    before=raw_read(out/'before-01');actual=raw_read(root/'conker/build/conker.us.elf')
    if actual!=raw_read(out/'first-predicted.elf'):raise ValueError('Forward selector image differs from first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Forward selector changed other bodies/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],428,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Forward selector changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    raw,bindings=checked_object(out/'qualified.o')
    if raw_read(root/'conker/retail_word_patches.us.csv')!=recovered_guards(raw_read(out/'before-02'),raw,bindings):
        raise ValueError('Forward selector guards differ from appended rows')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Forward selector changed protected Game data')
    result=dict(functions=len(a),only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),new_guards=37,old_guard_prefix_unchanged=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forms',action='store_true');parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    if args.forms:
        for name,body in forms():
            row=measure(root,root/BUILD,name,body)[2]
            print(json.dumps(dict(name=name,words=row['words'],frame=row['frame'],differences=row['differences'],sha=row['raw_sha256'])),flush=True)
    else:print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
