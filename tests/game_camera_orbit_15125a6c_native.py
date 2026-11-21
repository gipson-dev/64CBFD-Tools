from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_camera_orbit_15125a6c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_orbit_15125a6c_guest as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    source=body((out/'qualified-source/selected-owner.c').read_text(),'func_15125A6C')
    view=packet.MANIFEST['setup_view']
    queue=body((out/'additional-baseline/conker/src/game/generated_15AA10.c').read_text(),'func_1512D560').replace('func_1512D560(','queue_append(',1)
    controls={'mode':('state == 0x2A','state == 0x2B'),'exact-mode-word':('camera->unk2C != 0x40000','!(camera->unk2C & 0x40000)'),
     'byte-width':('D_800C365C = 0;','D_800C365C = 0; D_800C3600.pad5D[0] = 0;'),
     'phase':('heading - 90.0f','heading - 80.0f'),'x-scale':('138.0f * trig','137.0f * trig'),
     'release-order':('func_1512D560((u8 *)camera, 6, 0);\n        camera->unk7E4 = 0;','camera->unk7E4 = 0;\n        func_1512D560((u8 *)camera, 6, 0);')}
    functions=[source.replace('func_15125A6C(','selected(',1)];checks=[]
    for i,(name,(old,new))in enumerate(controls.items()):
     assert old in source,name;identifier='bad_'+str(i);functions.append(source.replace('func_15125A6C(',identifier+'(',1).replace(old,new,1));checks.append('if(!check('+identifier+'))return '+str(20+i)+';')
    fields=[n for n in guest.Case.__dataclass_fields__ if n!='phase'];cases=[]
    for c in guest.corpus():
     if c.alias:continue
     cases.append('{'+','.join('0x%Xu'%(getattr(c,n)&0xFFFFFFFF)for n in fields)+'}')
    text=Path(__file__).with_name('game_camera_orbit_15125a6c_native.c.in').read_text().replace('@@VIEW@@',view).replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@QUEUE_BODY@@',queue).replace('@@CASES@@',',\n'.join(cases)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt);command=native_command(opt)+['-fstrict-aliasing','-fno-builtin-sinf','-fno-builtin-cosf','-Wno-unused-variable','-o',str(exe),str(file)]
     q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':len(cases),'controls':len(controls),'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'actual_SDK_camera_and_actor_types':True,'inline_setup_typed_member_aliases':True,'real_recovered_queue_body':True,
     'limits':'Finite pure deterministic trig ABI providers, not libm accuracy/FCSR acceptance; separate typed objects; no native-frame claim. Unused IDO frame locals have a targeted native-only warning suppression.',
     'source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
