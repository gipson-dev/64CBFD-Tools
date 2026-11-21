from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_camera_wobble_151256bc_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_wobble_151256bc_guest as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    source=body((out/'qualified-source/selected-owner.c').read_text(),'func_151256BC')
    rotation=body((out/'baseline/conker/src/game_BC430.c').read_text(),'func_1508EF80')
    rotation=rotation.replace('    f32 dx, dz, radians, providerValue, z, x, cachedValue;', '    f32 dx, dz, radians, providerValue, z, x, cachedValue;\n    record(4,offset(point),offset(pivot),word(degrees),offset(output));')
    prefix='static void record(u32,u32,u32,u32,u32);\nstatic u32 offset(const void*);\nstatic u32 word(f32);\n'
    controls={'gate':('camera->flags & 0x80000','camera->flags & 0x40000'),
     'modulo':('% 3','% 2'),'strict-wrap':('camera->phase > firstScale','camera->phase >= firstScale'),
     'active-smoothing':('* D_800A353C','* D_800A3544'),
     'second-scale':('secondScale = 20.0f','secondScale = 4.0f'),
     'second-pivot':('func_1508EF80(camera->pivot, camera->position,','func_1508EF80(camera->pivot, camera->pivot,'),
     'decay':('camera->phase -= camera->phase * D_800A3544','camera->phase += camera->phase * D_800A3544')}
    functions=[source.replace('func_151256BC(','selected(',1)];checks=[]
    for i,(name,(a,b))in enumerate(controls.items()):
     assert a in source,name;identifier='bad_'+str(i);functions.append(source.replace('func_151256BC(',identifier+'(',1).replace(a,b,1));checks.append('if(!check('+identifier+'))return '+str(20+i)+';')
    fields=[n for n in guest.Case.__dataclass_fields__ if n!='phase'];cases=[]
    for c in guest.corpus():
     if c.phase:continue
     cases.append('{'+','.join('0x%Xu'%(getattr(c,n)&0xFFFFFFFF)for n in fields)+'}')
    text=Path(__file__).with_name('game_camera_wobble_151256bc_native.c.in').read_text().replace('@@VIEW@@',packet.MANIFEST['wobble_view']).replace('@@FUNCTIONS@@',prefix+'\n'.join(functions)).replace('@@ROTATE_BODY@@',rotation).replace('@@CASES@@',',\n'.join(cases)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt);command=native_command(opt)+['-fstrict-aliasing','-fno-builtin-sinf','-fno-builtin-cosf','-o',str(exe),str(file)]
     q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':len(cases),'effective_controls':list(controls),'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'real_recovered_rotation_C':True,'SDK_offset_and_extent_assertions':True,
     'limits':'Typed camera padding view and float arrays with pure finite trig providers; no native private-frame or hardware/FCSR claim.',
     'source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
