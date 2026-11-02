"""Third integer oscillator: sequenced providers and complete-image closure."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools

BUILD='conker/build/game-third-integer-oscillator-150C673C-match'
BASELINE='05b63fbbce7c8dc92744419c597d3a01bbbc3840a19eee4fa22d9fbc96779d93'
LINKED='50a5fd84eaff7f7f4bb61300e1ff9200987ba37e6fc4a6fcde83140f71748416'
SPECS=(('func_150C673C','generated_F3BA0',0x150C673C,0xF3BEC),)
PATCHES=((0x44,0xAFA30018,0xAFA3001C),(0x50,0xA3A60023,0xA3A60027),(0x54,0x8FA30018,0x8FA3001C),(0x5C,0x83A60023,0x83A60027),(0x90,0x8FA30018,0x8FA3001C),(0x98,0x83A60023,0x83A60027))
RAW_SHA='011ba6f3f9cb1f60d7823aa80c3fc75fb5f2cf2d68576ac95086f88df745957f'
BINDINGS={28:[('R_MIPS_HI16','D_800BE9E4')],40:[('R_MIPS_LO16','D_800BE9E4')],76:[('R_MIPS_26','func_150ADA20')],136:[('R_MIPS_26','func_150ADA68')]}
sha=lambda data:hashlib.sha256(data).hexdigest()

def checked_payload(raw,bindings):
    if len(raw)!=240 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Oscillator payload or bindings changed')
    return raw,bindings

def normalized(raw,bindings):
    checked_payload(raw,bindings);out=bytearray(raw)
    for at,before,after in PATCHES:
        if struct.unpack_from('>I',out,at)[0]!=before:raise ValueError('Oscillator spill guard changed')
        struct.pack_into('>I',out,at,after)
    return bytes(out),bindings

def recovered_owner(before,target):
    function,owner,entry,rom=SPECS[target];lo,hi=function_span(before,function)
    if before[lo:hi]!='s32 '+function+'() {\n    return 0;\n}':raise ValueError('Oscillator predecessor changed')
    return before[:lo]+HEADERS.replace('#include <ultra64.h>\n','')+'/* Capture and clear notification, renew expired timing, then blend the signed rate. */\n'+SELECTED.replace(SPECS[0][0],function).rstrip()+before[hi:]

def snapshot(output):
    index=(output/'input-snapshot.json').read_bytes()
    if sha(index)!=SNAPSHOT_SHA:raise ValueError('Oscillator snapshot index changed')
    values={}
    for name,wanted in json.loads(index)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(data)!=wanted:raise ValueError('Oscillator frozen input changed: '+name)
        values[name]=data
    return values

def verify_prepared(output):
    index=(output/'prepared-artifacts.json').read_bytes()
    if sha(index)!=ARTIFACT_SHA:raise ValueError('Oscillator preparation index changed')
    for name,wanted in json.loads(index).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Oscillator preparation changed: '+name)
    return True

def predict(before,rom):
    if sha(before)!=BASELINE:raise ValueError('Oscillator image predecessor changed')
    out=bytearray(before)
    for function,owner,entry,offset in SPECS:
        row,=[r for r in symbol_rows(before)if r[1]==function]
        if row[2][1:3]!=(entry,12):raise ValueError('Oscillator predecessor extent changed')
        truth=rom[offset:offset+240]
        if len(truth)!=240:raise ValueError('Oscillator retail slot missing')
        at=elf_slot_offset(before,entry,240);out[at:at+240]=truth;struct.pack_into('>I',out,row[0]+8,240)
    return bytes(out)

def check_image(before,actual,rom):
    if actual!=predict(before,rom):raise ValueError('Oscillator entire image differs')

def expected_map(output):
    data=(output/'private-joint-linked.map').read_bytes()
    for _,owner,_,_ in SPECS:
        private=(BUILD.removeprefix('conker/')+'/make-shadow-'+owner+'/src/game/'+owner+'.c.o').encode()
        if data.count(private)!=9:raise ValueError('Oscillator map owner count changed')
        data=data.replace(private,('build/src/game/'+owner+'.c.o').encode())
    private=(BUILD.removeprefix('conker/')+'/private-joint-linked.elf').encode()
    if data.count(private)!=1:raise ValueError('Oscillator map output changed')
    return data.replace(private,b'build/conker.us.elf')

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:
        for i,(_,owner,_,_)in enumerate(SPECS):
            name='conker/src/game/'+owner+'.c';changes[name]=recovered_owner(values[name].decode(),i).encode()
            changes['conker/build/src/game/'+owner+'.c.o']=(output/('qualified-'+owner+'.o')).read_bytes()
        changes.update({'conker/retail_word_patches.us.csv':(output/'proposed-guards.csv').read_bytes(),
            'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin']),
            'conker/build/conker.us.map':expected_map(output)})
    for name,data in values.items():
        if (root/name).read_bytes()!=changes.get(name,data):raise ValueError('Oscillator live input changed: '+name)
    return values

def audit(root,output,installed=False):
    from tools.check_game_data_layout import audit_layout
    verify_prepared(output);values=check_inputs(root,output,installed)
    elf=root/'conker/build/conker.us.elf'if installed else output/'private-joint-linked.elf'
    actual=elf.read_bytes();check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'])
    if sha(actual)!=LINKED:raise ValueError('Oscillator linked image changed')
    data=audit_layout(elf,root/'conker')
    if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Oscillator protected data changed')
    targets={v[0]for v in SPECS};expected=Counter((n,f[1],240 if n in targets else f[2],*f[3:])for _,n,f,_ in symbol_rows(values['conker/build/conker.us.elf']))
    if expected!=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual)):raise ValueError('Oscillator named definition changed')
    q=json.loads((output/'private-owner-image-v4.json').read_text());q.update(private_only=not installed,installed=installed,matching_credit=1 if installed else 0,protected_data=data)
    if installed:(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n')
    return q

HEADERS='#include <ultra64.h>\ntypedef struct {\n    u32 opaque0;\n    u8 notification;\n    u8 opaque5[3];\n    f32 base;\n    f32 amplitude;\n    f32 target;\n    s16 remaining;\n    s16 minimum;\n    s16 range;\n    u16 opaque1A;\n    f32 gain;\n} EmbeddedIntegerOscillator;\nextern s32 D_800BE9E4;\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\n'
SELECTED='s32 func_150C673C(u8 *input) {\n    EmbeddedIntegerOscillator *oscillator;\n    s8 notified;\n    oscillator = (EmbeddedIntegerOscillator *)(input + 0xB0);\n    notified = 1;\n    if (oscillator->notification == 0) notified = 0;\n    oscillator->notification = 0;\n    oscillator->remaining -= (u32)D_800BE9E4;\n    if (oscillator->remaining < 0) {\n        u32 randomValue;\n        randomValue = (u32)func_150ADA20();\n        oscillator->remaining = randomValue % (oscillator->range + 1) + oscillator->minimum;\n        oscillator->target = func_150ADA68();\n        oscillator->target = oscillator->target * oscillator->amplitude + oscillator->base;\n    }\n    *(s32 *)(input + 0x24) = (u32)(s32)((oscillator->target - (f32)*(s32 *)(input + 0x24)) * oscillator->gain) + (u32)*(s32 *)(input + 0x24);\n    return notified;\n}\n'
SNAPSHOT_SHA='f4e69708d7504207e1da928a10d96af5aa43331cc758ff7b49fdad4ef7ddc2dc'
ARTIFACT_SHA='b8ed16aee8dba5a075380e7a84fed520274bbd4a28e189cbebf4b5c95fbda4bd'
