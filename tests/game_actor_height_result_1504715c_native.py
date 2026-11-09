"""Preserved twelve native32 actor/result contracts and effective controls."""
import json,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tools.experiments.game_actor_height_result_1504715c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import test_game_actor_height_result_builder as fixture
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_remaining_donor_candidates import body
def mutations(selected):
 rows={
 'wrong-selector':selected.replace('actor->flags & 0x200000','actor->flags & 0x100000'),
 'wrong-coordinate':selected.replace('x = actor->x;','x = actor->z;'),
 'wrong-truncation':selected.replace('y = actor->height;','y = actor->height + 1.0f;'),
 'missing-vertex':selected.replace('result->vertices[8] = z - 1000;','result->vertices[8] = z + 1000;'),
 'wrong-copy-field':selected.replace('= actor->vertices;','= *(HeightCoordinates71820 *)((u8 *)actor + 0x188);'),
 'early-metadata':selected.replace('    result->height = actor->height;','    metadata = actor->metadata;\n    result->height = actor->height;').replace('    metadata = actor->metadata;\n    result->flags','    result->flags'),
 'late-metadata':selected.replace('    metadata = actor->metadata;\n    result->flags = 6;','    result->flags = 6;\n    metadata = actor->metadata;'),
 'wrong-index':selected.replace('        index--;','        index++;'),
 'wrong-stride':selected.replace('(s32)&D_800DBEF4[index]','(s32)((u8 *)D_800DBEF4 + index * 159)'),
 'low-byte-truth':selected.replace('func_15145C90(index) ? 1 : 0','(u8)func_15145C90(index) ? 1 : 0'),
 'stale-post-helper-flags':selected.replace('    u32 metadata;','    u32 metadata;\n    u8 flags;').replace('        accepted =','        flags = result->flags;\n        accepted =').replace('result->flags |= accepted;','result->flags = flags | accepted;'),
 'wrong-zero-state':selected.replace('result->state = 1;','result->state = 0;'),
 'unknown-padding-write':selected.replace('    result->height = actor->height;','    result->pad16 = 0;\n    result->height = actor->height;'),
 }
 assert len(rows)==13 and all(v!=selected for v in rows.values());return rows
def main():
 snippets=[]
 class Capture(fixture.GameActorHeightResultBuilderTests):
  def run_case(self,text):snippets.append(text)
 with patch.object(fixture,'__file__',str(root/'tools/tests/test_game_actor_height_result_builder.py')),patch.object(fixture.highest,'__file__',str(root/'tools/tests/test_game_highest_height_query.py')):Capture.setUpClass()
 try:
  for n in sorted(n for n in dir(Capture)if n.startswith('test_')):getattr(Capture(n),n)()
  assert len(snippets)==12;prefix=Capture.source
 finally:Capture.doClassCleanups()
 selected=body((out/'final-owner.c').read_text(),'func_1504715C');old=body(prefix,'func_1504715C');assert prefix.count(old)==1;program=prefix.replace(old,'')
 program=program.replace('i < sizeof(actor)','(u32)i < sizeof(actor)').replace('i < sizeof(output)','(u32)i < sizeof(output)')
 variants={'candidate':selected,**mutations(selected)}
 for name,part in variants.items():program+=part.replace('func_1504715C(',name.replace('-','_')+'(',1)+'\n'
 program+='typedef void(*Builder)(HeightResult71820 *,HeightActor71820 *);static Builder subject;\n_Static_assert(sizeof(void*)==4,"native32");\n'
 for i,text in enumerate(snippets):program+='static int scenario_'+str(i)+'(void){\n'+text.replace('func_1504715C(','subject(')+'\nreturn 0;}\n'
 program+='static int check(Builder fn){subject=fn;\n'+''.join('if(scenario_'+str(i)+'())return '+str(i+1)+';\n'for i in range(12))+'return 0;}\nstatic int run(void){if(check(candidate))return 1;\n'
 for i,name in enumerate(mutations(selected)):program+='if(!check('+name.replace('-','_')+'))return '+str(i+20)+';\n'
 program+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=out/'native.c';p.write_text(program);profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-Wno-unused-function',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(exit=0,scenarios=12,effective_controls=13,UBSan=True)
 report=dict(profiles=profiles,all_65535_entity_indices=True,all_256_post_helper_flags=True,strict_aliasing=False,partial_stored_structure_overlap_qualified=False)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
