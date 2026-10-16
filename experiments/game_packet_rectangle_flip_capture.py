"""Test an inner flag snapshot after the rectangle's fractional-T conversion."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_middle as previous
from tools.experiments import game_packet_rectangle_compiler_trace as compiler
from tools.experiments import game_packet_rectangle_fitting as fitted
from tools.experiments.game_packet_rectangle_lifetime import shape
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.experiments.game_actor_classifier_candidates import sections

BUILD='conker/build/game-packet-rectangle-flip-capture'
OWNER,FUNCTION,ENTRY,ROM,WORDS=previous.OWNER,previous.FUNCTION,previous.ENTRY,previous.ROM,previous.WORDS
PATHS,BASELINE,build=previous.PATHS,previous.BASELINE,previous.build
INITIAL=previous.SELECTED
PREDECESSOR_FREEZE=previous.freeze


def freeze(root,out):
    from tools.tests import packet_rectangle_flip_capture_checkpoint as checkpoint
    read=Path.read_bytes
    with patch.object(Path,'read_bytes',lambda p:checkpoint.previous_input(read(p),p,root)):
        PREDECESSOR_FREEZE(root,out)


def recovered_owner(before,selected=None):
    return previous.recovered_owner(before,SELECTED if selected is None else selected)


def measure(root,out,label='selected',selected=None):
    with patch.object(previous,'freeze',freeze):
        return previous.measure(root,out,label,SELECTED if selected is None else selected)


def forms():
    yield 'predecessor',INITIAL
    without=INITIAL.replace('    flipFlags = packet->flipFlags;\n','')
    body=without.replace('    if (flipFlags != 0) {',
        '    if (packet->flipFlags != 0) {\n        flipFlags = packet->flipFlags;',1)
    yield 'inner-snapshot',body
    yield 'inner-snapshot-mixed',body.replace('* 32.0f','* 32')
    mixed=body.replace('* 32.0f','* 32')
    for role in ('S','T'):
        name='step'+role
        original='originalStep'+role
        split=mixed.replace('    s32 '+name+';', '    s32 '+original+';\n    s32 '+name+';').replace(
            '    '+name+' = numerator / integerScale'+('X' if role=='S' else 'Y')+';',
            '    '+original+' = numerator / integerScale'+('X' if role=='S' else 'Y')+';\n'
            '    '+name+' = '+original+';').replace('(u32)'+name,'(u32)'+original)
        yield 'shaped-split-'+role,split
    yield 'shaped-block-scope',mixed.replace('    s32 flipFlags;\n','').replace(
        '        flipFlags = packet->flipFlags;', '        s32 flipFlags = packet->flipFlags;',1)
    yield 'shaped-direct-condition',mixed.replace('if (packet->flipFlags != 0)', 'if (packet->flipFlags)')
    yield 'shaped-masked-condition',mixed.replace('if (packet->flipFlags != 0)', 'if ((packet->flipFlags & 255) != 0)')
    for kind in ('u32','u8','s8','u16','s16'):
        typed=body.replace('    s32 flipFlags;', '    '+kind+' flipFlags;')
        yield 'typed-inner-'+kind,typed
        yield 'typed-inner-'+kind+'-mixed',typed.replace('* 32.0f','* 32')
    body=without.replace('    if (flipFlags != 0) {',
        '    if (packet->flipFlags != 0) {',1).replace('if (flipFlags & 1)',
        'if ((flipFlags = packet->flipFlags) & 1)',1)
    yield 'assigned-inner-snapshot',body
    yield 'assigned-inner-snapshot-mixed',body.replace('* 32.0f','* 32')


TRACE_SIGNATURE={'316ee797208d3d0561a22693e1b90862dd5e6f53492a60f9eb01836cda584aff':
    '6f15273cc09304bf1324a83acc427bd35436e66e7d8fe2ed8599a5f9db458c57',
    'f95ee415f2eba533fa4076e5f6c42331367bf3444eb855a78b7816f598dc48c3':
    '6f15273cc09304bf1324a83acc427bd35436e66e7d8fe2ed8599a5f9db458c57'}
SELECTED=dict(forms())['shaped-split-S']
RAW_SHA256='f95ee415f2eba533fa4076e5f6c42331367bf3444eb855a78b7816f598dc48c3'
SLOT_SHA256='ad37e44da7fb64c05539fe6d3529b2d1c4edf53305fb0e51d68f13dc88c394c2'
RELOCATIONS=fitted.RELOCATIONS


def checked_object(obj):
    text,funcs,rel=parse_object(obj)
    f=funcs[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
    pools={n:d for n,(_,d) in sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=1384 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=RELOCATIONS or pools:
        raise ValueError('Unknown rectangle inner-capture words, bindings or pools')
    return raw,bindings


def candidate_slot(data):
    if len(data)!=1384 or hashlib.sha256(data).hexdigest()!=SLOT_SHA256:
        raise ValueError('Unknown rectangle inner-capture linked slot')
    return data


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified')
    checked_object(obj)
    truth=list(struct.unpack_from('>346I',(out/'before-retail_rom').read_bytes(),ROM))
    if (row['words'],row['frame'],row['differences'],row['diagnostics'])!=(346,136,18,''):
        raise ValueError('Unknown rectangle inner-capture compiler shape')
    if words[:148]!=truth[:148] or words[-91:]!=truth[-91:]:
        raise ValueError('Lost rectangle inner-capture literal spans')
    padded=out/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(obj,root/PATHS['packet_original'],filename=OWNER,
        word_patches_path=out/'before-guards'))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded.with_suffix('.o')),str(padded)],
        check=True,capture_output=True)
    data,functions=build.link_owner(root,out,padded.with_suffix('.o'),OWNER)
    f=functions[FUNCTION]
    slot=candidate_slot(data[f['value']:f['value']+1384])
    if f['size']!=1384 or slot!=struct.pack('>346I',*words):
        raise ValueError('Rectangle inner-capture padder changed the body')
    target=out/'predicted-slot.bin'
    if not target.exists():
        target.write_bytes(slot)
    if target.read_bytes()!=slot:
        raise ValueError('Changed rectangle inner-capture first slot prediction')
    row.update(new_guards=0,raw_match=False,body_bytes=1384,slot_bytes=1384,
        literal_prefix_words=148,literal_suffix_words=91)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded.with_suffix('.o'),words,row


def slot_expected_image(before,slot):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:
        raise ValueError('Unknown rectangle inner-capture predecessor ELF')
    candidate_slot(slot)
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,1384):
        raise ValueError('Unknown rectangle inner-capture predecessor extent')
    result=bytearray(before)
    at=elf_slot_offset(before,ENTRY,1384)
    result[at:at+1384]=slot
    return bytes(result)


def expected_inputs(root,out):
    return dict(elf=slot_expected_image((out/'before-elf').read_bytes(),(out/'predicted-slot.bin').read_bytes()),
        packet_owner=recovered_owner((out/'before-packet_owner').read_text()).encode())


def prelink_prediction(root,out):
    def adapter(root,out):
        obj,padded,words,row=qualify(root,out)
        return obj,padded,words,None,row
    core=fitted.previous.previous.previous.previous
    with patch.multiple(core,PATHS=PATHS,BASELINE=BASELINE,qualify=adapter,expected_inputs=expected_inputs):
        row=core.prelink_prediction(root,out)
    row.pop('draw_guards')
    row.pop('projected_guards')
    row.update(slot_bytes=1384,body_bytes=1384,new_guards=0,raw_match=False,unresolved_differences=18,
        metadata_serialization_bytes=0,literal_prefix_words=148,literal_suffix_words=91)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def trace(root,out,label):
    body=SELECTED
    with patch.object(compiler,'SIGNATURES',dict(compiler.SIGNATURES,**TRACE_SIGNATURE)):
        result=compiler.trace(root,out,label,body)
    return {k:result[k] for k in ('label','normal','code_unchanged','record_counts','installable')}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--filter',default='')
    parser.add_argument('--trace')
    parser.add_argument('--qualify',action='store_true')
    parser.add_argument('--prelink',action='store_true')
    args=parser.parse_args()
    if args.prelink:
        print(json.dumps(prelink_prediction(args.root,args.root/BUILD),indent=2))
        return
    if args.qualify:
        print(json.dumps(qualify(args.root,args.root/BUILD)[-1],indent=2))
        return
    if args.trace:
        print(json.dumps(trace(args.root,args.root/BUILD,args.trace),indent=2))
        return
    for label,body in forms():
        if args.filter and args.filter not in label:
            continue
        out=args.root/BUILD
        row=measure(args.root,out,label,body)[2]
        print(json.dumps(dict({k:row[k] for k in ('label','words','frame','differences','diagnostics')},
            **shape(out,label))),flush=True)


if __name__=='__main__':
    main()
