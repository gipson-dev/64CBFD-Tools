import os,sys,hashlib,json,struct,csv,io,inspect
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-150BF0F4-match'
NAME='func_150BF0F4';OWNER='game/generated_EC420';SOURCE='conker/src/game/generated_EC420.c';ENTRY=0x150BF0F4;ROM=0xEC5A4;SIZE=296
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_effect_state_callback_150bf0f4_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
BASE='s32 func_150BF0F4(u8 *record) {\n    s32 value = record[0x1F];\n    s32 target = record[0x26];\n    s32 phase;\n    if (record[0x24] != 0) {\n        if (value != target) {\n            value = (s32)((u32)value + (u32)D_800BE9E4 * record[0x27]);\n            if (value > target) value = target;\n            record[0x1F] = value;\n        }\n    } else if (value != 0) {\n        value = (s32)((u32)value - (u32)D_800BE9E4 * record[0x2F]);\n        if (value < 0) value = 0;\n        record[0x1F] = value;\n    }\n    if (record[0x24] == 0 && value == 0) return 1;\n    *(s16 *)(record + 0x14) = (s32)((u32)*(s16 *)(record + 0x14) + (u32)(s32)*(s8 *)(record + 0x2D) * (u32)D_800BE9E4);\n    *(s16 *)(record + 0x16) = (s32)((u32)*(s16 *)(record + 0x16) + (u32)(s32)*(s8 *)(record + 0x2E) * (u32)D_800BE9E4);\n    if (*(s16 *)(record + 0x14) <= 0) {\n        *(s16 *)(record + 0x16) = 0;\n        *(s16 *)(record + 0x14) = *(s16 *)(record + 0x16);\n        return 1;\n    }\n    phase = (s32)((u32)record[0x2C] + (u32)D_800BE9E4);\n    if (phase >= 128) phase = 127;\n    record[0x2C] = phase;\n    return 0;\n}'
SELECTED='#include <ultra64.h>\n\nextern s32 D_800BE9E4;\n\n/* Non-matching placeholders for the text-only asm slice asm/EC420.s. */\n\nvoid func_150BEF70(s32 arg0) {\n}\n\ns32 func_150BEF7C() {\n    return 0;\n}\n\n/* Advance effect intensity and two signed accumulators; return 1 when finished. */\ns32 func_150BF0F4(u8 *record) {\n    s32 value = record[0x1F];\n    s32 target = record[0x26];\n    s32 phase;\n    if (record[0x24] != 0) {\n        if (value != target) {\n            value = (s32)((u32)value + (u32)D_800BE9E4 * record[0x27]);\n            if (value > target) value = target;\n            record[0x1F] = value;\n        }\n    } else if (value != 0) {\n        value = (s32)((u32)value - (u32)D_800BE9E4 * record[0x2F]);\n        if (value < 0) value = 0;\n        record[0x1F] = value;\n    }\n    if (record[0x24] == 0 && value == 0) return 1;\n    *(s16 *)(record + 0x14) = (s32)((u32)*(s16 *)(record + 0x14) + (u32)(s32)*(s8 *)(record + 0x2D) * (u32)D_800BE9E4);\n    *(s16 *)(record + 0x16) = (s32)((u32)*(s16 *)(record + 0x16) + (u32)(s32)*(s8 *)(record + 0x2E) * (u32)D_800BE9E4);\n    if (*(s16 *)(record + 0x14) <= 0) {\n        *(s16 *)(record + 0x16) = 0;\n        *(s16 *)(record + 0x14) = *(s16 *)(record + 0x16);\n        return 1;\n    }\n    phase = (s32)((u32)record[0x2C] + (u32)D_800BE9E4);\n    if (phase >= 128) phase = 127;\n    record[0x2C] = phase;\n    return 0;\n}\n\ns32 func_150BF21C() {\n    return 0;\n}\n\ns32 func_150BF760() {\n    return 0;\n}\n\ns32 func_150BFA7C() {\n    return 0;\n}\n\ns32 func_150BFFE0() {\n    return 0;\n}\n\ns32 func_150C01DC() {\n    return 0;\n}\n\ns32 func_150C04C0() {\n    return 0;\n}\n\ns32 func_150C0648() {\n    return 0;\n}\n'
def payload(path):
 t,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return t[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def variant(old):
 assert hashlib.sha256(old.encode()).hexdigest()==FROZEN[SOURCE]
 return SELECTED

PIN=MANIFEST["raw_pin"];n=p
EXPECTED_REFS={24:[('R_MIPS_HI16','D_800BE9E4')],28:[('R_MIPS_LO16','D_800BE9E4')],88:[('R_MIPS_HI16','D_800BE9E4')],92:[('R_MIPS_LO16','D_800BE9E4')],136:[('R_MIPS_HI16','D_800BE9E4')],144:[('R_MIPS_LO16','D_800BE9E4')]}
def normalize(raw,refs):
 if len(raw)!=292 or hashlib.sha256(raw).hexdigest()!=PIN['raw_sha256'] or refs!=EXPECTED_REFS:raise ValueError('Effect callback body or bindings changed')
 words=list(struct.unpack('>73I',raw))
 for row in PIN['rows']:
  i=row['index'];assert not refs.get(4*i) and words[i]==int(row['expected'],16);words[i]=int(row['replacement'],16)
 inserted=int(next(row['insert_after']for row in PIN['rows']if row['index']==56),16)
 if inserted!=0x1C600006:raise ValueError('Retail branch insertion changed')
 words.insert(57,inserted)
 return struct.pack('>74I',*words),{k+(4 if k>=57*4 else 0):v for k,v in refs.items()}
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='generated_EC420',function=p.NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['expected'],replacement='0x'+d['replacement'],expected_relocations='-',replacement_relocations='-',note='Normalize effect callback register scheduling and restore the retail branch',insert_after=('0x'+d['insert_after']) if d['insert_after'] else '',insert_after_relocations='',omit='false')for d in PIN['rows']]
def write_csv():
 raw,refs=p.payload(p.out/'final.o');before=(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(p.out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode());print(json.dumps(dict(guards=len(PIN['rows']),inserted_branches=1,previous_bytes=len(before))))

from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_150BF0F4':296}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']

MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_EC420.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption effect-state input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen effect-state input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown effect-state source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed effect-state qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed effect-state result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Effect-state source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)


def main():
 q.p=p
 frozen,installed=freeze()
 source=variant((out/'frozen'/SOURCE).read_text());(out/'selected-source.c').write_text(source);compile_owner(root,out,source,'final');old=(p.out/'frozen'/p.SOURCE).read_bytes();nl='\r\n' if b'\r\n' in old else '\n';proposal=p.out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());n.write_csv()
 targets,commands=q.actual_make({p.OWNER:proposal});obj=targets[p.OWNER];compact=__import__('pathlib').Path(str(obj)+'.compact')
 before,bd=p.compile_owner(p.root,p.out,old.decode(),'independent-before');after,ad=p.compile_owner(p.root,p.out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(p.NAME,))==9 and same_functions(compact,after)==10 and same_functions(p.out/'frozen/conker/build/src/game/generated_EC420.c.o',obj,(p.NAME,))==9
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 raw,refs=p.payload(compact);fixed,references=n.normalize(raw,refs);assert p.payload(obj)==(fixed,references)
 lookup={v[1]:v[2][1] for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(fixed,references,{name:lookup[name] for es in references.values() for _,name in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>74I',*words)==truth
 elf=q.link(targets);baseline=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys() and oa==na and {name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact'] and data['different_bytes']==0
 live_inputs(installed)
 hashes={name:sha(f.read_bytes()) for name,f in ((p.SOURCE,proposal),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game/generated_EC420.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=73,retail_words=74,inserted_branches=1,frame=0,guards=28,non_target_neighbors=9,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from effect-state workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
