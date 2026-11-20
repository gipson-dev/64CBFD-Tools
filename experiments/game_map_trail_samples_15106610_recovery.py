"""Private recovery of interior map-trail radial samples."""
import hashlib,json,os,re,struct,subprocess
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_map_trail_update_1510608c_recovery import bind
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
BUILD='conker/build/game-map-trail-samples-15106610-private';OUT=ROOT/BUILD
SOURCE='conker/src/game/generated_133190.c';FUNCTION='func_15106610'
ENTRY,ROM,WORDS,FRAME=0x15106610,0x133AC0,106,112
STUB='#pragma GLOBAL_ASM("asm/nonmatchings/generated_133190/func_15106610.s")'
PREAMBLE='''f32 func_150ADA68(void);
void func_15143874(s16, f32, f32 *, f32 *);
'''
BODY='''/* Offset each interior sample in its curve frame, retaining both endpoints. */
void func_15106610(MapTrailRecord133190 *record) {
    MapTrailSegment133190 *segments, *segment;
    MapTrailPoint133190 *points, *point;
    s32 random;
    s32 i;
    f32 second;
    f32 first;
    f32 sample;

    segments = func_151061E0(record);
    points = (MapTrailPoint133190 *)func_151061EC((u8 *)record);
    points[0] = record->packet.points[0];
    points[record->packet.pieces + 1] = record->packet.points[3];
    i = 1;
    if ((s32)((u32)record->packet.pieces + 1U) >= 2) {
        do {
            point = &points[i];
            segment = &segments[i - 1];
            random = func_150ADA20();
            sample = func_150ADA68();
            func_15143874((s16)(random & 255), sample * record->packet.width,
                          &first, &second);
            point->x = (segment->normal.x * first + segment->binormal.x * second) + segment->position.x;
            point->y = (segment->normal.y * first + segment->binormal.y * second) + segment->position.y;
            point->z = (segment->normal.z * first + segment->binormal.z * second) + segment->position.z;
            i++;
        } while (i <= record->packet.pieces);
    }
}'''

def source():
    fp=json.loads((OUT/'baseline/fingerprints.json').read_text());path=OUT/'baseline'/SOURCE
    assert hashlib.sha256(path.read_bytes()).hexdigest()==fp['inputs'][SOURCE]
    before=path.read_text();assert before.count(STUB)==1
    return before,before.replace(STUB,PREAMBLE+'\n'+BODY,1)

def screen():
    out=OUT/'screen';out.mkdir(parents=True,exist_ok=True)
    before,after=source();old,old_diag=compile_owner(ROOT,out,before,'before');obj,diag=compile_owner(ROOT,out,after,'candidate')
    raw,refs=payload(obj,FUNCTION);words=bind(raw,refs)
    retail=struct.unpack_from('>106I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)
    assert normalized_pools(old)==normalized_pools(obj),'Owner pools changed'
    clean=lambda t:re.sub(r'\S+\.c, line \d+:','<owner>:',t)
    assert clean(old_diag)==clean(diag),(old_diag,diag)
    dis=subprocess.run(['mips-linux-gnu-objdump','-dr',str(obj)],capture_output=True,text=True,check=True)
    (out/'candidate-disassembly.txt').write_text(dis.stdout)
    result=dict(function=FUNCTION,source_installed=False,credit=0,words=len(words),frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,retail))+abs(len(words)-WORDS),
        unchanged_neighbors=same_functions(old,obj,(FUNCTION,)),pools_unchanged=True,
        raw_sha256=hashlib.sha256(raw).hexdigest(),diagnostics=diag)
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='diagnostics'}));return result

def caller_census():
    rom=(ROOT/'conker/conker.us.bin').read_bytes()
    def offsets(value):
        needle=struct.pack('>I',value);result=[];at=0
        while True:
            at=rom.find(needle,at)
            if at<0:return result
            if at%4==0:result.append(at)
            at+=1
    direct=offsets(0x0C000000|((ENTRY>>2)&0x3FFFFFF));pointers=offsets(ENTRY)
    assert direct==[0x1332C4,0x1335FC],direct
    assert pointers==[],pointers
    live=(ROOT/SOURCE).read_text()
    assert 'void func_15106610(MapTrailRecord133190 *);'in live
    assert live.count('func_15106610(record);')==1
    assert live.count('func_15106610((MapTrailRecord133190 *)node);')==1
    polar=(ROOT/'conker/src/game_16EE20.c').read_text()
    assert 'void func_15143874(s16 arg0, f32 arg1, f32 *arg2, f32 *arg3)'in polar
    return dict(direct_JALs=direct,literal_pointers=pointers,callers=['func_15105CE0','func_1510608C'],
                signature='void(MapTrailRecord133190 *)',polar_signature='void(s16,f32,f32*,f32*)',
                private_homes=[80,84],complete_parent_execution_qualified=False,arbitrary_computed_callers_excluded=False)

if __name__=='__main__':screen()
