import os,sys,hashlib,json,struct,csv,io,inspect,subprocess
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-150C8600-match'
NAME='func_150C8600';OWNER='game/generated_F5800';SOURCE='conker/src/game/generated_F5800.c';ENTRY=0x150C8600;ROM=0xF5AB0;SIZE=304
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
MANIFEST=json.loads(Path(__file__).with_name('game_segment_binding_150c8600_manifest.json').read_text(encoding='utf-8'));FROZEN=MANIFEST['frozen'];PIN=MANIFEST['raw_pin'];p=sys.modules[__name__];n=p
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_150C8600':304}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_F5800.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
SELECTED='#include <ultra64.h>\nextern f32 D_800BE9A4;\nextern s32 D_800BE4E0;\ns32 func_150ADA20(void);\nvoid func_150CDB6C(s32 value);\n\n\n/* Restored functions and remaining placeholders for asm/F5800.s. */\n\ns32 func_150C8350() {\n    return 0;\n}\n\n/* Advance the motion table once for the primary frame layer. */\nvoid func_150C84F4(s32 view) {\n    if (view == 0) {\n        func_150C8350();\n    }\n}\n\n/* Randomize ten motion targets from the selected intensity. */\nvoid func_150C851C(s32 intensity) {\n    s32 offset;\n    s32 base;\n    u32 span;\n    s32 target;\n\n    if (D_800BE4E0 != 0) {\n        func_150CDB6C(intensity);\n        base = (intensity * 300) >> 8;\n        span = ((intensity * 50) >> 8) + 50;\n        for (offset = 0; offset != 100; offset += 10) {\n            target = base;\n            target += (u32)func_150ADA20() % span;\n            *(s16 *)(D_800BE4E0 + offset + 8) = target;\n        }\n    }\n}\n\ntypedef struct { u8 group, reserved01; s8 marker; u8 reserved03; s16 choice, previous, next; } SegmentEntry150C8600;\nextern s32 *D_80088810[2];\nu32 func_1510D0EC(s32 resource, s32 *extent, s32 mode, s32 flags);\n\n/* Emit ten segment bindings for the current group and clamped resource choice. */\nGfx *func_150C8600(Gfx *cursor) {\n    s32 *groups[2];\n    s32 index, choice, extent;\n    u32 address;\n    SegmentEntry150C8600 *entry;\n    groups[0] = D_80088810[0];\n    groups[1] = D_80088810[1];\n    for (index = 0; index < 10; index++) {\n        entry = (SegmentEntry150C8600 *)D_800BE4E0 + index;\n        choice = entry->choice >> 8;\n        if (choice < 0) choice = 0;\n        if (choice >= 5) choice = 4;\n        if (entry->group >= 2) {\n            entry->group = 0;\n            entry = (SegmentEntry150C8600 *)D_800BE4E0 + index;\n        }\n        address = func_1510D0EC(groups[entry->group][choice], &extent, 3, 0);\n        gSPSegment(cursor++, index + 1, address);\n    }\n    return cursor;\n}\n\ns32 func_150C8730() {\n    return 0;\n}\n\ns32 func_150C88D0() {\n    return 0;\n}\n\ns32 func_150C8A68() {\n    return 0;\n}\n\ns32 func_150C8DB8() {\n    return 0;\n}\n\ns32 func_150C99B4() {\n    return 0;\n}\n\ns32 func_150C9BDC() {\n    return 0;\n}\n\ns32 func_150C9DC4() {\n    return 0;\n}\n\n/* Integrate position and angles, retaining the original single-precision grouping. */\ns32 func_150CA07C(u8 *record) {\n    f32 acceleration = *(f32 *)(record + 0x5C);\n    f32 verticalVelocity = *(f32 *)(record + 0x48);\n    *(f32 *)(record + 0x38) += *(f32 *)(record + 0x44) * D_800BE9A4;\n    *(f32 *)(record + 0x3C) += verticalVelocity * D_800BE9A4\n        + acceleration * D_800BE9A4 * D_800BE9A4 * 0.5f;\n    *(f32 *)(record + 0x40) += *(f32 *)(record + 0x4C) * D_800BE9A4;\n    { f32 delta = acceleration * D_800BE9A4;\n    *(f32 *)(record + 0x48) = verticalVelocity + delta; }\n    *(f32 *)(record + 0x20) += *(f32 *)(record + 0x50) * D_800BE9A4;\n    *(f32 *)(record + 0x24) += *(f32 *)(record + 0x54) * D_800BE9A4;\n    *(f32 *)(record + 0x28) += *(f32 *)(record + 0x58) * D_800BE9A4;\n    return 1;\n}\n\ns32 func_150CA150() {\n    return 0;\n}\n\n#include "structs.h"\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid func_1514C678(f32, f32, f32, f32, s16, s16, s16, u8, s32, f32, void *, u8);\n\n/* Submit a randomized type-19 burst at the point after both RNG calls. */\nvoid func_150CA930(struct17 *point) {\n    s16 count = (u32)func_150ADA20() % 21U + 10;\n    f32 scale = func_150ADA68() * 59.0f + 170.0f;\n\n    func_1514C678(point->unk0, point->unk4, point->unk8, scale,\n        0, 255, count, 0x13, 0, 0.0f, 0, 255);\n}\n\ns32 func_150CA9D0(u8 *arg0) {\n    s32 temp_v0 = *(s16 *)(arg0 + 0x1C);\n\n    if (temp_v0 < 0x20) {\n        s32 temp_v1 = temp_v0 << 3;\n        if (temp_v1 < *(u8 *)(arg0 + 0x28)) {\n            *(u8 *)(arg0 + 0x28) = temp_v1;\n        }\n    }\n    return 1;\n}\n\ns32 func_150CAA04() {\n    return 0;\n}\n\ns32 func_150CAC28() {\n    return 0;\n}\n\ns32 func_150CADD0() {\n    return 0;\n}\n\n/* Integrate position and angles, retaining the original single-precision grouping. */\ns32 func_150CB008(u8 *record) {\n    f32 acceleration = *(f32 *)(record + 0x5C);\n    f32 verticalVelocity = *(f32 *)(record + 0x48);\n    *(f32 *)(record + 0x38) += *(f32 *)(record + 0x44) * D_800BE9A4;\n    *(f32 *)(record + 0x3C) += verticalVelocity * D_800BE9A4\n        + acceleration * D_800BE9A4 * D_800BE9A4 * 0.5f;\n    *(f32 *)(record + 0x40) += *(f32 *)(record + 0x4C) * D_800BE9A4;\n    { f32 delta = acceleration * D_800BE9A4;\n    *(f32 *)(record + 0x48) = verticalVelocity + delta; }\n    *(f32 *)(record + 0x20) += *(f32 *)(record + 0x50) * D_800BE9A4;\n    *(f32 *)(record + 0x24) += *(f32 *)(record + 0x54) * D_800BE9A4;\n    *(f32 *)(record + 0x28) += *(f32 *)(record + 0x58) * D_800BE9A4;\n    return 1;\n}\n'
def payload(path):
 data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def decode(rows):return {int(k):[tuple(x)for x in v]for k,v in rows.items()}
def normalize(raw,refs):
 if len(raw)!=300 or sha(raw)!=PIN['raw_sha256'] or refs!=decode(PIN['raw_refs']):raise ValueError('Segment binding body or bindings changed')
 words=list(struct.unpack('>75I',raw));outwords=[];outrefs={};patches={r['index']:r for r in PIN['rows']}
 if len(patches)!=45:raise ValueError('Unexpected guard count')
 for i,word in enumerate(words):
  row=patches.get(i);current=refs.get(4*i,[])
  if row:
   expected=[tuple(x)for x in row['expected_relocations']];replacement=[tuple(x)for x in row['replacement_relocations']]
   if word!=int(row['expected'],16) or current!=expected:raise ValueError('Segment binding word guard changed')
   word=int(row['replacement'],16);current=replacement
  if current:outrefs[4*len(outwords)]=current
  outwords.append(word)
  if row and row['insert_after'] is not None:
   inserted=[tuple(x)for x in row['insert_after_relocations']]
   if inserted:outrefs[4*len(outwords)]=inserted
   outwords.append(int(row['insert_after'],16))
 if len(outwords)!=76 or outrefs!=decode(PIN['retail_refs']):raise ValueError('Segment binding output length or bindings changed')
 return struct.pack('>76I',*outwords),outrefs
def relocation_spec(rows):return ';'.join(kind+':'+name for kind,name in rows)if rows else '-'
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='generated_F5800',function=NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['expected'],replacement='0x'+d['replacement'],expected_relocations=relocation_spec(d['expected_relocations']),replacement_relocations=relocation_spec(d['replacement_relocations']),note='Normalize segment binding register allocation and control flow',insert_after=('0x'+d['insert_after']if d['insert_after']else ''),insert_after_relocations=(relocation_spec(d['insert_after_relocations'])if d['insert_after']else ''),omit='false')for d in PIN['rows']]
def write_csv():
 raw,refs=payload(out/'final.o');before=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode())

def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption segment binding input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen segment binding input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown segment binding source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed segment binding qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed segment binding result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Segment binding source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)




def assemble_original():
 whole=(out/'frozen/conker/asm/F5800.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;target=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';src=out/'original_150C8600.s';src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+NAME+',.-'+NAME+'\n');obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)

def main():
 q.p=p
 frozen,installed=freeze()
 assemble_original()
 source=SELECTED;old=(out/'frozen'/SOURCE).read_bytes();nl='\r\n'if b'\r\n'in old else '\n';proposal=out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(out/'selected-source.c').write_text(source)
 compile_owner(root,out,source,'final');write_csv()
 targets,commands=q.actual_make({OWNER:proposal});obj=targets[OWNER];compact=Path(str(obj)+'.compact');before,bd=compile_owner(root,out,old.decode(),'independent-before');after,ad=compile_owner(root,out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(NAME,))==18 and same_functions(compact,after)==19 and same_functions(out/'frozen/conker/build/src/game/generated_F5800.c.o',obj,(NAME,))==18
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 def payload(o):
  data,fs,rs=parse_object(o);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 raw,refs=payload(compact);original,origrefs=payload(out/'original_150C8600.o');fixed,freferences=payload(obj);assert (fixed,freferences)==(original,origrefs);assert sha(raw)==PIN['raw_sha256'];assert normalize(raw,refs)==(fixed,freferences)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(fixed,freferences,{nm:lookup[nm]for es in freferences.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0xF5AB0:0xF5AB0+304];assert struct.pack('>76I',*words)==truth
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and{name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={NAME}
 data=audit_layout(elf,root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((SOURCE,proposal),('conker/retail_word_patches.us.csv',out/'proposed-guards.csv'),('conker/build/src/game/generated_F5800.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=75,retail_words=76,guards=45,inserted_words=1,non_target_neighbors=18,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from segment binding workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
