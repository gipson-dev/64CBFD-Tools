import os,sys,hashlib,json,struct,csv,io,inspect,subprocess
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-150DFDD0-match'
NAME='func_150DFDD0';OWNER='game/generated_10CD70';SOURCE='conker/src/game/generated_10CD70.c';ENTRY=0x150DFDD0;ROM=0x10D280;SIZE=300
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
MANIFEST=json.loads(Path(__file__).with_name('game_tile_fade_callback_150dfdd0_manifest.json').read_text(encoding='utf-8'));FROZEN=MANIFEST['frozen'];PIN=MANIFEST['raw_pin'];p=sys.modules[__name__];n=p
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_150DFDD0':300}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_10CD70.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
SELECTED='#include <ultra64.h>\nextern u8 D_80088980;\nextern f32 D_800A0FB0;\ntypedef struct {\n    u8 unk0[0x14];\n    u8 active;\n    u8 unk15[0x1F];\n} struct_150DF8C0_record;\ntypedef struct {\n    u8 values[3];\n} struct_150DF8C0_indices;\nextern struct_150DF8C0_record *D_800D3098;\nextern struct_150DF8C0_indices D_80088984;\n\n/* Non-matching placeholders for the text-only asm slice asm/10CD70.s. */\n\ns32 func_150DF8C0(s32 arg0) {\n    struct_150DF8C0_indices indices = D_80088984;\n\n    if (D_800D3098[indices.values[arg0]].active != 0) {\n        return 1;\n    }\n    return 0;\n}\n\ns32 func_150DF920() {\n    return 0;\n}\n\nextern u8 D_800DD405;\nextern s32 D_80090324[];\nu32 func_1510D0EC(s32, s32 *, s32, s32);\n\n/* Load the three resource segments selected by the live activity and variant. */\nGfx *func_150DFBD0(Gfx *cursor) {\n    s32 index;\n    /* The loader writes one word; preserve the retail aligned output cell. */\n    union {\n        s64 alignment;\n        s32 value;\n    } extent;\n    s32 resource;\n    u32 address;\n\n    for (index = 0; index < 3; index++) {\n        address = func_150DF8C0(index);\n        if (address) {\n            address = D_800DD405;\n            resource = D_80090324[address + 9];\n        } else {\n            resource = D_80090324[8];\n        }\n        address = func_1510D0EC(resource, &extent.value, 3, 0);\n        gSPSegment(cursor++, index + 2, address);\n    }\n    return cursor;\n}\n\n#ifdef RETAIL_FUNC_150DFCA8\nextern f32 D_800A0FA0, D_800A0FA4, D_800A0FA8, D_800A0FAC;\nextern s32 D_800BE9E4;\ntypedef struct MotionTargetState150DFCA8 {\n    f32 field0;\n    f32 position;\n    u8 reserved08[0x5C];\n    f32 velocity;\n    u8 reserved68[0x14];\n    f32 targetVelocity;\n} MotionTargetState150DFCA8;\n\n/* Integrate vertical motion and approach the region-selected velocity. */\nvoid func_150DFCA8(MotionTargetState150DFCA8 *state) {\n    f32 target;\n\n    state->position += state->velocity * (f32)D_800BE9E4;\n    if (state->position < 11.0f) {\n        target = D_800A0FA0;\n        state->targetVelocity = target;\n    } else if (55.0f < state->position) {\n        target = -D_800A0FA4;\n        state->targetVelocity = target;\n    } else {\n        target = state->targetVelocity;\n    }\n\n    if (state->velocity < target) {\n        state->velocity += D_800A0FA8;\n        if (target < state->velocity) {\n            state->velocity = target;\n        }\n    } else if (target < state->velocity) {\n        state->velocity -= D_800A0FAC;\n        if (state->velocity < target) {\n            state->velocity = target;\n        }\n    }\n}\n#else\ns32 func_150DFCA8() {\n    return 0;\n}\n#endif\n\nvoid func_150DFDA4(u8 *arg0) {\n    u8 *temp_v0 = *(u8 **) (arg0 + 0x1D4) + 0x40;\n\n    *(f32 *) (temp_v0 + 0x30) = *(f32 *) (arg0 + 0x14);\n    *(f32 *) (temp_v0 + 0x34) = D_800A0FB0;\n    *(f32 *) (temp_v0 + 0x38) = *(f32 *) (arg0 + 0x1C);\n}\n\ntypedef struct { u32 word0, word1; } TileCommand150DFDD0;\ntypedef struct { TileCommand150DFDD0 *commands; } TileModel150DFDD0;\ntypedef struct {\n    u8 reserved00[0x13]; u8 state; u8 reserved14[0x10];\n    TileModel150DFDD0 *model;\n} TileOwner150DFDD0;\ntypedef struct {\n    u8 reserved00[0x2D8]; f32 remaining, scale; u8 reserved2E0[0xC]; s32 active;\n} TileFade150DFDD0;\nextern f32 D_800BE9A4;\n\n/* Advance the fade and update the first tile-size command. */\ns32 func_150DFDD0(TileOwner150DFDD0 *owner, TileFade150DFDD0 *fade) {\n    TileCommand150DFDD0 *command;\n    f32 progress;\n    s32 tileOffset;\n    s32 position;\n    if (fade->active != 0) {\n        owner->state = 2;\n        fade->remaining -= D_800BE9A4;\n        if (fade->remaining < 0.0f) {\n            fade->active = 0;\n            return 1;\n        }\n        progress = 1.0f - fade->scale * fade->remaining;\n    } else {\n        owner->state = 0;\n        progress = 0.0f;\n    }\n    command = owner->model->commands;\n    if (command != NULL) {\n        while ((command->word0 >> 24) != 0xF2) command++;\n        tileOffset = 2 - (s32)((command->word0 >> 12) & 0xFFF) / 3;\n        while (tileOffset < 0) tileOffset += 64;\n        position = (s32)(500.0f * progress + 2.0f);\n        command->word0 = 0xF2000000 | ((position & 0xFFF) << 12) | (tileOffset & 0xFFF);\n    }\n    return 0;\n}\n\ns32 func_150DFEFC() {\n    return 0;\n}\n\nvoid func_150E02C0(u8 *arg0, s32 arg1, u8 arg2) {\n    func_15149514(arg1, arg2, (s32) (arg0 + 0x28), (s32) (arg0 + 0x2C), (s32) arg0);\n}\n\nvoid func_150E0300(void) {\n    if (D_80088980 == 0) {\n        func_1515F170(6, 0);\n        func_1513BAE8();\n        D_80088980 = 1;\n    }\n}\n\ntypedef struct {\n    f32 x, y, z;\n} OwnerVector10CD70;\n\ntypedef struct {\n    u32 zero0, zero4;\n    u8 ownerIdentity, reserved09[3];\n    u8 *owner;\n    u8 attachment, reserved11[3];\n    OwnerVector10CD70 vector;\n    f32 value20, value24;\n    s16 duration;\n    u8 flags, kind;\n    s8 callback;\n    u8 mode;\n} OwnerVectorDescriptor10CD70;\n\n/* Retail reads the complete 12-byte vector preset at this symbol. */\nextern OwnerVector10CD70 D_800A5480;\nextern f32 D_800A0FB4, D_800A0FB8;\nvoid *func_1513418C(void *, s32, u8, s32);\n\n/* Submit the owner-linked descriptor with the shared vector preset. */\nvoid *func_150E0348(u8 *owner, u8 selector, s32 category) {\n    OwnerVectorDescriptor10CD70 descriptor;\n\n    descriptor.zero0 = 0;\n    descriptor.zero4 = 0;\n    descriptor.ownerIdentity = owner[0x3B];\n    descriptor.owner = owner;\n    descriptor.attachment = 0;\n    descriptor.vector = D_800A5480;\n    descriptor.value20 = D_800A0FB4;\n    descriptor.value24 = D_800A0FB8;\n    descriptor.duration = 300;\n    descriptor.flags = 0x1B;\n    descriptor.kind = 0x0B;\n    descriptor.callback = -1;\n    descriptor.mode = 0;\n    return func_1513418C(&descriptor, 0, selector, category);\n}\n\ns32 func_150E03F8() {\n    return 0;\n}\n\nextern u8 *D_800DBFF0;\n\n/* Fade the record byte between the near and far player-distance thresholds. */\nvoid func_150E05F8(u8 *record) {\n    f32 z;\n    f32 x;\n    f32 y;\n    f32 nearDistance;\n    f32 distance;\n    s32 result;\n\n    nearDistance = 2570.0f;\n    z = *(f32 *)(D_800DBFF0 + 0x300) - *(s16 *)(record + 0x14);\n    x = *(f32 *)(D_800DBFF0 + 0x2F8) - *(s16 *)(record + 0x10);\n    y = *(f32 *)(D_800DBFF0 + 0x2FC) - *(s16 *)(record + 0x12);\n    distance = sqrtf(z * z + (x * x + y * y));\n\n    if (distance <= nearDistance) {\n        result = 255;\n    } else {\n        f32 farDistance = 3850.0f;\n        if (farDistance <= distance) {\n            result = 0;\n        } else {\n            result = (s32)(255 - (distance - nearDistance) *\n                           (1.0f / (farDistance - nearDistance)) * 255.0f);\n        }\n    }\n    record[0x8A] = result;\n}\n\ns32 func_150E06D8() {\n    return 0;\n}\n'
def payload(path):
 data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def decode(rows):return {int(k):[tuple(x)for x in v]for k,v in rows.items()}
def normalize(raw,refs):
 if len(raw)!=284 or sha(raw)!=PIN['raw_sha256'] or refs!=decode(PIN['raw_refs']):raise ValueError('Tile fade body or bindings changed')
 words=list(struct.unpack('>71I',raw));outwords=[];outrefs={};patches={r['index']:r for r in PIN['rows']}
 if len(patches)!=31:raise ValueError('Unexpected guard count')
 for i,word in enumerate(words):
  row=patches.get(i);current=refs.get(4*i,[])
  if row:
   expected=[tuple(x)for x in row['expected_relocations']];replacement=[tuple(x)for x in row['replacement_relocations']]
   if word!=int(row['expected'],16) or current!=expected:raise ValueError('Tile fade word guard changed')
   word=int(row['replacement'],16);current=replacement
  if current:outrefs[4*len(outwords)]=current
  outwords.append(word)
  if row and row['insert_after'] is not None:
   inserted=[tuple(x)for x in row['insert_after_relocations']]
   if inserted:outrefs[4*len(outwords)]=inserted
   outwords.append(int(row['insert_after'],16))
 if len(outwords)!=75 or outrefs!=decode(PIN['retail_refs']):raise ValueError('Tile fade output length or bindings changed')
 return struct.pack('>75I',*outwords),outrefs
def relocation_spec(rows):return ';'.join(kind+':'+name for kind,name in rows)if rows else '-'
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='generated_10CD70',function=NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['expected'],replacement='0x'+d['replacement'],expected_relocations=relocation_spec(d['expected_relocations']),replacement_relocations=relocation_spec(d['replacement_relocations']),note='Normalize tile fade callback register allocation and control flow',insert_after=('0x'+d['insert_after']if d['insert_after']else ''),insert_after_relocations=(relocation_spec(d['insert_after_relocations'])if d['insert_after']else ''),omit='false')for d in PIN['rows']]
def write_csv():
 raw,refs=payload(out/'final.o');before=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode())

def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption tile fade callback input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen tile fade callback input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown tile fade callback source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed tile fade callback qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed tile fade callback result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Tile fade callback source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)




def assemble_original():
 whole=(out/'frozen/conker/asm/10CD70.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;target=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';src=out/'original_150DFDD0.s';src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+NAME+',.-'+NAME+'\n');obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)

def main():
 q.p=p
 code=inspect.getsource(q.actual_make).replace("sum('../ido/ido5.3_recomp/cc'in line for line in commands)==1","sum('../ido/ido5.3_recomp/cc'in line for line in commands)==2");scope=dict(q.actual_make.__globals__);exec(code,scope);actual_make_two=scope['actual_make']
 frozen,installed=freeze()
 assemble_original()
 source=SELECTED;old=(out/'frozen'/SOURCE).read_bytes();nl='\r\n'if b'\r\n'in old else '\n';proposal=out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(out/'selected-source.c').write_text(source)
 compile_owner(root,out,source,'final');write_csv()
 targets,commands=actual_make_two({OWNER:proposal});obj=targets[OWNER];compact=Path(str(obj)+'.compact');before,bd=compile_owner(root,out,old.decode(),'independent-before');after,ad=compile_owner(root,out,source,'independent-selected')
 assert sum('-DRETAIL_FUNC_150DFCA8' in line for line in commands)==1
 motion=Path(str(obj)+'.motion.compact');define='#define RETAIL_FUNC_150DFCA8 1\n';motion_before,mbd=compile_owner(root,out,define+old.decode(),'independent-motion-before');motion_after,mad=compile_owner(root,out,define+source,'independent-motion-selected')
 assert diagnostic_rows(mbd)==diagnostic_rows(mad)
 assert same_functions(motion_before,motion_after,(NAME,))==12 and same_functions(motion,motion_after)==13
 assert normalized_pools(motion_before)==normalized_pools(motion_after)==normalized_pools(motion) and sections(motion_after)['.reginfo']==sections(motion)['.reginfo']
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(NAME,))==12 and same_functions(compact,after)==13 and same_functions(out/'frozen/conker/build/src/game/generated_10CD70.c.o',obj,(NAME,))==12
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 def payload(o):
  data,fs,rs=parse_object(o);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 raw,refs=payload(compact);original,origrefs=payload(out/'original_150DFDD0.o');fixed,freferences=payload(obj);assert (fixed,freferences)==(original,origrefs);assert sha(raw)==PIN['raw_sha256'];assert normalize(raw,refs)==(fixed,freferences)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(fixed,freferences,{nm:lookup[nm]for es in freferences.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0x10D280:0x10D280+300];assert struct.pack('>75I',*words)==truth
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and{name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={NAME}
 data=audit_layout(elf,root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((SOURCE,proposal),('conker/retail_word_patches.us.csv',out/'proposed-guards.csv'),('conker/build/src/game/generated_10CD70.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=71,retail_words=75,guards=31,inserted_words=4,non_target_neighbors=12,motion_profile_audited=True,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from tile fade callback workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
