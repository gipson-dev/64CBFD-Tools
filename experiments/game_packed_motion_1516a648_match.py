"""Actual-Make shadow plus independent strict complete-image audit."""
import csv,hashlib,inspect,io,json,struct
from pathlib import Path
import os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-1516A648-match'
NAME='func_1516A648';OWNER='game/generated_197120';SOURCE='conker/src/game/generated_197120.c';ENTRY=0x1516A648;ROM=0x197AF8;SIZE=292
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_packed_motion_1516a648_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
DECLS='\nextern s32 D_800BE9E4;\nvoid func_1516F864(u8 *);\ns32 func_1510F8D8(s16, s16, s16, s32);\nvoid func_1516F94C(u8 *, s32);\n'
BASE='s32 func_1516A648(u8 *record) {\n    s32 alpha = record[0x1F];\n    s32 state = record[0x24];\n    s32 level;\n    if (state != 0) {\n        if (alpha != 255) {\n            alpha = (s32)((u32)alpha + ((u32)D_800BE9E4 << 4));\n            if (alpha >= 256) alpha = 255;\n            record[0x1F] = alpha;\n            state = ((volatile u8 *)record)[0x24];\n        }\n    } else {\n        if (alpha != 0) {\n            alpha = (s32)((u32)alpha - ((u32)D_800BE9E4 << 2));\n            if (alpha < 0) alpha = 0;\n            record[0x1F] = alpha;\n            state = ((volatile u8 *)record)[0x24];\n        }\n    }\n    if (state == 0 && alpha == 0) return 1;\n    *(s16 *)(record + 0x18) -= 300;\n    func_1516F864(record);\n    level = (s32)((u32)func_1510F8D8(*(s16 *)(record + 0x0E), *(s16 *)(record + 0x10), *(s16 *)(record + 0x12), 0) + 10u);\n    record[0x2C] = level >> 8;\n    record[0x2D] = level;\n    if (*(s16 *)(record + 0x10) < level) {\n        *(s16 *)(record + 0x10) = level;\n        *(s16 *)(record + 0x18) = (s32)((f32)*(s16 *)(record + 0x18) * -0.5f);\n        func_1516F94C(record, 230);\n    }\n    return 0;\n}'
def payload(path):
 text,fs,rs=parse_object(path);a,n=fs[NAME]["value"],fs[NAME]["size"];return text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def variant(old):
 text=old.replace('#include <ultra64.h>', '#include <ultra64.h>\n'+DECLS,1)
 return text.replace(body(text,NAME),'/* Advance the packed record fade, motion and contact response. */\n'+BASE)

"""Pin the complete raw body and normalize its closed register roles."""
import hashlib,json,struct
PIN=MANIFEST['raw_pin']
def normalize(raw,refs):
 expected={int(k):[tuple(x)for x in v]for k,v in PIN['refs'].items()}
 if len(raw)!=292 or hashlib.sha256(raw).hexdigest()!=PIN['raw_sha256']or refs!=expected:raise ValueError('Actor attachment updater raw body or bindings changed')
 ws=list(struct.unpack('>73I',raw));assert ws[0]==0x27BDFFE0
 for item in PIN['differences']:
  i=item['index'];assert not refs.get(i*4)and ws[i]==int(item['raw'],16);ws[i]=int(item['retail'],16)
 result=struct.pack('>73I',*ws);assert hashlib.sha256(result).hexdigest()==PIN['retail_unbound_sha256'];return result,dict(refs)
def rows(raw,refs):
 normal,_=normalize(raw,refs);result=[]
 for i,(a,b)in enumerate(zip(struct.unpack('>73I',raw),struct.unpack('>73I',normal))):
  if a!=b:result.append(dict(filename='generated_197120',function=p.NAME,offset='0x%X'%(4*i),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',note='Normalize packed-record update temporary registers',insert_after='',insert_after_relocations='',omit='false'))
 assert len(result)==6;return result

n=p
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda data:hashlib.sha256(data).hexdigest()

code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_1516A648':292}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope["strict_image"]
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_197120.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption packed-motion input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen packed-motion input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown packed-motion source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed packed-motion qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed packed-motion result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Packed-motion source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def main():
 q.p=p
 frozen,installed=freeze()
 source=p.variant((p.out/"frozen"/p.SOURCE).read_text());(p.out/"selected-source.c").write_text(source);old=(p.out/"frozen"/p.SOURCE).read_bytes();nl="\r\n" if b"\r\n" in old else "\n";proposal=p.out/"game-proposal.c";proposal.write_bytes(source.replace("\n",nl).encode());recipe,_=p.compile_owner(p.root,p.out,source,"recipe-input");guard0=(p.out/"frozen/conker/retail_word_patches.us.csv").read_bytes();raw,refs=p.payload(recipe);fields=next(csv.reader(io.StringIO(guard0.decode())));stream=io.StringIO(newline="");writer=csv.DictWriter(stream,fieldnames=fields,lineterminator="\r\n" if b"\r\n" in guard0 else "\n");writer.writerows(n.rows(raw,refs));(p.out/"proposed-guards.csv").write_bytes(guard0+stream.getvalue().encode())
 targets,commands=q.actual_make({p.OWNER:proposal});obj=targets[p.OWNER];compact=Path(str(obj)+".compact");before,bd=p.compile_owner(p.root,p.out,old.decode(),"independent-before");after,ad=p.compile_owner(p.root,p.out,source,"independent-selected");assert not bd and not ad,(bd,ad)
 assert same_functions(before,after,(p.NAME,))==3 and same_functions(compact,after)==4 and same_functions(p.out/"frozen/conker/build/src/game/generated_197120.c.o",obj,(p.NAME,))==3;assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)[".reginfo"]==sections(compact)[".reginfo"]
 raw,refs=p.payload(compact);normal,nrefs=n.normalize(raw,refs);assert p.payload(obj)==(normal,nrefs);lookup={name:int(name.split("_")[1],16)for es in nrefs.values()for _,name in es};words=p.bound_blob(normal,nrefs,lookup);truth=(p.root/"conker/conker.us.bin").read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack(">73I",*words)==truth
 elf=q.link(targets);baseline=(p.out/"frozen/conker/build/conker.us.elf").read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth});oldfunc,_,oa=load_elf_functions(str(p.out/"frozen/conker/build/conker.us.elf"),"mips-linux-gnu-objdump");newfunc,_,na=load_elf_functions(str(elf),"mips-linux-gnu-objdump");assert oldfunc.keys()==newfunc.keys()and oa==na and {name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={p.NAME}
 data=audit_layout(elf,p.root/"conker");assert data["exact"] and data["different_bytes"]==0
 live_inputs(installed)
 hashes={name:sha(path.read_bytes())for name,path in ((p.SOURCE,proposal),("conker/retail_word_patches.us.csv",p.out/"proposed-guards.csv"),("conker/build/src/game/generated_197120.c.o",obj),("conker/build/conker.us.elf",elf))};assert hashes==MANIFEST["installed_hashes"] and image==MANIFEST["image"]
 r=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=73,slot_words=74,padding_words=1,frame=32,guards=6,non_target_neighbors=3,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/"qualification.json").write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r,indent=2),flush=True);return r
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from packed-motion workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
