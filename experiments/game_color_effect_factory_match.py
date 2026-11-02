"""Color-effect packet factory: direct-exact C, private extent, caller ABI and full-image qualification."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions

BUILD='conker/build/game-color-effect-factory-15152874-match'
BASELINE='6ae9f23a08f217174eaf205953426224966321f4d8769900dfd599bb7417dd4e'
LINKED='f459bd92845118fe65e9615347275c6b6a08821b21558c9546b87922a6e88b20'
FUNCTION='func_15152874';OWNER='generated_17CAF0';ENTRY=0x15152874;ROM=0x17FD24;SIZE=584
SPECS=((FUNCTION,OWNER,ENTRY,ROM),)
RAW_SHA='cfcd734f0d79c98d7874b2f9b24d5eb39629d15db87ed3a9efc7831ff8c5f4f4'
BINDINGS={int(k):[tuple(x) for x in v] for k,v in json.loads("{\"60\":[[\"R_MIPS_26\",\"func_150ADA20\"]],\"164\":[[\"R_MIPS_26\",\"func_150ADA20\"]],\"172\":[[\"R_MIPS_26\",\"func_150ADA20\"]],\"180\":[[\"R_MIPS_26\",\"func_150ADA68\"]],\"300\":[[\"R_MIPS_26\",\"func_15143794\"]],\"308\":[[\"R_MIPS_26\",\"func_150ADA68\"]],\"332\":[[\"R_MIPS_26\",\"func_150ADA20\"]],\"380\":[[\"R_MIPS_26\",\"func_150ADA68\"]],\"404\":[[\"R_MIPS_26\",\"func_150ADA68\"]],\"420\":[[\"R_MIPS_HI16\",\"D_8008AC60\"]],\"468\":[[\"R_MIPS_LO16\",\"D_8008AC60\"]],\"516\":[[\"R_MIPS_26\",\"func_150CCEB0\"]]}").items()}
METADATA_GROUPS=((2952024,('D_8008AC60','D_8009EE78'),(1,0)),)
HEADERS="#include <ultra64.h>\ntypedef struct { f32 x, y, z; } EffectPosition;\ntypedef struct {\n    s32 baseCount, countRange;\n    EffectPosition position;\n    s16 firstBase, firstRange, secondBase, secondRange;\n    f32 radiusBase, radiusRange, field24;\n    f32 scaleBase, scaleRange;\n    s8 colorSelector;\n    u8 padding31;\n    s16 lifetimeBase, lifetimeRange;\n    u8 padding36[2];\n    f32 field38, field3C, field40, field44, field48;\n} ColorEffectInput;\ntypedef struct {\n    EffectPosition position;\n    f32 direction[3];\n    f32 field18, scale;\n    u8 colors[4];\n    s32 lifetime;\n    f32 field28, field2C, field30;\n    u8 privateTail34[4];\n} ColorEffectPacket;\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid func_15143794(s16, s16, f32, f32 *);\ns32 func_150CCEB0(ColorEffectPacket *, u8, u8);\nextern void (*D_8008AC60[])(u8 *);\n\r\n"
SELECTED="void func_15152874(ColorEffectInput *input, u8 mode, s32 extra) {\n    ColorEffectPacket packet;\n    u32 remaining;\n    u32 first, second;\n    first = (u32)func_150ADA20();\n    remaining = first % ((u32)input->countRange + 1U) + (u32)input->baseCount;\n    packet.position = input->position;\n    packet.field18 = input->field24;\n    packet.field30 = input->field48;\n    while (remaining != 0) {\n        first = (u32)func_150ADA20();\n        second = (u32)func_150ADA20();\n        func_15143794((s16)(first % (u32)(input->firstRange + 1) + input->firstBase),\n                      (s16)(second % (u32)(input->secondRange + 1) + input->secondBase),\n                      func_150ADA68() * input->radiusRange + input->radiusBase, packet.direction);\n        packet.scale = func_150ADA68() * input->scaleRange + input->scaleBase;\n        first = (u32)func_150ADA20();\n        packet.lifetime = first % (u32)(input->lifetimeRange + 1) + input->lifetimeBase;\n        packet.field28 = func_150ADA68() * input->field40 + input->field38;\n        packet.field2C = func_150ADA68() * input->field44 + input->field3C;\n        if (input->colorSelector != -1) {\n            D_8008AC60[input->colorSelector](packet.colors);\n        } else {\n            packet.colors[0] = 255;\n            packet.colors[1] = 255;\n            packet.colors[2] = 255;\n            packet.colors[3] = 255;\n        }\n        func_150CCEB0(&packet, (u8)mode, (u8)extra);\n        remaining--;\n    }\n}\n\r\n"
sha=lambda data:hashlib.sha256(data).hexdigest()

def checked_payload(raw,bindings):
 if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Color-effect factory payload or bindings changed')
 return raw,bindings

def recovered_owner(before):
 before=before.replace('\r\n','\n')
 lo,hi=function_span(before,FUNCTION)
 if before[lo:hi]!='s32 '+FUNCTION+'() {\n    return 0;\n}':raise ValueError('Color-effect factory predecessor changed')
 header=HEADERS.replace('\r','').replace('#include <ultra64.h>\n','').rstrip()+'\n'
 return before[:lo]+header+'/* Emit randomized color-effect packets from live input fields using the complete private packet extent. */\n'+SELECTED.replace('\r','').rstrip()+before[hi:]

def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Color-effect factory named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Color-effect factory symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Color-effect factory metadata length changed')

def predict(before,rom):
 if sha(before)!=BASELINE:raise ValueError('Color-effect factory image predecessor changed')
 out=bytearray(before);row,=[r for r in symbol_rows(before)if r[1]==FUNCTION]
 if row[2][1:3]!=(ENTRY,12):raise ValueError('Color-effect factory predecessor extent changed')
 truth=rom[ROM:ROM+SIZE]
 if len(truth)!=SIZE:raise ValueError('Color-effect factory retail slot missing')
 at=elf_slot_offset(before,ENTRY,SIZE);out[at:at+SIZE]=truth;struct.pack_into('>I',out,row[0]+8,SIZE);reorder_metadata(before,out);return bytes(out)

def check_image(before,actual,rom):
 if actual!=predict(before,rom):raise ValueError('Color-effect factory entire image differs')

def expected_map(output):
 data=(output/'private-joint-linked.map').read_bytes();private=(BUILD.removeprefix('conker/')+'/make-shadow-'+OWNER+'/src/game/'+OWNER+'.c.o').encode()
 if data.count(private)!=9:raise ValueError('Color-effect factory map owner count changed')
 data=data.replace(private,('build/src/game/'+OWNER+'.c.o').encode());private=(BUILD.removeprefix('conker/')+'/private-joint-linked.elf').encode()
 if data.count(private)!=1:raise ValueError('Color-effect factory map output changed')
 return data.replace(private,b'build/conker.us.elf')

def verify_prepared(output):
 q=json.loads((output/'private-layout-v4.json').read_text())
 if (q['words'],q['frame'],q['guards'],q['raw_SHA256'])!=(146,144,0,RAW_SHA) or len(q['layouts'])!=3:raise ValueError('Color-effect factory layout receipt changed')
 if payload(output/'selected-final.o',FUNCTION)!=payload(output/('original-'+FUNCTION+'.o'),FUNCTION):raise ValueError('Color-effect direct-exact payload changed')
 for name in ('private-guest-v5.json','private-native-v1.json','private-caller-v1.json','private-owner-image-v17.json','qualified-'+OWNER+'.o','private-joint-linked.elf'):
  if not(output/name).is_file():raise ValueError('Color-effect prepared artifact missing: '+name)
 return True

def check_inputs(root,output,installed=False):
 verify_prepared(output)
 baseline={
  'conker/src/game/'+OWNER+'.c':(output/'before-conker_src_game_generated_17CAF0.c').read_bytes(),
  'conker/build/src/game/'+OWNER+'.c.o':(output/'before-conker_build_src_game_generated_17CAF0.c.o').read_bytes(),
  'conker/build/conker.us.elf':(output/'before-conker_build_conker.us.elf').read_bytes(),
  'conker/build/conker.us.map':(output/'before-conker_build_conker.us.map').read_bytes(),
  'conker/retail_word_patches.us.csv':(output/'before-conker_retail_word_patches.us.csv').read_bytes(),
 }
 changes={}
 if installed:
  changes['conker/src/game/'+OWNER+'.c']=(output/('proposed-'+OWNER+'.c')).read_bytes()
  changes['conker/build/src/game/'+OWNER+'.c.o']=(output/('qualified-'+OWNER+'.o')).read_bytes()
  changes['conker/build/conker.us.elf']=predict(baseline['conker/build/conker.us.elf'],(root/'conker/conker.us.bin').read_bytes())
  changes['conker/build/conker.us.map']=expected_map(output)
  changes['conker/retail_word_patches.us.csv']=(output/'proposed-guards.csv').read_bytes()
 for name,data in baseline.items():
  if (root/name).read_bytes()!=changes.get(name,data):raise ValueError('Color-effect factory live input changed: '+name)
 return baseline

def audit(root,output,installed=False):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,installed);actual=((root/'conker/build/conker.us.elf')if installed else(output/'private-joint-linked.elf')).read_bytes();rom=(root/'conker/conker.us.bin').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,rom)
 if sha(actual)!=LINKED:raise ValueError('Color-effect factory linked image changed')
 data=audit_layout((root/'conker/build/conker.us.elf')if installed else(output/'private-joint-linked.elf'),root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Color-effect factory protected data changed')
 a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str((root/'conker/build/conker.us.elf')if installed else(output/'private-joint-linked.elf')),'mips-linux-gnu-objdump')
 if a.keys()!=b.keys()or aa!=bb or{n for n in a if a[n]!=b[n]}!={FUNCTION}:raise ValueError('Color-effect factory changed another body')
 targets={FUNCTION};expected=Counter((n,f[1],SIZE if n in targets else f[2],*f[3:])for _,n,f,_ in symbol_rows(values['conker/build/conker.us.elf']))
 if expected!=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual)):raise ValueError('Color-effect factory named definition changed')
 q=json.loads((output/'private-owner-image-v17.json').read_text());q.update(private_only=not installed,installed=installed,matching_credit=1 if installed else 0,protected_data=data)
 if installed:(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n')
 return q
