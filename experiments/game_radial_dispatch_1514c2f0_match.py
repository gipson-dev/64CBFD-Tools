"""Actual-Make both owners and strict image with the dependent caller audited."""
import csv,hashlib,io,json,struct,inspect
from pathlib import Path
import os,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-1514C2F0-match'
NAME='func_1514C2F0';OWNER='game/generated_176A00';SOURCE='conker/src/game/generated_176A00.c';ENTRY=0x1514C2F0;ROM=0x1797A0;SIZE=384
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_radial_dispatch_1514c2f0_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
DECLS='\ntypedef s32 (*RadialCallback176A00)(s32, s16, f32, f32, f32, f32, f32, f32, u8, u8, f32, s32, f32, s32, u8);\nextern RadialCallback176A00 D_8008AA00[];\nf32 func_151423D8(u8);\n\n'
BASE='void func_1514C2F0(f32 x, f32 y, f32 z, f32 radius, u8 start, s8 step, s16 count, u8 selector, s32 arg8, f32 arg9, s32 arg10, u8 arg11) {\n    s16 i;\n    u8 angle = start;\n    f32 quarter;\n    f32 sample;\n    f32 pointZ;\n    RadialCallback176A00 callback;\n\n    i = 0;\n    while (i < count) {\n        quarter = func_151423D8((u8)(angle - 64));\n        sample = func_151423D8(angle);\n        pointZ = radius * sample + z;\n        callback = D_8008AA00[selector];\n        if (callback != 0) {\n            if (!callback(1, i, x + radius * quarter, y, pointZ,\n                          x, y, z, angle, start, radius, arg8, arg9, arg10, arg11)) {\n                return;\n            }\n        }\n        angle += step;\n        i++;\n    }\n}'
def payload(path,name=NAME):
 text,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];return text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def variant(old):
 text=old.replace('#include "structs.h"\n','#include "structs.h"\n'+DECLS,1)
 return text.replace(body(text,NAME),'/* Dispatch radial samples until the selected callback stops the loop. */\n'+BASE)

"""Pin the complete raw body and normalize its closed register roles."""
import hashlib,json,struct
PIN=MANIFEST['raw_pin']
def normalize(raw,refs):
 expected={int(k):[tuple(x)for x in v]for k,v in PIN['refs'].items()}
 if len(raw)!=384 or hashlib.sha256(raw).hexdigest()!=PIN['raw_sha256']or refs!=expected:raise ValueError('Radial dispatcher raw body or bindings changed')
 ws=list(struct.unpack('>96I',raw));assert ws[0]==0x27BDFF60
 for item in PIN['differences']:
  i=item['index'];assert not refs.get(i*4)and ws[i]==int(item['raw'],16);ws[i]=int(item['retail'],16)
 result=struct.pack('>96I',*ws);assert hashlib.sha256(result).hexdigest()==PIN['retail_unbound_sha256'];return result,dict(refs)
def rows(raw,refs):
 normal,_=normalize(raw,refs);result=[]
 for i,(a,b)in enumerate(zip(struct.unpack('>96I',raw),struct.unpack('>96I',normal))):
  if a!=b:result.append(dict(filename='generated_176A00',function=p.NAME,offset='0x%X'%(4*i),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',note='Normalize radial callback saved-float and loop temporary register roles',insert_after='',insert_after_relocations='',omit='false'))
 assert len(result)==17;return result

n=p
from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda data:hashlib.sha256(data).hexdigest()
scope=dict(q.actual_make.__globals__);scope["p"]=p;code=inspect.getsource(q.actual_make).replace("==1\n return targets,commands","==len(sources)\n return targets,commands");exec(code,scope);actual_make=scope['actual_make']
scope2=dict(q.strict_image.__globals__);code2=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_1514C2F0':384}");exec(code2,scope2);strict_image=scope2['strict_image']
MUTABLE=(SOURCE,'conker/src/game/generated_EEB10.c','conker/retail_word_patches.us.csv','conker/build/src/game/generated_176A00.c.o','conker/build/src/game/generated_EEB10.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption radial-dispatch input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen radial-dispatch input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown radial-dispatch source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed radial-dispatch qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed radial-dispatch result incomplete: '+n)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Radial-dispatch source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)
def main():
 q.p=p
 frozen,installed=freeze()
 source=p.variant((p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8'));(p.out/'selected-source.c').write_text(source);old=(p.out/'frozen'/p.SOURCE).read_bytes();nl='\r\n'if b'\r\n'in old else'\n';proposal=p.out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());caller=p.out/'caller-proposal.c';caller_old=(p.out/'frozen/conker/src/game/generated_EEB10.c').read_text(encoding='utf-8');caller_new=caller_old.replace('s32 func_1514C2F0(f32,','void func_1514C2F0(f32,');assert caller_new!=caller_old;caller.write_text(caller_new);recipe,_=p.compile_owner(p.root,p.out,source,'recipe-input');guard0=(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();raw,refs=p.payload(recipe);fields=next(csv.reader(io.StringIO(guard0.decode())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in guard0 else'\n');writer.writerows(n.rows(raw,refs));(p.out/'proposed-guards.csv').write_bytes(guard0+stream.getvalue().encode())
 sources={p.OWNER:proposal,'game/generated_EEB10':caller};targets,commands=actual_make(sources);obj=targets[p.OWNER];compact=Path(str(obj)+'.compact');other=targets['game/generated_EEB10'];other_compact=Path(str(other)+'.compact')
 before,bd=p.compile_owner(p.root,p.out,old.decode(),'independent-before');after,ad=p.compile_owner(p.root,p.out,source,'independent-selected');assert diagnostic_rows(bd)==diagnostic_rows(ad);assert same_functions(before,after,(p.NAME,))==35 and same_functions(compact,after)==36 and same_functions(p.out/'frozen/conker/build/src/game/generated_176A00.c.o',obj,(p.NAME,))==35;assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact)and sections(after)['.reginfo']==sections(compact)['.reginfo']
 other_old=(p.out/'frozen/conker/src/game/generated_EEB10.c').read_text(encoding='utf-8');other_before,od=p.compile_owner(p.root,p.out,other_old,'caller-independent-before');other_after,nd=p.compile_owner(p.root,p.out,caller.read_text(encoding='utf-8'),'caller-independent-after');assert diagnostic_rows(od)==diagnostic_rows(nd)and same_functions(other_before,other_after)==3 and same_functions(other_compact,other_after)==3;assert normalized_pools(other_before)==normalized_pools(other_after)==normalized_pools(other_compact)and sections(other_after)['.reginfo']==sections(other_compact)['.reginfo'];before_sections=sections(p.out/'frozen/conker/build/src/game/generated_EEB10.c.o');after_sections=sections(other);assert before_sections==after_sections and (p.out/'frozen/conker/build/src/game/generated_EEB10.c.o').read_bytes()==other.read_bytes()
 raw,refs=p.payload(compact);normal,nrefs=n.normalize(raw,refs);assert p.payload(obj)==(normal,nrefs);lookup={name:int(name.split('_')[1],16)for es in nrefs.values()for _,name in es};ws=p.bound_blob(normal,nrefs,lookup);truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>96I',*ws)==truth
 elf=q.link(targets);baseline=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth});oldfunc,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and {name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes={name:sha(path.read_bytes())for name,path in ((p.SOURCE,proposal),('conker/src/game/generated_EEB10.c',caller),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game/generated_176A00.c.o',obj),('conker/build/src/game/generated_EEB10.c.o',other),('conker/build/conker.us.elf',elf))};assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 r=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=96,frame=160,guards=17,non_target_neighbors=35,caller_functions_unchanged=3,caller_all_sections_identical=len(before_sections),caller_whole_object_identical=True,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2),flush=True);return r
def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from bound radial workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
