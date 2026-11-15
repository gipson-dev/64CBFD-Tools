"""Restore the genuine handwritten register-protocol helper, without C credit."""
from pathlib import Path
import hashlib,json,os
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
FUNCTION='func_150A613C'
ENTRY,ROM,BODY_BYTES,SLOT_BYTES=0x150A613C,0xD35EC,212,212
BUILD='conker/build/game-vertex-clip-150a613c-restoration'
SOURCE='conker/src/game/generated_D3040.c'
ASSEMBLY='conker/asm/nonmatchings/generated_D3040/func_150A613C.s'
RAW_SHA256='a377334400eefe1c1ef1ec0e8199667b6b559aa9403f7c286d81b41a5d00aeeb'
ASM_SHA256='12956de8441d5254408d38e46be509c3ccdaa02ec2cd05e7d709f85093578a6f'
PLACEHOLDER='s32 func_150A613C() {\n    return 0;\n}'
RESTORED='''/* Handwritten vertex transform/clip helper: T4 is the signed XYZ vertex;
 * F20..F31 hold the matrix, F16/F17 the projection scales, F18/F19 the
 * depth limits. Returns F13/F14/F15 and T3; updates the caller's S2 mask. */
#pragma GLOBAL_ASM("asm/nonmatchings/generated_D3040/func_150A613C.s")'''
def proposed(source):
 if source.count(PLACEHOLDER)!=1:raise ValueError('Unknown vertex clip source state')
 return source.replace(PLACEHOLDER,RESTORED)
def main():
 root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
 record=json.loads((out/'production-baseline/fingerprints.json').read_text());plan=json.loads((out/'adoption-plan.json').read_text()) if (out/'adoption-plan.json').exists() else {}
 def immutable(installed):
  for name,want in record['inputs'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==(plan.get(name,want) if installed else want),name
 assembly=(root/'conker/asm/D3040.s').read_text();a=assembly.index('glabel '+FUNCTION+'\n');z=assembly.index('endlabel '+FUNCTION,a)+len('endlabel '+FUNCTION)
 assert (root/ASSEMBLY).read_bytes()==(assembly[a:z]+'\n').encode()
 assert hashlib.sha256((root/ASSEMBLY).read_bytes()).hexdigest()==ASM_SHA256
 current=(root/SOURCE).read_text();installed=PLACEHOLDER not in current
 immutable(installed)
 if installed:
  assert RESTORED in current
  frozen=out/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());data=(frozen/SOURCE).read_bytes();assert hashlib.sha256(data).hexdigest()==record['inputs'][SOURCE];before=data.decode();candidate=current
 else:before=current;candidate=proposed(current)
 first,_=compile_owner(root,out,before,'baseline');second,diagnostics=compile_owner(root,out,candidate,'selected');assert not diagnostics
 raw,refs=payload(second,FUNCTION);assert raw==(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+BODY_BYTES] and refs=={} and hashlib.sha256(raw).hexdigest()==RAW_SHA256
 assert same_functions(first,second,(FUNCTION,))==16 and normalized_pools(first)==normalized_pools(second)
 immutable(installed)
 report=dict(body_words=53,slot_words=53,alignment_words=0,neighbors=16,guards=0,raw_sha256=RAW_SHA256,assembly_sha256=ASM_SHA256,installed=installed,c_match_credit=0)
 (out/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
