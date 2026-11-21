from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_camera_position_151247c0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_position_151247c0_guest as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    source=body((out/'qualified-source/selected-owner.c').read_text(),'func_151247C0')
    spring_body=body((out/'baseline/conker/src/game/generated_76A60.c').read_text(),'func_150495B0').replace('func_150495B0(','spring_real(',1)
    controls={'activity-width':('u8 active;','u32 active;'),'disabled-gate':('camera->disabled != 0','camera->disabled == 0'),
     'paired-mean':('* 0.5f','* 1.0f'),'lerp-sign':('camera->x = camera->x +','camera->x = camera->x -'),
     'spring-delta':('camera->deltaTime);','1.0f);'),'offset-snap':('camera->offset = camera->targetOffset;','camera->offset = 0;'),
     'output-field':('camera->outputZ = camera->z;','camera->outputY = camera->z;'),'cosine-provider':('cosf(camera->heading','sinf(camera->heading')}
    functions=[source.replace('func_151247C0(','selected(',1)];checks=[]
    for i,(name,(a,b))in enumerate(controls.items()):
     assert a in source,name;identifier='bad_'+str(i);functions.append(source.replace('func_151247C0(',identifier+'(',1).replace(a,b,1));checks.append('if(!check('+identifier+'))return '+str(20+i)+';')
    fields=[n for n in guest.Case.__dataclass_fields__ if n!='phase'];cases=[];seen=set()
    for c in guest.corpus():
     if c.alias>1:continue
     row=tuple(getattr(c,n)&0xFFFFFFFF for n in fields)
     if row in seen:continue
     seen.add(row);cases.append('{'+','.join('0x%Xu'%v for v in row)+'}')
    text=Path(__file__).with_name('game_camera_position_151247c0_native.c.in').read_text().replace('@@VIEW@@',packet.MANIFEST['position_view']).replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@SPRING_BODY@@',spring_body).replace('@@CASES@@',',\n'.join(cases)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt);command=native_command(opt)+['-fstrict-aliasing','-fno-builtin-sinf','-fno-builtin-cosf','-o',str(exe),str(file)]
     q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':len(cases),'effective_controls':list(controls),'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'real_recovered_spring_C':True,'SDK_offset_and_extent_assertions':True,
     'limits':'Typed camera/SDK union and valid primary-partner aliases; finite float32, pure trig and bounded finalization. Camera/actor storage overlaps are guest-only. No native private-frame/FCSR/hardware claim.',
     'source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
