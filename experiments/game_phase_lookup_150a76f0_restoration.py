"""Restore the genuine handwritten register-protocol helper, without C credit."""
from pathlib import Path
import hashlib,json,os
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
FUNCTION='func_150A76F0'
ENTRY,ROM,BODY_BYTES,SLOT_BYTES=0x150A76F0,0xD4BA0,116,128
BUILD='conker/build/game-phase-lookup-150a76f0-restoration'
SOURCE='conker/src/game/generated_D4450.c'
ASSEMBLY='conker/asm/nonmatchings/generated_D4450/func_150A76F0.s'
RAW_SHA256='8094bf0973b11f720425b9a80440e605c6d5c1605a4fbee7440c4662ec6cb112'
ASM_SHA256='d072dfbe8cbea7b38efacfb167dc3426aa6d3b23d9dafd49619bd39ee29b8126'
PLACEHOLDER='s32 func_150A76F0() {\n    return 0;\n}'
RESTORED='''/* Handwritten phase lookup: T4 is the byte phase, S6 the 65-word table,
 * S7/T9 the folding constants 128/256, and F8 the result. Returns through V0;
 * this register convention is deliberately not exposed as a C function. */
#pragma GLOBAL_ASM("asm/nonmatchings/generated_D4450/func_150A76F0.s")'''
def proposed(source):
 if source.count(PLACEHOLDER)!=1:raise ValueError('Unknown phase-lookup source state')
 return source.replace(PLACEHOLDER,RESTORED)
def main():
 root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
 assembly=(root/'conker/asm/D4450.s').read_text();a=assembly.index('glabel '+FUNCTION+'\n');z=assembly.index('endlabel '+FUNCTION,a)+len('endlabel '+FUNCTION)
 assert (root/ASSEMBLY).read_bytes()==(assembly[a:z]+'\n').encode()
 assert hashlib.sha256((root/ASSEMBLY).read_bytes()).hexdigest()==ASM_SHA256
 current=(root/SOURCE).read_text();installed=PLACEHOLDER not in current
 if installed:
  assert RESTORED in current
  frozen=out/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());data=(frozen/SOURCE).read_bytes();assert hashlib.sha256(data).hexdigest()==record['inputs'][SOURCE];before=data.decode();candidate=current
 else:before=current;candidate=proposed(current)
 first,_=compile_owner(root,out,before,'baseline');second,diagnostics=compile_owner(root,out,candidate,'selected');assert not diagnostics
 raw,refs=payload(second,FUNCTION);assert raw==(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+BODY_BYTES] and refs=={} and hashlib.sha256(raw).hexdigest()==RAW_SHA256
 assert same_functions(first,second,(FUNCTION,))==18 and normalized_pools(first)==normalized_pools(second)
 report=dict(body_words=29,slot_words=32,alignment_words=3,neighbors=18,guards=0,raw_sha256=RAW_SHA256,assembly_sha256=ASM_SHA256,installed=installed,c_match_credit=0)
 (out/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
