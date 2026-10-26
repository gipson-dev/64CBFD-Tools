"""Complete menu reset C and checked bounded-loop/byte-forwarding normalization."""
import csv,hashlib,io,json,struct
P = {
  "function": "func_15007778",
  "owner": "game_33990",
  "source": "conker/src/game_33990.c",
  "object": "conker/build/src/game_33990.c.o",
  "asm": "conker/asm/nonmatchings/game_33990/func_15007778.s",
  "entry": 352352120,
  "ROM": 216104,
  "body_bytes": 176,
  "slot_bytes": 184,
  "RAW_SHA": "e18db73c61fa12000aa20d6b28ef6dfa2b688352e1e9165ca6aea5bb6d6bec85",
  "RAW_BINDINGS": {
    "0": [
      [
        "R_MIPS_HI16",
        "D_800BE3F8"
      ]
    ],
    "4": [
      [
        "R_MIPS_LO16",
        "D_800BE3F8"
      ]
    ],
    "36": [
      [
        "R_MIPS_HI16",
        "D_800BE3DC"
      ]
    ],
    "40": [
      [
        "R_MIPS_LO16",
        "D_800BE3DC"
      ]
    ],
    "44": [
      [
        "R_MIPS_HI16",
        "D_800BE3DE"
      ]
    ],
    "48": [
      [
        "R_MIPS_LO16",
        "D_800BE3DE"
      ]
    ],
    "52": [
      [
        "R_MIPS_HI16",
        "D_80082BC0"
      ]
    ],
    "60": [
      [
        "R_MIPS_HI16",
        "D_800D2E4C"
      ]
    ],
    "64": [
      [
        "R_MIPS_LO16",
        "D_80082BC0"
      ]
    ],
    "72": [
      [
        "R_MIPS_LO16",
        "D_800D2E4C"
      ]
    ],
    "100": [
      [
        "R_MIPS_HI16",
        "D_800D2E60"
      ]
    ],
    "104": [
      [
        "R_MIPS_HI16",
        "D_800D2E60"
      ]
    ],
    "108": [
      [
        "R_MIPS_LO16",
        "D_800D2E60"
      ]
    ],
    "112": [
      [
        "R_MIPS_LO16",
        "D_800D2E60"
      ]
    ],
    "132": [
      [
        "R_MIPS_HI16",
        "D_800BE3D8"
      ]
    ],
    "136": [
      [
        "R_MIPS_LO16",
        "D_800BE3D8"
      ]
    ]
  },
  "SNAPSHOT_SHA": "9a9ed6ce70f89e6463b058b22481854eed8d169c1d34bb260f001f2773010f77",
  "BEFORE_ELF_SHA": "40663e322b4c401cb94a4a81a703498310b00346da0bd4444beec9c155d04e9d",
  "BEFORE_OBJECT_SHA": "42b9959badba9b858631d8b39c20fef7290f8a7286f280497f9bb703d133b6ef",
  "GUARD_SHA": "a72b7892470dbf90e90aeb998c4675994fc707941ee76938bdc2ebdfa937cf83"
}
P["selected"] = r"""/* Reset inline record sentinels, the pointed-to bytes and local selection bytes. */
void func_15007778(void) {
    s32 i;
    u8 *cursor;

    D_800BE3F8.unk8 = -1;
    D_800BE3F8.unk18 = -1;
    D_800BE3F8.unk28 = -1;
    D_800BE3F8.unkE = -1;
    D_800BE3F8.unk1E = -1;
    D_800BE3F8.unk2E = -1;
    D_800BE3DC = -1;
    D_800BE3DE = 0;
    D_80082BC0 = 1;

    i = 0;
    for (;;) {
        ((u8 *)D_800D2E4C)[i++] = 0;
        if (i >= 27) {
            break;
        }
    }

    cursor = D_800D2E60;
    do {
        *cursor++ = 0;
    } while (cursor < D_800D2E60 + 9);

    D_800BE3D8.byte0 = D_800BE3D8.byte1 = D_800BE3D8.byte2 = D_800BE3D8.byte3 = -1;
}
"""
P["type_definition"] = r"""/* Four adjacent signed menu-selection sentinels at D_800BE3D8. */
typedef struct {
    s8 byte0;
    s8 byte1;
    s8 byte2;
    s8 byte3;
} MenuResetSentinels;"""
P["raw_header_prefix"] = r"""#include <ultra64.h>

#include "functions.h"
#include "variables.h"
"""

FUNCTION,OWNER,SOURCE,OBJECT,ASM=(P[n]for n in('function','owner','source','object','asm'))
ENTRY,ROM,BODY,SIZE=P['entry'],P['ROM'],P['body_bytes'],P['slot_bytes']
BUILD='conker/build/game-menu-state-reset-match'
SELECTED,TYPE_DEFINITION,HEADERS=P['selected'],P['type_definition'],P['raw_header_prefix']
RAW_BINDINGS={int(k):[tuple(x)for x in v]for k,v in P['RAW_BINDINGS'].items()}
ALIASES={'D_800D2E69':('D_800D2E60',9),'D_800BE3DB':('D_800BE3D8',3),'D_800BE3DA':('D_800BE3D8',2),'D_800BE3D9':('D_800BE3D8',1)}
sha=lambda b:hashlib.sha256(b).hexdigest()

def rt(w):return(w>>16)&31
def rs(w):return(w>>21)&31
def with_rt(w,n):return(w&~(31<<16))|(n<<16)
def with_regs(w,a,b):return(w&~((31<<21)|(31<<16)))|(a<<21)|(b<<16)

def normalized(raw,bindings):
 if len(raw)!=BODY or sha(raw)!=P['RAW_SHA']or bindings!=RAW_BINDINGS:raise ValueError('Reset raw body/bindings changed')
 w=list(struct.unpack('>44I',raw));f=list(w);rel={k:list(v)for k,v in bindings.items()}
 if w[17]!=0x00001025 or w[19]>>26!=9 or rs(w[19])!=0 or rt(w[19])!=5 or(w[19]&65535)!=27:raise ValueError('Reset bounded loop changed')
 if w[20:25]!=[0x8C6F0000,0x01E2C021,0x24420001,0x1445FFFC,0xA3000000]:raise ValueError('Reset byte-clear access order changed')
 # i starts at zero, advances once after each byte address is captured, and
 # reaches 27 without overflow. On this exact interval BNE(i,27) and i<27
 # select the same 27 visits. Preserve the pointer reload and store delay slot.
 f[17],f[18]=w[18],w[17];rel[68]=rel.pop(72)
 f[19:22]=w[20:23]
 limit=w[19]&65535;f[22]=(10<<26)|(2<<21)|(1<<16)|limit
 f[23]=(5<<26)|(1<<21)|((19-(23+1))&65535)
 # Swap the two pointer roles and capture the known nine-byte end through its
 # existing linker alias. Separate named HI/LO pairs preserve carry rebases.
 if(w[27]&65535,w[28]&65535)!=(0,9):raise ValueError('Reset nine-byte end changed')
 f[25]=with_rt(w[25],3);f[26]=with_rt(w[26],2)
 f[27]=with_regs(w[28],2,2)&~65535;f[28]=with_regs(w[27],3,3)
 rel[104]=[('R_MIPS_HI16','D_800D2E69')];rel[108]=[('R_MIPS_LO16','D_800D2E69')]
 f[29]=with_regs(w[29],3,3);f[30]=(w[30]&~((31<<21)|(31<<16)))|(3<<21)|(2<<16);f[32]=(w[32]&~(31<<21))|(3<<21)
 # The first high-byte store receives the invariant -1 from A0. Each signed
 # reload reads exactly the byte just stored, so all four chain values are -1.
 # Forward those values, retain high-to-low stores, and allocate four rematerialized
 # temporaries from the observed T9,T0,T1 sequence followed by T2.
 if w[2]!=0x2404FFFF or(w[34]&65535)!=0:raise ValueError('Reset negative sentinel producer changed')
 stores=[35,37,39,41];loads=[36,38,40];offsets=[3,2,1,0]
 prior=4;temps=[]
 for index,off in zip(stores,offsets):
  q=w[index]
  if q>>26!=40 or rs(q)!=2 or rt(q)!=prior or(q&65535)!=off:raise ValueError('Reset signed store chain changed')
  if index!=41:
   load=w[index+1]
   if load>>26!=32 or rs(load)!=2 or(load&65535)!=off:raise ValueError('Reset forwarding load changed')
   prior=rt(load);temps.append(prior)
 if temps!=[25,8,9]:raise ValueError('Reset temporary cycle changed')
 temps.append(temps[-1]+1);f[33]=with_rt(w[33],1)
 rel[132]=[('R_MIPS_HI16','D_800BE3DB')];rel.pop(136)
 for index,temp in zip(range(34,38),temps):f[index]=with_rt(w[2],temp)
 aliases=['D_800BE3DB','D_800BE3DA','D_800BE3D9','D_800BE3D8']
 for index,old,temp,alias in zip(range(38,42),stores,reversed(temps),aliases):
  f[index]=(w[old]&0xFC000000)|(1<<21)|(temp<<16);rel[index*4]=[('R_MIPS_LO16',alias)]
 return struct.pack('>44I',*f),rel

def guard_bytes(before,raw,bindings):
 if sha(before)!=P['GUARD_SHA']:raise ValueError('Reset guard predecessor changed')
 reader=csv.DictReader(io.StringIO(before.decode()));schema=reader.fieldnames
 if any(row['function']==FUNCTION for row in reader):raise ValueError('Reset guards already present')
 fixed,rebased=normalized(raw,bindings);a=struct.unpack('>44I',raw);b=struct.unpack('>44I',fixed)
 stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=schema,lineterminator=chr(13)+chr(10)if before.endswith(bytes([13,10]))else chr(10))
 spec=lambda rows:';'.join(t+':'+n for t,n in rows)or'-'
 for i,(x,y)in enumerate(zip(a,b)):
  old,new=bindings.get(4*i,[]),rebased.get(4*i,[])
  if x==y and old==new:continue
  note=('Derive the closed 27-byte loop test and access schedule'if i<25 else'Derive pointer roles and the named nine-byte end'if i<33 else'Forward four signed -1 stores through their named byte aliases')
  writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(4*i),expected='0x%08X'%x,replacement='0x%08X'%y,expected_relocations=spec(old),replacement_relocations=spec(new),note=note,omit='false'))
 return before+stream.getvalue().encode()

def snapshot(output):
 raw=(output/'input-snapshot.json').read_bytes()
 if sha(raw)!=P['SNAPSHOT_SHA']:raise ValueError('Reset snapshot changed')
 values={}
 for n,wanted in json.loads(raw)['INPUTS'].items():
  b=(output/('before-'+n.replace('/','_'))).read_bytes()
  if sha(b)!=wanted:raise ValueError('Reset frozen input changed: '+n)
  values[n]=b
 if sha(values['conker/build/conker.us.elf'])!=P['BEFORE_ELF_SHA']or sha(values[OBJECT])!=P['BEFORE_OBJECT_SHA']:raise ValueError('Reset predecessor changed')
 return values

def recovered_owner(before):
 old='s32 func_15007778() {'+chr(10)+'    return 0;'+chr(10)+'}'
 if before.count(old)!=1:raise ValueError('Reset placeholder changed')
 after=before.replace('s32 func_15007778();'+chr(10),'').replace('/* Non-matching C placeholders for asm/nonmatchings/game_33990/func_15007778.s. */'+chr(10),'').replace(old,SELECTED.rstrip())
 mark='// NON-MATCHING: should probably start over..'
 if after.count(mark)!=1:raise ValueError('Reset old handoff changed')
 return after[:after.index(mark)].rstrip()+chr(10)

def recovered_headers(values):
 vh=values['conker/include/variables.h'].decode();sh=values['conker/include/structs.h'].decode()
 if vh.count('extern s8   D_800BE3D8;')!=1 or vh.count('extern struct162 *D_800BE3F8;')!=1 or sh.count('} struct162;')!=1:raise ValueError('Reset global declarations changed')
 vh=vh.replace('extern s8   D_800BE3D8;','extern MenuResetSentinels D_800BE3D8;').replace('extern struct162 *D_800BE3F8;','extern struct162 D_800BE3F8;')
 sh=sh.replace('} struct162;','} struct162;'+chr(10)+chr(10)+TYPE_DEFINITION)
 return{'conker/include/variables.h':vh.encode(),'conker/include/structs.h':sh.encode()}

SERIALIZATION=('D_800D2E69','D_80099DF0','D_800AB77C','.L151901CC_game_data','.L15027038_game_data')

def elf_sections(data):
 at=struct.unpack_from('>I',data,32)[0];size,count,index=struct.unpack_from('>3H',data,46)
 row=struct.unpack_from('>10I',data,at+size*index);names=data[row[4]:row[4]+row[5]]
 result={}
 for i in range(count):
  row=struct.unpack_from('>10I',data,at+i*size);start=row[0]
  result[names[start:names.index(0,start)].decode()]=row
 return result

def predicted_image(before,truth):
 from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
 if sha(before)!=P['BEFORE_ELF_SHA']or len(truth)!=SIZE or truth[BODY:]!=bytes(8):raise ValueError('Reset image predecessor/span changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
 all_rows=list(symbol_rows(before));by_name={}
 for off,name,fields,_ in all_rows:
  if name in SERIALIZATION or name==FUNCTION:
   if name in by_name:raise ValueError('Reset metadata name is not unique')
   by_name[name]=(off,fields)
 off,fields=by_name[FUNCTION]
 if fields[1:]!=(ENTRY,12,18,0,5):raise ValueError('Reset predecessor function symbol changed')
 struct.pack_into('>I',result,off+8,BODY)
 positions=[by_name[n][0]for n in SERIALIZATION]
 if positions!=list(range(positions[0],positions[0]+16*5,16)):raise ValueError('Reset closed serialization block moved')
 string_base=elf_sections(before)['.strtab'][4];cursor=by_name[SERIALIZATION[0]][1][0]
 old_block=b''.join(n.encode()+bytes(1)for n in SERIALIZATION)
 if before[string_base+cursor:string_base+cursor+len(old_block)]!=old_block:raise ValueError('Reset symbol-string block changed')
 order=SERIALIZATION[1:]+SERIALIZATION[:1]
 for off,name in zip(positions,order):
  fields=by_name[name][1];struct.pack_into('>IIIBBH',result,off,cursor,*fields[1:]);cursor+=len(name.encode())+1
 start=by_name[SERIALIZATION[0]][1][0]
 result[string_base+start:string_base+start+len(old_block)]=b''.join(n.encode()+bytes(1)for n in order)
 return bytes(result)

def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Reset strict whole image differs')

def make_shadow(root,output):
 import shlex,subprocess
 from tools.experiments.game_actor_state_tick_integration import same_functions
 from tools.experiments.game_four_head_lookup_match import diagnostics
 from tools.pad_generated_object import parse_object
 conker=root/'conker';shadow=output/'make-shadow-target';target=(shadow/OBJECT.removeprefix('conker/build/')).relative_to(conker).as_posix()
 (conker/target).parent.mkdir(parents=True,exist_ok=True)
 p=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
 (output/'make-plan.txt').write_text(p.stdout+p.stderr);commands=[]
 for line in p.stdout.replace('\\'+chr(10),'').splitlines():
  args=shlex.split(line)
  if not args or args[0]=='rm':continue
  if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown legacy Make command: '+repr(args))
  substitutions={SOURCE.removeprefix('conker/'):(output/'raw-after-v2/after-owner.c').relative_to(conker).as_posix(),
                 'retail_word_patches.us.csv':(output/'qualified-guards.csv').relative_to(conker).as_posix()}
  args=[substitutions.get(x,x)for x in args]
  if args[0]=='../ido/ido5.3_recomp/cc':args[1:1]=['-I',str(output/'raw-after-v2')]
  redirect=None
  if '>'in args:
   if args[-2]!='>'or args.count('>')!=1:raise ValueError('Unknown legacy Make redirect')
   redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
  run=subprocess.run(args,cwd=conker,capture_output=True,text=True)
  expected=(output/'after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
  if run.returncode or diagnostics(run.stderr)!=diagnostics(expected)or(redirect is None and run.stdout):raise ValueError(run.stdout+run.stderr)
  if redirect is not None:redirect.write_text(run.stdout)
  commands.append(args)
 obj=conker/target
 if len(commands)!=3 or obj.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Reset actual legacy Make differs')
 count=len(parse_object(output/'after-owner.o')[1])
 if same_functions(output/'after-owner.o',__import__('pathlib').Path(str(obj)+'.compact'),())!=count:raise ValueError('Reset Make compact bodies differ')
 report=dict(commands=3,normal_O2_g3=True,qualified_header_overlay=True,compact_functions_equal=count,
             complete_padded_object_equal=True,GLOBAL_ASM=0,inherited_warnings=p.stderr)
 (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+chr(10))
 return report

def check_inputs(root,output,installed=False):
 values=snapshot(output);truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
 changes={SOURCE:recovered_owner(values[SOURCE].decode()).encode(),
          OBJECT:(output/'qualified-padded.o').read_bytes(),
          'conker/retail_word_patches.us.csv':(output/'qualified-guards.csv').read_bytes(),
          'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],truth),
          **recovered_headers(values)}
 for n,before in values.items():
  if(root/n).read_bytes()!=(changes.get(n,before)if installed else before):raise ValueError('Reset live input differs: '+n)
 return values

def linked_function_audit(before,after):
 from tools.match_progress import load_elf_functions
 a,_,aa=load_elf_functions(str(before),'mips-linux-gnu-objdump')
 b,_,ba=load_elf_functions(str(after),'mips-linux-gnu-objdump')
 if set(a)!=set(b)or aa!=ba:raise ValueError('Reset linked function set/addresses differ')
 changed=[n for n in a if a[n]!=b[n]]
 if changed!=[FUNCTION]:raise ValueError('Reset changed another function: '+repr(changed))
 return dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True)

def audit(root,output):
 from tools.check_game_data_layout import audit_layout
 values=check_inputs(root,output,True);truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
 check_image(values['conker/build/conker.us.elf'],(root/'conker/build/conker.us.elf').read_bytes(),truth)
 result=linked_function_audit(output/'before-conker_build_conker.us.elf',root/'conker/build/conker.us.elf')
 data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if(data['exact'],data['owner_count'],data['bytes'],data['different_bytes'])!=(True,720,189088,0):raise ValueError('Reset protected Game data differs')
 result.update(game_data=data);(output/'installed-audit.json').write_text(json.dumps(result,indent=2)+chr(10))
 return result

ARTIFACTS=('before-owner.o','after-owner.o','selected.o','before-padded.o','qualified-padded.o',
           'qualified-guards.csv','proposed-owner.c','proposed-variables.h','proposed-structs.h',
           'first-linked.elf','original-func_15007778.o')

def verify_prepared(output):
 rows=json.loads((output/'artifact-fingerprint.json').read_text())
 if set(rows)!=set(ARTIFACTS):raise ValueError('Reset prepared artifact set changed')
 for n,wanted in rows.items():
  if sha((output/n).read_bytes())!=wanted:raise ValueError('Reset prepared artifact changed: '+n)
 for n,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
  if sha((output/n).read_bytes())!=wanted:raise ValueError('Reset raw execution changed: '+n)
 q=json.loads((output/'qualification.json').read_text())
 if sha((output/'make-plan.txt').read_bytes())!=q['Make_plan_SHA256']:raise ValueError('Reset Make plan changed')
 return rows

def freeze_prepared(root,output):
 if(output/'artifact-fingerprint.json').exists():raise ValueError('Inspect completed reset artifact freeze')
 values=check_inputs(root,output);headers=recovered_headers(values)
 proposed=recovered_owner(values[SOURCE].decode()).encode()
 if(output/'after-owner.c').read_bytes()!=proposed:raise ValueError('Reset compiled owner source changed')
 outputs={'proposed-owner.c':proposed,'proposed-variables.h':headers['conker/include/variables.h'],
          'proposed-structs.h':headers['conker/include/structs.h']}
 for n,data in outputs.items():
  p=output/n
  if p.exists()and p.read_bytes()!=data:raise ValueError('Reset proposed output changed: '+n)
  p.write_bytes(data)
 from tools.experiments.game_four_head_lookup_match import payload
 raw,rs=payload(output/'after-owner.o',FUNCTION)
 if normalized(raw,rs)!=payload(output/'original-func_15007778.o',FUNCTION):raise ValueError('Reset final emitted fit changed')
 if(output/'qualified-guards.csv').read_bytes()!=guard_bytes(values['conker/retail_word_patches.us.csv'],raw,rs):raise ValueError('Reset final guard derivation changed')
 (output/'artifact-fingerprint.json').write_text(json.dumps({n:sha((output/n).read_bytes())for n in ARTIFACTS},indent=2)+chr(10))
 return verify_prepared(output)
