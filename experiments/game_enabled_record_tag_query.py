"""Recover the enabled descriptor/current-record byte query and boolean ABI."""
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
from tools.experiments.game_remaining_donor_candidates import compile_owner as compile_caller,link_owner,function_span
from tools.experiments.game_grouped_actor_dispatch_candidates import compile_owner
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD='conker/build/game-enabled-record-tag-query'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_49D30','func_15022B08',0x15022B08,0x4FFB8,39
COUNT,ENABLED,DESCRIPTORS,RECORDS=0x800C363A,0x800C35C8,0x800C35F0,0x800DBEF4
INPUTS={
    'conker/src/game/generated_49D30.c':'e0376d1609bcde42ce5b340453f9fbfcce6022a230b9016a0944f4044f23e187',
    'conker/build/conker.us.elf':'6f9f3636ee46917e8815196a03dfa8a3755e7cfd4763f64dc2b074d21013c3a6',
    'conker/retail_word_patches.us.csv':'625033dd1c2150ce2edb45badf13c05d09aa95b83a0c2b1231e092105d3fc2b3',
    'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/49D30.s':'745b8aaa3c4871d74f21c6cf2479a494cb5e01bcb2df1486c8dbc56004c3ae41',
    'conker/Makefile':'840897f11d9fea8109c4e67c57e927efa6e1686de2b399fec2c9025828b92d49',
    'conker/symbol_addrs.us.txt':'d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    'conker/include/structs.h':'081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'conker/include/2.0L/PR/sched.h':'40a7e05e5e774a3cbc015d44bb8225f469937de178bfe84cd1de9ef3c5ff7572',
    'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'ido/ido5.3_recomp/cfe':'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9',
    'ido/ido5.3_recomp/uopt':'23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ido/ido5.3_recomp/ugen':'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d',
    'conker/src/game/generated_142560.c':'c9e6044506b47ac23ef11f88612d30dd705f51cdfb287572956bea6bf24a4759',
    'conker/asm/142560.s':'ca734f7ffd435f954360ac879e7762e8adbb56cc72ce60eadebcac3030d1121f',
    'conker/build/src/game/generated_142560.c.o':'898b6213f95d4d0d24b05ce98261514521f8413a02ee366f09a73edd74a77fcf',
}
SELECTED='''/* Find an enabled descriptor whose tag matches the selected record. */
s32 func_15022B08(s32 recordIndex, s32 category) {
    extern u8 *D_800DBEF4;
    s32 count = D_800C363A[category];
    s32 i = 0;
    u16 *enabled;

    if (count > 0) {
        enabled = D_800C35C8[category];
        do {
            if (*enabled != 0) {
                if (D_800C35F0[category][i * 8 + 2] ==
                    D_800DBEF4[(u32)recordIndex * 0xA0 + 0x72]) {
                    return 1;
                }
            }
            i++;
            enabled++;
        } while (i < count);
    }
    return 0;
}
'''
INITIAL=SELECTED
raw_read,raw_text=Path.read_bytes,Path.read_text
AFTER={
    'conker/build/conker.us.elf':'23478930a3dea7a22178648e4c9330cb4b09d9271474b01fd9ddd2240826b85a',
    'conker/src/game/generated_49D30.c':'350c4b08699ee583e4c5dd58b6fd403ab49dba62bf4aab53211d146850dc81de',
    'conker/src/game/generated_142560.c':'8a6596d3f961e0b7e1b8ab66bb07ba96664537b10feadeab5113396146ecfff2',
    'conker/retail_word_patches.us.csv':'8f709f6c1cb03108c0f1e6f7b460e624d76f29734c97ed5fe9739f411f2046a1',
}
RAW_SHA='2725b2c7822030ee1dc09c12d45c63687e199d3c7c7aaf636bf34b713602348f'


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15022B08() {\n    return 0;\n}':
        raise ValueError('Unknown enabled record query placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def measure(root,out,label='selected',body=None):
    if body is None:body=SELECTED
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner(values['conker/src/game/generated_49D30.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>39I',values['conker/conker.us.bin'],ROM)
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    row=dict(words=len(words),diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        different=[(i,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def forms():
    first=INITIAL.replace('    s32 count = D_800C363A[category];\n    s32 i = 0;',
        '    s32 i = 0;\n    s32 count = D_800C363A[category];')
    for name,body in (('count-first',INITIAL),('i-first',first)):
        yield name+'-do',body
        yield name+'-do-table-tail',body.replace('} while (i < count);',
            '} while (i < D_800C363A[category]);')
        yield name+'-do-table-gate',body.replace('if (count > 0)',
            'if (D_800C363A[category] > 0)')
        yield name+'-do-prefix-tail',body.replace('            i++;\n','').replace(
            '} while (i < count);','} while (++i < count);')
        yield name+'-do-pointer-first',body.replace('            i++;\n            enabled++;',
            '            enabled++;\n            i++;')
        loop=body.replace('        do {','        for (; i < count; i++) {').replace(
            '            i++;\n','').replace('        } while (i < count);','        }')
        yield name+'-for',loop
        yield name+'-while',body.replace('        do {','        while (i < count) {').replace(
            '        } while (i < count);','        }')
        outer=loop.replace('    if (count > 0) {\n','').replace('    }\n    return 0;','    return 0;')
        outer='\n'.join(line[4:] if line.startswith('        ') else line for line in outer.splitlines())+'\n'
        yield name+'-plain-for',outer
        yield name+'-plain-for-steps',outer.replace('for (; i < count; i++)',
            'for (; i < count; i++, enabled++)').replace('        enabled++;\n','')
        direct=outer.replace('    s32 count = D_800C363A[category];\n','').replace(
            'i < count','i < D_800C363A[category]')
        yield name+'-table-bound',direct
        yield name+'-table-bound-init',direct.replace('s32 i = 0;','s32 i;').replace(
            'for (; i <','for (i = 0; i <')
        yield name+'-table-bound-post',direct.replace('for (; i < D_800C363A[category]; i++)',
            'for (; i < D_800C363A[category]; i++, enabled++)').replace('        enabled++;\n','')


def shaped_forms():
    body=dict(forms())['i-first-do-table-tail']
    yield 'shaped',body
    for name,old,new in (('register-count','    s32 count','    register s32 count'),
            ('register-i','    s32 i','    register s32 i'),
            ('register-enabled','    u16 *enabled','    register u16 *enabled'),
            ('unsigned-index','s32 recordIndex','u32 recordIndex'),
            ('signed-product','(u32)recordIndex *','recordIndex *')):
        yield name,body.replace(old,new)
    for descriptor,record in ((True,False),(False,True),(True,True)):
        code=body
        if descriptor:code=code.replace('D_800C35F0[category][i * 8 + 2]',
            '((u8 (*)[8])D_800C35F0[category])[i][2]')
        if record:code=code.replace('D_800DBEF4[(u32)recordIndex * 0xA0 + 0x72]',
            '((u8 (*)[0xA0])D_800DBEF4)[recordIndex][0x72]')
        yield 'array-views-%d%d'%(descriptor,record),code
    yield 'local-tags',body.replace('''                if (D_800C35F0[category][i * 8 + 2] ==
                    D_800DBEF4[(u32)recordIndex * 0xA0 + 0x72]) {''','''                u8 tag = D_800C35F0[category][i * 8 + 2];
                if (tag == D_800DBEF4[(u32)recordIndex * 0xA0 + 0x72]) {''')
    yield 'local-pointers',body.replace('''                if (D_800C35F0[category][i * 8 + 2] ==
                    D_800DBEF4[(u32)recordIndex * 0xA0 + 0x72]) {''','''                u8 *descriptor = D_800C35F0[category] + i * 8;
                u8 *record = D_800DBEF4 + (u32)recordIndex * 0xA0;
                if (descriptor[2] == record[0x72]) {''')


def final_forms():
    body=dict(shaped_forms())['array-views-01']
    yield 'record-view',body
    no_count=body.replace('    s32 count = D_800C363A[category];\n','').replace(
        'if (count > 0)','if (D_800C363A[category] > 0)')
    yield 'record-view-table-guard',no_count
    for name,code in (('record-view',body),('record-view-table-guard',no_count)):
        yield name+'-pointer-first',code.replace('    u16 *enabled;\n','').replace(
            '    s32 i = 0;','    u16 *enabled;\n    s32 i = 0;')
    yield 'record-view-byte-count',body.replace('    s32 count =','    u8 count =')


SELECTED=dict(final_forms())['record-view-table-guard']


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    expected={4:[('R_MIPS_HI16','D_800C363A')],12:[('R_MIPS_LO16','D_800C363A')],
        28:[('R_MIPS_HI16','D_800C35C8')],44:[('R_MIPS_LO16','D_800C35C8')],
        36:[('R_MIPS_HI16','D_800DBEF4')],52:[('R_MIPS_LO16','D_800DBEF4')],
        40:[('R_MIPS_HI16','D_800C35F0')],48:[('R_MIPS_LO16','D_800C35F0')]}
    if len(raw)!=156 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown record query body or eight bindings')
    return raw,bindings


def normalized(words,bindings=None):
    result=list(words)
    # A0/A2 are dead argument roles before this window and caller-saved at exit.
    for i in range(5,36):
        word=result[i];op=word>>26
        if op==0:shifts=(21,16,11)
        elif op==15:shifts=(16,)
        elif op in (4,5,6,7,9,20,21,35,36,37):shifts=(21,16)
        else:raise ValueError('Unexpected register-cycle opcode')
        for shift in shifts:
            old=(word>>shift)&31
            if old in (4,6):word=(word&~(31<<shift))|((10-old)<<shift)
        result[i]=word
    result[11:14]=[result[12],result[13],result[11]]
    if bindings is None:return result
    moved={i:bindings.get({44:48,48:52,52:44}.get(i,i),[]) for i in range(0,156,4)}
    return result,{i:v for i,v in moved.items() if v}


def owner_guards(raw,bindings):
    words=struct.unpack('>39I',raw);wanted,target=normalized(words,bindings)
    def reloc(entries):return ';'.join(kind+':'+name for kind,name in entries) or '-'
    rows=[]
    for i,(a,b) in enumerate(zip(words,wanted)):
        if a==b and bindings.get(i*4,[])==target.get(i*4,[]):continue
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(i*4),
            expected='0x%08X'%a,replacement='0x%08X'%b,
            expected_relocations=reloc(bindings.get(i*4,[])),replacement_relocations=reloc(target.get(i*4,[])),
            note='Normalize closed query register cycle and independent pointer-load schedule',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=9:raise ValueError('Unclosed query normalization')
    return rows


def recovered_guards(before,raw,bindings):
    if not before.endswith(b'\n'):raise ValueError('Unterminated record query guard prefix')
    if any(row['filename']==OWNER and row['function']==FUNCTION for row in csv.DictReader(io.StringIO(before.decode()))):
        raise ValueError('Existing query guards cannot be overwritten')
    out=io.StringIO(newline='')
    writer=csv.DictWriter(out,fieldnames=next(csv.reader(io.StringIO(before.decode()))),lineterminator='\n')
    writer.writerows(owner_guards(raw,bindings))
    return before+out.getvalue().encode('ascii')


def recovered_caller(before):
    old='s32 func_15022B08();'
    if before.count(old)!=1:raise ValueError('Unknown query caller declaration')
    return before.replace(old,'s32 func_15022B08(s32 recordIndex, s32 category);',1)


def qualify_caller(root,out,values):
    before=values['conker/src/game/generated_142560.c'].decode()
    a,da=compile_caller(root,out,before,'caller-before')
    b,db=compile_caller(root,out,recovered_caller(before),'caller-after')
    if da.replace('caller-before.c','caller.c')!=db.replace('caller-after.c','caller.c') or normalized_pools(a)!=normalized_pools(b):
        raise ValueError('Query caller diagnostics/pools changed')
    count=same_functions(a,b)
    script=out/'caller-padded.s'
    script.write_text(emit_padded_assembly(b,root/'conker/asm/142560.s',filename='generated_142560',
        word_patches_path=root/'conker/retail_word_patches.us.csv'))
    obj=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(script)],check=True,capture_output=True)
    if obj.read_bytes()!=values['conker/build/src/game/generated_142560.c.o']:
        raise ValueError('Typed query caller changed complete production object')
    return dict(functions=count,whole_object_identical=True,diagnostics=da)


def qualify(root,out):
    values=freeze(root,out);obj,words,row=measure(root,out,'qualified');raw,bindings=checked_object(obj)
    truth=struct.unpack_from('>39I',values['conker/conker.us.bin'],ROM)
    if normalized(words)!=list(truth):raise ValueError('Query normalization changes more than the closed cycle/schedule')
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_49D30.c'].decode(),'owner-before')
    row['neighbors']=same_functions(before,obj,(FUNCTION,))
    if row['diagnostics'] or diagnostics or row['differences']!=9 or normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed query diagnostics/shape/pools')
    guards=recovered_guards(values['conker/retail_word_patches.us.csv'],raw,bindings)
    manifest=out/'after-guards'
    if manifest.exists() and manifest.read_bytes()!=guards:raise ValueError('Changed first query guard successor')
    if not manifest.exists():manifest.write_bytes(guards)
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/49D30.s',filename=OWNER,word_patches_path=manifest))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=156 or data[f['value']:f['value']+156]!=values['conker/conker.us.bin'][ROM:ROM+156]:
        raise ValueError('Padded query differs from retail')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out);obj,padded,words,row=qualify(root,out);caller=qualify_caller(root,out,values)
    script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected query linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,156)
    if image[at:at+156]!=values['conker/conker.us.bin'][ROM:ROM+156]:raise ValueError('Full query prediction differs from retail')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Query prediction changed other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_49D30.c':recovered_owner(values['conker/src/game/generated_49D30.c'].decode()).encode(),
        'conker/src/game/generated_142560.c':recovered_caller(values['conker/src/game/generated_142560.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':(out/'after-guards').read_bytes()}
    for p,data in [*expected.items(),('first-predicted.elf',image)]:
        path=out/('after-elf' if p.endswith('/conker.us.elf') else 'after-caller' if p.endswith('generated_142560.c') else
            'after-owner' if p.endswith('.c') else 'after-guards' if p.endswith('.csv') else p)
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first query successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=39,
        raw_differences=9,normalized_differences=0,guards=9,functions=len(a),neighbors=row['neighbors'],bytes=len(image),caller=caller)
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else 'after-caller' if p.endswith('generated_142560.c') else
        'after-owner' if p.endswith('.c') else 'after-guards')) for p in AFTER}
    if {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:raise ValueError('Changed exact query successor')
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
    if actual!=raw_read(out/'first-predicted.elf'):raise ValueError('Query image differs from first prediction')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Query changed other bodies/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],156,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Query changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    if raw_read(root/'conker/build/src/game/generated_142560.c.o')!=raw_read(out/'caller-padded.o'):
        raise ValueError('Installed query caller changes complete object')
    if hashlib.sha256(raw_read(root/'conker/Makefile')).hexdigest()!=INPUTS['conker/Makefile']:
        raise ValueError('Query changed existing profiles/build')
    raw,bindings=checked_object(out/'qualified.o')
    if raw_read(root/'conker/retail_word_patches.us.csv')!=recovered_guards(raw_read(out/'before-02'),raw,bindings):
        raise ValueError('Query guard history differs from nine expected rows')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Query changed protected Game data')
    result=dict(functions=len(a),only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),new_guards=9,old_guard_prefix_unchanged=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forms',action='store_true')
    parser.add_argument('--predict',action='store_true');args=parser.parse_args()
    if args.forms:
        for name,body in forms():
            row=measure(root,root/BUILD,name,body)[2]
            print(json.dumps(dict(name=name,words=row['words'],differences=row['differences'],sha=row['raw_sha256'])),flush=True)
    else:print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
