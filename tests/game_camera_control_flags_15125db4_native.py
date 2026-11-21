from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_camera_control_flags_15125db4_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_control_flags_15125db4_guest as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    source=body((out/'source-screen/selected-owner.c').read_text(),'func_15125DB4')
    view=packet.MANIFEST['timer_view']
    controls={'global-busy':('D_80084480 != 0','D_80084480 == 0'),'event':('0x25, 0x13, 480','0x24, 0x13, 480'),
     'linked-mask':('*camera->unk36C &= ~0x0C','*camera->unk36C &= ~0x1C'),
     'actor-state':('[0x1B3] != 0','[0x1B2] != 0'),
     'timer-direction':('timer -= D_800BE9E4','timer += D_800BE9E4'),
     'timer-clamp':('->timer <= 0','->timer < -1')}
    functions=[source.replace('func_15125DB4(','selected(',1)];checks=[]
    for i,(name,(old,new))in enumerate(controls.items()):
     assert old in source,name;identifier='bad_'+str(i)
     functions.append(source.replace('func_15125DB4(',identifier+'(',1).replace(old,new,1));checks.append('if(!check('+identifier+'))return '+str(20+i)+';')
    fields=[n for n in guest.Case.__dataclass_fields__ if n!='phase'];cases=[]
    for c in guest.corpus():
     if c.alias not in(0,1)or not 0<=c.index<8:continue
     if not -(2**31)<=c.timer-c.ticks<2**31:continue
     if not -(2**31)<=c.timer+c.ticks<2**31:continue
     cases.append('{'+','.join('((s32)0x%Xu)'%(getattr(c,n)&0xFFFFFFFF)for n in fields)+'}')
    text=Path(__file__).with_name('game_camera_control_flags_15125db4_native.c.in').read_text().replace('@@VIEW@@',view).replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CASES@@',',\n'.join(cases)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt)
     q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-o',str(exe),str(file)],cwd=root,capture_output=True,text=True)
     assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':len(cases),'controls':len(controls),'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'actual_SDK_structures':True,'GCC_may_alias_timer_view':True,
     'limits':'Defined SDK32 objects and two legal linked-u16 arrangements; valid table indices and no promoted signed arithmetic overflow. The narrow timer follows SDK two-complement narrowing.',
     'source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
