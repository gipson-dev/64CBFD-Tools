"""Recover five-neighbor byte selection and its nonzero-class priority."""
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
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-record-neighbor-selector'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_150888A8',0x150888A8,0xB5D58,88
TABLE=0x800D2350
INPUTS={
    'conker/src/game/generated_B3020.c':'478b47b1e70f3b49c9b45f8b2d5dd1a9e22570ac871e71f03318a64d553ebcb8',
    'conker/build/conker.us.elf':'963b19f2f16d695e93aa85ac2b1a8aaaff08f865f3af843c0f0e736d43a806d4',
    'conker/retail_word_patches.us.csv':'dcdd24364339be141dc68c91756fb2450414e06b736d863109a81f80628b2a35',
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
SELECTED='''/* Prefer a non-requested neighbor class; retain the last requested-class fallback. */
s32 func_150888A8(u8 excludedId, u8 recordIndex, s8 alternate) {
    s32 excluded = excludedId;
    s32 requested;
    s32 fallback = 0xFF;
    s32 i;
    u8 selected = 0xFF;
    u8 current;
    u8 candidate;
    u8 second;
    u8 kind;
    u8 *record;
    u8 *cursor;
    u8 *entry;

    if (alternate != 0) {
        requested = 1;
    } else {
        requested = 2;
    }
    record = D_800D2350 + recordIndex * 0x10;
    candidate = record[9];
    if (candidate != 0xFF && excluded != candidate) {
        entry = D_800D2350 + candidate * 0x10;
        if (entry[0xE] == 0) {
            if (requested != entry[0xF]) {
                selected = candidate & 0xFF;
            } else {
                fallback = candidate & 0xFF;
            }
        }
    }
    i = 1;
    cursor = record + 1;
    current = selected;
    /* The retail loop handles the remaining four neighbors in pairs. */
    do {
        candidate = cursor[9];
        i += 2;
        if (candidate != 0xFF && excluded != candidate) {
            entry = D_800D2350 + candidate * 0x10;
            if (entry[0xE] == 0) {
                kind = entry[0xF];
                if (requested != kind) {
                    if (current == 0xFF || kind != 0) {
                        selected = candidate & 0xFF;
                        current = selected;
                    }
                } else {
                    fallback = candidate & 0xFF;
                }
            }
        }
        second = cursor[0xA];
        if (second != 0xFF && excluded != second) {
            entry = D_800D2350 + second * 0x10;
            if (entry[0xE] == 0) {
                kind = entry[0xF];
                if (requested != kind) {
                    if (current == 0xFF || kind != 0) {
                        selected = second & 0xFF;
                        current = selected;
                    }
                } else {
                    fallback = second & 0xFF;
                }
            }
        }
        cursor += 2;
    } while (i != 5);
    if (current == 0xFF) {
        selected = fallback & 0xFF;
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
    if before[lo:hi]!='s32 func_150888A8() {\n    return 0;\n}':
        raise ValueError('Unknown neighbor selector placeholder')
    result=before[:lo]+body.rstrip()+before[hi:]
    if '\nu8 excludedId;' in body:
        signature='s32 func_150888A8(s32 excludedId, s32 recordIndex, s32 alternate);'
    else:
        start,_=function_span(body,FUNCTION)
        signature=body[start:body.index('{',start)].strip()+';'
    result=result.replace('s32 func_150888A8();',signature,1)
    if 'u8 excludedId, u8 recordIndex, s8 alternate' in body:
        result=result.replace('func_150888A8(rec[0x2C], value & 0xFF, 1)',
            'func_150888A8(rec[0x2C], value, 1)',1)
    return result


def forms():
    yield 'initial',INITIAL
    yield 'wide-inputs',INITIAL.replace('u8 excludedId, u8 recordIndex, s8 alternate',
        's32 excludedId, s32 recordIndex, s32 alternate').replace('excluded = excludedId;',
        'excluded = (u8)excludedId;').replace('alternate != 0','(s8)alternate != 0').replace(
        'recordIndex * 0x10','(u8)recordIndex * 0x10')
    yield 'wide-fallback',INITIAL.replace('s32 fallback = 0xFF;','u8 fallback = 0xFF;')
    yield 'wide-selected',INITIAL.replace('u8 selected = 0xFF;','s32 selected = 0xFF;')
    yield 'separate-kinds',INITIAL.replace('    u8 kind;','    u8 kind;\n    u8 secondKind;').replace(
        'second != 0xFF'+INITIAL.split('second != 0xFF',1)[1].split('        cursor += 2;',1)[0],
        ('second != 0xFF'+INITIAL.split('second != 0xFF',1)[1].split('        cursor += 2;',1)[0]).replace('kind','secondKind'))
    ordered=INITIAL.replace('s32 excluded = excludedId;','s32 excluded;').replace(
        's32 fallback = 0xFF;','s32 fallback;').replace('u8 selected = 0xFF;','u8 selected;').replace(
        '    if (alternate != 0)', '    excluded = excludedId;\n    selected = 0xFF;\n    fallback = 0xFF;\n    if (alternate != 0)',1)
    yield 'ordered',ordered
    separate=ordered.replace('    u8 candidate;', '    u8 candidate;\n    u8 firstCandidate;').replace(
        '    u8 kind;','    u8 kind;\n    u8 secondKind;').replace(
        '    u8 *entry;','    u8 *entry;\n    u8 *firstEntry;\n    u8 *secondEntry;')
    lo=separate.index('    candidate = record[9];');hi=separate.index('    i = 1;')
    separate=separate[:lo]+separate[lo:hi].replace('candidate','firstCandidate').replace('entry','firstEntry')+separate[hi:]
    lo=separate.index('        second = cursor');hi=separate.index('        cursor += 2;')
    separate=separate[:lo]+separate[lo:hi].replace('entry','secondEntry').replace('kind','secondKind')+separate[hi:]
    yield 'separate-lifetimes',separate
    yield 'separate-lifetimes-wide-selected',separate.replace('    u8 selected;', '    s32 selected;')
    yield 'separate-lifetimes-masks',separate.replace('excluded = excludedId;', 'excluded = excludedId & 0xFF;')
    for n,b in (('initial',INITIAL),('ordered',ordered),('separate',separate)):
        yield n+'-byte-return',b.replace('s32 func_150888A8(', 'u8 func_150888A8(')
        yield n+'-byte-return-wide-selected',b.replace('s32 func_150888A8(', 'u8 func_150888A8(').replace(
            'u8 selected','s32 selected')
    for selected in ('u8','s32'):
        for current in ('u8','s32'):
            for candidate in ('u8','s32'):
                if selected==current==candidate=='u8':continue
                b=ordered.replace('u8 selected;',selected+' selected;').replace('u8 current;',current+' current;')
                for var in ('candidate','second','kind'):b=b.replace('u8 '+var+';',candidate+' '+var+';')
                yield 'words-'+selected+'-'+current+'-'+candidate,b
    simple='''/* Prefer a non-requested neighbor class; retain the last requested-class fallback. */
s32 func_150888A8(u8 excludedId, u8 recordIndex, s8 alternate) {
    s32 excluded = excludedId;
    s32 requested;
    u8 selected = 0xFF;
    s32 fallback = 0xFF;
    s32 i;
    u8 candidate;
    u8 kind;
    u8 *record;
    u8 *entry;

    if (alternate != 0) {
        requested = 1;
    } else {
        requested = 2;
    }
    record = D_800D2350 + recordIndex * 0x10;
    for (i = 0; i < 5; i++) {
        candidate = record[i + 9];
        if (candidate != 0xFF && excluded != candidate) {
            entry = D_800D2350 + candidate * 0x10;
            if (entry[0xE] == 0) {
                kind = entry[0xF];
                if (requested != kind) {
                    if (selected == 0xFF || kind != 0) {
                        selected = candidate & 0xFF;
                    }
                } else {
                    fallback = candidate & 0xFF;
                }
            }
        }
    }
    if (selected == 0xFF) {
        selected = fallback & 0xFF;
    }
    return selected;
}
'''
    yield 'simple-for',simple
    yield 'simple-for-wide',simple.replace('u8 selected','s32 selected').replace('u8 candidate','s32 candidate').replace('u8 kind','s32 kind')
    yield 'simple-do',simple.replace('    for (i = 0; i < 5; i++) {', '    i = 0;\n    do {').replace(
        '    }\n    if (selected == 0xFF)', '        i++;\n    } while (i != 5);\n    if (selected == 0xFF)')
    for selected in ('u8','s32'):
        for candidate in ('u8','s32'):
            for kind in ('u8','s32'):
                b=simple.replace('u8 selected',selected+' selected').replace('u8 candidate',candidate+' candidate').replace('u8 kind',kind+' kind')
                yield 'simple-types-'+selected+'-'+candidate+'-'+kind,b
    for first in ('u8','s32'):
        for loop in ('u8','s32'):
            for current in ('u8','s32'):
                b=separate.replace('u8 selected;', 's32 selected;').replace('u8 current;',current+' current;')
                b=b.replace('u8 firstCandidate;',first+' firstCandidate;')
                for var in ('candidate','second','kind','secondKind'):b=b.replace('u8 '+var+';',loop+' '+var+';')
                yield 'mixed-'+first+'-'+loop+'-'+current,b
    for n,b in (('ordered',ordered),('separate',separate),('separate-word-candidates',
            separate.replace('u8 firstCandidate;','s32 firstCandidate;').replace('u8 candidate;','s32 candidate;').replace(
                'u8 second;','s32 second;').replace('u8 kind;','s32 kind;').replace('u8 secondKind;','s32 secondKind;'))):
        for var in ('candidate','firstCandidate','second','fallback'):b=b.replace(var+' & 0xFF',var)
        yield n+'-implicit-byte-conversion',b
    wide=separate
    for var in ('selected','current','candidate','firstCandidate','second','kind','secondKind'):
        wide=wide.replace('u8 '+var+';','s32 '+var+';')
    wide=wide.replace('u8 excludedId, u8 recordIndex, s8 alternate','s32 excludedId, s32 recordIndex, s32 alternate').replace(
        'excluded = excludedId;', 'excluded = (u8)excludedId;').replace('alternate != 0','(s8)alternate != 0').replace(
        'recordIndex * 0x10','(u8)recordIndex * 0x10')
    yield 'word-ABI',wide
    promoted=wide.replace('s32 func_150888A8(s32 excludedId, s32 recordIndex, s32 alternate) {',
        '/* Byte formals retain the promoted-word interface used by retail callers. */\n'
        's32 func_150888A8(excludedId, recordIndex, alternate)\nu8 excludedId;\nu8 recordIndex;\ns8 alternate;\n{').replace(
        'excluded = (u8)excludedId;', 'excluded = excludedId;').replace('(s8)alternate != 0','alternate != 0').replace(
        '(u8)recordIndex * 0x10','recordIndex * 0x10')
    yield 'promoted-ABI',promoted


SELECTED=dict(forms())['mixed-s32-s32-s32']
RAW_SHA='72a73228b5d5ec20212eca6c4682406ce6ffdb11f6266f4aa2e1ccc483241de4'
AFTER={
    'conker/build/conker.us.elf':'52311814c017d8714aa125c789243a20fc0eade9c09cb66680f15e5116d45f77',
    'conker/src/game/generated_B3020.c':'dde8438e4b98764c530ded940cf659620f4210dbf954161d85d1476d990860f3',
    'conker/retail_word_patches.us.csv':'73e3a4be767287fcef63d082bacd379919e1477372e6e74d20b25c4505a7ada1',
}


def measure(root,out,label='selected',body=None):
    values=freeze(root,out)
    owner=recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body)
    if body and 's32 excludedId' in body:
        owner=owner.replace('s32 func_150888A8(u8, u8, s8);','s32 func_150888A8(s32, s32, s32);')
    obj,diagnostics=compile_owner(root,out,owner,label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>88I',values['conker/conker.us.bin'],ROM)
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    row=dict(words=len(words),diagnostics=diagnostics,frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        different=[(i,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def renamed(word,roles):
    op=word>>26
    fields=([21,16,11] if op==0 else [21,16] if op in (4,5,9,12,20,21,35,36,43) else [16] if op==15 else [])
    if not fields:raise ValueError('Unknown neighbor-selector rename opcode')
    for shift in fields:
        r=(word>>shift)&31;word=(word&~(31<<shift))|(roles.get(r,r)<<shift)
    return word


def normalized(words):
    if len(words)!=88:raise ValueError('Neighbor selector requires complete 88-word body')
    result=list(words)
    for i in range(8,86):
        roles={3:5,5:6,6:8,7:3,8:7,10:12}
        if i<15:roles={7:3,8:7}
        if i in (30,31):roles[24]=10
        if i in (42,48,55,60) or 61<=i<=79:roles[5]=11
        if i in (44,45):roles[25]=24
        if i in (46,47):roles[14]=25
        if 49<=i<=54:roles[12]=10
        if 61<=i<=79:roles.update({11:10,12:6})
        if i in (64,65):roles[15]=14
        if i in (66,67):roles[24]=15
        # The old current-selection value dies at the acceptance test. Retail
        # writes the return role first, then copies it into the next loop state.
        if i in (53,56,73,76):roles[10]=3
        if i in (58,78):roles.update({7:12,10:3})
        result[i]=renamed(result[i],roles)
    for i in (22,41,52,61,72,82):
        w=result[i]
        if w>>26 not in (4,5,20,21):raise ValueError('Expected symmetric equality test')
        result[i]=(w&~(1023<<16))|(((w>>16)&31)<<21)|(((w>>21)&31)<<16)
    return result


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION];raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    if len(raw)!=352 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!={
            60:[('R_MIPS_HI16','D_800D2350')],64:[('R_MIPS_LO16','D_800D2350')]}:
        raise ValueError('Unknown neighbor selector body or two bindings')
    return raw,bindings


def owner_guards(raw,bindings):
    words=list(struct.unpack('>88I',raw));fixed=normalized(words);rows=[]
    for i,(a,b) in enumerate(zip(words,fixed)):
        if a==b:continue
        binding=';'.join(kind+':'+name for kind,name in bindings.get(i*4,[])) or '-'
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
            replacement='0x%08X'%b,expected_relocations=binding,replacement_relocations=binding,
            note='Normalize neighbor selector live register roles and symmetric equality operands',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=60:raise ValueError('Expected sixty neighbor selector guards')
    return rows


def recovered_guards(before,raw,bindings):
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):raise ValueError('Preexisting neighbor selector guards')
    if not before.endswith(b'\n'):raise ValueError('Guard prefix lacks line terminator')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=reader.fieldnames,lineterminator='\r\n')
    writer.writerows(owner_guards(raw,bindings));return before+out.getvalue().encode()


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified');raw,bindings=checked_object(obj)
    truth=list(struct.unpack_from('>88I',values['conker/conker.us.bin'],ROM))
    if normalized(words)!=truth:raise ValueError('Neighbor selector register normalization differs from retail')
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if row['diagnostics'] or diagnostics or row['differences']!=60 or normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed neighbor selector diagnostics/shape/pools')
    guards=out/'qualified-guards.csv';guards.write_bytes(recovered_guards(values['conker/retail_word_patches.us.csv'],raw,bindings))
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/B3020.s',filename=OWNER,word_patches_path=guards))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=352 or data[f['value']:f['value']+352]!=values['conker/conker.us.bin'][ROM:ROM+352]:
        raise ValueError('Padded neighbor selector differs from retail')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected neighbor selector linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,352)
    if image[at:at+352]!=values['conker/conker.us.bin'][ROM:ROM+352]:raise ValueError('Neighbor selector prediction slot mismatch')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Neighbor selector prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_B3020.c':recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':raw_read(out/'qualified-guards.csv')}
    for p,data in [*expected.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else 'after-owner' if p.endswith('.c') else 'after-guards' if p.endswith('.csv') else p)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first neighbor selector successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=88,
        raw_differences=60,guards=60,frame=8,functions=len(a),neighbors=row['neighbors'],bytes=len(image))
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n');return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-owner' if p.endswith('.c') else 'after-guards')) for p in AFTER}
    if not values or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:raise ValueError('Changed exact neighbor selector successor')
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
    if actual!=raw_read(out/'first-predicted.elf'):raise ValueError('Neighbor selector image differs from first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Neighbor selector changed other bodies/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],352,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Neighbor selector changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    raw,bindings=checked_object(out/'qualified.o')
    if raw_read(root/'conker/retail_word_patches.us.csv')!=recovered_guards(raw_read(out/'before-02'),raw,bindings):
        raise ValueError('Neighbor selector guards differ from appended rows')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Neighbor selector changed protected Game data')
    result=dict(functions=len(a),only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),new_guards=60,old_guard_prefix_unchanged=True,game_data=data)
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
