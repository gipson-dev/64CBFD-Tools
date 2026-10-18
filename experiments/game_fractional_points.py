"""Recover two fractional vector points without losing overlapping store order."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_yxz_matrix_compose as previous
from tools.experiments import game_actor_owned_resource_cleanup as checkpoint
from tools.pad_generated_object import parse_object,emit_padded_assembly

BUILD='conker/build/game-fractional-points'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_133190','func_15107AE0',0x15107AE0,0x134F90,38
FIRST,SECOND=0x800A2420,0x800A2424
INPUTS={
    'conker/src/game/generated_133190.c':'0e8e35e2c907235ba5b481087abe3d74f89e768ed5e391b5355b1d413ebdbe08',
    'conker/build/conker.us.elf':'c20a95cd43bb3ea44e97fdd57f7691f530144cabe398370943f4aa04d074b5ec',
    'conker/retail_word_patches.us.csv':'625033dd1c2150ce2edb45badf13c05d09aa95b83a0c2b1231e092105d3fc2b3',
    'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/133190.s':'f6105409feaa68357ab4471fdb51a0e092c8b33a9244a8863c3266cf54189419',
    'conker/Makefile':'a6e92d90cdeb8c65e7d1ff57f6603ea4f0e5bee6c09d5a028a51a1e0e369bfd6',
    'conker/symbol_addrs.us.txt':'d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    'conker/asm/nonmatchings/generated_133190/func_15107B78.s':'11e30673c9109a68411b2bd4acda8d175fa2bfa5852b23468d6f6f0429ea48eb',
    'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'ido/ido5.3_recomp/cfe':'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9',
    'ido/ido5.3_recomp/uopt':'23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ido/ido5.3_recomp/ugen':'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d',
    'conker/asm/data/246ED0.rodata.s':'f64662a2c1c477ce8955567940d0ecdb04af273ffefcecc7db346d5dbef81168',
}
SELECTED='''/* Write two fractional points, retaining the original deltas across stores. */
void func_15107AE0(const f32 start[3], const f32 end[3], f32 first[3], f32 second[3]) {
    extern f32 D_800A2420, D_800A2424;
    f32 firstFraction = D_800A2420;
    f32 secondFraction = D_800A2424;
    f32 dx = end[0] - start[0];
    f32 dy = end[1] - start[1];
    f32 dz = end[2] - start[2];

    first[0] = start[0] + dx * firstFraction;
    first[1] = start[1] + dy * firstFraction;
    first[2] = start[2] + dz * firstFraction;
    second[0] = start[0] + dx * secondFraction;
    second[1] = start[1] + dy * secondFraction;
    second[2] = start[2] + dz * secondFraction;
}
'''
INITIAL=SELECTED
compile_owner,link_owner,function_span=previous.compile_owner,previous.link_owner,previous.function_span
same_functions,normalized_pools=previous.same_functions,previous.normalized_pools
elf_slot_offset=previous.elf_slot_offset
raw_read,raw_text=Path.read_bytes,Path.read_text
RAW_SHA='8be0c877fd146def90f9ec4194c677fe9bb75cb3f8a4133ed4c05ba062865bbf'
AFTER={
    'conker/build/conker.us.elf':'d6f9ef39a264d51413b532ae5a4b587400864b346d0cbab1b9e066eaf09c327b',
    'conker/src/game/generated_133190.c':'07ef53eb53f67b749de94a6390cbc836dbcf99b7e1983c91efd27fc0730d4ed4',
    'conker/Makefile':'840897f11d9fea8109c4e67c57e927efa6e1686de2b399fec2c9025828b92d49',
}


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def recovered_owner(before,body=None):
    if body is None:body=SELECTED
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15107AE0() {\n    return 0;\n}':
        raise ValueError('Unknown fractional-point placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def measure(root,out,label='selected',body=None):
    if body is None:body=SELECTED
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,
        recovered_owner(values['conker/src/game/generated_133190.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER);f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=struct.unpack_from('>38I',values['conker/conker.us.bin'],ROM)
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    row=dict(words=len(words),diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        different=[(i,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def forms():
    yield 'register-coefficients',INITIAL.replace('    f32 firstFraction','    register f32 firstFraction').replace(
        '    f32 secondFraction','    register f32 secondFraction')
    yield 'register-deltas',INITIAL.replace('    f32 dx','    register f32 dx').replace(
        '    f32 dy','    register f32 dy').replace('    f32 dz','    register f32 dz')
    yield 'register-all',INITIAL.replace('    f32 ','    register f32 ')
    deferred=INITIAL.replace('    f32 firstFraction', '    f32 dx, dy, dz;\n    f32 firstFraction').replace(
        '    f32 dx =','    dx =').replace('    f32 dy =','    dy =').replace('    f32 dz =','    dz =')
    yield 'deferred-deltas',deferred
    yield 'deferred-register-all',deferred.replace('    f32 ','    register f32 ')
    yield 'mutable-inputs',INITIAL.replace('const f32','f32')
    literals=INITIAL.replace('    extern f32 D_800A2420, D_800A2424;\n','').replace(
        'firstFraction = D_800A2420','firstFraction = 0.333f').replace(
        'secondFraction = D_800A2424','secondFraction = 0.6667f')
    yield 'literal-fractions',literals
    yield 'literal-inline',literals.replace('    f32 firstFraction = 0.333f;\n','').replace(
        '    f32 secondFraction = 0.6667f;\n','').replace('firstFraction','0.333f').replace('secondFraction','0.6667f')
    for value in ('dx','dy','dz'):
        yield 'return-'+value,INITIAL.replace('void func_15107AE0','f32 func_15107AE0').replace(
            '    second[2] = start[2] + dz * secondFraction;',
            '    second[2] = start[2] + dz * secondFraction;\n    return '+value+';')


SELECTED=dict(forms())['literal-fractions']


def recovered_makefile(before):
    anchor='$(BUILD_DIR)/$(SRC_DIR)/game/generated_113D60.c.o: RETAIL_RODATA_SYMBOL := D_800A1350\n'
    if before.count(anchor)!=1 or 'generated_133190.c.o: RETAIL_RODATA_SYMBOL' in before:
        raise ValueError('Unknown fractional-point build anchor')
    return before.replace(anchor,anchor+
        '# Fractional points use their two original adjacent coefficient literals.\n'
        '$(BUILD_DIR)/$(SRC_DIR)/game/generated_133190.c.o: RETAIL_RODATA_SYMBOL := D_800A2420\n',1)


def checked_object(obj):
    text,functions,rel=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    expected={i:[('R_MIPS_HI16' if i%8==0 else 'R_MIPS_LO16','.rodata')] for i in (0,4,8,12)}
    pool=normalized_pools(obj)
    if len(raw)!=152 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected or \
            pool!={'.rodata':(bytes.fromhex('3eaa7efa3f2aacda0000000000000000'),()),'.data':None}:
        raise ValueError('Unknown fractional body, four bindings or exact literal pool')
    return raw,bindings


def qualify(root,out):
    values=freeze(root,out)
    obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_133190.c'].decode(),'owner-before')
    if row['diagnostics'].replace('qualified.c','owner.c')!=diagnostics.replace('owner-before.c','owner.c') or \
            same_functions(before,obj,(FUNCTION,))!=36 or \
            normalized_pools(before)!={'.rodata':None,'.data':None}:
        raise ValueError('Changed fractional diagnostics/neighbors/old pools')
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/133190.s',filename=OWNER,
        word_patches_path=root/'conker/retail_word_patches.us.csv',rodata_symbol='D_800A2420'))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=152 or data[f['value']:f['value']+152]!=values['conker/conker.us.bin'][ROM:ROM+152]:
        raise ValueError('Anchored fractional constructor differs from retail')
    return obj,padded,list(struct.unpack_from('>38I',data,f['value'])),row


def predict(root,out):
    values=freeze(root,out)
    obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+OWNER+'.c.o'
    if old not in script:raise ValueError('Missing fractional owner linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'first-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes();at=elf_slot_offset(image,ENTRY,152)
    if image[at:at+152]!=values['conker/conker.us.bin'][ROM:ROM+152]:
        raise ValueError('Complete fractional prediction differs from retail')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Fractional prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_133190.c':recovered_owner(values['conker/src/game/generated_133190.c'].decode()).encode(),
        'conker/Makefile':recovered_makefile(values['conker/Makefile'].decode()).encode()}
    for p,data in expected.items():
        path=out/('after-elf' if p.endswith('.elf') else 'after-makefile' if p.endswith('Makefile') else 'after-owner')
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first fractional successor')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=38,
        raw_instruction_differences=0,isolated_pool_address_words=4,guards=0,functions=len(a),neighbors=36)
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def expected_inputs(root,out):
    values={p:raw_read(out/('after-elf' if p.endswith('.elf') else
        'after-makefile' if p.endswith('Makefile') else 'after-owner')) for p in AFTER}
    if {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed exact fractional successor')
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
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Fractional installation changed other functions/addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1;old[(FUNCTION,fields[1],152,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Fractional changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    for p in ('conker/retail_word_patches.us.csv','conker/asm/data/246ED0.rodata.s'):
        if hashlib.sha256(raw_read(root/p)).hexdigest()!=INPUTS[p]:raise ValueError('Fractional changed guards/data source')
    at=elf_slot_offset(actual,FIRST,16)
    if actual[at:at+16]!=bytes.fromhex('3eaa7efa3f2aacda0000000000000000'):
        raise ValueError('Original fractional literals changed')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Fractional changed protected Game data')
    result=dict(functions=len(a),neighbors=36,only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),guards_unchanged=True,
        original_literal_pool_unchanged=True,game_data=data)
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
            print(json.dumps(dict(name=name,words=row['words'],differences=row['differences'])),flush=True)
    else:print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
