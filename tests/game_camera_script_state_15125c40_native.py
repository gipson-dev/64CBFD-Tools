from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_camera_script_state_15125c40_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    source=body((out/'variant-s32-first/selected-owner.c').read_text(),'func_15125C40')
    controls={'category':('== 0x42','== 0x43'),'state':('state == 3','state == 4'),
     'countdown':('camera->unk7CC--;','camera->unk7CC = camera->unk7CC;'),
     'activation-flag':('camera->unk5F0 |= 2','camera->unk5F0 |= 4'),
     'linked-flag':('*camera->unk36C |= 0x10','*camera->unk36C |= 0x20'),
     'cleanup-command':('0x0F','0x0E')}
    functions=[source.replace('func_15125C40(','selected(',1)];checks=[]
    for i,(name,(old,new))in enumerate(controls.items()):
     assert old in source,name
     identifier='bad_'+str(i);functions.append(source.replace('func_15125C40(',identifier+'(',1).replace(old,new,1))
     checks.append('if(!check('+identifier+'))return '+str(20+i)+';')
    text=Path(__file__).with_name('game_camera_script_state_15125c40_native.c.in').read_text().replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CONTROLS@@','\n'.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt);command=native_command(opt)+['-fstrict-aliasing','-o',str(exe),str(file)]
     q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':76800,'controls':6,'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'actual_SDK_structures':True,'complete_function_body':True,'native_private_frame_claim':False,
     'limits':'Defined non-overlapping SDK objects; signed decrement excludes INT_MIN, float-to-int inputs are finite and representable.',
     'source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
