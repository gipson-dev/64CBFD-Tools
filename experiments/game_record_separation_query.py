"""Recover the first matching record's packed quantized separation query."""
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
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-record-separation-query'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_150882E4',0x150882E4,0xB5794,51
TABLE,COUNT=0x800872A0,0x800D2398
INPUTS={
    'conker/src/game/generated_B3020.c':'b087b1069a1e0db0629bffd448962a2c726a56b07099f1cc0735e3d5fcdfc0be',
    'conker/build/conker.us.elf':'c1e56f1d074a85813ef0e6cedd22b1d41f109ec0f60abdf43cd80914f7ec6407',
    'conker/retail_word_patches.us.csv':'8f709f6c1cb03108c0f1e6f7b460e624d76f29734c97ed5fe9739f411f2046a1',
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
    'conker/asm/CB3D0.s':'dcbd723600e63455ecdcef33eef8929dac0bf75a81ee39d960d044d34a743f06',
    'conker/src/game/generated_CB3D0.c':'898ae03067a45599844b0aadc20161340ebd76f155b04c16ed1b84194418125f',
}
SELECTED='''/* Pack the first matching non-self slot with its quantized separation. */
u32 func_150882E4(s32 recordIndex, s32 idOffset) {
    u8 *table = D_800872A0;
    u8 *record;
    u8 *candidate;
    s32 count;
    s32 wanted;
    s32 i;
    u32 distance;

    if (table == 0) {
        return 0x10;
    }
    count = D_800D2398;
    record = table + recordIndex * 0x84;
    wanted = *(s8 *)(record + 0x29) + idOffset;
    for (i = 0, candidate = table; i < count; i++, candidate += 0x84) {
        if (*(s8 *)(candidate + 0x29) == wanted && i != recordIndex) {
            distance = (u32)(s32)*(s16 *)(record + 0x24) * 16u +
                       (u32)(s32)(*(f32 *)(record + 8) * 16.0f) -
                       (u32)(s32)*(s16 *)(candidate + 0x24) * 16u -
                       (u32)(s32)(*(f32 *)(candidate + 8) * 16.0f);
            if (distance & 0x80000000u) {
                distance = 0u - distance;
            }
            return (distance << 8) | (u32)i;
        }
    }
    return 0x10;
}
'''
INITIAL=SELECTED
raw_read,raw_text=Path.read_bytes,Path.read_text


def forms():
    yield 'initial',INITIAL
    cast=INITIAL.replace('distance & 0x80000000u','(s32)distance < 0')
    yield 'signed-test',cast
    do=cast.replace('    s32 i;','    s32 i = 0;').replace(
        '    for (i = 0, candidate = table; i < count; i++, candidate += 0x84) {',
        '    if (count > 0) {\n        candidate = table;\n        do {').replace(
        '    }\n    return 0x10;\n}',
        '            i++;\n            candidate += 0x84;\n        } while (i < count);\n    }\n    return 0x10;\n}')
    for label,body in (('for',cast),('do',do)):
        yield label+'-byte-count',body.replace('    s32 count;','    s8 count;')
        yield label+'-live-bound',body.replace('i < count','i < D_800D2398')
        reuse=body.replace('    u32 distance;\n','').replace('distance = ', 'recordIndex = ').replace(
            '(s32)distance < 0','recordIndex < 0').replace('0u - distance','0u - (u32)recordIndex').replace(
            '(distance << 8)','((u32)recordIndex << 8)')
        yield label+'-reuse-index',reuse
        yield label+'-reuse-both',reuse.replace('    s32 wanted;\n','').replace(
            'wanted = *(s8 *)(record + 0x29) + idOffset;', 'idOffset += *(s8 *)(record + 0x29);').replace(
            '== wanted','== idOffset')
    yield 'do',do
    compact='''/* Pack the first matching non-self slot with its quantized separation. */
u32 func_150882E4(u32 recordIndex, u32 idOffset) {
    u8 *candidate = D_800872A0;
    u8 *record;
    s32 i;

    if (candidate == 0) {
        return 0x10;
    }
    record = candidate + recordIndex * 0x84;
    idOffset += (s32)*(s8 *)(record + 0x29);
    for (i = 0; i < D_800D2398; i++, candidate += 0x84) {
        if ((u32)(s32)*(s8 *)(candidate + 0x29) == idOffset && (u32)i != recordIndex) {
            recordIndex = (u32)(s32)*(s16 *)(record + 0x24) * 16u +
                          (u32)(s32)(*(f32 *)(record + 8) * 16.0f) -
                          (u32)(s32)*(s16 *)(candidate + 0x24) * 16u -
                          (u32)(s32)(*(f32 *)(candidate + 8) * 16.0f);
            if ((s32)recordIndex < 0) {
                recordIndex = 0u - recordIndex;
            }
            return (recordIndex << 8) | (u32)i;
        }
    }
    return 0x10;
}
'''
    yield 'compact-unsigned',compact
    yield 'compact-msb',compact.replace('(s32)recordIndex < 0','recordIndex & 0x80000000u')
    yield 'compact-count',compact.replace('    s32 i;','    s32 count;\n    s32 i;').replace(
        '    record = candidate + recordIndex * 0x84;',
        '    count = D_800D2398;\n    record = candidate + recordIndex * 0x84;').replace(
        'i < D_800D2398','i < count')
    yield 'compact-signed-index',compact.replace('u32 recordIndex,','s32 recordIndex,').replace(
        'recordIndex = 0u - recordIndex;','recordIndex = 0u - (u32)recordIndex;').replace(
        '(recordIndex << 8)','((u32)recordIndex << 8)')
    split=compact.replace('    u8 *candidate = D_800872A0;',
        '    u8 *table = D_800872A0;\n    u8 *candidate;').replace(
        'if (candidate == 0)','if (table == 0)').replace(
        'record = candidate + recordIndex * 0x84;','record = table + recordIndex * 0x84;').replace(
        'idOffset += (s32)*(s8 *)(record + 0x29);',
        'idOffset = (s32)*(s8 *)(record + 0x29) + idOffset;').replace(
        'for (i = 0; i < D_800D2398;', 'for (i = 0, candidate = table; i < D_800D2398;')
    yield 'split-for',split
    guarded=split.replace('    s32 i;','    s32 i = 0;').replace(
        '    for (i = 0, candidate = table; i < D_800D2398; i++, candidate += 0x84) {',
        '    if (D_800D2398 > 0) {\n        for (candidate = table; i < D_800D2398; i++, candidate += 0x84) {').replace(
        '    }\n    return 0x10;\n}', '        }\n    }\n    return 0x10;\n}')
    yield 'split-guarded-for',guarded
    guarded_do=guarded.replace(
        '        for (candidate = table; i < D_800D2398; i++, candidate += 0x84) {',
        '        candidate = table;\n        do {').replace(
        '        }\n    }\n    return 0x10;\n}',
        '            i++;\n            candidate += 0x84;\n        } while (i < D_800D2398);\n    }\n    return 0x10;\n}')
    yield 'split-guarded-do',guarded_do
    yield 'split-guarded-goto',guarded_do.replace('        do {','loop:').replace(
        '        } while (i < D_800D2398);',
        '        if (i >= D_800D2398) return 0x10;\n        goto loop;')
    indexed=split.replace('    for (i = 0, candidate = table; i < D_800D2398; i++, candidate += 0x84) {',
        '    for (i = 0; i < D_800D2398; i++) {\n        candidate = table + i * 0x84;')
    yield 'indexed',indexed
    for name,body in (('split',split),('indexed',indexed)):
        sequential=body.replace('''            recordIndex = (u32)(s32)*(s16 *)(record + 0x24) * 16u +
                          (u32)(s32)(*(f32 *)(record + 8) * 16.0f) -
                          (u32)(s32)*(s16 *)(candidate + 0x24) * 16u -
                          (u32)(s32)(*(f32 *)(candidate + 8) * 16.0f);''','''            recordIndex = (u32)(s32)*(s16 *)(record + 0x24) * 16u +
                          (u32)(s32)(*(f32 *)(record + 8) * 16.0f);
            recordIndex -= (u32)(s32)*(s16 *)(candidate + 0x24) * 16u;
            recordIndex -= (u32)(s32)(*(f32 *)(candidate + 8) * 16.0f);''')
        yield name+'-sequential',sequential
        yield name+'-nested',body.replace(
            'if ((u32)(s32)*(s8 *)(candidate + 0x29) == idOffset && (u32)i != recordIndex) {',
            'if ((u32)(s32)*(s8 *)(candidate + 0x29) == idOffset) {\n            if ((u32)i != recordIndex) {').replace(
            '            return (recordIndex << 8) | (u32)i;',
            '            return (recordIndex << 8) | (u32)i;\n            }')
    signed_offset=indexed.replace('u32 idOffset)','s32 idOffset)').replace(
        'idOffset = (s32)*(s8 *)(record + 0x29) + idOffset;',
        'idOffset = (u32)(s32)*(s8 *)(record + 0x29) + (u32)idOffset;').replace(
        '(u32)(s32)*(s8 *)(candidate + 0x29) == idOffset','*(s8 *)(candidate + 0x29) == idOffset')
    yield 'indexed-signed-offset',signed_offset
    for name,body in (('indexed',indexed),('indexed-signed-offset',signed_offset)):
        yield name+'-signed-products',body.replace(
            '(u32)(s32)*(s16 *)(record + 0x24) * 16u', '(u32)(*(s16 *)(record + 0x24) * 16)').replace(
            '(u32)(s32)*(s16 *)(candidate + 0x24) * 16u', '(u32)(*(s16 *)(candidate + 0x24) * 16)')
    yield 'indexed-signed-parameters',signed_offset.replace('u32 recordIndex,','s32 recordIndex,').replace(
        'recordIndex = 0u - recordIndex;','recordIndex = 0u - (u32)recordIndex;').replace(
        '(recordIndex << 8)','((u32)recordIndex << 8)')


SELECTED=dict(forms())['indexed']
RAW_SHA='da80a9bd436b7cc0ed9fbea44ab74192c3ba9bae8f93ed1ba6664754b2d38b65'
AFTER={
    'conker/build/conker.us.elf':'40f55fff85c81f794705962d4e5311ff4ad2bcdf29dbc5462036515135b00eb2',
    'conker/src/game/generated_B3020.c':'eaee25d9babb94f5ae8ba8f6ffa9476c9118ff81749c5ef74b626a1bbf2ec208',
    'conker/retail_word_patches.us.csv':'5beb07aa1970717fe8fcb1aef89c3381dc51ceb30cc35f0cc7ce9ee24edbc91a',
}


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150882E4() {\n    return 0;\n}':
        raise ValueError('Unknown record separation placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def measure(root,out,label='selected',body=None):
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>51I',values['conker/conker.us.bin'],ROM)
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    row=dict(words=len(words),diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        different=[(i,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def renamed(word,roles):
    op,fn=word>>26,word&63
    fields=([21,16,11] if op==0 and fn in (0,8,33,35,37,42) else
        [21,16] if op in (9,32,33,35,4,5,20,21) else
        [21] if op in (1,49) else
        [16] if op==17 and (word>>21)&31 in (0,4) else [])
    if not fields and op not in (15,17):raise ValueError('Unexpected separation rename opcode')
    for shift in fields:
        r=(word>>shift)&31
        word=(word&~(31<<shift))|(roles.get(r,r)<<shift)
    return word


def normalized(words):
    if len(words)!=51:raise ValueError('Separation normalization requires complete slot')
    result=list(words)
    # The offset dies at word15; the cursor starts at word16, so their roles can exchange.
    if (result[15]>>11)&31!=6 or (result[16]>>11)&31!=5:
        raise ValueError('Unknown separation cursor transition')
    result[15]=(result[15]&~(31<<11))|(5<<11)
    result[16]=(result[16]&~(31<<11))|(6<<11)
    for i in range(17,48):result[i]=renamed(result[i],{5:6,6:5})
    # The original input index is dead after word20; the final distance stays in A0.
    for i in range(27,38):result[i]=renamed(result[i],{13:12,14:13,12:4,15:14})
    for i in range(34,38):result[i]=renamed(result[i],{25:24})
    for i in range(39,44):result[i]=renamed(result[i],{10:25})
    return result


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    expected={4:[('R_MIPS_HI16','D_800872A0')],8:[('R_MIPS_LO16','D_800872A0')],
        36:[('R_MIPS_HI16','D_800D2398')],40:[('R_MIPS_LO16','D_800D2398')]}
    if len(raw)!=204 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown separation query body or four bindings')
    return raw,bindings


def owner_guards(raw,bindings):
    words=list(struct.unpack('>51I',raw));fixed=normalized(words)
    rows=[]
    for i,(a,b) in enumerate(zip(words,fixed)):
        if a==b:continue
        if i*4 in bindings:raise ValueError('Separation rename touches a relocation')
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
            replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',
            note='Normalize separation query cursor and dead-input arithmetic register roles',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=15:raise ValueError('Expected exactly fifteen separation register guards')
    return rows


def recovered_guards(before,raw,bindings):
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):
        raise ValueError('Preexisting separation query guards')
    if not before.endswith(b'\n'):raise ValueError('Guard prefix lacks line terminator')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=reader.fieldnames,lineterminator='\r\n')
    writer.writerows(owner_guards(raw,bindings))
    return before+out.getvalue().encode()


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified');raw,bindings=checked_object(obj)
    truth=list(struct.unpack_from('>51I',values['conker/conker.us.bin'],ROM))
    if normalized(words)!=truth:raise ValueError('Separation role normalization differs from retail')
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if row['diagnostics'] or diagnostics or row['differences']!=15 or normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed separation query diagnostics/shape/pools')
    guards=out/'qualified-guards.csv';guards.write_bytes(recovered_guards(values['conker/retail_word_patches.us.csv'],raw,bindings))
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/B3020.s',filename=OWNER,word_patches_path=guards))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=204 or data[f['value']:f['value']+204]!=values['conker/conker.us.bin'][ROM:ROM+204]:
        raise ValueError('Padded separation query differs from retail')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected separation query linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,204)
    if image[at:at+204]!=values['conker/conker.us.bin'][ROM:ROM+204]:raise ValueError('Separation prediction slot mismatch')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Separation prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_B3020.c':recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':raw_read(out/'qualified-guards.csv')}
    for p,data in [*expected.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else 'after-owner' if p.endswith('.c') else 'after-guards' if p.endswith('.csv') else p)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first separation successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=51,
        raw_differences=15,guards=15,frame=0,functions=len(a),neighbors=row['neighbors'],bytes=len(image))
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner' if p.endswith('.c') else 'after-guards')) for p in AFTER}
    if not values or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed exact separation successor')
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
    if actual!=raw_read(out/'first-predicted.elf'):raise ValueError('Separation image differs from first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Separation changed other bodies/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],204,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Separation changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    raw,bindings=checked_object(out/'qualified.o')
    if raw_read(root/'conker/retail_word_patches.us.csv')!=recovered_guards(raw_read(out/'before-02'),raw,bindings):
        raise ValueError('Separation guards differ from fifteen appended rows')
    if hashlib.sha256(raw_read(root/'conker/Makefile')).hexdigest()!=INPUTS['conker/Makefile']:
        raise ValueError('Separation changed existing build/profile')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Separation changed protected Game data')
    result=dict(functions=len(a),only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),new_guards=15,old_guard_prefix_unchanged=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forms',action='store_true');parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    if args.forms:
        for name,body in forms():
            row=measure(root,root/BUILD,name,body)[2]
            print(json.dumps(dict(name=name,words=row['words'],differences=row['differences'],sha=row['raw_sha256'])),flush=True)
    else:print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
