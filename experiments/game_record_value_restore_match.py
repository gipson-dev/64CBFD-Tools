"""Record value restore: guarded C, actual ABI and literal owner/image audit."""
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
FUNCTION,OWNER='func_151152A8','generated_142560'
ENTRY,ROM,BODY,SIZE=0x151152A8,0x142758,192,192
SOURCE='conker/src/game/generated_142560.c'
OBJECT='conker/build/src/game/generated_142560.c.o'
ASM='conker/asm/142560.s'
BUILD='conker/build/game-record-value-restore-match'
RAW_SHA="5bbf43f04a0ee142a0cfbe8459884080b347ca3d4649f16902babfe706f1409c"
SNAPSHOT_SHA="5460e100658a5a8f5844018d3bc1334b90410e1023e7b3a5682ee2cece098e22"
BEFORE_ELF_SHA="90784cd8cccfb9b4ada79065984003ebf4fc1ae7ead31cd2b824700665287087"
TRUTH_SHA="2a4fa7b16e13727b5a4cb0fe70e5b27dc351697f1c48222abcdb53823f680f08"
TICKS,FACTOR,TABLE=0x800BE9E4,0x800A2F8C,0x80088C90
BINDINGS={4:[('R_MIPS_HI16','D_800A2F8C')],52:[('R_MIPS_HI16','D_800BE9E4')],76:[('R_MIPS_LO16','D_800BE9E4')],116:[('R_MIPS_HI16','D_800BE9E4')],120:[('R_MIPS_LO16','D_800BE9E4')],128:[('R_MIPS_LO16','D_800A2F8C')]}
HEADERS="#include <ultra64.h>\n"
DECLARATIONS="extern s32 D_800BE9E4;\nextern f32 D_800A2F8C;\n"
SELECTED="/* Capture the initial value and advance the signed halfword by its selected mode. */\nvoid func_151152A8(u8 *record) {\n    s32 baseline = *(s32 *)(record + 0x7C);\n    s32 current;\n    s32 difference;\n    s32 packed;\n\n    if (baseline == 0) {\n        baseline = *(s16 *)(record + 0x12);\n        *(s32 *)(record + 0x7C) = baseline;\n    }\n    current = *(s16 *)(record + 0x12);\n    difference = (s32)((u32)baseline - (u32)current);\n    if (record[0x4F] & 4) {\n        packed = *(s32 *)(record + 0x3C);\n        if (difference < (s16)packed) {\n            *(s16 *)(record + 0x12) = (u32)current -\n                (u32)(s16)(packed >> 16) * (u32)D_800BE9E4;\n        }\n    } else {\n        *(s16 *)(record + 0x12) = (s32)((f32)current +\n            (f32)difference * D_800A2F8C * (f32)D_800BE9E4);\n    }\n}"
sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Record value restore body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    stub='s32 func_151152A8() {'+chr(10)+'    return 0;'+chr(10)+'}'
    if before.count(stub)!=1:raise ValueError('Record value restore placeholder changed')
    return before.replace('extern s32 D_800BE9E4;','extern s32 D_800BE9E4;'+chr(10)+'extern f32 D_800A2F8C;',1).replace(stub,SELECTED,1)


def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Record value restore snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Record value restore frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Record value restore predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Record value restore live input differs: '+name)
    return values

def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Record value restore strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[pos for pos,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Record value restore original extent changed')
    struct.pack_into('>I',result,rows[0]+8,BODY)
    # Exact GNU symbol/string permutation caused by the newly referenced factor.
    names=('D_800A2F8C','D_8009078C','func_151A8A78')
    triples=[next((p,n,f)for p,n,f,_ in symbol_rows(before)if n==name)for name in names]
    if [x[0]for x in triples]!=[0x2BA844,0x2BA854,0x2BA864]or[x[2][0]for x in triples]!=[115308,115319,115330]:raise ValueError('Record value metadata cycle changed')
    old_blob=b'D_800A2F8C\0D_8009078C\0func_151A8A78\0';new_blob=b'D_8009078C\0func_151A8A78\0D_800A2F8C\0'
    if before.count(old_blob)!=1 or len(old_blob)!=len(new_blob):raise ValueError('Record value string cycle changed')
    pos=before.index(old_blob);result[pos:pos+len(old_blob)]=new_blob
    for destination,index,name_at in zip((0x2BA844,0x2BA854,0x2BA864),(1,2,0),(115308,115319,115333)):
        fields=triples[index][2];struct.pack_into('>IIIBBH',result,destination,name_at,*fields[1:])
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Record value restore image differs from body and extent prediction')
    expected=Counter((n,f[1],192 if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Record value restore named ELF definitions changed')


NEW_GUARDS=json.loads('[{"filename": "generated_142560", "function": "func_151152A8", "offset": "0x00C", "expected": "0x908E004F", "replacement": "0x908F004F", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x018", "expected": "0x908E004F", "replacement": "0x908F004F", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x020", "expected": "0x31CF0004", "replacement": "0x31F80004", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x024", "expected": "0x51E00012", "replacement": "0x53000012", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x028", "expected": "0x00437823", "replacement": "0x0043C023", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x030", "expected": "0x0043C023", "replacement": "0x0043C823", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x034", "expected": "0x3C0C0000", "replacement": "0x3C0D0000", "expected_relocations": "R_MIPS_HI16:D_800BE9E4", "replacement_relocations": "R_MIPS_HI16:D_800BE9E4", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x038", "expected": "0x0005CC00", "replacement": "0x00054400", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x03C", "expected": "0x00194403", "replacement": "0x00084C03", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x040", "expected": "0x0308082A", "replacement": "0x0329082A", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x048", "expected": "0x00054C03", "replacement": "0x00055403", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x04C", "expected": "0x8D8C0000", "replacement": "0x8DAD0000", "expected_relocations": "R_MIPS_LO16:D_800BE9E4", "replacement_relocations": "R_MIPS_LO16:D_800BE9E4", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x050", "expected": "0x00095400", "replacement": "0x000A5C00", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x054", "expected": "0x000A5C03", "replacement": "0x000B6403", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x058", "expected": "0x016C0019", "replacement": "0x018D0019", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x05C", "expected": "0x00006812", "replacement": "0x00007012", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x060", "expected": "0x006D7023", "replacement": "0x006E7823", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x068", "expected": "0xA48E0012", "replacement": "0xA48F0012", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x06C", "expected": "0x00437823", "replacement": "0x0043C023", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x070", "expected": "0x448F2000", "replacement": "0x44982000", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x074", "expected": "0x3C190000", "replacement": "0x3C080000", "expected_relocations": "R_MIPS_HI16:D_800BE9E4", "replacement_relocations": "R_MIPS_HI16:D_800BE9E4", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x078", "expected": "0x8F390000", "replacement": "0x8D080000", "expected_relocations": "R_MIPS_LO16:D_800BE9E4", "replacement_relocations": "R_MIPS_LO16:D_800BE9E4", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x084", "expected": "0x44998000", "replacement": "0x44888000", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x0AC", "expected": "0x44085000", "replacement": "0x44095000", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}, {"filename": "generated_142560", "function": "func_151152A8", "offset": "0x0B4", "expected": "0xA4880012", "replacement": "0xA4890012", "expected_relocations": "-", "replacement_relocations": "-", "note": "Normalize one closed record-value restore compiler GPR allocation cycle", "insert_after": "", "insert_after_relocations": "", "omit": "false"}]')
def guard_manifest(before):
    import csv,io
    if sha(before)!='f867c3817abab6b6ef822343afa48a4b188e7067ce1d4c69a078b54a6f4b4c40':raise ValueError('Record value inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames;rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('Record value guard already present')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fields,lineterminator=chr(13)+chr(10));writer.writerows(NEW_GUARDS)
    return before+out.getvalue().encode()

def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);words=list(struct.unpack('>48I',raw));seen=set()
    for row in NEW_GUARDS:
        at=int(row['offset'],0);rs=';'.join(k+':'+n for k,n in bindings.get(at,[]))or'-'
        if at in seen or words[at//4]!=int(row['expected'],0)or row['expected_relocations']!=rs or row['replacement_relocations']!=rs:raise ValueError('Record value expected word/binding changed')
        seen.add(at);words[at//4]=int(row['replacement'],0)
    if len(seen)!=25:raise ValueError('Record value guard count changed')
    result=struct.pack('>48I',*words)
    if sha(result)!='293e0f2e158836f267e7414f2acb12a2d55b846ddf57497b2f6b570082fb358a':raise ValueError('Record value normalized body changed')
    return result,bindings

ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_151152A8.o','first-linked.elf','proposed-word-patches.csv')
EVIDENCE=("before-owner.c","before-owner-processed.c","before-owner.o","before-owner-diagnostics.txt","after-owner.c","after-owner-processed.c","after-owner.o","after-owner-diagnostics.txt","selected.c","selected-processed.c","selected.o","selected-diagnostics.txt","selected-input.c","make-shadow/src/game/generated_142560.c","actual-Make-plan.txt","Make-commands.json","actual-Make-diagnostics.txt","make-shadow/src/game/generated_142560.c.o","make-shadow/src/game/generated_142560.c.o.compact","make-shadow/src/game/generated_142560.c.o.padded.s",)

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Record value restore artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record value restore artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record value restore raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Record value restore evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Record value restore Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    if any((output/(n+'-diagnostics.txt')).read_bytes()for n in('before-owner','after-owner'))or(output/'actual-Make-diagnostics.txt').read_bytes():raise ValueError('Unexpected EEPROM owner/Make diagnostics')
    if(output/'make-shadow/src/game/generated_142560.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Record value restore Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=25 or q['exclusions']!=0:raise ValueError('Record value restore private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Record value restore changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record value restore protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=48,alignment_words=0,slot_words=48,strict_first_link_reproduced=True,guards=25,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
