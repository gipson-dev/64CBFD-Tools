"""Fresh native32 reuse of descriptor and connected-dispatcher contracts."""
import json,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tools.experiments.game_positioned_emitter_150e75a0_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import test_game_positioned_emitter_descriptor as fixture
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_remaining_donor_candidates import body
SCENARIOS=('test_initialized_fields_and_submission_arguments','test_return_values_and_narrowing_edges','test_submission_observes_copies_before_mutating_sources','test_descriptor_extent_and_field_offsets','test_dispatcher_positioned_path_uses_actual_helper')
def mutations(selected):
 rows={
 'wrong-kind':selected.replace('descriptor.kind = 4;','descriptor.kind = 3;'),
 'missing-flag-bit':selected.replace('flags | 0x40','flags'),
 'wrong-flag-bit':selected.replace('flags | 0x40','flags | 0x20'),
 'swapped-position':selected.replace('descriptor.position = *(EmitterPosition113D60 *)position;','descriptor.position.x = position[1]; descriptor.position.y = position[0];'),
 'wrong-scale':selected.replace('descriptor.scale[1] = scale;','descriptor.scale[1] = 0.0f;'),
 'swapped-sizes':selected.replace('descriptor.size0 = size0;','descriptor.size0 = size1;'),
 'lost-context':selected.replace('0, slot, context);','0, slot, 0);'),
 'wrong-mode':selected.replace('pair, mode,','pair, mode + 1,'),
 'wrong-slot':selected.replace('0, slot, context);','0, slot ^ 1, context);'),
 'lost-result':selected.replace('    return func_1515548C','    func_1515548C').replace('0, slot, context);','0, slot, context);\n    return 0;'),
 'wrong-tag':selected.replace('descriptor.tag = tag[0];','descriptor.tag = tag[0] ^ 1;'),
 'wrong-duration':selected.replace('descriptor.duration = duration;','descriptor.duration = 255;'),
 }
 assert len(rows)==12 and all(v!=selected for v in rows.values());return rows
def capture():
 snippets=[]
 class Capture(fixture.GamePositionedEmitterDescriptorTests):
  def run_host(self,text):snippets.append((self.fixture,text))
 with patch.object(fixture,'__file__',str(root/'tools/tests/test_game_positioned_emitter_descriptor.py')):Capture.setUpClass()
 try:
  selected=body((out/'final-owner.c').read_text(),'func_150E75A0');Capture.fixture=Capture.fixture.replace(Capture.body,selected);Capture.body=selected
  with patch.object(fixture.dispatch_tests,'__file__',str(root/'tools/tests/test_game_random_dispatch.py')),patch.object(fixture.dispatch_tests.GameRandomDispatchTests,'run_host',Capture.run_host):
   for name in SCENARIOS:getattr(Capture(name),name)()
  assert len(snippets)==5
 finally:Capture.doClassCleanups()
 return selected,snippets
def run_program(program,label,opt):
 p=out/('native-'+label+'.c');exe=p.with_suffix('');p.write_text(program)
 command=native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)];r=subprocess.run(command,cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(label,r.stdout,r.stderr)
 r=subprocess.run([str(exe)],capture_output=True,timeout=10);return r.returncode
def main():
 selected,snippets=capture();profiles={}
 def program(prefix,snippet):return prefix+'\n_Static_assert(sizeof(void*)==4,"native32");\nstatic int run(void){\n'+snippet+'\nreturn 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 for opt in('-O0','-O2','-O3'):
  for i,(prefix,snippet)in enumerate(snippets):assert run_program(program(prefix,snippet),opt+'-'+str(i),opt)==0,(opt,SCENARIOS[i])
  profiles[opt]=dict(scenarios=5,exit=0,UBSan=True)
 prefix,snippet=snippets[0];controls={}
 for name,mutant in mutations(selected).items():
  assert prefix.count(selected)==1
  code=run_program(program(prefix.replace(selected,mutant),snippet),'control-'+name,'-O2');assert code!=0,(name,'Ineffective control');controls[name]=code
 report=dict(profiles=profiles,effective_controls=controls,scenarios=SCENARIOS,strict_aliasing=False,real_dispatcher_with_final_submission_bounded=True)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
