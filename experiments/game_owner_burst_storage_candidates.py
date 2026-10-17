"""Screen compiler-observed packet alignment and nonoverlapping local storage."""
import json
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_owner_burst_emitter as source
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools
import struct

BUILD='conker/build/game-owner-burst-storage'


def aligned_pairs(body,types):
    declaration='    BurstVector2D14 *inputs[2];'
    if body.count(declaration)!=1:raise ValueError('Unknown burst input-pair declaration')
    types+='''typedef union {
    BurstVector2D14 *points[2];
    u8 *created;
    u64 alignment;
} BurstInputPair2D14;
'''
    body=body.replace(declaration,'    BurstInputPair2D14 inputs;').replace('inputs[0]','inputs.points[0]').replace(
        'inputs[1]','inputs.points[1]').replace('func_15145EA4(inputs,','func_15145EA4(inputs.points,')
    return body,types


def const_scale(body,types):
    anchor='extern f32 D_800A195C[], D_800A1968, D_800A196C;'
    if types.count(anchor)!=1:raise ValueError('Unknown burst rodata declaration')
    types=types.replace(anchor,'extern f32 D_800A195C[], D_800A1968;\nextern const f32 D_800A196C;')
    return body.replace('    f32 multiplier;\n','').replace('                multiplier = D_800A196C;\n','').replace(
        'payload.multiplier = multiplier;','payload.multiplier = D_800A196C;'),types


def copy_phase(body,types):
    return body.replace('    u8 *created;\n','').replace('created = func_1513D2F0(',
        'inputs.created = func_1513D2F0(').replace('if (created != NULL)',
        'if (inputs.created != NULL)').replace('memcpy(created + 0x110,','memcpy(inputs.created + 0x110,'),types


def inline_owner(body,types):
    body=body.replace('    u8 *owner;\n','').replace('        owner = data->owner;\n','')
    for a,b in (('*(s32 *)owner','*(s32 *)data->owner'),('owner[','data->owner['),
            ('(owner + 0x1D4)','(data->owner + 0x1D4)'),('payload.owner = owner;','payload.owner = data->owner;')):
        body=body.replace(a,b)
    return body,types


def inline_data(body,types):
    body=body.replace('    Generated11FF10Payload *data;\n','').replace(
        '    data = (Generated11FF10Payload *)(actor + 0x28);\n    savedData = data;',
        '    savedData = (Generated11FF10Payload *)(actor + 0x28);').replace(
        'Generated11FF10Payload *savedData;','Generated11FF10Payload *volatile savedData;').replace(
        'data->','((Generated11FF10Payload *)(actor + 0x28))->')
    return body,types


def forms():
    _,body,types=next(source.alignment_forms())
    body,types=aligned_pairs(body,types)
    yield 'aligned-pairs',body,types
    yield 'aligned-const-scale',*const_scale(body,types)
    yield 'aligned-copy-phase',*copy_phase(body,types)
    both=copy_phase(*const_scale(body,types))
    yield 'aligned-const-copy',*both
    owner=inline_owner(*both)
    yield 'aligned-inline-owner',*owner
    yield 'aligned-inline-data',*inline_data(*owner)


def measure(root,out,label,body,types):
    with patch.object(source,'TYPE',types):obj,words,row=source.measure(root,out,label,body)
    return obj,words,row


def qualify_aligned(root,out):
    label,body,types=next(forms());obj,words,row=measure(root,out,label,body,types)
    if (row['words'],row['frame'],row['differences'],row['raw_sha'])!=(288,352,85,
            '23e2faa5074572a4fddad79b0676cc091d94668583ecf8b952b8015c1dc5f079'):
        raise ValueError('Changed aligned-pair burst candidate')
    old,diag=source.compile_owner(root,out,(out/'before-record_gate_owner').read_text(),'owner-before')
    if diag or normalized_pools(old)!=normalized_pools(obj):raise ValueError('Changed aligned-pair owner/pools')
    neighbors=same_functions(old,obj,(source.FUNCTION,));padded=source.padded_object(root,out,obj,'aligned-pairs')
    if same_functions(source.padded_object(root,out,old,'owner-before'),padded,(source.FUNCTION,))!=neighbors:
        raise ValueError('Changed aligned-pair padded neighbors')
    data,fs=source.build.link_owner(root,out,padded,source.OWNER)
    padded_words=list(struct.unpack_from('>288I',data,fs[source.FUNCTION]['value']))
    if padded_words!=words:raise ValueError('Unexpected aligned-pair padding rewrite')
    row.update(unchanged_raw_padded_neighbors=neighbors,owner_pools_unchanged=True,new_guards=0,matching_credit=0)
    (out/'aligned-pairs-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,[words,padded_words],row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];out=root/BUILD;results=[]
    for label,body,types in forms():
        row=measure(root,out,label,body,types)[-1];results.append(dict(label=label,**row))
        print(label,json.dumps({k:v for k,v in row.items() if k!='bindings'}),flush=True)
    (out/'measurements.json').write_text(json.dumps(results,indent=2)+'\n')
