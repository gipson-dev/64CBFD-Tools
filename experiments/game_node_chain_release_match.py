"""Node chain release guarded C, owner and literal image audit."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_151D3130','game_1FFF60'
ENTRY,ROM,BODY,SIZE=0x151D3130,0x2005E0,196,196
SOURCE='conker/src/game_1FFF60.c'
OBJECT='conker/build/src/game_1FFF60.c.o'
ASM='conker/asm/nonmatchings/game_1FFF60/func_151D3130.s'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-node-chain-release-151D3130-match'
RAW_SHA='efef53a5d5a4d70e6b02bc67864654cc00a11b06383a628e9cade99e7646d676'
TRUTH_SHA='2c705f318b63d07595907acd109c7d12ad21ced57dc5d33fcb4ac0a845a204c8'
BEFORE_ELF_SHA='0c7cc112eb7b61f6e3322e8d4e84dbdaea048cad244c5aca5f941ac33eec3cbb'
BINDINGS={36:[('R_MIPS_HI16','D_8008FC5C')],48:[('R_MIPS_LO16','D_8008FC5C')],72:[('R_MIPS_HI16','D_8008FC48')],76:[('R_MIPS_LO16','D_8008FC48')],132:[('R_MIPS_26','func_1516972C')],156:[('R_MIPS_26','func_1514EDF0')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
NEW_GUARDS=[(140, 1130539, 35684389, '-'), (144, 352387057, 1445003250, '-'), (148, 35684389, 2181169194, '-')]
HEADERS='#include <ultra64.h>\n#include "structs.h"\ntypedef struct ReleaseChainNode ReleaseChainNode;\nstruct ReleaseChainNode {\n    u8 retained[0x2A];\n    s8 releaseKind;\n    u8 pad2B;\n    void *owner;\n    u8 pad30[4];\n    u8 payload[12];\n    ReleaseChainNode *next;\n};\ntypedef struct {\n    u8 retained[0x10];\n    void *listOwner;\n    u8 pad14[9];\n    u8 releaseKind;\n    u8 pad1E[6];\n    ReleaseChainNode *head;\n} ReleaseChainOwner;\ntypedef void (*ReleaseOwnerCallback)(ReleaseChainOwner *);\ntypedef void (*ReleaseNodeCallback)(ReleaseChainNode *, void *);\nextern ReleaseOwnerCallback D_8008FC5C[];\nextern ReleaseNodeCallback D_8008FC48[];\nvoid func_1516972C(struct102 *);\nvoid func_1514EDF0(s32, u8 *);\n'
SELECTED="/* Notify the owner and release its child chain using links captured before callbacks.\n * Finally detach the owner key from the referenced object's list. */\nvoid func_151D3130(void *ownerData) {\n    ReleaseChainOwner *owner = ownerData;\n    ReleaseChainNode *node;\n    ReleaseChainNode *next;\n    ReleaseOwnerCallback callback;\n    ReleaseNodeCallback *callbacks;\n    s32 skipKind;\n\n    callback = D_8008FC5C[owner->releaseKind];\n    if (callback != NULL) {\n        callback(owner);\n    }\n    node = owner->head;\n    callbacks = D_8008FC48;\n    skipKind = -1;\n    if (node != NULL) {\n        do {\n            next = node->next;\n            if (node->releaseKind != skipKind) {\n                callbacks[node->releaseKind](node, node->payload);\n            }\n            node->owner = NULL;\n            func_1516972C((struct102 *)node);\n            node = next;\n        } while ((node != NULL) != 0);\n    }\n    func_1514EDF0((s32)owner, (u8 *)owner->listOwner);\n}\n"

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Node chain release payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 old='/* Non-matching C placeholders for asm/nonmatchings/game_1FFF60/func_151D3130.s. */\ns32 func_151D3130(s32 arg0) {\n    return 0;\n}'
 declaration='s32 func_151D3130(s32 arg0);'
 if before.count(old)!=1 or before.count(declaration)!=1:raise ValueError('Chain release placeholder changed')
 local=HEADERS.split('#include "structs.h"\n',1)[1]
 return before.replace(old,SELECTED.rstrip(),1).replace(declaration,'void func_151D3130(void *ownerData);',1).replace('/* Generated placeholder declarations. */',local+'\n/* Generated placeholder declarations. */',1)

def proposed_guards(before):
 if b'game_1FFF60,func_151D3130,' in before:raise ValueError('Node chain release guards already present')
 if not before.endswith(b'\n'):raise ValueError('Guard table lost final newline')
 newline='\r\n'if b'\r\n'in before else'\n'
 rows=[]
 for offset,expected,replacement,reloc in NEW_GUARDS:
  rows.append('game_1FFF60,func_151D3130,0x%X,0x%08X,0x%08X,%s,%s,Normalize closed child-chain loop backedge and next-kind preload,,,false'%(offset,expected,replacement,reloc,reloc))
 return before+(newline.join(rows)+newline).encode()

def diagnostic_rows(text):
 rows=[]
 lines=text.splitlines()
 for i,line in enumerate(lines):
  match=re.match(r'cfe: Warning (\d+): .*?, line \d+: (.*)',line)
  if match:rows.append((match[1],match[2],lines[i+1].strip()))
  elif line.startswith('cfe:')and 'Warning'not in line:raise ValueError('Unexpected compiler diagnostic')
 return Counter(rows)
def check_owner_diagnostics(before,after):
 a,b=diagnostic_rows(before),diagnostic_rows(after)
 removed=Counter({('712','illegal combination of pointer and integer','func_151D3130(arg0);'):2})
 if a-b!=removed or b-a:raise ValueError(('Unexpected chain owner diagnostic change',a-b,b-a))
 return dict(before=sum(a.values()),after=sum(b.values()),removed_pointer_integer_argument_warnings=2)

def predicted_image(before,truth):
 if sha(before)!=BEFORE_ELF_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Node chain release predictor baseline changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,16):raise ValueError('Node chain release predecessor extent changed')
 struct.pack_into('>I',result,rows[0][0]+8,BODY)
 # GNU ld swaps this adjacent symbol/string pair when the new owner references
 # are introduced. Predict the complete serialization from pinned BEFORE rows;
 # retain both definitions, all metadata fields and the exact total string size.
 rows=symbol_rows(before);first=next(row for row in rows if row[1]=='func_150F85A0');second=next(row for row in rows if row[1]=='D_8009E6F0')
 if second[0]!=first[0]+16 or second[2][0]!=first[2][0]+len(first[1])+1:raise ValueError('GNU symbol pair order changed')
 header=struct.unpack_from('>16sHHIIIIIHHHHHH',before);sections=[struct.unpack_from('>10I',before,header[6]+i*header[11])for i in range(header[12])]
 symtab=next(v for v in sections if v[1]==2);strings=sections[symtab[6]];index=first[2][0];at=strings[4]+index
 old=(first[1]+'\0'+second[1]+'\0').encode();new=(second[1]+'\0'+first[1]+'\0').encode()
 if before[at:at+len(old)]!=old:raise ValueError('GNU symbol strings changed')
 if any(index<row[2][0]<index+len(old)and row[1]!=second[1]for row in rows):raise ValueError('Unexpected substring symbol reference')
 result[at:at+len(old)]=new
 result[first[0]:first[0]+16]=before[second[0]:second[0]+16];struct.pack_into('>I',result,first[0],index)
 result[second[0]:second[0]+16]=before[first[0]:first[0]+16];struct.pack_into('>I',result,second[0],index+len(second[1])+1)
 return bytes(result)

SNAPSHOT_SHA='27514afa6431db8e1278ea2966f3a1442adb2004eb84ac0c934300937d156ea5'
PREPARED_SHA='27d18b781b98e359f71e2a2972f082121ba9c44176891d4b0968388ecfb4707a'
NEIGHBORS=18
EVIDENCE=('selected-final.o', 'selected-final.c', 'selected-final-processed.c', 'selected-final-diagnostics.txt', 'original-func_151D3130.o', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.o', 'after-owner-diagnostics.txt', 'proposed-owner.c', 'qualified-padded.o', 'qualified-padded.s', 'before-padded.o', 'Make-commands.json', 'actual-Make-plan.txt', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_1FFF60.c.o', 'first-link.ld', 'first-linked.elf', 'preparation.json', 'runtime-qualification.json', 'caller-census.json', 'proposed-guards.csv')

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Node chain release input index changed')
 values={}
 for name,h in json.loads(data)['INPUTS'].items():
  value=(output/('before-'+name.replace('/','_'))).read_bytes()
  if sha(value)!=h:raise ValueError('Node chain release frozen input changed: '+name)
  values[name]=value
 return values
def verify_prepared(output):
 data=(output/'canonical-prepared-fingerprint.json').read_bytes()
 if sha(data)!=PREPARED_SHA:raise ValueError('Node chain release preparation index changed')
 rows=json.loads(data)
 if set(rows)!=set(EVIDENCE):raise ValueError('Node chain release evidence set changed')
 for name,h in rows.items():
  if sha((output/name).read_bytes())!=h:raise ValueError('Node chain release prepared artifact changed: '+name)
 q=json.loads((output/'preparation.json').read_text())
 if not(q['complete']and q['strict_whole_image_prediction']and q['actual_Make_object_equals_qualified']and q['neighbors']==NEIGHBORS and q['guards']==3 and q['exclusions']==0):raise ValueError('Node chain release preparation failed')
 return rows
def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Node chain release literal whole-image mismatch')
 expected=Counter((name,f[1],BODY if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
 if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):raise ValueError('Node chain release named definitions changed')
def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:
  changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':proposed_guards(values['conker/retail_word_patches.us.csv'])}
  changes['conker/build/conker.us.elf']=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
 for name,data in values.items():
  if(root/name).read_bytes()!=changes.get(name,data):raise ValueError('Node chain release live input changed: '+name)
 return values
def audit(root,output):
 from tools.match_progress import load_elf_functions
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or[name for name in a if a[name]!=b[name]]!=[FUNCTION]:raise ValueError('Node chain release linked neighbor/address changed')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Node chain release protected data changed')
 result=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=49,frame=48,alignment_words=0,guards=3,direct_C_match=False,strict_first_link_reproduced=True,game_data=data)
 (output/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
