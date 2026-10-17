"""Full burst with real object homes and eleven guarded scratch-register words."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_transition_pointer_lifetimes as previous
from tools.tests import transition_child_motion_checkpoint as child
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import emit_padded_assembly

BUILD='conker/build/game-transition-burst-match'
OWNER,FUNCTION,ENTRY,ROM,SIZE=previous.OWNER,previous.FUNCTION,previous.ENTRY,previous.ROM,previous.SIZE
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE,**child.AFTER)
for key,path,sha in (
    ('burst_pointer_screen','tools/experiments/game_transition_pointer_lifetimes.py',
     '71e5b038bb91e7d0771055db27987f1d8aa0ac41c151cb3ca3d1988b61c1f607'),
    ('burst_pointer_tests','tools/tests/test_game_transition_pointer_lifetimes.py',
     'ffc234c82d966efe404cfdf2f356673129def98d4bb13bac99eb864a57550ddc'),
    ('child_checkpoint','tools/tests/transition_child_motion_checkpoint.py',
     '4cc59a79c4c6fd1a1daa057f1f6abe06d9b5358c2b2b3b16faa80f70000a3230')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,projection=previous.build,previous.compile_owner,previous.projection
link_raw,parse_object=previous.link_raw,previous.parse_object
BINDINGS=previous.BINDINGS
RAW_SHA='dd76d6be5742594b4c4445d30efda676e9ab249bbd0e5ed8743f8c37b1fbd8b7'
POOL_BYTES=previous.previous.previous.POOL_BYTES
CANDIDATE=previous.CANDIDATE
line='    f32 progress;\n'
if CANDIDATE.count(line)!=1: raise ValueError('Unknown burst progress declaration')
CANDIDATE=CANDIDATE.replace(line,'').replace('    BurstDescriptorFC5F0 descriptor;',
    line+'    BurstDescriptorFC5F0 descriptor;',1)
SCRATCH_MAP={8:10,10:14,14:15,15:8,13:25,25:24,24:11,11:13}
EXPECTED={189:0x01916825,190:0x35AE0038,191:0x24190010,192:0xA7AE00C0,
    193:0xAFB90010,194:0x928F000C,197:0xAFAF0014,198:0x92980001,
    201:0xAFB80018,208:0x00124600,209:0x00089603}


def rename(word):
    op,fn=word>>26,word&63
    if op==3:return word
    if op==0:
        if fn in (0,3):shifts=(16,11)
        elif fn==37:shifts=(21,16,11)
        else:raise ValueError('Unknown burst scratch R operation')
    elif op in (4,9,13,36,41,43):shifts=(21,16)
    else:raise ValueError('Unknown burst scratch operation')
    for shift in shifts:
        reg=(word>>shift)&31
        word=(word&~(31<<shift))|(SCRATCH_MAP.get(reg,reg)<<shift)
    return word


PATCHES={i*4:(word,rename(word)) for i,word in EXPECTED.items()}


def normalize(words):
    if len(words)!=251 or set(SCRATCH_MAP)!=set(SCRATCH_MAP.values()):
        raise ValueError('Unknown burst extent or scratch bijection')
    result=list(words)
    for i in range(189,210):result[i]=rename(result[i])
    if {i*4:(a,b) for i,(a,b) in enumerate(zip(words,result)) if a!=b}!=PATCHES:
        raise ValueError('Burst is not the expected scratch relabeling')
    return result


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import transition_burst_checkpoint as installed
            data=installed.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Unknown burst match input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed burst match fixture: '+key)


def recovered_owner(before,body=CANDIDATE):
    return previous.recovered_owner(before,body)


def recovered_makefile(before):
    anchor='$(BUILD_DIR)/$(SRC_DIR)/game/generated_113D60.c.o: RETAIL_RODATA_SYMBOL := D_800A1350\n'
    if before.count(anchor)!=1 or 'generated_FC5F0.c.o: RETAIL_RODATA_SYMBOL' in before:
        raise ValueError('Unknown burst rodata mapping predecessor')
    return before.replace(anchor,anchor+
        '# Transition burst uses its six existing retail motion constants.\n'
        '$(BUILD_DIR)/$(SRC_DIR)/game/generated_FC5F0.c.o: RETAIL_RODATA_SYMBOL := D_800A0860\n',1)


def recovered_child_checkpoint(before):
    anchor='def previous_input(current,path,root):\n'
    if before.count(anchor)!=1:raise ValueError('Unknown child checkpoint predecessor')
    return before.replace(anchor,anchor+
        '    from tools.tests import transition_burst_checkpoint as latest\n'
        '    current=latest.previous_input(current,path,root)\n',1)


def guard_bytes(before):
    rows=list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in rows) or not before.endswith(b'\n'):
        raise ValueError('Unknown burst guard predecessor')
    fields=next(csv.reader(io.StringIO(before.decode())));out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=fields,lineterminator='\n')
    for offset,(expected,replacement) in PATCHES.items():
        writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%offset,
            expected='0x%08X'%expected,replacement='0x%08X'%replacement,
            expected_relocations='-',replacement_relocations='-',
            note='Normalize certified burst scratch-register roles',insert_after='',insert_after_relocations='',omit='false'))
    return before+out.getvalue().encode()


def parts(obj):
    data,functions,relocs=parse_object(obj);f=functions[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in relocs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown full burst words/bindings')


def padded_object(root,out,obj,label,guards):
    text=emit_padded_assembly(obj,out/'before-tile_original',word_patches_path=guards,filename=OWNER,rodata_symbol='D_800A0860')
    path=out/(label+'-padded.s');path.write_text(text);target=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(path)],capture_output=True,check=True)
    return target


def qualify(root,out):
    freeze(root,out);before=(out/'before-tile_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Burst owner compiler diagnostics')
    checked_parts(*parts(obj))
    if projection.sections(obj)['.rodata'][1]!=POOL_BYTES+bytes(8):raise ValueError('Unknown burst constant pool')
    if (out/'before-retail_rom').read_bytes()[0x245320:0x245338]!=POOL_BYTES:raise ValueError('Burst constants differ from retail')
    neighbors=same_functions(old,obj,(FUNCTION,))
    guards=out/'candidate-guards.csv';guards.write_bytes(guard_bytes((out/'before-guards').read_bytes()))
    padded=padded_object(root,out,obj,'candidate',guards)
    old_padded=padded_object(root,out,old,'owner-before',out/'before-guards')
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:raise ValueError('Burst padded neighbors changed')
    images=[]
    for path,linker in ((obj,link_raw),(padded,build.link_owner)):
        data,functions=linker(root,out,path) if linker==link_raw else linker(root,out,path,OWNER)
        f=functions[FUNCTION];images.append(list(struct.unpack_from('>251I',data,f['value'])))
    truth=list(struct.unpack_from('>251I',(out/'before-retail_rom').read_bytes(),ROM))
    if normalize(images[0])!=truth or images[1]!=truth:raise ValueError('Incomplete guarded burst match')
    row=dict(words=251,frame=264,raw_differences=11,bindings=31,new_guards=11,
        descriptor=0xAC,payload=0x9C,unchanged_raw_padded_neighbors=neighbors,
        scratch_map=SCRATCH_MAP,no_stack_displacement_patches=True)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
