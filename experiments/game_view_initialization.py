"""Restore view-buffer allocation, split-height rounding and projection startup."""
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

from tools.experiments import game_frame_timing_fitting as previous
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_shared_overlay_pass import rename
from tools.pad_generated_object import parse_object
from tools import pad_c_object

BUILD = 'conker/build/game-view-initialization'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'game_476D0', 'func_1501A220', 0x1501A220, 0x476D0, 95
PATHS = dict(previous.PATHS, view_init_original='conker/asm/nonmatchings/game_476D0/func_1501A220.s',
    view_init_caller='conker/asm/nonmatchings/game_34F20/func_15007B3C.s',
    view_init_caller_owner='conker/src/game_34F20.c', view_init_constants='conker/asm/data/23B3A0.rodata.s',
    view_init_allocator='conker/src/init_3C40.c')
BASELINE = dict(previous.BASELINE,
    view_init_original='da7b442df6b30f6a600766a164d4240eacd91716f2aed05a5a5a68fc642ab79f',
    view_init_caller='fbe6f895bfe7849d87ef1a8b9a32bdffaaa0b6c64032c99c2e919cce9345e422',
    view_init_constants='b6e4c87b32c839501d9d088617884a06c0c7b687de3d56f6488dba828c0becfd',
    view_init_caller_owner='8700a34ad41475c20756d7ceef7d75bd7e87f29478547e6e2b3e80befdd9c5ab',
    view_init_allocator='7345e09fd962a1ddde96f352e3ce0ba3f1bdcff8ad512b306e3b860fb1682bdb')
build = previous.build
DECLARATIONS = '''/* Keep the retail float factor distinct from the legacy integer declaration. */
extern const f32 D_800968E0;
s32 allocate_memory(s32 size, s32 tag, s32 pool, s32 flags);
void func_150006E0(s32 category);
void func_1510B070(s32 mode);

'''
INITIAL = '''/* Allocate view state, round the single-view height and initialize projections. */
void func_1501A220(s32 requestedViews, s32 projectionMode) {
    u32 slots;
    s32 index;
    f32 height;
    s32 rounded;

    D_80082FA0 = requestedViews;
    if (requestedViews == 0) {
        slots = 1;
    } else {
        slots = (u32)requestedViews + 2;
    }
    D_800BE628 = allocate_memory((s32)((slots * 3) << 7), 1, 1, 0);
    D_800BE62C = allocate_memory((s32)(slots * 16), 1, 1, 0);
    if (D_80082FA0 == 1) {
        height = (f32)D_800BE63C[0] - 2.0f;
        rounded = (s32)(height * D_800968E0);
        D_800BE6B8 = (f32)(rounded - rounded % 4) / height;
    }
    func_150006E0(D_800BE9F0);
    for (index = 0; index <= D_80082FA0; index = (s32)((u32)index + 1)) {
        func_1501A8C0(index, D_80082FA0, 1023, 0);
    }
    if (D_80082FA0 != 0) {
        func_1501A8C0(index, 0, 1023, 0);
    }
    D_800BE617 = 1;
    D_800BE614 = 1;
    D_800BE635 = 0;
    func_1510B070(projectionMode);
}'''
SELECTED = INITIAL


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    with patch.multiple(previous.previous, PATHS=PATHS, BASELINE=BASELINE):
        previous.previous.freeze(root, out)


def recovered_owner(before, selected=None):
    selected = SELECTED if selected is None else selected
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1501A220() {\n    return 0;\n}':
        raise ValueError('Unknown view-initialization predecessor')
    result = before[:lo]+selected.split('\n',1)[1]+before[hi:]
    start = result.index('// NON-MATCHING: 80% there\n')
    end = result.index('/* Non-matching C placeholders for asm/nonmatchings/game_476D0/func_1501A39C.s. */', start)
    result = result[:start]+result[end:]
    edits = (
        ('#include "variables.h"', '#define D_800968E0 ViewInitLegacyFactorWord\n#include "variables.h"\n#undef D_800968E0\n\n'+DECLARATIONS.rstrip()),
        ('s32 func_1501A220();', selected.splitlines()[1][:-2]+';'),
        ('/* Non-matching C placeholders for asm/nonmatchings/game_476D0/func_1501A220.s. */',
            '/* Allocate view state, round the single-view height and initialize projections. */'))
    for old,new in edits:
        if result.count(old) != 1:
            raise ValueError('Unknown view-initialization interface/declaration')
        result = result.replace(old,new,1)
    return result


def forms():
    yield 'initial', INITIAL
    yield 'signed-slots', INITIAL.replace('    u32 slots;', '    s32 slots;').replace(
        'slots = (u32)requestedViews + 2;', 'slots = (s32)((u32)requestedViews + 2);').replace(
        '(slots * 3)', '((u32)slots * 3)').replace('(slots * 16)', '((u32)slots * 16)')
    yield 'word-index', INITIAL.replace('    s32 index;', '    u32 index;').replace(
        'index <= D_80082FA0', '(s32)index <= D_80082FA0').replace(
        'index = (s32)((u32)index + 1)', 'index++')
    for size, scaled, cached in ((True,False,False),(False,True,False),(False,False,True),
            (True,True,False),(True,False,True),(False,True,True),(True,True,True)):
        body = INITIAL
        if size:
            body = body.replace('(s32)((slots * 3) << 7)', '(s32)(slots * sizeof(ViewProjection476D0))')
        if scaled:
            body = body.replace('    f32 height;', '    f32 height;\n    f32 scaledHeight;').replace(
                '        rounded = (s32)(height * D_800968E0);',
                '        scaledHeight = height * D_800968E0;\n        rounded = (s32)scaledHeight;')
        if cached:
            body = body.replace('    s32 index;', '    s32 index;\n    s32 viewCount;').replace(
                '    D_80082FA0 = requestedViews;', '    viewCount = requestedViews;\n    D_80082FA0 = viewCount;').replace(
                'if (requestedViews == 0)', 'if (viewCount == 0)').replace(
                '(u32)requestedViews + 2', '(u32)viewCount + 2').replace(
                'index <= D_80082FA0', 'index <= (viewCount = D_80082FA0)').replace(
                'func_1501A8C0(index, D_80082FA0,', 'func_1501A8C0(index, viewCount,').replace(
                'if (D_80082FA0 != 0)', 'if (viewCount != 0)')
        yield 'fit-%d%d%d'%(size,scaled,cached), body


def allocation_forms():
    body = dict(forms())['fit-110']
    live = body.replace('index <= D_80082FA0',
        'index <= (requestedViews = D_80082FA0)').replace(
        'func_1501A8C0(index, D_80082FA0,', 'func_1501A8C0(index, requestedViews,').replace(
        'if (D_80082FA0 != 0)', 'if (requestedViews != 0)')
    yield 'live-count-parameter', live
    unsigned = live.replace('s32 requestedViews,', 'u32 requestedViews,').replace(
        'D_80082FA0 = requestedViews;', 'D_80082FA0 = (s32)requestedViews;').replace(
        'index <= (requestedViews = D_80082FA0)', 'index <= (s32)(requestedViews = D_80082FA0)')
    yield 'unsigned-live-count-parameter', unsigned
    yield 'unsigned-live-global-gate', unsigned.replace('if (requestedViews == 0)', 'if (D_80082FA0 == 0)')
    yield 'signed-size-control', body.replace('    u32 slots;', '    s32 slots;').replace(
        'slots = (u32)requestedViews + 2;', 'slots = requestedViews + 2;').replace(
        '(s32)(slots * sizeof(ViewProjection476D0))', 'slots * 0x180').replace(
        '(s32)(slots * 16)', 'slots * 16')
    for name, size in (('repeated-size-ternary','(requestedViews == 0 ? 1U : (u32)requestedViews + 2)'),
            ('repeated-size-count','(requestedViews != 0 ? (u32)requestedViews + 2 : 1U)')):
        yield name, body.replace('(s32)(slots * 16)', '(s32)('+size+' * 16)')


SELECTED = dict(allocation_forms())['live-count-parameter'].replace('requestedViews', 'viewCount')
RAW_SHA256 = '1c22c489f8afee8c522a18f879ceea435dddc4d2495ff409c3b905bf788ffa95'
RELOCATIONS = {}
for hi,lo,name in ((8,20,'D_80082FA0'),(84,88,'D_800BE628'),(112,116,'D_800BE62C'),
        (128,140,'D_800BE63C'),(156,160,'D_800968E0'),(168,232,'D_800BE6B8'),
        (136,240,'D_800BE9F0'),(324,328,'D_800BE617'),(332,336,'D_800BE614'),(340,344,'D_800BE635')):
    RELOCATIONS[hi] = [('R_MIPS_HI16',name)]
    RELOCATIONS[lo] = [('R_MIPS_LO16',name)]
for offset,name in ((76,'allocate_memory'),(104,'allocate_memory'),(236,'func_150006E0'),
        (268,'func_1501A8C0'),(312,'func_1501A8C0'),(348,'func_1510B070')):
    RELOCATIONS[offset] = [('R_MIPS_26',name)]


def checked_object(obj):
    text, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value']+f['size']]
    bindings = {a-f['value']:r for a,r in relocations.items() if f['value']<=a<f['value']+f['size']}
    pools = {n:d for n,(_,d) in sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=380 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=RELOCATIONS or pools:
        raise ValueError('Unknown view-initialization object/bindings/pools')
    return list(struct.unpack('>95I',raw)), bindings


def normalized_instructions(obj):
    words, bindings = checked_object(obj)
    result = {i*4:(word,bindings.get(i*4,[])) for i,word in enumerate(words)}
    # S1 aliases incoming A0 after the moved copy. Preserve the old S1 save first.
    routing = {0xC:0x14,0x10:0x18,0x14:0xC,0x18:0x1C,0x1C:0x20,0x20:0x28,0x24:0x24,0x28:0x10}
    for target, origin in routing.items():
        word = words[origin//4]
        if target in (0x20,0x24):
            word = rename(word,{17:4})
        result[target] = word, bindings.get(origin,[])
    return result


def guarded_manifest(out, obj):
    before = (out/'before-guards').read_bytes()
    reader = csv.DictReader(io.StringIO(before.decode()))
    fields = reader.fieldnames
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in reader):
        raise ValueError('View initialization is already guarded')
    words,bindings = checked_object(obj)
    normalized = normalized_instructions(obj)
    added = io.StringIO(newline='')
    writer = csv.DictWriter(added,fieldnames=fields,lineterminator='\n')
    spec = lambda rows:';'.join(kind+':'+name for kind,name in rows) or '-'
    rows = []
    for offset,(replacement,rel) in normalized.items():
        expected = words[offset//4]
        if expected==replacement and rel==bindings.get(offset,[]):
            continue
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%offset,
            expected='0x%08X'%expected,replacement='0x%08X'%replacement,
            expected_relocations=spec(bindings.get(offset,[])),replacement_relocations=spec(rel),
            note='Normalize closed view-initializer prologue schedule and live argument aliases',
            insert_after='',insert_after_relocations='',omit='false'))
    if len(rows)!=8:
        raise ValueError('Unknown view-initialization guard count')
    writer.writerows(rows)
    return before+added.getvalue().encode()


def checked_manifest(data, out, obj):
    if data!=guarded_manifest(out,obj):
        raise ValueError('Changed view-initialization guarded manifest')
    return data


def qualify(root, out):
    obj, words, row = measure(root,out,'qualified')
    checked_object(obj)
    before = (out/'before-frustum_owner').read_text()
    old_obj, diagnostics = build.compile_owner(root,out,before,'neighbor-before')
    if diagnostics or row['diagnostics']:
        raise ValueError('Changed view-initialization diagnostics')
    old,new = parse_object(old_obj),parse_object(obj)
    if set(old[1])!=set(new[1]):
        raise ValueError('Changed view-initialization owner function set')
    for name,f in old[1].items():
        if name==FUNCTION:
            continue
        g = new[1][name]
        relative = lambda p,s:{a-s['value']:r for a,r in p[2].items() if s['value']<=a<s['value']+s['size']}
        if old[0][f['value']:f['value']+f['size']]!=new[0][g['value']:g['value']+g['size']] or relative(old,f)!=relative(new,g):
            raise ValueError('Changed view-initialization neighbor: '+name)
    guards = out/'normalized-guards.csv'
    guards.write_bytes(guarded_manifest(out,obj))
    assembly = out/'qualified-padded.s'
    assembly.write_text(pad_c_object.emit_padded_assembly(obj,root/PATHS['layout'],OWNER,word_patches_path=guards))
    padded = assembly.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(assembly)],capture_output=True,check=True)
    data,functions = build.link_owner(root,out,padded,OWNER)
    f = functions[FUNCTION]
    slot = data[f['value']:f['value']+380]
    if f['size']!=380 or slot!=(out/'before-retail_rom').read_bytes()[ROM:ROM+380]:
        raise ValueError('View-initialization normalized slot differs')
    row.update(byte_exact=True,new_guards=8,body_words=95,slot_words=95,unchanged_neighbors=len(old[1])-1,
        slot_sha256=hashlib.sha256(slot).hexdigest())
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,words,row


def measure(root, out, label='selected', selected=None):
    freeze(root,out)
    content = recovered_owner((out/'before-frustum_owner').read_text(), selected)
    obj, diagnostics = build.compile_owner(root,out,content,label)
    text, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    data, placed = build.link_owner(root,out,obj,OWNER)
    words = list(struct.unpack_from('>%dI'%(f['size']//4),data,placed[FUNCTION]['value']))
    truth = list(struct.unpack_from('>95I',(out/'before-retail_rom').read_bytes(),ROM))
    slot = words + [0]*max(0,WORDS-len(words))
    row = dict(label=label,words=len(words),frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(slot,truth))+max(0,len(words)-WORDS),diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:r for a,r in relocations.items() if f['value']<=a<f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items()
            if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def expected_inputs(root,out):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    before = (out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:
        raise ValueError('Changed view-initialization image predecessor')
    slot = (out/'before-retail_rom').read_bytes()[ROM:ROM+380]
    row = next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,12):
        raise ValueError('Unknown view-initialization predecessor extent')
    data = bytearray(before)
    at = elf_slot_offset(before,ENTRY,380)
    data[at:at+380] = slot
    struct.pack_into('>I',data,row[0]+8,380)
    path = out/'structural-prediction.elf'
    if not path.exists():path.write_bytes(data)
    if path.read_bytes()!=data:raise ValueError('Changed first view-initialization structural image')
    obj = out/'qualified.o'
    return dict(elf=bytes(data),
        frustum_owner=recovered_owner((out/'before-frustum_owner').read_text()).encode(),
        guards=guarded_manifest(out,obj))


def prelink_prediction(root,out):
    _,padded,_,_=qualify(root,out)
    live = lambda:{k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()}
    capture = out/'link-inputs.json'
    if not capture.exists():
        if live()!=BASELINE:raise ValueError('View-initialization link capture must precede installation')
        for name,path in (('before-linkscript','conker/build/conker.ld'),('before-owner.o','conker/build/src/'+OWNER+'.c.o')):
            (out/name).write_bytes((root/path).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest()
            for n in ('before-linkscript','before-owner.o')},indent=2)+'\n')
    for name,digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Changed view-initialization link capture')
    link = (out/'before-linkscript').read_text()
    needle = 'build/src/'+OWNER+'.c.o(.text);'
    if link.count(needle)!=1:raise ValueError('Unknown view-initialization link selector')
    for label,obj in (('baseline',out/'before-owner.o'),('prediction',padded)):
        script = out/(label+'.ld')
        script.write_text(link.replace(needle,str(obj.relative_to(root/'conker'))+'(.text);',1))
        result = subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str((out/('prelink-'+label+'.elf')).relative_to(root/'conker'))],
            cwd=root/'conker',capture_output=True,text=True)
        if result.returncode:raise ValueError(result.stderr)
    if (out/'prelink-baseline.elf').read_bytes()!=(out/'before-elf').read_bytes():
        raise ValueError('View-initialization predecessor image not reproduced')
    expected = expected_inputs(root,out)
    actual = (out/'prelink-prediction.elf').read_bytes()
    if actual!=expected['elf']:
        raise ValueError('View-initialization link differs outside its exact slot/extent prediction')
    hashes = {k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}
    initial = out/'initial-prediction.json'
    if not initial.exists():
        if live()!=BASELINE:raise ValueError('View-initialization prediction must precede installation')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first view-initialization prediction')
    row = dict(after=hashes,changed_ELF_bytes=sum(a!=b for a,b in zip((out/'before-elf').read_bytes(),actual)),
        body_bytes=380,slot_bytes=380,new_guards=8,metadata_exclusions=0)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}:
        raise ValueError('Changed first view-initialization installation prediction')
    edits=[]
    for key in ('frustum_owner','guards'):
        path=root/PATHS[key];before=path.read_bytes();after=expected[key]
        if hashlib.sha256(before).hexdigest()!=BASELINE[key]:
            raise ValueError('View-initialization live input changed before installation: '+key)
        diff=list(difflib.unified_diff(before.decode().splitlines(),after.decode().splitlines(),n=3,lineterm=''))
        edits.append('*** Update File: '+str(path)+'\n'+'\n'.join('@@' if line.startswith('@@') else line for line in diff[2:]))
    return '*** Begin Patch\n'+'\n'.join(edits)+'\n*** End Patch\n'


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screens', action='store_true')
    parser.add_argument('--allocations', action='store_true')
    parser.add_argument('--prelink', action='store_true')
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.prepare:
        print(installation_patch(root,root/BUILD),end='')
        raise SystemExit(0)
    if args.prelink:
        print(json.dumps(prelink_prediction(root,root/BUILD),indent=2))
        raise SystemExit(0)
    for name,body in (allocation_forms() if args.allocations else forms() if args.screens else [('selected',SELECTED)]):
        row = measure(root,root/BUILD,name,body)[2]
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','raw_sha256','diagnostics','pools')}),flush=True)
