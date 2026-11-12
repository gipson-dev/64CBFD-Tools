import os,sys,hashlib,json,struct,csv,io,inspect,subprocess
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-15114B94-match'
NAME='func_15114B94';OWNER='game/generated_13D350';SOURCE='conker/src/game/generated_13D350.c';ENTRY=0x15114B94;ROM=0x142044;SIZE=304
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
MANIFEST=json.loads(Path(__file__).with_name('game_record_tail_release_15114b94_manifest.json').read_text(encoding='utf-8'));FROZEN=MANIFEST['frozen'];PIN=MANIFEST['raw_pin'];p=sys.modules[__name__];n=p
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_15114B94':304}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_13D350.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
SELECTED='#include <ultra64.h>\n\nextern u8 *D_800B0DF0;\nextern u8 D_80038080;\nextern s32 *D_800891BC[];\nextern void *D_800DBE80;\nvoid func_10004074(void *);\nvoid func_1510D694(s32);\ns32 func_15111858(void);\nvoid func_1502B7F0(void **, s32, s32, s32);\n\n\nextern s32 D_80082FA0, D_80082FA4;\ns32 func_1501A490(Gfx *, s16, s32, s32, s32, s32);\nGfx *func_1501A6CC(Gfx *, s32, s32, s32, s32);\nGfx *func_15110544(Gfx *, s32, s32, s32, s32, u8, u8, u8);\n\nextern s32 D_800BE9F0, D_800BE620, D_800BE624;\nextern u8 *D_800DBFF0;\nextern u8 D_800DBEA8[];\n\nvoid func_150A7CB0(f32 matrix[4][4], f32 x, f32 y, f32 z);\nvoid func_150A8050(f32 [4][4], f32, f32, f32);\nvoid func_150A7A48(f32 [4][4], f32 [4][4], f32 [4][4]);\ntypedef struct {\n    u8 pad0[0x24];\n    f32 top, bottom, left, right;\n    u8 pad34[0x88];\n    f32 mtx[4][4];\n    u8 padFC[0x84];\n} Record13D350;\nextern Record13D350 *D_800BE628;\nextern s32 D_800DBEF0;\nextern u8 *D_800DBEF4;\nextern s32 *D_800DBF94;\n\n/* Partially recovered text-only slice asm/13D350.s. */\n\ns32 func_1510FEA0() {\n    return 0;\n}\n\n/* Compose separate Y, X and Z rotations using one temporary matrix. */\nvoid func_151102CC(f32 matrix[4][4], f32 x, f32 y, f32 z) {\n    f32 temporary[4][4];\n\n    func_150A8050(matrix, 0.0f, y, 0.0f);\n    func_150A8050(temporary, x, 0.0f, 0.0f);\n    func_150A7A48(matrix, temporary, matrix);\n    func_150A8050(temporary, 0.0f, 0.0f, z);\n    func_150A7A48(matrix, temporary, matrix);\n}\n\nvoid func_15110360(s32 arg0, f32 arg1[4][4], f32 arg2, f32 arg3, f32 arg4) {\n    func_151102CC(arg1, arg2, arg3, arg4);\n    func_150A7A48(arg1, D_800BE628[arg0].mtx, arg1);\n}\n\n/* Fill the selected view and append the active split-screen dividers. */\nGfx *func_151103C8(Gfx *commands, f32 unusedX, f32 unusedY, f32 unusedZ) {\n    Record13D350 *view = (Record13D350 *)((u32)D_800BE628 + (u32)D_80082FA4 * 0x180);\n\n    commands = func_15110544(commands, (s32)view->left, (s32)view->top,\n        (s32)(view->right - 1.0f), (s32)view->bottom,\n        D_800DBEA8[0], D_800DBEA8[1], D_800DBEA8[2]);\n    if (D_80082FA0 != 0 && D_80082FA4 == 0) {\n        gDPPipeSync(commands++);\n        commands = (Gfx *)func_1501A490(commands, 0xFF, 0, 0, 0, 0);\n        gDPSetFillColor(commands++, 0x00010001);\n        commands = func_1501A6CC(commands, 0, (D_800BE624 >> 1) - 6,\n            D_800BE620, (D_800BE624 >> 1) + 6);\n        if (D_80082FA0 != 1) {\n            commands = func_1501A6CC(commands, (D_800BE620 >> 1) - 1, 0,\n                (D_800BE620 >> 1) + 1, D_800BE624);\n        }\n    }\n    return commands;\n}\n\nGfx *func_1501A680(Gfx *commands);\nGfx *func_1501A6CC(Gfx *commands, s32 left, s32 top, s32 right, s32 bottom);\n\n/* Append an RGBA16 fill rectangle, with the retail legacy blend-mask bits. */\nGfx *func_15110544(Gfx *commands, s32 left, s32 top, s32 right, s32 bottom,\n                    u8 red, u8 green, u8 blue) {\n    gDPPipeSync(commands++);\n    gDPSetOtherMode(commands++, G_CYC_FILL | G_TF_BILERP | G_TC_FILT | 0xF,\n        G_AC_NONE | G_ZS_PRIM | G_RM_NOOP | G_RM_NOOP2);\n    commands = func_1501A680(commands);\n    gDPSetFillColor(commands++, ((u32)GPACK_RGBA5551(red, green, blue, 1) << 16) |\n        GPACK_RGBA5551(red, green, blue, 1));\n    return func_1501A6CC(commands, left, top, right, bottom);\n}\n\n/* Fill the frame for the selected categories and qualifying child state. */\nGfx *func_15110600(Gfx *commands, f32 unusedX, f32 unusedY, f32 unusedZ) {\n    if (D_800BE9F0 == 0x1B || D_800BE9F0 == 0x1E ||\n        (D_800BE9F0 == 0x31 && (*(u8 **)(D_800DBFF0 + 0x3D4))[0x78] == 3)) {\n        commands = (Gfx *)func_15110544(commands, 2, 0,\n            (s32)((u32)D_800BE620 - 2), D_800BE624,\n            D_800DBEA8[0], D_800DBEA8[1], D_800DBEA8[2]);\n    }\n    return commands;\n}\n\ns32 func_151106A8() {\n    return 0;\n}\n\ns32 func_151108C4() {\n    return 0;\n}\n\ns32 func_15110CFC() {\n    return 0;\n}\n\n/* Process a requested mode change and optional slot cleanup. */\nvoid func_1511172C(s32 mode) {\n    s32 index;\n    if (mode == 1) {\n        D_800B0DF0[8] = 1;\n        if (D_800DBE80) { void *allocation = D_800DBE80; func_10004074(allocation); }\n        func_15111858();\n    } else if (mode != D_800B0DF0[9] && D_800B0DF0[8] == 4) {\n        if (D_80038080 != 0) {\n            for (index = 0; index < 360; index++) {\n                func_1510D694(D_800891BC[D_800B0DF0[9]][0] + index);\n            }\n        }\n        func_10004074(D_800DBE80);\n        D_800B0DF0[9] = mode;\n        func_1502B7F0(&D_800DBE80, 2, 13, D_800B0DF0[9]);\n    }\n}\n\ns32 func_15111858() {\n    return 0;\n}\n\ns32 func_15111AF4() {\n    return 0;\n}\n\ns32 func_15112520() {\n    return 0;\n}\n\ns32 func_15112A80() {\n    return 0;\n}\n\n/* Refresh bit 0x40 from each record\'s flags and attached-object state. */\nvoid func_15113180(void) {\n    s32 index = 0;\n    u32 offset = 0;\n    u8 *record;\n    u32 flags;\n\n    if (D_800DBEF0 > 0) {\n        do {\n            record = D_800DBEF4 + offset;\n            record[0x6F] &= ~0x40;\n            record = D_800DBEF4 + offset;\n            flags = record[0x6F];\n            if (((flags & 0x0F) != 0 || (record[0x70] & 4) == 4) &&\n                *(s32 *)(record + 0x38) != 0) {\n                record[0x6F] = flags | 0x40;\n            }\n            index++;\n            offset += 0xA0;\n        } while (index < D_800DBEF0);\n    }\n}\n\ns32 func_15113218() {\n    return 0;\n}\n\ns32 func_151135C4() {\n    return 0;\n}\n\ns32 func_151137D4() {\n    return 0;\n}\n\ns32 func_15113C88() {\n    return 0;\n}\n\ns32 func_15113E54() {\n    return 0;\n}\n\ns32 func_15114050(u8 *arg0, s32 arg1) {\n    if (arg0[0x4F] & 0x80) {\n        if (arg1 == -1) {\n            return 1;\n        }\n        if (D_800DBF94[(arg0 - D_800DBEF4) / 0xA0] & (1 << arg1)) {\n            return 1;\n        }\n    }\n    return 0;\n}\n\n/* Return the first set record-mask bit, or zero when disabled or empty. */\ns32 func_151140C4(u8 *record) {\n    s32 index = 0;\n    s32 mask;\n    if (record[0x4F] & 0x80) {\n        mask = D_800DBF94[(record - D_800DBEF4) / 0xA0];\n        for (; index < 32; index++) {\n            if (mask & (1U << index)) {\n                return index;\n            }\n        }\n    }\n    return 0;\n}\n\ns32 func_15114188() {\n    return 0;\n}\n\ns32 func_15114348() {\n    return 0;\n}\n\ns32 func_1511473C() {\n    return 0;\n}\n\nvoid func_151148A8(f32 arg0[4][4], f32 arg1[3]) {\n    f32 temp[4][4];\n\n    func_150A8050(arg0, 0.0f, arg1[1], 0.0f);\n    func_150A8050(temp, arg1[0], 0.0f, arg1[2]);\n    func_150A7A48(temp, arg0, arg0);\n}\n\n/* Build the actor\'s rotated, translated and scaled world matrix. */\nvoid func_1511490C(f32 matrix[4][4], u8 *actor) {\n    f32 scale[4][4];\n\n    func_151148A8(matrix, (f32 *)actor);\n    matrix[3][0] = *(s16 *)(actor + 0x10);\n    matrix[3][1] = *(f32 *)(actor + 0x18) + *(s16 *)(actor + 0x12);\n    matrix[3][2] = *(s16 *)(actor + 0x14);\n    func_150A7CB0(scale, *(f32 *)(actor + 0x2C), *(f32 *)(actor + 0x30), *(f32 *)(actor + 0x34));\n    func_150A7A48(scale, matrix, matrix);\n}\n\nu8 *func_151149AC(u8 arg0) {\n    s32 offset;\n    s32 i;\n    u8 *base;\n    u8 *record;\n\n    if (arg0 == 0) {\n        return NULL;\n    }\n\n    i = 0;\n    if (D_800DBEF0 > 0) {\n        base = D_800DBEF4;\n        offset = 0;\n        record = base;\n        do {\n            if (record[0x72] == arg0) {\n                return offset + base;\n            }\n            i++;\n            offset += 0xA0;\n            record += 0xA0;\n        } while (i < D_800DBEF0);\n    }\n    return NULL;\n}\n\ns32 func_15114A1C() {\n    return 0;\n}\n\n#include "structs.h"\nextern u32 D_800DBF98;\nvoid func_1516972C(struct102 *);\n\n/* Mark a record as released, then trim released records from the tail. */\nvoid func_15114B94(u32 index) {\n    u32 count, boundary, offset;\n    u8 *record;\n    if (index < (u32)D_800DBEF0) {\n        offset = index * 0xA0;\n        record = D_800DBEF4 + offset;\n        if (*(struct102 **)(record + 0x94) != NULL) {\n            func_1516972C(*(struct102 **)(record + 0x94));\n            *(struct102 **)(D_800DBEF4 + offset + 0x94) = NULL;\n        }\n        D_800DBEF4[offset + 0x70] |= 8;\n        D_800DBEF4[offset + 0x6E] = 1;\n    }\n    count = (u32)D_800DBEF0;\n    boundary = count - D_800DBF98;\n    while (count != 0 && (D_800DBEF4[(count - 1) * 0xA0 + 0x70] & 8)) {\n        if (count - 1 >= boundary && D_800DBF98 != 0) D_800DBF98--;\n        else boundary--;\n        D_800DBEF0 = --count;\n    }\n}\n\nextern s32 func_15114CC4();\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_13D350/func_15114CC4.s")\n\n#pragma GLOBAL_ASM("asm/nonmatchings/generated_13D350/func_15114D24.s")\n\nvoid func_15114F04(s32 arg0, s32 arg1, s32 arg2) {\n    func_1001001C(func_15114CC4, arg0, 0, arg1, arg2);\n}\n\ns32 func_15114F44() {\n    return 0;\n}\n'
def payload(path):
 data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def decode(rows):return {int(k):[tuple(x)for x in v]for k,v in rows.items()}
def normalize(raw,refs):
 if len(raw)!=304 or sha(raw)!=PIN['raw_sha256'] or refs!=decode(PIN['raw_refs']):raise ValueError('Record tail body or bindings changed')
 words=list(struct.unpack('>76I',raw));outwords=[];outrefs={};patches={r['index']:r for r in PIN['rows']}
 if len(patches)!=51:raise ValueError('Unexpected guard count')
 for i,word in enumerate(words):
  row=patches.get(i);current=refs.get(4*i,[])
  if row:
   expected=[tuple(x)for x in row['expected_relocations']];replacement=[tuple(x)for x in row['replacement_relocations']]
   if word!=int(row['expected'],16) or current!=expected:raise ValueError('Record tail word guard changed')
   word=int(row['replacement'],16);current=replacement
  if current:outrefs[4*len(outwords)]=current
  outwords.append(word)
  if row and row['insert_after'] is not None:
   inserted=[tuple(x)for x in row['insert_after_relocations']]
   if inserted:outrefs[4*len(outwords)]=inserted
   outwords.append(int(row['insert_after'],16))
 if len(outwords)!=76 or outrefs!=decode(PIN['retail_refs']):raise ValueError('Record tail output length or bindings changed')
 return struct.pack('>76I',*outwords),outrefs
def relocation_spec(rows):return ';'.join(kind+':'+name for kind,name in rows)if rows else '-'
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='generated_13D350',function=NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['expected'],replacement='0x'+d['replacement'],expected_relocations=relocation_spec(d['expected_relocations']),replacement_relocations=relocation_spec(d['replacement_relocations']),note='Normalize record tail release register allocation and control flow',insert_after=('0x'+d['insert_after']if d['insert_after']else ''),insert_after_relocations=(relocation_spec(d['insert_after_relocations'])if d['insert_after']else ''),omit='false')for d in PIN['rows']]
def write_csv():
 raw,refs=payload(out/'final.o');before=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode())

def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption record tail release input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen record tail release input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown record tail release source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed record tail release qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed record tail release result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Record tail release source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)




def assemble_original():
 whole=(out/'frozen/conker/asm/13D350.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;target=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';src=out/'original_15114B94.s';src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+NAME+',.-'+NAME+'\n');obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)

def main():
 q.p=p
 frozen,installed=freeze()
 assemble_original()
 source=SELECTED;old=(out/'frozen'/SOURCE).read_bytes();nl='\r\n'if b'\r\n'in old else '\n';proposal=out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(out/'selected-source.c').write_text(source)
 compile_owner(root,out,source,'final');write_csv()
 targets,commands=q.actual_make({OWNER:proposal});obj=targets[OWNER];compact=Path(str(obj)+'.compact');before,bd=compile_owner(root,out,old.decode(),'independent-before');after,ad=compile_owner(root,out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(NAME,))==33 and same_functions(compact,after)==34 and same_functions(out/'frozen/conker/build/src/game/generated_13D350.c.o',obj,(NAME,))==33
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 def payload(o):
  data,fs,rs=parse_object(o);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 raw,refs=payload(compact);original,origrefs=payload(out/'original_15114B94.o');fixed,freferences=payload(obj);assert (fixed,freferences)==(original,origrefs);assert sha(raw)==PIN['raw_sha256'];assert normalize(raw,refs)==(fixed,freferences)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(fixed,freferences,{nm:lookup[nm]for es in freferences.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0x142044:0x142044+304];assert struct.pack('>76I',*words)==truth
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and{name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={NAME}
 data=audit_layout(elf,root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((SOURCE,proposal),('conker/retail_word_patches.us.csv',out/'proposed-guards.csv'),('conker/build/src/game/generated_13D350.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=76,retail_words=76,guards=51,inserted_words=0,non_target_neighbors=33,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from record tail release workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
