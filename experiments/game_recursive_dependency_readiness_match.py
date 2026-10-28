"""Recursive dependency readiness: guarded C private proposal, actual ABI and literal owner/image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import link_owner,function_span
from tools.experiments.game_view_list_setup import compile_owner as compile_retail_owner
def compile_owner(root,output,content,label,flags=("-O2","-g3")):
    if flags not in (("-O2","-g3"),("-O2","-g3","-Wo,-loopunroll,0")):raise ValueError("Unexpected recursive dependency compiler profile")
    return compile_retail_owner(root,output,content,label,no_unroll=True)
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1509CBD4','generated_C9EC0'
ENTRY,ROM,BODY,SIZE=0x1509CBD4,0xCA084,192,192
SOURCE='conker/src/game/generated_C9EC0.c'
OBJECT='conker/build/src/game/generated_C9EC0.c.o'
ASM='conker/asm/C9EC0.s'
BUILD='conker/build/game-recursive-dependency-readiness-match'
RAW_SHA="a70bbbf44cf0f326dded327566a1e9d78ef896e1d38095047e898c7e4ab31613"
SNAPSHOT_SHA="b2d6c5159401a61056d13b7b27ef9425bbbadc967c5545c3a228a3f9b5b10dda"
BEFORE_ELF_SHA="94a8c7a621abb2f884dbd959f6bb6ec427539b9f3a164f7efcf16299e0b708c3"
TRUTH_SHA="c5c69000b343e2f2c508a6a5186639631972bd019baae66b49b5d2bfeb34c4b0"
TABLE,BITMAP=0x8008743C,0x800D2E4C
BINDINGS={40:[('R_MIPS_HI16','D_8008743C')],48:[('R_MIPS_LO16','D_8008743C')],52:[('R_MIPS_HI16','D_800D2E4C')],56:[('R_MIPS_LO16','D_800D2E4C')],76:[('R_MIPS_26','func_1509CBD4')]}
NORMALIZED_BINDINGS=dict(BINDINGS)
HEADERS="#include <ultra64.h>\nextern s32 D_8008743C[];\n"
DECLARATIONS="extern u8 *D_800D2E4C;\n\n"
SELECTED="/* Require every dependency to be recursively ready and marked active. */\ns32 func_1509CBD4(s32 index) {\n    u16 *initial = *(u16 **)((u8 *)D_8008743C + index * 20);\n    u16 *dependency;\n    s32 child;\n    s32 result;\n    if ((child = *initial) != 0xFFFF) {\n        dependency = initial;\n        do {\n            result = func_1509CBD4(child);\n            child = *dependency;\n            if (!(D_800D2E4C[child >> 3] & (1 << (child & 7))) || result == 0) { return 0; }\n            child = *++dependency;\n        } while (child != 0xFFFF);\n    }\n    return 1;\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Recursive dependency readiness body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_1509CBD4() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Recursive dependency readiness placeholder changed')
    return before.replace(stub,DECLARATIONS+SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Recursive dependency readiness snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Recursive dependency readiness frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Recursive dependency readiness predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Recursive dependency readiness live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Recursive dependency readiness strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Recursive dependency readiness original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Recursive dependency readiness image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Recursive dependency readiness named ELF definitions changed')

def derive_guards():
    """Derive one closed entry layout, scratch allocation and symmetric compare."""
    expected={60:0x94500000,68:0x52130017,72:0x24020001,92:0x240A0001,
              96:0x001078C3,100:0x01F8C821,104:0x93280000,108:0x32090007,
              112:0x012A5804,116:0x010B6024,120:0x11800003,152:0x1613FFEC}
    result=dict(expected)
    # The raw opening load already produces a zero-extended halfword in S0.
    # Retail keeps it in T7, assigns the same S0 in a nonannulled delay slot,
    # and reaches the existing return-one instruction before the epilogue.
    result[60]=(expected[60]&~(31<<16))|(15<<16)
    result[68]=(4<<26)|(19<<21)|(15<<16)|((160-(68+4))//4)
    result[72]=(12<<26)|(15<<21)|(16<<16)|65535
    allocation={10:11,15:25,25:8,8:9,9:10,11:12,12:13}
    def exchange(word,fields):
        for shift in fields:
            reg=(word>>shift)&31;word=(word&~(31<<shift))|(allocation.get(reg,reg)<<shift)
        return word
    for at,fields in((92,(16,)),(96,(11,16)),(100,(21,16,11)),
                     (104,(21,16)),(108,(21,16)),(112,(21,16,11)),
                     (116,(21,16,11)),(120,(21,16))):
        result[at]=exchange(expected[at],fields)
    def commute(word):
        left,right=(word>>21)&31,(word>>16)&31
        return(word&~((31<<21)|(31<<16)))|(right<<21)|(left<<16)
    result[100]=commute(result[100]);result[116]=commute(result[116])
    result[152]=commute(expected[152])
    assert set(expected)==set(result)and all(expected[x]!=result[x]for x in expected)
    rows=[]
    for at in sorted(expected):
        note=('Normalize closed empty-list branch and delay-slot value lifetime'if at<76
              else'Normalize closed bitmap-check scratch allocation and commutative operands'if at<124
              else'Normalize symmetric loop sentinel comparison operand order')
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%at,
            expected='0x%08X'%expected[at],replacement='0x%08X'%result[at],
            expected_relocations='-',replacement_relocations='-',note=note,
            insert_after='',insert_after_relocations='',omit='false'))
    return rows

NEW_GUARDS=derive_guards()
def guard_manifest(before):
    import csv,io
    if sha(before)!='1383ae8599001c8769a2557ce1e4d2791f5f3bb5fcf8b59e822cdbc12e618f85':raise ValueError('Recursive dependency inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Recursive dependency guards already present')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator=chr(13)+chr(10));writer.writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);words=list(struct.unpack('>48I',raw));result_bindings={at:list(rs)for at,rs in bindings.items()};seen=set()
    for row in NEW_GUARDS:
        at=int(row['offset'],0);expected=';'.join(k+':'+n for k,n in result_bindings.get(at,[]))or'-'
        if at in seen or words[at//4]!=int(row['expected'],0)or row['expected_relocations']!=expected:raise ValueError('Recursive dependency expected word/binding changed')
        seen.add(at);words[at//4]=int(row['replacement'],0);replacement=row['replacement_relocations']
        if replacement=='-':result_bindings.pop(at,None)
        else:result_bindings[at]=[tuple(part.split(':',1))for part in replacement.split(';')]
    result=struct.pack('>48I',*words)
    if len(seen)!=12 or sha(result)!='1aa89546ea48a2aed2814cc77d4440fe10e33c207322144ee41d4f0de1efca8b'or result_bindings!=NORMALIZED_BINDINGS:raise ValueError('Recursive dependency normalized body/bindings changed')
    return result,result_bindings

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1509CBD4.o','first-linked.elf','proposed-word-patches.csv')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_C9EC0.c.o","make-shadow/src/game/generated_C9EC0.c.o.compact","make-shadow/src/game/generated_C9EC0.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Recursive dependency readiness artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Recursive dependency readiness artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Recursive dependency readiness raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Recursive dependency readiness evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Recursive dependency readiness Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected recursive dependency owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_C9EC0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Recursive dependency readiness Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=12 or q['exclusions']!=0:raise ValueError('Recursive dependency readiness private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Recursive dependency readiness changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Recursive dependency readiness protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,frame=40,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=12,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
