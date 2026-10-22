"""Direct C circular-buffer read/write and strict two-slot image gates."""
import hashlib,json,re,shlex,struct,subprocess,sys
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span,link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

SOURCE,OWNER,OBJECT='conker/src/game_70200.c','game_70200','conker/build/src/game_70200.c.o'
BUILD='conker/build/game-ring-buffer-transfers/qualified'
SIZE=168
TARGETS={
    'func_15043A20':(0x15043A20,0x70ED0,'conker/asm/nonmatchings/game_70200/func_15043A20.s'),
    'func_15043AC8':(0x15043AC8,0x70F78,'conker/asm/nonmatchings/game_70200/func_15043AC8.s'),
}
RAW_SHA={
    'func_15043A20':'d8a2e99c4a17efcca79bff7e3c901913d98d6d1d29a764bac8124c1906c4f1ad',
    'func_15043AC8':'7ebddca1423f06e939096e2907025ac1a6afde41cb6e9c7645d674e82354c7c5',
}
INPUTS = {
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/include/macros.h": "dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769",
    "conker/include/2.0L/ultra64.h": "334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d",
    "conker/include/2.0L/PR/ultratypes.h": "1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
    "conker/undefined_funcs.us.txt": "92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a",
    "conker/undefined_syms.us.txt": "d678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e",
    "conker/build/conker.us.elf": "a7dddd4be56547f972507c8bd4cad37dbad7e1113e6dc06ba9c5129ea5e46645",
    "conker/retail_word_patches.us.csv": "bcd49d5d0ecb38b8765efa62ce8561f5e857b8a9b42c5bd75948ffa54d6708cb",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721",
    "conker/include/2.0L/PR/gbi.h": "155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6",
    "conker/src/game_70200.c": "1b6c11aa53cc96e351f51671daae61669726ff89f45806bc47082d56414dca6b",
    "conker/asm/nonmatchings/game_70200/func_15043A20.s": "db4f800f0304df9a02f3ab7b70ab2059cde12376d2ad7c607d5121b12b68ddd1",
    "conker/asm/nonmatchings/game_70200/func_15043AC8.s": "e946d70914d39aed71855e397032bd54a3e088b05fe9321e0f80f0cf23910937",
    "conker/asm/nonmatchings/game_70200/func_15043BB8.s": "146c1be87feb40f423e87692c76e02b6d8a7ab123d5c315f9de0249e5d1928d3",
    "conker/asm/nonmatchings/game_70200/func_15043CA4.s": "1884e295626b4c3422da030c1bb01313b08af1c6c7ac516bef8768a4e5b51c96",
    "conker/src/libultra/libc/string.c": "6c66f2298d39e0b159e2645570caed26c869928215aedc41e600daebfc7b98d0",
    "conker/include/libc/stdarg.h": "759498a7844671810843e0715215b1ddb3b402d2465e96aa19b65494d71ac2b4"
}
BEFORE_OBJECT_SHA='e407fc30d9f8af95e774be5e65a5c95405be5a0217c93d67bfd44f5d1e8ab2a3'
SELECTED = {'func_15043A20': '/* Copy linear bytes into the ring and return its updated cursor. */\ns32 func_15043A20(u8 *ring, s32 capacity, s32 cursor, u8 *linear, s32 count) {\n    s32 chunk;\n\n    while (count != 0) {\n        chunk = capacity < (s32)((u32)cursor + (u32)count) ? (s32)((u32)capacity - (u32)cursor) : count;\n        memcpy(ring + cursor, linear, chunk);\n        cursor = (s32)((u32)cursor + (u32)chunk);\n        linear += chunk;\n        count = (s32)((u32)count - (u32)chunk);\n        if (cursor >= capacity) {\n            cursor = 0;\n        }\n    }\n    return cursor;\n}', 'func_15043AC8': '/* Copy linear bytes from the ring and return its updated cursor. */\ns32 func_15043AC8(u8 *ring, s32 capacity, s32 cursor, u8 *linear, s32 count) {\n    s32 chunk;\n\n    while (count != 0) {\n        chunk = capacity < (s32)((u32)cursor + (u32)count) ? (s32)((u32)capacity - (u32)cursor) : count;\n        memcpy(linear, ring + cursor, chunk);\n        cursor = (s32)((u32)cursor + (u32)chunk);\n        linear += chunk;\n        count = (s32)((u32)count - (u32)chunk);\n        if (cursor >= capacity) {\n            cursor = 0;\n        }\n    }\n    return cursor;\n}'}
BINDINGS={88:[('R_MIPS_26','memcpy')]}


def digest(data):return hashlib.sha256(data).hexdigest()
def diagnostics(text):return re.sub(r'line\s+\d+','line #',re.sub(r'\S+\.c','<unit>',text))


def snapshot(output):
    result={}
    for name,wanted in INPUTS.items():
        data=(output/('before-'+name.replace('/','_'))).read_bytes()
        if digest(data)!=wanted:raise ValueError('Ring historical input changed: '+name)
        result[name]=data
    return result


def freeze(root,output):
    output.mkdir(parents=True,exist_ok=True)
    for name,wanted in INPUTS.items():
        data=(root/name).read_bytes()
        if digest(data)!=wanted:raise ValueError('Ring predecessor changed: '+name)
        p=output/('before-'+name.replace('/','_'))
        if p.exists()and p.read_bytes()!=data:raise ValueError('Ring snapshot changed: '+name)
        if not p.exists():p.write_bytes(data)
    p=output/'before-padded.o'
    if not p.exists():p.write_bytes((root/OBJECT).read_bytes())
    if digest(p.read_bytes())!=BEFORE_OBJECT_SHA:raise ValueError('Ring padded predecessor changed')
    return snapshot(output)


def recovered_owner(before):
    result=before
    for name,body in SELECTED.items():
        lo,hi=function_span(result,name)
        if result[lo:hi]!='s32 '+name+'() {\n    return 0;\n}':raise ValueError('Unknown ring stub: '+name)
        prototype='s32 '+name+'(u8 *ring, s32 capacity, s32 cursor, u8 *linear, s32 count);'
        if result.count('s32 '+name+'();')!=1:raise ValueError('Unknown ring prototype: '+name)
        result=result[:lo]+body+result[hi:]
        result=result.replace('s32 '+name+'();',prototype,1)
        marker='/* Non-matching C placeholders for asm/nonmatchings/game_70200/'+name+'.s. */\n'
        if result.count(marker)!=1:raise ValueError('Unknown ring recovery marker: '+name)
        result=result.replace(marker,'',1)
    return result.replace('// something with memcpy\n','',1)


def payload(obj,name):
    text,fs,rs=parse_object(obj);f=fs[name];raw=text[f['value']:f['value']+f['size']]
    words=struct.unpack('>%dI'%(len(raw)//4),raw);end=max(i for i,w in enumerate(words)if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero ring alignment tail')
    return raw[:end*4],{at-f['value']:v for at,v in rs.items()if f['value']<=at<f['value']+end*4}


def original(root,output,name):
    from tools.tests.test_game_view_list_setup import ViewListSetupTests
    context=type('RingOriginal',(),dict(root=root,out=output))
    return ViewListSetupTests.original.__func__(context,'original-ring-'+name,(root/TARGETS[name][2]).read_text(),name)


def truths(values):return {name:values['conker/conker.us.bin'][rom:rom+SIZE]for name,(_,rom,_)in TARGETS.items()}


def qualify(root,output):
    values=freeze(root,output);wanted=recovered_owner(values[SOURCE].decode())
    before,da=compile_owner(root,output,values[SOURCE].decode(),'before-owner')
    after,db=compile_owner(root,output,wanted,'after-owner')
    isolated,dc=compile_owner(root,output,'#include <ultra64.h>\n'+'\n'.join(SELECTED.values()),'selected')
    if diagnostics(da)!=diagnostics(db)or dc:raise ValueError('Ring compiler diagnostics: '+da+db+dc)
    linked,fs=link_owner(root,output,isolated,OWNER);truth=truths(values)
    for name in TARGETS:
        raw,rs=payload(isolated,name);at=fs[name]['value']
        if len(raw)!=SIZE or digest(raw)!=RAW_SHA[name]or rs!=BINDINGS or linked[at:at+SIZE]!=truth[name]:raise ValueError('Ring direct C differs: '+name)
        if payload(after,name)!=(raw,rs)or payload(original(root,output,name),name)!=(raw,rs):raise ValueError('Ring GNU/owner body differs: '+name)
    neighbors=same_functions(before,after,tuple(TARGETS))
    if neighbors!=14 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Ring raw neighbors/pools changed')
    padder=Path(parse_object.__code__.co_filename).with_name('pad_c_object.py')
    asm=output/'qualified-padded.s';obj=asm.with_suffix('.o')
    subprocess.run([sys.executable,str(padder),str(after),str(root/'conker/retail_layout.us.txt'),OWNER,str(asm),
        '--word-patches',str(root/'conker/retail_word_patches.us.csv')],check=True,capture_output=True,text=True)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(asm)],check=True,capture_output=True)
    old=output/'before-padded.o';a,fa=link_owner(root,output,old,OWNER);b,fb=link_owner(root,output,obj,OWNER)
    expected={name:dict(info)for name,info in fa.items()};image=bytearray(a)
    for name,(entry,_,_)in TARGETS.items():
        if expected[name]['size']!=12:raise ValueError('Unknown ring old extent')
        expected[name]['size']=SIZE;at=fb[name]['value'];slot=elf_slot_offset(values['conker/build/conker.us.elf'],entry,SIZE)
        if a[at:at+SIZE]!=values['conker/build/conker.us.elf'][slot:slot+SIZE]:raise ValueError('Ring old object/ELF differs')
        image[at:at+SIZE]=truth[name]
    if expected!=fb or bytes(image)!=b:raise ValueError('Ring padding changed another slot/address/extent')
    if same_functions(old,obj,tuple(TARGETS))!=neighbors or normalized_pools(old)!=normalized_pools(obj):raise ValueError('Ring padded neighbors/pools changed')
    (output/'proposed-owner.c').write_text(wanted)
    report=dict(functions=list(TARGETS),words=84,words_each=42,frame_each=48,relocations=2,new_guards=0,compiler_only=True,
        owner_diagnostics_unchanged=True,isolated_diagnostics_empty=True,preserved_neighbors=neighbors,all_owner_addresses_fixed=True,
        targets_size_before=12,targets_size_after=168,raw_SHA256=RAW_SHA)
    (output/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return report


def make_shadow(root,output):
    values=freeze(root,output)
    if (output/'proposed-owner.c').read_text()!=recovered_owner(values[SOURCE].decode()):raise ValueError('Ring shadow source changed')
    conker=root/'conker';shadow=output/'make-shadow';(shadow/'src').mkdir(parents=True,exist_ok=True)
    target=(shadow/'src/game_70200.c.o').relative_to(conker).as_posix()
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
    (output/'make-shadow-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown ring Make command: '+repr(args))
        args=[(output/'proposed-owner.c').relative_to(conker).as_posix()if a=='src/game_70200.c'else a for a in args]
        process=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected=(output/'after-owner-diagnostics.txt').read_text()if args[0]=='../ido/ido5.3_recomp/cc'else''
        if process.returncode or diagnostics(process.stdout+process.stderr)!=diagnostics(expected):raise ValueError('Ring Make failed: '+process.stdout+process.stderr)
        commands.append(args)
    actual=conker/target;cc=[a for a in commands if a[0]=='../ido/ido5.3_recomp/cc']
    if len(commands)!=3 or len(cc)!=1 or not all(x in cc[0]for x in('-O2','-g3'))or any('loopunroll'in a for a in cc[0]):raise ValueError('Ring Make profile changed')
    if same_functions(output/'after-owner.o',Path(str(actual)+'.compact'))!=16:raise ValueError('Ring Make raw owner differs')
    if link_owner(root,output,actual,OWNER)!=link_owner(root,output,output/'qualified-padded.o',OWNER):raise ValueError('Ring Make padded owner differs')
    report=dict(actual_Make_commands=3,normal_O2_g3=True,all_raw_functions_equal=True,padded_code_and_metadata_equal=True,cleanup_skipped=True,inherited_Make_warnings=plan.stderr)
    (output/'make-shadow.json').write_text(json.dumps(report,indent=2)+'\n');return report


def predicted_image(before,truth):
    if digest(before)!=INPUTS['conker/build/conker.us.elf']or set(truth)!=set(TARGETS)or any(len(x)!=SIZE for x in truth.values()):raise ValueError('Ring strict image inputs changed')
    result=bytearray(before)
    for name,(entry,_,_)in TARGETS.items():
        at=elf_slot_offset(before,entry,SIZE);result[at:at+SIZE]=truth[name]
        rows=[off for off,n,fields,_ in symbol_rows(before)if n==name and fields[1:3]==(entry,12)and fields[3]&15==2]
        if len(rows)!=1:raise ValueError('Ring symbol extent changed: '+name)
        struct.pack_into('>I',result,rows[0]+8,SIZE)
    return bytes(result)


def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Ring image differs from strict two-body/two-size prediction')


def predict(root,output):
    values=freeze(root,output);script=(root/'conker/build/conker.ld').read_text();old='build/src/game_70200.c.o'
    if script.count(old)!=1:raise ValueError('Unknown ring link input')
    link=output/'first-link.ld';link.write_text(script.replace(old,(output/'qualified-padded.o').relative_to(root/'conker').as_posix()));elf=output/'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',link.relative_to(root/'conker').as_posix(),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt',
        '-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(root/'conker').as_posix()],cwd=root/'conker',capture_output=True,check=True)
    before=values['conker/build/conker.us.elf'];actual=elf.read_bytes();truth=truths(values);check_image(before,actual,truth)
    code=sum(sum(a!=b for a,b in zip(before[elf_slot_offset(before,entry,SIZE):elf_slot_offset(before,entry,SIZE)+SIZE],truth[name]))for name,(entry,_,_)in TARGETS.items())
    changed=sum(a!=b for a,b in zip(before,actual));report=dict(exact_prediction=True,SHA256=digest(actual),changed_bytes=changed,code_bytes_changed=code,metadata_bytes_changed=changed-code,metadata_exclusions=0)
    (output/'first-link.json').write_text(json.dumps(report,indent=2)+'\n');return report


def audit(root,output):
    values=snapshot(output);wanted=predicted_image(values['conker/build/conker.us.elf'],truths(values))
    for name,old in values.items():
        expected=recovered_owner(old.decode()).encode()if name==SOURCE else wanted if name=='conker/build/conker.us.elf'else old
        if (root/name).read_bytes()!=expected:raise ValueError('Ring installed input differs: '+name)
    if (output/'first-linked.elf').read_bytes()!=wanted:raise ValueError('Ring first image changed')
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys()or {n for n in a if a[n]!=b[n]}!=set(TARGETS):raise ValueError('Ring changed another body/address')
    if parse_object(root/OBJECT)!=parse_object(output/'qualified-padded.o')or normalized_pools(root/OBJECT)!=normalized_pools(output/'qualified-padded.o'):raise ValueError('Ring installed padded owner differs')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Ring protected data changed')
    report=dict(functions=len(b),other_bodies_fixed=len(b)-2,all_addresses_fixed=True,target_words=84,strict_first_link_reproduced=True,game_data=data)
    (output/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n');return report
