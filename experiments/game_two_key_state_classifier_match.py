"""Two-key actor state classification: complete C and derived storage/register fit."""
import csv,io,json,shlex,struct,subprocess
from pathlib import Path
from tools.experiments.game_four_head_lookup_match import digest,diagnostics,payload
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span,link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly,parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_view_list_setup import ViewListSetupTests
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
OWNER='generated_185560'
FUNCTION='func_151592B8'
SOURCE='conker/src/game/generated_185560.c'
OBJECT='conker/build/src/game/generated_185560.c.o'
ASM='conker/asm/185560.s'
BUILD='conker/build/game-two-key-state-classifier-match'
ENTRY,ROM,SIZE,TABLE=0x151592B8,0x186768,184,0x8008B040
BEFORE_ELF_SHA='ae2868d7489238a6ed10b99e956ec9a8dd4d94a8f13008b26d2d8c7dc5045322'
BEFORE_OBJECT_SHA='09cc80b59196990d56352e0aae66756723b8f0031a76b0855d913359b2320be9'
GUARD_SHA='8c374d6e04e30a01128238f044a404be119457734195fc61543fea76082c4013'
SNAPSHOT_SHA='8f14a3e57a14c9d087e20bc8278600ef06b841f82dad1e58598e27c66d83bb86'
RAW_SHA='0e2a8cae1b1fc8315d2027fb08bb5da06e7a04577d44c72d5e28ebbdf7602016'
BINDINGS={24:[('R_MIPS_HI16','D_8008B040')],28:[('R_MIPS_LO16','D_8008B040')]}
CYCLE=('D_800991D0','D_8009E6E0')
HEADERS='#include <ultra64.h>\n'
DECLARATIONS='extern u16 D_8008B040;\n'
SELECTED="/* Prioritize the two special actor types, then flag and motion states. */\ns32 func_151592B8(u8 *actor, u8 mode) {\n    u16 keys[1];\n    u32 cursor;\n    s32 actorType;\n    s32 matched;\n    s32 result;\n\n    if (mode == 0) {\n        keys[0] = D_8008B040;\n        matched = 0;\n        actorType = *(u16 *)(actor + 0x84);\n        cursor = (u32)((u8 *)keys + 1);\n        do {\n            if (actorType == *(u8 *)cursor--) {\n                matched = 1;\n            }\n        } while (!matched && cursor >= (u32)(u8 *)keys);\n    } else {\n        matched = 0;\n    }\n    if (matched) {\n        result = 3;\n    } else if (actor[0xAD] != 0) {\n        result = 2;\n    } else if (0.0f != *(f32 *)(actor + 0x28)) {\n        result = 1;\n    } else {\n        result = 4;\n    }\n    return result;\n}"


def snapshot(output):
 raw=(output/'input-snapshot.json').read_bytes()
 if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Classifier snapshot changed')
 values={}
 for n,wanted in json.loads(raw)['INPUTS'].items():
  data=(output/('before-'+n.replace('/','_'))).read_bytes()
  if digest(data)!=wanted:raise ValueError('Classifier frozen input changed: '+n)
  values[n]=data
 if digest(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA or digest(values[OBJECT])!=BEFORE_OBJECT_SHA:raise ValueError('Classifier predecessor changed')
 return values


def recovered_owner(before):
 lo,hi=function_span(before,FUNCTION)
 if before[lo:hi]!='s32 func_151592B8() {\n    return 0;\n}':raise ValueError('Classifier original placeholder changed')
 text=before[:lo]+SELECTED+before[hi:]
 return text.replace(HEADERS,HEADERS+'\n'+DECLARATIONS,1)


def original(root,output,name=FUNCTION):
 context=type('ClassifierOriginal',(),dict(root=root,out=output))
 return ViewListSetupTests.original.__func__(context,'original-'+name,(root/ASM).read_text(),name)


def normalized(raw,bindings):
 if len(raw)!=184 or digest(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Classifier raw body or bindings changed')
 w=list(struct.unpack('>46I',raw))
 expected={9:0x27A50015,10:0xA7AF0014,11:0x94830084,12:0x27A70014,13:0x90B80000,14:0x24A5FFFF,15:0x00A7082B,16:0x14780002,22:0x90B80000}
 if any(w[i]!=v for i,v in expected.items())or(w[0],w[-1])!=(0x27BDFFE8,0x27BD0018):raise ValueError('Classifier storage/role instruction changed')
 w[9]=(w[9]&~((31<<16)|65535))|(6<<16)|13
 w[10]=(w[10]&~65535)|12;w[11]=(w[11]&~(31<<16))|(5<<16);w[12]=(w[12]&~65535)|12
 for i in(13,22):w[i]=(w[i]&~(31<<21))|(6<<21)
 w[14]=(w[14]&~((31<<21)|(31<<16)))|(6<<21)|(6<<16)
 w[15]=(w[15]&~(31<<21))|(6<<21);w[16]=(w[16]&~(31<<21))|(5<<21)
 return struct.pack('>46I',*w),dict(bindings)


def guard_bytes(before,raw,bindings):
 if digest(before)!=GUARD_SHA:raise ValueError('Classifier guard history changed')
 reader=csv.DictReader(io.StringIO(before.decode()));schema=reader.fieldnames
 if any(row['function']==FUNCTION for row in reader):raise ValueError('Classifier guards already present')
 fitted,_=normalized(raw,bindings);a=struct.unpack('>46I',raw);b=struct.unpack('>46I',fitted)
 stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=schema,lineterminator='\r\n'if before.endswith(b'\r\n')else'\n')
 for i,(x,y)in enumerate(zip(a,b)):
  if x!=y:writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%03X'%(4*i),expected='0x%08X'%x,replacement='0x%08X'%y,expected_relocations='-',replacement_relocations='-',note='Derive two live register roles and the complete two-byte local stack relocation',omit='false'))
 return before+stream.getvalue().encode()


def predicted_image(before,truth):
 if digest(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE:raise ValueError('Classifier image predecessor changed')
 rows={n:(off,f)for off,n,f,_ in symbol_rows(before)};off,f=rows[FUNCTION]
 if f[1:]!=(ENTRY,12,18,0,5):raise ValueError('Classifier baseline symbol changed')
 result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth;struct.pack_into('>I',result,off+8,SIZE)
 positions=[rows[n][0]for n in CYCLE]
 if positions!=[positions[0],positions[0]+16]:raise ValueError('Classifier closed symbol swap moved')
 for n,other in zip(CYCLE,CYCLE[::-1]):
  off,source=rows[n][0],rows[other][0];result[off+4:off+16]=before[source+4:source+16]
  a,b=n.encode()+b'\0',other.encode()+b'\0'
  if len(a)!=len(b)or before.count(a)!=1:raise ValueError('Classifier symbol-string swap changed')
  at=before.index(a);result[at:at+len(a)]=b
 return bytes(result)


def check_image(before,actual,truth):
 if actual!=predicted_image(before,truth):raise ValueError('Classifier strict complete image differs')


def check_inputs(root,output,installed=False):
 values=snapshot(output);truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
 changes={SOURCE:(output/'proposed-owner.c').read_bytes(),'conker/retail_word_patches.us.csv':(output/'qualified-guards.csv').read_bytes(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],truth)}
 for n,before in values.items():
  wanted=changes.get(n,before)if installed else before
  if(root/n).read_bytes()!=wanted:raise ValueError('Classifier current input differs: '+n)
 return values


def make_shadow(root,output):
    conker=root/'conker';shadow=output/'make-shadow-target';target=(shadow/OBJECT.removeprefix('conker/build/')).relative_to(conker).as_posix()
    (conker/target).parent.mkdir(parents=True,exist_ok=True)
    p=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-plan.txt').write_text(p.stdout+p.stderr);commands=[]
    for line in p.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown plane-component Make command: '+repr(args))
        changes={SOURCE.removeprefix('conker/'):(output/'proposed-owner.c').relative_to(conker).as_posix(),
                 'retail_word_patches.us.csv':(output/'qualified-guards.csv').relative_to(conker).as_posix(),
                 'retail_layout.us.txt':(output/'qualified-layout.txt').relative_to(conker).as_posix()}
        args=[changes.get(a,a)for a in args];redirect=None
        if '>'in args:
            if args[-2]!='>'or args.count('>')!=1:raise ValueError('Unknown plane-component redirect')
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        result=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected=(output/'after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
        if result.returncode or diagnostics(result.stderr)!=diagnostics(expected)or(redirect is None and result.stdout):raise ValueError(result.stdout+result.stderr)
        if redirect is not None:redirect.write_text(result.stdout)
        commands.append(args)
    obj=conker/target
    if len(commands)!=5 or obj.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Classifier actual Make differs')
    if same_functions(output/'after-owner.o',Path(str(obj)+'.compact'),())!=len(parse_object(output/'after-owner.o')[1]):raise ValueError('Classifier Make compact functions changed')
    report=dict(commands=5,normal_O2_g3=True,compact_functions_equal=len(parse_object(output/'after-owner.o')[1]),complete_padded_object_equal=True,preserved_global_asm=snapshot(output)[SOURCE].decode().count('#pragma GLOBAL_ASM'),inherited_warnings=p.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report


ARTIFACTS=('before-owner.o','after-owner.o','selected.o','before-padded.o','qualified-padded.o','qualified-guards.csv','proposed-owner.c','first-linked.elf')


def verify_prepared(output):
 rows=json.loads((output/'artifact-fingerprint.json').read_text())
 if set(rows)!=set(ARTIFACTS):raise ValueError('Classifier artifact set changed')
 for n,wanted in rows.items():
  if digest((output/n).read_bytes())!=wanted:raise ValueError('Classifier prepared artifact changed: '+n)
 for n,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
  if digest((output/n).read_bytes())!=wanted:raise ValueError('Classifier original raw execution changed: '+n)
 q=json.loads((output/'qualification.json').read_text())
 if digest((output/'make-plan.txt').read_bytes())!=q['Make_plan_SHA256']:raise ValueError('Classifier Make profile changed')
 return rows


def prepare_emitted(root,output):
 if(output/'artifact-fingerprint.json').exists():raise ValueError('Inspect completed classifier qualification')
 values=check_inputs(root,output);raw,rs=payload(output/'after-owner.o',FUNCTION)
 if normalized(raw,rs)!=payload(original(root,output),FUNCTION)or payload(output/'selected.o',FUNCTION)!=(raw,rs):raise ValueError('Classifier raw/owner/original differs')
 if(output/'proposed-owner.c').read_text()!=recovered_owner(values[SOURCE].decode()):raise ValueError('Classifier recovered source changed')
 if(output/'qualified-guards.csv').read_bytes()!=guard_bytes(values['conker/retail_word_patches.us.csv'],raw,rs):raise ValueError('Classifier guard derivation changed')
 a=same_functions(output/'before-owner.o',output/'after-owner.o',(FUNCTION,));b=same_functions(output/'before-padded.o',output/'qualified-padded.o',(FUNCTION,))
 if a!=b or normalized_pools(output/'before-owner.o')!=normalized_pools(output/'after-owner.o'):raise ValueError('Classifier owner neighbors/pools changed')
 truth=values['conker/conker.us.bin'][ROM:ROM+SIZE];check_image(values['conker/build/conker.us.elf'],(output/'first-linked.elf').read_bytes(),truth)
 Make=make_shadow(root,output)
 q=dict(body_words=46,frame=24,new_guards=9,bindings=2,preserved_neighbors=a,preserved_global_asm=values[SOURCE].decode().count('#pragma GLOBAL_ASM'),Make=Make,Make_plan_SHA256=digest((output/'make-plan.txt').read_bytes()),changed_bytes=137,code_bytes=122,metadata_bytes=15,exclusions=0,raw_objects_recompiled=False)
 (output/'qualification.json').write_text(json.dumps(q,indent=2)+'\n')
 (output/'artifact-fingerprint.json').write_text(json.dumps({n:digest((output/n).read_bytes())for n in ARTIFACTS},indent=2)+'\n');verify_prepared(output);return q


def linked_function_audit(before,after):
 a,_,aa=load_elf_functions(str(before),'mips-linux-gnu-objdump');b,_,ba=load_elf_functions(str(after),'mips-linux-gnu-objdump')
 if set(a)!=set(b)or aa!=ba:raise ValueError('Classifier linked functions/addresses changed')
 changed=[n for n in a if a[n]!=b[n]]
 if changed!=[FUNCTION]:raise ValueError('Classifier other linked body changed: '+repr(changed))
 return dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True)


def audit(root,output):
 values=check_inputs(root,output,True);verify_prepared(output);truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
 check_image(values['conker/build/conker.us.elf'],(root/'conker/build/conker.us.elf').read_bytes(),truth)
 q=linked_function_audit(output/'before-conker_build_conker.us.elf',root/'conker/build/conker.us.elf');data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
 if(data['exact'],data['owner_count'],data['bytes'],data['different_bytes'])!=(True,720,189088,0):raise ValueError('Classifier protected Game data changed')
 q.update(game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
