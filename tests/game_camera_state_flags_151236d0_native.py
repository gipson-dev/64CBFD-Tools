from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_camera_state_flags_151236d0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_state_flags_151236d0_guest as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    source=body((out/'qualified-source/selected-owner.c').read_text(),'func_151236D0')
    controls={'old-snapshot':('oldHeightFlag = camera->unk5F0 & 1','oldHeightFlag = camera->unk5F0 & 4'),
     'ordered-height':('camera->unk2FC <=','camera->unk2FC <'),
     'exact-mode':('camera->unk2C != 0x100','!(camera->unk2C & 0x100)'),
     'secondary-state':('[0x4E] == 2','[0x4E] == 3'),
     'release-order':('func_1515BA48(camera->unk23D);\n            *(CameraFlagFloat14FF90 *)((u8 *)camera + 0x7B0) = 0.0f;', '*(CameraFlagFloat14FF90 *)((u8 *)camera + 0x7B0) = 0.0f;\n            func_1515BA48(camera->unk23D);'),
     'new-active-route':('func_1515BAAC(camera->unk23D)','func_1515BA80(camera->unk23D)'),
     'actor-flag':('camera->unk5F0 |= 0x40','camera->unk5F0 |= 0x20')}
    functions=[source.replace('func_151236D0(','selected(',1)];checks=[]
    for i,(name,(a,b))in enumerate(controls.items()):
     assert a in source,name;identifier='bad_'+str(i);functions.append(source.replace('func_151236D0(',identifier+'(',1).replace(a,b,1));checks.append('if(!check('+identifier+'))return '+str(20+i)+';')
    fields=[n for n in guest.Case.__dataclass_fields__ if n!='phase'];cases=[];seen=set()
    for c in guest.corpus():
     if c.alias>1 or c.mutation&2:continue
     row=tuple(getattr(c,n)&0xFFFFFFFF for n in fields)
     if row in seen:continue
     seen.add(row);cases.append('{'+','.join('0x%Xu'%v for v in row)+'}')
    text=Path(__file__).with_name('game_camera_state_flags_151236d0_native.c.in').read_text().replace('@@VIEWS@@',packet.MANIFEST['scalar_views']).replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CASES@@',',\n'.join(cases)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt);command=native_command(opt)+['-fstrict-aliasing','-o',str(exe),str(file)]
     q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':len(cases),'effective_controls':list(controls),'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'actual_SDK_camera_and_actor_types':True,'SDK_offset_and_extent_assertions':True,'declarative_transition_table_reference':True,
     'limits':'Valid SDK object/primary-secondary aliases; bounded helper effects. Cross-object storage aliases and incoming-home redirects are guest-only. No native frame or full provider/gameplay claim.',
     'source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
