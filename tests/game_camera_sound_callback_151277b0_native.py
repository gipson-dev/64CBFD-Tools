from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_camera_sound_callback_151277b0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_sound_callback_151277b0_guest as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    selected=(out/'qualified-source/selected-owner.c').read_text();function=body(selected,'func_151277B0')
    view=packet.MANIFEST['callback_view']
    controls={'actor-state':('->state == 2','->state == 3'),'counter-edge':('count < 10','count < 9'),
     'delta-edge':('previous - current > 100','previous - current >= 100'),
     'clear-handle':('slot->handle = 0;','slot->handle = 1;'),
     'flag-mask':('slot->flags &= ~0x80;','slot->flags &= ~0x40;'),
     'coordinate':('->x_position','->y_position'),'initial-id':('*state == 0x622','*state == 0x621')}
    functions=[function.replace('func_151277B0(','selected(',1)];checks=[]
    for i,(name,(old,new))in enumerate(controls.items()):
     assert old in function,name;identifier='bad_'+str(i)
     functions.append(function.replace('func_151277B0(',identifier+'(',1).replace(old,new,1));checks.append('if(!check('+identifier+'))return '+str(20+i)+';')
    names=list(guest.Case.__dataclass_fields__);cases=[]
    for c in guest.corpus():
     if any(not -32768<=guest.floating(v)<32768 for v in(c.x,c.y,c.z)):continue
     cases.append('{'+','.join('0x%Xu'%(getattr(c,n)&0xFFFFFFFF)for n in names)+'}')
    text=Path(__file__).with_name('game_camera_sound_callback_151277b0_native.c.in').read_text().replace('@@VIEW@@',view).replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CASES@@',',\n'.join(cases)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt);cmd=native_command(opt)+['-fstrict-aliasing','-o',str(exe),str(file)]
     q=subprocess.run(cmd,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':len(cases),'effective_source_controls':len(controls),'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'SDK_camera_and_primary_actor':True,'typed_private_sound_record_and_secondary_scale':True,
     'limits':'Separate typed objects; state may alias sound ID, handle, or coordinate halfwords. Float-to-short inputs stay representable. Guest-only out-of-range narrowing and private frame states are separate evidence.',
     'source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
