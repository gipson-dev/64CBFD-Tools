"""Reuse the established resolver contracts with candidate C, native32 and UBSan."""
import hashlib,json,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tools.experiments.game_resource_resolver_1510d0ec_match import ROOT,BUILD,NEW_SOURCE,HEADERS
root=ROOT;out=root/BUILD
from tools.tests import test_game_texture_resource_setup as fixture
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_remaining_donor_candidates import body
source=NEW_SOURCE;selected=body(source,'func_1510D0EC')
SCENARIOS=('test_resolver_invalid_ids_update_range_without_table_or_output_access','test_zero_size_overwrites_cache_but_still_publishes_extent_and_activity','test_cached_signed_priority_truncation_and_saturating_activity','test_miss_alignment_both_allocation_flags_and_no_decoder_result_gate','test_allocation_failures_leave_extent_cache_state_and_activity_untouched','test_fresh_table_scratch_and_output_reads_across_callbacks')
def controls():
 rows={
 'exclude_last_ID':selected.replace('id >= 0x1E52','id >= 0x1E51'),
 'missing_minimum':selected.replace('D_800D9F58 = id;',';'),
 'wrong_empty_state':selected.replace('D_800B0E58[id] = 0x80000000;','D_800B0E58[id] = 0;'),
 'odd_align_up':selected.replace('            source--;','            source++;'),
 'missing_source_skip':selected.replace('compressed + skip,','compressed,'),
 'wrong_alignment':selected.replace('(size + 15) & ~0xF','(size + 7) & ~7'),
 'wrong_compressed_flags':selected.replace('~0xF, 1, 2, 1, 2','~0xF, 1, 1, 1, 2'),
 'stale_expanded_extent':selected.replace('func_10003C6C(D_800B87A0[id],','func_10003C6C(size,'),
 'missing_failure_free':selected.replace('if (expanded == NULL) {\n            func_10004074(compressed);','if (expanded == NULL) {'),
 'uncapped_activity':selected.replace(' && D_800D9F68[id] < 0xFF',''),
 'double_activity':selected.replace('D_800D9F68[id]++;','D_800D9F68[id] += 2;'),
 'wrong_miss_priority':selected.replace('priority = 0x3E;','priority = 0x3D;'),
 }
 line='    address = D_800B0E58[id];\n';rows['early_return_capture']=selected.replace(line,'').replace('    if (extent != NULL) {',line+'    if (extent != NULL) {')
 assert all(text!=selected for text in rows.values());return rows
def main():
 snippets=[]
 class Capture(fixture.GameTextureResourceSetupTests):
  def run_host(self,text):snippets.append(text)
 with patch.object(fixture,'__file__',str(root/'tools/tests/test_game_texture_resource_setup.py')):Capture.setUpClass()
 try:
  for name in SCENARIOS:getattr(Capture(name),name)()
  assert len(snippets)==6;original=Capture.bodies['func_1510D0EC'];assert Capture.fixture.count(original)==1
  program=Capture.fixture.replace(original,selected)
 finally:Capture.doClassCleanups()
 program+='\n_Static_assert(sizeof(void*)==4,"native32");\ntypedef u32(*Loader)(s32,s32*,s32,s32);static Loader test_loader;\n'
 for name,text in controls().items():program+=text.replace('func_1510D0EC(','negative_'+name+'(',1)+'\n'
 for i,text in enumerate(snippets):program+='static int scenario_'+str(i)+'(void){\n'+text.replace('func_1510D0EC(','test_loader(')+'\nreturn 0;}\n'
 program+='static int check(Loader fn){test_loader=fn;\n'+''.join('if(scenario_'+str(i)+'())return '+str(i+1)+';\n'for i in range(6))+'return 0;}\nstatic int run(void){if(check(func_1510D0EC))return 10;\n'
 for i,name in enumerate(controls()):program+='if(!check(negative_'+name+'))return '+str(20+i)+';\n'
 program+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=out/'native.c';p.write_text(program);profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fstrict-aliasing','-Wno-unused-function',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(exit=0,contract_scenarios=6,UBSan=True,strict_aliasing=True,effective_controls=len(controls()))
 report=dict(profiles=profiles,reused_contract_code_freshly_executed=True,contract_sha256=hashlib.sha256(Path(fixture.__file__).read_bytes()).hexdigest(),scenarios=list(SCENARIOS),effective_semantic_controls=list(controls()),allocator_DMA_decoder_free_bounded=True,full_hardware_loading_claimed=False)
 (out/'native-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
