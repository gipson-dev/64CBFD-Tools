"""Private semantic recovery of the cubic map-trail curve builder."""
import hashlib,json,os,re,struct,subprocess
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_map_trail_update_1510608c_recovery import bind
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
BUILD='conker/build/game-map-trail-curve-15106214-private'
OUT=ROOT/BUILD
SOURCE='conker/src/game/generated_133190.c'
FUNCTION='func_15106214'
ENTRY,ROM,WORDS,FRAME=0x15106214,0x1336C4,168,128
STUB='#pragma GLOBAL_ASM("asm/nonmatchings/generated_133190/func_15106214.s")'

VIEW='''typedef struct {
    f32 parameter;
    MapTrailPoint133190 position, tangent, normal, binormal;
} MapTrailSegment133190;
'''
PREAMBLE='''f32 func_151064B4(f32);
f32 func_151064DC(f32);
f32 func_15106510(f32);
f32 func_15106540(f32);
f32 func_15106558(f32);
f32 func_15106584(f32);
f32 func_151065BC(f32);
f32 func_151065EC(f32);
s32 func_15146078(MapTrailPoint133190 *, MapTrailPoint133190 *, MapTrailPoint133190 *);
'''
BODY='''/* Sample the cubic curve and construct a frame for each interior segment. */
void func_15106214(MapTrailRecord133190 *record) {
    MapTrailPoint133190 *tangent, *normal, *binormal;
    f32 step, parameter;
    s32 i;
    MapTrailSegment133190 *segment;
    f32 b0, b1, b2, b3, d0, d1, d2, d3;

    segment = func_151061E0(record);
    step = record->reciprocal;
    parameter = step;
    i = 0;
    if (record->packet.pieces > 0) {
        tangent = &segment->tangent;
        normal = &segment->normal;
        binormal = &segment->binormal;
        do {
            segment->parameter = parameter;
            b0 = func_151064B4(parameter);
            b1 = func_151064DC(parameter);
            b2 = func_15106510(parameter);
            b3 = func_15106540(parameter);
            d0 = func_15106558(parameter);
            d1 = func_15106584(parameter);
            d2 = func_151065BC(parameter);
            d3 = func_151065EC(parameter);
            segment->position.x = record->packet.points[0].x * b0 + record->packet.points[1].x * b1 +
                record->packet.points[2].x * b2 + record->packet.points[3].x * b3;
            segment->position.y = record->packet.points[0].y * b0 + record->packet.points[1].y * b1 +
                record->packet.points[2].y * b2 + record->packet.points[3].y * b3;
            segment->position.z = record->packet.points[0].z * b0 + record->packet.points[1].z * b1 +
                record->packet.points[2].z * b2 + record->packet.points[3].z * b3;
            segment->tangent.x = record->packet.points[0].x * d0 + record->packet.points[1].x * d1 +
                record->packet.points[2].x * d2 + record->packet.points[3].x * d3;
            segment->tangent.y = record->packet.points[0].y * d0 + record->packet.points[1].y * d1 +
                record->packet.points[2].y * d2 + record->packet.points[3].y * d3;
            segment->tangent.z = record->packet.points[0].z * d0 + record->packet.points[1].z * d1 +
                record->packet.points[2].z * d2 + record->packet.points[3].z * d3;
            if (func_15146078(tangent, normal, binormal) == 0) {
                segment->normal.x = 0.0f;
                segment->normal.y = 0.0f;
                segment->normal.z = 0.0f;
                segment->binormal.x = 0.0f;
                segment->binormal.y = 0.0f;
                segment->binormal.z = 0.0f;
            }
            i++;
            segment++;
            tangent = (MapTrailPoint133190 *)((u8 *)tangent + sizeof(*segment));
            normal = (MapTrailPoint133190 *)((u8 *)normal + sizeof(*segment));
            binormal = (MapTrailPoint133190 *)((u8 *)binormal + sizeof(*segment));
            parameter += step;
        } while (i < record->packet.pieces);
    }
}'''


def source():
    fp=json.loads((OUT/'baseline/fingerprints.json').read_text())
    path=OUT/'baseline'/SOURCE
    assert hashlib.sha256(path.read_bytes()).hexdigest()==fp['inputs'][SOURCE]
    before=path.read_text()
    assert before.count(STUB)==1
    old='s32 func_151061E0(s32 arg0) {\n    return arg0 + 0x88;\n}'
    assert before.count(old)==1
    getter='MapTrailSegment133190 *func_151061E0(void *record) {\n    return (MapTrailSegment133190 *)((u8 *)record + 0x88);\n}'
    after=before.replace(old,VIEW+'\n'+getter,1).replace(STUB,PREAMBLE+'\n'+BODY,1)
    return before,after


def screen():
    out=OUT/'screen';out.mkdir(parents=True,exist_ok=True)
    before,after=source()
    old,old_diagnostics=compile_owner(ROOT,out,before,'before')
    obj,diagnostics=compile_owner(ROOT,out,after,'candidate')
    raw,refs=payload(obj,FUNCTION);words=bind(raw,refs)
    retail=struct.unpack_from('>%dI'%WORDS,(ROOT/'conker/conker.us.bin').read_bytes(),ROM)
    assert normalized_pools(old)==normalized_pools(obj),'Owner pools changed'
    clean=lambda t:re.sub(r'\S+\.c, line \d+:','<owner>:',t)
    assert clean(old_diagnostics)==clean(diagnostics),(old_diagnostics,diagnostics)
    dis=subprocess.run(['mips-linux-gnu-objdump','-dr',str(obj)],capture_output=True,text=True,check=True)
    (out/'candidate-disassembly.txt').write_text(dis.stdout)
    result=dict(function=FUNCTION,source_installed=False,credit=0,words=len(words),frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,retail))+abs(len(words)-WORDS),
        unchanged_neighbors=same_functions(old,obj,(FUNCTION,)),pools_unchanged=True,
        raw_sha256=hashlib.sha256(raw).hexdigest(),diagnostics=diagnostics)
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='diagnostics'}))
    return result


def caller_census():
    rom=(ROOT/'conker/conker.us.bin').read_bytes()
    def offsets(value):
        needle=struct.pack('>I',value);result=[];at=0
        while True:
            at=rom.find(needle,at)
            if at<0:return result
            if at%4==0:result.append(at)
            at+=1
    direct=offsets(0x0C000000|((ENTRY>>2)&0x3FFFFFF))
    pointers=offsets(ENTRY)
    assert direct==[0x1332BC,0x1335D4],direct
    assert pointers==[],pointers
    live=(ROOT/SOURCE).read_text()
    assert 'void func_15106214(MapTrailRecord133190 *);'in live
    assert live.count('func_15106214(record);')==1
    assert live.count('func_15106214((MapTrailRecord133190 *)node);')==1
    return dict(direct_JALs=direct,literal_pointers=pointers,
                callers=['func_15105CE0','func_1510608C'],signature='void(MapTrailRecord133190 *)',
                complete_parent_execution_qualified=False,arbitrary_computed_callers_excluded=False)


if __name__=='__main__':screen()
