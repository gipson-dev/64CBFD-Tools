"""Freeze the first complete overlay image and three typed source successors."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_color_overlay_draw as source
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD='conker/build/game-color-overlay-draw-install'
SERIALIZATION=()


def digest(data):return hashlib.sha256(data).hexdigest()


def expected_inputs(root,out):
    before=(out/'before-elf').read_bytes()
    if digest(before)!=source.BASELINE['elf']:raise ValueError('Changed overlay predecessor image')
    row=next(r for r in symbol_rows(before) if r[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,28):raise ValueError('Unknown overlay predecessor extent')
    data=bytearray(before);at=elf_slot_offset(before,source.ENTRY,788)
    data[at:at+788]=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+788]
    struct.pack_into('>I',data,row[0]+8,788)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization,'SERIALIZATION',SERIALIZATION):serialization.apply_burst_symbol_serialization(data)
    result=dict(elf=bytes(data),color_owner=source.recovered_owner((out/'before-color_owner').read_text()).encode())
    for key,_,_ in source.CALLERS:result[key]=source.recovered_caller((out/('before-'+key)).read_text()).encode()
    return result


def prelink_prediction(root,out):
    source.freeze(root,out);_,padded,_,_=source.qualify(root,out)
    live=lambda:{k:digest((root/p).read_bytes()) for k,p in source.PATHS.items()}
    capture=out/'link-inputs.json';owners=('game/'+source.OWNER,*['game/'+owner for _,owner,_ in source.CALLERS])
    captured=[('before-linkscript','conker/build/conker.ld')]+[
        ('before-link-%d.o'%i,'conker/build/src/'+owner+'.c.o') for i,owner in enumerate(owners)]
    if not capture.exists():
        if live()!=source.BASELINE:raise ValueError('Overlay capture must precede installation')
        for name,path in captured:(out/name).write_bytes((root/path).read_bytes())
        capture.write_text(json.dumps({name:digest((out/name).read_bytes()) for name,_ in captured},indent=2)+'\n')
    for name,value in json.loads(capture.read_text()).items():
        if digest((out/name).read_bytes())!=value:raise ValueError('Changed overlay link capture')
    for label,objects in (('baseline',[out/('before-link-%d.o'%i) for i in range(3)]),
            ('prediction',[padded]+[out/(key+'-after-padded.o') for key,_,_ in source.CALLERS])):
        link=(out/'before-linkscript').read_text()
        for owner,obj in zip(owners,objects):
            selector='build/src/'+owner+'.c.o(.text);'
            if link.count(selector)!=1:raise ValueError('Unknown overlay link selector')
            link=link.replace(selector,str(obj.relative_to(root/'conker'))+'(.text);',1)
        script=out/(label+'.ld');script.write_text(link)
        subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str((out/('prelink-'+label+'.elf')).relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True)
    if (out/'prelink-baseline.elf').read_bytes()!=(out/'before-elf').read_bytes():raise ValueError('Overlay predecessor not reproduced')
    expected=expected_inputs(root,out);actual=(out/'prelink-prediction.elf').read_bytes()
    if actual!=expected['elf']:raise ValueError('Unpredicted overlay ELF bytes: %d'%sum(a!=b for a,b in zip(actual,expected['elf'])))
    hashes={k:digest(v) for k,v in expected.items()};initial=out/'initial-prediction.json'
    if not initial.exists():
        if live()!=source.BASELINE:raise ValueError('First overlay prediction must precede installation')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first overlay prediction')
    row=dict(after=hashes,changed_ELF_bytes=sum(a!=b for a,b in zip((out/'before-elf').read_bytes(),actual)),
        body_bytes=788,new_guards=0,exact_symbol_groups=len(SERIALIZATION),metadata_exclusions=0)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n');return row


def installation_patch(root,out):
    expected=expected_inputs(root,out)
    if json.loads((out/'initial-prediction.json').read_text())!={k:digest(v) for k,v in expected.items()}:
        raise ValueError('Changed overlay installation prediction')
    patches=[]
    for key,after in expected.items():
        if key=='elf':continue
        path=root/source.PATHS[key];before=path.read_bytes()
        if digest(before)!=source.BASELINE[key]:raise ValueError('Changed overlay source/callers')
        diff=list(difflib.unified_diff(before.decode().splitlines(),after.decode().splitlines(),n=3,lineterm=''))
        patches.append('*** Update File: '+str(path)+'\n'+'\n'.join('@@' if line.startswith('@@') else line for line in diff[2:]))
    return '*** Begin Patch\n'+'\n'.join(patches)+'\n*** End Patch\n'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.prepare:print(installation_patch(root,root/BUILD),end='')
    else:print(json.dumps(prelink_prediction(root,root/BUILD),indent=2),flush=True)
