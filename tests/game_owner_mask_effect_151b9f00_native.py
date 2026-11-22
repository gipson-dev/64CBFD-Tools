from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_owner_mask_effect_151b9f00_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run():
    owner=(out/'qualified-source/selected-owner.c').read_text()
    selected=body(owner,'func_151B9F00')
    declarations=owner.split('typedef struct {\n    u8 retained00[0x54];',1)[0].replace('#include <ultra64.h>\n','',1)
    controls={
        'wrong-mode-two-mask':('mask = 253','mask = 252'),
        'wrong-mode-four-mask':('251 : 247','250 : 246'),
        'wrong-player-limit':('index < 2','index < 1'),
        'wrong-resource':('field34 = 429','field34 = 428'),
        'short-copy':('&scratch, 8','&scratch, 4'),
        'wrong-return':('return created;','return NULL;')
    }
    functions=[selected.replace('func_151B9F00(','selected(',1)]
    checks=[]
    for index,(label,(old,new))in enumerate(controls.items()):
        assert old in selected,label
        name='bad_'+str(index)
        functions.append(selected.replace(old,new).replace('func_151B9F00(',name+'(',1))
        checks.append('if (!check('+name+')) return '+str(20+index)+';')
    program=Path(__file__).with_name('game_owner_mask_effect_151b9f00_native.c.in').read_text().replace('@@DECL@@',declarations).replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CONTROLS@@','\n    '.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True)
    path=where/'cases.c';path.write_text(program)
    reports=[]
    for optimization in ('-O0','-O2','-O3'):
        executable=where/('selected'+optimization)
        result=subprocess.run(native_command(optimization)+['-fstrict-aliasing','-o',str(executable),str(path)],cwd=root,capture_output=True,text=True)
        assert result.returncode==0 and not result.stdout and not result.stderr,result.stdout+result.stderr
        result=subprocess.run([str(executable)],cwd=root,capture_output=True,text=True)
        assert result.returncode==0 and not result.stdout and not result.stderr,(optimization,result.returncode,result.stdout,result.stderr)
        reports.append(dict(optimization=optimization,cases=3840,effective_controls=list(controls),strict_aliasing=True,UBSan=True))
    report=dict(valid=reports,SDK_offsets_and_extents=True,valid_owner_indices=[0,1,2,3],padding_scope='Descriptor fields and copied pointer/identity bytes are checked. Parent padding bytes retain their C object-representation scope.',helper_scope='Five-argument factory, dynamic tail offset and byte-copy contracts',source_installed=packet.installed(),matching_credit=0)
    (out/'native-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return report
if __name__=='__main__':run()
