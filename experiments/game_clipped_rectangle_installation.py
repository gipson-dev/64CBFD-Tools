"""Freeze the first complete clipped-rectangle ELF and source prediction."""
import difflib
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_clipped_rectangle as source
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows

BUILD='conker/build/game-clipped-rectangle-install'
SERIALIZATION=()


def digest(data):return hashlib.sha256(data).hexdigest()


def expected_inputs(root,out):
    before=(out/'before-elf').read_bytes()
    if digest(before)!=source.BASELINE['elf']:raise ValueError('Changed clipped rectangle predecessor')
    row=next(row for row in symbol_rows(before) if row[1]==source.FUNCTION)
    if row[2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown clipped rectangle predecessor extent')
    data=bytearray(before);at=elf_slot_offset(before,source.ENTRY,424)
    data[at:at+424]=(out/'before-retail_rom').read_bytes()[source.ROM:source.ROM+424]
    struct.pack_into('>I',data,row[0]+8,424)
    return dict(elf=bytes(data),color_owner=source.recovered_owner((out/'before-color_owner').read_text()).encode())


def predict(root,out):
    source.freeze(root,out);_,padded,_,_=source.qualify(root,out)
    live=lambda:{k:digest((root/p).read_bytes()) for k,p in source.PATHS.items()}
    capture=out/'link-inputs.json';items=(('before-linkscript','conker/build/conker.ld'),
        ('before-owner.o','conker/build/src/game/'+source.OWNER+'.c.o'))
    if not capture.exists():
        if live()!=source.BASELINE:raise ValueError('Rectangle capture must precede installation')
        for name,path in items:(out/name).write_bytes((root/path).read_bytes())
        capture.write_text(json.dumps({name:digest((out/name).read_bytes()) for name,_ in items},indent=2)+'\n')
    for name,value in json.loads(capture.read_text()).items():
        if digest((out/name).read_bytes())!=value:raise ValueError('Changed rectangle link capture')
    selector='build/src/game/'+source.OWNER+'.c.o(.text);'
    for label,obj in (('baseline',out/'before-owner.o'),('prediction',padded)):
        script=(out/'before-linkscript').read_text()
        if script.count(selector)!=1:raise ValueError('Unknown rectangle link selector')
        script=script.replace(selector,str(obj.relative_to(root/'conker'))+'(.text);',1)
        path=out/(label+'.ld');path.write_text(script)
        subprocess.run(['mips-linux-gnu-ld','-T',str(path.relative_to(root/'conker')),'-T','undefined_syms.us.txt',
            '-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt',
            '--no-check-sections','--no-warn-mismatch','-o',str((out/('prelink-'+label+'.elf')).relative_to(root/'conker'))],
            cwd=root/'conker',capture_output=True,check=True)
    if (out/'prelink-baseline.elf').read_bytes()!=(out/'before-elf').read_bytes():raise ValueError('Rectangle baseline not reproduced')
    expected=expected_inputs(root,out);actual=(out/'prelink-prediction.elf').read_bytes()
    if actual!=expected['elf']:raise ValueError('Unpredicted rectangle image differences')
    hashes={k:digest(v) for k,v in expected.items()};initial=out/'initial-prediction.json'
    if not initial.exists():
        if live()!=source.BASELINE:raise ValueError('First rectangle prediction must precede edits')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first rectangle prediction')
    at=elf_slot_offset(actual,source.ENTRY,424);before=(out/'before-elf').read_bytes()
    row=dict(after=hashes,changed_ELF_bytes=sum(a!=b for a,b in zip(before,actual)),
        code_bytes=sum(a!=b for a,b in zip(before[at:at+424],actual[at:at+424])),extent_bytes=2,
        new_guards=0,exact_symbol_groups=0,metadata_exclusions=0)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n');return row


def installation_patch(root,out):
    expected=expected_inputs(root,out);hashes={k:digest(v) for k,v in expected.items()}
    if json.loads((out/'initial-prediction.json').read_text())!=hashes:raise ValueError('Changed rectangle first prediction')
    path=root/source.PATHS['color_owner'];before=path.read_bytes()
    if digest(before)!=source.BASELINE['color_owner']:raise ValueError('Changed rectangle source input')
    diff=list(difflib.unified_diff(before.decode().splitlines(),expected['color_owner'].decode().splitlines(),n=3,lineterm=''))
    return '*** Begin Patch\n*** Update File: '+str(path)+'\n'+'\n'.join('@@' if line.startswith('@@') else line for line in diff[2:])+'\n*** End Patch\n'


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.prepare:print(installation_patch(root,root/BUILD),end='')
    else:print(json.dumps(predict(root,root/BUILD),indent=2),flush=True)
