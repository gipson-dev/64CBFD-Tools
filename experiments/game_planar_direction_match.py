"""Plane-component normalization and its independently emitted low-bit accessor."""
import csv,io,json,shlex,struct,subprocess
from pathlib import Path
from tools.experiments.game_four_head_lookup_match import digest,diagnostics,payload
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span,link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import emit_padded_assembly,parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_view_list_setup import ViewListSetupTests
from tools import progress as progress_tool
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

OWNER='generated_13BB20'
FUNCTION,LEAF='func_1510F820','func_1510F8CC'
SOURCE='conker/src/game/generated_13BB20.c'
OBJECT='conker/build/src/game/generated_13BB20.c.o'
ASM='conker/asm/13BB20.s'
BUILD='conker/build/game-planar-direction-match'
ENTRY,LEAF_ENTRY,ROM,SIZE,BODY=0x1510F820,0x1510F8CC,0x13CCD0,184,172
HELPER,SCALE=0x1510E388,0x800A2D9C
SNAPSHOT_SHA='3880c09eaf1ed720f0b07706215f56896748ead1e80738432b28e214aa9a987e'
BEFORE_ELF_SHA='d657fc688a62a3883830cf9a96a59ef95eba3318594c684e5be97a4a032be72f'
BEFORE_OBJECT_SHA='243410f1dc17921b7af8429e6fde5b827f62da1fdc28e3fb26af7453b93d0f55'
GUARD_SHA='0fc7da71a110d7ab703aa7ea98374fe69f6fddb14ad87b46e0085b82c0d4815e'
RAW_SHA='cd91b91626b621e7c1f78abd35cf3019e4d7b58520a59a47335eca607d4de0e6'
MAKE_PLAN_SHA='abf32e74411ad8439cb109f0cab80c732b42e2160b507db8d948e5c3c6026cc2'
LEAF_RAW_SHA='17da24965109cb7e9ea29ece4ce439695121e840905cd692c52b34176d560024'
HEADERS='#include <ultra64.h>\n'
DECLARATIONS="extern f32 D_800A2D9C;\nf32 sqrtf(f32);\ns32 func_1510E388(void *, void *, f32 *, f32 *);\n"
SELECTED="/* Resolve the plane components and normalize their scaled length. */\nvoid func_1510F820(void *indirectVertices, void *packedVertices,\n                   f32 *directionA, f32 *directionB, f32 *unusedOutput,\n                   f32 *rawA, f32 *rawB) {\n    f32 first, second, length;\n\n    func_1510E388(indirectVertices, packedVertices, &first, &second);\n    length = sqrtf(first * first + second * second);\n    *rawA = first;\n    *rawB = second;\n    length *= D_800A2D9C;\n    if (length == 0.0f) {\n        *directionA = 1.0f;\n        *directionB = 0.0f;\n    } else {\n        *directionA = first / length;\n        *directionB = second / length;\n    }\n}"
LEAF_SELECTED="/* Extract the low five bits of the incoming word. */\nu32 func_1510F8CC(u32 value) {\n    return value & 0x1F;\n}"
PROTOTYPE="void func_1510F820(void *, void *, f32 *, f32 *, f32 *, f32 *, f32 *);\n"
BINDINGS={20:[('R_MIPS_26','func_1510E388')],64:[('R_MIPS_HI16','D_800A2D9C')],76:[('R_MIPS_LO16','D_800A2D9C')]}
CYCLE=('D_800A2D9C','D_80090ADC','D_8009059C')


def snapshot(output):
    raw=(output/'input-snapshot.json').read_bytes()
    if digest(raw)!=SNAPSHOT_SHA:raise ValueError('Plane-component snapshot changed')
    values={}
    for name,wanted in json.loads(raw)['INPUTS'].items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Plane-component frozen input changed: '+name)
        values[name]=data
    if digest(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA or digest((output/'before-padded.o').read_bytes())!=BEFORE_OBJECT_SHA:
        raise ValueError('Plane-component predecessor changed')
    return values


def recovered_owner(before):
    result=before
    for name,body in((FUNCTION,SELECTED),(LEAF,LEAF_SELECTED)):
        lo,hi=function_span(result,name)
        if result[lo:hi]!='s32 '+name+'() {\n    return 0;\n}':raise ValueError('Plane-component placeholder changed: '+name)
        result=result[:lo]+body+result[hi:]
    if not result.startswith(HEADERS):raise ValueError('Plane-component include changed')
    return result.replace(HEADERS,HEADERS+'\n'+DECLARATIONS,1)


def recovered_layout(before):
    old=b'game,generated_13BB20,func_1510F820,0x1510F820,0x1510F8D8'
    if before.count(old)!=1:raise ValueError('Plane-component layout predecessor changed')
    newline=b'\r\n'if old+b'\r\n'in before else b'\n'
    new=b'game,generated_13BB20,func_1510F820,0x1510F820,0x1510F8CC'+newline+b'game,generated_13BB20,func_1510F8CC,0x1510F8CC,0x1510F8D8'
    return before.replace(old,new)


def recovered_undefined(before):
    line=b'func_1510F8CC = 0x1510F8CC;'
    if before.count(line)!=1:raise ValueError('Plane-component fallback predecessor changed')
    return before.replace(line+(b'\r\n'if line+b'\r\n'in before else b'\n'),b'')


def original(root,output,name=FUNCTION):
    context=type('PlaneComponentOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+name,(root/ASM).read_text(),name)


def normalized(raw,bindings):
    if len(raw)!=172 or digest(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Plane-component raw body or bindings changed')
    words=list(struct.unpack('>43I',raw));word=words[25]
    if(word>>26,word>>21&31,word&63)!=(17,16,50):raise ValueError('Plane-component comparison changed')
    fs,ft=word>>11&31,word>>16&31
    words[25]=(word&~((31<<11)|(31<<16)))|(fs<<16)|(ft<<11)
    if words[25]==word:raise ValueError('Plane-component comparison control ineffective')
    return struct.pack('>43I',*words),dict(bindings)


def checked_leaf(raw,bindings):
    if len(raw)!=12 or digest(raw)!=LEAF_RAW_SHA or bindings:raise ValueError('Low-bit accessor raw body changed')
    return raw,bindings


def guard_bytes(before,raw,bindings):
    if digest(before)!=GUARD_SHA:raise ValueError('Plane-component guard history changed')
    reader=csv.DictReader(io.StringIO(before.decode()));schema=reader.fieldnames
    if any(row['function']in(FUNCTION,LEAF)for row in reader):raise ValueError('Plane-component guards already exist')
    fitted,_=normalized(raw,bindings);newline='\r\n'if before.endswith(b'\r\n')else'\n'
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=schema,lineterminator=newline)
    writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x064',expected='0x%08X'%struct.unpack_from('>I',raw,100)[0],
        replacement='0x%08X'%struct.unpack_from('>I',fitted,100)[0],expected_relocations='-',replacement_relocations='-',
        note='Preserve the commutative zero-length comparison operand order',omit='false'))
    return before+stream.getvalue().encode()


def predicted_image(before,truth,inventory_only=False):
    if digest(before)!=BEFORE_ELF_SHA or len(truth)!=184:raise ValueError('Plane-component image predecessor changed')
    rows={name:(off,f)for off,name,f,_ in symbol_rows(before)}
    off,f=rows[LEAF]
    if f[1:]!=(LEAF_ENTRY,12,18,0,65521):raise ValueError('Low-bit accessor absolute symbol changed')
    result=bytearray(before);struct.pack_into('>H',result,off+14,5)
    if inventory_only:return bytes(result)
    off,f=rows[FUNCTION]
    if f[1:]!=(ENTRY,12,18,0,5):raise ValueError('Plane-component function symbol changed')
    at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth;struct.pack_into('>I',result,off+8,172)
    positions=[rows[n][0]for n in CYCLE]
    if positions!=list(range(positions[0],positions[0]+48,16)):raise ValueError('Plane-component symbol cycle changed')
    for name,next_ in zip(CYCLE,CYCLE[1:]+CYCLE[:1]):
        off,other=rows[name][0],rows[next_][0];result[off+4:off+16]=before[other+4:other+16]
        a,b=name.encode()+b'\0',next_.encode()+b'\0'
        if len(a)!=len(b)or before.count(a)!=1:raise ValueError('Plane-component symbol string cycle changed')
        at=before.index(a);result[at:at+len(a)]=b
    return bytes(result)


def check_image(before,actual,truth,inventory_only=False):
    if actual!=predicted_image(before,truth,inventory_only):raise ValueError('Plane-component strict full image differs')


def check_inputs(root,output,installed=False):
    values=snapshot(output);truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    replacements={SOURCE:(output/'proposed-owner.c').read_bytes(),'conker/retail_word_patches.us.csv':(output/'qualified-guards.csv').read_bytes(),
        'conker/retail_layout.us.txt':(output/'qualified-layout.txt').read_bytes(),'conker/undefined_funcs_auto.txt':(output/'qualified-undefined-functions.txt').read_bytes(),
        OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],truth),
        'conker/progress.csv':(output/'projected-progress.csv').read_bytes()}
    for name,before in values.items():
        expected=replacements.get(name,before)if installed else before
        if(root/name).read_bytes()!=expected:raise ValueError('Plane-component current input differs: '+name)
    return values


def project_progress(root,output,mapfile,shadow_owner=False,prefix='projected'):
    text=mapfile.read_text()
    if shadow_owner:text=text.replace((output/'qualified-padded.o').relative_to(root/'conker').as_posix(),OBJECT.removeprefix('conker/'))
    combined=[];rows=[]
    for section in('init','game','debugger'):
        files,functions=progress_tool.parse_map(io.StringIO(text),'.'+section)
        for filename,names in files.items():
            for name in progress_tool.parse_file(str(root/'conker'),filename,names):functions[name]['language']='c'
        section_text=progress_tool.generate_csv(files,functions,'us',section)+'\n';combined.append(section_text)
        (output/(prefix+'-progress.'+section+'.csv')).write_text(section_text)
        rows.extend(csv.DictReader(io.StringIO(section_text)))
    (output/(prefix+'-progress.csv')).write_text(''.join(combined))
    pair={row['function']:row for row in rows if row['function']in(FUNCTION,LEAF)}
    if len(rows)!=6045 or sum(row['language']=='c'for row in rows)!=5506 or len(pair)!=2:raise ValueError('Plane-component inventory totals changed')
    if[(pair[n]['filename'],pair[n]['length'],pair[n]['language'])for n in(FUNCTION,LEAF)]!=[(OWNER,'172','c'),(OWNER,'12','c')]:
        raise ValueError('Plane-component inventory boundary changed')
    return dict(functions=len(rows),converted=5506,pair=pair,shadow_object_path_projected=shadow_owner)


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
    if len(commands)!=5 or obj.read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Plane-component actual Make differs')
    if same_functions(output/'after-owner.o',Path(str(obj)+'.compact'),())!=14:raise ValueError('Plane-component Make compact functions changed')
    report=dict(commands=5,normal_O2_g3=True,compact_functions_equal=14,complete_padded_object_equal=True,preserved_global_asm=1,inherited_warnings=p.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report


ARTIFACTS=('before-owner.o','after-owner.o','selected.o','qualified-padded.o','qualified-guards.csv','qualified-layout.txt',
           'qualified-undefined-functions.txt','proposed-owner.c','first-linked.elf','inventory-only.elf','projected-progress.csv',
           'projected-progress.init.csv','projected-progress.game.csv','projected-progress.debugger.csv')


def verify_prepared(output):
    if digest((output/'make-plan.txt').read_bytes())!=MAKE_PLAN_SHA:raise ValueError('Plane-component actual Make plan changed')
    plan=(output/'make-plan.txt').read_text()
    compilers=[shlex.split(x)for x in plan.splitlines()if x.startswith('../ido/ido5.3_recomp/cc ')]
    if len(compilers)!=1 or not all(x in compilers[0]for x in('-O2','-g3','-mips2','-o32')):raise ValueError('Plane-component actual compiler profile changed')
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Plane-component artifact set changed')
    for name,wanted in rows.items():
        if digest((output/name).read_bytes())!=wanted:raise ValueError('Plane-component prepared artifact changed: '+name)
    return rows


def prepare_emitted(root,output):
    if(output/'artifact-fingerprint.json').exists():raise ValueError('Inspect existing plane-component prepared artifacts')
    values=snapshot(output);wanted=recovered_owner(values[SOURCE].decode())
    for name,text in(('before-owner',values[SOURCE].decode()),('after-owner',wanted),('selected',HEADERS+DECLARATIONS+SELECTED+'\n'+LEAF_SELECTED)):
        if(output/(name+'.c')).read_text()!=text:raise ValueError('Plane-component emitted source changed: '+name)
    if diagnostics((output/'before-owner-diagnostics.txt').read_text())!=diagnostics((output/'after-owner-diagnostics.txt').read_text())or(output/'selected-diagnostics.txt').read_text():
        raise ValueError('Plane-component diagnostics changed')
    raw,rs=payload(output/'after-owner.o',FUNCTION)
    if normalized(raw,rs)!=payload(original(root,output),FUNCTION)or payload(output/'selected.o',FUNCTION)!=(raw,rs):raise ValueError('Plane-component raw/original/owner differs')
    if checked_leaf(*payload(output/'after-owner.o',LEAF))!=payload(original(root,output,LEAF),LEAF):raise ValueError('Low-bit accessor differs')
    if(output/'proposed-owner.c').read_text()!=wanted or(output/'qualified-guards.csv').read_bytes()!=guard_bytes(values['conker/retail_word_patches.us.csv'],raw,rs):raise ValueError('Plane-component proposed source/guards changed')
    if(output/'qualified-layout.txt').read_bytes()!=recovered_layout(values['conker/retail_layout.us.txt'])or(output/'qualified-undefined-functions.txt').read_bytes()!=recovered_undefined(values['conker/undefined_funcs_auto.txt']):raise ValueError('Plane-component inventory inputs changed')
    if same_functions(output/'before-owner.o',output/'after-owner.o',(FUNCTION,LEAF))!=12 or same_functions(output/'before-padded.o',output/'qualified-padded.o',(FUNCTION,LEAF))!=12:raise ValueError('Plane-component neighbors changed')
    if normalized_pools(output/'before-owner.o')!=normalized_pools(output/'after-owner.o'):raise ValueError('Plane-component private pools changed')
    truth=values['conker/conker.us.bin'][ROM:ROM+SIZE];before=values['conker/build/conker.us.elf']
    check_image(before,(output/'inventory-only.elf').read_bytes(),truth,True);check_image(before,(output/'first-linked.elf').read_bytes(),truth)
    inventory=project_progress(root,output,output/'inventory-only.map',prefix='inventory-only')
    full=project_progress(root,output,output/'first-linked.map',True)
    if inventory['pair']!=full['pair']:raise ValueError('Plane-component private inventory projections differ')
    Make=make_shadow(root,output)
    (output/'artifact-fingerprint.json').write_text(json.dumps({n:digest((output/n).read_bytes())for n in ARTIFACTS},indent=2)+'\n')
    verify_prepared(output)
    report=dict(body_words=43,leaf_words=3,frame=40,new_guards=1,bindings=3,preserved_neighbors=12,preserved_global_asm=1,
        compiler_only_normalizer=False,compiler_only_accessor=True,inventory_only_code_unchanged=True,inventory=inventory,Make=Make,
        changed_bytes=150,code_bytes=127,metadata_bytes=23,exclusions=0,raw_objects_recompiled=False)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report


def linked_function_audit(before,after):
    a,_,aa=load_elf_functions(str(before),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(after),'mips-linux-gnu-objdump')
    if set(b)-set(a)!={LEAF}or set(a)-set(b):raise ValueError('Plane-component function reindex changed')
    if any(ba[n]!=v for n,v in aa.items())or ba[LEAF]!=LEAF_ENTRY:raise ValueError('Plane-component function address changed')
    if {n for n in a if a[n]!=b[n]}!={FUNCTION}:raise ValueError('Plane-component other body changed')
    if len(a[FUNCTION])!=46 or len(b[FUNCTION])!=43 or b[LEAF]!=[0x3082001F,0x03E00008,0]:raise ValueError('Plane-component split function boundary changed')
    return dict(other_bodies_fixed=len(a)-1,all_addresses_fixed=True,before_disassembly_functions=len(a),
                after_disassembly_functions=len(b),newly_indexed_leaf=LEAF)


def audit(root,output):
    values=check_inputs(root,output,True);verify_prepared(output)
    before,truth=values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE]
    check_image(before,(root/'conker/build/conker.us.elf').read_bytes(),truth)
    report=linked_function_audit(output/'before-conker_build_conker.us.elf',root/'conker/build/conker.us.elf')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['owner_count'],data['bytes'],data['different_bytes'])!=(True,720,189088,0):raise ValueError('Plane-component protected data changed')
    report.update(game_data=data,inventory_added_only=LEAF)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
