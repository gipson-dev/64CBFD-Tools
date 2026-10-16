"""Recover the two-row display-list initializer using the original SDK macros."""
import argparse
import csv
import difflib
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_view_initialization as previous
from tools.tests import view_initialization_checkpoint as checkpoint
from tools.pad_generated_object import parse_object
from tools.experiments.game_shared_overlay_pass import rename
from tools import pad_c_object

BUILD = 'conker/build/game-view-list-setup'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'game_476D0', 'func_1501A39C', 0x1501A39C, 0x4784C, 61
PATHS = dict(previous.PATHS,
    view_list_original='conker/asm/nonmatchings/game_476D0/func_1501A39C.s',
    view_list_caller_original='conker/asm/49D30.s',
    view_list_caller_owner='conker/src/game/generated_49D30.c')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    view_list_original='06649dd54e179dac479b0a511276926c3445cfece4d07cab11bc4328a43e5d48',
    view_list_caller_original='745b8aaa3c4871d74f21c6cf2479a494cb5e01bcb2df1486c8dbc56004c3ae41',
    view_list_caller_owner='0525fb887b599c579a51162b9f3bd44b7995c317b20035b56b847bffc8047520')
build = previous.build
DECLARATIONS = 'extern s32 D_800BE9C8[];\nextern Gfx D_8002C930[];\n\n'
INITIAL = '''/* Initialize both display-list rows and publish their command cursors. */
void func_1501A39C(void) {
    s32 *input;
    s32 *output;
    u32 viewportOffset;
    Gfx *commands;

    input = D_800BE9C8;
    output = D_800BE9D8;
    viewportOffset = 0;
    do {
        commands = (Gfx *)*input++;
        gSPSegment(commands++, 0, 0);
        gSPSegment(commands++, 0, 0);
        gSPDisplayList(commands++, D_8002C930);
        gDPSetDepthImage(commands++, D_800BE9C4);
        gSPViewport(commands++, (u32)D_800BE628 + viewportOffset + 0x40);
        *output++ = (s32)commands;
        viewportOffset += 0x10;
    } while (output != &D_800BE9E0);
}'''


def freeze(root, out):
    with patch.multiple(previous, PATHS=PATHS, BASELINE=BASELINE):
        previous.freeze(root, out)


def recovered_owner(before, body=None):
    body = SELECTED if body is None else body
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1501A39C() {\n    return 0;\n}':
        raise ValueError('Unknown view-list setup predecessor')
    result = before[:lo]+body.split('\n',1)[1]+before[hi:]
    lo = result.index('// NON-MATCHING: something along these lines\n')
    hi = result.index('/* Non-matching C placeholders for asm/nonmatchings/game_476D0/func_1501A490.s. */',lo)
    result = result[:lo]+'\n'+result[hi:]
    for old,new in (
        ('s32 func_1501A39C();',body.splitlines()[1][:-2]+';'),
        ('/* Generated placeholder declarations. */',DECLARATIONS+'/* Generated placeholder declarations. */'),
        ('/* Non-matching C placeholders for asm/nonmatchings/game_476D0/func_1501A39C.s. */',body.splitlines()[0])):
        if result.count(old)!=1:
            raise ValueError('Unknown view-list setup declaration/comment')
        result = result.replace(old,new,1)
    return result


def forms():
    yield 'initial', INITIAL
    yield 'late-input', INITIAL.replace('(Gfx *)*input++','(Gfx *)*input').replace(
        '        *output++ = (s32)commands;', '        input++;\n        *output++ = (s32)commands;')
    yield 'signed-offset', INITIAL.replace('u32 viewportOffset','s32 viewportOffset')
    yield 'offset-before-output', INITIAL.replace(
        '        *output++ = (s32)commands;\n        viewportOffset += 0x10;',
        '        viewportOffset += 0x10;\n        *output++ = (s32)commands;')
    yield 'less-output', INITIAL.replace('output != &D_800BE9E0','output < &D_800BE9E0')
    yield 'word-less-output', INITIAL.replace('output != &D_800BE9E0','(u32)output < (u32)&D_800BE9E0')
    yield 'word-not-equal-output', INITIAL.replace('output != &D_800BE9E0','(u32)output != (u32)&D_800BE9E0')


def compile_owner(root,out,content,label,no_unroll=False):
    run = subprocess.run
    def invoke(command,*args,**kwargs):
        if no_unroll and str(command[0])==str(root/'ido/ido5.3_recomp/cc'):
            command = [command[0],'-Wo,-loopunroll,0',*command[1:]]
        return run(command,*args,**kwargs)
    with patch.object(subprocess,'run',side_effect=invoke):
        return build.compile_owner(root,out,content,label)


def carrier_forms():
    late = dict(forms())['late-input']
    typed = INITIAL.replace('s32 *input','Gfx **input').replace('s32 *output','Gfx **output').replace(
        'input = D_800BE9C8','input = (Gfx **)D_800BE9C8').replace(
        'output = D_800BE9D8','output = (Gfx **)D_800BE9D8').replace(
        '(Gfx *)*input++','*input++').replace('(s32)commands','commands').replace(
        'output != &D_800BE9E0','output != (Gfx **)&D_800BE9E0')
    for label,body in (('word',INITIAL),('late',late),('pointer',typed)):
        yield label+'-return-cursor', body.replace('void func_','Gfx *func_').replace(
            '\n}', '\n    return commands;\n}')
        if label=='pointer':
            yield 'pointer-void',body
            yield 'pointer-late-void',body.replace('commands = *input++;','commands = *input;').replace(
                '        *output++ = commands;', '        input++;\n        *output++ = commands;')


SELECTED = dict(forms())['late-input']
RAW_SHA256 = '3f1e319ef790a96ec3c8abbeca3afe9aa922c1dc499eb8113055368690439021'
RELOCATIONS = {}
for hi,lo,name in ((0x18,0x34,'D_800BE9C8'),(0x1C,0x38,'D_800BE9D8'),
        (0x20,0x50,'D_8002C930'),(0x24,0x4C,'D_800BE9E0'),
        (0x28,0x48,'D_800BE628'),(0x30,0x40,'D_800BE9C4')):
    RELOCATIONS[hi] = [('R_MIPS_HI16',name)]
    RELOCATIONS[lo] = [('R_MIPS_LO16',name)]
ROLES = {2:3,3:11,4:10,5:2,6:4,7:5,8:6,9:7,10:8,11:9}
ROUTING = {0x1C:0x20,0x20:0x1C,0x34:0x40,0x38:0x44,0x3C:0x48,0x40:0x4C,
    0x44:0x38,0x48:0x50,0x4C:0x34,0x50:0x3C,0xB4:0xB8,0xB8:0xB4,0xCC:0xD4,0xD4:0xCC}
MAKE_RULE = '''# Only the two-row graphics initializer uses the retail no-unroll profile.
# Keep every neighboring function in the established normal-profile object.
$(BUILD_DIR)/$(SRC_DIR)/game_476D0.c.o: \\
\t\t$(SRC_DIR)/game_476D0.c $(RETAIL_LAYOUT) ../tools/pad_c_object.py ../tools/pad_generated_object.py retail_word_patches.us.csv Makefile
\t$(CC) -c -32 $(CFLAGS) $(OPT_FLAGS) $(MIPSBIT) -o $@.compact $<
\t$(CC) -c -32 $(CFLAGS) $(OPT_FLAGS) -Wo,-loopunroll,0 $(MIPSBIT) -o $@.nounroll.compact $<
\t$(PYTHON) ../tools/pad_c_object.py $@.compact $(RETAIL_LAYOUT) game_476D0 $@.padded.s \\
\t\t--function-object func_1501A39C=$@.nounroll.compact --word-patches retail_word_patches.us.csv
\t$(AS) $(ASFLAGS) -o $@ $@.padded.s
\trm -f $@.compact $@.nounroll.compact $@.padded.s

'''


def checked_object(obj):
    text,functions,relocations = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value']+f['size']]
    bindings = {a-f['value']:r for a,r in relocations.items() if f['value']<=a<f['value']+f['size']}
    pools = {n:d for n,(_,d) in previous.sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=244 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=RELOCATIONS or pools:
        raise ValueError('Unknown view-list setup object/bindings/pools')
    return list(struct.unpack('>61I',raw)),bindings


def normalized_instructions(obj):
    words,bindings = checked_object(obj)
    return {at:(rename(words[ROUTING.get(at,at)//4],ROLES),bindings.get(ROUTING.get(at,at),[]))
        for at in range(0,244,4)}


def guarded_manifest(out,obj):
    before = (out/'before-guards').read_bytes()
    reader = csv.DictReader(io.StringIO(before.decode()))
    fields = reader.fieldnames
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):
        raise ValueError('View-list setup is already guarded')
    words,bindings = checked_object(obj)
    rows = []
    spec = lambda rel:';'.join(kind+':'+name for kind,name in rel) or '-'
    for at,(replacement,rel) in normalized_instructions(obj).items():
        if replacement==words[at//4] and rel==bindings.get(at,[]):continue
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%at,
            expected='0x%08X'%words[at//4],replacement='0x%08X'%replacement,
            expected_relocations=spec(bindings.get(at,[])),replacement_relocations=spec(rel),
            note='Normalize closed two-row graphics scratch roles and independent schedule',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=38:raise ValueError('Unknown view-list setup guard count')
    added = io.StringIO(newline='')
    writer = csv.DictWriter(added,fieldnames=fields,lineterminator='\n');writer.writerows(rows)
    return before+added.getvalue().encode()


def checked_manifest(data,out,obj):
    if data!=guarded_manifest(out,obj):raise ValueError('Changed view-list setup manifest')
    return data


def recovered_makefile(before):
    anchor = '# The recovered audio bootstrap perturbs IDO\'s translation-unit state'
    if before.count(anchor)!=1 or 'game_476D0.c.o: \\' in before:
        raise ValueError('Unknown view-list setup Makefile predecessor')
    return before.replace(anchor,MAKE_RULE+anchor,1)


def qualify(root,out):
    obj,words,row = measure(root,out,'qualified',SELECTED,True)
    checked_object(obj)
    before = (out/'before-frustum_owner').read_text()
    old,diag = compile_owner(root,out,before,'neighbor-before')
    primary,normal_diag = compile_owner(root,out,recovered_owner(before),'qualified-normal')
    if row['diagnostics'] or diag or normal_diag:raise ValueError('Changed view-list setup diagnostics')
    a,b = parse_object(old),parse_object(primary)
    if set(a[1])!=set(b[1]):raise ValueError('Changed view-list setup function set')
    for name,f in a[1].items():
        if name==FUNCTION:continue
        g = b[1][name]
        relative = lambda p,s:{at-s['value']:v for at,v in p[2].items() if s['value']<=at<s['value']+s['size']}
        if a[0][f['value']:f['value']+f['size']]!=b[0][g['value']:g['value']+g['size']] or relative(a,f)!=relative(b,g):
            raise ValueError('Changed normal-profile view-list neighbor: '+name)
    guards = out/'normalized-guards.csv';guards.write_bytes(guarded_manifest(out,obj))
    assembly = out/'qualified-padded.s'
    assembly.write_text(pad_c_object.emit_padded_assembly(primary,root/PATHS['layout'],OWNER,
        word_patches_path=guards,function_objects={FUNCTION:obj}))
    padded = assembly.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(assembly)],capture_output=True,check=True)
    data,functions = build.link_owner(root,out,padded,OWNER);f = functions[FUNCTION]
    slot = data[f['value']:f['value']+244]
    if f['size']!=244 or slot!=(out/'before-retail_rom').read_bytes()[ROM:ROM+244]:
        raise ValueError('View-list setup normalized slot differs')
    row.update(byte_exact=True,new_guards=38,unchanged_normal_neighbors=len(a[1])-1,
        slot_sha256=hashlib.sha256(slot).hexdigest(),target_only_no_unroll=True)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,words,row


def expected_inputs(root,out):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    before = (out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:
        raise ValueError('Changed view-list setup image predecessor')
    row = next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,12):raise ValueError('Unknown view-list setup predecessor extent')
    data = bytearray(before)
    at = elf_slot_offset(before,ENTRY,244)
    data[at:at+244] = (out/'before-retail_rom').read_bytes()[ROM:ROM+244]
    struct.pack_into('>I',data,row[0]+8,244)
    return dict(elf=bytes(data),frustum_owner=recovered_owner((out/'before-frustum_owner').read_text()).encode(),
        guards=guarded_manifest(out,out/'qualified.o'),
        makefile=recovered_makefile((out/'before-makefile').read_text()).encode())


def prelink_prediction(root,out):
    _,padded,_,_ = qualify(root,out)
    live = lambda:{k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()}
    capture = out/'link-inputs.json'
    if not capture.exists():
        if live()!=BASELINE:raise ValueError('View-list link capture must precede installation')
        for name,path in (('before-linkscript','conker/build/conker.ld'),('before-owner.o','conker/build/src/'+OWNER+'.c.o')):
            (out/name).write_bytes((root/path).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest()
            for n in ('before-linkscript','before-owner.o')},indent=2)+'\n')
    for name,digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Changed view-list setup link capture')
    link = (out/'before-linkscript').read_text();needle = 'build/src/'+OWNER+'.c.o(.text);'
    if link.count(needle)!=1:raise ValueError('Unknown view-list setup link selector')
    for label,obj in (('baseline',out/'before-owner.o'),('prediction',padded)):
        script = out/(label+'.ld')
        script.write_text(link.replace(needle,str(obj.relative_to(root/'conker'))+'(.text);',1))
        subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str((out/('prelink-'+label+'.elf')).relative_to(root/'conker'))],
            cwd=root/'conker',capture_output=True,check=True)
    if (out/'prelink-baseline.elf').read_bytes()!=(out/'before-elf').read_bytes():
        raise ValueError('View-list predecessor image not reproduced')
    expected = expected_inputs(root,out)
    actual = (out/'prelink-prediction.elf').read_bytes()
    if actual!=expected['elf']:
        raise ValueError('View-list link differs outside its slot/extent prediction')
    hashes = {k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}
    initial = out/'initial-prediction.json'
    if not initial.exists():
        if live()!=BASELINE:raise ValueError('View-list prediction must precede installation')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first view-list setup prediction')
    row = dict(after=hashes,changed_ELF_bytes=sum(a!=b for a,b in zip((out/'before-elf').read_bytes(),actual)),
        body_bytes=244,slot_bytes=244,new_guards=38,metadata_exclusions=0)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def installation_patch(root,out):
    expected = expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}:
        raise ValueError('Changed first view-list setup installation prediction')
    edits = []
    for key in ('frustum_owner','guards','makefile'):
        path = root/PATHS[key];before = path.read_bytes();after = expected[key]
        if hashlib.sha256(before).hexdigest()!=BASELINE[key]:
            raise ValueError('View-list setup live input changed before installation: '+key)
        diff = list(difflib.unified_diff(before.decode().splitlines(),after.decode().splitlines(),n=3,lineterm=''))
        edits.append('*** Update File: '+str(path)+'\n'+'\n'.join('@@' if line.startswith('@@') else line for line in diff[2:]))
    return '*** Begin Patch\n'+'\n'.join(edits)+'\n*** End Patch\n'


def measure(root, out, label='selected', body=None, no_unroll=False):
    freeze(root,out)
    content = recovered_owner((out/'before-frustum_owner').read_text(),body)
    obj,diagnostics = compile_owner(root,out,content,label,no_unroll)
    text,functions,relocations = parse_object(obj)
    f = functions[FUNCTION]
    data,placed = build.link_owner(root,out,obj,OWNER)
    words = list(struct.unpack_from('>%dI'%(f['size']//4),data,placed[FUNCTION]['value']))
    truth = list(struct.unpack_from('>61I',(out/'before-retail_rom').read_bytes(),ROM))
    slot = words+[0]*max(0,WORDS-len(words))
    row = dict(label=label,words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(slot,truth))+max(0,len(words)-WORDS),
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(slot,truth)) if a!=b],
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:r for a,r in relocations.items() if f['value']<=a<f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in previous.sections(obj).items()
            if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screens',action='store_true')
    parser.add_argument('--profiles',action='store_true')
    parser.add_argument('--carriers',action='store_true')
    parser.add_argument('--qualify',action='store_true')
    parser.add_argument('--prelink',action='store_true')
    parser.add_argument('--prepare',action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.prepare:
        print(installation_patch(root,root/BUILD),end='')
        raise SystemExit(0)
    if args.prelink:
        print(json.dumps(prelink_prediction(root,root/BUILD),indent=2),flush=True)
        raise SystemExit(0)
    if args.qualify:
        print(json.dumps(qualify(root,root/BUILD)[3]),flush=True)
        raise SystemExit(0)
    for label,body in (carrier_forms() if args.carriers else forms() if args.screens else [('selected',SELECTED)]):
        for no_unroll in ((False,True) if args.profiles else (False,)):
            row = measure(root,root/BUILD,label+('-no-unroll' if no_unroll else ''),body,no_unroll)[2]
            print(json.dumps({k:row[k] for k in ('label','words','frame','differences','diagnostics','raw_sha256','pools')}),flush=True)
