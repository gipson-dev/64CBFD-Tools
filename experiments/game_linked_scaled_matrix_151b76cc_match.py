import os,sys,hashlib,json,struct,csv,io,inspect,subprocess
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-151B76CC-match'
NAME='func_151B76CC';OWNER='game/generated_1E37D0';SOURCE='conker/src/game/generated_1E37D0.c';ENTRY=0x151B76CC;ROM=0x1E4B7C;SIZE=296
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
MANIFEST=json.loads(Path(__file__).with_name('game_linked_scaled_matrix_151b76cc_manifest.json').read_text(encoding='utf-8'));FROZEN=MANIFEST['frozen'];PIN=MANIFEST['raw_pin'];p=sys.modules[__name__];n=p
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_151B76CC':296}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']
MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game/generated_1E37D0.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
SELECTED='#include <ultra64.h>\ntypedef struct {\n    f32 x;\n    f32 y;\n    f32 z;\n} ActorPosition151B6320;\n\ntypedef struct {\n    ActorPosition151B6320 position;\n    s16 duration;\n    u16 flags;\n    s32 kind;\n    u8 reserved14; /* Preserved stack byte copied by the retail helper. */\n    u8 count;\n    u8 reserved16[2]; /* Preserved stack bytes copied by the retail helper. */\n} ActorEffectRequest151B6320;\n\ntypedef struct {\n    u8 *owner;\n    u8 identity;\n    u8 reserved05[3];\n    ActorPosition151B6320 position;\n    f32 velocityX;\n    f32 velocityY;\n    f32 lowerBound;\n    f32 upperBound;\n    f32 velocityZ;\n    u32 reserved28; /* Retail copies this untouched stack word. */\n} ActorEffectPayload151B6320;\n\ntypedef struct {\n    ActorEffectPayload151B6320 payload;\n    u32 layoutGap; /* Original local spacing; not part of either packet. */\n    ActorEffectRequest151B6320 request;\n    u32 layoutTail; /* Preserves the original 0x90-byte frame. */\n} ActorEffectLocals151B6320;\n\nu8 *func_15147A80(void *, s32, s32, s32, s32, s32, s32, s32,\n    void *, u8, s32);\nvoid *memcpy(void *, const void *, unsigned int);\n\nextern void (*D_8008FB98[])(u8 *, s32, u8);\n\n/* Non-matching placeholders for the text-only asm slice asm/1E37D0.s. */\n\n/* Snapshot one actor position and submit its retail effect packet. */\nvoid func_151B6320(u8 *actor, u8 channel, s32 context) {\n    ActorEffectLocals151B6320 locals;\n    u8 *record;\n\n    locals.request.count = 10;\n    locals.request.position.x = *(f32 *)(actor + 0x14);\n    locals.request.position.y = *(f32 *)(actor + 0x18);\n    locals.request.position.z = *(f32 *)(actor + 0x1C);\n    locals.request.duration = 300;\n    locals.request.flags = 6;\n    locals.payload.owner = actor;\n    locals.payload.identity = actor[0x3B];\n    locals.payload.position = locals.request.position;\n    locals.payload.velocityX = 0.0f;\n    locals.payload.velocityY = 0.0f;\n    locals.payload.upperBound = -16384.0f;\n    locals.payload.lowerBound = -16384.0f;\n    locals.payload.velocityZ = 0.0f;\n    locals.request.kind = 13;\n    record = func_15147A80(&locals.request, 0x30, 0x1C, 0xB, 0xB, 0xB,\n        0, 0, NULL, channel, context);\n    if (record != NULL) {\n        memcpy(*(void **)(record + 0x98), &locals.payload, 0x2C);\n    }\n}\n\ns32 func_151B6420() {\n    return 0;\n}\n\ns32 func_151B65D4() {\n    return 0;\n}\n\ns32 func_151B6928() {\n    return 0;\n}\n\n// Matched with guarded event/current register and return scheduling.\nvoid func_151B70B4(u8 *arg0, u8 *arg1, u8 arg2) {\n    u8 *link;\n    u8 *current;\n    u8 *first;\n    u8 event;\n\n    link = *(u8 **)(arg0 + 0x98);\n    event = arg2;\n    current = *(u8 **)link;\n\n    if (arg2 == 0) {\n        if (*(u8 **)arg1 != current) {\n            return;\n        }\n        arg0[0x30] = 0;\n        *(u16 *)(arg0 + 0x1E) |= 8;\n        return;\n    }\n\n    if (event == 0x2D) {\n        first = *(u8 **)arg1;\n        if (first == current) {\n            *(u8 **)link = *(u8 **)(arg1 + 4);\n            link[4] = arg1[9];\n            return;\n        }\n        if (*(u8 **)(arg1 + 4) == current) {\n            *(u8 **)link = first;\n            link[4] = arg1[8];\n        }\n    }\n}\n\ns32 func_151B7144() {\n    return 0;\n}\n\ns32 func_151B7328() {\n    return 0;\n}\n\ns32 func_151B7678(u8 *arg0, f32 *arg1) {\n    u8 *container = *(u8 **)(arg0 + 0x98);\n    u8 *entry = *(u8 **)(container + 4);\n    u8 *record = *(u8 **)entry;\n\n    if (*(s32 *)record == 0 || entry[4] != record[0x3B]) {\n        return 0;\n    }\n    arg1[0] = *(f32 *)(record + 0x14);\n    arg1[1] = *(f32 *)(record + 0x18);\n    arg1[2] = *(f32 *)(record + 0x1C);\n    return 1;\n}\n\ntypedef struct { u8 reserved00[0x18]; f32 scaleX, scaleY; f32 rotation[3]; u8 reserved2C[0xC]; f32 translation[3]; } MatrixSource151B76CC;\ntypedef struct { MatrixSource151B76CC *source; } MatrixLink151B76CC;\ntypedef struct { u8 reserved00[4]; MatrixLink151B76CC *link; } MatrixData151B76CC;\ntypedef struct { u8 reserved00[0x10]; ActorPosition151B6320 position; u8 reserved1C[0x7C]; MatrixData151B76CC *data; } MatrixOwner151B76CC;\nvoid func_150A8050(f32 [4][4], f32, f32, f32);\nvoid func_150A7960(f32 [4][4], f32, f32, f32, f32 *, f32 *, f32 *);\n/* Transform a local offset through the linked scaled rotation and translation. */\ns32 func_151B76CC(MatrixOwner151B76CC *owner, ActorPosition151B6320 *output) {\n    f32 matrix[4][4];\n    MatrixSource151B76CC *source = owner->data->link->source;\n    func_150A8050(matrix, source->rotation[0], source->rotation[1], source->rotation[2]);\n    matrix[3][0] = source->translation[0];\n    matrix[3][1] = source->translation[1];\n    matrix[3][2] = source->translation[2];\n    matrix[0][0] *= source->scaleX; matrix[0][1] *= source->scaleX; matrix[0][2] *= source->scaleX;\n    matrix[1][0] *= source->scaleY; matrix[1][1] *= source->scaleY; matrix[1][2] *= source->scaleY;\n    matrix[2][0] *= source->scaleX; matrix[2][1] *= source->scaleX; matrix[2][2] *= source->scaleX;\n    func_150A7960(matrix, 0.0f, 0.0f, -250.0f, &output->x, &output->y, &output->z);\n    return 1;\n}\n\ns32 func_151B77F4() {\n    return 0;\n}\n\ns32 func_151B7998() {\n    return 0;\n}\n\ns32 func_151B7C38() {\n    return 0;\n}\n\nvoid func_151B82CC(u8 *arg0, s32 arg1, u8 arg2) {\n    u8 *temp_v0 = *(u8 **) (arg0 + 0x98);\n    void (*temp_v1)(u8 *, s32, u8) =\n        D_8008FB98[*(temp_v0 + 8)];\n\n    if (temp_v1 != 0) {\n        temp_v1(arg0, arg1, arg2);\n    }\n}\n\nvoid func_151B8318(u8 *arg0, u8 *arg1, u8 arg2) {\n    u8 *container = *(u8 **)(arg0 + 0x98);\n    u8 *entry = *(u8 **)(container + 4);\n\n    if (arg2 == 0) {\n        s32 value = *(s32 *)arg1;\n\n        if (value == *(s32 *)entry || entry[4] == arg1[4]) {\n            func_1516972C(arg0);\n        }\n    }\n}\n\nvoid func_151B8370(arg0, arg1)\nu8 *arg0;\ns32 arg1;\n{\n    u8 *temp_v0 = *(u8 **) (arg0 + 0x98);\n\n    arg1 = *(s32 *) temp_v0;\n    if (arg1 != 0) {\n        func_1516972C(arg1);\n    }\n}\n\ns32 func_151B83A0(s32 arg0) {\n    func_151B8370(arg0);\n    func_151478F4(arg0);\n}\n\ns32 func_151B83CC(s32 arg0) {\n    func_151B8370(arg0);\n    func_15147928(arg0);\n}\n'
def payload(path):
 data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}

def decode(rows):return {int(k):[tuple(x)for x in v]for k,v in rows.items()}
def normalize(raw,refs):
 if len(raw)!=296 or sha(raw)!=PIN['raw_sha256'] or refs!=decode(PIN['raw_refs']):raise ValueError('Linked matrix body or bindings changed')
 words=list(struct.unpack('>74I',raw));outwords=[];outrefs={};patches={r['index']:r for r in PIN['rows']}
 if len(patches)!=38:raise ValueError('Unexpected guard count')
 for i,word in enumerate(words):
  row=patches.get(i);current=refs.get(4*i,[])
  if row:
   expected=[tuple(x)for x in row['expected_relocations']];replacement=[tuple(x)for x in row['replacement_relocations']]
   if word!=int(row['expected'],16) or current!=expected:raise ValueError('Linked matrix word guard changed')
   word=int(row['replacement'],16);current=replacement
  if current:outrefs[4*len(outwords)]=current
  outwords.append(word)
  if row and row['insert_after'] is not None:
   inserted=[tuple(x)for x in row['insert_after_relocations']]
   if inserted:outrefs[4*len(outwords)]=inserted
   outwords.append(int(row['insert_after'],16))
 if len(outwords)!=74 or outrefs!=decode(PIN['retail_refs']):raise ValueError('Linked matrix output length or bindings changed')
 return struct.pack('>74I',*outwords),outrefs
def relocation_spec(rows):return ';'.join(kind+':'+name for kind,name in rows)if rows else '-'
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='generated_1E37D0',function=NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['expected'],replacement='0x'+d['replacement'],expected_relocations=relocation_spec(d['expected_relocations']),replacement_relocations=relocation_spec(d['replacement_relocations']),note='Normalize linked scaled-matrix transform register allocation and control flow',insert_after=('0x'+d['insert_after']if d['insert_after']else ''),insert_after_relocations=(relocation_spec(d['insert_after_relocations'])if d['insert_after']else ''),omit='false')for d in PIN['rows']]
def write_csv():
 raw,refs=payload(out/'final.o');before=(out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode())

def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption linked scaled-matrix transform input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen linked scaled-matrix transform input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown linked scaled-matrix transform source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed linked scaled-matrix transform qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed linked scaled-matrix transform result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Linked scaled-matrix transform source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)




def assemble_original():
 whole=(out/'frozen/conker/asm/1E37D0.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;target=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';src=out/'original_151B76CC.s';src.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+NAME+',.-'+NAME+'\n');obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)

def main():
 q.p=p
 frozen,installed=freeze()
 assemble_original()
 source=SELECTED;old=(out/'frozen'/SOURCE).read_bytes();nl='\r\n'if b'\r\n'in old else '\n';proposal=out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());(out/'selected-source.c').write_text(source)
 compile_owner(root,out,source,'final');write_csv()
 targets,commands=q.actual_make({OWNER:proposal});obj=targets[OWNER];compact=Path(str(obj)+'.compact');before,bd=compile_owner(root,out,old.decode(),'independent-before');after,ad=compile_owner(root,out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(NAME,))==16 and same_functions(compact,after)==17 and same_functions(out/'frozen/conker/build/src/game/generated_1E37D0.c.o',obj,(NAME,))==16
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 def payload(o):
  data,fs,rs=parse_object(o);a,n=fs[NAME]['value'],fs[NAME]['size'];return data[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 raw,refs=payload(compact);original,origrefs=payload(out/'original_151B76CC.o');fixed,freferences=payload(obj);assert (fixed,freferences)==(original,origrefs);assert sha(raw)==PIN['raw_sha256'];assert normalize(raw,refs)==(fixed,freferences)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(fixed,freferences,{nm:lookup[nm]for es in freferences.values()for _,nm in es});truth=(root/'conker/conker.us.bin').read_bytes()[0x1E4B7C:0x1E4B7C+296];assert struct.pack('>74I',*words)==truth
 elf=q.link(targets);baseline=(out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys()and oa==na and{name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={NAME}
 data=audit_layout(elf,root/'conker');assert data['exact']and data['different_bytes']==0
 live_inputs(installed)
 hashes={n:sha(f.read_bytes())for n,f in ((SOURCE,proposal),('conker/retail_word_patches.us.csv',out/'proposed-guards.csv'),('conker/build/src/game/generated_1E37D0.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=74,retail_words=74,guards=38,inserted_words=0,non_target_neighbors=16,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from ring-entry workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
