from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_timed_effect_update_15188b74_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_timed_effect_update_15188b74_guest as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    source=body((out/'qualified-source/selected-owner.c').read_text(),'func_15188B74')
    controls={
     'fade-in-rate':('opacity += D_800BE9E4 * 16','opacity += D_800BE9E4 * 8'),
     'fade-out-rate':('opacity = opacity - D_800BE9E4 * 8','opacity = opacity - D_800BE9E4 * 4'),
     'next-after-callback':('            next = node->next;',''),
     'cleanup-table':('D_8008D588[node->active](node)','D_8008D580[node->active](node)'),
     'skip-timer-clamp':('if (node->timer < 0)','if (0)'),
     'zero-opacity-predecessor':('            node = next;','            if (node->timer == 0 && node->opacity == 0) previous = node;\n            node = next;'),
     'cached-kind':('D_8008D588[node->active](node)','D_8008D588[0](node)')}
    functions=[source.replace('func_15188B74(','selected(',1)];checks=[]
    for i,(name,(a,b))in enumerate(controls.items()):
     assert a in source,name
     changed=source.replace(a,b,1)
     if name=='next-after-callback':changed=changed.replace('D_8008D580[node->active](node);','D_8008D580[node->active](node);\n            next = node->next;',1)
     identifier='bad_'+str(i);functions.append(changed.replace('func_15188B74(',identifier+'(',1));checks.append('if(!check('+identifier+'))return '+str(20+i)+';')
    rows=[];seen=set()
    for c in guest.corpus():
     if not -32<=guest.signed(c.delta)<=32:continue
     row=(c.timer,c.opacity,c.delta&0xFFFFFFFF,c.list,c.count,c.mutation,c.pattern)
     if row in seen:continue
     seen.add(row);rows.append('{'+str(row[0])+','+','.join('0x%Xu'%v for v in row[1:])+'}')
    text=Path(__file__).with_name('game_timed_effect_update_15188b74_native.c.in').read_text().replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CASES@@',',\n'.join(rows)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt);command=native_command(opt)+['-fstrict-aliasing','-o',str(exe),str(file)]
     q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':len(rows),'effective_controls':list(controls),'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'SDK_offset_and_extent_assertions':True,
     'limits':'Typed adjacent head array and valid nodes under SDK32, defined signed arithmetic tick domain [-32,32]; callbacks/free are recorded side-effect contracts. No native private-frame/hardware/gameplay or full callback claim.',
     'source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
