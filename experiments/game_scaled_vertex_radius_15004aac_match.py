import os,sys,hashlib,json,struct,csv,io,inspect
from pathlib import Path
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
root=ROOT;out=root/'conker/build/game-next-15004AAC-match'
NAME='func_15004AAC';OWNER='game_30E90';SOURCE='conker/src/game_30E90.c';ENTRY=0x15004AAC;ROM=0x31F5C;SIZE=324
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
MANIFEST=json.loads(Path(__file__).with_name('game_scaled_vertex_radius_15004aac_manifest.json').read_text(encoding='utf-8'))
FROZEN=MANIFEST['frozen'];p=sys.modules[__name__]
BASE='void func_15004AAC(BoundsRecord *record, s32 unused) {\n    s32 i;\n    s32 maximum = 0;\n    for (i = 0; i < record->count; i++) {\n        s16 vz = record->vertices[i].z;\n        f32 x = record->vertices[i].x * record->sx;\n        f32 y = record->vertices[i].y * record->sy;\n        f32 z = vz * record->sz;\n        s32 distance = z * z + (x * x + y * y);\n        if (maximum < distance) maximum = distance;\n    }\n    if (maximum != 0) {\n        s32 radius = sqrtf((f32)maximum);\n        if (record->radius == 0) {\n            record->radius = radius;\n            record->maximum = radius;\n            D_800BE2A2++;\n        } else if (record->radius < radius || record->maximum < radius) {\n            D_800BE2A0++;\n        } else {\n            D_800BE2A4++;\n        }\n    }\n}'
SELECTED='#include <ultra64.h>\n\n#include "functions.h"\n#include "variables.h"\n\ntypedef struct { s16 x,y,z; u8 pad[10]; } BoundsVertex;\ntypedef struct { u8 pad0[0x16]; u16 count; u8 pad18[0x10]; BoundsVertex *vertices; f32 sx,sy,sz; u8 pad38[0x18]; u16 radius, maximum; } BoundsRecord;\nextern u16 D_800BE2A0,D_800BE2A2,D_800BE2A4;\n\ntypedef struct { u8 reserved[0x72]; u8 id; u8 tail[0x2D]; } ByteIdRecordView;\n\n\n/* Generated placeholder declarations. */\ns32 func_150039E0();\ns32 func_150045C4();\nvoid func_150049A4(s8 *, u32, u32);\nvoid func_15004AAC(BoundsRecord *, s32);\ns32 func_15004BF0(s32 descending);\n/* End generated placeholder declarations. */\n\n/* Non-matching C placeholders for asm/nonmatchings/game_30E90/func_150039E0.s. */\ns32 func_150039E0() {\n    return 0;\n}\n\n// FIXME: matches but something isnt right\nvoid func_15004574(void) {\n    if (D_800DBF88 != 0xFF) {\n        D_800DBF8C = D_800DBEF4[D_800DBF88].unk1C;\n        D_800DBF90 = D_800DBEF4[D_800DBF88].unk28;\n    }\n}\n\nvoid func_150045BC(void) {\n}\n\n/* Non-matching C placeholders for asm/nonmatchings/game_30E90/func_150045C4.s. */\ns32 func_150045C4() {\n    return 0;\n}\n/* Relocate vertex/data and matrix command addresses in place. */\nvoid func_150049A4(s8 *commands, u32 dataOffset, u32 matrixOffset) {\n    s32 index;\n    s8 *command;\n    s32 opcode;\n\n    for (index = 0; commands[index << 3] != (s8)G_ENDDL; index++) {\n        command = commands + (index << 3);\n        opcode = command[0];\n        switch (opcode) {\n            /* Retail keeps this positive comparison after the signed load. */\n            case G_DL:\n                *(u32 *)(command + 4) += dataOffset;\n                break;\n            case G_VTX:\n                *(u32 *)(command + 4) += dataOffset;\n                break;\n            case (s8)G_MOVEMEM:\n                if ((u8)command[3] == G_MV_MATRIX) {\n                    *(u32 *)(command + 4) += matrixOffset;\n                }\n                break;\n        }\n    }\n}\n// NON-MATCHING: not this...\nvoid func_15004A4C(void) {\n    s32 i;\n\n    for (i = 0; i < D_800DBEF0; i++) {\n        D_800DBEF8[i] = 0;\n        D_800DBEFC[i] = 0;\n    }\n}\n\n/* Check the scaled vertex radius and count the result. */\nvoid func_15004AAC(BoundsRecord *record, s32 unused) {\n    s32 i;\n    s32 maximum = 0;\n    for (i = 0; i < record->count; i++) {\n        s16 vz = record->vertices[i].z;\n        f32 x = record->vertices[i].x * record->sx;\n        f32 y = record->vertices[i].y * record->sy;\n        f32 z = vz * record->sz;\n        s32 distance = z * z + (x * x + y * y);\n        if (maximum < distance) maximum = distance;\n    }\n    if (maximum != 0) {\n        s32 radius = sqrtf((f32)maximum);\n        if (record->radius == 0) {\n            record->radius = radius;\n            record->maximum = radius;\n            D_800BE2A2++;\n        } else if (record->radius < radius || record->maximum < radius) {\n            D_800BE2A0++;\n        } else {\n            D_800BE2A4++;\n        }\n    }\n}\n/* Search record byte IDs in either direction, retaining saturation fallbacks. */\ns32 func_15004BF0(s32 descending) {\n    s32 id;\n    s32 index;\n    /* After choosing direction, retain the scan boundary in the argument. */\n    if (descending == 0) {\n        id = 1;\n        for (index = descending = D_800DBF00; index < D_800DBEF0; index++) {\n            if (id == ((ByteIdRecordView *)D_800DBEF4)[index].id) {\n                id++;\n                index = descending - 1;\n            }\n            if (id >= 256) { id = 255; break; }\n        }\n    } else {\n        descending = 255 - D_800DBF00;\n        id = descending;\n        for (index = 0; index < D_800DBEF0; index++) {\n            if (id == ((ByteIdRecordView *)D_800DBEF4)[index].id) {\n                id--;\n                index = -1;\n            }\n            if (id <= 0) { id = descending; break; }\n        }\n    }\n    return id;\n}\nvoid func_15004CE0(s8 *arg0, s32 arg1) {\n    s32 i = 0;\n    s8 *cur = arg0;\n    s32 opcode;\n\n    if (cur[0] != -0x21) {\n        opcode = *(volatile s8 *)cur;\n        do {\n            if ((opcode == -0x24) && ((u8)cur[3] == 0xE) && (*(u32 *)(cur + 4) < 0x80000000U)) {\n                *(u32 *)(cur + 4) += arg1;\n            }\n            i++;\n            cur = (s8 *)((u32)arg0 + (i << 3));\n            opcode = cur[0];\n        } while (opcode != -0x21);\n    }\n}\n'
def payload(path):
 t,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return t[a:a+n],{i-a:v for i,v in rs.items() if a<=i<a+n}

def variant(old):
 assert hashlib.sha256(old.encode()).hexdigest()==FROZEN[SOURCE]
 return SELECTED

PIN=MANIFEST["raw_pin"];n=p
def normalize(raw,refs):
 expected={int(k):[tuple(x) for x in v] for k,v in PIN['refs'].items()}
 if len(raw)!=324 or hashlib.sha256(raw).hexdigest()!=PIN['sha256'] or refs!=expected:raise ValueError('Vertex-radius body or bindings changed')
 words=list(struct.unpack('>81I',raw))
 for row in PIN['differences']:
  i=row['index'];assert not refs.get(4*i) and words[i]==int(row['raw'],16);words[i]=int(row['retail'],16)
 return struct.pack('>81I',*words),dict(refs)
def rows(raw,refs):
 normalize(raw,refs)
 return [dict(filename='game_30E90',function=p.NAME,offset='0x%X'%(4*d['index']),expected='0x'+d['raw'],replacement='0x'+d['retail'],expected_relocations='-',replacement_relocations='-',note='Normalize scaled-vertex calculation register allocation and scheduling',insert_after='',insert_after_relocations='',omit='false') for d in PIN['differences']]
def write_csv():
 raw,refs=p.payload(p.out/'final.o');before=(p.out/'frozen/conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(before.decode())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writerows(rows(raw,refs));assert before.endswith(b'\n');(p.out/'proposed-guards.csv').write_bytes(before+stream.getvalue().encode());print(json.dumps(dict(guards=27,previous_bytes=len(before))))

from tools.experiments import game_sequence_direction_1501fe68_match as q
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
sha=lambda b:hashlib.sha256(b).hexdigest()
code=inspect.getsource(q.strict_image).replace("{'func_1501FE68':384,'func_1501F72C':28,'func_1501FFE8':28}","{'func_15004AAC':324}");scope=dict(q.strict_image.__globals__);exec(code,scope);strict_image=scope['strict_image']

MUTABLE=(SOURCE,'conker/retail_word_patches.us.csv','conker/build/src/game_30E90.c.o','conker/build/conker.us.elf','conker/build/conker.us.bin')
def freeze():
 out.mkdir(parents=True,exist_ok=True)
 for n in set(MUTABLE)|{'conker/build/conker.ld','conker/progress.csv','conker/retail_layout.us.txt'}:
  f=out/'frozen'/n
  if not f.exists():
   data=(root/n).read_bytes()
   if sha(data)!=FROZEN[n]:raise ValueError('Retained pre-adoption vertex-radius input required: '+n)
   f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
  if sha(f.read_bytes())!=FROZEN[n]:raise ValueError('Changed frozen vertex-radius input: '+n)
 live=sha((root/SOURCE).read_bytes())
 if live==FROZEN[SOURCE]:installed=False
 elif live==MANIFEST['installed_hashes'][SOURCE]:installed=True
 else:raise ValueError('Unknown vertex-radius source state')
 allowed=dict(MANIFEST['installed_hashes']);allowed['conker/build/conker.us.bin']=MANIFEST['binary_sha256']
 for n,h in FROZEN.items():
  actual=sha((root/n).read_bytes())
  if actual!=h and not(installed and n in allowed and actual==allowed[n]):raise ValueError('Changed vertex-radius qualification input: '+n)
 if installed:
  for n,h in allowed.items():
   if sha((root/n).read_bytes())!=h:raise ValueError('Installed vertex-radius result incomplete: '+n)
 truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert sha(truth)==MANIFEST['truth_sha256'];(out/'original-function.bin').write_bytes(truth)
 return FROZEN,installed
def live_inputs(installed):
 _,state=freeze()
 if state!=installed:raise ValueError('Vertex-radius source state changed during validation')
 return dict(fingerprinted_inputs=len(FROZEN),source_installed=state)


def main():
 q.p=p
 frozen,installed=freeze()
 source=variant((out/'frozen'/SOURCE).read_text());(out/'selected-source.c').write_text(source);compile_owner(root,out,source,'final');old=(p.out/'frozen'/p.SOURCE).read_bytes();nl='\r\n' if b'\r\n' in old else '\n';proposal=p.out/'game-proposal.c';proposal.write_bytes(source.replace('\n',nl).encode());n.write_csv()
 targets,commands=q.actual_make({p.OWNER:proposal});obj=targets[p.OWNER];compact=__import__('pathlib').Path(str(obj)+'.compact')
 before,bd=p.compile_owner(p.root,p.out,old.decode(),'independent-before');after,ad=p.compile_owner(p.root,p.out,source,'independent-selected')
 assert diagnostic_rows(bd)==diagnostic_rows(ad),(bd,ad)
 assert same_functions(before,after,(p.NAME,))==8 and same_functions(compact,after)==9 and same_functions(p.out/'frozen/conker/build/src/game_30E90.c.o',obj,(p.NAME,))==8
 assert normalized_pools(before)==normalized_pools(after)==normalized_pools(compact);assert sections(after)['.reginfo']==sections(compact)['.reginfo']
 raw,refs=p.payload(compact);fixed,references=n.normalize(raw,refs);assert p.payload(obj)==(fixed,references)
 lookup={v[1]:v[2][1] for v in p.symbol_rows((p.root/'conker/build/conker.us.elf').read_bytes())};words=p.bound_blob(fixed,references,{name:lookup[name] for es in references.values() for _,name in es});truth=(p.root/'conker/conker.us.bin').read_bytes()[p.ROM:p.ROM+p.SIZE];assert struct.pack('>81I',*words)==truth
 elf=q.link(targets);baseline=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();actual=elf.read_bytes();image=strict_image(baseline,actual,{p.NAME:truth})
 oldfunc,_,oa=load_elf_functions(str(p.out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');newfunc,_,na=load_elf_functions(str(elf),'mips-linux-gnu-objdump');assert oldfunc.keys()==newfunc.keys() and oa==na and {name for name in oldfunc if oldfunc[name]!=newfunc[name]}=={p.NAME}
 data=audit_layout(elf,p.root/'conker');assert data['exact'] and data['different_bytes']==0
 live_inputs(installed)
 hashes={name:sha(f.read_bytes()) for name,f in ((p.SOURCE,proposal),('conker/retail_word_patches.us.csv',p.out/'proposed-guards.csv'),('conker/build/src/game_30E90.c.o',obj),('conker/build/conker.us.elf',elf))}
 assert hashes==MANIFEST['installed_hashes'] and image==MANIFEST['image']
 result=dict(source_installed=installed,frozen_inputs=len(frozen),raw_words=81,frame=0,guards=27,non_target_neighbors=8,actual_Make_commands=len(commands),functions=len(newfunc),all_addresses_fixed=True,image=image,protected_data=data,installed_hashes=hashes)
 (p.out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);return result

def prepare(consumer=ROOT):
 if Path(consumer).resolve()!=ROOT:raise ValueError("Consumer differs from vertex-radius workspace")
 prior=q.p
 try:return main()
 finally:q.p=prior

if __name__=="__main__":prepare()
