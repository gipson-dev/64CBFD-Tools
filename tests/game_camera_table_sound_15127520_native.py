from pathlib import Path
import json,math,subprocess,sys
from tools.experiments import game_camera_table_sound_15127520_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_table_sound_15127520_guest as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    selected=(out/'qualified-source/selected-owner.c').read_text();function=body(selected,'func_15127520')
    view=packet.MANIFEST['callback_view']
    controls={'selector':('selector = slot->packedScale >> 31;','selector = (slot->packedScale >> 31) ^ 1;'),
     'history-mask':('slot->packedScale & 0xFFFFFF','slot->packedScale & 0xFFFFFE'),
     'changed-test':('previous != (u32)scaled','previous == (u32)scaled'),
     'reset-id':('*pendingSoundId == sounds[2]','*pendingSoundId == sounds[1]'),
     'clear-handle':('slot->handle = 0;','slot->handle = 1;'),
     'flag-mask':('slot->flags &= ~0x80;\n    return 0;','slot->flags &= ~0x40;\n    return 0;'),
     'emit-volume':('20000, 64','19999, 64')}
    functions=[function.replace('func_15127520(','selected(',1)];checks=[]
    for i,(name,(old,new))in enumerate(controls.items()):
     assert old in function,name;n='bad_'+str(i);functions.append(function.replace('func_15127520(',n+'(',1).replace(old,new,1));checks.append('if(!check('+n+'))return '+str(20+i)+';')
    cases=[]
    for c in guest.corpus():
     if c.fcsr:continue
     value=guest.product(c)
     if c.mode==2 and(not math.isfinite(value)or not 0<=math.trunc(value)<2**32):continue
     if any(not -32768<=guest.floating(v)<32768 for v in(c.x,c.y,c.z)):continue
     cases.append('{'+','.join('0x%Xu'%(getattr(c,n)&0xFFFFFFFF)for n in guest.Case.__dataclass_fields__)+'}')
    text=Path(__file__).with_name('game_camera_table_sound_15127520_native.c.in').read_text().replace('@@VIEW@@',view).replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CASES@@',',\n'.join(cases)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt);cmd=native_command(opt)+['-fstrict-aliasing','-o',str(exe),str(file)]
     q=subprocess.run(cmd,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':len(cases),'effective_source_controls':len(controls),'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'actual_SDK_camera_and_actors':True,'legal_typed_record_and_table_aliases':True,
     'limits':'Float-to-unsigned inputs have representable integral parts; native FCSR and guest fault ordering are separate. Global table and automatic outgoing storage are disjoint.',
     'source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
