"""Restore the genuine handwritten register-protocol helper, without C credit."""
from pathlib import Path
import hashlib,json,os
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
FUNCTION='func_151F8870'
ENTRY,ROM,BODY_BYTES,SLOT_BYTES=0x151F8870,0x225D20,188,188
BUILD='conker/build/game-huffman-pair-151f8870-restoration'
SOURCE='conker/src/game/generated_225D20.c'
ASSEMBLY='conker/asm/nonmatchings/generated_225D20/func_151F8870.s'
RAW_SHA256='f38a8bb78d87a3fcb4bd760f2e88a317c35201067d8013f6e60f4b14cc1fd2cd'
ASM_SHA256='36fedf62211aaa3f80ec475ca2a03dffad4331711f8d46651e1ea010c9aba6eb'
PLACEHOLDER='s32 func_151F8870() {\n    return 0;\n}'
RESTORED='''/* Handwritten Huffman pair decoder. A0/T0 are the byte/bit cursors,
 * A2 selects the lookup bank, S5 holds the fast tables, and S0 the tree.
 * Returns V0/T1 and advances A0/T0; keep this custom register interface. */
#pragma GLOBAL_ASM("asm/nonmatchings/generated_225D20/func_151F8870.s")'''
def proposed(source):
 if source.count(PLACEHOLDER)!=1:raise ValueError('Unknown Huffman pair source state')
 return source.replace(PLACEHOLDER,RESTORED)
def main():
 root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True)
 assembly=(root/'conker/asm/225D20.s').read_text();a=assembly.index('/* Handwritten function */\nglabel '+FUNCTION+'\n');z=assembly.index('endlabel '+FUNCTION,a)+len('endlabel '+FUNCTION)
 assert (root/ASSEMBLY).read_bytes()==(assembly[a:z]+'\n').encode()
 assert hashlib.sha256((root/ASSEMBLY).read_bytes()).hexdigest()==ASM_SHA256
 current=(root/SOURCE).read_text();installed=PLACEHOLDER not in current
 if installed:
  assert RESTORED in current
  frozen=out/'production-baseline';record=json.loads((frozen/'fingerprints.json').read_text());data=(frozen/SOURCE).read_bytes();assert hashlib.sha256(data).hexdigest()==record['inputs'][SOURCE];before=data.decode();candidate=current
 else:before=current;candidate=proposed(current)
 first,_=compile_owner(root,out,before,'baseline');second,diagnostics=compile_owner(root,out,candidate,'selected');assert not diagnostics
 raw,refs=payload(second,FUNCTION);assert raw==(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+BODY_BYTES] and refs=={} and hashlib.sha256(raw).hexdigest()==RAW_SHA256
 assert same_functions(first,second,(FUNCTION,))==5 and normalized_pools(first)==normalized_pools(second)
 report=dict(body_words=47,slot_words=47,alignment_words=0,neighbors=5,guards=0,raw_sha256=RAW_SHA256,assembly_sha256=ASM_SHA256,installed=installed,c_match_credit=0)
 (out/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
