"""Resource header scan: semantic C, bounded roles and strict whole-image accounting."""
from pathlib import Path
from collections import Counter
import hashlib,json,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_actor_transform_position_match import check_owner_diagnostics
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,OWNER='func_15003570','game_305D0'
ENTRY,ROM,BODY,SIZE=0x15003570,0x30A20,248,248
SOURCE='conker/src/game_305D0.c'
OBJECT='conker/build/src/game_305D0.c.o'
BUILD='conker/build/game-resource-header-scan-15003570-match'
BASELINE='d84330cbf2a3b42de99a5866420c428b00e42a6735f43a6601c76e4235255996'
sha=lambda data:hashlib.sha256(data).hexdigest()
HEADERS='#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\nvoid *allocate_memory(s32,s32,s32,s32);\nextern u8 D_1A37E0;\nextern u16 D_800BC444;\n'
SELECTED='void func_15003570(void) {\n    u8 *buffer;\n    u8 *header;\n    u16 *length;\n    u16 *extent;\n    u16 *end;\n    u32 source;\n    u32 skip;\n    u32 value;\n    u32 amount;\n\n    buffer = allocate_memory(16, 1, 2, 0);\n    source = (u32)&D_1A37E0;\n    length = D_80091D20;\n    extent = D_800B87A0;\n    end = D_800B87A0 + 7762;\n    do {\n        if (source & 1) {\n            source--;\n            skip = 1;\n        } else {\n            skip = 0;\n        }\n        func_10004514(source, buffer, 16, 1);\n        header = buffer + skip;\n        value = ((u32)header[0] << 24) + ((u32)header[1] << 16) + ((u32)header[2] << 8) + header[3];\n        amount = *length + skip;\n        *extent++ = value;\n        length++;\n        source += amount;\n    } while (extent != end);\n    func_10004074(buffer);\n}\n'
BEFORE_BODY='void func_15003570(void) {\n    u8 *buffer;\n    u8 *header;\n    u16 *length = D_80091D20;\n    u16 *extent = D_800B87A0;\n    u16 *end = D_800B87A0 + 7762;\n    u32 source;\n    u32 skip;\n    u32 value;\n    u32 amount;\n\n    buffer = allocate_memory(16, 1, 2, 0);\n    source = (u32)&D_1A37E0;\n    do {\n        skip = source & 1;\n        source -= skip;\n        func_10004514(source, buffer, 16, 1);\n        header = buffer + skip;\n        value = ((u32)header[0] << 24) + header[3]\n              + ((u32)header[1] << 16) + ((u32)header[2] << 8);\n        amount = *length + skip;\n        *extent++ = value;\n        length++;\n        source += amount;\n    } while (extent != end);\n    func_10004074(buffer);\n}'
RAW_SHA='6c9da53b1f6b2b86f923c1b34b061e45a97035ddc42b580b4eef5a02f4b8447a'
BINDINGS={44: [('R_MIPS_26', 'allocate_memory')], 52: [('R_MIPS_HI16', 'D_1A37E0')], 72: [('R_MIPS_LO16', 'D_1A37E0')], 56: [('R_MIPS_HI16', 'D_80091D20')], 76: [('R_MIPS_LO16', 'D_80091D20')], 60: [('R_MIPS_HI16', 'D_800B87A0')], 80: [('R_MIPS_LO16', 'D_800B87A0')], 64: [('R_MIPS_HI16', 'D_800B87A0')], 84: [('R_MIPS_LO16', 'D_800B87A0')], 124: [('R_MIPS_26', 'func_10004514')], 204: [('R_MIPS_26', 'func_10004074')]}
NORMALIZED_BINDINGS={44: [('R_MIPS_26', 'allocate_memory')], 52: [('R_MIPS_HI16', 'D_1A37E0')], 56: [('R_MIPS_HI16', 'D_80091D20')], 60: [('R_MIPS_HI16', 'D_800B87A0')], 64: [('R_MIPS_HI16', 'D_800BC444')], 72: [('R_MIPS_LO16', 'D_1A37E0')], 76: [('R_MIPS_LO16', 'D_800BC444')], 80: [('R_MIPS_LO16', 'D_800B87A0')], 84: [('R_MIPS_LO16', 'D_80091D20')], 124: [('R_MIPS_26', 'func_10004514')], 204: [('R_MIPS_26', 'func_10004074')]}
NEW_GUARDS=[[56, 1007878144, 1007812608, 'R_MIPS_HI16:D_80091D20', 'R_MIPS_HI16:D_80091D20', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [60, 1007812608, 1007878144, 'R_MIPS_HI16:D_800B87A0', 'R_MIPS_HI16:D_800B87A0', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [64, 1008009216, 1008009216, 'R_MIPS_HI16:D_800B87A0', 'R_MIPS_HI16:D_800BC444', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [76, 645070848, 649396224, 'R_MIPS_LO16:D_80091D20', 'R_MIPS_LO16:D_800BC444', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [80, 642908160, 645070848, 'R_MIPS_LO16:D_800B87A0', 'R_MIPS_LO16:D_800B87A0', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [84, 649411748, 642908160, 'R_MIPS_LO16:D_800B87A0', 'R_MIPS_LO16:D_80091D20', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [132, 43063329, 36966433, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [136, 2423783424, 2421686272, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [140, 2423193603, 2421096451, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [144, 2422800385, 2420703233, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [148, 2422996994, 2420899842, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [152, 2523791360, 2521694208, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [176, 23928865, 645070850, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [180, 642908162, 23926817, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [184, 30484513, 30523425, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [188, 2789539838, 642908162, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [192, 645070850, 2791571454, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [196, 374734820, 376831972, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule'], [200, 33914913, 35160097, '-', '-', 'Restore bounded metadata cursor/temporary roles and independent address or integer schedule']]
GUARD_ROWS=b'game_305D0,func_15003570,0x038,0x3C130000,0x3C120000,R_MIPS_HI16:D_80091D20,R_MIPS_HI16:D_80091D20,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x03C,0x3C120000,0x3C130000,R_MIPS_HI16:D_800B87A0,R_MIPS_HI16:D_800B87A0,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x040,0x3C150000,0x3C150000,R_MIPS_HI16:D_800B87A0,R_MIPS_HI16:D_800BC444,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x04C,0x26730000,0x26B50000,R_MIPS_LO16:D_80091D20,R_MIPS_LO16:D_800BC444,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x050,0x26520000,0x26730000,R_MIPS_LO16:D_800B87A0,R_MIPS_LO16:D_800B87A0,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x054,0x26B53CA4,0x26520000,R_MIPS_LO16:D_800B87A0,R_MIPS_LO16:D_80091D20,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x084,0x02911821,0x02341021,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x088,0x90780000,0x90580000,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x08C,0x906F0003,0x904F0003,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x090,0x90690001,0x90490001,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x094,0x906C0002,0x904C0002,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x098,0x966E0000,0x964E0000,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x0B0,0x016D2021,0x26730002,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x0B4,0x26520002,0x016D1821,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x0B8,0x01D12821,0x01D1C021,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x0BC,0xA644FFFE,0x26520002,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x0C0,0x26730002,0xA663FFFE,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x0C4,0x1655FFE4,0x1675FFE4,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\ngame_305D0,func_15003570,0x0C8,0x02058021,0x02188021,-,-,Restore bounded metadata cursor/temporary roles and independent address or integer schedule,,,false\n'
SNAPSHOT_SHA='ecfab3c31135a0922f0f00084bc2fc6eba20d74902c3e900706990ba87e58bc8'
ARTIFACT_SHA='2fbdfd03a907dd48dc0010200751217ec03d5162865602dc1a60a5be4e000f95'

def payload(obj):return function_payload(obj,FUNCTION)
def checked_payload(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Metadata scan payload/bindings changed')
 return raw,bindings
def recovered_owner(before):
 lo,hi=function_span(before,FUNCTION)
 if before[lo:hi]!=BEFORE_BODY:raise ValueError('Metadata scan predecessor changed')
 return before[:lo]+'/* Read each aligned resource header and publish its truncated extent. */\n'+SELECTED.rstrip()+before[hi:]
def recovered_guards(before):
 if not before.endswith(b'\n')or b',func_15003570,'in before:raise ValueError('Metadata guard predecessor changed')
 return before+GUARD_ROWS

def normalize_linked_words(words):
 if len(words)!=62 or words[0]!=0x27BDFFD0:raise ValueError("Metadata shape changed")
 new=list(words)
 for at in range(0x34,0xCC,4):
  w=new[at//4];op=w>>26
  fields=(21,16,11)if op==0 else(16,)if op==15 else(21,16)if op in(4,5,9,12,36,37,41)else()if op==3 else None
  assert fields is not None,hex(w)
  for shift in fields:
   reg=w>>shift&31
   if reg in(18,19):w=(w&~(31<<shift))|((37-reg)<<shift)
  new[at//4]=w
 # Restore the anonymous header, assembled value and captured advance roles.
 w=new[0x84//4];assert w&63==33 and(w>>11&31)==3 and(w>>21&31,w>>16&31)==(20,17)
 new[0x84//4]=(w&~((31<<21)|(31<<16)|(31<<11)))|(17<<21)|(20<<16)|(2<<11)
 for at in(0x88,0x8C,0x90,0x94):
  w=new[at//4];assert w>>21&31==3;new[at//4]=(w&~(31<<21))|(2<<21)
 assert new[0xB0//4]>>11&31==4;new[0xB0//4]=(new[0xB0//4]&~(31<<11))|(3<<11)
 assert new[0xB8//4]>>11&31==5;new[0xB8//4]=(new[0xB8//4]&~(31<<11))|(24<<11)
 assert new[0xBC//4]>>16&31==4;new[0xBC//4]=(new[0xBC//4]&~(31<<16))|(3<<16)
 assert new[0xC8//4]>>16&31==5;new[0xC8//4]=(new[0xC8//4]&~(31<<16))|(24<<16)
 # All swaps exchange independent operations; there are no inserted/deleted words.
 for a,b in((0x4C,0x54),(0xB0,0xB4),(0xBC,0xC0)):
  new[a//4],new[b//4]=new[b//4],new[a//4]
 return new

def normalized_payload(raw,bindings):
 checked_payload(raw,bindings);words=normalize_linked_words(struct.unpack('>62I',raw));refs={at:list(v)for at,v in bindings.items()}
 refs[0x4C],refs[0x54]=refs[0x54],refs[0x4C]
 if words[0x4C//4]&65535!=15524 or refs[0x40]!=[('R_MIPS_HI16','D_800B87A0')]or refs[0x4C]!=[('R_MIPS_LO16','D_800B87A0')]:raise ValueError('Metadata endpoint addend/bindings changed')
 words[0x4C//4]&=0xFFFF0000;refs[0x40]=[('R_MIPS_HI16','D_800BC444')];refs[0x4C]=[('R_MIPS_LO16','D_800BC444')]
 if refs!=NORMALIZED_BINDINGS:raise ValueError('Metadata final bindings changed')
 return struct.pack('>62I',*words),refs
import struct
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string
def serialize_metadata(image):
 before=bytes(image);rows=list(symbol_rows(before));names=('n_alSynFreeVoice','D_8009E694')
 a=next(v for v in rows if v[1]==names[0]);b=next(v for v in rows if v[1]==names[1])
 assert b[0]==a[0]+16 and b[2][0]==a[2][0]+len(names[0])+1
 h=ELF_HEADER.unpack_from(before);sections=list(SECTION_HEADER.iter_unpack(before[h[6]:h[6]+h[11]*h[12]]));labels=sections[h[13]];labels=before[labels[4]:labels[4]+labels[5]]
 strings,= [s for s in sections if read_c_string(labels,s[0])=='.strtab'];base=a[2][0];first=names[0].encode()+b'\0';second=names[1].encode()+b'\0';at=strings[4]+base
 assert before[at:at+len(first)+len(second)]==first+second
 assert [(v[0],v[1])for v in rows if base<=v[2][0]<base+len(first)+len(second)]==[(a[0],a[1]),(b[0],b[1])]
 out=bytearray(before);out[at:at+len(first)+len(second)]=second+first
 af,bf=list(a[2]),list(b[2]);bf[0]=base;af[0]=base+len(second)
 struct.pack_into('>IIIBBH',out,a[0],*bf);struct.pack_into('>IIIBBH',out,b[0],*af)
 after=bytes(out);fresh=list(symbol_rows(after))
 assert Counter((n,*f[1:])for _,n,f,_ in rows)==Counter((n,*f[1:])for _,n,f,_ in fresh)
 permitted=set(range(a[0],b[0]+16))|set(range(at,at+len(first)+len(second)))
 assert len(before)==len(after)and all(i in permitted for i,(x,y)in enumerate(zip(before,after))if x!=y)
 return after

def snapshot(output):
 data=(output/'input-snapshot.json').read_bytes()
 if sha(data)!=SNAPSHOT_SHA:raise ValueError('Metadata scan snapshot changed')
 values={}
 for n,h in json.loads(data)['INPUTS'].items():
  data=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(data)!=h:raise ValueError('Metadata scan frozen input changed: '+n)
  values[n]=data
 return values
def verify_prepared(output):
 data=(output/'prepared-artifacts.json').read_bytes()
 if sha(data)!=ARTIFACT_SHA:raise ValueError('Metadata scan prepared index changed')
 for n,h in json.loads(data).items():
  if sha((output/n).read_bytes())!=h:raise ValueError('Metadata scan prepared artifact changed: '+n)
 return True

def expected_map(output):
 data=(output/'first-linked.map').read_bytes();private=b'build/game-resource-header-scan-15003570-match/make-shadow/src/game_305D0.c.o'
 if data.count(private)!=9:raise ValueError('Metadata scan map owner count changed')
 data=data.replace(private,b'build/src/game_305D0.c.o');private=b'build/game-resource-header-scan-15003570-match/first-linked.elf'
 if data.count(private)!=1:raise ValueError('Metadata scan map output count changed')
 return data.replace(private,b'build/conker.us.elf')

def check_inputs(root,output,installed=False):
 values=snapshot(output);changes={}
 if installed:changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/retail_word_patches.us.csv':recovered_guards(values['conker/retail_word_patches.us.csv']),'conker/build/conker.us.elf':predict(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])[0],'conker/build/conker.us.map':expected_map(output)}
 for n,data in values.items():
  if(root/n).read_bytes()!=changes.get(n,data):raise ValueError('Metadata scan live input changed: '+n)
 return values
def verify_group(image):
 symbols={n:f[1]for _,n,f,_ in symbol_rows(image)}
 if symbols['D_800BC444']!=symbols['D_800B87A0']+15524:raise ValueError('Metadata extent endpoint geometry changed')
 return True
def predict(before,truth):
 if sha(before)!=BASELINE or len(truth)!=SIZE:raise ValueError('Metadata image predecessor or slot changed')
 verify_group(before);row,=[v for v in symbol_rows(before)if v[1]==FUNCTION]
 if row[2][1:3]!=(ENTRY,232):raise ValueError('Metadata predecessor extent changed')
 out=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);out[at:at+SIZE]=truth;struct.pack_into('>I',out,row[0]+8,BODY);result=serialize_metadata(out)
 return result,dict(target=FUNCTION,target_words=62,frame=48,guards=19,old_symbol_bytes=232,new_symbol_bytes=248,strict_exclusions=0,metadata_order_pair=['n_alSynFreeVoice','D_8009E694'])
def check_image(before,actual,truth):
 if actual!=predict(before,truth)[0]:raise ValueError('Metadata entire image prediction differs')
def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);actual=(root/'conker/build/conker.us.elf').read_bytes()
 check_image(values['conker/build/conker.us.elf'],actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
 if actual!=(output/'first-linked.elf').read_bytes():raise ValueError('Metadata production differs from private link')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if not data['exact']or data['bytes']!=189088 or data['owner_count']!=720:raise ValueError('Metadata protected data changed')
 q=json.loads((output/'private-owner-image-v15.json').read_text());q.update(private_only=False,installed=True,matching_credit=1,guest_native_caller_gates_pending=False,protected_data=data,actual_Make_literal_image_equal=True)
 (output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
