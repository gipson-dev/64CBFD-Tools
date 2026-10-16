"""Recover signed-view scissor commands and the six-word cursor-return ABI."""
import argparse
import difflib
import hashlib
import json
import re
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_view_list_setup as previous
from tools.tests import view_list_setup_checkpoint as checkpoint
from tools.pad_generated_object import parse_object
from tools import pad_c_object

BUILD = 'conker/build/game-view-scissor-setup'
OWNER,FUNCTION,ENTRY,ROM,WORDS = 'game_476D0','func_1501A490',0x1501A490,0x47940,124
PATHS = dict(previous.PATHS,
    scissor_original='conker/asm/nonmatchings/game_476D0/func_1501A490.s',
    scissor_clamp_original='conker/asm/nonmatchings/game_476D0/func_1501AF44.s',
    scissor_reference='../Another Source/CBFD-Recompiled/conker/conker/src/game_476D0.c')
BASELINE = dict(previous.BASELINE,**checkpoint.AFTER,
    scissor_original='f45dc8f46d8593accec3986a99e6d85e452c425b8c9876ae166e8be88a66920d',
    scissor_clamp_original='d8592183f600ebfc33229cb7edbcf8096feebbf1dd9d1ca6c11f61e3499c798e',
    scissor_reference='e833124f972d54c321b266ebf25cab79e3c0d99f73b2c2702adf816dff21a8e1')
build = previous.build
FIELDS = '''    u8 padding14[0x10];
    f32 top, bottom, left, right;
    u8 padding34[0x38];'''
DECLARATION = 'void func_1501AF44(f32 *ulx, f32 *uly, f32 *lrx, f32 *lry);\n'
INITIAL = '''/* Append pipe sync and the selected view's clipped scissor rectangle. */
s32 func_1501A490(s32 commandAddress, s16 view, s32 unused2, s32 unused3, s32 bottomLimit, s32 mode) {
    Gfx *commands = (Gfx *)commandAddress;
    ViewProjection476D0 *record;
    f32 left;
    f32 right;
    f32 top;
    f32 bottom;

    gDPPipeSync(commands++);
    if (view == 0xFF) {
        gDPSetScissor(commands++, mode, 2, 0, (f32)(s32)((u32)D_800BE620 - 2), (f32)D_800BE624);
    } else {
        record = (ViewProjection476D0 *)((u32)D_800BE628 + (u32)(s32)view * 0x180);
        left = record->left;
        right = record->right;
        top = record->top;
        if (bottomLimit != 0) {
            bottom = (f32)bottomLimit < record->bottom ? (f32)bottomLimit : record->bottom;
        } else {
            bottom = record->bottom;
        }
        func_1501AF44(&left, &top, &right, &bottom);
        gDPSetScissor(commands++, mode, left, top, right, bottom);
    }
    return (s32)commands;
}'''
SELECTED = INITIAL


def freeze(root,out):
    with patch.multiple(previous,PATHS=PATHS,BASELINE=BASELINE):previous.freeze(root,out)


def recovered_owner(before,body=None):
    body = SELECTED if body is None else body
    lo,hi = build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1501A490(s32 arg0, s16 arg1, s32 arg2, s32 arg3, s32 arg4, s32 arg5) {\n    return 0;\n}':
        raise ValueError('Unknown view scissor predecessor')
    result = before[:lo]+body.split('\n',1)[1]+before[hi:]
    if '(Gfx *commands,' in body or 'Gfx *func_1501A490(' in body:
        old = '#include "functions.h"'
        new = '/* Legacy callers pass the same six word-sized arguments and cursor result. */\n#define func_1501A490 ViewScissorLegacyWordSignature\n'+old+'\n#undef func_1501A490'
        if result.count(old)!=1:raise ValueError('Unknown scissor header anchor')
        result = result.replace(old,new,1)
    for old,new in (
        ('    u8 padding14[0x58];',FIELDS),
        ('/* Generated placeholder declarations. */',DECLARATION+'\n/* Generated placeholder declarations. */'),
        ('/* Non-matching C placeholders for asm/nonmatchings/game_476D0/func_1501A490.s. */',body.splitlines()[0])):
        if result.count(old)!=1:raise ValueError('Unknown view scissor declaration/field anchor')
        result = result.replace(old,new,1)
    return result


def forms():
    yield 'initial',INITIAL
    for names in (('left','top','right','bottom'),('bottom','top','right','left'),('top','bottom','left','right')):
        old = '    f32 left;\n    f32 right;\n    f32 top;\n    f32 bottom;'
        yield 'locals-'+'-'.join(names),INITIAL.replace(old,'\n'.join('    f32 '+n+';' for n in names))
    yield 'explicit-minimum',INITIAL.replace('            bottom = (f32)bottomLimit < record->bottom ? (f32)bottomLimit : record->bottom;',
        '            if ((f32)bottomLimit < record->bottom) {\n                bottom = (f32)bottomLimit;\n            } else {\n                bottom = record->bottom;\n            }')
    yield 'else-full-view',INITIAL.replace('if (view == 0xFF)', 'if (view != 0xFF)',1).replace(
        '        gDPSetScissor(commands++, mode, 2, 0, (f32)(s32)((u32)D_800BE620 - 2), (f32)D_800BE624);\n    } else {\n',
        '').replace('        gDPSetScissor(commands++, mode, left, top, right, bottom);\n    }',
        '        gDPSetScissor(commands++, mode, left, top, right, bottom);\n    } else {\n        gDPSetScissor(commands++, mode, 2, 0, (f32)(s32)((u32)D_800BE620 - 2), (f32)D_800BE624);\n    }')
    yield 'pointer-offset',INITIAL.replace('(u32)D_800BE628 + (u32)(s32)view * 0x180',
        '(u8 *)D_800BE628 + (s32)view * 0x180')


def carrier_forms():
    yield 'register-local-cursor',INITIAL.replace('    Gfx *commands =','    register Gfx *commands =')
    typed = INITIAL.replace('s32 commandAddress,','Gfx *commands,').replace('    Gfx *commands = (Gfx *)commandAddress;\n','')
    yield 'typed-cursor-parameter',typed
    for label,body in (('word',INITIAL),('typed',typed)):
        yield label+'-register-limit',body.replace('s32 bottomLimit,','register s32 bottomLimit,')
        yield label+'-copied-limit',body.replace('    ViewProjection476D0 *record;',
            '    ViewProjection476D0 *record;\n    s32 limit = bottomLimit;').replace(
            'if (bottomLimit != 0)','if (limit != 0)').replace('(f32)bottomLimit','(f32)limit')


def record_forms():
    body = dict(carrier_forms())['typed-cursor-parameter']
    inline = body.replace('    ViewProjection476D0 *record;\n','').replace(
        '        record = (ViewProjection476D0 *)((u32)D_800BE628 + (u32)(s32)view * 0x180);\n','').replace(
        'record->','VIEW_PROJECTIONS_476D0[view].')
    yield 'inline-typed-record',inline
    yield 'inline-unsigned-record',inline.replace('VIEW_PROJECTIONS_476D0[view].',
        '((ViewProjection476D0 *)((u32)D_800BE628 + (u32)(s32)view * 0x180))->')
    yield 'inline-explicit-min',inline.replace(
        '            bottom = (f32)bottomLimit < VIEW_PROJECTIONS_476D0[view].bottom ? (f32)bottomLimit : VIEW_PROJECTIONS_476D0[view].bottom;',
        '            if ((f32)bottomLimit < VIEW_PROJECTIONS_476D0[view].bottom) {\n                bottom = (f32)bottomLimit;\n            } else {\n                bottom = VIEW_PROJECTIONS_476D0[view].bottom;\n            }')


def temporary_forms():
    for label,body in (('record',dict(carrier_forms())['typed-cursor-parameter']),
            ('inline',dict(record_forms())['inline-unsigned-record'])):
        limited=body.replace('    f32 left;', '    f32 requestedBottom;\n    f32 left;').replace(
            '        if (bottomLimit != 0) {','        if (bottomLimit != 0) {\n            requestedBottom = (f32)bottomLimit;').replace(
            'bottom = (f32)bottomLimit <','bottom = requestedBottom <').replace(' ? (f32)bottomLimit :',' ? requestedBottom :')
        yield label+'-named-float-limit',limited
        if label=='record':
            offset=body.replace('    ViewProjection476D0 *record;', '    ViewProjection476D0 *record;\n    u32 recordOffset;').replace(
                '        record = (ViewProjection476D0 *)((u32)D_800BE628 + (u32)(s32)view * 0x180);',
                '        recordOffset = (u32)(s32)view * 0x180;\n        record = (ViewProjection476D0 *)((u32)D_800BE628 + recordOffset);')
            yield 'record-named-offset',offset
            yield 'record-offset-and-float-limit',limited.replace('    ViewProjection476D0 *record;',
                '    ViewProjection476D0 *record;\n    u32 recordOffset;').replace(
                '        record = (ViewProjection476D0 *)((u32)D_800BE628 + (u32)(s32)view * 0x180);',
                '        recordOffset = (u32)(s32)view * 0x180;\n        record = (ViewProjection476D0 *)((u32)D_800BE628 + recordOffset);')


def result_forms():
    for label,body in (('word',INITIAL),('record',dict(carrier_forms())['typed-cursor-parameter']),
            ('inline',dict(record_forms())['inline-typed-record'])):
        yield label+'-pointer-result',body.replace('s32 func_1501A490(', 'Gfx *func_1501A490(').replace(
            'return (s32)commands;', 'return commands;')


def packet_forms():
    body = dict(carrier_forms())['typed-cursor-parameter']
    for label,pipe,scissor in (('pipe',True,False),('scissor',False,True),('both',True,True)):
        form=body.replace('    ViewProjection476D0 *record;','    ViewProjection476D0 *record;\n    Gfx *packet;')
        if pipe:form=form.replace('    gDPPipeSync(commands++);','    packet = commands++;\n    gDPPipeSync(packet);')
        if scissor:form=form.replace('        gDPSetScissor(commands++,','        packet = commands++;\n        gDPSetScissor(packet,')
        yield 'named-packet-'+label,form


def container_forms():
    for label,body in (('record',dict(carrier_forms())['typed-cursor-parameter']),
            ('inline',dict(record_forms())['inline-unsigned-record'])):
        for kind in ('array','struct'):
            names = {n:('edges[%d]'%i if kind=='array' else 'bounds.'+n)
                for n,i in (('left',3),('right',2),('top',1),('bottom',0))}
            form = re.sub(r'(?<!->)\b(left|right|top|bottom)\b',lambda m:names[m[0]],body)
            old = '\n'.join('    f32 '+names[n]+';' for n in ('left','right','top','bottom'))
            new = '    f32 edges[4];' if kind=='array' else '    struct { f32 bottom, top, right, left; } bounds;'
            if form.count(old)!=1:raise ValueError('Unknown scissor local-container anchor')
            yield label+'-'+kind+'-bounds',form.replace(old,new,1)


def scope_forms():
    body = dict(carrier_forms())['typed-cursor-parameter']
    floats = '    f32 left;\n    f32 right;\n    f32 top;\n    f32 bottom;\n'
    declarations = '    ViewProjection476D0 *record;\n'+floats
    yield 'record-after-floats',body.replace(declarations,floats+'    ViewProjection476D0 *record;\n')
    yield 'register-record',body.replace('    ViewProjection476D0 *record;', '    register ViewProjection476D0 *record;')
    for label,local in (('all',declarations),('floats',floats)):
        candidate=body.replace(local,'',1).replace('    } else {\n        record =',
            '    } else {\n'+''.join('    '+line+'\n' for line in local.splitlines())+'\n        record =',1)
        yield 'branch-local-'+label,candidate


def branch_temporary_forms():
    body = dict(scope_forms())['branch-local-all']
    named = body.replace('        f32 left;', '        f32 requestedBottom;\n        f32 left;').replace(
        '        if (bottomLimit != 0) {','        if (bottomLimit != 0) {\n            requestedBottom = (f32)bottomLimit;').replace(
        'bottom = (f32)bottomLimit <','bottom = requestedBottom <').replace(' ? (f32)bottomLimit :',' ? requestedBottom :')
    yield 'branch-named-float-limit',named
    yield 'branch-named-offset',body.replace('        ViewProjection476D0 *record;',
        '        ViewProjection476D0 *record;\n        u32 recordOffset;').replace(
        '        record = (ViewProjection476D0 *)((u32)D_800BE628 + (u32)(s32)view * 0x180);',
        '        recordOffset = (u32)(s32)view * 0x180;\n        record = (ViewProjection476D0 *)((u32)D_800BE628 + recordOffset);')


def branch_inline_forms():
    for label,body in (('plain',dict(scope_forms())['branch-local-all']),
            ('float-limit',dict(branch_temporary_forms())['branch-named-float-limit'])):
        inline=body.replace('        ViewProjection476D0 *record;\n','').replace(
            '        record = (ViewProjection476D0 *)((u32)D_800BE628 + (u32)(s32)view * 0x180);\n','').replace(
            'record->','((ViewProjection476D0 *)((u32)D_800BE628 + (u32)(s32)view * 0x180))->')
        yield 'branch-inline-'+label,inline


SELECTED = dict(branch_inline_forms())['branch-inline-plain'].replace(
    '((ViewProjection476D0 *)((u32)D_800BE628 + (u32)(s32)view * 0x180))->',
    'VIEW_PROJECTIONS_476D0[view].')
RAW_SHA256 = '066c1d3eb6ad197f1212f7dcd370102278875f8c5b1861a7c4f5f9e9018a9368'
RELOCATIONS = {}
for hi,lo,name in ((0x60,0x64,'D_800BE620'),(0x6C,0x78,'D_800BE624'),(0xCC,0xD0,'D_800BE628')):
    RELOCATIONS[hi]=[('R_MIPS_HI16',name)];RELOCATIONS[lo]=[('R_MIPS_LO16',name)]
RELOCATIONS[0x140]=[('R_MIPS_26','func_1501AF44')]


def checked_object(obj):
    text,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:r for a,r in relocations.items() if f['value']<=a<f['value']+f['size']}
    pools={n:d for n,(_,d) in previous.previous.sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=496 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=RELOCATIONS or pools:
        raise ValueError('Unknown direct scissor object/bindings/pools')
    return list(struct.unpack('>124I',raw)),bindings


def recovered_makefile(before):
    old='$(BUILD_DIR)/$(SRC_DIR)/init_EB00.c.o $(BUILD_DIR)/$(SRC_DIR)/game_221290.c.o, '
    new=old.replace('.c.o, ','.c.o $(BUILD_DIR)/$(SRC_DIR)/game_476D0.c.o, ')
    if before.count(old)!=1:raise ValueError('Unknown scissor Makefile predecessor')
    return before.replace(old,new,1)


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified',SELECTED);checked_object(obj)
    old,diag=build.compile_owner(root,out,(out/'before-frustum_owner').read_text(),'neighbor-before')
    a,b=parse_object(old),parse_object(obj)
    if diag or row['diagnostics']:raise ValueError('Changed scissor diagnostics')
    if set(a[1])!=set(b[1]):raise ValueError('Changed scissor owner function set')
    rel=lambda p,f:{at-f['value']:r for at,r in p[2].items() if f['value']<=at<f['value']+f['size']}
    for name,f in a[1].items():
        if name==FUNCTION:continue
        g=b[1][name]
        if a[0][f['value']:f['value']+f['size']]!=b[0][g['value']:g['value']+g['size']] or rel(a,f)!=rel(b,g):
            raise ValueError('Changed scissor owner neighbor: '+name)
    alternate,diag=previous.compile_owner(root,out,recovered_owner((out/'before-frustum_owner').read_text()),'qualified-nounroll',True)
    if diag:raise ValueError('Changed no-unroll neighbor diagnostics')
    previous.checked_object(alternate)
    assembly=out/'qualified-padded.s'
    assembly.write_text(pad_c_object.emit_padded_assembly(obj,root/PATHS['layout'],OWNER,
        word_patches_path=out/'before-guards',function_objects={previous.FUNCTION:alternate}))
    padded=assembly.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(assembly)],capture_output=True,check=True)
    data,functions=build.link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    truth=(out/'before-retail_rom').read_bytes()
    if f['size']!=496 or data[f['value']:f['value']+496]!=truth[ROM:ROM+496]:
        raise ValueError('Direct scissor slot differs')
    helper=functions['func_1501AF44']
    row.update(byte_exact=True,new_guards=0,unchanged_neighbors=len(a[1])-1,
        clamp_words=helper['size']//4,clamp_exact=data[helper['value']:helper['value']+348]==truth[0x483F4:0x483F4+348])
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,words,row


def expected_inputs(root,out):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    before=(out/'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:raise ValueError('Changed scissor predecessor image')
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,28):raise ValueError('Unknown scissor predecessor extent')
    data=bytearray(before);at=elf_slot_offset(before,ENTRY,496)
    data[at:at+496]=(out/'before-retail_rom').read_bytes()[ROM:ROM+496]
    struct.pack_into('>I',data,row[0]+8,496)
    return dict(elf=bytes(data),frustum_owner=recovered_owner((out/'before-frustum_owner').read_text()).encode(),
        makefile=recovered_makefile((out/'before-makefile').read_text()).encode())


def prelink_prediction(root,out):
    _,padded,_,_=qualify(root,out)
    live=lambda:{k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()}
    capture=out/'link-inputs.json'
    if not capture.exists():
        if live()!=BASELINE:raise ValueError('Scissor link capture must precede installation')
        for name,path in (('before-linkscript','conker/build/conker.ld'),('before-owner.o','conker/build/src/'+OWNER+'.c.o')):
            (out/name).write_bytes((root/path).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest()
            for n in ('before-linkscript','before-owner.o')},indent=2)+'\n')
    for name,digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=digest:raise ValueError('Changed scissor link capture')
    link=(out/'before-linkscript').read_text();needle='build/src/'+OWNER+'.c.o(.text);'
    if link.count(needle)!=1:raise ValueError('Unknown scissor link selector')
    for label,obj in (('baseline',out/'before-owner.o'),('prediction',padded)):
        script=out/(label+'.ld');script.write_text(link.replace(needle,str(obj.relative_to(root/'conker'))+'(.text);',1))
        subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str((out/('prelink-'+label+'.elf')).relative_to(root/'conker'))],
            cwd=root/'conker',capture_output=True,check=True)
    if (out/'prelink-baseline.elf').read_bytes()!=(out/'before-elf').read_bytes():raise ValueError('Scissor predecessor not reproduced')
    expected=expected_inputs(root,out);actual=(out/'prelink-prediction.elf').read_bytes()
    if actual!=expected['elf']:raise ValueError('Scissor link differs outside its slot/extent prediction')
    hashes={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()};initial=out/'initial-prediction.json'
    if not initial.exists():
        if live()!=BASELINE:raise ValueError('Scissor prediction must precede installation')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first scissor prediction')
    row=dict(after=hashes,changed_ELF_bytes=sum(a!=b for a,b in zip((out/'before-elf').read_bytes(),actual)),
        body_bytes=496,slot_bytes=496,new_guards=0,metadata_exclusions=0)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n');return row


def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}:
        raise ValueError('Changed first scissor installation prediction')
    edits=[]
    for key in ('frustum_owner','makefile'):
        path=root/PATHS[key];before=path.read_bytes();after=expected[key]
        if hashlib.sha256(before).hexdigest()!=BASELINE[key]:raise ValueError('Changed scissor live input before installation: '+key)
        diff=list(difflib.unified_diff(before.decode().splitlines(),after.decode().splitlines(),n=3,lineterm=''))
        edits.append('*** Update File: '+str(path)+'\n'+'\n'.join('@@' if line.startswith('@@') else line for line in diff[2:]))
    return '*** Begin Patch\n'+'\n'.join(edits)+'\n*** End Patch\n'


def measure(root,out,label='selected',body=None,flags=('-O2','-g3')):
    freeze(root,out)
    obj,diagnostics = build.compile_owner(root,out,recovered_owner((out/'before-frustum_owner').read_text(),body),label,flags)
    text,functions,relocations = parse_object(obj);f = functions[FUNCTION]
    data,placed = build.link_owner(root,out,obj,OWNER)
    words = list(struct.unpack_from('>%dI'%(f['size']//4),data,placed[FUNCTION]['value']))
    truth = list(struct.unpack_from('>124I',(out/'before-retail_rom').read_bytes(),ROM))
    slot = words+[0]*max(0,WORDS-len(words))
    row = dict(label=label,words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(slot,truth))+max(0,len(words)-WORDS),
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={a-f['value']:r for a,r in relocations.items() if f['value']<=a<f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in previous.previous.sections(obj).items()
            if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d},
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(slot,truth)) if a!=b])
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screens',action='store_true');parser.add_argument('--carriers',action='store_true');parser.add_argument('--records',action='store_true');parser.add_argument('--temporaries',action='store_true');parser.add_argument('--results',action='store_true');parser.add_argument('--packets',action='store_true');parser.add_argument('--profiles',action='store_true');parser.add_argument('--containers',action='store_true');parser.add_argument('--scopes',action='store_true');parser.add_argument('--branch-temporaries',action='store_true');parser.add_argument('--branch-inline',action='store_true');parser.add_argument('--qualify',action='store_true')
    parser.add_argument('--prelink',action='store_true');parser.add_argument('--prepare',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    if args.prelink:
        print(json.dumps(prelink_prediction(root,root/BUILD),indent=2),flush=True);raise SystemExit(0)
    if args.prepare:
        print(installation_patch(root,root/BUILD),end='');raise SystemExit(0)
    if args.qualify:
        print(json.dumps(qualify(root,root/BUILD)[3]),flush=True);raise SystemExit(0)
    if args.profiles:
        for label,flags in (('o2',('-O2',)),('o1',('-O1',))):
            row=measure(root,root/BUILD,'profile-'+label,dict(carrier_forms())['typed-cursor-parameter'],flags)[2]
            print(json.dumps({k:row[k] for k in ('label','words','frame','differences','diagnostics','raw_sha256','pools')}),flush=True)
        raise SystemExit(0)
    for label,body in (branch_inline_forms() if args.branch_inline else branch_temporary_forms() if args.branch_temporaries else scope_forms() if args.scopes else container_forms() if args.containers else packet_forms() if args.packets else result_forms() if args.results else temporary_forms() if args.temporaries else record_forms() if args.records else carrier_forms() if args.carriers else forms() if args.screens else [('selected',SELECTED)]):
        row=measure(root,root/BUILD,label,body)[2]
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','diagnostics','raw_sha256','pools')}),flush=True)
