"""Owner sine scale: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_151B6254','generated_1E34C0'
ENTRY,ROM,BODY,SIZE=0x151B6254,0x1E3704,192,204
SOURCE='conker/src/game/generated_1E34C0.c'
OBJECT='conker/build/src/game/generated_1E34C0.c.o'
ASM='conker/asm/1E34C0.s'
BUILD='conker/build/game-owner-sine-scale-match'
RODATA_SYMBOL=None
RAW_SHA='df23a6e45a5207128491b62de3bb6f3140502ff2ce9036d870a63e85733b9a0c'
SNAPSHOT_SHA='55b218ddb4fb3ff03cf136a39412c9c00592f3002e7698c54d80e6f9080fb3c6'
BEFORE_ELF_SHA='c93de765466346ab35b5ef9e1e2635ef3486a425a94a1bd5a08fa836a42d74ae'
TRUTH_SHA='48558f99268979b2efcbee737b85d15931f88855b8c27ef1051249b08b56ceee'
BINDINGS={8: [('R_MIPS_HI16', 'D_800AA454')], 12: [('R_MIPS_LO16', 'D_800AA454')], 16: [('R_MIPS_HI16', 'D_800AA458')], 20: [('R_MIPS_LO16', 'D_800AA458')], 24: [('R_MIPS_HI16', 'D_800BE9A4')], 28: [('R_MIPS_LO16', 'D_800BE9A4')], 116: [('R_MIPS_26', 'sinf')], 128: [('R_MIPS_HI16', 'D_800AA45C')], 132: [('R_MIPS_LO16', 'D_800AA45C')], 164: [('R_MIPS_26', 'func_15133894')]}
HEADERS='#include <ultra64.h>\nextern f32 D_800AA454, D_800AA458, D_800AA45C, D_800BE9A4;\nf32 sinf(f32);\ns32 func_15133894(u8 *);\n\n'
DECLARATIONS='extern f32 D_800AA454, D_800AA458, D_800AA45C, D_800BE9A4;\nf32 sinf(f32);\ns32 func_15133894(u8 *);\n\n'
SELECTED="/* Advance the owner's phase and apply its sine-modulated scale. */\ns32 func_151B6254(u8 *owner) {\n    f32 *state = (f32 *)(owner + 0x170);\n    f32 period = D_800AA454;\n    f32 result;\n\n    *(f32 *)(owner + 0x170) += D_800AA458 * D_800BE9A4;\n    while (*state > period) {\n        *state -= period;\n    }\n    result = sinf(*state);\n    result = (result * (D_800AA45C * state[1])) + state[1];\n    *(f32 *)(owner + 0x18) = *(f32 *)(owner + 0x1C) = result;\n    return func_15133894(owner);\n}\n"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected owner-sine-scale owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=188 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner sine scale body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151B6254() {\n    return 0;\n}'
    if before.count(stub)!=1:raise ValueError('Owner sine scale placeholder changed')
    return before.replace('#include <ultra64.h>\n','#include <ultra64.h>\n\n'+DECLARATIONS,1).replace(stub,SELECTED.strip())


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner sine scale snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Owner sine scale frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Owner sine scale predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Owner sine scale live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Owner sine scale frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner sine scale original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    # Two closed linker name/definition permutations, reconstructed from input.
    named={name:(pos,fields,stringpos)for pos,name,fields,stringpos in symbol_rows(before)}
    groups=((('.L15032CC8_game_data','D_8009E774'),(2845476,2845492),3116991),
            (('D_800AA45C','D_800AA80C'),(2961428,2961444),3212569))
    for names,positions,stringpos in groups:
        pairs=[named[name]for name in names];labels=[name.encode()+b'\0'for name in names]
        if tuple(x[0]for x in pairs)!=positions or pairs[0][2]!=stringpos or pairs[1][2]!=stringpos+len(labels[0]):raise ValueError('Owner sine scale metadata positions changed')
        if before[stringpos:stringpos+sum(map(len,labels))]!=b''.join(labels):raise ValueError('Owner sine scale metadata names changed')
        result[stringpos:stringpos+sum(map(len,labels))]=b''.join(labels[::-1])
        namebase=pairs[0][1][0]
        for i,j in enumerate((1,0)):
            nameoff=namebase if i==0 else namebase+len(labels[1])
            struct.pack_into('>IIIBBH',result,pairs[i][0],nameoff,*pairs[j][1][1:])
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Owner sine scale strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Owner sine scale named definitions changed')

def derive_guards():
    rows=[]
    specs=((4,0xAFBF0014,0x3C010000,'-','R_MIPS_HI16:D_800AA454',''),
           (8,0x3C010000,0xC4220000,'R_MIPS_HI16:D_800AA454','R_MIPS_LO16:D_800AA454',''),
           (12,0xC4220000,0xAFBF0014,'R_MIPS_LO16:D_800AA454','-',''),
           (164,0x0C000000,0xE4820018,'R_MIPS_26:func_15133894','-',''),
           (168,0xE4820018,0x0C000000,'-','R_MIPS_26:func_15133894','0x00000000'))
    for offset,expected,replacement,oldrel,newrel,insert in specs:
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%offset,expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations=oldrel,replacement_relocations=newrel,note='Preserve retail save and global-load schedule plus pre-call output store and nop',insert_after=insert,insert_after_relocations='-'if insert else'',omit='false'))
    return rows

NEW_GUARDS=derive_guards()

def guard_manifest(before):
    import csv,io
    if sha(before)!='66db844df59f934b2a8008d1995d5fc5ec32d04c2e1be87199bc739190bfd4f9':raise ValueError('Owner sine scale inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Owner sine scale already patched')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fields,lineterminator=chr(13)+chr(10));writer.writerows(NEW_GUARDS)
    return before+stream.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);out=bytearray(raw)
    for row in NEW_GUARDS:
        at=int(row['offset'],0);expected=int(row['expected'],0)
        if struct.unpack_from('>I',out,at)[0]!=expected:raise ValueError('Owner sine scale guarded word changed')
        struct.pack_into('>I',out,at,int(row['replacement'],0))
    out[172:172]=bytes(4)
    relocated={at:value for at,value in bindings.items()if at not in(8,12,164)}
    relocated.update({4:[('R_MIPS_HI16','D_800AA454')],8:[('R_MIPS_LO16','D_800AA454')],168:[('R_MIPS_26','func_15133894')]})
    if len(out)!=BODY or sha(out)!='dd4115ac4a19a518d5d0d8ea0e395c9be360b6f157846bff86e2234c5682d64f':raise ValueError('Owner sine scale normalized body changed')
    return bytes(out),relocated

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151B6254.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_1E34C0.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1E34C0.c.o","make-shadow/src/game/generated_1E34C0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Owner sine scale artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner sine scale artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner sine scale raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Owner sine scale evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Owner sine scale Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1E34C0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Owner sine scale Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=5 or q['exclusions']!=0:raise ValueError('Owner sine scale private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Owner sine scale changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Owner sine scale protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=40,alignment_words=3,slot_words=51,strict_first_link_reproduced=True,guards=5,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
