"""Recover the active-view world-point projection as direct byte-exact C."""
import hashlib,json,os,re,struct,subprocess
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_map_trail_update_1510608c_recovery import bind
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
BUILD='conker/build/game-view-point-projection-1517eaac-private';OUT=ROOT/BUILD
SOURCE='conker/src/game/generated_1AB530.c';FUNCTION='func_1517EAAC'
OWNER='generated_1AB530';OBJECT='conker/build/src/game/generated_1AB530.c.o'
ENTRY,ROM,WORDS,FRAME=0x1517EAAC,0x1ABF5C,92,152
STUB='s32 func_1517EAAC() {\n    return 0;\n}'
PREAMBLE='typedef struct {\n    u8 opaque0[0x380];\n    f32 rotationY;\n    u8 opaque384[4];\n    f32 rotationX;\n    u8 opaque38C[0x260];\n    f32 rotationZ;\n    u8 opaque5F0[0x3B0];\n} ProjectionCamera1AB530;\ntypedef struct {\n    u8 opaque0[0xC];\n    f32 scaleX, scaleY;\n    u8 opaque14[0x16C];\n} ProjectionView1AB530;\nextern ProjectionCamera1AB530 *D_800DBFF0;\nextern ProjectionView1AB530 *D_800BE628;\nextern s32 D_80082FA4;\nvoid func_15110360(s32, f32 [4][4], f32, f32, f32);\nvoid func_150A7A00(f32 [4][4], f32, f32, f32, f32 *, f32 *, f32 *, f32 *);\n'
BODY='/* Project a world point through the active view; reject depths at or below ten. */\ns32 func_1517EAAC(f32 x, f32 y, f32 z, f32 *screenX, f32 *screenY) {\n    f32 rotationX, rotationY, rotationZ;\n    f32 inverse;\n    f32 projectedX, projectedY, projectedZ, projectedW;\n    f32 matrix[4][4];\n    f32 scaleX, scaleY;\n\n    rotationX = -D_800DBFF0[D_80082FA4].rotationX;\n    rotationY = -D_800DBFF0[D_80082FA4].rotationY;\n    rotationZ = D_800DBFF0[D_80082FA4].rotationZ;\n    func_15110360(D_80082FA4, matrix, rotationX, rotationY, rotationZ);\n    scaleX = D_800BE628[D_80082FA4].scaleX;\n    scaleY = D_800BE628[D_80082FA4].scaleY;\n    func_150A7A00(matrix, x, y, z, &projectedX, &projectedY,\n                  &projectedZ, &projectedW);\n    if (projectedW > 10.0f) {\n        inverse = 1.0f / projectedW;\n        projectedX = projectedX * scaleX * inverse;\n        projectedY = projectedY * scaleY * inverse;\n        *screenX = scaleX + projectedX;\n        *screenY = scaleY - projectedY;\n        return 1;\n    }\n    *screenX = 0.0f;\n    *screenY = 0.0f;\n    return 0;\n}'

def source():
    fp=json.loads((OUT/'baseline/fingerprints.json').read_text());p=OUT/'baseline'/SOURCE
    assert hashlib.sha256(p.read_bytes()).hexdigest()==fp['inputs'][SOURCE]
    before=p.read_text();assert before.count(STUB)==1
    return before,before.replace(STUB,PREAMBLE+'\n'+BODY,1)

def screen():
    out=OUT/'qualified-screen';out.mkdir(parents=True,exist_ok=True)
    before,after=source();old,bd=compile_owner(ROOT,out,before,'before');obj,ad=compile_owner(ROOT,out,after,'candidate')
    raw,refs=payload(obj,FUNCTION);words=bind(raw,refs)
    retail=struct.unpack_from('>92I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)
    assert tuple(words)==retail and ((-words[0])&65535)==FRAME
    assert hashlib.sha256(raw).hexdigest()=='4b986c6b2542fe26fad290c59a44247bbe107d43ca79d51d015c108ad26da6fd'
    assert normalized_pools(old)==normalized_pools(obj)
    clean=lambda t:re.sub(r'\S+\.c, line \d+:','<owner>:',t)
    assert clean(bd)==clean(ad),(bd,ad)
    neighbors=same_functions(old,obj,(FUNCTION,));assert neighbors==7
    result=dict(function=FUNCTION,words=92,frame=152,differences=0,unchanged_neighbors=neighbors,
        pools_unchanged=True,diagnostics=ad,source_installed=(ROOT/SOURCE).read_text()==after,
        raw_SHA256=hashlib.sha256(raw).hexdigest())
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def caller_census():
    rom=(ROOT/'conker/conker.us.bin').read_bytes()
    def offsets(value):
        needle=struct.pack('>I',value);at=0;result=[]
        while True:
            at=rom.find(needle,at)
            if at<0:return result
            if at%4==0:result.append(at)
            at+=1
    direct=offsets(0x0C000000|((ENTRY>>2)&0x3FFFFFF));pointers=offsets(ENTRY)
    assert direct==[0x1AB838] and pointers==[],(direct,pointers)
    assert struct.unpack_from('>10I',rom,0x1AB820)==(0x00085880,0x004B1021,0x8C42CFFC,0xC44C0000,0xC44E0004,0x8C460008,0x0D45FAAB,0xAFB80010,0x10530002,0x241200FF)
    actual=(ROOT/'conker/src/game/generated_13D350.c').read_text()
    assert 'void func_15110360(s32 arg0, f32 arg1[4][4], f32 arg2, f32 arg3, f32 arg4)'in actual
    assert 'func_150A7A00(f32 matrix[4][4], f32 x, f32 y, f32 z,'in(ROOT/'conker/src/game_476D0.c').read_text()
    return dict(direct_JALs=direct,literal_pointers=pointers,signature='s32(f32,f32,f32,f32*,f32*)',
        caller='func_1517E28C',caller_window_ROM=0x1AB820,matrix_home=0x38,output_homes=[0x84,0x80,0x7C,0x78],
        complete_parent_execution_qualified=False,arbitrary_computed_callers_excluded=False)

if __name__=='__main__':print(json.dumps(screen()))
