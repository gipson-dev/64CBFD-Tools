import os,sys,hashlib,json,struct,csv,io,inspect,subprocess
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-1514BE20-match'
NAME='func_1514BE20';OWNER='game/generated_176A00';SOURCE='conker/src/game/generated_176A00.c';ENTRY=0x1514BE20;ROM=0x1792D0;SIZE=304
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
MANIFEST=json.loads(Path(__file__).with_name('game_actor_radial_offset_1514be20_manifest.json').read_text(encoding='utf-8'));FROZEN=MANIFEST['frozen'];PIN=MANIFEST['raw_pin'];p=sys.modules[__name__];n=p
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_1514BE20':304}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_176A00.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
SELECTED='#include <ultra64.h>\n#include "structs.h"\n\ntypedef s32 (*RadialCallback176A00)(s32, s16, f32, f32, f32, f32, f32, f32, u8, u8, f32, s32, f32, s32, u8);\nextern RadialCallback176A00 D_8008AA00[];\nf32 func_151423D8(u8);\n\nextern f32 D_800A57A0, D_800A57A4, D_800A57A8, D_800A57AC;\nvoid func_1513F680(struct171 *, u8, u8, u8, u8);\n\n/* Partially recovered text-only slice asm/176A00.s. */\n\nextern f32 D_800BE9A4;\n\ns32 func_1514BC08();\n\ns32 func_15149550() {\n    return 0;\n}\n\ns32 func_15149838() {\n    return 0;\n}\n\ns32 func_15149A94() {\n    return 0;\n}\n\ns32 func_15149BF4(u8 *arg0) {\n    *(f32 *)(arg0 + 0x2C) -= *(f32 *)(arg0 + 0x2C) * *(f32 *)(arg0 + 0x150);\n    *(f32 *)(arg0 + 0x30) -= *(f32 *)(arg0 + 0x30) * *(f32 *)(arg0 + 0x150);\n\n    if (*(f32 *)(arg0 + 0x2C) < 2.0f || *(f32 *)(arg0 + 0x30) < 2.0f) {\n        return 0;\n    }\n    return 1;\n}\n\n/* Damp billboard extents, integrate vertical motion and test the active bounds. */\ns32 func_15149C58(u8 *actor) {\n    *(f32 *)(actor + 0x2C) -= *(f32 *)(actor + 0x2C) * *(f32 *)(actor + 0x150);\n    *(f32 *)(actor + 0x30) -= *(f32 *)(actor + 0x30) * *(f32 *)(actor + 0x150);\n    *(f32 *)(actor + 0x50) += *(f32 *)(actor + 0x4C) * D_800BE9A4;\n    *(f32 *)(actor + 0x38) += *(f32 *)(actor + 0x50) * D_800BE9A4;\n    if (*(f32 *)(actor + 0x15C) < *(f32 *)(actor + 0x38)) {\n        return 0;\n    }\n    if (*(f32 *)(actor + 0x2C) < 4.0f || *(f32 *)(actor + 0x30) < 4.0f) {\n        return 0;\n    }\n    return 1;\n}\n\ns32 func_15149D18() {\n    return 0;\n}\n\ntypedef struct { f32 x, y, z; } EffectPosition176A00;\ntypedef struct {\n    EffectPosition176A00 position;\n    u8 retained0C[10];\n    s16 value16, value18, value1A, value1C, value1E, value20;\n    s16 value22, value24, value26;\n    u8 firstRGB[3], secondRGB[3], alpha, value2F;\n    s8 value30;\n    u8 flags;\n} EffectDescriptor176A00;\ns32 func_150ADA20(void);\nvoid func_151429E0(u8, u8 *, u8 *, u8 *);\nvoid func_1518CA80(EffectDescriptor176A00 *, u8);\n\n/* Submit a position snapshot with ordered random fields and two color rows. */\ns32 func_15149EC4(u8 *actor) {\n    EffectDescriptor176A00 descriptor;\n\n    descriptor.position = *(EffectPosition176A00 *)(actor + 0x34);\n    descriptor.value16 = 0;\n    descriptor.value18 = 0;\n    descriptor.value1A = descriptor.value1C = (u32)func_150ADA20() % 6u + 8;\n    descriptor.value1E = 0;\n    descriptor.value20 = 0;\n    descriptor.value22 = (u32)func_150ADA20() % 201u + 100;\n    descriptor.value24 = (u32)func_150ADA20() % 5u + 3;\n    descriptor.value26 = 600;\n    func_151429E0(3, &descriptor.firstRGB[0], &descriptor.firstRGB[1], &descriptor.firstRGB[2]);\n    func_151429E0(4, &descriptor.secondRGB[0], &descriptor.secondRGB[1], &descriptor.secondRGB[2]);\n    descriptor.alpha = 255;\n    descriptor.value2F = (u32)func_150ADA20() % 65u + 92;\n    descriptor.value30 = (u32)func_150ADA20() % 3u + 1;\n    descriptor.flags = 0;\n    func_1518CA80(&descriptor, 1);\n    return 0;\n}\n\ns32 func_15149FD0() {\n    return 0;\n}\n\ns32 func_1514A19C() {\n    return 0;\n}\n\n/* Approach both target extents, then select the settled update callback. */\ns32 func_1514A380(u8 *owner) {\n    s32 complete = 1;\n    u8 *payload = owner + 0x110;\n\n    if ((owner[0x74] & 2) == 0) {\n        *(f32 *)(owner + 0x2C) +=\n            (*(f32 *)(payload + 8) - *(f32 *)(owner + 0x2C)) * D_800A57A0;\n        if (*(f32 *)(payload + 8) * D_800A57A4 < *(f32 *)(owner + 0x2C)) {\n            owner[0x74] |= 2;\n        } else {\n            complete = 0;\n        }\n    }\n    if ((owner[0x74] & 8) == 0) {\n        *(f32 *)(owner + 0x30) +=\n            (*(f32 *)(payload + 0x18) - *(f32 *)(owner + 0x30)) * D_800A57A8;\n        if (*(f32 *)(payload + 0x18) * D_800A57AC < *(f32 *)(owner + 0x30)) {\n            owner[0x74] |= 8;\n        } else {\n            complete = 0;\n        }\n    }\n    if (complete) {\n        func_1513F680((struct171 *)owner, owner[0x70], 4, owner[0x72], owner[0x73]);\n    }\n    return 1;\n}\n\ns32 func_1514A498(u8 *arg0) {\n    f32 value0 = *(f32 *)(arg0 + 0x30);\n    f32 scale = *(f32 *)(arg0 + 0x144);\n    f32 value1 = *(f32 *)(arg0 + 0x2C);\n    s32 index = *(s16 *)(arg0 + 0x1C);\n\n    *(f32 *)(arg0 + 0x30) = value0 - (value0 * scale);\n    *(f32 *)(arg0 + 0x2C) = value1 - (value1 * scale);\n    if (index < *(s16 *)(arg0 + 0x156)) {\n        arg0[0x5C] = (u32)index * (u32)*(s16 *)(arg0 + 0x158);\n    }\n    return 1;\n}\n\n/* Snapshot position, damp horizontal velocity and integrate the live timestep. */\ns32 func_1514A4EC(u8 *actor) {\n    f32 damping = *(f32 *)(actor + 0x140);\n\n    *(u32 *)(actor + 0x40) = *(u32 *)(actor + 0x34);\n    *(u32 *)(actor + 0x44) = *(u32 *)(actor + 0x38);\n    *(u32 *)(actor + 0x48) = *(u32 *)(actor + 0x3C);\n    *(f32 *)(actor + 0x130) *= damping;\n    *(f32 *)(actor + 0x134) += *(f32 *)(actor + 0x13C) * D_800BE9A4;\n    *(f32 *)(actor + 0x138) *= damping;\n    *(f32 *)(actor + 0x34) += *(f32 *)(actor + 0x130) * D_800BE9A4;\n    *(f32 *)(actor + 0x38) += *(f32 *)(actor + 0x134) * D_800BE9A4;\n    *(f32 *)(actor + 0x3C) += *(f32 *)(actor + 0x138) * D_800BE9A4;\n    return 1;\n}\n\n/* Integrate two points, then blend the second toward the first. */\ns32 func_1514A594(u8 *owner) {\n    f32 *record = (f32 *)owner;\n    f32 dx, yComponent, zComponent;\n    f32 weight;\n    f32 firstX;\n\n    *(f32 *)(owner + 0x130) *= *(f32 *)(owner + 0x140);\n    *(f32 *)(owner + 0x134) += *(f32 *)(owner + 0x13C) * D_800BE9A4;\n    *(f32 *)(owner + 0x138) *= *(f32 *)(owner + 0x140);\n    dx = record[0x130 / 4] * D_800BE9A4;\n    yComponent = record[0x134 / 4] * D_800BE9A4;\n    zComponent = record[0x138 / 4] * D_800BE9A4;\n    record[0x34 / 4] += dx;\n    record[0x38 / 4] += yComponent;\n    record[0x3C / 4] += zComponent;\n    record[0x40 / 4] += dx;\n    record[0x44 / 4] += yComponent;\n    record[0x48 / 4] += zComponent;\n    firstX = record[0x34 / 4];\n    weight = record[0x54 / 4];\n    /* The finished Y/Z steps can now hold the first-point coordinates. */\n    yComponent = record[0x38 / 4];\n    zComponent = record[0x3C / 4];\n    record[0x40 / 4] = firstX + (record[0x40 / 4] - firstX) * weight;\n    record[0x44 / 4] = yComponent + (record[0x44 / 4] - yComponent) * weight;\n    record[0x48 / 4] = zComponent + (record[0x48 / 4] - zComponent) * weight;\n    return 1;\n}\n\ns32 func_1514A6A0() {\n    return 0;\n}\n\ns32 func_1514AB5C() {\n    return 0;\n}\n\ns32 func_1514AD9C() {\n    return 0;\n}\n\n/* Damp billboard extents and integrate position before advancing vertical velocity. */\ns32 func_1514AF74(u8 *actor) {\n    *(f32 *)(actor + 0x2C) -= *(f32 *)(actor + 0x2C) * *(f32 *)(actor + 0x150);\n    *(f32 *)(actor + 0x30) -= *(f32 *)(actor + 0x30) * *(f32 *)(actor + 0x150);\n    *(f32 *)(actor + 0x38) += *(f32 *)(actor + 0x50) * D_800BE9A4 +\n        0.5f * *(f32 *)(actor + 0x4C) * D_800BE9A4 * D_800BE9A4;\n    *(f32 *)(actor + 0x50) += *(f32 *)(actor + 0x4C) * D_800BE9A4;\n    if (*(f32 *)(actor + 0x2C) < 10.0f || *(f32 *)(actor + 0x30) < 10.0f) {\n        return 0;\n    }\n    return 1;\n}\n\ns32 func_1514B034() {\n    return 0;\n}\n\ns32 func_1514B364() {\n    return 0;\n}\n\ns32 func_1514B844(u8 *arg0) {\n    u8 *temp_v0 = *(u8 **) (arg0 + 0x98);\n    s32 temp_v1 = *(s16 *) (arg0 + 0x1C);\n\n    if (temp_v1 < 0x10) {\n        s32 shifted = temp_v1 << 4;\n\n        if (shifted < *(temp_v0 + 0x1B)) {\n            *(temp_v0 + 0x1B) = shifted;\n        }\n    }\n    return 1;\n}\n\ns32 func_1514B87C(f32 *arg0) {\n    f32 delta = arg0[0x4C / 4] * D_800BE9A4;\n\n    arg0[0x2C / 4] += delta;\n    arg0[0x30 / 4] += delta;\n    return 1;\n}\n\ns32 func_1514B8B0(u8 *arg0) {\n    s32 temp_v0 = *(s16 *)(arg0 + 0x1C);\n\n    if (temp_v0 < 0x10) {\n        s32 temp_v1 = temp_v0 << 4;\n        if (temp_v1 < *(u8 *)(arg0 + 0x5C)) {\n            *(u8 *)(arg0 + 0x5C) = temp_v1;\n        }\n    }\n    return 1;\n}\n\ns32 func_1514B8E4() {\n    return 0;\n}\n\ns32 func_1514BC08() {\n    return 0;\n}\n\nvoid func_1514BE00(register u8 *arg0) {\n    func_1514BC08(arg0, arg0 + 0x110);\n}\n\ns32 func_15145128(struct17 *, struct17 *, f32 *, f32 *);\n\n/* Reposition the secondary point on a 100-unit radius around the actor. */\ns32 func_1514BE20(u8 *actor) {\n    s32 normalized;\n    struct17 target, interpolated, direction;\n    f32 length, reciprocal;\n    f32 fraction = *(f32 *)(actor + 0x15C);\n    target.unk0 = *(f32 *)(actor + 0x34);\n    target.unk4 = *(f32 *)(actor + 0x38) + 100.0f;\n    target.unk8 = *(f32 *)(actor + 0x3C);\n    interpolated.unk0 = *(f32 *)(actor + 0x40) + (target.unk0 - *(f32 *)(actor + 0x40)) * fraction;\n    interpolated.unk4 = *(f32 *)(actor + 0x44) + (target.unk4 - *(f32 *)(actor + 0x44)) * fraction;\n    interpolated.unk8 = *(f32 *)(actor + 0x48) + (target.unk8 - *(f32 *)(actor + 0x48)) * fraction;\n    direction.unk0 = interpolated.unk0 - target.unk0;\n    direction.unk4 = interpolated.unk4 - *(f32 *)(actor + 0x38);\n    direction.unk8 = interpolated.unk8 - target.unk8;\n    normalized = func_15145128(&direction, &direction, &length, &reciprocal);\n    if (normalized) {\n        *(f32 *)(actor + 0x40) = *(f32 *)(actor + 0x34) + direction.unk0 * 100.0f;\n        *(f32 *)(actor + 0x44) = *(f32 *)(actor + 0x38) + direction.unk4 * 100.0f;\n        *(f32 *)(actor + 0x48) = *(f32 *)(actor + 0x3C) + direction.unk8 * 100.0f;\n    } else {\n        *(struct17 *)(actor + 0x40) = *(struct17 *)(actor + 0x34);\n    }\n    return normalized;\n}\n\nvoid func_1514BF50(u8 *arg0) {\n    *(f32 *) (arg0 + 0x40) = *(f32 *) (arg0 + 0x34);\n    *(f32 *) (arg0 + 0x44) = *(f32 *) (arg0 + 0x38) + 100.0f;\n    *(f32 *) (arg0 + 0x48) = *(f32 *) (arg0 + 0x3C);\n}\n\nvoid func_1514BF7C(register u8 *arg0) {\n    func_1514BC08(arg0, arg0 + 0x110);\n}\n\ns32 func_1514BF9C() {\n    return 0;\n}\n\ns32 func_1514C258(s32 arg0) {\n    func_1514BF9C(arg0);\n    func_1514BE20((u8 *)arg0);\n    return 1;\n}\n\ns32 func_1514C288(s32 arg0) {\n    func_1514BF9C(arg0);\n    func_1514BF50(arg0);\n    return 1;\n}\n\ns32 func_1514C2B8(u8 *arg0) {\n    *(arg0 + 0x72) = 0;\n    *(arg0 + 0x71) = 0x24;\n    *(s16 *) (arg0 + 0x1C) = *(s16 *) (arg0 + 0x164);\n    *(u32 *) (arg0 + 0x58) |= 0x8000000;\n    *(f32 *) (arg0 + 0x154) = *(f32 *) (arg0 + 0x160);\n    return 1;\n}\n\n/* Dispatch radial samples until the selected callback stops the loop. */\nvoid func_1514C2F0(f32 x, f32 y, f32 z, f32 radius, u8 start, s8 step, s16 count, u8 selector, s32 arg8, f32 arg9, s32 arg10, u8 arg11) {\n    s16 i;\n    u8 angle = start;\n    f32 quarter;\n    f32 sample;\n    f32 pointZ;\n    RadialCallback176A00 callback;\n\n    i = 0;\n    while (i < count) {\n        quarter = func_151423D8((u8)(angle - 64));\n        sample = func_151423D8(angle);\n        pointZ = radius * sample + z;\n        callback = D_8008AA00[selector];\n        if (callback != 0) {\n            if (!callback(1, i, x + radius * quarter, y, pointZ,\n                          x, y, z, angle, start, radius, arg8, arg9, arg10, arg11)) {\n                return;\n            }\n        }\n        angle += step;\n        i++;\n    }\n}\n\ns32 func_1514C470() {\n    return 0;\n}\n\n/* Note 313: original ROM implementation, retained as assembly until C conversion. */\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_176A00/func_1514C678.s")\n\ns32 func_1514C858() {\n    return 0;\n}\n'
def payload(path):
 data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def decode(rows):return {int(k):[tuple(x)for x in v]for k,v in rows.items()}
def normalize(raw,refs):
 if len(raw)!=288 or sha(raw)!=PIN['raw_sha256'] or refs!=decode(PIN['raw_refs']):raise ValueError('Actor radial offset body or bindings changed')
 words=list(struct.unpack('>72I',raw));outwords=[];outrefs={};patches={r['index']:r for r in PIN['rows']}
 if len(patches)!=64:raise ValueError('Unexpected guard count')
 for i,word in enumerate(words):
  row=patches.get(i);current=refs.get(4*i,[])
  if row:
   expected=[tuple(x)for x in row['expected_relocations']];replacement=[tuple(x)for x in row['replacement_relocations']]
   if word!=int(row['expected'],16) or current!=expected:raise ValueError('Actor radial offset word guard changed')
   word=int(row['replacement'],16);current=replacement
  if current:outrefs[4*len(outwords)]=current
  outwords.append(word)
  if row and row['insert_after'] is not None:
   inserted=[tuple(x)for x in row['insert_after_relocations']]
   if inserted:outrefs[4*len(outwords)]=inserted
   outwords.append(int(row['insert_after'],16))
 if len(outwords)!=76 or outrefs!=decode(PIN['retail_refs']):raise ValueError('Actor radial offset output length or bindings changed')
 return struct.pack('>76I',*outwords),outrefs
def relocation_spec(rows):return ';'.join(kind+':'+name for kind,name in rows)if rows else '-'
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='generated_176A00',function=NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['expected'],replacement='0x'+d['replacement'],expected_relocations=relocation_spec(d['expected_relocations']),replacement_relocations=relocation_spec(d['replacement_relocations']),note='Normalize actor radial offset register allocation and control flow',insert_after=('0x'+d['insert_after']if d['insert_after']else ''),insert_after_relocations=(relocation_spec(d['insert_after_relocations'])if d['insert_after']else ''),omit='false')for d in PIN['rows']]
def write_csv():
 raw,refs=payload(out/'final.o');before=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode())

def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption actor radial offset input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen actor radial offset input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown actor radial offset source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed actor radial offset qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed actor radial offset result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Actor radial offset source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)




def assemble_original():
 whole=(out/'frozen/conker/asm/176A00.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;target=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';src=out/'original_1514BE20.s';src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+NAME+',.-'+NAME+'\n');obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)

def main():
 q.p=p
 frozen,installed=freeze()
 assemble_original()
 source=SELECTED;old=(out/'frozen'/SOURCE).read_bytes();nl='\r\n'if b'\r\n'in old else '\n';proposal=out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(out/'selected-source.c').write_text(source)
 compile_owner(root,out,source,'final');write_csv()
 targets,commands=q.actual_make({OWNER:proposal});obj=targets[OWNER];compact=Path(str(obj)+'.compact');before,bd=compile_owner(root,out,old.decode(),'independent-before');after,ad=compile_owner(root,out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(NAME,))==35 and same_functions(compact,after)==36 and same_functions(out/'frozen/conker/build/src/game/generated_176A00.c.o',obj,(NAME,))==35
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 def payload(o):
  data,fs,rs=parse_object(o);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 raw,refs=payload(compact);original,origrefs=payload(out/'original_1514BE20.o');fixed,freferences=payload(obj);assert (fixed,freferences)==(original,origrefs);assert sha(raw)==PIN['raw_sha256'];assert normalize(raw,refs)==(fixed,freferences)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(fixed,freferences,{nm:lookup[nm]for es in freferences.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0x1792D0:0x1792D0+304];assert struct.pack('>76I',*words)==truth
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and{name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={NAME}
 data=audit_layout(elf,root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((SOURCE,proposal),('conker/retail_word_patches.us.csv',out/'proposed-guards.csv'),('conker/build/src/game/generated_176A00.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=72,retail_words=76,guards=64,inserted_words=4,non_target_neighbors=35,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from actor radial offset workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
