"""Recover the route-record dispatcher without changing live source during fitting."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_route_projection_integration as prior
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.pad_generated_object import parse_object
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools

BUILD='conker/build/game-route-dispatcher-match'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_15087CC0',0x15087CC0,0xB5170,67
INPUTS=dict(prior.INPUTS,**prior.AFTER)
INPUTS.update({
    'conker/src/game_45B80.c':'63ff5cd1051b8ed117581dcc5321b4e4dd5370f8cffaf62bc5091087e968b210',
    'conker/asm/nonmatchings/game_45B80/func_15019130.s':'ce3f6e240cec6e4e8ee5c74e979f0a2ce91c14e364b7a24e3f0781f77e67b619',
    'conker/retail_layout.us.txt':'a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5',
})
MODEL='''/* Dispatch route records using their live actor slot and movement state. */
void func_15087CC0(void) {
    extern s8 D_800D23A9;
    extern void func_150891E8(u8 *, u8 *);
    extern s32 func_150896EC();
    s32 i;
    u8 *record;
    u8 *actor;

    D_800D23A9 = 0;
    if (D_800872A0 != 0) {
        for (i = 0; i < D_800D2398; i++) {
            record = D_800872A0 + i * 0x84;
            actor = D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C;
            if (*(s32 *)(actor + 0x318) != 0) {
                if (*(s8 *)(record + 0x30) >= 2) {
                    func_150891E8(record, actor);
                } else if (record[0x48] == 0) {
                    func_150896EC(record, actor, 0);
                } else if (*(s8 *)(record + 0x49) != 0) {
                    func_150896EC(record, actor, 1);
                }
            }
        }
    }
}
'''
SELECTED=MODEL.replace('D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C',
    '&D_800CC2D0[*(s8 *)(record + 0x31) * 0x32C]')
RAW_SHA='42bfc05284be2e0cbe657b8925287fb5b43ab4c150edb1d1092538d83180e2a8'
BINDINGS={at:[(kind,name)] for at,kind,name in (
    (8,'R_MIPS_HI16','D_800872A0'),(12,'R_MIPS_LO16','D_800872A0'),
    (36,'R_MIPS_HI16','D_800D23A9'),(40,'R_MIPS_LO16','D_800D23A9'),
    (48,'R_MIPS_HI16','D_800D2398'),(60,'R_MIPS_LO16','D_800D2398'),
    (80,'R_MIPS_HI16','D_800CC2D0'),(84,'R_MIPS_LO16','D_800CC2D0'),
    (140,'R_MIPS_26','func_150891E8'),(148,'R_MIPS_HI16','D_800D2398'),
    (156,'R_MIPS_LO16','D_800D2398'),(172,'R_MIPS_26','func_150896EC'),
    (180,'R_MIPS_HI16','D_800D2398'),(188,'R_MIPS_LO16','D_800D2398'),
    (204,'R_MIPS_26','func_150896EC'),(212,'R_MIPS_HI16','D_800D2398'),
    (216,'R_MIPS_LO16','D_800D2398'))}
AFTER={
    'conker/build/conker.us.elf':'dfa6424d042a037e643108a051757e78515e4b89ac9772a95b8b9845938742e2',
    'conker/src/game/generated_B3020.c':'4fee3adb19dd5ee7f6d9e62994c948472365705afd6867d46fc7634aa260e1fe',
    'conker/src/game_45B80.c':'f507c0c211e4990894bef42047f05dd40df85d9fe7a8996b887a547104cdc1ba',
}
SUCCESSOR_FILES={'conker/build/conker.us.elf':'after-elf',
    'conker/src/game/generated_B3020.c':'after-owner','conker/src/game_45B80.c':'after-caller'}
raw_read,raw_text=Path.read_bytes,Path.read_text


def freeze(root,out):
    values={}
    for path,digest in INPUTS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:
            raise ValueError('Changed route dispatcher input: '+path)
        values[path]=data
    out.mkdir(parents=True,exist_ok=True)
    for index,data in enumerate(values.values()):
        target=out/('before-%02d'%index)
        if target.exists() and target.read_bytes()!=data:
            raise ValueError('Changed route dispatcher snapshot: '+str(target))
        if not target.exists():target.write_bytes(data)
    return values


def recovered_owner(before,body=SELECTED):
    lo,hi=function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_15087CC0() {\n    return 0;\n}':
        raise ValueError('Unknown route dispatcher placeholder')
    return before[:lo]+body.rstrip()+before[hi:]


def recovered_caller(before):
    old='s32 func_15087CC0(void);'
    if before.count(old)!=1:raise ValueError('Unknown route dispatcher caller declaration')
    return before.replace(old,'void func_15087CC0(void);')


def measure(root,out,body=SELECTED,label='direct'):
    values=freeze(root,out)
    owner=recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body)
    obj,diagnostics=prior.compile_profile(root,out,owner,label)
    if diagnostics:raise ValueError(diagnostics)
    data,functions=prior.link_owner(root,out,obj,OWNER)
    f=functions[FUNCTION]
    actual=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=list(struct.unpack_from('>67I',values['conker/conker.us.bin'],ROM))
    text,defs,relocations=parse_object(obj);f=defs[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in relocations.items() if f['value']<=at<f['value']+f['size']}
    differences=[i for i in range(max(len(actual),WORDS)) if i>=len(actual) or i>=WORDS or actual[i]!=truth[i]]
    row=dict(words=len(actual),frame=(-actual[0])&65535,differences=len(differences),different=differences,
        raw_sha256=hashlib.sha256(raw).hexdigest(),bindings=bindings,production_installed=False)
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,actual,row


def forms():
    expression='D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C'
    result={name:MODEL.replace(expression,value) for name,value in (
        ('swapped-add','*(s8 *)(record + 0x31) * 0x32C + D_800CC2D0'),
        ('indexed','&D_800CC2D0[*(s8 *)(record + 0x31) * 0x32C]'),
        ('integer-base','(u8 *)((u32)D_800CC2D0 + *(s8 *)(record + 0x31) * 0x32C)'),
        ('integer-swapped','(u8 *)(*(s8 *)(record + 0x31) * 0x32C + (u32)D_800CC2D0)'),
    )}
    result['stride']=MODEL.replace('    s32 i;','    s32 i;\n    s32 stride;').replace(
        '        for (i = 0;','        stride = 0x32C;\n        for (i = 0;').replace(' * 0x32C;',' * stride;')
    result['actor-base']=MODEL.replace('    u8 *actor;','    u8 *actor;\n    u8 *actors;').replace(
        '        for (i = 0;','        actors = D_800CC2D0;\n        for (i = 0;').replace(expression,'actors + *(s8 *)(record + 0x31) * 0x32C')
    return result


def checked(obj):
    text,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in relocations.items() if f['value']<=at<f['value']+f['size']}
    if hashlib.sha256(raw).hexdigest()!=RAW_SHA or len(raw)!=268 or bindings!=BINDINGS:
        raise ValueError('Unknown direct route dispatcher body or bindings')
    return raw,bindings


def qualify(root,out):
    values=freeze(root,out);before=values['conker/src/game/generated_B3020.c'].decode()
    obj,words,row=measure(root,out);checked(obj)
    if words!=list(struct.unpack_from('>67I',values['conker/conker.us.bin'],ROM)):
        raise ValueError('Direct route dispatcher differs from retail')
    old,diag=prior.compile_profile(root,out,before,'owner-before')
    normal,nd=prior.compile_profile(root,out,recovered_owner(before),'owner-normal',True)
    if diag or nd:raise ValueError('Route dispatcher profile diagnostics')
    prior.candidate.checked(normal)
    if same_functions(old,obj,(FUNCTION,))!=72 or normalized_pools(old)!=normalized_pools(obj):
        raise ValueError('Route dispatcher changed a primary neighbor or pool')
    guards=out/'unchanged-guards.csv';guards.write_bytes(values['conker/retail_word_patches.us.csv'])
    a=prior.padded(root,out,old,'baseline-padded',guards,normal)
    b=prior.padded(root,out,obj,'qualified-padded',guards,normal)
    aa,fa=prior.link_owner(root,out,a,OWNER);bb,fb=prior.link_owner(root,out,b,OWNER)
    at=fa[FUNCTION]['value']
    if aa[:at]!=bb[:at] or aa[at+268:]!=bb[at+268:] or fa.keys()!=fb.keys() or any(
        fa[n]['value']!=fb[n]['value'] or n!=FUNCTION and fa[n]!=fb[n] for n in fa):
        raise ValueError('Padded route dispatcher changed another body/address/extent')
    if normalized_pools(a)!=normalized_pools(b):raise ValueError('Padded route dispatcher changed pools')
    baseline=root/'conker/build/src/game/generated_B3020.c.o'
    live=hashlib.sha256(raw_read(root/'conker/build/conker.us.elf')).hexdigest()
    if live==INPUTS['conker/build/conker.us.elf']:same_functions(a,baseline)
    elif live==AFTER.get('conker/build/conker.us.elf'):same_functions(b,baseline)
    else:raise ValueError('Unknown live dispatcher image stage')
    caller=values['conker/src/game_45B80.c'].decode()
    ca,cda=prior.normal_owner(root,out,caller,'caller-before')
    cb,cdb=prior.normal_owner(root,out,recovered_caller(caller),'caller-after')
    if re.sub('caller-before','caller',cda)!=re.sub('caller-after','caller',cdb):
        raise ValueError('Caller prototype introduces diagnostics')
    count=same_functions(ca,cb)
    if normalized_pools(ca)!=normalized_pools(cb):raise ValueError('Caller prototype changed pools')
    row.update(unchanged_primary_neighbors=72,projection_raw_and_bindings_unchanged=True,
        unchanged_caller_functions=count,unchanged_guards_and_Makefile=True,actual_mixed_profile_padding=True)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,b,words,row


def predicted_image(before,span):
    result=bytearray(before);at=prior.elf_slot_offset(before,ENTRY,268);result[at:at+268]=span
    rows=[r for r in prior.symbol_rows(before) if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Unknown dispatcher predecessor extent')
    struct.pack_into('>I',result,rows[0][0]+8,268);return bytes(result)


def predict(root,out,qualified=None):
    values=freeze(root,out);obj=qualified if qualified is not None else qualify(root,out)[1]
    script=raw_text(root/'conker/build/conker.ld');old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unknown dispatcher linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,obj.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(elf.relative_to(root/'conker'))],
        cwd=root/'conker',check=True,capture_output=True)
    data=raw_read(elf)
    if data!=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+268]):
        raise ValueError('First route dispatcher ELF prediction changes unrelated bytes')
    after={
        'conker/build/conker.us.elf':data,
        'conker/src/game/generated_B3020.c':recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode(),
        'conker/src/game_45B80.c':recovered_caller(values['conker/src/game_45B80.c'].decode()).encode(),
    }
    for path,value in after.items():
        target=out/SUCCESSOR_FILES[path]
        if target.exists() and raw_read(target)!=value:raise ValueError('Changed first route dispatcher successor')
        if not target.exists():target.write_bytes(value)
    result=dict(changed_ELF_bytes=sum(a!=b for a,b in zip(values['conker/build/conker.us.elf'],data)),
        after={p:hashlib.sha256(v).hexdigest() for p,v in after.items()},only_target_code_and_size_changed=True)
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n');return result


def expected_inputs(root,out):
    values={p:raw_read(out/name) for p,name in SUCCESSOR_FILES.items()}
    if not AFTER or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed first dispatcher successor')
    return values


@contextmanager
def checkpoint_context():
    with patch.multiple(prior.candidate.source.checkpoint,INPUTS=INPUTS,AFTER=AFTER,expected_inputs=expected_inputs):yield


@contextmanager
def historical_view(root,out):
    with checkpoint_context(),prior.candidate.source.checkpoint.historical_view(root,out):yield


def verify(root,out,installed=False):
    with checkpoint_context():return prior.candidate.source.checkpoint.verify(root,out,installed)


def audit(root,out):
    verify(root,out,True)
    for index,(path,digest) in enumerate(INPUTS.items()):
        if hashlib.sha256(raw_read(out/('before-%02d'%index))).hexdigest()!=digest or \
            hashlib.sha256(raw_read(root/path)).hexdigest()!=AFTER.get(path,digest):
            raise ValueError('Changed installed dispatcher input: '+path)
    before=raw_read(out/'before-01');actual=raw_read(root/'conker/build/conker.us.elf');rom=raw_read(root/'conker/conker.us.bin')
    if actual!=raw_read(out/'after-elf') or actual!=predicted_image(before,rom[ROM:ROM+268]):
        raise ValueError('Installed dispatcher differs from first prediction')
    from tools.match_progress import load_elf_functions
    from tools.check_game_data_layout import audit_layout
    a,_,aa=load_elf_functions(str(out/'before-01'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys() or [n for n in a if a[n]!=b[n]]!=[FUNCTION]:
        raise ValueError('Dispatcher changed another linked function/address')
    same_functions(out/'qualified-padded.o',root/'conker/build/src/game/generated_B3020.c.o')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Dispatcher changed protected Game data')
    result=dict(functions=len(a),all_addresses_fixed=True,only_target_code_and_size_changed=True,
        changed_ELF_bytes=sum(x!=y for x,y in zip(before,actual)),game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screen',action='store_true')
    parser.add_argument('--predict',action='store_true');parser.add_argument('--audit',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    if args.screen:
        for label,body in forms().items():
            print(json.dumps(dict(label=label,**measure(root,out,body,label)[2])),flush=True)
    else:print(json.dumps(audit(root,out) if args.audit else predict(root,out) if args.predict else measure(root,out)[2],indent=2))
