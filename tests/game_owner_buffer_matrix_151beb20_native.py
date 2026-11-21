from pathlib import Path
import json
import subprocess
import sys

from tools.experiments import game_owner_buffer_matrix_151beb20_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run():
    owner=(out/'qualified-source/selected-owner.c').read_text()
    source=body(owner,'func_151BEB20')
    declarations=owner.split('/* Non-matching placeholders',1)[0].replace('#include <ultra64.h>\n','',1)
    controls={
        'translation-source':('= owner->x','= owner->z'),
        'wrong-product':('[0][0] *= scale','[0][0] += scale'),
        'missing-product':('    owner->matrices[D_800BE9C0][2][2] *= scale;',''),
        'wrong-return':('return 1;','return 0;'),
        'old-scale':('    f32 scale;','    f32 scale = D_800AA8E0;'),
        'old-page':('    f32 scale;','    f32 scale;\n    u8 page = D_800BE9C0;')
    }
    functions=[source.replace('func_151BEB20(','selected(',1)]
    checks=[]
    for i,(label,(before,after)) in enumerate(controls.items()):
        assert before in source,label
        changed=source.replace(before,after,1)
        if label=='old-scale':
            changed=changed.replace('    scale = D_800AA8E0;\n','')
        if label=='old-page':
            changed=changed.replace('owner->matrices[D_800BE9C0]','owner->matrices[page]')
        name='bad_'+str(i)
        functions.append(changed.replace('func_151BEB20(',name+'(',1))
        checks.append('if (!check('+name+')) return '+str(20+i)+';')
    text=Path(__file__).with_name('game_owner_buffer_matrix_151beb20_native.c.in').read_text().replace('@@DECL@@',declarations).replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CONTROLS@@','\n    '.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True)
    file=where/'cases.c';file.write_text(text)
    reports=[]
    for optimization in ('-O0','-O2','-O3'):
        executable=where/('selected'+optimization)
        result=subprocess.run(native_command(optimization)+['-fstrict-aliasing','-o',str(executable),str(file)],cwd=root,capture_output=True,text=True)
        assert result.returncode==0 and not result.stdout and not result.stderr,result.stdout+result.stderr
        result=subprocess.run([str(executable)],cwd=root,capture_output=True,text=True)
        assert result.returncode==0 and not result.stdout and not result.stderr,(optimization,result.returncode,result.stdout,result.stderr)
        reports.append(dict(optimization=optimization,cases=768,effective_controls=list(controls),strict_aliasing=True,UBSan=True))
    report=dict(valid=reports,SDK_offset_and_extent_assertions=True,valid_buffer_indices=[0,1],helper_contract='seeded finite matrix and mutable selector, scale and owner fields',source_installed=packet.installed(),matching_credit=0)
    (out/'native-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return report

if __name__=='__main__':
    run()
