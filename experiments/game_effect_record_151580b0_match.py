"""Actual-Make shadow plus independent strict complete-image audit."""
import csv,hashlib,inspect,io,json,struct
from pathlib import Path
import os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-151580B0-match'
NAME='func_151580B0';OWNER='game/generated_185560';SOURCE='conker/src/game/generated_185560.c';ENTRY=0x151580B0;ROM=0x185560;SIZE=296
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_effect_record_151580b0_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
DECLS='\ns32 func_1515D480(s32);\ns32 func_1515D440(void);\n'
BASE='s32 func_151580B0(data, entryCount, extra, alternate, bytes, mode, parameter) s32 data, entryCount, extra, bytes, parameter; u8 alternate, mode; {\n    u8 *record;\n    s32 i;\n    record = func_15167A68((u8)alternate ? 0x55 : 0x37, parameter, (s32)((u32)bytes + 0xF8u), 1, (u8)mode, 1);\n    if (record == NULL) return 0;\n    memcpy(record + 0x10, (void *)data, 0x44);\n    *(s32 *)(record + 0xD8) = entryCount;\n    *(s32 *)(record + 0xF4) = extra;\n    record[0xDC] = 0;\n    for (i = 0; i < 4; i++) *(s32 *)(record + 0xE0 + i * 4) = 0;\n    *(s32 *)(record + 0xF0) = 0;\n    if (entryCount != 0) {\n        for (i = 0; i <= D_80082FA0; i++) {\n            *(s32 *)(record + 0xE0 + i * 4) = func_1515D480(entryCount);\n        }\n        *(s32 *)(record + 0xF0) = func_1515D440();\n    }\n    return (s32)record;\n}'
def payload(path):
 text,fs,rs=parse_object(path);a,n=fs[NAME]["value"],fs[NAME]["size"];return text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def variant(old):
 text=old.replace('#include <ultra64.h>', '#include <ultra64.h>\n'+DECLS,1)
 return text.replace(body(text,NAME),'/* Allocate and initialize a copied effect record with optional entry allocations. */\n'+BASE)

"""Pin the complete raw body and normalize its closed register roles."""
import hashlib,json,struct
PIN=MANIFEST['raw_pin']
def normalize(raw,refs):
 expected={int(k):[tuple(x)for x in v]for k,v in PIN['refs'].items()}
 if len(raw)!=296 or hashlib.sha256(raw).hexdigest()!=PIN['raw_sha256']or refs!=expected:raise ValueError('Actor attachment updater raw body or bindings changed')
 ws=list(struct.unpack('>74I',raw));assert ws[0]==0x27BDFFC8
 for item in PIN['differences']:
  i=item['index'];assert not refs.get(i*4)and ws[i]==int(item['raw'],16);ws[i]=int(item['retail'],16)
 result=struct.pack('>74I',*ws);assert hashlib.sha256(result).hexdigest()==PIN['retail_unbound_sha256'];return result,dict(refs)
def rows(raw,refs):
 normal,_=normalize(raw,refs);result=[]
 for i,(a,b)in enumerate(zip(struct.unpack('>74I',raw),struct.unpack('>74I',normal))):
  if a!=b:result.append(dict(filename='generated_185560',function=p.NAME,offset='0x%X'%(4*i),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',note='Normalize effect record initialization loop scheduling',insert_after='',insert_after_relocations='',omit='false'))
 assert len(result)==2;return result

n=p
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda data:hashlib.sha256(data).hexdigest()

code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_151580B0':296}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope["strict_image"]
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_185560.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption effect-record input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen effect-record input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown effect-record source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed effect-record qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed effect-record result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Effect-record source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def main():
 q.p=p
 frozen,installed=freeze()
 source=p.variant((p.out/"frozen"/p.SOURCE).read_text());(p.out/"selected-source.c").write_text(source);old=(p.out/"frozen"/p.SOURCE).read_bytes();nl="\r\n" if b"\r\n" in old else "\n";proposal=p.out/"game-proposal.c";proposal.write_bytes(source.replace("\n",nl).encode());recipe,_=p.compile_owner(p.root,p.out,source,"recipe-input");guard0=(p.out/"frozen/conker/retail_word_patches.us.csv").read_bytes();raw,refs=p.payload(recipe);fields=next(csv.reader(io.StringIO(guard0.decode())));stream=io.StringIO(newline="");writer=csv.DictWriter(stream,fieldnames=fields,lineterminator="\r\n" if b"\r\n" in guard0 else "\n");writer.writerows(n.rows(raw,refs));(p.out/"proposed-guards.csv").write_bytes(guard0+stream.getvalue().encode())
 targets,commands=q.actual_make({p.OWNER:proposal});obj=targets[p.OWNER];compact=Path(str(obj)+".compact");before,bd=p.compile_owner(p.root,p.out,old.decode(),"independent-before");after,ad=p.compile_owner(p.root,p.out,source,"independent-selected");assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(p.NAME,))==36 and same_functions(compact,after)==37 and same_functions(p.out/"frozen/conker/build/src/game/generated_185560.c.o",obj,(p.NAME,))==36;assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)[".reginfo"]==sections(compact)[".reginfo"]
 raw,refs=p.payload(compact);normal,nrefs=n.normalize(raw,refs);assert p.payload(obj)==(normal,nrefs);lookup={v[1]:v[2][1]for v in p.symbol_rows((p.root/"conker/build/conker.us.elf").read_bytes())};lookup={name:lookup[name] for es in nrefs.values()for _,name in es};words=p.bound_blob(normal,nrefs,lookup);truth=(p.root/"conker/conker.us.bin").read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack(">74I",*words)==truth
 elf=q.link(targets);baseline=(p.out/"frozen/conker/build/conker.us.elf").read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth});oldfunc,_,oa=load_elf_functions(str(p.out/"frozen/conker/build/conker.us.elf"),"mips-linux-gnu-objdump");newfunc,_,na=load_elf_functions(str(elf),"mips-linux-gnu-objdump");assert oldfunc.keys()==newfunc.keys()and oa==na and {name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={p.NAME}
 data=audit_layout(elf,p.root/"conker");assert data["exact"] and data["different_bytes"]==0
 live_inputs(installed)
 hashes={name:sha(path.read_bytes())for name,path in ((p.SOURCE,proposal),("conker/retail_word_patches.us.csv",p.out/"proposed-guards.csv"),("conker/build/src/game/generated_185560.c.o",obj),("conker/build/conker.us.elf",elf))};assert hashes==MANIFEST["installed_hashes"] and image==MANIFEST["image"]
 r=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=74,frame=56,guards=2,non_target_neighbors=36,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/"qualification.json").write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r,indent=2),flush=True);return r
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from effect-record workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
