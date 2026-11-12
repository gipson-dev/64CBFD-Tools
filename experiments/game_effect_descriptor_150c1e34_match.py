import os,sys,hashlib,json,struct,csv,io,inspect,subprocess
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-150C1E34-match'
NAME='func_150C1E34';OWNER='game/generated_EEE70';SOURCE='conker/src/game/generated_EEE70.c';ENTRY=0x150C1E34;ROM=0xEF2E4;SIZE=300
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
MANIFEST=json.loads(Path(__file__).with_name('game_effect_descriptor_150c1e34_manifest.json').read_text(encoding='utf-8'));FROZEN=MANIFEST['frozen'];PIN=MANIFEST['raw_pin'];p=sys.modules[__name__];n=p
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_150C1E34':288}").replace('len(payload)==sizes[name]', 'len(payload)==300').replace("struct.pack_into('>I',expected,r[0]+8,len(payload))", "struct.pack_into('>I',expected,r[0]+8,sizes[name])");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_EEE70.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
SELECTED='#include <ultra64.h>\n\n/* Non-matching placeholders for the text-only asm slice asm/EEE70.s. */\n\ns32 func_150C19C0(void *arg0, u8 *arg1, u8 arg2) {\n    s32 command;\n\n    switch (arg2) {\n        case 1:\n            command = 0x18;\n            break;\n        case 2:\n            command = 0x15;\n            break;\n    }\n    func_15142314(*(s32 *) (arg1 + 0x1D4), command, arg0);\n    return 1;\n}\n\ns32 func_150C1A2C(s32 arg0, s32 arg1) {\n    return 7;\n}\n\ns32 func_150C1A40() {\n    return 0;\n}\n\ntypedef struct {\n    f32 position[3];\n    u8 retained0C[10];\n    s16 value16, value18, value1A, value1C, value1E, value20;\n    s16 value22, value24, value26;\n    u8 firstRGB[3], secondRGB[3], alpha, value2F;\n    s8 value30;\n    u8 flags;\n} EffectDescriptor150C1E34;\nextern f64 D_800A0228;\nvoid func_151429E0(u8, u8 *, u8 *, u8 *);\ns32 func_150ADA20(void);\nvoid func_1518CA80(EffectDescriptor150C1E34 *, u8);\n\ns32 func_150C1E34(s32 type, s32 index, f32 x, f32 y, f32 z,\n                  f32 previousX, f32 previousY, f32 previousZ,\n                  s32 angle, s32 originalAngle, f32 radius,\n                  s32 unused, f32 scale, s32 extra, s32 flags) {\n    EffectDescriptor150C1E34 descriptor;\n    descriptor.position[0] = x;\n    descriptor.position[1] = y;\n    descriptor.position[2] = z;\n    descriptor.value16 = (s16)scale;\n    descriptor.value18 = (s16)scale;\n    descriptor.value1A = (s16)(scale * D_800A0228);\n    descriptor.value1C = (s16)(scale * D_800A0228);\n    descriptor.value1E = (s16)((x - previousX) * 10.0f);\n    descriptor.value20 = (s16)((z - previousZ) * 10.0f);\n    descriptor.value22 = 150;\n    descriptor.value24 = 20;\n    descriptor.value26 = 600;\n    func_151429E0(0, &descriptor.firstRGB[0], &descriptor.firstRGB[1], &descriptor.firstRGB[2]);\n    func_151429E0(0, &descriptor.secondRGB[0], &descriptor.secondRGB[1], &descriptor.secondRGB[2]);\n    descriptor.alpha = 255;\n    descriptor.value2F = 255;\n    descriptor.value30 = (func_150ADA20() & 15) + 12;\n    descriptor.flags = 1;\n    func_1518CA80(&descriptor, 1);\n    return 1;\n}\n'
def payload(path):
 data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def decode(rows):return {int(k):[tuple(x)for x in v]for k,v in rows.items()}
def normalize(raw,refs):
 if len(raw)!=284 or sha(raw)!=PIN['raw_sha256'] or refs!=decode(PIN['raw_refs']):raise ValueError('Effect descriptor body or bindings changed')
 words=list(struct.unpack('>71I',raw));outwords=[];outrefs={};patches={r['index']:r for r in PIN['rows']}
 if len(patches)!=48:raise ValueError('Unexpected guard count')
 for i,word in enumerate(words):
  row=patches.get(i);current=refs.get(4*i,[])
  if row:
   expected=[tuple(x)for x in row['expected_relocations']];replacement=[tuple(x)for x in row['replacement_relocations']]
   if word!=int(row['expected'],16) or current!=expected:raise ValueError('Effect descriptor word guard changed')
   word=int(row['replacement'],16);current=replacement
  if current:outrefs[4*len(outwords)]=current
  outwords.append(word)
  if row and row['insert_after'] is not None:
   inserted=[tuple(x)for x in row['insert_after_relocations']]
   if inserted:outrefs[4*len(outwords)]=inserted
   outwords.append(int(row['insert_after'],16))
 if len(outwords)!=72 or outrefs!=decode(PIN['retail_refs']):raise ValueError('Effect descriptor output length or bindings changed')
 return struct.pack('>72I',*outwords),outrefs
def relocation_spec(rows):return ';'.join(kind+':'+name for kind,name in rows)if rows else '-'
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='generated_EEE70',function=NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['expected'],replacement='0x'+d['replacement'],expected_relocations=relocation_spec(d['expected_relocations']),replacement_relocations=relocation_spec(d['replacement_relocations']),note='Normalize effect descriptor register allocation and control flow',insert_after=('0x'+d['insert_after']if d['insert_after']else ''),insert_after_relocations=(relocation_spec(d['insert_after_relocations'])if d['insert_after']else ''),omit='false')for d in PIN['rows']]
def write_csv():
 raw,refs=payload(out/'final.o');before=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode())

def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption effect descriptor input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen effect descriptor input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown effect descriptor source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed effect descriptor qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed effect descriptor result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Effect descriptor source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)




def assemble_original():
 whole=(out/'frozen/conker/asm/EEE70.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;target=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';src=out/'original_150C1E34.s';src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+NAME+',.-'+NAME+'\n');obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)

def main():
 q.p=p
 frozen,installed=freeze()
 assemble_original()
 source=SELECTED;old=(out/'frozen'/SOURCE).read_bytes();nl='\r\n'if b'\r\n'in old else '\n';proposal=out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(out/'selected-source.c').write_text(source)
 compile_owner(root,out,source,'final');write_csv()
 targets,commands=q.actual_make({OWNER:proposal});obj=targets[OWNER];compact=Path(str(obj)+'.compact');before,bd=compile_owner(root,out,old.decode(),'independent-before');after,ad=compile_owner(root,out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(NAME,))==3 and same_functions(compact,after)==4 and same_functions(out/'frozen/conker/build/src/game/generated_EEE70.c.o',obj,(NAME,))==3
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 def payload(o):
  data,fs,rs=parse_object(o);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 raw,refs=payload(compact);original,origrefs=payload(out/'original_150C1E34.o');fixed,freferences=payload(obj);assert (fixed,freferences)==(original,origrefs);assert sha(raw)==PIN['raw_sha256'];assert normalize(raw,refs)==(fixed,freferences)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(fixed,freferences,{nm:lookup[nm]for es in freferences.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0xEF2E4:0xEF2E4+300];assert struct.pack('>72I',*words)==truth[:288]
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and{name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={NAME}
 data=audit_layout(elf,root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((SOURCE,proposal),('conker/retail_word_patches.us.csv',out/'proposed-guards.csv'),('conker/build/src/game/generated_EEE70.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=71,retail_words=72,guards=48,inserted_words=1,non_target_neighbors=3,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from effect descriptor workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
