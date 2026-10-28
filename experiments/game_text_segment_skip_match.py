"""Text segment skip: direct C, actual ABI and literal owner/image audit."""
from pathlib import Path
import hashlib,json,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1516C878','generated_197C20'
ENTRY,ROM,BODY,SIZE=0x1516C878,0x199D28,188,188
SOURCE='conker/src/game/generated_197C20.c'
OBJECT='conker/build/src/game/generated_197C20.c.o'
ASM='conker/asm/197C20.s'
BUILD='conker/build/game-text-segment-skip-match'
RAW_SHA='571fb7ae69134287a9cec8c80e7b37ca3c6ddd054c2147ce8d62a0ed88657bbb'
SNAPSHOT_SHA='22c04b82dd7934bc89648447f8b1a50a3bbec5630946bf00a3bd04692e43af7d'
BEFORE_ELF_SHA='b0183c080c3556af45e9eefe8f349268ee71682729805d7370af6d72ee47a78f'
TRUTH_SHA='9ede4c9be8fe5f8d7bdab663110c3efe42641ede44137ca36682331efe52091a'
GLOBALS=(0x800DD254,0x800DD258)
BINDINGS={20:[('R_MIPS_HI16','D_800DD254')],60:[('R_MIPS_LO16','D_800DD254')],32:[('R_MIPS_HI16','D_800DD258')],84:[('R_MIPS_LO16','D_800DD258')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="typedef struct {\n    u8 *text;\n    u32 reserved;\n} TextBankEntry;\ntypedef struct {\n    u32 flags;\n    union { u32 index; u8 *text; } value;\n} TextSegmentSource;\nextern TextBankEntry *D_800DD254;\nextern TextBankEntry *D_800DD258;\n"
SELECTED="/* Select bank 0/1 or direct text (2), then advance across zero-separated text runs. */\nu8 *func_1516C878(TextSegmentSource *source, s32 segment, s16 bank) {\n    s32 current;\n    u8 *text;\n\n    switch (bank) {\n        case 0:\n            text = D_800DD254[source->value.index].text;\n            break;\n        case 1:\n            text = D_800DD258[source->value.index].text;\n            break;\n        case 2:\n            text = source->value.text;\n            break;\n    }\n    for (current = 0; current < segment; current++) {\n        while (*text != 0) {\n            text++;\n        }\n        while (*text == 0) {\n            text++;\n        }\n    }\n    return text;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Text segment skip body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1516C878() {\n    return 0;\n}'
    if before.count(stub)!=1 or 'TextSegmentSource'in before:raise ValueError('Text segment skip placeholder changed')
    return before.replace(stub,DECLARATIONS+'\n'+SELECTED,1).replace('/* Non-matching placeholders for the text-only asm slice asm/197C20.s. */','/* Partially recovered text-only slice asm/197C20.s. */')

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Text segment skip snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Text segment skip frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Text segment skip predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Text segment skip live input differs: '+name)
    return values

SYMBOL_CYCLE_BEFORE=('D_800DD258','func_1503F404','func_151BBEE4')
SYMBOL_CYCLE_AFTER=('func_1503F404','func_151BBEE4','D_800DD258')
def reorder_metadata(result,before):
    rows={}
    for pos,name,fields,string_at in symbol_rows(before):
        if name in SYMBOL_CYCLE_BEFORE:
            if name in rows:raise ValueError('Duplicate text-segment metadata symbol')
            rows[name]=(pos,fields,string_at)
    if set(rows)!=set(SYMBOL_CYCLE_BEFORE):raise ValueError('Text-segment metadata symbol set changed')
    expected={'D_800DD258':(0x800DD258,0,16,0,65521),'func_1503F404':(0x1503F404,160,18,0,5),'func_151BBEE4':(0x151BBEE4,216,18,0,5)}
    first=rows[SYMBOL_CYCLE_BEFORE[0]];position,base_string,base_name=first[0],first[2],first[1][0];offset=0
    for i,name in enumerate(SYMBOL_CYCLE_BEFORE):
        at,fields,string_at=rows[name]
        if at!=position+16*i or fields[1:]!=expected[name]or string_at!=base_string+offset or fields[0]!=base_name+offset:raise ValueError('Text-segment metadata predecessor changed')
        offset+=len(name)+1
    old_names=b''.join(name.encode()+b'\0'for name in SYMBOL_CYCLE_BEFORE);new_names=b''.join(name.encode()+b'\0'for name in SYMBOL_CYCLE_AFTER)
    if len(old_names)!=len(new_names)or before[base_string:base_string+len(old_names)]!=old_names:raise ValueError('Text-segment name cycle changed')
    result[base_string:base_string+len(old_names)]=new_names;offset=0
    for i,name in enumerate(SYMBOL_CYCLE_AFTER):
        fields=rows[name][1];struct.pack_into('>IIIBBH',result,position+16*i,base_name+offset,*fields[1:]);offset+=len(name)+1
    return result

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Text segment skip strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Text segment skip original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY);reorder_metadata(result,before)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Text segment skip image differs from body, extent and closed named metadata prediction')
    expected=Counter((n,f[1],188 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Text segment skip named ELF definitions changed')

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1516C878.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game/generated_197C20.c.o","make-shadow/src/game/generated_197C20.c.o.compact","make-shadow/src/game/generated_197C20.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Text segment skip artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Text segment skip artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Text segment skip raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Text segment skip evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Text segment skip Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Text segment skip expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_197C20.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Text segment skip Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=0 or q['exclusions']!=0:raise ValueError('Text segment skip private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Text segment skip changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Text segment skip protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=47,strict_first_link_reproduced=True,guards=0,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
