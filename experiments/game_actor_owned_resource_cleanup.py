"""Recover the actor's five ordered resource releases and final destruction."""
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

from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.alternative_source_function_isolation import preprocessor_flags
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

BUILD = 'conker/build/game-actor-owned-resource-cleanup'
OWNER,FUNCTION,ENTRY,ROM,WORDS = 'generated_12DAB0','func_15101148',0x15101148,0x12E5F8,40
INPUTS = {
    'conker/src/game/generated_12DAB0.c':'762391603b41804b86a10a03e79e2ce0087b84a5afd50b1f64c2b9bcc71a46e1',
    'conker/build/conker.us.elf':'9a3f5eeca3804bde42fd9ee5b2dbd2d49c34ae58b7c5a1c47003f6e391a5441b',
    'conker/retail_word_patches.us.csv':'6fbe433672dd2e72c09417034b7127feeba4ea827403c9ccbb55af83c3dd4a5e',
    'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/12DAB0.s':'3287aa96f4f54d2b79c6c4143ee498d68ad95c2de77b78a4f8fb15f443cbcd4e',
    'conker/Makefile':'a6e92d90cdeb8c65e7d1ff57f6603ea4f0e5bee6c09d5a028a51a1e0e369bfd6',
    'conker/symbol_addrs.us.txt':'d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    'conker/include/structs.h':'081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'conker/include/functions.h':'2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81',
    'conker/src/game_169510.c':'914f001c486928dec6b98dc840d66a3708d9e2c176f009fcc6eafdf5da268fb7',
    'conker/src/game_1944C0.c':'328877b17dd2d16b88ec270bea2c09f900bceaa584cb904fa75b0e3e8029084b',
    'conker/asm/data/22E730.rodata.s':'04adc08432aaa1052219d977d68d9769ac85e1efca4aa89b8b35b8cddedf8413',
    'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'ido/ido5.3_recomp/cfe':'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9',
    'ido/ido5.3_recomp/uopt':'23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ido/ido5.3_recomp/ugen':'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d',
}
DECLARATIONS = '''
#include "structs.h"

extern void func_1513CAA0();

typedef struct {
    u8 pad0[0x24];
    struct102 *resource24;
    struct102 *resource28;
    struct102 *resource2C;
    struct102 *resource30;
    struct102 *resource34;
} ActorOwnedResources101148;
'''
INITIAL = '''/* Release owned objects in retail order, then destroy their actor. */
void func_15101148(struct210 *actor) {
    extern void func_1516979C(struct102 *resource);
    ActorOwnedResources101148 *resources;

    if (*(struct102 **)((u8 *)actor + 0x138) != NULL) {
        func_1516979C(*(struct102 **)((u8 *)actor + 0x138));
    }
    resources = (ActorOwnedResources101148 *)((u8 *)actor + 0x110);
    if (resources->resource2C != NULL) {
        func_1516979C(resources->resource2C);
    }
    if (resources->resource24 != NULL) {
        func_1516979C(resources->resource24);
    }
    if (resources->resource30 != NULL) {
        func_1516979C(resources->resource30);
    }
    if (resources->resource34 != NULL) {
        func_1516979C(resources->resource34);
    }
    func_1513CAA0(actor);
}
'''


def forms():
    yield 'initial',INITIAL
    old = '''    if (*(struct102 **)((u8 *)actor + 0x138) != NULL) {
        func_1516979C(*(struct102 **)((u8 *)actor + 0x138));
    }'''
    new = '''    resource = *(struct102 **)((u8 *)actor + 0x138);
    if (resource != NULL) {
        func_1516979C(resource);
    }'''
    first = INITIAL.replace('    ActorOwnedResources101148 *resources;',
        '    ActorOwnedResources101148 *resources;\n    struct102 *resource;').replace(old,new)
    yield 'first-snapshot',first
    for label,body in (('volatile-owner',first),('volatile-owner-first-decl',first.replace(
            '    ActorOwnedResources101148 *resources;\n    struct102 *resource;',
            '    struct102 *resource;\n    ActorOwnedResources101148 *resources;'))):
        yield label,body.replace('struct210 *actor)', 'struct210 *volatile actor)',1)
    selected = first.replace('struct210 *actor)', 'struct210 *volatile actor)',1).replace(
        '    ActorOwnedResources101148 *resources;\n    struct102 *resource;',
        '    struct102 *resource;\n    ActorOwnedResources101148 *resources;')
    yield 'word-resource',selected.replace('    struct102 *resource;', '    u32 resource;').replace(
        '    resource = *(struct102 **)', '    resource = *(u32 *)').replace(
        '        func_1516979C(resource);','        func_1516979C((struct102 *)resource);',1)
    yield 'register-resource',selected.replace('    struct102 *resource;', '    register struct102 *resource;')
    snapshot = selected.replace('    struct102 *resource;', '    struct210 *firstOwner;').replace(
        new,'''    firstOwner = actor;
    if (*(struct102 **)((u8 *)firstOwner + 0x138) != NULL) {
        func_1516979C(*(struct102 **)((u8 *)firstOwner + 0x138));
    }''')
    yield 'first-owner-snapshot',snapshot
    yield 'conditional-assignment',selected.replace(
        '    resource = *(struct102 **)((u8 *)actor + 0x138);\n    if (resource != NULL) {',
        '    if ((resource = *(struct102 **)((u8 *)actor + 0x138)) != NULL) {')
    yield 'initializer-resource',selected.replace('    struct102 *resource;',
        '    struct102 *resource = *(struct102 **)((u8 *)actor + 0x138);').replace(
        '    resource = *(struct102 **)((u8 *)actor + 0x138);\n','')
    yield 'byte-owner-snapshot',snapshot.replace('    struct210 *firstOwner;', '    u8 *firstOwner;').replace(
        '    firstOwner = actor;', '    firstOwner = (u8 *)actor;')


SELECTED = dict(forms())['volatile-owner-first-decl']
RAW_SHA = 'cbb47854ef6c04e0de22430c14521969a26cfd799a1a5b1f0eeb5851a4ea55cd'
RELEASE,DESTROY = 0x1516979C,0x1513CAA0
AFTER = {'conker/build/conker.us.elf':'d2cda82f7b4ae411706bad464b7680eebcd46efff7b50b6b77fa7e2a50e9be72',
    'conker/src/game/generated_12DAB0.c':'8d42746275aa7e3a3523a6a6be4cda8441c1956d502ad788fbf195f272f406a5',
    'conker/retail_word_patches.us.csv':'034e4adad354d74935a842725e1e2c3490a6c68bad6f875897e2ca6c4ee6282f'}
raw_read,raw_text = Path.read_bytes,Path.read_text
_active = False


def freeze(root,out):
    values = {}
    for path,digest in INPUTS.items():
        data = (root/path).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Changed owned-resource input: '+path)
        values[path] = data
    out.mkdir(parents=True,exist_ok=True)
    for index,data in enumerate(values.values()):
        path = out/('before-%02d'%index)
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Changed owned-resource fixture: '+str(path))
        if not path.exists():
            path.write_bytes(data)
    return values


def recovered_owner(before,body=SELECTED):
    lo,hi = function_span(before,FUNCTION)
    if before[lo:hi] != 's32 func_15101148() {\n    return 0;\n}':
        raise ValueError('Unknown owned-resource placeholder')
    result = before[:lo]+body.rstrip()+before[hi:]
    return result.replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+DECLARATIONS,1)


def measure(root,out,label='selected',body=SELECTED,flags=('-O2','-g3')):
    values = freeze(root,out)
    owner = recovered_owner(values['conker/src/game/generated_12DAB0.c'].decode(),body)
    processor_flags = preprocessor_flags(owner,flags,c_only=True)
    obj,diagnostics = compile_owner(root,out,
        owner,label,processor_flags)
    if tuple(processor_flags) != tuple(flags):
        includes = ['.', 'include', 'include/2.0L', 'include/2.0L/PR', 'include/libc',
            'src/libultra/os', 'src/libultra/audio', 'src/libultra/io']
        result = subprocess.run([str(root/'ido/ido5.3_recomp/cc'),'-c','-32','-G','0',
            '-Xfullwarn','-Xcpluscomm','-signed','-nostdinc','-non_shared','-Wab,-r4300_mul',
            '-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32','-woff','649,838',
            *[flag for path in includes for flag in ('-I',path)],*flags,'-mips2','-o32',
            '-o',str(obj.relative_to(root/'conker')),str((out/(label+'-processed.c')).relative_to(root/'conker'))],
            cwd=root/'conker',capture_output=True,text=True)
        diagnostics = result.stdout+result.stderr
        (out/(label+'-diagnostics.txt')).write_text(diagnostics)
        if result.returncode:
            raise ValueError(diagnostics)
    data,functions = link_owner(root,out,obj,OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth = list(struct.unpack_from('>40I',values['conker/conker.us.bin'],ROM))
    different = [i for i in range(max(len(words),WORDS)) if i>=len(words) or i>=WORDS or words[i]!=truth[i]]
    text,raw_functions,rel = parse_object(obj)
    rf = raw_functions[FUNCTION]
    row = dict(label=label,words=len(words),frame=(-words[0])&65535,differences=len(different),
        different=different,diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(text[rf['value']:rf['value']+rf['size']]).hexdigest(),
        bindings={a-rf['value']:v for a,v in rel.items() if rf['value']<=a<rf['value']+rf['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def checked_object(obj):
    text,functions,rel = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value']+f['size']]
    bindings = {a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    expected = {i:[('R_MIPS_26','func_1516979C')] for i in (28,56,80,104,128)}
    expected[136] = [('R_MIPS_26','func_1513CAA0')]
    if len(raw)!=160 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown owned-resource body or six call bindings')
    return raw,bindings


def owner_guards():
    return [dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(i*4),expected='0x%08X'%a,
        replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',
        note='Normalize first owned-resource pointer register and call-delay argument copy',
        insert_after='',insert_after_relocations='',omit='false') for i,a,b in (
            (4,0x8DC40138,0x8DCF0138),(5,0x50800004,0x51E00004),(8,0x00000000,0x01E02025))]


def recovered_guards(before):
    if not before.endswith(b'\n'):
        raise ValueError('Unterminated owned-resource guard prefix')
    output=io.StringIO(newline='')
    writer=csv.DictWriter(output,fieldnames=next(csv.reader(io.StringIO(before.decode()))),lineterminator='\n')
    writer.writerows(owner_guards())
    return before+output.getvalue().encode()


def first_call_proof(raw,truth):
    if len(raw)!=40 or len(truth)!=40 or [i for i,(a,b) in enumerate(zip(raw,truth)) if a!=b] != [4,5,8]:
        raise ValueError('Unclosed first resource argument window')
    for row in owner_guards():
        i=int(row['offset'],0)//4
        if (raw[i],truth[i])!=(int(row['expected'],0),int(row['replacement'],0)):
            raise ValueError('Changed first resource allocation/copy')
    if raw[3]!=0x8FAE0020 or raw[6]!=0x8FA20020 or raw[9]!=0x8FA20020 or raw[10]!=0x8C44013C:
        raise ValueError('Changed first resource actor/next argument reload')
    # The source uses a0 as the resource role; retail uses t7 until the call's
    # delay slot. On the skipped path a0 is overwritten at word10 before use.
    for word in raw[10:]:
        op,rs,rt,fn=word>>26,word>>21&31,word>>16&31,word&63
        if op not in (2,3) and (rs==15 or op==0 and fn not in (8,9) and rt==15):
            raise ValueError('First resource scratch remains live in the target')
    return dict(window=[4,8],branches=2,call_arguments_equal=True,next_argument_overwritten_at=10,
        source_resource_register=4,retail_resource_register=15,t7_is_ABI_caller_saved=True,
        no_full_dead_scratch_register_equality_claim=True)


def qualify(root,out):
    values=freeze(root,out)
    obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    truth=struct.unpack_from('>40I',values['conker/conker.us.bin'],ROM)
    first_call_proof(words,truth)
    before,diag=compile_owner(root,out,values['conker/src/game/generated_12DAB0.c'].decode(),'owner-before')
    if row['diagnostics'] or diag or same_functions(before,obj,(FUNCTION,))!=22 or normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed owned-resource diagnostics/neighbors/pools')
    guards=recovered_guards(values['conker/retail_word_patches.us.csv'])
    manifest=out/'after-guards'
    if manifest.exists() and manifest.read_bytes()!=guards:
        raise ValueError('Changed owned-resource guard prediction')
    if not manifest.exists():
        manifest.write_bytes(guards)
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/12DAB0.s',filename=OWNER,word_patches_path=manifest))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(script.with_suffix('.o')),str(script)],
        check=True,capture_output=True)
    data,functions=link_owner(root,out,script.with_suffix('.o'),OWNER)
    f=functions[FUNCTION]
    slot=data[f['value']:f['value']+f['size']]
    if f['size']!=160 or slot!=struct.pack('>40I',*truth):
        raise ValueError('Owned-resource padder does not match retail')
    return obj,script.with_suffix('.o'),words,row


def predict(root,out):
    values=freeze(root,out)
    obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text()
    old='build/src/game/'+OWNER+'.c.o'
    replacement=padded.relative_to(root/'conker').as_posix()
    if not script.count(old):
        raise ValueError('Missing owned-resource linker input')
    trial=out/'predicted.ld'
    trial.write_text(script.replace(old,replacement))
    path=out/'first-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(trial.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(path.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=path.read_bytes()
    at=elf_slot_offset(image,ENTRY,160)
    if image[at:at+160]!=values['conker/conker.us.bin'][ROM:ROM+160]:
        raise ValueError('Full owned-resource prediction differs from retail')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(path),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Full owned-resource prediction changes other functions')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_12DAB0.c':recovered_owner(values['conker/src/game/generated_12DAB0.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':(out/'after-guards').read_bytes()}
    for key,data in expected.items():
        name='after-'+('elf' if key.endswith('.elf') else 'owner' if key.endswith('.c') else 'guards')
        path=out/name
        if path.exists() and path.read_bytes()!=data:
            raise ValueError('Changed first full owned-resource prediction')
        if not path.exists():
            path.write_bytes(data)
    result=dict(after={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()},
        functions=len(a),only_target_changed=True,raw_differences=3,normalized_differences=0,
        new_guards=3,whole_image_bytes=len(image),slot_bytes=160)
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def expected_inputs(root,out):
    paths={'conker/build/conker.us.elf':'after-elf','conker/src/game/generated_12DAB0.c':'after-owner',
        'conker/retail_word_patches.us.csv':'after-guards'}
    values={p:raw_read(out/n) for p,n in paths.items()}
    if {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed first owned-resource successor')
    return values


def verify(root,out,installed=False):
    expected=expected_inputs(root,out)
    stages=set()
    for p,new in expected.items():
        old=raw_read(out/('before-%02d'%list(INPUTS).index(p)))
        if hashlib.sha256(old).hexdigest()!=INPUTS[p]:
            raise ValueError('Changed owned-resource predecessor fixture')
        current=raw_read(root/p)
        if current==old:
            stages.add('before')
        elif current==new:
            stages.add('after')
        else:
            raise ValueError('Unexpected live owned-resource member: '+p)
    if len(stages)!=1 or installed and stages!={'after'}:
        raise ValueError('Mixed or uninstalled owned-resource successor')
    return next(iter(stages))


@contextmanager
def historical_view(root,out):
    global _active
    if _active:
        raise RuntimeError('Owned-resource predecessor view cannot nest')
    verify(root,out)
    values={str((root/p).resolve()):raw_read(out/('before-%02d'%list(INPUTS).index(p)))
        for p in AFTER}
    def read_bytes(path):
        return values.get(str(path.resolve()),raw_read(path))
    def read_text(path,encoding=None,errors=None,newline=None):
        if str(path.resolve()) not in values:
            return raw_text(path,encoding=encoding,errors=errors,newline=newline)
        with io.TextIOWrapper(io.BytesIO(read_bytes(path)),encoding=encoding,errors=errors,newline=newline) as stream:
            return stream.read()
    _active=True
    try:
        with patch.object(Path,'read_bytes',read_bytes),patch.object(Path,'read_text',read_text):
            yield
    finally:
        _active=False


def audit(root,out):
    verify(root,out,installed=True)
    from tools.match_progress import load_elf_functions
    from tools.tests.test_game_one_shot_timer_match import canonical_symbols,symbol_rows
    from tools.check_game_data_layout import audit_layout
    before=raw_read(out/'before-01')
    actual=raw_read(root/'conker/build/conker.us.elf')
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Owned-resource installation changed other bodies/addresses')
    old=canonical_symbols(before)
    new=canonical_symbols(actual)
    original=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*original[1:])]-=1
    old[(FUNCTION,original[1],160,*original[3:])]+=1
    if +old!=+new:
        raise ValueError('Owned-resource installation changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Owned-resource installation changed Game data')
    if struct.unpack_from('>I',actual,elf_slot_offset(actual,0x80089F30,4))[0]!=ENTRY:
        raise ValueError('Owned-resource callback slot changed')
    result=dict(functions=len(a),only_target_changed=True,all_addresses_preserved=True,
        actual_owner_and_relocations_identical=True,symbol_definitions_only_target_size_changed=True,
        callback='0x80089F30',game_data=data,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)))
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def install_guards(root,out):
    freeze(root,out)
    expected=expected_inputs(root,out)
    (root/'conker/retail_word_patches.us.csv').write_bytes(expected['conker/retail_word_patches.us.csv'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--predict',action='store_true')
    args=parser.parse_args()
    print(json.dumps(predict(args.root,args.root/BUILD) if args.predict else
        measure(args.root,args.root/BUILD)[2],indent=2))


if __name__=='__main__':
    main()
