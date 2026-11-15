"""Complete private scalar-first quaternion matrix recovery, without installation."""
from pathlib import Path
import hashlib,json,os,struct
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-quaternion-matrix-1504a140-private';OUT=ROOT/BUILD
SOURCE='conker/src/game/generated_770F0.c';NAME='func_1504A140'
ENTRY,ROM,SIZE,SLOT_SIZE=0x1504a140,0x775f0,356,368
BODY='''/* Write a scalar-first quaternion's rotation while preserving translation. */
void func_1504A140(f32 *quaternion, f32 *matrix) {
    f32 scale = 2.0f / (((quaternion[0] * quaternion[0] +
        quaternion[1] * quaternion[1]) + quaternion[2] * quaternion[2]) +
        quaternion[3] * quaternion[3]);
    f32 scaledX = quaternion[1] * scale;
    f32 scaledY = quaternion[2] * scale;
    f32 scaledZ = quaternion[3] * scale;
    f32 wx = quaternion[0] * scaledX;
    f32 wy = quaternion[0] * scaledY;
    f32 wz = quaternion[0] * scaledZ;
    f32 xx = quaternion[1] * scaledX;
    f32 xy = quaternion[1] * scaledY;
    f32 xz = quaternion[1] * scaledZ;
    f32 yy = quaternion[2] * scaledY;
    f32 yz = quaternion[2] * scaledZ;
    f32 zz = quaternion[3] * scaledZ;

    matrix[0] = 1.0f - (yy + zz);
    matrix[1] = xy + wz;
    matrix[2] = xz - wy;
    matrix[4] = xy - wz;
    matrix[5] = 1.0f - (xx + zz);
    matrix[6] = yz + wx;
    matrix[8] = xz + wy;
    matrix[9] = yz - wx;
    matrix[10] = 1.0f - (xx + yy);
    matrix[3] = 0.0f;
    matrix[7] = 0.0f;
    matrix[11] = 0.0f;
    matrix[15] = 1.0f;
}'''

def proposed(source):
 stub=body(source,NAME);assert stub=='s32 func_1504A140() {\n    return 0;\n}'
 return source.replace(stub,BODY).rstrip()+'\n'

def programs():
 truth=list(struct.unpack_from('>89I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM));raw,refs=payload(OUT/'recovered.o',NAME);assert not refs
 return [(truth,ENTRY),(list(struct.unpack('>%dI'%(len(raw)//4),raw)),ENTRY)]

def main():
 frozen=OUT/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 before=(frozen/SOURCE).read_text();candidate=proposed(before);installed=(ROOT/SOURCE).read_text()==candidate
 plan=json.loads((OUT/'adoption-plan.json').read_text()) if (OUT/'adoption-plan.json').exists() else {}
 for name,want in record['inputs'].items():assert sha(ROOT/name)==(plan.get(name,want) if installed else want),name
 base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,candidate,'recovered')
 assert d1==d2=='' and same_functions(base,obj,(NAME,))==3 and normalized_pools(base)==normalized_pools(obj)
 truth,raw=[p[0] for p in programs()];assert len(raw)==89 and raw[0]==0x27bdffb8 and raw[1]==0xf7b40008
 assert truth==raw
 report=dict(body_words=89,slot_words=92,frame=72,fp_pair_save='F20/F21 at SP+8',bindings=0,neighbors=3,real_word_differences=0,raw_sha256=hashlib.sha256(payload(obj,NAME)[0]).hexdigest(),installed=installed,c_match_credit=int(installed))
 for name,want in record['inputs'].items():assert sha(ROOT/name)==(plan.get(name,want) if installed else want),name
 (OUT/'recovery-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
