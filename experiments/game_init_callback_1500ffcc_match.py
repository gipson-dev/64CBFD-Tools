"""Actual-Make shadow and strict complete-image audit for the callback."""
import csv,hashlib,inspect,io,json,struct
from pathlib import Path
import os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-1500FFCC-match'
NAME='func_1500FFCC';OWNER='game/generated_3D2E0';SOURCE='conker/src/game/generated_3D2E0.c';ENTRY=0x1500FFCC;ROM=0x3D47C;SIZE=316
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_init_callback_1500ffcc_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
DECLS='\nextern s32 D_800B0E00,D_800B0E04,D_800902DC;\nextern u8 *D_80088870;\nvoid *func_15195AA8(s32,s32,s32,s32,s32,s32,s32,s32);\nu8 *func_151491F4(s32,s32,s32,s32,s32,s32,s32,s32);\nu8 *func_15149130(s32,s32,s32,s32,s32,s32,s32,s32,s32);\n'
BASE='void func_1500FFCC(void) {\n    f32 first;\n    f32 pair[3];\n    u8 *record;\n    func_15195AA8(D_800B0E00, D_800902DC, 1, -1, 0, 0, 0, -4);\n    func_15195AA8(D_800B0E04, D_800902DC, 1, -1, 0, 1, 0, -4);\n    func_1500FE30();\n    func_1500FF9C();\n    first = 0.0f;\n    record = func_151491F4(300, -1, 18, 0, 14, 4, 255, 0);\n    if (record != 0) memcpy(record + 0x28, &first, 4);\n    pair[0] = 0.0f;\n    pair[1] = 0.0f;\n    D_80088870 = func_15149130(300, -1, 23, -1, 0, 20, 8, 255, 1);\n    if (D_80088870 != 0) memcpy(D_80088870 + 0x28, pair, 8);\n}'
def payload(path):
 text,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return text[a:a+n],{i-a:v for i,v in rs.items() if a<=i<a+n}

def variant(old):
 text=old.replace('#include <ultra64.h>','#include <ultra64.h>\n'+DECLS,1)
 return text.replace(body(text,NAME),'/* Initialize callback state and create two optional records. */\n'+BASE)

"""Pin and normalize the 15-word call-preparation schedule."""
import hashlib,json,struct
PIN=MANIFEST['raw_pin']
def normalize(raw,refs):
 expected={int(k):[tuple(x) for x in v] for k,v in PIN['refs'].items()}
 if len(raw)!=316 or hashlib.sha256(raw).hexdigest()!=PIN['raw_sha256'] or refs!=expected:raise ValueError('Initialization body or bindings changed')
 words=list(struct.unpack('>79I',raw))
 for row in PIN['differences']:
  i=row['index'];assert not refs.get(4*i) and words[i]==int(row['raw'],16);words[i]=int(row['retail'],16)
 result=struct.pack('>79I',*words);assert hashlib.sha256(result).hexdigest()==PIN['retail_unbound_sha256']
 return result,dict(refs)
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='generated_3D2E0',function=p.NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['raw'],replacement='0x'+d['retail'],expected_relocations='-',replacement_relocations='-',note='Normalize independent initialization and call-argument scheduling',insert_after='',insert_after_relocations='',omit='false') for d in PIN['differences']]

n=p
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda data:hashlib.sha256(data).hexdigest()

code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_1500FFCC':316}")
scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_3D2E0.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption init-callback input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen init-callback input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown init-callback source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed init-callback qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed init-callback result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Init-callback source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def main():
 q.p=p
 frozen,installed=freeze()
 source=variant((p.out/'frozen'/p.SOURCE).read_text());(p.out/'selected-source.c').write_text(source)
 old=(p.out/'frozen'/p.SOURCE).read_bytes();nl='\r\n' if b'\r\n' in old else '\n';proposal=p.out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode())
 recipe,_=p.compile_owner(p.root,p.out,source,'recipe-input');guard0=(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();raw,refs=p.payload(recipe)
 fields=next(csv.reader(io.StringIO(guard0.decode())));stream=io.StringIO(newline='')
 writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in guard0 else '\n');writer.writerows(n.rows(raw,refs))
 (p.out/'proposed-guards.csv').write_bytes(guard0+stream.getvalue().encode())
 targets,commands=q.actual_make({p.OWNER:proposal});obj=targets[p.OWNER];compact=Path(str(obj)+'.compact')
 before,bd=p.compile_owner(p.root,p.out,old.decode(),'independent-before');after,ad=p.compile_owner(p.root,p.out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(p.NAME,))==2 and same_functions(compact,after)==3 and same_functions(p.out/'frozen/conker/build/src/game/generated_3D2E0.c.o',obj,(p.NAME,))==2
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 raw,refs=p.payload(compact);normal,nrefs=n.normalize(raw,refs);assert p.payload(obj)==(normal,nrefs)
 lookup={v[1]:v[2][1] for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())}
 words=p.bound_blob(normal,nrefs,{name:lookup[name] for es in nrefs.values() for _,name in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>79I',*words)==truth
 elf=q.link(targets);baseline=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
 assert oldfunc.keys()==newfunc.keys() and oa==na and {name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact'] and data['different_bytes']==0
 live_inputs(installed)
 hashes={name:sha(path.read_bytes()) for name,path in ((p.SOURCE,proposal),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game/generated_3D2E0.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 r=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=79,alignment_words=2,frame=72,guards=15,non_target_neighbors=2,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True);return r
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError('Consumer differs from init-callback workspace')
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=='__main__':prepare()
