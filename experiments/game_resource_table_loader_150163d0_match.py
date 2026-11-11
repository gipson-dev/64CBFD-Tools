import os,sys,hashlib,json,struct,csv,io,inspect,subprocess
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-150163D0-match'
NAME='func_150163D0';OWNER='game/generated_43880';SOURCE='conker/src/game/generated_43880.c';ENTRY=0x150163D0;ROM=0x43880;SIZE=300
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
MANIFEST=json.loads(Path(__file__).with_name('game_resource_table_loader_150163d0_manifest.json').read_text(encoding='utf-8'));FROZEN=MANIFEST['frozen'];PIN=MANIFEST['raw_pin'];p=sys.modules[__name__];n=p
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_150163D0':300}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_43880.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
SELECTED='#include <ultra64.h>\n\n/* Resource table loader recovered from the text-only asm slice asm/43880.s. */\n\nextern u32 *D_800D18B0;\nu32 func_1502B7F0(void **output, u32 depth, ...);\n\n/* Load the zero-terminated offset table and relocate each entry in place. */\nvoid func_150163D0(u32 resource) {\n    s32 count, i;\n    u32 *cursor;\n    if ((s32)func_1502B7F0((void **)&D_800D18B0, 3, 12, resource, 9) > 0) {\n        count = 0;\n        cursor = D_800D18B0;\n        if (*cursor != 0) {\n            do { count++; cursor += 2; } while (*cursor != 0);\n        }\n        for (i = 0; i < count; i++) {\n            D_800D18B0[i * 2] += (u32)D_800D18B0;\n        }\n    } else {\n        D_800D18B0 = NULL;\n    }\n}\n'
def payload(path):
 data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def decode(rows):return {int(k):[tuple(x)for x in v]for k,v in rows.items()}
def normalize(raw,refs):
 if len(raw)!=300 or hashlib.sha256(raw).hexdigest()!=PIN['raw_sha256'] or refs!=decode(PIN['raw_refs']):raise ValueError('Resource table loader body or bindings changed')
 words=list(struct.unpack('>75I',raw));outrefs={k:list(v)for k,v in refs.items()}
 for row in PIN['rows']:
  i=row['index'];expected=[tuple(x)for x in row['expected_relocations']];replacement=[tuple(x)for x in row['replacement_relocations']]
  if words[i]!=int(row['expected'],16)or outrefs.get(4*i,[])!=expected:raise ValueError('Resource table loader word guard changed')
  words[i]=int(row['replacement'],16)
  if replacement:outrefs[4*i]=replacement
  else:outrefs.pop(4*i,None)
 if outrefs!=decode(PIN['retail_refs']):raise ValueError('Resource table loader replacement bindings changed')
 return struct.pack('>75I',*words),outrefs
def relocation_spec(rows):return ';'.join(kind+':'+name for kind,name in rows)if rows else '-'
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='generated_43880',function=p.NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['expected'],replacement='0x'+d['replacement'],expected_relocations=relocation_spec(d['expected_relocations']),replacement_relocations=relocation_spec(d['replacement_relocations']),note='Normalize resource table loader control flow and register allocation',insert_after='',insert_after_relocations='',omit='false')for d in PIN['rows']]
def write_csv():
 raw,refs=p.payload(p.out/'final.o');before=(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(p.out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode());print(json.dumps(dict(guards=len(PIN['rows']),relocation_changes=0,previous_bytes=len(before))))


def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption resource table loader input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen resource table loader input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown resource table loader source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed resource table loader qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed resource table loader result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Resource table loader source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)



def assemble_original():
 whole=(out/'frozen/conker/asm/43880.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;target=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';src=out/'original_150163D0.s';src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+NAME+',.-'+NAME+'\n');obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)

def main():
 q.p=p
 frozen,installed=freeze()
 assemble_original()
 source=SELECTED;old=(out/'frozen'/SOURCE).read_bytes();nl='\r\n' if b'\r\n'in old else '\n';proposal=out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(out/'selected-source.c').write_text(source)
 compile_owner(root,out,source,'final');write_csv()
 targets,commands=q.actual_make({OWNER:proposal});obj=targets[OWNER];compact=Path(str(obj)+'.compact');before,bd=compile_owner(root,out,old.decode(),'independent-before');after,ad=compile_owner(root,out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(NAME,))==0 and same_functions(compact,after)==1 and same_functions(out/'frozen/conker/build/src/game/generated_43880.c.o',obj,(NAME,))==0
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 def payload(o):
  data,fs,rs=parse_object(o);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 raw,refs=payload(compact);original,origrefs=payload(out/'original_150163D0.o');fixed,freferences=payload(obj);assert (fixed,freferences)==(original,origrefs);assert sha(raw)==PIN['raw_sha256']
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(fixed,refs,{nm:lookup.get(nm,int(nm[2:],16)if nm.startswith('D_')else 0)for es in refs.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0x43880:0x43880+300];assert struct.pack('>75I',*words)==truth
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys() and oa==na and {name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={NAME}
 data=audit_layout(elf,root/'conker');assert data['exact'] and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((SOURCE,proposal),('conker/retail_word_patches.us.csv',out/'proposed-guards.csv'),('conker/build/src/game/generated_43880.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=75,slot_words=76,guards=52,non_target_neighbors=0,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from resource-loader workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
