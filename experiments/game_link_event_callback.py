"""Recover the full removal/link-swap callback with one commutative branch guard."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_transition_burst_match as previous
from tools.tests import transition_burst_checkpoint as burst
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import emit_padded_assembly

BUILD='conker/build/game-link-event-callback'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_FC5F0','func_150CF484',0x150CF484,0xFC934,172
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE,**burst.AFTER)
for key,path,sha in (
    ('burst_match','tools/experiments/game_transition_burst_match.py',
     'f1987b46f84179e469ae71db12266ccd4f432978476f6a33f7bf3f8eb6776959'),
    ('burst_checkpoint','tools/tests/transition_burst_checkpoint.py',
     'f0208d3f52735bd3ae506bb5eb67a0a3227fdf82f3c821715ca24d5017b6d5d3'),
    ('link_dispatcher','conker/src/game/done/game_1765E0.c',
     '19dd4f8a4e0561ad2de70ee59e12e50c11a9938357816dd0eacb2334d8c0c5af'),
    ('link_table','conker/asm/data/22EF80.rodata.s',
     '0711a45ed594246cf7054df44d7e73dd1506372423061bf7e6d8f6b147eb7b79')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,projection,parse_object=previous.build,previous.compile_owner,previous.projection,previous.parse_object
RAW_SHA='4d9d64e0a3911e4a931a63b7ad418cb8f237dbe1f8e305038ec0586129dc49ec'
BINDINGS={68:[('R_MIPS_26','func_1516972C')]}
TYPE='''typedef struct {
    s32 value;
    u8 tag;
} LinkStateFC5F0;
'''
SELECTED='''/* Event packets use different layouts for removal and link replacement. */
void func_150CF484(u8 *record, u8 *packet, u8 event) {
    LinkStateFC5F0 *link;
    s32 first, current;

    link = (LinkStateFC5F0 *)(record + 0x28);
    if (event == 0) {
        first = *(s32 *)packet;
        if (first == link->value || link->tag == packet[4]) {
            func_1516972C(record);
        }
    } else {
        if (event == 0x2D) {
            current = link->value;
            first = *(s32 *)packet;
            if (first == current) {
                link->value = *(s32 *)(packet + 4);
                link->tag = packet[9];
            } else if (*(s32 *)(packet + 4) == current) {
                link->value = first;
                link->tag = packet[8];
            }
        }
    }
}'''


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import link_event_checkpoint as installed
            data=installed.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Unknown link-event input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed link-event fixture: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150CF484() {\n    return 0;\n}' or before.count('#include <ultra64.h>\n')!=1:
        raise ValueError('Unknown link-event placeholder')
    return (before[:lo]+body+before[hi:]).replace('#include <ultra64.h>\n',
        '#include <ultra64.h>\nvoid func_1516972C(u8 *);\n'+TYPE,1)


def recovered_burst_checkpoint(before):
    anchor='def previous_input(current,path,root):\n'
    if before.count(anchor)!=1:raise ValueError('Unknown burst checkpoint predecessor')
    return before.replace(anchor,anchor+
        '    from tools.tests import link_event_checkpoint as latest\n'
        '    current=latest.previous_input(current,path,root)\n',1)


def guard_bytes(before):
    rows=list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in rows) or not before.endswith(b'\n'):
        raise ValueError('Unknown link-event guard predecessor')
    fields=next(csv.reader(io.StringIO(before.decode())));out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=fields,lineterminator='\n')
    writer.writerow(dict(filename=OWNER,function=FUNCTION,offset='0x88',expected='0x548A0005',
        replacement='0x55440005',expected_relocations='-',replacement_relocations='-',
        note='Preserve retail commutative link-equality branch operand order',
        insert_after='',insert_after_relocations='',omit='false'))
    return before+out.getvalue().encode()


def parts(obj):
    data,functions,relocs=parse_object(obj);f=functions[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in relocs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown full link-event words/bindings')


def padded_object(root,out,obj,label,guards):
    text=emit_padded_assembly(obj,out/'before-tile_original',word_patches_path=guards,
        filename=OWNER,rodata_symbol='D_800A0860')
    path=out/(label+'-padded.s');path.write_text(text);target=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(path)],capture_output=True,check=True)
    return target


def qualify(root,out):
    freeze(root,out);before=(out/'before-tile_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Link-event owner compiler diagnostics')
    checked_parts(*parts(obj))
    pools=lambda p:{n:d for n,(_,d) in projection.sections(p).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):raise ValueError('Link-event owner pools changed')
    neighbors=same_functions(old,obj,(FUNCTION,))
    guards=out/'candidate-guards.csv';guards.write_bytes(guard_bytes((out/'before-guards').read_bytes()))
    padded=padded_object(root,out,obj,'candidate',guards)
    old_padded=padded_object(root,out,old,'owner-before',out/'before-guards')
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:raise ValueError('Link-event padded neighbors changed')
    truth=list(struct.unpack_from('>43I',(out/'before-retail_rom').read_bytes(),ROM));images=[]
    for p in (obj,padded):
        data,functions=build.link_owner(root,out,p,OWNER);f=functions[FUNCTION]
        images.append(list(struct.unpack_from('>43I',data,f['value'])))
    if images[1]!=truth or [i for i,(a,b) in enumerate(zip(images[0],truth)) if a!=b]!=[34]:
        raise ValueError('Incomplete link-event match')
    if (images[0][34],truth[34])!=(0x548A0005,0x55440005):raise ValueError('Unknown branch operand difference')
    row=dict(words=43,frame=24,bindings=1,new_guards=1,raw_differences=1,unchanged_raw_padded_neighbors=neighbors)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
