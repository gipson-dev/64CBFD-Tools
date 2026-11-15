"""Reuse the exhaustive signed-selector model with the new defined C body."""
import ast,json,subprocess
from tools.experiments import game_selector_mask_1515942c_match as s
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
    old=s.ROOT/'tools/tests/game_selector_mask_1515942c_native.py'
    tree=ast.parse(old.read_text());values={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in('prefix','harness')}
    source=values['prefix']+body((s.OUT/'proposed-owner.c').read_text(),s.NAME)+values['harness']+START
    path=s.OUT/'native.c';path.write_text(source);profiles=[]
    for opt in ('-O0','-O2','-O3'):
        for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
            exe=s.OUT/('native'+opt+alias)
            p=subprocess.run(native_command(opt)+['-mstackrealign',alias,'-o',str(exe),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
            q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr)
            profiles.append(opt+alias)
    # The same exhaustive harness must reject a semantically narrower mask.
    bad=s.OUT/'native-control.c';assert source.count('((fourth + 9) & 31)')==1
    bad.write_text(source.replace('((fourth + 9) & 31)','((fourth + 9) & 15)'))
    for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
        exe=s.OUT/('negative'+alias);p=subprocess.run(native_command('-O2')+['-mstackrealign',alias,'-o',str(exe),str(bad)],capture_output=True,text=True);assert p.returncode==0,p.stderr
        assert subprocess.run([str(exe)],capture_output=True).returncode==42
    report=dict(cases_per_profile=328960,profiles=profiles,UBSan=True,effective_controls=2)
    (s.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
