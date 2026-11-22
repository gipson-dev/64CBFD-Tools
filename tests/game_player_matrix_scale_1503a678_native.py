from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_player_matrix_scale_1503a678_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run():
    selected=body((out/'qualified-source/selected-owner.c').read_text(),'func_1503A678')
    controls={'wrong-type-gate':('actor[4] == 0x22','actor[4] == 0x21'),'wrong-factor':('0.015625f','0.03125f'),'missing-reciprocal':('reciprocal = 1.0f / factor','reciprocal = factor'),'wrong-unit-axis':('scale[1] = 1.0f','scale[1] = 2.0f'),'lost-translation':('matrix[3][0] = translation[0]','matrix[3][0] = 0.0f'),'stale-phase':('D_800C3FFA++;','D_800C3FFA = 1;')}
    functions=[selected.replace('func_1503A678(','selected(',1)];checks=[]
    for index,(label,(old,new))in enumerate(controls.items()):
        assert old in selected,label;name='bad_'+str(index)
        functions.append(selected.replace(old,new).replace('func_1503A678(',name+'(',1));checks.append('if (!check('+name+')) return '+str(20+index)+';')
    program=Path(__file__).with_name('game_player_matrix_scale_1503a678_native.c.in').read_text().replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CONTROLS@@','\n    '.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);path=where/'cases.c';path.write_text(program);reports=[]
    for optimization in('-O0','-O2','-O3'):
        executable=where/('selected'+optimization)
        q=subprocess.run(native_command(optimization)+['-fstrict-aliasing','-o',str(executable),str(path)],cwd=root,capture_output=True,text=True)
        assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
        q=subprocess.run([str(executable)],cwd=root,capture_output=True,text=True)
        assert q.returncode==0 and not q.stdout and not q.stderr,(optimization,q.returncode,q.stdout,q.stderr)
        reports.append(dict(optimization=optimization,cases=2496,effective_controls=list(controls),strict_aliasing=True,UBSan=True))
    report=dict(valid=reports,SDK_offsets_and_extents=True,valid_actor_indices=[0,1,2,3],helper_scope='Bounded matrix/byte-copy services and mutations. Original MIPS matrix helpers execute in the separate guest group.',source_installed=packet.installed(),matching_credit=0)
    (out/'native-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
if __name__=='__main__':run()
