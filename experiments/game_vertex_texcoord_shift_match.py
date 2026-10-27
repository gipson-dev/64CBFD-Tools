"""Vertex texture-coordinate shift: guarded C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_15116058','generated_142560'
ENTRY,ROM,BODY,SIZE=0x15116058,0x143508,184,184
SOURCE='conker/src/game/generated_142560.c'
OBJECT='conker/build/src/game/generated_142560.c.o'
ASM='conker/asm/142560.s'
BUILD='conker/build/game-vertex-texcoord-shift-match'
RAW_SHA='4038e27a208a573949810c3baf0f1a75c3ae1513dc422a1d975853e1b06cef40'
SNAPSHOT_SHA='3850f9037183934a33b3bea9b189db221ac883b430ff06ec8eea39a3d83c252e'
BEFORE_ELF_SHA='fab3176a559a9a2b3a7e9a61539fa4e48b94c953b3819893b6454bfef01084f4'
TRUTH_SHA='e35bf0e081c84c8a46c5344dbf171aee7ad9bbc5ee401a359594cb174bcfa5b3'
SELECTOR=0x800BE9C0
BINDINGS={36:[('R_MIPS_HI16','D_800BE9C0')],44:[('R_MIPS_LO16','D_800BE9C0')]}
GUARD_SHA="0a217eed8db620f8a20448d2b0fd665ae437deaf9b4fa1d3ab5beded44c2b070"
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="typedef struct {\n    u8 reserved[0x16];\n    u16 vertexCount;\n    u8 reserved18[8];\n    u8 *buffers[2];\n    u8 reserved28[0x14];\n    s32 packedOffset;\n} TexcoordShiftRecord;\nextern u8 D_800BE9C0;\n"
SELECTED="/* Add packed signed offsets to texture coordinates in the selected buffer. */\nvoid func_15116058(TexcoordShiftRecord *record) {\n    s16 offsetS = record->packedOffset >> 16;\n    s16 offsetT = record->packedOffset & 0xFFFF;\n    s32 index = 0;\n    s32 offset;\n\n    if (record->vertexCount > 0) {\n        offset = 0;\n        do {\n            *(s16 *)(record->buffers[D_800BE9C0] + offset + 8) =\n                *(s16 *)(record->buffers[!D_800BE9C0] + offset + 8) + offsetS;\n            *(s16 *)(record->buffers[D_800BE9C0] + offset + 10) =\n                *(s16 *)(record->buffers[!D_800BE9C0] + offset + 10) + offsetT;\n            index++;\n            offset += 16;\n        } while (index < record->vertexCount);\n    }\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Vertex texture-coordinate shift body/bindings changed')
    return raw,bindings


# These permutations follow the packed/shift/count definitions before the loop,
# then the two closed GPR cycles used for the entire loop. No opcode, immediate,
# memory operation, branch target or arithmetic expression changes.
LOOP_ROLES={0:0,6:6,8:7,7:3,11:24,4:4,12:25,13:10,25:14,10:15,3:8,14:11,15:12,2:2,24:13,9:9,5:5,1:1,31:31}
GUARD_WORDS=(0,1,3,4,5,6,7,8,10,11,12,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,43)

def normalized(raw,bindings):
    checked_payload(raw,bindings);words=list(struct.unpack('>46I',raw));result=[]
    if set(LOOP_ROLES)!=set(LOOP_ROLES.values()):raise ValueError('Texture-coordinate loop roles are not a permutation')
    opening=({5:12},{10:15},{},{5:12,2:24},{2:24,14:25},{5:12,24:13},{14:25},{10:15},{24:13})
    for i,word in enumerate(words):
        op=word>>26;roles=opening[i]if i<9 else LOOP_ROLES
        if op not in(0,6,9,11,15,21,33,35,36,37,41):raise ValueError('Unexpected texture-coordinate opcode')
        if op==0 and word&63 not in(0,3,8,33,37,42):raise ValueError('Unexpected texture-coordinate register operation')
        a,b,d=word>>21&31,word>>16&31,word>>11&31
        changed=(word&0xFC00FFFF)|(roles.get(a,a)<<21)|(roles.get(b,b)<<16)
        if op==0:changed=(changed&0xFFFF07FF)|(roles.get(d,d)<<11)
        result.append(changed)
    # The LO16 address add and independent cursor zero share no written/read GPR.
    if words[10]!=0x00001825 or words[11]!=0x25290000:raise ValueError('Independent opening schedule changed')
    result[10],result[11]=result[11],result[10]
    if tuple(i for i,(a,b)in enumerate(zip(words,result))if a!=b)!=GUARD_WORDS:raise ValueError('Texture-coordinate guard closure changed')
    updated=dict(bindings);updated[40]=updated.pop(44)
    return struct.pack('>46I',*result),updated

def guard_bytes(old,raw,bindings):
    import csv,io
    if sha(old)!=GUARD_SHA:raise ValueError('Texture-coordinate guard history changed')
    reader=csv.DictReader(io.StringIO(old.decode()));schema=reader.fieldnames
    if schema!=['filename','function','offset','expected','replacement','expected_relocations','replacement_relocations','note','insert_after','insert_after_relocations','omit']:raise ValueError('Texture-coordinate guard schema changed')
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Texture-coordinate guards already exist')
    fitted,updated=normalized(raw,bindings);before=struct.unpack('>46I',raw);after=struct.unpack('>46I',fitted)
    newline='\r\n'if old.endswith(b'\r\n')else'\n'
    if not old.endswith(newline.encode()):raise ValueError('Texture-coordinate guard terminator missing')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=schema,lineterminator=newline)
    for i in GUARD_WORDS:
        rel=lambda entries:';'.join(kind+':'+name for kind,name in entries)or'-'
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(i*4),expected='0x%08X'%before[i],replacement='0x%08X'%after[i],expected_relocations=rel(bindings.get(i*4,[])),replacement_relocations=rel(updated.get(i*4,[])),note='Close texture-coordinate GPR lifetimes and independent opening address schedule',omit='false'))
    return old+stream.getvalue().encode()

def recovered_owner(before):
    stub='s32 func_15116058() {\n    return 0;\n}'
    if before.count(stub)!=1 or 'TexcoordShiftRecord'in before:raise ValueError('Texture-coordinate placeholder changed')
    return before.replace(stub,DECLARATIONS+'\n'+SELECTED,1)

def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Vertex texture-coordinate shift snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Vertex texture-coordinate shift frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Vertex texture-coordinate shift predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE]),'conker/retail_word_patches.us.csv':guard_bytes(values['conker/retail_word_patches.us.csv'],*payload(output/'after-owner.o'))}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Vertex texture-coordinate shift live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Vertex texture-coordinate shift strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Vertex texture-coordinate shift original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Vertex texture-coordinate shift image differs from the closed body/extent/serialization prediction')
    expected=Counter((n,f[1],184 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Vertex texture-coordinate shift named ELF definitions changed')

ARTIFACTS=('qualified-guards.csv','before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15116058.o','first-linked.elf')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","actual-Make-plan.txt","Make-commands.json","make-shadow/src/game/generated_142560.c.o","make-shadow/src/game/generated_142560.c.o.compact","make-shadow/src/game/generated_142560.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Vertex texture-coordinate shift artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Vertex texture-coordinate shift artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Vertex texture-coordinate shift raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Vertex texture-coordinate shift evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Vertex texture-coordinate shift Make/diagnostics evidence changed: '+name)
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner','selected')):raise ValueError('Vertex texture-coordinate shift expected empty diagnostics')
    if(output/'make-shadow/src/game/generated_142560.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Vertex texture-coordinate shift Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=40 or q['exclusions']!=0:raise ValueError('Vertex texture-coordinate shift private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Vertex texture-coordinate shift changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Vertex texture-coordinate shift protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=46,strict_first_link_reproduced=True,guards=40,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
