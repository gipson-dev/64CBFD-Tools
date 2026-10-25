"""Seven-output setup defaults: semantic C, ordinary padding and strict image."""
import hashlib,json,re,shlex,struct,subprocess
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span,link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

FUNCTION,ENTRY,ROM,SIZE='func_1518E524',0x1518E524,0x1BB9D4,180
SOURCE,OWNER,ASM='conker/src/game/generated_1BA1D0.c','generated_1BA1D0','conker/asm/1BA1D0.s'
OBJECT='conker/build/src/game/generated_1BA1D0.c.o'
BUILD='conker/build/game-setup-byte-defaults-match'
INPUTS = {
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/asm/1BA1D0.s": "091ecf705e3957bff810d1736e7a6a38cc23503b3af34c65e22046f7fd019c93",
    "conker/asm/data/2320A0.rodata.s": "fdc0ddda06c87e11229f43c5738f4adcf61c7fa753eedc2c8f56136ecc9f1b64",
    "conker/asm/nonmatchings/game_DAE50/func_150ADA20.s": "64b478aa7a866ba3793982326254c86aad25a0e378e364497ea1a32b4eb2f50a",
    "conker/build/asm/data/2320A0.rodata.s.o": "f66b31d9982b5dd78ce5f64287235138002de32403755f7f4e21e02ef78595aa",
    "conker/build/conker.us.elf": "66bdd012b8d94c6d1d998f3ee6392703b21ae99f754e637efde85078084cc838",
    "conker/build/src/game/generated_1BA1D0.c.o": "47d68fb378294429e2ded64740ae481415ab3ee54db7c56e81ea598dad162117",
    "conker/build/src/game_169510.c.o": "95374151740bf29c76b8ade5e52c775a098e20041fccc984eb78095278a50b8c",
    "conker/build/src/game_DAE50.c.o": "4d1d3e2f8e8a3aef5874580eeb6917083720e2354db3dbb43d732631beb26c4f",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/include/2.0L/PR/gbi.h": "155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6",
    "conker/include/2.0L/PR/ultratypes.h": "1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd",
    "conker/include/2.0L/ultra64.h": "334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/libc/stdarg.h": "759498a7844671810843e0715215b1ddb3b402d2465e96aa19b65494d71ac2b4",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/macros.h": "dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769",
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/retail_word_patches.us.csv": "876afb871a1a6c41916b69b192d8b9fc786b688ad91a2381bfdcd9a698814d3b",
    "conker/src/game/generated_1BA1D0.c": "71581382374d9c4b0fe0fa1501a8a6b9465b7a359a792ef4a9a0976b125832ac",
    "conker/src/game_169510.c": "cb2f5e4bc1df3d0c31b27ccf4094a98834cac2caee9b18cc00944207ed2647f8",
    "conker/src/game_DAE50.c": "ca6779c0fd3e2cd16b2f8ce758865df59310da359987cce07781cc5005733729",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs.us.txt": "92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/undefined_syms.us.txt": "d678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e",
    "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
    "tools/experiments/game_random_selector_outputs_candidates.py": "34f0bb18c9379b6446a31747ad1839303595bc28cf8bc86a7e588457eacf61e8",
    "tools/tests/game_frame_timing_oracle.py": "0473246cfb1219a8081c279b680aea19c5fef7829ca4a35878568a70ef643fa7",
    "tools/tests/game_owner_pool.py": "159b8c009af7b2d26ba5dce29f0c46ca0805cf14dbb27e5c682d107e551ca50e",
    "tools/tests/game_view_render_pass_oracle.py": "97782140d5683fada720f2bc3e01d84f21e5ea6d7b6947f1cc69fbe1886c8ee9",
    "tools/tests/test_game_actor_triangle_transform_match.py": "f56c48c913792764f361c509c32ae68b0ae2a77aad3f4657cfa869f13e3f7844",
    "tools/tests/test_game_effect_owner_ray.py": "62376c5022f50db9a53b0ec8b9517a63bc9f298dff8c7a3047963ed216a0555f",
    "tools/tests/test_game_indexed_state_save_match.py": "7515863c27054949e982a4338637dbb7d312d76d520c5ed2453056e4a5eb7248",
    "tools/tests/test_game_projected_packet_draw.py": "e488215f4551d0ed97454e57edb43522c0df9d1ebe9b0303f42cbd236e0261d8",
    "tools/tests/test_game_random_curve_record.py": "c2ef8cf99121bd79e92ea7fb2c8be873be1064d3f1cec131a8c603d9f8fc5380",
    "tools/tests/test_game_random_selector_outputs_match.py": "95a3f7a3cc26644f82d932b0cf9d5223ab87ccb025789c4660581ea3fd0974d4",
    "tools/tests/test_game_row_destination_fill.py": "b79e64e36c55617f835d5fe7abadbba5d97272cd93d50055fb4167db8f8273fd",
    "tools/tests/test_game_table_range_loader.py": "75ef2dc2a01af9047086a823352e1dcc30ab6751e74a7cad5d18cf69f54f2141"
}
DECLARATIONS='s32 func_150ADA20(void);\n'
SELECTED='''/* Initialize flags, choose the kind, and set opaque black RGBA defaults. */
void func_1518E524(u8 *kind, u8 *flags, u8 *red, u8 *green, u8 *blue,
                  u8 *alpha, s16 *mode) {
    *flags = 2;
    if (func_150ADA20() & 1) {
        *flags |= 1;
    }
    switch (func_150ADA20() & 1) {
        case 0:
            *kind = 0x13;
            break;
        case 1:
            *kind = 0x14;
            break;
    }
    *red = 0;
    *green = 0;
    *blue = 0;
    *alpha = 0xFF;
    *mode = 0x301;
}'''
RAW_SHA256='0086c4a0d807b3ead5b46e7167bfd6ddab7e660f1a1e5141ad449b837625326b'
BINDINGS={28:[('R_MIPS_26','func_150ADA20')],60:[('R_MIPS_26','func_150ADA20')]}

def digest(data):return hashlib.sha256(data).hexdigest()

def diagnostics(text):
    return re.sub(r'line\s+\d+','line #',re.sub(r'\S+\.c','<unit>',text))

def snapshot(output):
    if not INPUTS:raise ValueError('Setup defaults baseline has not been pinned')
    values={}
    for name,wanted in INPUTS.items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Setup defaults frozen input changed: '+name)
        values[name]=data
    return values

def freeze(root,output):
    values=snapshot(output)
    for name,old in values.items():
        if(root/name).read_bytes()!=old:raise ValueError('Setup defaults predecessor changed: '+name)
    if(output/'before-padded.o').read_bytes()!=values[OBJECT]:raise ValueError('Setup defaults predecessor object changed')
    return values

def recovered_owner(before):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1518E524() {\n    return 0;\n}':raise ValueError('Unknown setup defaults predecessor')
    if DECLARATIONS.strip()not in before:raise ValueError('Missing typed RNG declaration')
    return before[:lo]+SELECTED+before[hi:]

def payload(obj):
    text,functions,relocations=parse_object(obj);info=functions[FUNCTION]
    raw=text[info['value']:info['value']+info['size']]
    words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words)if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero setup defaults alignment tail')
    bindings={at-info['value']:rows for at,rows in relocations.items()if info['value']<=at<info['value']+end*4}
    return raw[:end*4],bindings

def checked_payload(raw,bindings):
    if len(raw)!=SIZE or digest(raw)!=RAW_SHA256 or bindings!=BINDINGS:raise ValueError('Changed setup defaults words/bindings')

def original(root,output,name=FUNCTION,asm=ASM):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('SetupOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-'+name,(root/asm).read_text(),name)

def qualify(root,output):
    values=freeze(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'qualified-before-owner')
    after,db=compile_owner(root,output,wanted,'qualified-after-owner')
    isolated,dc=compile_owner(root,output,'#include <ultra64.h>\n'+DECLARATIONS+SELECTED,'qualified-selected')
    if diagnostics(da)!=diagnostics(db)or dc:raise ValueError('Setup defaults compiler diagnostics: '+da+db+dc)
    raw,bindings=payload(isolated);checked_payload(raw,bindings)
    truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    linked,functions=link_owner(root,output,isolated,OWNER);at=functions[FUNCTION]['value']
    if linked[at:at+SIZE]!=truth or payload(after)!=(raw,bindings):raise ValueError('Setup defaults source/owner differs')
    if payload(original(root,output))!=(raw,bindings):raise ValueError('Setup defaults GNU original differs')
    neighbors=same_functions(before,after,(FUNCTION,))
    if neighbors!=60 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Setup defaults raw neighbors/pools changed')
    assembly=output/'qualified-padded.s'
    assembly.write_text(emit_padded_assembly(after,root/ASM,word_patches_path=root/'conker/retail_word_patches.us.csv',filename=OWNER))
    obj=assembly.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(assembly)],check=True,capture_output=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={n:dict(info)for n,info in fa.items()}
    if expected[FUNCTION]['size']!=12:raise ValueError('Setup defaults predecessor extent changed')
    expected[FUNCTION]['size']=SIZE;at=fb[FUNCTION]['value']
    slot=elf_slot_offset(values['conker/build/conker.us.elf'],ENTRY,SIZE)
    if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]:raise ValueError('Setup defaults predecessor slot changed')
    if b[at:at+SIZE]!=truth or expected!=fb or a[:at]!=b[:at]or a[at+SIZE:]!=b[at+SIZE:]:raise ValueError('Setup defaults padded body/address/extent differs')
    if same_functions(old,obj,(FUNCTION,))!=neighbors or normalized_pools(old)!=normalized_pools(obj):raise ValueError('Setup defaults padded neighbors/pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(words=45,frame=24,differences=0,relocations=2,new_guards=0,alignment_words=0,
        raw_SHA256=digest(raw),preserved_neighbors=neighbors,compiler_only=True,
        owner_diagnostics_unchanged=True,isolated_diagnostics_empty=True,shared_headers_unchanged=True,
        target_size_before=12,target_size_after=SIZE,unreachable_switch_default_offsets=[92,96])
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report

def make_shadow(root,output):
    freeze(root,output);conker=root/'conker';shadow=output/'make-shadow'
    (shadow/'src/game').mkdir(parents=True,exist_ok=True)
    target=(shadow/'src/game/generated_1BA1D0.c.o').relative_to(conker).as_posix()
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unexpected setup defaults Make command: '+repr(args))
        args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a=='src/game/generated_1BA1D0.c'else a for a in args]
        redirect=None
        if '>'in args:
            if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown setup defaults Make redirect')
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected=(output/'qualified-after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
        if p.returncode or diagnostics(p.stderr+(p.stdout if redirect is None else''))!=diagnostics(expected):raise ValueError('Setup defaults Make command failed: '+p.stdout+p.stderr)
        if redirect is not None:redirect.write_text(p.stdout)
        commands.append(args)
    actual=conker/target;compilers=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
    if len(compilers)!=1 or not all(f in compilers[0]for f in('-O2','-g3'))or any('-loopunroll'in f for f in compilers[0]):raise ValueError('Setup defaults Make compiler profile changed')
    if same_functions(output/'qualified-after-owner.o',Path(str(actual)+'.compact'))!=61:raise ValueError('Setup defaults Make raw owner differs')
    if link_owner(root,output,actual,OWNER)!=link_owner(root,output,output/'qualified-padded.o',OWNER):raise ValueError('Setup defaults Make padded owner differs')
    report=dict(actual_Make_commands=len(commands),normal_O2_g3=True,all_raw_functions_equal=True,
        padded_code_and_metadata_equal=True,inherited_Make_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report

def predicted_image(before,truth):
    if digest(before)!=INPUTS['conker/build/conker.us.elf']or len(truth)!=SIZE:raise ValueError('Setup defaults strict predecessor changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[offset for offset,name,fields,_ in symbol_rows(before)if name==FUNCTION and fields[1:3]==(ENTRY,12)and fields[3]&15==2]
    if len(rows)!=1:raise ValueError('Setup defaults original symbol extent changed')
    struct.pack_into('>I',result,rows[0]+8,SIZE)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Setup defaults image differs from strict body/size prediction')

def predict(root,output):
    values=freeze(root,output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game/generated_1BA1D0.c.o'
    if script.count(old)!=1:raise ValueError('Unknown setup defaults link input')
    link=output/'first-link.ld';link.write_text(script.replace(old,(output/'qualified-padded.o').relative_to(root/'conker').as_posix()))
    elf=output/'first-linked.elf'
    p=subprocess.run(['mips-linux-gnu-ld','-T',link.relative_to(root/'conker').as_posix(),'-T','undefined_syms.us.txt',
        '-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt',
        '--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(root/'conker').as_posix()],cwd=root/'conker',capture_output=True,text=True)
    (output/'first-link.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise ValueError('Setup defaults independent link failed: '+p.stdout+p.stderr)
    before=values['conker/build/conker.us.elf'];actual=elf.read_bytes();truth=values['conker/conker.us.bin'][ROM:ROM+SIZE]
    check_image(before,actual,truth)
    changed=sum(a!=b for a,b in zip(before,actual));code_changed=sum(a!=b for a,b in zip(before[elf_slot_offset(before,ENTRY,SIZE):][:SIZE],truth))
    report=dict(SHA256=digest(actual),changed_bytes=changed,code_bytes=code_changed,metadata_bytes=changed-code_changed,
        strict_prediction=True,metadata_exclusions=0)
    (output/'first-link.json').write_text(json.dumps(report,indent=2)+'\n');return report

def audit_inputs(root,output):
    values=snapshot(output)
    wanted=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])
    for name,old in values.items():
        expected=(recovered_owner(old.decode()).encode()if name==SOURCE else
            (output/'qualified-padded.o').read_bytes()if name==OBJECT else
            wanted if name=='conker/build/conker.us.elf'else old)
        if(root/name).read_bytes()!=expected:raise ValueError('Setup defaults installed input differs: '+name)
    return values,wanted

def audit(root,output):
    values,wanted=audit_inputs(root,output);before=output/'before-conker_build_conker.us.elf';elf=root/'conker/build/conker.us.elf'
    if(output/'first-linked.elf').read_bytes()!=wanted:raise ValueError('Setup defaults independent image changed')
    a,_,aa=load_elf_functions(str(before),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(elf),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb:raise ValueError('Setup defaults linked function identities/addresses changed')
    if b[FUNCTION]!=list(struct.unpack('>45I',values['conker/conker.us.bin'][ROM:ROM+SIZE])):raise ValueError('Setup defaults installed body differs')
    for n in a:
        if n!=FUNCTION and a[n]!=b[n]:raise ValueError('Setup defaults changed another linked body: '+n)
    check_image(values['conker/build/conker.us.elf'],elf.read_bytes(),values['conker/conker.us.bin'][ROM:ROM+SIZE])
    data=audit_layout(elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Setup defaults protected Game data changed')
    report=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=45,
        strict_first_link_reproduced=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
