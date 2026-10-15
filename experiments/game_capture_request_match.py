"""Close the capture request's allocation/schedule delta with guarded relocations."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_capture_request_slot as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.pad_generated_object import parse_object,emit_padded_assembly

BUILD=source.BUILD+'/match'
RAW_SHA256='c118408dfbd80615033bf5797a72c6814ad980061b913bc0cb57ab96179d4948'
RAW_RELOCATIONS={4:[('R_MIPS_HI16','D_800DD348')],8:[('R_MIPS_HI16','D_800DD3FC')],
    12:[('R_MIPS_LO16','D_800DD348')],16:[('R_MIPS_LO16','D_800DD3FC')]}
POINTER_WORDS=(0x4,0x8,0xC,0x10,0x14,0x1C,0x20,0x24,0x30,0x34,0x40,0x44,0x54,0x84,0x88,0x8C)
# Destination/source offsets form a bijection; no instruction is inserted or omitted.
SCHEDULE={0xC:0x10,0x10:0xC,0x20:0x28,0x24:0x38,0x28:0x48,0x30:0x20,
    0x34:0x24,0x38:0x30,0x3C:0x34,0x40:0x44,0x44:0x50,0x48:0x54,
    0x4C:0x3C,0x50:0x40,0x54:0x4C}
GUARDS=((0x4,0x3C020000,0x3C030000),(0x8,0x3C030000,0x3C020000),
    (0xC,0x24420000,0x24420000),(0x10,0x24630000,0x24630000),
    (0x14,0x904E000C,0x906E000C),(0x1C,0x2442003C,0x2463003C),
    (0x20,0xE44C0000,0xC7A40008),(0x24,0xE44E0004,0x83B80013),
    (0x28,0xC7A40008,0x8FB90014),(0x30,0xA04F000C,0xE46C0000),
    (0x34,0xE4440008,0xE46E0004),(0x38,0x83B80013,0xA06F000C),
    (0x3C,0x00E05025,0xE4640008),(0x40,0x00405825,0xA0780034),
    (0x44,0xA0580034,0x10E0000D),(0x48,0x8FB90014,0xAC790038),
    (0x4C,0x24E90024,0x00E05025),(0x50,0x10E0000A,0x00605825),
    (0x54,0xAC590038,0x24E90024),(0x84,0x2442003C,0x2463003C),
    (0x88,0x5443FFE3,0x5462FFE3),(0x8C,0x904E000C,0x906E000C))


def swap_pointer_registers(word):
    opcode=word>>26
    if opcode==15:
        fields=(16,)
    elif opcode in (9,21):
        fields=(21,16)
    elif opcode in (0x24,0x28,0x2B,0x39):
        fields=(21,)
    elif (opcode==0 and word&63==0x25 and (word>>21)&31 in (2,3)
            and (word>>16)&31==0 and (word>>11)&31==11):
        fields=(21,)
    else:
        raise ValueError('Unexpected pointer-lifetime instruction')
    changed=0
    for shift in fields:
        register=(word>>shift)&31
        if register in (2,3):
            word=(word&~(31<<shift))|((5-register)<<shift)
            changed+=1
    if not changed:
        raise ValueError('Pointer lifetime site contains neither cursor nor end')
    return word


def normalized_instructions(raw,relocations):
    if hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or relocations!=RAW_RELOCATIONS:
        raise ValueError('Unknown capture request raw words or relocations')
    words=list(struct.unpack('>39I',raw))
    for offset in POINTER_WORDS:
        words[offset//4]=swap_pointer_registers(words[offset//4])
    mapping={offset:SCHEDULE.get(offset,offset) for offset in range(0,156,4)}
    if set(mapping.values())!=set(mapping):
        raise ValueError('Capture request schedule is not a bijection')
    output=[words[mapping[offset]//4] for offset in range(0,156,4)]
    moved={at:list(relocations[old]) for at,old in mapping.items() if old in relocations}
    old_branch=words[0x50//4]
    if old_branch!=0x10E0000A or output[0x44//4]!=old_branch:
        raise ValueError('Unexpected capture request optional-copy branch')
    target=0x50+4+(old_branch&65535)*4
    if target!=0x7C:
        raise ValueError('Capture request copy suppression target changed')
    output[0x44//4]=(old_branch&0xFFFF0000)|((target-0x44-4)//4)
    if (output[0x7C//4:0x84//4]!=words[0x7C//4:0x84//4] or
            output[0x90//4:]!=words[0x90//4:]):
        raise ValueError('Capture request return values or normal exits changed')
    return output,moved


def relocation_spec(rows):
    return ';'.join(kind+':'+symbol for kind,symbol in rows) if rows else '-'


def guard_rows():
    replacement=dict(RAW_RELOCATIONS)
    replacement[12],replacement[16]=RAW_RELOCATIONS[16],RAW_RELOCATIONS[12]
    return ''.join('%s,%s,0x%X,0x%08X,0x%08X,%s,%s,Preserve closed capture-request allocation and independent scheduling,,,false\n'%(
        source.OWNER,source.FUNCTION,offset,expected,retail,
        relocation_spec(RAW_RELOCATIONS.get(offset,[])),relocation_spec(replacement.get(offset,[])))
        for offset,expected,retail in GUARDS)


def guard_manifest(before):
    if not before.endswith(b'\n') or (','+source.FUNCTION+',').encode() in before:
        raise ValueError('Unexpected capture request guard baseline or duplicate rows')
    return before+guard_rows().encode()


def pad(root,out,obj,label,guards):
    manifest=out/(label+'-guards.csv')
    manifest.write_bytes(guards)
    assembly=emit_padded_assembly(obj,root/source.PATHS['request_original'],filename=source.OWNER,
        word_patches_path=manifest)
    path=out/(label+'.s')
    path.write_text('.include "'+str(root/'conker/include/asm_processor_prelude.inc')+'"\n'+assembly)
    padded=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(path)],capture_output=True,check=True)
    return padded


def qualify(root,out):
    source.freeze(root,root/source.BUILD)
    out.mkdir(parents=True,exist_ok=True)
    obj,_,_=source.qualify(root,root/source.BUILD)
    data,functions,relocations=parse_object(obj)
    f=functions[source.FUNCTION]
    raw=data[f['value']:f['value']+f['size']]
    relative={at-f['value']:v for at,v in relocations.items() if f['value']<=at<f['value']+f['size']}
    normalized,moved=normalized_instructions(raw,relative)
    original=list(struct.unpack('>39I',raw))
    changed=[(i*4,a,b) for i,(a,b) in enumerate(zip(original,normalized))
        if a!=b or relative.get(i*4,[])!=moved.get(i*4,[])]
    if tuple(changed)!=GUARDS:
        raise ValueError('Capture request guards do not equal the closed transformation')
    guards=guard_manifest((root/source.BUILD/'before-guards').read_bytes())
    padded=pad(root,out,obj,'qualified',guards)
    linked,lf=build.link_owner(root,out,padded,source.OWNER)
    target=lf[source.FUNCTION]
    words=list(struct.unpack_from('>40I',linked,target['value']))
    retail=list(struct.unpack_from('>40I',(root/'conker/conker.us.bin').read_bytes(),source.ROM))
    if target['size']!=156 or words!=retail:
        raise ValueError('Guarded capture request does not match the full retail slot')
    receipt=dict(raw_body_words=39,slot_words=40,raw_differences=22,linked_differences=0,
        guards=22,relocation_only_guards=[12,16],pointer_lifetime_sites=len(POINTER_WORDS),
        schedule_bijection=True,optional_copy_target=0x7C,frame=0,profile_unchanged=True,
        guards_are_allocation_and_schedule_only=True,not_a_direct_unguarded_C_match=True)
    (out/'qualification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return obj,padded,words,receipt


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    root=Path(__file__).resolve().parents[2]
    _,_,_,record=qualify(root,root/BUILD)
    print(json.dumps(record,indent=2))


if __name__=='__main__':
    main()
