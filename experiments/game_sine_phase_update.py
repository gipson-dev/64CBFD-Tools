"""Recover the two-channel sine output and phase updater with one ADDU guard."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_actor_counter_motion as previous
from tools.tests import actor_counter_motion_checkpoint as checkpoint
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import emit_padded_assembly

BUILD='conker/build/game-sine-phase-update'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_11F780','func_150F2480',0x150F2480,0x11F930,152
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE,**checkpoint.AFTER)
for key,path,sha in (
    ('phase_owner','conker/src/game/generated_11F780.c','4dc07e63dcb590d1ea971eb9efc7a0f4decd1a3e5b129a22ba110b2b05905473'),
    ('phase_original','conker/asm/11F780.s','2cb6659e0f8be7c5b82b3964295bc9433f604e5b2996f853ce8bc7368cb895b2'),
    ('phase_table','conker/asm/data/22E680.rodata.s','370db36a674c7e60d46c71b6de8abc8e3a486404b64cdddb76cb9ed0482d18d6'),
    ('phase_caller','conker/asm/nonmatchings/game_168A90/func_1513B798.s','47d2ae3bcca3df2fdda1590c6e929f9f9c3f52393c11ae2295f20af9f467c896'),
    ('phase_sine_source','conker/src/libultra/gu/sinf.c','ae271497692ea1a00abd96bcfed9209458cf8ea694b0df385aa5dddf9fc1a679'),
    ('phase_sine_asm','conker/asm/nonmatchings/libultra/gu/sinf/sinf.s','aaa2e4b725d2370cf7cc8f09860753184858f98c2a54635bc4ffad935b5916bd'),
    ('phase_wrap_source','conker/src/game_16EE20.c','7acc24c75dc922e9aa72027a030b4c8e43b0d2a2d9bc5f8c2a17fccb3dba7810'),
    ('phase_wrap_asm','conker/asm/nonmatchings/game_16EE20/func_15144B68.s','472c6822afc3d244b2471949c6d5143830d08a8b5bc9bc4863e5f97332a757f1'),
    ('motion_checkpoint','tools/tests/actor_counter_motion_checkpoint.py','5d56e2e53a9189a2e1f04634fd91e9155b6295e4d24b0d67473791865c9b70a6'),
    ('motion_tests','tools/tests/test_game_actor_counter_motion.py','0a54a20dc4057e5cf39893181251270d0b4e149d06b0a3c850c1252002a00c5f'),
    ('phase_sine_tests','tools/tests/test_game_trig_match.py','eb554d3b54442737d1a34f4ab88ca8f746fd7a22e947bacbdb242305bed317d9')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,parse_object,projection=previous.build,previous.compile_owner,previous.parse_object,previous.projection
TYPE='extern f32 D_800BE9A4;\nf32 func_15144B68(f32);\n'
SELECTED='''/* Update sine outputs, then advance and wrap both phases. */
s32 func_150F2480(u8 *actor) {
    f32 *state;

    state = (f32 *)(actor + *(s32 *)(actor + 0x50) + 0xF8);
    state[9] = state[4] * sinf(state[0]);
    state[10] = state[5] * sinf(state[1]);
    state[0] = func_15144B68(state[2] * D_800BE9A4 + state[0]);
    state[1] = func_15144B68(state[3] * D_800BE9A4 + state[1]);
    return 1;
}'''
RAW_SHA='c28ce833e8d95a2cac321ac6dab4f9ee7b2f83da45f0ea6b7c15343781ce51db'
BINDINGS={24:[('R_MIPS_26','sinf')],44:[('R_MIPS_26','sinf')],
    56:[('R_MIPS_HI16','D_800BE9A4')],76:[('R_MIPS_LO16','D_800BE9A4')],
    84:[('R_MIPS_26','func_15144B68')],96:[('R_MIPS_HI16','D_800BE9A4')],
    100:[('R_MIPS_LO16','D_800BE9A4')],116:[('R_MIPS_26','func_15144B68')]}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import sine_phase_update_checkpoint as latest
            data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed sine-phase live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed sine-phase frozen input: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150F2480() {\n    return 0;\n}' or before.count('#include <ultra64.h>\n')!=1:
        raise ValueError('Unknown sine-phase predecessor')
    return (before[:lo]+body+before[hi:]).replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+TYPE,1)


def recovered_guards(before):
    rows=list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['function']==FUNCTION for r in rows):raise ValueError('Existing sine-phase guard')
    if not before.endswith(b'\n'):raise ValueError('Unknown guard terminator')
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\r\n' if b'\r\n' in before else '\n')
    writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x10',expected='0x01C48021',replacement='0x008E8021',
        expected_relocations='-',replacement_relocations='-',
        note='Normalize commutative sine-phase state-address ADDU operand order',
        insert_after='',insert_after_relocations='',omit='false'))
    return before+stream.getvalue().encode()


def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Changed complete sine-phase words/bindings')


def padded_object(root,out,obj,label,guarded=True):
    guards=out/'candidate-guards.csv'
    guards.write_bytes(recovered_guards((out/'before-guards').read_bytes()))
    text=emit_padded_assembly(obj,out/'before-phase_original',
        word_patches_path=guards if guarded else out/'before-guards',filename=OWNER)
    asm=out/(label+'-padded.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def qualify(root,out):
    freeze(root,out);before=(out/'before-phase_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Sine-phase compiler diagnostics')
    checked_parts(*parts(obj))
    pools=lambda p:{n:d for n,(_,d) in projection.sections(p).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):raise ValueError('Sine-phase owner pools changed')
    neighbors=same_functions(old,obj,(FUNCTION,));padded=padded_object(root,out,obj,'candidate')
    if same_functions(padded_object(root,out,old,'owner-before',False),padded,(FUNCTION,))!=neighbors:
        raise ValueError('Sine-phase padded neighbors changed')
    images=[]
    for path in (obj,padded):
        data,fs=build.link_owner(root,out,path,OWNER)
        images.append(list(struct.unpack_from('>38I',data,fs[FUNCTION]['value'])))
    truth=list(struct.unpack_from('>38I',(out/'before-retail_rom').read_bytes(),ROM))
    if [i for i,(a,b) in enumerate(zip(images[0],truth)) if a!=b]!=[4] or images[1]!=truth:
        raise ValueError('Incomplete sine-phase match')
    row=dict(words=38,frame=32,bindings=8,new_guards=1,raw_differences=1,
        unchanged_raw_padded_neighbors=neighbors,installed=False)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
