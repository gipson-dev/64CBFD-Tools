"""Recover projected list-depth updates with a closed FP normalization."""
import hashlib,json,os,re,struct,subprocess
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_map_trail_update_1510608c_recovery import bind
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.pad_generated_object import SYMBOL
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
BUILD='conker/build/game-list-depth-1517ec1c-private';OUT=ROOT/BUILD
SOURCE='conker/src/game/generated_1AB530.c';FUNCTION='func_1517EC1C';OWNER='generated_1AB530'
OBJECT='conker/build/src/game/generated_1AB530.c.o'
ENTRY,ROM,WORDS,FRAME,SLOT=0x1517EC1C,0x1AC0CC,135,72,137
STUB='s32 func_1517EC1C() {\n    return 0;\n}'
TYPE_CHANGES={'    u8 opaque0[0xC];': '    f32 position[3];', '    u8 opaque14[0x10];': '    f32 direction[3];\n    f32 facingThreshold;', '    u8 opaque2C[2];': '    u16 depth2C;', '    u8 opaque0[0x380];': '    u8 opaque0[0x2F8];\n    f32 position[3];\n    u8 opaque304[0x7C];', '    u8 opaque14[0x16C];': '    u8 opaque14[0x2C];\n    Vp viewports[2];\n    u8 opaque60[0x120];'}
PREAMBLE='typedef struct {\n    u32 shift, base;\n} PackedDepthRange1AB530;\nextern const PackedDepthRange1AB530 D_80089630[8];\nextern u8 D_800BE9C0;\nf32 sqrtf(f32);\ns32 func_1509563C(f32, f32, f32, f32 *, f32 *, f32 *, f32 *, f32);\n'
BODY='/* Project the record, apply its optional facing gate, and update depth values. */\ns32 func_1517EC1C(ListRecord1AB530 *record, u32 *sampleDepth) {\n    f32 dx, dy, dz;\n    f32 distance;\n    u16 sample;\n    PackedDepthRange1AB530 const *range;\n    f32 depth, divisor;\n\n    if (func_1509563C(record->position[0], record->position[1], record->position[2],\n                      &record->valueC, &record->value10, &depth, &divisor, 4000.0f) == 1) {\n        if (record->flags2E & 4) {\n            dx = record->position[0] - D_800DBFF0->position[0];\n            dy = record->position[1] - D_800DBFF0->position[1];\n            dz = record->position[2] - D_800DBFF0->position[2];\n            distance = sqrtf((dx * dx + dy * dy) + dz * dz);\n            dx = ((dx * record->direction[0] + dy * record->direction[1]) +\n                      dz * record->direction[2]) / distance;\n            if (dx < record->facingThreshold) {\n                return 1;\n            }\n        }\n        sample = record->sample2A;\n        /* The immutable range table contains only shift counts zero through six. */\n        range = &D_80089630[sample >> 13];\n        *sampleDepth = (range->base + (((sample >> 2) & 0x7FFU) << range->shift)) >> 3;\n        record->depth2C = (u32)(((depth / divisor) * D_800BE628->viewports[D_800BE9C0].vp.vscale[2] +\n                               D_800BE628->viewports[D_800BE9C0].vp.vtrans[2]) * 32.0f);\n        return 1;\n    }\n    return 0;\n}'

def source():
    fp=json.loads((OUT/'baseline/fingerprints.json').read_text());p=OUT/'baseline'/SOURCE
    assert hashlib.sha256(p.read_bytes()).hexdigest()==fp['inputs'][SOURCE]
    before=p.read_text();after=before
    for a,b in TYPE_CHANGES.items():
        assert after.count(a)==(2 if a=='    u8 opaque0[0xC];'else 1),a
        after=after.replace(a,b,1)
    assert after.count(STUB)==1
    return before,after.replace(STUB,PREAMBLE+'\n'+BODY,1)

def screen():
    out=OUT/'qualified-screen';out.mkdir(parents=True,exist_ok=True)
    before,after=source();old,bd=compile_owner(ROOT,out,before,'before');obj,ad=compile_owner(ROOT,out,after,'candidate')
    raw,refs=payload(obj,FUNCTION);words=bind(raw,refs)
    retail=struct.unpack_from('>135I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)
    assert len(words)==135 and ((-words[0])&65535)==72
    assert hashlib.sha256(raw).hexdigest()=='a81d5b64888448e1af841741ea1bec6b083146b32e6132f3332f9d07464178ac'
    assert sum(a!=b for a,b in zip(words,retail))==9
    assert normalized_pools(old)==normalized_pools(obj) and not bd and not ad
    assert same_functions(old,obj,(FUNCTION,))==7
    result=dict(function=FUNCTION,words=135,frame=72,differences=9,unchanged_neighbors=7,
        pools_unchanged=True,diagnostics=ad,source_installed=(ROOT/SOURCE).read_text()==after,
        raw_SHA256=hashlib.sha256(raw).hexdigest())
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');return result

def original():
    text=(ROOT/'conker/asm/1AB530.s').read_text();start=text.index('glabel '+FUNCTION+'\n');end=text.index('endlabel '+FUNCTION,start)+len('endlabel '+FUNCTION)
    out=OUT/'qualified-screen';out.mkdir(exist_ok=True);p=out/'original.s'
    p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+text[start:end]+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    obj=p.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True)
    return payload(obj,FUNCTION)

def caller_census():
    rom=(ROOT/'conker/conker.us.bin').read_bytes()
    def offsets(v):
        p=struct.pack('>I',v);at=0;result=[]
        while True:
            at=rom.find(p,at)
            if at<0:return result
            if at%4==0:result.append(at)
            at+=1
    calls=offsets(0x0C000000|((ENTRY>>2)&0x3FFFFFF));pointers=offsets(ENTRY)
    assert calls==[0x1AB870]and pointers==[],(calls,pointers)
    assert struct.unpack_from('>4I',rom,0x1AB870)==(0x0D45FB07,0x27A5006C,0x10530002,0x8FAF006C)
    helper=(ROOT/'conker/src/game/generated_C1D70.c').read_text()
    assert 's32 func_1509563C(f32 x, f32 y, f32 z, f32 *screenX, f32 *screenY,'in helper
    table=rom[0x22E0F0:0x22E130]
    expected=(6,0,5,0x20000,4,0x30000,3,0x38000,2,0x3C000,1,0x3E000,0,0x3F000,0,0x3F800)
    assert struct.unpack('>16I',table)==expected
    image=(ROOT/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(image,0x80089630,64)
    assert image[at:at+64]==table
    return dict(direct_JALs=calls,literal_pointers=pointers,signature='s32(ListRecord1AB530*,u32*)',
        caller='func_1517E28C',depth_home=0x2C,divisor_home=0x28,table_bytes=64,table_shifts=expected[::2],
        C_shift_counts_defined_by_immutable_table=True,full_parent_or_hardware_claim=False)

def reorder_metadata(image):
    """Predict the closed three-name linker rotation from baseline definitions."""
    names=('func_1505A630','func_15073C48','D_800B06BC')
    rows=symbol_rows(image);entries={name:(at,record,string)for at,name,record,string in rows}
    group=[entries[n]for n in names];start,string_at=group[0][0],group[0][2]
    strings_base=string_at-group[0][1][0]
    assert all(at==start+i*SYMBOL.size and string-record[0]==strings_base for i,(at,record,string)in enumerate(group))
    literals=b''.join(n.encode()+b'\0'for n in names)
    assert image[string_at:string_at+len(literals)]==literals
    result=bytearray(image)
    for i,name in enumerate(names[-1:]+names[:-1]):
        record=list(entries[name][1]);record[0]=string_at-strings_base
        SYMBOL.pack_into(result,start+i*SYMBOL.size,*record)
        literal=name.encode()+b'\0';result[string_at:string_at+len(literal)]=literal;string_at+=len(literal)
    canonical=lambda data:sorted((name,record[1:])for _,name,record,_ in symbol_rows(data))
    assert canonical(result)==canonical(image)
    return bytes(result)

if __name__=='__main__':print(json.dumps(screen()))
