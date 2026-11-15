"""Recover the complete randomized effect dispatcher without installing it."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-randomized-dispatch-150c2898-private';OUT=ROOT/BUILD
SOURCE='conker/src/game_EF410.c';NAME='func_150C2898'
ENTRY,ROM,SIZE=0x150c2898,0xefd48,344
PREAMBLE='''void *func_151D9014(void *, f32 *, u8, f32, s16, u8, f32, u8,
                    f32, f32, u8, s32, u8, u8, u8, s32);
'''
BODY='''/* Emit a randomized effect opposite the incoming direction. */
void func_150C2898(f32 x, f32 y, f32 z, f32 dx, f32 dy, f32 dz, u8 *owner) {
    f32 position[3];
    f32 velocity[3];
    f32 speed, second;
    u32 secondValue, firstValue;
    f32 first;

    position[0] = x;
    position[1] = y;
    position[2] = z;
    speed = (func_150ADA68() * 112.0f + 247.0f) * D_800A0288;
    velocity[0] = -dx * speed;
    velocity[1] = -dy * speed;
    velocity[2] = -dz * speed;
    first = func_150ADA68();
    firstValue = func_150ADA20();
    secondValue = func_150ADA20();
    second = func_150ADA68();
    func_151D9014(position, velocity, 6,
        first * D_800A028C + D_800A0290,
        (firstValue & 15U) + 25, secondValue % 101U + 155,
        second * 119.0f + 129.0f, 0, 1.0f, 1.0f,
        1, 0, 1, 0, owner[0xC], owner[1]);
}'''

def proposed(source):
 stub=body(source,NAME);assert stub=='s32 func_150C2898() {\n    return 0;\n}'
 result=source.replace(stub,BODY).replace('s32 func_150C2898();\n','')
 result=result.replace('/* Generated placeholder declarations. */',PREAMBLE+'\n/* Generated placeholder declarations. */',1)
 result=result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_EF410/func_150C2898.s. */\n','')
 return result.rstrip()+'\n'

def symbols():return dict(D_800A0288=0x800a0288,D_800A028C=0x800a028c,D_800A0290=0x800a0290,func_150ADA68=0x150ada68,func_150ADA20=0x150ada20,func_151D9014=0x151d9014)

def programs():
 truth=list(struct.unpack_from('>86I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
 raw,refs=payload(OUT/'recovered.o',NAME)
 return truth,bound_blob(raw,refs,symbols())

def main():
 frozen=OUT/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 before=(frozen/SOURCE).read_text();candidate=proposed(before);installed=(ROOT/SOURCE).read_text()==candidate
 plan=json.loads((OUT/'adoption-plan.json').read_text()) if (OUT/'adoption-plan.json').exists() else {}
 for name,want in record['inputs'].items():assert sha(ROOT/name)==(plan.get(name,want) if installed else want),name
 base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,candidate,'recovered')
 assert d1==d2,(d1,d2)
 neighbors=same_functions(base,obj,(NAME,));assert normalized_pools(base)==normalized_pools(obj)
 truth,raw=programs();assert truth==raw and len(raw)==86 and raw[0]==0x27bdff88 and neighbors==17
 blob,refs=payload(obj,NAME)
 report=dict(body_words=len(raw),retail_words=86,frame=120,neighbors=neighbors,real_word_differences=0,raw_sha256=hashlib.sha256(blob).hexdigest(),bindings=len(refs),guards=0,installed=installed,c_match_credit=int(installed))
 for name,want in record['inputs'].items():assert sha(ROOT/name)==(plan.get(name,want) if installed else want),name
 (OUT/'recovery-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
