"""Derive the retail conditional layout from source instructions, not a ROM array."""
from pathlib import Path
import hashlib,json,struct,subprocess
from tools.experiments import game_list_render_1517e28c_recovery as s
OUT=s.OUT/'cfg-recovery'
SPEC=json.loads((Path(__file__).resolve().parents[1]/'experiments/game_list_render_1517e28c_match_manifest.json').read_text())

def derive(raw,refs):
    if len(raw)!=528 or hashlib.sha256(raw).hexdigest()!=SPEC['raw_sha256']:
        raise ValueError('Unknown renderer source payload')
    expected=SPEC['raw_refs']
    if json.loads(json.dumps(refs))!=expected:raise ValueError('Unknown renderer source bindings')
    words=list(struct.unpack('>132I',raw))
    order=(list(range(45))+[None]+list(range(46,57))+list(range(58,66))+
        [66,57,68,69,70,71,None,73,None,74,75,72,77,45,79,80,81,82,78,83,84,85,86,87,None,88,None]+
        list(range(89,132)))
    assert len(order)==135
    omitted=[67,76]
    assert sorted(i for i in order if i is not None)==[i for i in range(132)if i not in omitted]
    assert words[67]==words[69]==0x960D002A
    assert words[76]==words[89]==0x30590002
    positions={origin:i for i,origin in enumerate(order)if origin is not None}
    result=[];bindings={}
    for i,origin in enumerate(order):
        if origin is None:
            if i in(45,71):w=0
            elif i in(73,89):w=0x10000000|((92-i-1)&65535)
            elif i==91:w=words[88]
            else:raise AssertionError(i)
        else:
            w=words[origin]
            if origin in(66,71):
                assert w>>26==20
                w=(w&0x03FFFFFF)|(4<<26)
            if w>>26 in(1,4,5,6,7,20,21,22,23):
                target=origin+1+(((words[origin]&65535)^32768)-32768)
                target=68 if origin==66 else 92 if origin==75 else positions[target]
                w=(w&0xFFFF0000)|((target-i-1)&65535)
            if origin*4 in refs:bindings[i*4]=refs[origin*4]
        result.append(w)
    report=dict(source_words=132,derived_words=135,source_origins_retained=130,
        omitted_duplicate_origins=omitted,inserted_NOP_indices=[45,71],inserted_branch_indices=[73,89],
        unreachable_duplicate_flag_load_index=91,conditional_likely_to_normal_origins=[66,71],
        output_address_origin=45,output_address_index=78,strength_255_origin=57,strength_255_index=66,
        strength_minus_one_origin=78,strength_minus_one_index=83,
        ROM_or_original_assembly_used_to_generate_output=False)
    assert sum(origin is not None for origin in order)==130
    return struct.pack('>135I',*result),bindings,report

def original():
    text=(s.ROOT/'conker/asm/1AB530.s').read_text();a=text.index('glabel '+s.FUNCTION+'\n');b=text.index('endlabel '+s.FUNCTION,a)+len('endlabel '+s.FUNCTION)
    p=OUT/'original.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+text[a:b]+'\n.size '+s.FUNCTION+',.-'+s.FUNCTION+'\n')
    obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(s.ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True)
    return s.payload(obj,s.FUNCTION)
