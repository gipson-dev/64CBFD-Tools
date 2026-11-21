from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_camera_mode_gates_1512317c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_mode_gates_1512317c_guest as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    source=body((out/'qualified-source/selected-owner.c').read_text(),'func_1512317C')
    sealed=(out/'baseline/conker/src/game_14FF90.c').read_text()
    helpers='\n'.join(body(sealed,n).replace(n+'(',alias+'(',1)for n,alias in(('func_15123934','save_real'),('func_151239CC','restore_real')))
    helpers+='\n'+body((out/'baseline/conker/src/game/generated_76A60.c').read_text(),'func_150495B0').replace('func_150495B0(','spring_real(',1)
    controls={'stunned-exclusion':('camera->unk23E != 9','camera->unk23E != 8'),
     'old-flag':('camera->unk5F0 & 0x100','camera->unk5F0 & 0x400'),
     'primary-reload':('(actor = camera->unk3D0)->health','actor->health'),
     'speed-boundary':('> 15.0f','> 16.0f'),
     'input-gate':('(*camera->unk36C & 0x10)','(*camera->unk36C & 0x20)'),
     'save-mode':('func_15123934(camera, 0x100','func_15123934(camera, 0x200'),
     'actor-reset':('camera->unk3D4->unk197 = 0','camera->unk3D4->unk197 = 1'),
     'spring-damping':('4.0f, 9.0f','4.0f, 8.0f'),
     'substate-clear':('camera->unk73C = 0','camera->unk73C = 1')}
    functions=[source.replace('func_1512317C(','selected(',1)];checks=[]
    for i,(name,(a,b))in enumerate(controls.items()):
     assert a in source,name;identifier='bad_'+str(i);functions.append(source.replace('func_1512317C(',identifier+'(',1).replace(a,b,1));checks.append('if(!check('+identifier+'))return '+str(20+i)+';')
    fields=[n for n in guest.Case.__dataclass_fields__ if n!='phase'];cases=[];seen=set()
    for c in guest.corpus():
     if c.alias>3 or (c.value&0x7F800000)==0x7F800000 or (c.speed&0x7F800000)==0x7F800000:continue
     row=tuple(getattr(c,n)&0xFFFFFFFF for n in fields)
     if row in seen:continue
     seen.add(row);cases.append('{'+','.join('0x%Xu'%v for v in row)+'}')
    text=Path(__file__).with_name('game_camera_mode_gates_1512317c_native.c.in').read_text().replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@HELPERS@@',helpers).replace('@@CASES@@',',\n'.join(cases)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt);command=native_command(opt)+['-fstrict-aliasing','-o',str(exe),str(file)]
     q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':len(cases),'effective_controls':list(controls),'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'real_recovered_save_restore_spring_C':True,'SDK_offset_and_extent_assertions':True,
     'limits':'SDK/view union with valid actor and input aliases; query, activation and downstream reset/index contracts are bounded. Finite floats only; no native private-frame/FCSR/hardware or gameplay claim. Cross-object storage overlap is guest-only.',
     'source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
