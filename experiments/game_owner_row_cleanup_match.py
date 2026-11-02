"""Owner row cleanup: semantic C, closed loop rotation and literal full-image audit."""
from pathlib import Path
import hashlib,json
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_1518BBF4','generated_1B8F40'
ENTRY,ROM,BODY,SIZE=0x1518BBF4,0x1B90A4,216,220
SOURCE='conker/src/game/generated_1B8F40.c'
OBJECT='conker/build/src/game/generated_1B8F40.c.o'
BUILD='conker/build/game-owner-row-cleanup-1518BBF4-match'
NEW_GUARDS=[[32, 301989925, 301989926, '-', '-', None, 'Retarget null-owner exit across the closed loop-rotation word'], [40, 1007943680, 1007943680, 'R_MIPS_HI16:D_800DCE50', 'R_MIPS_HI16:D_800DD190', None, 'Bind the table endpoint high half to its retained end alias'], [52, 645070848, 640745472, 'R_MIPS_LO16:D_800DCE50', 'R_MIPS_LO16:D_800DD190', None, 'Move independent traversal-depth address completion first'], [56, 647234368, 642908160, 'R_MIPS_LO16:D_800DCE50', 'R_MIPS_LO16:D_800DD198', None, 'Move independent traversal-stack address completion second'], [60, 640745472, 647233536, 'R_MIPS_LO16:D_800DD190', 'R_MIPS_LO16:D_800DD190', None, 'Complete the retained table endpoint alias third'], [64, 642908160, 645070848, 'R_MIPS_LO16:D_800DD198', 'R_MIPS_LO16:D_800DCE50', None, 'Complete the initial row address after the independent setup cycle'], [176, 376766436, 2720923648, '-', '-', None, 'Place the depth decrement store before the rotated back edge'], [180, 2720923648, 1450508260, '-', '-', 2184052736, 'Rotate the next-row depth load into the likely back-edge delay slot']]
sha=lambda b:hashlib.sha256(b).hexdigest()
HEADERS='#include <ultra64.h>\n#include "structs.h"\nextern u8 D_800DCE50[0x340];\nextern s8 D_800DD190;\nextern u8 *D_800DD198[];\nvoid func_1516972C(struct102 *);\n'
SELECTED='/* Walk both rows, retaining each next link across record cleanup. */\nvoid func_1518BBF4(u8 *owner) {\n    u8 *row;\n    u8 *record;\n    u8 *rowEnd;\n    if (owner != NULL) {\n        row = D_800DCE50;\n        rowEnd = D_800DCE50 + 0x340;\n        do {\n            record = *(u8 **)(row + 0x7C);\n            D_800DD190++;\n            while (record != NULL) {\n                D_800DD198[D_800DD190] = *(u8 **)(record + 8);\n                *(u8 **)(record + 0x24) = owner;\n                if (owner != NULL || owner[0x3B] == record[0x28]) {\n                    func_1516972C((struct102 *)record);\n                }\n                record = D_800DD198[D_800DD190];\n            }\n            D_800DD190--;\n            row += 0x1A0;\n        } while (row != rowEnd);\n    }\n}\n'
RAW_SHA='a1faf50f5736e7ad28255ff837773002798a24f33bc878e9362d1c17b2f2597e'
BINDINGS={36: [('R_MIPS_HI16', 'D_800DCE50')], 52: [('R_MIPS_LO16', 'D_800DCE50')], 40: [('R_MIPS_HI16', 'D_800DCE50')], 56: [('R_MIPS_LO16', 'D_800DCE50')], 44: [('R_MIPS_HI16', 'D_800DD198')], 64: [('R_MIPS_LO16', 'D_800DD198')], 48: [('R_MIPS_HI16', 'D_800DD190')], 60: [('R_MIPS_LO16', 'D_800DD190')], 132: [('R_MIPS_26', 'func_1516972C')]}
NORMALIZED_BINDINGS={36: [('R_MIPS_HI16', 'D_800DCE50')], 40: [('R_MIPS_HI16', 'D_800DD190')], 44: [('R_MIPS_HI16', 'D_800DD198')], 48: [('R_MIPS_HI16', 'D_800DD190')], 52: [('R_MIPS_LO16', 'D_800DD190')], 56: [('R_MIPS_LO16', 'D_800DD198')], 60: [('R_MIPS_LO16', 'D_800DD190')], 64: [('R_MIPS_LO16', 'D_800DCE50')], 132: [('R_MIPS_26', 'func_1516972C')]}
SNAPSHOT_SHA='0de914ea544ec372747bcadd778421da5fdeee4717d93141f1d3bee8bf31f464'
ARTIFACT_SHA='1ba4600d7d965f8ff06683201697afb2e6b714341f7eec3183ebecb397d0358a'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Owner row cleanup payload/bindings changed')
 return raw,bindings

DECLARATIONS='extern u8 D_800DCE50[0x340];\nextern s8 D_800DD190;\nextern u8 *D_800DD198[];\nvoid func_1516972C(struct102 *);'
def recovered_owner(before):
 lo,hi=function_span(before,FUNCTION)
 if before[lo:hi].strip()!='s32 func_1518BBF4() {\n    return 0;\n}':raise ValueError('Owner row cleanup predecessor changed')
 result=before[:lo]+SELECTED.rstrip()+before[hi:];anchor='s32 func_150ADA20(void);'
 if result.count(anchor)!=1:raise ValueError('Owner row cleanup declaration anchor changed')
 return result.replace(anchor,anchor+'\n\n'+DECLARATIONS,1)

GUARD_ROWS=b'generated_1B8F40,func_1518BBF4,0x020,0x12000025,0x12000026,-,-,Retarget null-owner exit across the closed loop-rotation word,,,false\ngenerated_1B8F40,func_1518BBF4,0x028,0x3C140000,0x3C140000,R_MIPS_HI16:D_800DCE50,R_MIPS_HI16:D_800DD190,Bind the table endpoint high half to its retained end alias,,,false\ngenerated_1B8F40,func_1518BBF4,0x034,0x26730000,0x26310000,R_MIPS_LO16:D_800DCE50,R_MIPS_LO16:D_800DD190,Move independent traversal-depth address completion first,,,false\ngenerated_1B8F40,func_1518BBF4,0x038,0x26940340,0x26520000,R_MIPS_LO16:D_800DCE50,R_MIPS_LO16:D_800DD198,Move independent traversal-stack address completion second,,,false\ngenerated_1B8F40,func_1518BBF4,0x03C,0x26310000,0x26940000,R_MIPS_LO16:D_800DD190,R_MIPS_LO16:D_800DD190,Complete the retained table endpoint alias third,,,false\ngenerated_1B8F40,func_1518BBF4,0x040,0x26520000,0x26730000,R_MIPS_LO16:D_800DD198,R_MIPS_LO16:D_800DCE50,Complete the initial row address after the independent setup cycle,,,false\ngenerated_1B8F40,func_1518BBF4,0x0B0,0x1674FFE4,0xA22E0000,-,-,Place the depth decrement store before the rotated back edge,,,false\ngenerated_1B8F40,func_1518BBF4,0x0B4,0xA22E0000,0x5674FFE4,-,-,Rotate the next-row depth load into the likely back-edge delay slot,0x822E0000,,false\n'
def recovered_guards(before):
 if not before.endswith(b'\n') or b',func_1518BBF4,' in before:raise ValueError('Owner row cleanup guard predecessor changed')
 return before+GUARD_ROWS

def normalized_payload(raw,bindings=None):
 import struct
 bindings=BINDINGS if bindings is None else bindings
 checked_payload(raw,bindings);patches={p[0]:p for p in NEW_GUARDS};out=bytearray();refs={}
 for at in range(0,len(raw),4):
  word=struct.unpack_from('>I',raw,at)[0];relocs=list(bindings.get(at,[]));patch=patches.get(at)
  if patch is not None:
   _,old,new,er,rr,insert,_=patch
   expected=[]if er=='-'else[tuple(er.split(':',1))]
   if word!=old or relocs!=expected:raise ValueError('Owner row cleanup closed layout expected word or binding changed')
   word=new;relocs=[]if rr=='-'else[tuple(rr.split(':',1))]
  if relocs:refs[len(out)]=relocs
  out.extend(struct.pack('>I',word))
  if patch is not None and patch[5]is not None:out.extend(struct.pack('>I',patch[5]))
 if len(out)!=SIZE or refs!=NORMALIZED_BINDINGS:raise ValueError('Owner row cleanup closed layout shape changed')
 return bytes(out),refs

def verify_group(image):
 rows={n:f[1]for _,n,f,_ in symbol_rows(image)};table=rows['D_800DCE50']
 if rows['D_800DD190']!=table+0x340 or rows['D_800DD198']!=table+0x348:raise ValueError('Owner row cleanup retained BSS group geometry changed')
 return True

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Owner row cleanup snapshot index changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  data=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(data)!=h:raise ValueError('Owner row cleanup frozen input changed: '+n)
  values[n]=data
 return values

def verify_prepared(output):
 data=(output/'prepared-artifacts.json').read_bytes()
 if sha(data)!=ARTIFACT_SHA:raise ValueError('Owner row cleanup prepared index changed')
 for n,h in json.loads(data).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Owner row cleanup prepared evidence changed: '+n)
 return True

def expected_map(output):
 data=(output/'first-linked.map').read_bytes();private=b'build/game-owner-row-cleanup-1518BBF4-match/make-shadow/src/game/generated_1B8F40.c.o'
 if data.count(private)!=9:raise ValueError('Owner row cleanup private map object occurrences changed')
 data=data.replace(private,b'build/src/game/generated_1B8F40.c.o');name=b'build/game-owner-row-cleanup-1518BBF4-match/first-linked.elf'
 if data.count(name)!=1:raise ValueError('Owner row cleanup private output map occurrence changed')
 return data.replace(name,b'build/conker.us.elf')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={'conker/retail_word_patches.us.csv':recovered_guards(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])[0],'conker/build/conker.us.map':expected_map(output)}
 for n,data in values.items():
  if(root/n).read_bytes()!=changes.get(n,data):raise ValueError('Owner row cleanup live input changed: '+n)
 return values

def check_image(before,actual,truth):
 if actual!=predict(before,truth)[0]:raise ValueError('Owner row cleanup literal full-image prediction differs')

def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 reference=(output/'first-linked.elf').read_bytes()
 if actual!=reference:raise ValueError('Owner row cleanup production differs from qualified first link')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Owner row cleanup protected data changed')
 q=json.loads((output/'private-owner-image-v15.json').read_text())
 if not q['success']or not q['strict_whole_image_prediction']or q['strict_exclusions']!=0:raise ValueError('Owner row cleanup image qualification failed')
 q.update(private_only=False,installed=True,matching_credit=1,protected_data=data,actual_Make_literal_image_equal=True)
 (output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q



from collections import Counter
import struct
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
BASELINE='2d4f55fb3eb0eb90fb9d5cf829d92ea1771b03b1d2529a3f22bb8a8ba0c7f3af'
def predict(before,truth):
 if sha(before)!=BASELINE or len(truth)!=220:raise ValueError('Owner row cleanup image predecessor or slot changed')
 verify_group(before);rows=[row for row in symbol_rows(before)if row[1]==FUNCTION]
 if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Owner row cleanup predecessor extent changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,220);result[at:at+220]=truth;struct.pack_into('>I',result,rows[0][0]+8,220)
 return bytes(result),dict(target=FUNCTION,raw_words=54,target_words=55,frame=48,guards=8,old_symbol_bytes=12,new_symbol_bytes=220,ELF_length_unchanged=True,strict_exclusions=0)
