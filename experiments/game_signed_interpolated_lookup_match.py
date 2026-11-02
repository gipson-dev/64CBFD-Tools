"""Direct signed angle interpolation and literal complete-image qualification."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_actor_transform_position_match import check_owner_diagnostics
from tools.tests.game_owner_pool import normalized_pools

FUNCTION,OWNER='func_150488C8','game_75C90'
ENTRY,ROM,BODY,SIZE=0x150488C8,0x75D78,220,232
SOURCE='conker/src/game_75C90.c'
OBJECT='conker/build/src/game_75C90.c.o'
BUILD='conker/build/game-signed-interpolated-lookup-150488C8-match'
BASELINE='f95f2f13f43d030328e6432e0240099f9abae1a5a5133719f649dd7cad72cf2c'
RAW_SHA='38792e63b67e679eda3babedd0c6cc9625db5c0bf1f1407a617e2bc5fbd011ce'
sha=lambda data:hashlib.sha256(data).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Signed interpolation payload/bindings changed')
 return raw,bindings

def recovered_owner(before):
 marker='/* Non-matching C placeholders for asm/nonmatchings/game_75C90/func_150488C8.s. */'
 lo,hi=function_span(before,FUNCTION)
 if before[lo:hi]!='f32 func_150488C8(f32 arg0) {\n    return 0.0f;\n}' or before.count(marker)!=1:raise ValueError('Signed interpolation predecessor changed')
 return before[:before.index(marker)]+"/* Interpolate the unsigned angle table and restore the input sign.\n * Preserve the retail routine's unchecked table index. */\n"+SELECTED

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Signed interpolation snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  data=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(data)!=h:raise ValueError('Signed interpolation frozen input changed: '+n)
  values[n]=data
 return values

def verify_prepared(output):
 data=(output/'prepared-artifacts.json').read_bytes()
 if sha(data)!=ARTIFACT_SHA:raise ValueError('Signed interpolation artifact index changed')
 for n,h in json.loads(data).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Signed interpolation artifact changed: '+n)
 return True

def expected_map(output):
 data=(output/'first-linked.map').read_bytes();private=b'build/game-signed-interpolated-lookup-150488C8-match/make-shadow/src/game_75C90.c.o'
 if data.count(private)!=9:raise ValueError('Signed interpolation map owner count changed')
 data=data.replace(private,b'build/src/game_75C90.c.o');private=b'build/game-signed-interpolated-lookup-150488C8-match/first-linked.elf'
 if data.count(private)!=1:raise ValueError('Signed interpolation map output changed')
 return data.replace(private,b'build/conker.us.elf')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])[0],'conker/build/conker.us.map':expected_map(output)}
 for n,data in values.items():
  if(root/n).read_bytes()!=changes.get(n,data):raise ValueError('Signed interpolation live input changed: '+n)
 return values

def predict(before,truth):
 if sha(before)!=BASELINE or len(truth)!=SIZE:raise ValueError('Signed interpolation predecessor or slot changed')
 row,=[v for v in symbol_rows(before)if v[1]==FUNCTION]
 if row[2][1:3]!=(ENTRY,20):raise ValueError('Signed interpolation predecessor extent changed')
 out=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);out[at:at+SIZE]=truth;struct.pack_into('>I',out,row[0]+8,BODY)
 return serialize_metadata(out),dict(target=FUNCTION,body_words=55,slot_words=58,frame=0,guards=0,old_symbol_bytes=20,new_symbol_bytes=220,strict_exclusions=0,metadata_groups=4,metadata_records=13)

def check_image(before,actual,truth):
 if actual!=predict(before,truth)[0]:raise ValueError('Signed interpolation entire image differs')

def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 if actual!=(output/'first-linked.elf').read_bytes():raise ValueError('Signed interpolation production differs from private link')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact'] or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Signed interpolation protected data changed')
 q=json.loads((output/'private-owner-image-v11.json').read_text());q.update(private_only=False,installed=True,matching_credit=1,guest_native_caller_gates_pending=False,protected_data=data,actual_Make_literal_image_equal=True)
 (output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q

"""Closed symbol/string ordering changes from the newly referenced constants."""
from collections import Counter
import struct
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, read_c_string

SERIALIZATION = (
    (('D_8009900C', 'D_800A72AC', 'D_800A330C'), (1, 2, 0)),
    (('D_80099014', 'D_80090128'), (1, 0)),
    (('D_80099010', 'D_8009E540', 'D_800A72B0', 'D_800A3310'), (1, 2, 3, 0)),
    (('.L150320B4_game_data', 'func_150238D0', 'D_8009E690', 'D_8009EB80'), (2, 3, 0, 1)),
)

def serialize_metadata(image):
    before = bytes(image)
    rows = list(symbol_rows(before))
    h = ELF_HEADER.unpack_from(before)
    sections = list(SECTION_HEADER.iter_unpack(before[h[6]:h[6]+h[11]*h[12]]))
    labels = sections[h[13]]
    labels = before[labels[4]:labels[4]+labels[5]]
    strings, = [s for s in sections if read_c_string(labels, s[0]) == '.strtab']
    out = bytearray(before)
    permitted = set()
    for names, order in SERIALIZATION:
        group = [next(v for v in rows if v[1] == n) for n in names]
        assert len(set(names)) == len(order) and sorted(order) == list(range(len(names)))
        assert [v[0] for v in group] == list(range(group[0][0], group[0][0]+16*len(group), 16))
        offset = group[0][2][0]
        original = b''.join(n.encode()+b'\0' for n in names)
        at = strings[4]+offset
        assert before[at:at+len(original)] == original
        assert [(v[0],v[1]) for v in rows if offset <= v[2][0] < offset+len(original)] == [(v[0],v[1]) for v in group]
        out[at:at+len(original)] = b''.join(names[i].encode()+b'\0' for i in order)
        for destination, i in zip(group, order):
            fields = list(group[i][2])
            fields[0] = offset
            struct.pack_into('>IIIBBH', out, destination[0], *fields)
            offset += len(names[i])+1
        permitted.update(range(group[0][0], group[-1][0]+16))
        permitted.update(range(at, at+len(original)))
    after = bytes(out)
    assert Counter((n,*f[1:]) for _,n,f,_ in rows) == Counter((n,*f[1:]) for _,n,f,_ in symbol_rows(after))
    assert len(before) == len(after) and all(i in permitted for i,(a,b) in enumerate(zip(before,after)) if a != b)
    return after


HEADERS='#include <ultra64.h>\n#include "functions.h"\nextern u16 D_80098E00[256];\nextern f32 D_8009900C,D_80099010,D_80099014;\n'
SELECTED='f32 func_150488C8(f32 input) {\n    f32 base;\n    f32 scaled;\n    s32 index;\n    f32 next;\n    f32 fraction;\n    scaled = fabsf(input) * D_8009900C;\n    index = scaled;\n    fraction = scaled - (f32)index;\n    base = D_80098E00[index];\n    next = (index < 255) ? D_80098E00[index + 1] : D_80099010;\n    base = ((((next - base) * fraction) + base) * D_80099014) / 65536.0f;\n    if (input < 0.0f) {\n        return -base;\n    }\n    return base;\n}\n'
BINDINGS={0: [('R_MIPS_HI16', 'D_8009900C')], 4: [('R_MIPS_LO16', 'D_8009900C')], 12: [('R_MIPS_HI16', 'D_80098E00')], 20: [('R_MIPS_LO16', 'D_80098E00')], 140: [('R_MIPS_HI16', 'D_80099010')], 144: [('R_MIPS_LO16', 'D_80099010')], 152: [('R_MIPS_HI16', 'D_80099014')], 156: [('R_MIPS_LO16', 'D_80099014')]}
SNAPSHOT_SHA='053308ce37b404affe14c5998c8056f965f61b91aab04d2b4ae80b5adafe55cd'
ARTIFACT_SHA='8aa2a47bdc8e5dd79db57a89d87f8390e5fd7c2df3370cd86bc988a4730a36ee'
