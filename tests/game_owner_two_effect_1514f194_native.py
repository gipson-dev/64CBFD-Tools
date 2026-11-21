from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_owner_two_effect_1514f194_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_owner_two_effect_1514f194_guest as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    source=body((out/'qualified-source/selected-owner.c').read_text(),'func_1514F194')
    controls={
     'first-channel':('func_151D0F60(owner, 1, 255, 1)','func_151D0F60(owner, 3, 255, 1)'),
     'stale-gate':('    struct225 *created;','    struct225 *created;\n    u8 oldGate = D_800BE616;'),
     'second-preset':('&D_800A5964','&D_800A5958'),
     'second-kind':('2, 300, 15','2, 300, 14'),
     'attachment-key':('0x19','0x18'),
     'first-result':('    func_15160A58(owner, 1, &D_800A5958','    created = func_15160A58(owner, 1, &D_800A5958'),
     'null-attachment':('if (created != NULL)','if (1)')}
    functions=[source.replace('func_1514F194(','selected(',1)];checks=[]
    for i,(name,(a,b))in enumerate(controls.items()):
     assert a in source,name;changed=source.replace(a,b,1)
     if name=='stale-gate':changed=changed.replace('if (D_800BE616 == 0)','if (oldGate == 0)')
     if name=='first-result':changed=changed.replace('    created = func_15160A58(owner, 1, &D_800A5964','    func_15160A58(owner, 1, &D_800A5964')
     identifier='bad_'+str(i);functions.append(changed.replace('func_1514F194(',identifier+'(',1));checks.append('if(!check('+identifier+'))return '+str(20+i)+';')
    rows=[];seen=set()
    for c in guest.corpus():
     if c.alias or c.first==2 or c.second==2:continue
     row=(c.gate,c.first,c.second,c.mutation_step,c.mutation_value)
     if row in seen:continue
     seen.add(row);rows.append('{'+','.join(str(v)+'u'for v in row)+'}')
    text=Path(__file__).with_name('game_owner_two_effect_1514f194_native.c.in').read_text().replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CASES@@',',\n'.join(rows)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt);command=native_command(opt)+['-fstrict-aliasing','-o',str(exe),str(file)]
     q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':len(rows),'effective_controls':list(controls),'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'SDK_offset_and_extent_assertions':True,
     'limits':'SDK32 valid owner/result storage and typed 16-argument factory interface; seven helpers use explicit side-effect contracts. Null/overlapping owner probes and private caller-frame state are guest only. No full helper/hardware/gameplay claim.',
     'source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
