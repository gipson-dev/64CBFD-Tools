import os,sys,hashlib,json,struct,csv,io,inspect,subprocess
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-15172B20-match'
NAME='func_15172B20';OWNER='game/generated_19F150';SOURCE='conker/src/game/generated_19F150.c';ENTRY=0x15172B20;ROM=0x19FFD0;SIZE=296
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
MANIFEST=json.loads(Path(__file__).with_name('game_quad_ground_placement_15172b20_manifest.json').read_text(encoding='utf-8'));FROZEN=MANIFEST['frozen'];PIN=MANIFEST['raw_pin'];p=sys.modules[__name__];n=p
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_15172B20':296}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_19F150.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
SELECTED='#include <ultra64.h>\n#include "structs.h"\n\n/* Animated quad records and remaining functions from asm/19F150.s. */\n\ntypedef struct {\n    u8 opaque0[0x10];\n    Vtx vertices[4];\n    s16 lifetime;\n    s16 frame;\n    s16 frameStep;\n    u16 color;\n    u8 imageIndex;\n    u8 flags;\n    u8 opaque5A[6];\n} QuadEffect19F150;\n\nvoid *func_15167A68(s32, s32, s32, s32, u8, u8);\n\n/* Allocate an animated quad and initialize its metadata and vertex flags. */\nvoid *func_15171CA0(s16 lifetime, u16 color, u8 imageIndex, s32 flags,\n                    s32 frameStep, s32 alternate, u8 slot, s32 context) {\n    QuadEffect19F150 *record;\n\n    record = func_15167A68(alternate == 0 ? 0xF : 0x43, context,\n                          sizeof(QuadEffect19F150), 1, slot, 1);\n    if (record == NULL) {\n        return NULL;\n    }\n    record->lifetime = lifetime;\n    record->frame = 0;\n    record->frameStep = frameStep;\n    record->color = color;\n    record->imageIndex = imageIndex;\n    record->flags = flags;\n    record->vertices[0].v.flag = 0;\n    record->vertices[1].v.flag = 0;\n    record->vertices[2].v.flag = 0;\n    record->vertices[3].v.flag = 0;\n    return record;\n}\n\ns32 func_15171D4C() {\n    return 0;\n}\n\nextern s32 D_800BE9E4;\nextern u8 *D_8008CA4C[];\ns32 func_151725FC(Vtx *, void *, f32, f32, f32, f32, s32, u8);\nvoid func_1516972C(struct102 *);\n\n/* Allocate an animated quad, build its vertices, and release it if geometry setup fails. */\nvoid func_15171F04(f32 x, f32 y, f32 z, void *indirectVertices,\n                   s16 lifetime, u16 color, u8 imageIndex, s32 scale,\n                   s32 flags, s32 frameStep, s32 alternate, u8 slot, s32 context) {\n    QuadEffect19F150 *record;\n\n    record = func_15171CA0(lifetime, color, imageIndex, flags,\n                          frameStep, alternate, slot, context);\n    if (record != NULL) {\n        if (func_151725FC(record->vertices, indirectVertices, x, y, z, 0.0f,\n                         scale, *(u16 *)(D_8008CA4C[record->imageIndex] + 6)) == 0) {\n            func_1516972C((struct102 *)record);\n        }\n    }\n}\n\n/* Advance an animated quad\'s lifetime and 8.8 fixed-point image frame. */\nvoid func_15171FC0(QuadEffect19F150 *record) {\n    s32 frameCount;\n\n    if (record->lifetime < -1) {\n        record->lifetime++;\n        if (record->lifetime == -1) {\n            func_1516972C((struct102 *)record);\n        }\n    } else if (record->lifetime == 0) {\n        record->lifetime = -3;\n    } else if (record->lifetime != -1) {\n        if ((record->flags & 4) == 0) {\n            if (record->lifetime > D_800BE9E4) {\n                record->lifetime = (s32)((u32)record->lifetime -\n                                         (u32)D_800BE9E4);\n            } else {\n                record->lifetime = 0;\n            }\n        }\n        record->frame += record->frameStep;\n        frameCount = D_8008CA4C[record->imageIndex][4];\n        if (record->frame / 256 >= frameCount) {\n            if (record->flags & 4) {\n                record->lifetime = -3;\n            } else {\n                record->frame = (frameCount << 8) - 256;\n            }\n        }\n    }\n}\n\ns32 func_151720C4() {\n    return 0;\n}\n\ns32 func_151725FC(Vtx *vertices, void *indirectVertices, f32 x, f32 y, f32 z,\n                   f32 rotation, s32 scale, u8 imageControl) {\n    return 0;\n}\n\nextern f32 D_800A7154, D_800A7158;\nf32 cosf(f32);\nf32 sinf(f32);\nvoid func_1510E82C(s32, s32, s32, s32, s32, s32,\n                   f32, f32, f32, f32, u16, s32);\n\n/* Place a quad at a projected ground contact, if one exists. */\ns32 func_15172B20(Vtx *vertices, f32 x, f32 y, f32 z, f32 angle,\n                  s32 radius, s32 scale, u8 imageControl) {\n    s32 hit, surface;\n    f32 height;\n    f32 radians = (angle - 90.0f) * D_800A7154;\n    f32 c = cosf(radians);\n    f32 s = sinf(radians);\n    x += (f32)radius * s;\n    z += (f32)radius * c;\n    func_1510E82C((s32)&hit, 0, (s32)&height, 0, (s32)&surface, 0,\n                  x, y, z, y, 0, 0);\n    if (hit == 0 || height == D_800A7158) return 0;\n    return func_151725FC(vertices, (void *)hit, x, height, z, angle, scale, imageControl);\n}\n'
def payload(path):
 data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def decode(rows):return {int(k):[tuple(x)for x in v]for k,v in rows.items()}
def normalize(raw,refs):
 if len(raw)!=288 or sha(raw)!=PIN['raw_sha256'] or refs!=decode(PIN['raw_refs']):raise ValueError('Quad ground placement body or bindings changed')
 words=list(struct.unpack('>72I',raw));outwords=[];outrefs={};patches={r['index']:r for r in PIN['rows']}
 if len(patches)!=11:raise ValueError('Unexpected guard count')
 for i,word in enumerate(words):
  row=patches.get(i);current=refs.get(4*i,[])
  if row:
   expected=[tuple(x)for x in row['expected_relocations']];replacement=[tuple(x)for x in row['replacement_relocations']]
   if word!=int(row['expected'],16) or current!=expected:raise ValueError('Quad ground placement word guard changed')
   word=int(row['replacement'],16);current=replacement
  if current:outrefs[4*len(outwords)]=current
  outwords.append(word)
  if row and row['insert_after'] is not None:
   inserted=[tuple(x)for x in row['insert_after_relocations']]
   if inserted:outrefs[4*len(outwords)]=inserted
   outwords.append(int(row['insert_after'],16))
 if len(outwords)!=74 or outrefs!=decode(PIN['retail_refs']):raise ValueError('Quad ground placement output length or bindings changed')
 return struct.pack('>74I',*outwords),outrefs
def relocation_spec(rows):return ';'.join(kind+':'+name for kind,name in rows)if rows else '-'
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='generated_19F150',function=NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['expected'],replacement='0x'+d['replacement'],expected_relocations=relocation_spec(d['expected_relocations']),replacement_relocations=relocation_spec(d['replacement_relocations']),note='Normalize quad placement register allocation and control flow',insert_after=('0x'+d['insert_after']if d['insert_after']else ''),insert_after_relocations=(relocation_spec(d['insert_after_relocations'])if d['insert_after']else ''),omit='false')for d in PIN['rows']]
def write_csv():
 raw,refs=payload(out/'final.o');before=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode())

def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption quad ground placement input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen quad ground placement input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown quad ground placement source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed quad ground placement qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed quad ground placement result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Quad ground placement release source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)




def assemble_original():
 whole=(out/'frozen/conker/asm/19F150.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;target=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';src=out/'original_15172B20.s';src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+NAME+',.-'+NAME+'\n');obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)

def main():
 q.p=p
 frozen,installed=freeze()
 assemble_original()
 source=SELECTED;old=(out/'frozen'/SOURCE).read_bytes();nl='\r\n'if b'\r\n'in old else '\n';proposal=out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(out/'selected-source.c').write_text(source)
 compile_owner(root,out,source,'final');write_csv()
 targets,commands=q.actual_make({OWNER:proposal});obj=targets[OWNER];compact=Path(str(obj)+'.compact');before,bd=compile_owner(root,out,old.decode(),'independent-before');after,ad=compile_owner(root,out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(NAME,))==6 and same_functions(compact,after)==7 and same_functions(out/'frozen/conker/build/src/game/generated_19F150.c.o',obj,(NAME,))==6
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 def payload(o):
  data,fs,rs=parse_object(o);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 raw,refs=payload(compact);original,origrefs=payload(out/'original_15172B20.o');fixed,freferences=payload(obj);assert (fixed,freferences)==(original,origrefs);assert sha(raw)==PIN['raw_sha256'];assert normalize(raw,refs)==(fixed,freferences)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(fixed,freferences,{nm:lookup[nm]for es in freferences.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0x19FFD0:0x19FFD0+296];assert struct.pack('>74I',*words)==truth
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and{name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={NAME}
 data=audit_layout(elf,root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((SOURCE,proposal),('conker/retail_word_patches.us.csv',out/'proposed-guards.csv'),('conker/build/src/game/generated_19F150.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=72,retail_words=74,guards=11,inserted_words=2,non_target_neighbors=6,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from quad ground placement workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
