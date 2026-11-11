import os,sys,hashlib,json,struct,csv,io,inspect,subprocess
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-151BC64C-match'
NAME='func_151BC64C';OWNER='game/generated_1E73B0';SOURCE='conker/src/game/generated_1E73B0.c';ENTRY=0x151BC64C;ROM=0x1E9AFC;SIZE=328
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import parse_object
from tools.experiments import game_sequence_direction_1501fe68_match as q
MANIFEST=json.loads(Path(__file__).with_name('game_ring_entry_update_151bc64c_manifest.json').read_text(encoding='utf-8'));FROZEN=MANIFEST['frozen'];PIN=MANIFEST['raw_pin'];p=sys.modules[__name__];n=p
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_151BC64C':328}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_1E73B0.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
SELECTED='#include <ultra64.h>\n#include "structs.h"\n\n/* Non-matching placeholders for the text-only asm slice asm/1E73B0.s. */\n\nextern s32 D_800BE9E4;\nextern f32 D_800AA860;\nextern f32 D_800AA864;\nextern f32 D_800AA82C;\nextern s32 D_800AA760;\nextern s32 D_800AA76C;\n\ns32 func_15160CDC(s32 arg0, s32 arg1, s32 *arg2, s32 *arg3, f32 arg4, s32 arg5, s32 arg6, s32 arg7, s32 arg8, s32 arg9, s32 arg10, s32 arg11, s32 arg12, s32 arg13, s32 arg14, s32 arg15);\nvoid func_1516972C(struct102 *arg0);\n\ns32 func_151B9F00() {\n    return 0;\n}\n\ns32 func_151BA084() {\n    return 0;\n}\n\ntypedef struct {\n    s32 value;\n    u8 tag;\n} OffsetReference1E73B0;\n\n\n/* Handle removal and ordered pair swaps through the owner\'s variable tail. */\nvoid func_151BA468(struct132 *owner, s32 pairAddress, u8 command) {\n    u8 *packet = (u8 *)pairAddress;\n    OffsetReference1E73B0 *link;\n    s32 first, current;\n    u8 *reference;\n\n    link = (OffsetReference1E73B0 *)((u8 *)owner + *(s32 *)((u8 *)owner + 0x50) + 0xF8);\n    reference = (u8 *)link->value;\n    current = link->value;\n    if (command == 0) {\n        first = *(s32 *)packet;\n        if (reference == (u8 *)first || reference[0x3B] == packet[4]) {\n            func_1516972C((struct102 *)owner);\n        }\n    } else {\n        if (command == 0x2D) {\n            first = *(s32 *)packet;\n            if (first == current) {\n                link->value = *(s32 *)(packet + 4);\n                link->tag = packet[9];\n            } else if (*(s32 *)(packet + 4) == current) {\n                link->value = first;\n                link->tag = packet[8];\n            }\n        }\n    }\n}\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_1E73B0/func_151BA518.s")\n\nu16 func_1000FA64(u16, s16, s16, s16, s32, u16, s16, s32, void *, s32, s32, s32);\ns32 func_151BB0E0();\n\n/* Register the actor\'s sound callback and return the sound-entry handle. */\nu16 func_151BB044(struct127 *actor) {\n    return func_1000FA64(0x4A7, (s16)(s32)actor->x_position,\n        (s16)(s32)actor->y_position, (s16)(s32)actor->z_position,\n        0x2000, 800, 200, (s32)func_151BB0E0, actor, 0, 8, 0);\n}\n\ns32 func_151BB0E0() {\n    return 0;\n}\n\ns32 func_151BB61C() {\n    return 0;\n}\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_1E73B0/func_151BBA9C.s")\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_1E73B0/func_151BBEE4.s")\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_1E73B0/func_151BBFBC.s")\n\ns32 func_151BC074(s32 arg0) {\n    if (arg0 != 0) {\n        return func_15160CDC(arg0, 1, &D_800AA760, &D_800AA76C, D_800AA82C, 2, 0x12C, 0xFF, 0xFF, 0xFF, 0xFF, 1, 0, 0, 0xFF, 1);\n    }\n}\n\ns32 func_151BC104() {\n    return 0;\n}\n\ns32 func_151BC370() {\n    return 0;\n}\n\ns32 func_151BC580(u8 *arg0) {\n    s32 *temp_v0 = *(s32 **) (arg0 + 0x40);\n\n    if (*temp_v0 == 0) {\n        return 0;\n    }\n    return 1;\n}\n\n/* Handle release notifications and update the inline descriptor pair. */\nvoid func_151BC5A4(struct102 *object, s32 eventAddress, u8 command) {\n    u8 *owner = (u8 *)object;\n    u8 *state = owner + 0x40;\n    s32 first = *(s32 *)state;\n    u8 *event = (u8 *)eventAddress;\n    s32 code = command;\n\n    if (command == 0) {\n        if (first == *(s32 *)event || event[4] == owner[0x44]) {\n            func_1516972C(object);\n        }\n    } else if (code == 0x2D) {\n        s32 value = *(s32 *)state;\n        first = *(s32 *)event;\n        if (first == value) {\n            *(s32 *)state = *(s32 *)(event + 4);\n            state[4] = event[9];\n        } else if (*(s32 *)(event + 4) == value) {\n            *(s32 *)state = first;\n            state[4] = event[8];\n        }\n    }\n}\n\ntypedef struct { f32 first, second, third; } RingValues151BC64C;\ntypedef struct { RingValues151BC64C values; s16 timer; u8 fade, retained0F; u32 retained10; } RingEntry151BC64C;\ntypedef struct {\n    u8 retained00[0x1E]; u16 flags;\n    u8 retained20[5]; u8 capacity; u8 retained26[6];\n    s8 count, current, end; u8 retained2F[0x25];\n    RingValues151BC64C output; u8 retained60[0x34]; RingEntry151BC64C *entries;\n} RingOwner151BC64C;\n\n/* Age ring entries, discard expired entries, and publish the current values. */\ns32 func_151BC64C(RingOwner151BC64C *owner) {\n    RingEntry151BC64C *entries = owner->entries;\n    s32 count = owner->count;\n    s32 index, current;\n    RingEntry151BC64C *entry;\n    s32 timer, shade;\n    if (count < 2 && (owner->flags & 8)) return 0;\n    index = owner->end;\n    current = owner->current;\n    while (index != current) {\n        index--;\n        if (index < 0) index = owner->capacity - 1;\n        entry = &entries[index];\n        entry->timer = (s16)((u32)(s32)entry->timer - (u32)D_800BE9E4);\n        timer = entry->timer;\n        if (timer < 0) {\n            while (index != current) {\n                owner->current = current + 1;\n                current = owner->current;\n                if (current == owner->capacity) {\n                    owner->current = 0;\n                    current = owner->current;\n                }\n                owner->count = owner->count - 1;\n            }\n        } else if (timer < 10) {\n            shade = timer * 25;\n            if (shade < entry->fade) entry->fade = shade;\n        }\n        current = owner->current;\n    }\n    if (owner->count > 0) {\n        owner->output = entries[current].values;\n    } else {\n        owner->output.first = 0.0f;\n        owner->output.second = 0.0f;\n        owner->output.third = 0.0f;\n    }\n    return 1;\n}\n\ns32 func_151BC794() {\n    return 0;\n}\n\ns32 func_151BCA90() {\n    return 0;\n}\n\nvoid func_151BD21C(u8 *arg0, u8 *arg1, u8 arg2) {\n    u8 *target = *(u8 **)(arg0 + 0x98);\n    s32 owner = *(s32 *)target;\n    s32 eventOwner;\n\n    if (arg2 == 0) {\n        if (*(s32 *)target == *(s32 *)arg1 || target[4] == arg1[4]) {\n            arg0[0x30] = 0;\n            *(u16 *)(arg0 + 0x1E) |= 8;\n        }\n    } else if (arg2 == 0x2D) {\n        eventOwner = *(s32 *)arg1;\n        if (eventOwner == owner) {\n            *(s32 *)target = *(s32 *)(arg1 + 4);\n            target[4] = arg1[9];\n        } else if (*(s32 *)(arg1 + 4) == owner) {\n            *(s32 *)target = eventOwner;\n            target[4] = arg1[8];\n        }\n    }\n}\n\ns32 func_151BD2BC(u8 *arg0) {\n    u8 *temp_v0 = *(u8 **) (arg0 + 0x28);\n\n    if (*(s32 *) temp_v0 == 0) {\n        return 0;\n    }\n    if (*(arg0 + 0x2C) != *(temp_v0 + 0x3B)) {\n        return 0;\n    }\n    return 1;\n}\n\ntypedef struct {\n    u8 ownerTag;\n    u8 padding1[3];\n    u8 *owner;\n    u8 enabled;\n    u8 padding9[3];\n    f32 parameters[6];\n    u8 kind;\n    u8 padding25;\n    s16 field26;\n    s16 field28;\n    s16 field2A;\n    u8 padding2C[2];\n    u8 field2E;\n    u8 field2F;\n    s8 field30;\n    u8 padding31[3];\n    f32 coefficient;\n    u8 field38;\n    s8 field39;\n    u8 padding3A[2];\n} MirroredEffectPacket;\nextern f32 D_800AA850;\nvoid *func_15134DAC(MirroredEffectPacket *, s32);\n\n/* Submit both sides using the packet fields left live by the first submission. */\nvoid func_151BD2F8(u8 *owner, s32 unused1, s32 unused2) {\n    MirroredEffectPacket packet;\n    u16 zero[1];\n    u8 *result;\n\n    if (owner != 0) {\n        packet.ownerTag = owner[0x3B];\n        packet.owner = owner;\n        packet.enabled = 1;\n        packet.parameters[0] = 31.0f;\n        packet.parameters[1] = -34.0f;\n        packet.parameters[2] = -117.0f;\n        packet.parameters[3] = 35.0f;\n        packet.parameters[4] = -24.0f;\n        packet.parameters[5] = -182.0f;\n        packet.kind = 0;\n        packet.field26 = 50;\n        packet.field28 = 100;\n        packet.field2A = 300;\n        packet.field2E = 4;\n        packet.field2F = 4;\n        packet.field30 = 3;\n        packet.field38 = 5;\n        packet.field39 = -1;\n        packet.coefficient = D_800AA850;\n        zero[0] = 0;\n        result = func_15134DAC(&packet, 2);\n        if (result != 0) {\n            memcpy(result + 0x80, zero, 2);\n        }\n        packet.parameters[0] = -packet.parameters[0];\n        packet.parameters[3] = -packet.parameters[3];\n        result = func_15134DAC(&packet, 2);\n        if (result != 0) {\n            memcpy(result + 0x80, zero, 2);\n        }\n    }\n}\n\ns32 func_151BD42C(u8 *arg0) {\n    *(s16 *)(arg0 + 0x80) = 0;\n    return 1;\n}\n\ns32 func_151BD43C() {\n    return 0;\n}\n\nf32 func_151BD750(u8 *arg0) {\n    s16 temp_v0 = *(s16 *)(arg0 + 0x80);\n    f32 result = (f32) temp_v0 * 2.0f * D_800AA860 + D_800AA864;\n\n    *(s16 *)(arg0 + 0x80) = temp_v0 + D_800BE9E4;\n    return result;\n}\n\ns32 func_151BD79C(u8 *arg0) {\n    u8 *temp_v0 = *(u8 **)(arg0 + 0xB0);\n\n    if (*(s32 *) temp_v0 != 0 && *(u8 *)(temp_v0 + 4) != 0xFF) {\n        *(f32 *)(arg0 + 0x4C) = *(f32 *)(temp_v0 + 0x14);\n        *(f32 *)(arg0 + 0x50) = *(f32 *)(temp_v0 + 0x18);\n        *(f32 *)(arg0 + 0x54) = *(f32 *)(temp_v0 + 0x1C);\n    }\n    return func_1513170C(arg0);\n}\n\ns32 func_151BD7F4(u8 *arg0) {\n    struct { u8 *ptr; u8 value; } temp;\n\n    temp.ptr = arg0;\n    temp.value = *(u8 *)(arg0 + 0x3B);\n    func_151494E0(&temp, 0x3B);\n}\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_1E73B0/func_151BD828.s")\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_1E73B0/func_151BDD8C.s")\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_1E73B0/func_151BE0AC.s")\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_1E73B0/func_151BE138.s")\n\ns32 func_151BE1B8(s32 arg0) {\n    func_151BE138(arg0);\n    func_1514933C(arg0);\n}\n\ns32 func_151BE1E4(s32 arg0) {\n    func_151BE138(arg0);\n    func_15149368(arg0);\n}\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_1E73B0/func_151BE210.s")\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_1E73B0/func_151BE4B8.s")\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_1E73B0/func_151BE558.s")\n\nvoid func_151BE604(u8 *arg0, s32 arg1, u8 arg2) {\n    func_15169850(arg1, arg2, (s32) (arg0 + 0x110), (s32) (arg0 + 0x114), (s32) arg0);\n}\n\nvoid func_151BE644(u8 *arg0) {\n    u8 *temp_v0 = arg0 + 0x110;\n\n    if (*(s32 *)(arg0 + 0x160) != 0) {\n        u8 *temp_v1 = *(u8 **)(temp_v0 + 0x50) + 0x28;\n        *(s32 *)(temp_v1 + (*(u8 *)(temp_v0 + 5) * 4) + 8) = 0;\n    }\n}\n\ns32 func_151BE674(s32 arg0) {\n    func_151BE644(arg0);\n    func_1513CA6C(arg0);\n}\n\ns32 func_151BE6A0(s32 arg0) {\n    func_151BE644(arg0);\n    func_1513CAA0(arg0);\n}\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_1E73B0/func_151BE6CC.s")\n\nvoid func_151BE788(u8 *arg0, s32 arg1, u8 arg2) {\n    func_15169850(arg1, arg2, (s32) (arg0 + 0x180), (s32) (arg0 + 0x184), (s32) arg0);\n}\n\nvoid func_151BE7C8(u8 *arg0) {\n    u8 *temp_v0 = arg0 + 0x170;\n\n    if (*(s32 *)(arg0 + 0x178) != 0) {\n        u8 *temp_v1 = *(u8 **)(temp_v0 + 8) + 0x28;\n        *(s32 *)(temp_v1 + (*(u8 *)(temp_v0 + 0xC) * 4) + 0x10) = 0;\n    }\n}\n\ns32 func_151BE7F8(s32 arg0) {\n    func_151BE7C8(arg0);\n    func_151411A4(arg0);\n}\n\ns32 func_151BE824(s32 arg0) {\n    func_151BE7C8(arg0);\n    func_151411C4(arg0);\n}\n\ns32 func_151BE850() {\n    return 0;\n}\n\ns32 func_151BEB20() {\n    return 0;\n}\n\ns32 func_151BEC94(s32 arg0, s32 arg1, s32 arg2, s32 arg3, u8 *arg4) {\n    *arg4 = 1;\n    return arg0;\n}\n\ns32 func_151BECB8() {\n    return 0;\n}\n\ns32 func_151BEE94(u8 *arg0) {\n    s32 temp_v0 = 0xFF;\n\n    if (temp_v0 == *(arg0 + 0x127)) {\n        return 0;\n    }\n    if (*(s32 *) arg0 == 0) {\n        return 0;\n    }\n    if (temp_v0 == *(arg0 + 4)) {\n        return 0;\n    }\n    return 1;\n}\n\ns32 func_151BEEE0() {\n    return 0;\n}\n\ns32 func_151BF0C8() {\n    return 0;\n}\n\ns32 func_151BF340() {\n    return 0;\n}\n\ns32 func_151BF81C() {\n    return 0;\n}\n\nvoid func_151BFB2C(u8 *arg0) {\n    u8 *base = arg0 + 0x28;\n    s32 i;\n\n    if (*(void **)base != NULL) {\n        func_1516972C(*(void **)base);\n    }\n    i = 0;\n    do {\n        void *entry = *(void **)(base + 4 + i * 4);\n\n        if (entry != NULL) {\n            func_1516972C(entry);\n        }\n        i++;\n    } while ((i = (u8)i) < 2);\n}\n\ns32 func_151BFBA4(s32 arg0) {\n    func_151BFB2C(arg0);\n    func_1514933C(arg0);\n}\n\ns32 func_151BFBD0(s32 arg0) {\n    func_151BFB2C(arg0);\n    func_15149368(arg0);\n}\n\nvoid func_151BFBFC(u8 *arg0, u8 arg1, u8 arg2) {\n    if (arg2 == 0x57) {\n        func_1516972C((struct102 *)arg0);\n    }\n}\n'
def payload(path):
 data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def decode(rows):return {int(k):[tuple(x)for x in v]for k,v in rows.items()}
def normalize(raw,refs):
 if len(raw)!=324 or sha(raw)!=PIN['raw_sha256'] or refs!=decode(PIN['raw_refs']):raise ValueError('Ring-entry body or bindings changed')
 words=list(struct.unpack('>81I',raw));outwords=[];outrefs={};patches={r['index']:r for r in PIN['rows']}
 if len(patches)!=29:raise ValueError('Unexpected guard count')
 for i,word in enumerate(words):
  row=patches.get(i);current=refs.get(4*i,[])
  if row:
   expected=[tuple(x)for x in row['expected_relocations']];replacement=[tuple(x)for x in row['replacement_relocations']]
   if word!=int(row['expected'],16) or current!=expected:raise ValueError('Ring-entry word guard changed')
   word=int(row['replacement'],16);current=replacement
  if current:outrefs[4*len(outwords)]=current
  outwords.append(word)
  if row and row['insert_after'] is not None:
   inserted=[tuple(x)for x in row['insert_after_relocations']]
   if inserted:outrefs[4*len(outwords)]=inserted
   outwords.append(int(row['insert_after'],16))
 if len(outwords)!=82 or outrefs!=decode(PIN['retail_refs']):raise ValueError('Ring-entry output length or bindings changed')
 return struct.pack('>82I',*outwords),outrefs
def relocation_spec(rows):return ';'.join(kind+':'+name for kind,name in rows)if rows else '-'
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='generated_1E73B0',function=NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['expected'],replacement='0x'+d['replacement'],expected_relocations=relocation_spec(d['expected_relocations']),replacement_relocations=relocation_spec(d['replacement_relocations']),note='Normalize ring-entry updater register allocation and control flow',insert_after=('0x'+d['insert_after']if d['insert_after']else ''),insert_after_relocations=(relocation_spec(d['insert_after_relocations'])if d['insert_after']else ''),omit='false')for d in PIN['rows']]
def write_csv():
 raw,refs=payload(out/'final.o');before=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode())

def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption ring-entry updater input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen ring-entry updater input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown ring-entry updater source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed ring-entry updater qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed ring-entry updater result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Ring-entry updater source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)




def assemble_original():
 whole=(out/'frozen/conker/asm/1E73B0.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;target=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';src=out/'original_151BC64C.s';src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+NAME+',.-'+NAME+'\n');obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)

def main():
 q.p=p
 frozen,installed=freeze()
 assemble_original()
 source=SELECTED;old=(out/'frozen'/SOURCE).read_bytes();nl='\r\n'if b'\r\n'in old else '\n';proposal=out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(out/'selected-source.c').write_text(source)
 compile_owner(root,out,source,'final');write_csv()
 targets,commands=q.actual_make({OWNER:proposal});obj=targets[OWNER];compact=Path(str(obj)+'.compact');before,bd=compile_owner(root,out,old.decode(),'independent-before');after,ad=compile_owner(root,out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(NAME,))==56 and same_functions(compact,after)==57 and same_functions(out/'frozen/conker/build/src/game/generated_1E73B0.c.o',obj,(NAME,))==56
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 def payload(o):
  data,fs,rs=parse_object(o);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 raw,refs=payload(compact);original,origrefs=payload(out/'original_151BC64C.o');fixed,freferences=payload(obj);assert (fixed,freferences)==(original,origrefs);assert sha(raw)==PIN['raw_sha256'];assert normalize(raw,refs)==(fixed,freferences)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(fixed,freferences,{nm:lookup[nm]for es in freferences.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0x1E9AFC:0x1E9AFC+328];assert struct.pack('>82I',*words)==truth
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and{name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={NAME}
 data=audit_layout(elf,root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((SOURCE,proposal),('conker/retail_word_patches.us.csv',out/'proposed-guards.csv'),('conker/build/src/game/generated_1E73B0.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=81,retail_words=82,guards=29,inserted_words=1,non_target_neighbors=56,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from ring-entry workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
