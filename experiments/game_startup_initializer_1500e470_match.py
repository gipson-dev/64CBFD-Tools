import os,sys,hashlib,json,struct,csv,io,inspect
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-1500E470-match'
NAME='func_1500E470';OWNER='game_3B920';SOURCE='conker/src/game_3B920.c';ENTRY=0x1500E470;ROM=0x3B920;SIZE=336
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_startup_initializer_1500e470_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
BASE='void func_1500E470(s32 arg0) {\n    u8 tmp;\n    D_800DD190 = -1;\n    bzero(&D_800DD198, 24);\n    D_800DD404 = 0xFF;\n    D_800DD405 = 0;\n    D_800DD406 = 0;\n    D_800E0930 = 0;\n    D_800E0934 = 0;\n    D_800E0940 = 0;\n    D_8008CD00 = 0;\n    D_80088B60 = 0;\n    D_800BE4E0 = 0;\n    { u8 value = func_15012720(); D_800E0A10 = value; }\n    func_15012370();\n\n    func_151EF640(64);\n    func_151732E0(arg0);\n    func_15004FE0(arg0);\n    func_150127B0();\n\n    func_1519582C();\n    func_15008BE0();\n    func_15008B90();\n    func_1500E5C0();\n\n    if (D_800B0DF0->unkA) {\n        D_80082D90[D_800B0DF0->unkA]();\n    }\n    func_1500ABA0(arg0);\n    func_1500BEC0();\n    func_1500AC14();\n    func_151872B0(arg0);\n    func_15178EB0();\n    func_15012FE0();\n\n    tmp = (D_800D2E4C->unk4 & 128) == 0;\n    func_151645C4(tmp);\n}'
def payload(path):
 text,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return text[a:a+n],{i-a:v for i,v in rs.items() if a<=i<a+n}

def variant(old):
 source=old.replace('s32 func_1500E470();','void func_1500E470(s32);',1)
 source=source.replace(body(source,NAME),BASE)
 source=source[:source.index('// NON-MATCHING: damn nops')]
 return source.replace('/* Non-matching C placeholders for asm/nonmatchings/game_3B920/func_1500E470.s. */','/* Reset startup state and initialize the active game systems. */',1)

PIN=MANIFEST["raw_pin"];n=p
def normalize(raw,refs):
 expected={int(k):[tuple(x) for x in v] for k,v in PIN['refs'].items()}
 if len(raw)!=336 or hashlib.sha256(raw).hexdigest()!=PIN['sha256'] or refs!=expected:raise ValueError('Startup body or bindings changed')
 words=list(struct.unpack('>84I',raw))
 for row in PIN['differences']:
  i=row['index'];assert not refs.get(4*i) and words[i]==int(row['raw'],16);words[i]=int(row['retail'],16)
 return struct.pack('>84I',*words),dict(refs)
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='game_3B920',function=p.NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['raw'],replacement='0x'+d['retail'],expected_relocations='-',replacement_relocations='-',note='Normalize two closed startup temporary-register cycles',insert_after='',insert_after_relocations='',omit='false') for d in PIN['differences']]
def write_csv():
 raw,refs=p.payload(p.out/'final.o');before=(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(p.out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode());print(json.dumps(dict(guards=5,previous_bytes=len(before))))

from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_1500E470':336}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']

MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game_3B920.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption startup-initializer input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen startup-initializer input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown startup-initializer source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed startup-initializer qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed startup-initializer result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Startup-initializer source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)


def main():
 q.p=p
 frozen,installed=freeze()
 source=variant((out/'frozen'/SOURCE).read_text());(out/'selected-source.c').write_text(source);compile_owner(root,out,source,'final');old=(p.out/'frozen'/p.SOURCE).read_bytes();nl='\r\n' if b'\r\n' in old else '\n';proposal=p.out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());n.write_csv()
 targets,commands=q.actual_make({p.OWNER:proposal});obj=targets[p.OWNER];compact=__import__('pathlib').Path(str(obj)+'.compact')
 before,bd=p.compile_owner(p.root,p.out,old.decode(),'independent-before');after,ad=p.compile_owner(p.root,p.out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(p.NAME,))==0 and same_functions(compact,after)==1 and same_functions(p.out/'frozen/conker/build/src/game_3B920.c.o',obj,(p.NAME,))==0
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 raw,refs=p.payload(compact);fixed,references=n.normalize(raw,refs);assert p.payload(obj)==(fixed,references)
 lookup={v[1]:v[2][1] for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(fixed,references,{name:lookup[name] for es in references.values() for _,name in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>84I',*words)==truth
 elf=q.link(targets);baseline=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys() and oa==na and {name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact'] and data['different_bytes']==0
 live_inputs(installed)
 hashes={name:sha(f.read_bytes()) for name,f in ((p.SOURCE,proposal),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game_3B920.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=84,frame=24,guards=5,non_target_neighbors=0,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from startup-initializer workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
