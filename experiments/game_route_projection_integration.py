"""Qualify the projection's exact override, guarded contraction and first ELF prediction."""
import argparse
from contextlib import contextmanager
import csv
import hashlib
import io
import json
from pathlib import Path
import shlex
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_route_projection_call_lifetime_fit as candidate
from tools.experiments import game_route_projection_layout_normalizer as layout
from tools.experiments import game_route_projection_native as native
from tools.experiments.game_remaining_donor_candidates import compile_owner as normal_owner,link_owner
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD=native.BUILD
OWNER,FUNCTION,ENTRY,ROM=candidate.source.OWNER,candidate.source.FUNCTION,candidate.source.ENTRY,candidate.source.ROM
AFTER={
    'conker/build/conker.us.elf':'7eb93e57d28fed26f58b58751c8884b3478f1db71b3fc8b2766022c7d75d27c6',
    'conker/src/game/generated_B3020.c':'2c7d59f471640e516240dfe340ec3344eba574cbd371251b73e248d5804f7ed7',
    'conker/retail_word_patches.us.csv':'07994470d0e3d22e880a7bbd18188badd28eb5fde11ced8ec40bfa3176ff6647',
    'conker/Makefile':'5d18b2170461785d270be99353e9bacdf4717ff2fd5d85231b702132740cb99d',
}
INPUTS=candidate.INPUTS
SUCCESSOR_FILES={
    'conker/build/conker.us.elf':'after-elf',
    'conker/src/game/generated_B3020.c':'after-owner',
    'conker/retail_word_patches.us.csv':'after-guards',
    'conker/Makefile':'after-Makefile',
}
raw_read,raw_text=Path.read_bytes,Path.read_text


def freeze(root,out):return candidate.prior.freeze(root,out)


def compile_profile(root,out,body,name,unrolled=False):
    run=subprocess.run;commands=[]
    def profile(argv,**kwargs):
        if argv[0]==str(root/'ido/ido5.3_recomp/cc'):
            argv=list(argv)
            if not unrolled:argv.insert(argv.index('-O2'),'-Wo,-loopunroll,0')
            commands.append(argv)
        return run(argv,**kwargs)
    with patch.object(subprocess,'run',side_effect=profile):result=normal_owner(root,out,body,name)
    if len(commands)!=1:raise ValueError('Unexpected projection compiler invocation')
    (out/(name+'-command.json')).write_text(json.dumps(commands[0],indent=2)+'\n')
    return result


def recovered_owner(before):return candidate.source.recovered_owner(before,candidate.SELECTED)


def recovered_makefile(before):
    old='\t$(BUILD_DIR)/$(SRC_DIR)/game/generated_6A3D0.c.o\n'
    profile='$(BUILD_DIR)/$(SRC_DIR)/game/generated_B3020.c.o: CFLAGS += -Wo,-loopunroll,0\n'
    global_asm='GLOBAL_ASM_GENERATED_SLICE_O_FILES := $(filter $(GLOBAL_ASM_O_FILES),$(GENERATED_SLICE_O_FILES))'
    unpadded='UNPADDED_GLOBAL_ASM_O_FILES := $(filter-out $(RETAIL_PAD_O_FILES) $(GLOBAL_ASM_GENERATED_SLICE_O_FILES),$(GLOBAL_ASM_O_FILES))'
    marker='# Keep the unrecovered factory\'s output unchanged.'
    if any(before.count(text)!=1 for text in (old,profile,marker,global_asm,unpadded)):
        raise ValueError('Unknown projection mixed-profile Makefile baseline')
    result=before.replace(old,old.rstrip()+' \\\n\t$(BUILD_DIR)/$(SRC_DIR)/game/generated_B3020.c.o\n')
    result=result.replace(profile,'B3020_NO_UNROLL_FLAG := -Wo,-loopunroll,0\n'+profile.replace('-Wo,-loopunroll,0','$(B3020_NO_UNROLL_FLAG)'))
    result=result.replace(global_asm,'GLOBAL_ASM_GENERATED_SLICE_O_FILES := $(filter-out $(BUILD_DIR)/$(SRC_DIR)/game/generated_B3020.c.o,$(filter $(GLOBAL_ASM_O_FILES),$(GENERATED_SLICE_O_FILES)))')
    result=result.replace(unpadded,unpadded.replace('$(RETAIL_PAD_O_FILES) ','$(RETAIL_PAD_O_FILES) $(MIXED_PROFILE_GENERATED_SLICE_O_FILES) '))
    recipe='''# Preserve every no-unroll neighbor; select only the complete route projection
# from its separately qualified normal-profile object.
$(BUILD_DIR)/$(SRC_DIR)/game/generated_B3020.c.o: \\
\t\t$(SRC_DIR)/game/generated_B3020.c $$(call generated_slice_asm,B3020) $$(wildcard asm/nonmatchings/generated_B3020/*.s) ../tools/pad_generated_object.py retail_word_patches.us.csv Makefile
\t$(PYTHON) $(ASM_PROCESSOR_DIR)/asm_processor.py $(OPT_FLAGS) $< > $(BUILD_DIR)/$<
\t$(CC) -c -32 $(CFLAGS) $(OPT_FLAGS) $(MIPSBIT) -o $@.compact $(BUILD_DIR)/$<
\t$(PYTHON) $(ASM_PROCESSOR_DIR)/asm_processor.py $(OPT_FLAGS) $< --post-process $@.compact \\
\t\t--assembler "$(AS) $(ASFLAGS)" --asm-prelude include/asm_processor_prelude.inc
\t$(CC) -c -32 $(filter-out $(B3020_NO_UNROLL_FLAG),$(CFLAGS)) $(OPT_FLAGS) $(MIPSBIT) -o $@.normal.compact $(BUILD_DIR)/$<
\t$(PYTHON) $(ASM_PROCESSOR_DIR)/asm_processor.py $(OPT_FLAGS) $< --post-process $@.normal.compact \\
\t\t--assembler "$(AS) $(ASFLAGS)" --asm-prelude include/asm_processor_prelude.inc
\t$(PYTHON) ../tools/pad_generated_object.py $@.compact $(call generated_slice_asm,B3020) $@.padded.s \\
\t\t--function-object func_150891E8=$@.normal.compact --word-patches retail_word_patches.us.csv --filename generated_B3020
\t$(AS) $(ASFLAGS) -o $@ $@.padded.s
\trm -f $@.compact $@.normal.compact $@.padded.s

'''
    return result.replace(marker,recipe+marker)


def recovered_guards(before,raw,bindings):
    normalized,moved=layout.normalize(raw,bindings);old=list(struct.unpack('>335I',raw));new=list(struct.unpack('>321I',normalized))
    order=layout.origins(old);kept=sorted(order);positions={source:index for index,source in enumerate(kept)}
    reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):raise ValueError('Existing projection guards')
    if not before.endswith(b'\n'):raise ValueError('Unterminated guard prefix')
    rows=[]
    def spec(entries):return ';'.join(k+':'+n for k,n in entries) or '-'
    for index,word in enumerate(old):
        omitted=index not in positions;destination=positions.get(index)
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(index*4),expected='0x%08X'%word,
            replacement='0x%08X'%(0 if omitted else new[destination]),
            expected_relocations=spec(bindings.get(index*4,[])),
            replacement_relocations='-' if omitted else spec(moved.get(destination*4,[])),
            note='Omit proven redundant route-scan word' if omitted else
                'Schedule semantic source word %d; normalize proven route projection layout'%order[destination],
            insert_after='',insert_after_relocations='',omit='true' if omitted else 'false'))
    output=io.StringIO(newline='');writer=csv.DictWriter(output,fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n');writer.writerows(rows)
    if len(rows)!=335 or sum(r['omit']=='true' for r in rows)!=14:raise ValueError('Changed projection guard extent')
    return before+output.getvalue().encode()


def padded(root,out,obj,name,guards,override=None):
    script=out/(name+'.s');script.write_text(emit_padded_assembly(obj,root/'conker/asm/B3020.s',
        function_objects=None if override is None else {FUNCTION:override},word_patches_path=guards,filename=OWNER))
    output=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
        '-I',str(root/'conker/include'),'-o',str(output),str(script)],check=True,capture_output=True)
    return output


def qualify(root,out):
    values=freeze(root,out);before=values['conker/src/game/generated_B3020.c'].decode();body=recovered_owner(before)
    primary,diag=compile_profile(root,out,body,'primary-no-unroll')
    original,old_diag=compile_profile(root,out,before,'before-no-unroll')
    override,over_diag=compile_profile(root,out,body,'override-normal',True)
    raw,bindings=candidate.checked(override)
    isolated,isolated_diag=normal_owner(root,out,candidate.prior.PREFIX+candidate.SELECTED,'isolated-normal')
    if candidate.checked(isolated)!=(raw,bindings) or set(parse_object(isolated)[1])!={FUNCTION}:
        raise ValueError('Isolated normal profile differs from complete projection')
    if any((diag,old_diag,over_diag,isolated_diag)):raise ValueError('Projection profile diagnostics')
    neighbor=candidate.source.neighbor
    if neighbor.same_functions(original,primary,(FUNCTION,))!=72 or neighbor.normalized_pools(original)!=neighbor.normalized_pools(primary):
        raise ValueError('Changed no-unroll primary neighbors or pools')
    guards=out/'qualified-guards.csv';guards.write_bytes(recovered_guards(values['conker/retail_word_patches.us.csv'],raw,bindings))
    old_guards=out/'baseline-guards.csv';old_guards.write_bytes(values['conker/retail_word_patches.us.csv'])
    baseline=padded(root,out,original,'baseline-padded',old_guards)
    output=padded(root,out,primary,'qualified-padded',guards,override)
    a,fa=link_owner(root,out,baseline,OWNER);b,fb=link_owner(root,out,output,OWNER)
    f=fb[FUNCTION];at=f['value'];span=values['conker/conker.us.bin'][ROM:ROM+1284]
    if f['size']!=1284 or b[at:at+1284]!=span:raise ValueError('Actual padded projection does not match retail')
    if fa.keys()!=fb.keys() or any(fa[n]['value']!=fb[n]['value'] or (n!=FUNCTION and fa[n]!=fb[n]) for n in fa):
        raise ValueError('Padded projection moved a function/neighbor extent')
    if a[:at]!=b[:at] or a[at+1284:]!=b[at+1284:]:raise ValueError('Padded projection changed another instruction')
    if neighbor.normalized_pools(baseline)!=neighbor.normalized_pools(output):raise ValueError('Padded projection changed data pools')
    actual=parse_object(primary)[1][FUNCTION]
    row=dict(raw_words=335,normalized_words=321,frame=120,retail_word_differences=0,guards=335,omitted=14,
        bindings=18,primary_target_words=actual['size']//4,no_unroll_neighbors=72,
        isolated_normal_raw_and_bindings_equal=True,normal_override_filters_only_owner_no_unroll_flag=True,
        actual_generated_padder_and_assembler=True,other_padded_bytes_addresses_extents_and_pools_fixed=True,
        raw_sha256=hashlib.sha256(raw).hexdigest(),installed=False,matching_credit=0)
    (out/'qualified-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    (out/'proposed-owner.c').write_text(body)
    (out/'proposed-Makefile').write_text(recovered_makefile(values['conker/Makefile'].decode()))
    return primary,override,output,row


def predicted_image(before,span):
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,1284);result[at:at+1284]=span
    rows=[r for r in symbol_rows(before) if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Unknown projection predecessor extent')
    struct.pack_into('>I',result,rows[0][0]+8,1284);return bytes(result)


def predict(root,out):
    values=freeze(root,out);_,_,obj,row=qualify(root,out)
    source=raw_text(root/'conker/build/conker.ld');old='build/src/game/'+OWNER+'.c.o'
    if source.count(old)!=1:raise ValueError('Unknown projection linker input')
    script=out/'predicted.ld';script.write_text(source.replace(old,obj.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
        '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image=raw_read(elf);expected=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+1284])
    if image!=expected:raise ValueError('Projection first prediction changes unrelated ELF bytes')
    result=dict(words=321,guards=335,omitted=14,only_target_code_and_symbol_extent_changed=True,
        elf_sha256=hashlib.sha256(image).hexdigest(),changed_bytes=sum(a!=b for a,b in zip(values['conker/build/conker.us.elf'],image)))
    first=out/'after-elf'
    if first.exists() and raw_read(first)!=image:raise ValueError('Changed first projection prediction')
    if not first.exists():first.write_bytes(image)
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n');return result


def make_shadow(root,out):
    values=freeze(root,out)
    if raw_text(out/'proposed-owner.c')!=recovered_owner(values['conker/src/game/generated_B3020.c'].decode()):
        raise ValueError('Changed shadow projection source')
    raw,bindings=candidate.checked(out/'override-normal.o')
    if raw_read(out/'qualified-guards.csv')!=recovered_guards(values['conker/retail_word_patches.us.csv'],raw,bindings):
        raise ValueError('Changed shadow projection guards')
    (out/'proposed-Makefile').write_text(recovered_makefile(values['conker/Makefile'].decode()))
    conker=root/'conker';shadow=out/'make-shadow';(shadow/'src/game').mkdir(parents=True,exist_ok=True)
    target=(shadow/'src/game/generated_B3020.c.o').relative_to(conker).as_posix()
    result=subprocess.run(['make','-n','-B','-f',str((out/'proposed-Makefile').relative_to(conker)),
        'BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True)
    (out/'make-shadow-plan.txt').write_text(result.stdout+result.stderr)
    baseline=subprocess.run(['make','-n','-B','-f','Makefile','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],
        cwd=conker,capture_output=True,text=True,check=True)
    (out/'make-shadow-baseline-plan.txt').write_text(baseline.stdout+baseline.stderr)
    def warnings(text):return [line.split(': warning: ',1)[1] if ': warning: ' in line else line for line in text.splitlines()]
    if warnings(result.stderr)!=warnings(baseline.stderr):raise ValueError('New Make dry-run diagnostics: '+result.stderr)
    invocations=[];flags=[]
    for line in result.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args:continue
        if args[0]=='rm':continue
        if args[0] not in ('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):
            raise ValueError('Unexpected shadow Make command: '+repr(args))
        args=[str((out/'proposed-owner.c').relative_to(conker)) if a=='src/game/generated_B3020.c' else
            str((out/'qualified-guards.csv').relative_to(conker)) if a=='retail_word_patches.us.csv' else a for a in args]
        if args[0]=='../ido/ido5.3_recomp/cc':flags.append(args.count('-Wo,-loopunroll,0'))
        redirect=None
        if '>' in args:
            if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unexpected shadow redirection')
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        process=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        if process.returncode or process.stderr or process.stdout and redirect is None:
            raise ValueError('Shadow Make command failed: '+process.stdout+process.stderr)
        if redirect is not None:redirect.write_text(process.stdout)
        invocations.append(args)
    if len(invocations)!=7 or flags!=[1,0]:raise ValueError('Wrong projection primary/override Make profile')
    actual=conker/target;normal=Path(str(actual)+'.normal.compact');candidate.checked(normal)
    if candidate.source.neighbor.same_functions(out/'primary-no-unroll.o',Path(str(actual)+'.compact'),())!=73:
        raise ValueError('Make primary compilation differs from qualification')
    a,fa=link_owner(root,out,out/'qualified-padded.o',OWNER);b,fb=link_owner(root,out,actual,OWNER)
    if (a,fa)!=(b,fb):raise ValueError('Actual Make recipe changed padded code or metadata')
    audit=dict(actual_expanded_Make_commands=7,primary_owner_flag_count=1,normal_override_flag_count=0,
        normal_raw_and_bindings_equal=True,all73_primary_functions_equal=True,padded_code_and_metadata_equal=True,
        only_inputs_substituted=['proposed-owner.c','qualified-guards.csv'],cleanup_skipped=True,
        production_source_and_build_artifacts_untouched=True,original_four_GLOBAL_ASM_bodies_preserved=True,
        inherited_Make_warnings=warnings(baseline.stderr))
    (out/'make-shadow.json').write_text(json.dumps(audit,indent=2)+'\n');return audit


def prepare_successor(root,out):
    values=freeze(root,out);make_shadow(root,out)
    raw,bindings=candidate.checked(out/'override-normal.o')
    after={
        'conker/build/conker.us.elf':raw_read(out/'after-elf'),
        'conker/src/game/generated_B3020.c':recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':recovered_guards(values['conker/retail_word_patches.us.csv'],raw,bindings),
        'conker/Makefile':recovered_makefile(values['conker/Makefile'].decode()).encode(),
    }
    if after['conker/build/conker.us.elf']!=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+1284]):
        raise ValueError('Changed first projection image')
    for path,data in after.items():
        target=out/SUCCESSOR_FILES[path]
        if target.exists() and raw_read(target)!=data:raise ValueError('Changed first projection successor: '+path)
        if not target.exists():target.write_bytes(data)
    return {path:hashlib.sha256(data).hexdigest() for path,data in after.items()}


def expected_inputs(root,out):
    values={path:raw_read(out/name) for path,name in SUCCESSOR_FILES.items()}
    if not AFTER or {p:hashlib.sha256(data).hexdigest() for p,data in values.items()}!=AFTER:
        raise ValueError('Changed first projection successor')
    return values


@contextmanager
def checkpoint_context():
    with patch.multiple(candidate.source.checkpoint,INPUTS=INPUTS,AFTER=AFTER,expected_inputs=expected_inputs):yield


@contextmanager
def historical_view(root,out):
    with checkpoint_context(),candidate.source.checkpoint.historical_view(root,out):yield


def verify(root,out,installed=False):
    with checkpoint_context():return candidate.source.checkpoint.verify(root,out,installed)


def audit(root,out):
    verify(root,out,True)
    for index,(path,digest) in enumerate(INPUTS.items()):
        if hashlib.sha256(raw_read(out/('before-%02d'%index))).hexdigest()!=digest or \
                hashlib.sha256(raw_read(root/path)).hexdigest()!=AFTER.get(path,digest):
            raise ValueError('Changed projection installed input: '+path)
    actual=raw_read(root/'conker/build/conker.us.elf');before=raw_read(out/'before-01')
    rom=raw_read(root/'conker/conker.us.bin')
    if actual!=raw_read(out/'after-elf') or actual!=predicted_image(before,rom[ROM:ROM+1284]):
        raise ValueError('Actual projection ELF differs from first prediction')
    from tools.match_progress import load_elf_functions
    from tools.check_game_data_layout import audit_layout
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or set(a)!=set(b) or [name for name in a if a[name]!=b[name]]!=[FUNCTION]:
        raise ValueError('Projection changed another function or address')
    candidate.source.neighbor.same_functions(out/'qualified-padded.o',root/'conker/build/src/game/generated_B3020.c.o')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Projection changed protected Game data')
    result=dict(functions=len(a),only_target_code_and_symbol_size_changed=True,all_addresses_preserved=True,
        first_prediction_reproduced=True,changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),guards=335,omitted=14,
        native_cases_per_build=native.CASES,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--predict',action='store_true')
    parser.add_argument('--make-shadow',action='store_true')
    parser.add_argument('--prepare-successor',action='store_true');parser.add_argument('--audit',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2];out=root/BUILD
    print(json.dumps(audit(root,out) if args.audit else prepare_successor(root,out) if args.prepare_successor else
        make_shadow(root,out) if args.make_shadow else predict(root,out) if args.predict else qualify(root,out)[3],indent=2))
