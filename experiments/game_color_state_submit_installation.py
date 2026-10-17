"""Predict every first color-helper ELF/source/caller byte before installation."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_color_state_submit as source
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD='conker/build/game-color-state-submit-install'
SERIALIZATION=(
    (('D_800DDDC0','func_150A6F2C'),(1,0),((2148392384,0,16,0,65521),(353005356,12,18,0,65521))),
    (('D_800CC210','D_80088B00'),(1,0),((2148319760,0,16,0,65521),(2148043520,0,16,0,65521))),
)


def digest(data):return hashlib.sha256(data).hexdigest()


def expected_inputs(root,out):
    before=(out/'before-elf').read_bytes()
    if digest(before)!=source.BASELINE['elf']:raise ValueError('Changed color predecessor image')
    row=next(r for r in symbol_rows(before) if r[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown color predecessor extent')
    data=bytearray(before);at=elf_slot_offset(before,source.ENTRY,192)
    data[at:at+192]=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+192]
    struct.pack_into('>I',data,row[0]+8,192)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization,'SERIALIZATION',SERIALIZATION):serialization.apply_burst_symbol_serialization(data)
    result=dict(elf=bytes(data),color_owner=source.recovered_owner((out/'before-color_owner').read_text()).encode())
    for key,_,_,_,old,new in source.CALLERS:
        result[key]=source.recovered_caller((out/('before-'+key)).read_text(),old,new).encode()
    return result


def prelink_prediction(root,out):
    source.freeze(root,out);_,padded,_,_=source.qualify(root,out)
    live=lambda:{k:digest((root/p).read_bytes()) for k,p in source.PATHS.items()}
    capture=out/'link-inputs.json';owners=('game/generated_1AC2F0','game/generated_49D30','game/generated_1A0100')
    captured=[('before-linkscript','conker/build/conker.ld')]+[
        ('before-link-%d.o'%i,'conker/build/src/'+owner+'.c.o') for i,owner in enumerate(owners)]
    if not capture.exists():
        if live()!=source.BASELINE:raise ValueError('Color link capture must precede installation')
        for name,path in captured:(out/name).write_bytes((root/path).read_bytes())
        capture.write_text(json.dumps({name:digest((out/name).read_bytes()) for name,_ in captured},indent=2)+'\n')
    for name,value in json.loads(capture.read_text()).items():
        if digest((out/name).read_bytes())!=value:raise ValueError('Changed color link capture')
    for label,objects in (('baseline',[out/('before-link-%d.o'%i) for i in range(3)]),
            ('prediction',[padded]+[out/(key+'-after-padded.o') for key,_,_,_,_,_ in source.CALLERS])):
        link=(out/'before-linkscript').read_text()
        for owner,obj in zip(owners,objects):
            selector='build/src/'+owner+'.c.o(.text);'
            if link.count(selector)!=1:raise ValueError('Unknown color link selector')
            link=link.replace(selector,str(obj.relative_to(root/'conker'))+'(.text);',1)
        script=out/(label+'.ld');script.write_text(link)
        subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str((out/('prelink-'+label+'.elf')).relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True)
    if (out/'prelink-baseline.elf').read_bytes()!=(out/'before-elf').read_bytes():raise ValueError('Color predecessor not reproduced')
    expected=expected_inputs(root,out);actual=(out/'prelink-prediction.elf').read_bytes()
    if actual!=expected['elf']:raise ValueError('Unpredicted color ELF bytes: %d'%sum(a!=b for a,b in zip(actual,expected['elf'])))
    hashes={k:digest(v) for k,v in expected.items()};initial=out/'initial-prediction.json'
    if not initial.exists():
        if live()!=source.BASELINE:raise ValueError('First color prediction must precede installation')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first color prediction')
    row=dict(after=hashes,changed_ELF_bytes=sum(a!=b for a,b in zip((out/'before-elf').read_bytes(),actual)),
        body_bytes=192,new_guards=0,exact_symbol_groups=len(SERIALIZATION),metadata_exclusions=0)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n');return row


def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:digest(v) for k,v in expected.items()}:
        raise ValueError('Changed color installation prediction')
    patches=[]
    for key,after in expected.items():
        if key=='elf':continue
        path=root/source.PATHS[key];before=path.read_bytes()
        if digest(before)!=source.BASELINE[key]:raise ValueError('Changed color owner/callers')
        diff=list(difflib.unified_diff(before.decode().splitlines(),after.decode().splitlines(),n=3,lineterm=''))
        patches.append('*** Update File: '+str(path)+'\n'+'\n'.join('@@' if line.startswith('@@') else line for line in diff[2:]))
    return '*** Begin Patch\n'+'\n'.join(patches)+'\n*** End Patch\n'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.prepare:print(installation_patch(root,root/BUILD),end='')
    else:print(json.dumps(prelink_prediction(root,root/BUILD),indent=2),flush=True)
