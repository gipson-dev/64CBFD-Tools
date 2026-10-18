"""Recover handle-first actor resource retirement without immediate freeing."""
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

from tools.experiments import game_actor_owned_resource_cleanup as previous
from tools.pad_generated_object import parse_object,emit_padded_assembly

BUILD='conker/build/game-actor-resource-retirement'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_12DAB0','func_15101090',0x15101090,0x12E540,46
HANDLE,RETIRE,FINISH=0x100111C8,0x1516972C,0x1513CA6C
INPUTS=dict(previous.INPUTS,**{
    'conker/src/game/generated_12DAB0.c':'8d42746275aa7e3a3523a6a6be4cda8441c1956d502ad788fbf195f272f406a5',
    'conker/build/conker.us.elf':'d2cda82f7b4ae411706bad464b7680eebcd46efff7b50b6b77fa7e2a50e9be72',
    'conker/retail_word_patches.us.csv':'034e4adad354d74935a842725e1e2c3490a6c68bad6f875897e2ca6c4ee6282f',
    'conker/src/init_EB00.c':'df10767e2955fc9d3e355712d3c5e8b3bf6fa9681ce79b528c50a689105dfb6e',
})
DECLARATIONS='''
extern void func_1513CA6C();

typedef struct {
    u8 pad0[0x110];
    ActorOwnedResources101148 resources;
    u8 pad148[0x58];
    u16 handle1A0;
} ActorResourceOwner101090;
'''
INITIAL='''/* Stop the unsigned handle, retire each owned object, then retire the actor. */
void func_15101090(ActorResourceOwner101090 *volatile actor) {
    extern void func_100111C8(u16 handle);
    extern void func_1516972C(struct102 *resource);
    u16 handle;
    ActorOwnedResources101148 *resources;

    handle = actor->handle1A0;
    if (handle != 0) {
        func_100111C8(handle);
    }
    resources = &actor->resources;
    if (resources->resource28 != NULL) {
        func_1516972C(resources->resource28);
    }
    if (resources->resource2C != NULL) {
        func_1516972C(resources->resource2C);
    }
    if (resources->resource24 != NULL) {
        func_1516972C(resources->resource24);
    }
    if (resources->resource30 != NULL) {
        func_1516972C(resources->resource30);
    }
    if (resources->resource34 != NULL) {
        func_1516972C(resources->resource34);
    }
    func_1513CA6C((struct210 *)actor);
}
'''
SELECTED=INITIAL
compile_owner,link_owner,function_span=previous.compile_owner,previous.link_owner,previous.function_span
same_functions,normalized_pools=previous.same_functions,previous.normalized_pools
elf_slot_offset=previous.elf_slot_offset
RAW_SHA='da4af84c00105525c73151096368ed9f5f18a7a531c0d82bffb8bb2fc814a003'
raw_read,raw_text=Path.read_bytes,Path.read_text
AFTER={
    'conker/build/conker.us.elf':'9f79786e248e2384422e8237865a30273a7ae17f1d3690cc9a4c87f1d46543c4',
    'conker/src/game/generated_12DAB0.c':'ed80609aab48edc56a76802f3bd4d7b535f06da6b11480ae9e6e62cfb1ef2214',
    'conker/retail_word_patches.us.csv':'625033dd1c2150ce2edb45badf13c05d09aa95b83a0c2b1231e092105d3fc2b3',
}


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):
        return previous.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15101090() {\n    return 0;\n}':
        raise ValueError('Unknown resource-retirement placeholder')
    result=before[:lo]+body.rstrip()+before[hi:]
    anchor='} ActorOwnedResources101148;\n'
    if result.count(anchor)!=1:
        raise ValueError('Unknown existing actor resource view')
    return result.replace(anchor,anchor+DECLARATIONS,1)


def measure(root,out,label='selected',body=SELECTED):
    values=freeze(root,out)
    obj,diagnostics=compile_owner(root,out,
        recovered_owner(values['conker/src/game/generated_12DAB0.c'].decode(),body),label)
    data,functions=link_owner(root,out,obj,OWNER)
    f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=list(struct.unpack_from('>46I',values['conker/conker.us.bin'],ROM))
    text,functions,rel=parse_object(obj)
    f=functions[FUNCTION]
    row=dict(label=label,words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        different=[(i,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def checked_object(obj):
    text,functions,rel=parse_object(obj)
    f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    expected={i:[('R_MIPS_26','func_1516972C')] for i in (56,80,104,128,152)}
    expected[28]=[('R_MIPS_26','func_100111C8')]
    expected[160]=[('R_MIPS_26','func_1513CA6C')]
    if len(raw)!=184 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=expected:
        raise ValueError('Unknown retirement body or seven call bindings')
    return raw,bindings


def owner_guards():
    rows=[]
    for index,old,new in ((4,0x95C401A0,0x95CF01A0),(5,0x50800004,0x51E00004),(8,0,0x01E02025)):
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(index*4),expected='0x%08X'%old,
            replacement='0x%08X'%new,expected_relocations='-',replacement_relocations='-',
            note='Normalize unsigned handle register and call-delay argument copy',
            insert_after='',insert_after_relocations='',omit='false'))
    return rows


def recovered_guards(before):
    with patch.object(previous,'owner_guards',owner_guards):
        return previous.recovered_guards(before)


def handle_binding_proof(words,truth):
    if len(words)!=46 or len(truth)!=46 or [i for i,(a,b) in enumerate(zip(words,truth)) if a!=b]!=[4,5,8]:
        raise ValueError('Unclosed unsigned handle binding window')
    for row in owner_guards():
        i=int(row['offset'],0)//4
        if (words[i],truth[i])!=(int(row['expected'],0),int(row['replacement'],0)):
            raise ValueError('Changed unsigned handle register/copy')
    if words[3]!=0x8FAE0020 or words[6]!=0x8FA20020 or words[9]!=0x8FA20020 or words[10]!=0x8C440138:
        raise ValueError('Changed handle/owner/next resource reload')
    for word in words[10:]:
        op,rs,rt,fn=word>>26,word>>21&31,word>>16&31,word&63
        if op not in (2,3) and (rs==15 or op==0 and fn not in (8,9) and rt==15):
            raise ValueError('Handle scratch remains live in the target')
    return dict(branches=2,source_register=4,retail_register=15,argument_bits=16,
        zero_extension=True,call_arguments_equal=True,next_argument_overwritten_at=10,
        no_dead_ABI_scratch_equality_claim=True)


def qualify(root,out):
    values=freeze(root,out)
    obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    truth=struct.unpack_from('>46I',values['conker/conker.us.bin'],ROM)
    handle_binding_proof(words,truth)
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_12DAB0.c'].decode(),'owner-before')
    neighbors=same_functions(before,obj,(FUNCTION,))
    if row['diagnostics'] or diagnostics or neighbors!=22 or normalized_pools(before)!=normalized_pools(obj):
        raise ValueError('Changed retirement diagnostics/neighbors/pools')
    manifest=out/'after-guards'
    guards=recovered_guards(values['conker/retail_word_patches.us.csv'])
    if manifest.exists() and manifest.read_bytes()!=guards:
        raise ValueError('Changed retirement guard prediction')
    if not manifest.exists():manifest.write_bytes(guards)
    script=out/'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/12DAB0.s',filename=OWNER,word_patches_path=manifest))
    padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],check=True,capture_output=True)
    data,functions=link_owner(root,out,padded,OWNER)
    f=functions[FUNCTION]
    if f['size']!=184 or data[f['value']:f['value']+184]!=struct.pack('>46I',*truth):
        raise ValueError('Retirement padder does not match all retail words')
    return obj,padded,words,row


def predict(root,out):
    values=freeze(root,out)
    obj,padded,words,row=qualify(root,out)
    script=(root/'conker/build/conker.ld').read_text()
    old='build/src/game/'+OWNER+'.c.o'
    if old not in script:raise ValueError('Missing retirement linker input')
    ld=out/'predicted.ld'
    ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'first-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=elf.read_bytes()
    at=elf_slot_offset(image,ENTRY,184)
    if image[at:at+184]!=values['conker/conker.us.bin'][ROM:ROM+184]:
        raise ValueError('Full retirement prediction is not retail exact')
    from tools.match_progress import load_elf_functions
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Retirement prediction changes other bodies/addresses')
    expected={'conker/build/conker.us.elf':image,
        'conker/src/game/generated_12DAB0.c':recovered_owner(values['conker/src/game/generated_12DAB0.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':(out/'after-guards').read_bytes()}
    for key,data in expected.items():
        name='after-'+('elf' if key.endswith('.elf') else 'owner' if key.endswith('.c') else 'guards')
        path=out/name
        if path.exists() and path.read_bytes()!=data:raise ValueError('Changed first retirement prediction')
        if not path.exists():path.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in expected.items()},words=46,frame=32,
        raw_differences=3,normalized_differences=0,guards=3,functions=len(a),neighbors=22)
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def expected_inputs(root,out):
    paths={'conker/build/conker.us.elf':'after-elf','conker/src/game/generated_12DAB0.c':'after-owner',
        'conker/retail_word_patches.us.csv':'after-guards'}
    values={p:raw_read(out/n) for p,n in paths.items()}
    if {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed exact retirement successor')
    return values


@contextmanager
def checkpoint_context():
    with patch.multiple(previous,INPUTS=INPUTS,AFTER=AFTER,expected_inputs=expected_inputs):
        yield


def verify(root,out,installed=False):
    with checkpoint_context():
        return previous.verify(root,out,installed)


@contextmanager
def historical_view(root,out):
    with checkpoint_context(),previous.historical_view(root,out):
        yield


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
        raise ValueError('Retirement installation changed other bodies or addresses')
    old,new=canonical_symbols(before),canonical_symbols(actual)
    fields=next(r[2] for r in symbol_rows(before) if r[1]==FUNCTION)
    old[(FUNCTION,*fields[1:])]-=1
    old[(FUNCTION,fields[1],184,*fields[3:])]+=1
    if +old!=+new:raise ValueError('Retirement changed unrelated symbol definitions')
    same_functions(out/'qualified-padded.o',root/('conker/build/src/game/'+OWNER+'.c.o'))
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Retirement changed Game data')
    if struct.unpack_from('>I',actual,elf_slot_offset(actual,0x80089EFC,4))[0]!=ENTRY:
        raise ValueError('Retirement callback slot changed')
    result=dict(functions=len(a),neighbors=22,only_target_changed=True,all_addresses_preserved=True,
        only_target_symbol_size_changed=True,actual_owner_and_relocations_identical=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),callback='0x80089EFC',game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def install_guards(root,out):
    freeze(root,out)
    (root/'conker/retail_word_patches.us.csv').write_bytes(expected_inputs(root,out)['conker/retail_word_patches.us.csv'])


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predict',action='store_true')
    args=parser.parse_args()
    print(json.dumps(predict(root,root/BUILD) if args.predict else measure(root,root/BUILD)[2],indent=2))
