"""Record cleanup: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import csv,io,hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_15183C28','generated_1B0740'
ENTRY,ROM,BODY,SIZE=0x15183C28,0x1B10D8,256,256
SOURCE='conker/src/game/generated_1B0740.c'
OBJECT='conker/build/src/game/generated_1B0740.c.o'
ASM='conker/asm/1B0740.s'
BUILD='conker/build/game-record-cleanup-match'
RODATA_SYMBOL=None
RAW_SHA="1374415707fa28a2254fe640eb95fd8d3b5ad2c66eeb34b5d7cdc7045d8a15f9"
SNAPSHOT_SHA="629f6e9dae35fb9a8f50aec9bb9d6ef808598b260653d8c0bba26a414db96c40"
BEFORE_ELF_SHA="701bc876df16234842a1432aa15e06b2d3371a81a444b688863f8bf3b6fbeb14"
TRUTH_SHA="90705a513cb844fe9f21ee9e9784e038b2e4bbe4bc64c9e9a46c8c51ff5ac9f9"
TABLE,FLAG,VIEWS,RESOURCE,FREE=0x800DDE80,0x800DDF68,0x800DDF78,0x1510D630,0x10004074
BINDINGS={20:[("R_MIPS_HI16","D_800DDE80")],24:[("R_MIPS_LO16","D_800DDE80")],52:[("R_MIPS_26","func_1510D630")],80:[("R_MIPS_HI16","D_800DDF71")],84:[("R_MIPS_LO16","D_800DDF71")],116:[("R_MIPS_HI16","D_800DDF70")],120:[("R_MIPS_LO16","D_800DDF70")],128:[("R_MIPS_HI16","D_800DDF20")],140:[("R_MIPS_LO16","D_800DDF20")],156:[("R_MIPS_26","func_10004074")],164:[("R_MIPS_HI16","D_800DDF20")],168:[("R_MIPS_LO16","D_800DDF20")],172:[("R_MIPS_HI16","D_800DDF98")],184:[("R_MIPS_LO16","D_800DDF98")],204:[("R_MIPS_26","func_10004074")],220:[("R_MIPS_HI16","D_800DDF78")],236:[("R_MIPS_LO16","D_800DDF78")]}
HEADERS="#include <ultra64.h>\ntypedef struct { s32 words[5]; } Record15183974;\nextern Record15183974 D_800DDE80[11];\nextern u32 D_800DDF78[];\n"
DECLARATIONS="extern s8 D_800DDF70;\nextern s8 D_800DDF71;\nextern s32 D_800DDF20;\nextern u32 D_800DDF98;\nvoid func_1510D630(s16 *allocation);\nvoid func_10004074(void *allocation);\n\n"
SELECTED="/* Release a record's resources and its shared backing allocation when ready. */\nvoid func_15183C28(s32 index) {\n    s16 *resources;\n\n    resources = (s16 *)D_800DDE80[index].words[4];\n    if (resources != 0) {\n        func_1510D630(resources);\n        D_800DDE80[index].words[4] = 0;\n    }\n    if (index == 8) {\n        if (D_800DDF71 != -2) {\n            return;\n        }\n    } else if (index == 9) {\n        if (D_800DDF70 == -2 && D_800DDF20 != 0) {\n            func_10004074((void *)D_800DDF20);\n            D_800DDF20 = 0;\n            D_800DDF98 = 0;\n        }\n    }\n    if (D_800DDE80[index].words[0] != 0) {\n        func_10004074((void *)D_800DDE80[index].words[0]);\n        D_800DDE80[index].words[0] = 0;\n        D_800DDF78[index] = 0;\n    }\n}"

def check_owner_diagnostics(text):
    if text:raise ValueError('Unexpected record-cleanup owner diagnostics')
    return 0

sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=256 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record cleanup body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_15183C28() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Record cleanup placeholder changed')
    return before.replace(stub,(DECLARATIONS+SELECTED).strip(),1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record cleanup snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record cleanup frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record cleanup predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record cleanup live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record cleanup strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    named={}
    for pos,name,fields,_ in symbol_rows(before):named.setdefault(name,[]).append((pos,fields))
    rows=named[FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Record cleanup original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    # Three closed GNU symbol/string order changes; no named definition changes.
    cycles=((('D_80095B1C','D_8009951C','D_8009EF1C'),(2,0,1),(2755988,2756004,2756020),(29102,29113,29124)),(('D_800DDF20','D_80087320'),(1,0),(2819028,2819044),(81182,81193)),(('func_151137D4','D_8009E7E8'),(1,0),(2946628,2946644),(185684,185698)))
    all_rows=symbol_rows(before)
    for names,order,positions,name_offsets in cycles:
        groups=[[row for row in all_rows if row[1]==name]for name in names]
        if any(len(g)!=1 for g in groups):raise ValueError('Record cleanup metadata definitions changed')
        rows=[g[0]for g in groups]
        if tuple(row[0]for row in rows)!=positions or tuple(row[2][0]for row in rows)!=name_offsets:raise ValueError('Record cleanup metadata order changed')
        old_blob=b''.join(name.encode()+bytes([0])for name in names);new_blob=b''.join(names[k].encode()+bytes([0])for k in order);string_at=rows[0][3]
        if before[string_at:string_at+len(old_blob)]!=old_blob or len(old_blob)!=len(new_blob):raise ValueError('Record cleanup string cycle changed')
        result[string_at:string_at+len(old_blob)]=new_blob;cursor=name_offsets[0]
        for destination,k in zip(positions,order):
            fields=rows[k][2];struct.pack_into('>IIIBBH',result,destination,cursor,*fields[1:]);cursor+=len(names[k])+1
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record cleanup image differs from body and extent prediction')
    expected=Counter((n,f[1],256 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record cleanup named ELF definitions changed')

GUARDS={48:(0xAFA30018,0xAFA3001C),60:(0x8FA30018,0x8FA3001C),152:(0xAFA30018,0xAFA3001C),176:(0x8FA30018,0x8FA3001C),200:(0xAFA30018,0xAFA3001C),216:(0x8FA30018,0x8FA3001C)}
NEW_GUARDS=list(GUARDS)

def guard_manifest(before):
    if sha(before)!='91cfc61697b2f874f74475c5dadac1faec1f2e3c4f2a515d593b62d15b71ba03':raise ValueError('Inherited guard bytes changed')
    rows=list(csv.DictReader(io.StringIO(before.decode())))
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Record cleanup already guarded')
    stream=io.StringIO(newline='');fields=next(csv.reader(io.StringIO(before.decode())));writer=csv.DictWriter(stream,fields,lineterminator=chr(13)+chr(10))
    for at,(old,new)in GUARDS.items():writer.writerow(dict(filename=OWNER,function=FUNCTION,offset=hex(at),expected=hex(old),replacement=hex(new),expected_relocations='-',replacement_relocations='-',note='Normalize closed record pointer spill slot within unchanged frame',insert_after='',insert_after_relocations='',omit='false'))
    return before+stream.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);result=bytearray(raw)
    # One closed private spill moves from SP+0x18 to SP+0x1C; frame and ABI homes stay fixed.
    for at,(old,new)in GUARDS.items():
        if struct.unpack_from('>I',raw,at)[0]!=old:raise ValueError('Record cleanup spill changed')
        struct.pack_into('>I',result,at,new)
    if sha(result)!='7ffe0b68d8e84e65af974c184575d72425ffc88c644416910fd0ea01d6de157b':raise ValueError('Record cleanup normalized body changed')
    return bytes(result),bindings

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_15183C28.o','first-linked.elf')
EVIDENCE=("proposed-guards.csv","before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_1B0740.c.o.compact","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_1B0740.c.o","make-shadow/src/game/generated_1B0740.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record cleanup artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record cleanup artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record cleanup raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record cleanup evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record cleanup Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text())
    if(output/'make-shadow/src/game/generated_1B0740.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record cleanup Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=6 or q['exclusions']!=0:raise ValueError('Record cleanup private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record cleanup changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record cleanup protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=64,frame=32,alignment_words=0,slot_words=64,strict_first_link_reproduced=True,guards=6,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
