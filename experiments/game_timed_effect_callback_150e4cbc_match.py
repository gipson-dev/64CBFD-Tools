import os,sys,hashlib,json,struct,csv,io,inspect,subprocess
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-150E4CBC-match'
NAME='func_150E4CBC';OWNER='game/generated_111670';SOURCE='conker/src/game/generated_111670.c';ENTRY=0x150E4CBC;ROM=0x11216c;SIZE=328
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
MANIFEST=json.loads(Path(__file__).with_name('game_timed_effect_callback_150e4cbc_manifest.json').read_text(encoding='utf-8'));FROZEN=MANIFEST['frozen'];PIN=MANIFEST['raw_pin'];p=sys.modules[__name__];n=p
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_150E4CBC':328}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_111670.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
SELECTED='#include <ultra64.h>\n\n/* Non-matching placeholders for the text-only asm slice asm/111670.s. */\n\n#include "structs.h"\n#include <math.h>\n\nextern struct108 *D_800DBFF0;\nextern s16 D_800D99F0[3];\n\n/* Build the offset point from truncated camera coordinates and two live angles. */\nvoid func_150E41C0(void) {\n    s32 x;\n    s32 y;\n    s32 z;\n    f32 zero;\n    f32 vertical;\n    f32 horizontal;\n    f32 sine;\n    f32 angle;\n\n    zero = 0.0f;\n    x = (s32)D_800DBFF0->unk2F8;\n    y = (s32)D_800DBFF0->unk2FC;\n    z = (s32)D_800DBFF0->unk300;\n    angle = D_800DBFF0->unk398;\n    sine = sinf(angle);\n    horizontal = cosf(angle);\n    vertical = 500.0f * sine;\n    horizontal = -500.0f * horizontal;\n    angle = D_800DBFF0->unk3A0;\n    sine = sinf(angle);\n    angle = cosf(angle);\n    x = (s32)((f32)x + (zero + horizontal * sine));\n    z = (s32)((f32)z + (horizontal * angle - zero));\n    y = (s32)((f32)y + vertical);\n    D_800D99F0[0] = x;\n    D_800D99F0[2] = z;\n    D_800D99F0[1] = y;\n}\n\ns32 func_150E42F8() {\n    return 0;\n}\n\nvoid func_150E4514(s32 arg0) {\n    func_150E41C0();\n    func_150E42F8(arg0 / 0x1E);\n}\n\ns32 func_150E4550() {\n    return 0;\n}\n\ns32 func_150E4928() {\n    return 0;\n}\n\ntypedef struct {\n    u8 retained00[0x90];\n    s32 age;\n    s16 base, strength, state;\n    u8 retained9A[8];\n    s16 amountA, amountB;\n    u8 retainedA6[0xE];\n    u8 intensity;\n} TimedEffect111670;\nextern s32 D_800BE9E4;\n\n/* Advance the effect timer and update its size and fade fields. */\nvoid func_150E4CBC(TimedEffect111670 *effect) {\n    s32 age = effect->age;\n    s32 scale, product, step;\n\n    if (age < 9) {\n        scale = (s32)((u32)age * 90U) / 9;\n        product = (s32)((u32)scale * (u32)(s32)effect->strength);\n        effect->amountB = (s32)((f32)product * (1.0f / 256.0f));\n    } else {\n        scale = 90 - (s32)((u32)age * 90U - 810U) / 600;\n        product = (s32)((u32)scale * (u32)(s32)effect->strength);\n        effect->amountB = (s32)((f32)product * (1.0f / 256.0f));\n        step = (s32)((u32)D_800BE9E4 * 17U);\n        if (step < effect->intensity) {\n            effect->intensity = (u32)effect->intensity - (u32)step;\n        } else {\n            effect->state = -1;\n        }\n        age = effect->age;\n    }\n    effect->amountA = (s32)((f32)effect->base * 14.0f) >> 8;\n    if (age >= 609) {\n        effect->state = -1;\n        age = effect->age;\n    }\n    effect->age = (s32)((u32)age + (u32)D_800BE9E4);\n}\n\ns32 func_150E4E04() {\n    return 0;\n}\n\ns32 func_150E5558() {\n    return 0;\n}\n\ns32 func_150E5810() {\n    return 0;\n}\n'
def payload(path):
 data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def decode(rows):return {int(k):[tuple(x)for x in v]for k,v in rows.items()}
def normalize(raw,refs):
 if len(raw)!=328 or sha(raw)!=PIN['raw_sha256'] or refs!=decode(PIN['raw_refs']):raise ValueError('Timed effect callback body or bindings changed')
 words=list(struct.unpack('>82I',raw));outwords=[];outrefs={};patches={r['index']:r for r in PIN['rows']}
 if len(patches)!=50:raise ValueError('Unexpected guard count')
 for i,word in enumerate(words):
  row=patches.get(i);current=refs.get(4*i,[])
  if row:
   expected=[tuple(x)for x in row['expected_relocations']];replacement=[tuple(x)for x in row['replacement_relocations']]
   if word!=int(row['expected'],16) or current!=expected:raise ValueError('Timed effect callback word guard changed')
   word=int(row['replacement'],16);current=replacement
  if current:outrefs[4*len(outwords)]=current
  outwords.append(word)
  if row and row['insert_after'] is not None:
   inserted=[tuple(x)for x in row['insert_after_relocations']]
   if inserted:outrefs[4*len(outwords)]=inserted
   outwords.append(int(row['insert_after'],16))
 if len(outwords)!=82 or outrefs!=decode(PIN['retail_refs']):raise ValueError('Timed effect callback output length or bindings changed')
 return struct.pack('>82I',*outwords),outrefs
def relocation_spec(rows):return ';'.join(kind+':'+name for kind,name in rows)if rows else '-'
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='generated_111670',function=NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['expected'],replacement='0x'+d['replacement'],expected_relocations=relocation_spec(d['expected_relocations']),replacement_relocations=relocation_spec(d['replacement_relocations']),note='Normalize timed effect callback register allocation and control flow',insert_after=('0x'+d['insert_after']if d['insert_after']else ''),insert_after_relocations=(relocation_spec(d['insert_after_relocations'])if d['insert_after']else ''),omit='false')for d in PIN['rows']]
def write_csv():
 raw,refs=payload(out/'final.o');before=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode())

def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption timed effect callback input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen timed effect callback input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown timed effect callback source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed timed effect callback qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed timed effect callback result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Timed effect callback release source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)




def assemble_original():
 whole=(out/'frozen/conker/asm/111670.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;target=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';src=out/'original_150E4CBC.s';src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+NAME+',.-'+NAME+'\n');obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)

def main():
 q.p=p
 frozen,installed=freeze()
 assemble_original()
 source=SELECTED;old=(out/'frozen'/SOURCE).read_bytes();nl='\r\n'if b'\r\n'in old else '\n';proposal=out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(out/'selected-source.c').write_text(source)
 compile_owner(root,out,source,'final');write_csv()
 targets,commands=q.actual_make({OWNER:proposal});obj=targets[OWNER];compact=Path(str(obj)+'.compact');before,bd=compile_owner(root,out,old.decode(),'independent-before');after,ad=compile_owner(root,out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(NAME,))==8 and same_functions(compact,after)==9 and same_functions(out/'frozen/conker/build/src/game/generated_111670.c.o',obj,(NAME,))==8
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 def payload(o):
  data,fs,rs=parse_object(o);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 raw,refs=payload(compact);original,origrefs=payload(out/'original_150E4CBC.o');fixed,freferences=payload(obj);assert (fixed,freferences)==(original,origrefs);assert sha(raw)==PIN['raw_sha256'];assert normalize(raw,refs)==(fixed,freferences)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(fixed,freferences,{nm:lookup[nm]for es in freferences.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0x11216c:0x11216c+328];assert struct.pack('>82I',*words)==truth
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and{name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={NAME}
 data=audit_layout(elf,root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((SOURCE,proposal),('conker/retail_word_patches.us.csv',out/'proposed-guards.csv'),('conker/build/src/game/generated_111670.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=82,retail_words=82,guards=50,inserted_words=0,non_target_neighbors=8,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from timed effect callback workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
