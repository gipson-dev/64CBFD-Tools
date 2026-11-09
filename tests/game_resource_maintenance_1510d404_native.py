"""Fresh native32 reuse of the nine maintenance contracts, with effective controls."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tools.experiments.game_resource_maintenance_1510d404_candidates import ROOT,BUILD,BODIES,SOURCE
root=ROOT;out=root/BUILD
from tools.tests import test_game_texture_metadata_and_maintenance as fixture
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_remaining_donor_candidates import body
source=(root/SOURCE).read_text()
NATIVE_BODIES=('baseline','counter','equal')
SCENARIOS=('test_maintenance_no_work_counter_and_freeze_gates','test_maintenance_all_signed_byte_states_and_activity_untouched','test_expiry_callbacks_captured_scan_range_fresh_next_state_and_cache_overwrite','test_staged_decode_captured_temporary_and_fresh_state_after_callbacks','test_staged_callbacks_preserve_cache_replacement_without_free_mutation','test_next_staged_entry_reads_scratch_and_cache_fresh_after_callbacks','test_complete_valid_scan_includes_both_endpoints_without_touching_fences','test_maintenance_empty_ranges_and_diagnostic_return_fallthrough','test_actual_metadata_initializer_setup_resolver_release_maintenance_lifecycle')
def controls():
 c=BODIES['counter'];rows={
 'frozen-stops-active-work':c.replace('if (D_800DBDBA == 0) {','if (1) {'),
 'missing-counter-decrement':c.replace('D_800DBDBA--;',';'),
 'unsigned-priority':c.replace('    s8 state;','    s32 state;').replace('state = D_800BC448[i];','state = (u8)D_800BC448[i];'),
 'tightened-diagnostic-limit':c.replace('last >= 0x1E53','last >= 0x1E52'),
 'lost-first-snapshot':c.replace('first = D_800D9F58;','first = 0xFFFF;'),
 'wrong-zero-transition':c.replace('if (D_800BC448[i] == 0) {','if (D_800BC448[i] != 0) {'),
 'missing-cache-sentinel':c.replace('D_800B0E58[i] = 0xFFFFFFFF;',';'),
 'wrong-temporary-free':c.replace('func_10004074((void *)temporary);','func_10004074(entry);'),
 'stale-post-callback-state':c.replace('D_800BC448[i] &= ~0x40;','D_800BC448[i] = state & ~0x40;'),
 'wrong-cleared-bit':c.replace('D_800BC448[i] &= ~0x40;','D_800BC448[i] &= ~0x20;'),
 'missing-maximum-requeue':c.replace('if (i > D_800D9F5C) {','if (0) {'),
 'live-last-loop':c.replace('i <= last','i <= D_800D9F5C'),
 'stale-next-scratch':c.replace('entry, D_8003809C','entry, 0x456789AB'),
 }
 assert all(v!=c for v in rows.values());return rows
def main():
 snippets=[]
 class Capture(fixture.GameTextureMetadataAndMaintenanceTests):
  def run_host(self,text):snippets.append(text)
 with patch.dict(os.environ,CBFD_CONSUMER_ROOT=str(root)):Capture.setUpClass()
 try:
  for name in SCENARIOS:getattr(Capture(name),name)()
  assert len(snippets)==9;program=Capture.fixture
 finally:Capture.doClassCleanups()
 program='typedef unsigned long long u64;typedef long long s64;\n'+program+'\n_Static_assert(sizeof(void*)==4,"native32");\n'
 for label in NATIVE_BODIES:program+=BODIES[label].replace('func_1510D404(',label+'_maintenance(',1)+'\n'
 for label,part in controls().items():program+=part.replace('func_1510D404(','negative_'+label.replace('-','_')+'(',1)+'\n'
 program+='typedef void(*Maintenance)(void);static Maintenance test_maintenance;\n'
 for i,text in enumerate(snippets):program+='static int scenario_'+str(i)+'(void){\n'+text.replace('func_1510D404(','test_maintenance(')+'\nreturn 0;}\n'
 program+='static int check(Maintenance fn){test_maintenance=fn;\n'+''.join('if(scenario_'+str(i)+'())return '+str(i+1)+';\n'for i in range(9))+'return 0;}\nstatic int run(void){\n'
 for i,label in enumerate(NATIVE_BODIES):program+='if(check('+label+'_maintenance))return '+str(i+1)+';\n'
 for i,label in enumerate(controls()):program+='if(!check(negative_'+label.replace('-','_')+'))return '+str(20+i)+';\n'
 program+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=out/'native.c';p.write_text(program);profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fstrict-aliasing','-Wno-unused-function',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(exit=0,scenarios=9,bodies=len(NATIVE_BODIES),effective_controls=len(controls()),UBSan=True,strict_aliasing=True)
 report=dict(profiles=profiles,fixture_sha256=hashlib.sha256(Path(fixture.__file__).read_bytes()).hexdigest(),scenarios=SCENARIOS,full_legacy_suite_claimed=False,hardware_providers_bounded=True,diagnostic_prefix_guest_only=True)
 (out/'native-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
