from pathlib import Path
import hashlib,json,re,subprocess,sys
from tools.experiments import game_camera_query_1509759c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_query_1509759c_guest as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    owner=(out/'qualified-source/selected-owner.c').read_text();source=body(owner,'func_1509759C')
    types={m[1]:m[0]for m in re.finditer(r'typedef struct\s*\{[^{}]*\}\s*(\w+);',owner,re.S)}
    typedefs='\n'.join(types[n]for n in('CameraShiftC3E20','CameraQueryPoint'))
    helper_path='conker/src/game_75FC0.c';expected=json.loads((out/'baseline/fingerprints.json').read_text())['inputs'][helper_path]
    assert hashlib.sha256((root/helper_path).read_bytes()).hexdigest()==expected
    helper=body((root/helper_path).read_text(),'func_15048F90').replace('func_15048F90(','delta_real(',1)
    controls={
     'wrong-view-limit':('D_80082FA0 < view','D_80082FA0 <= view'),
     'wrong-command-owner':('case 31:','case 28:'),
     'wrong-fixed-scale':('65536.0f','32768.0f'),
     'wrong-parameter-word':('parameters[2]','parameters[1]'),
     'wrong-point-axis':('camera->target.unk8 - point->z','camera->target.unk8 - point->x'),
     'missing-horizontal-clear':('            offset.unk4 = 0.0f;',''),
     'reversed-dot-test':('0.0f <= func_150AD900','0.0f >= func_150AD900'),
     'refreshed-camera':('actor = func_1505EEF4(parameters[2] & 0xFFF);','actor = func_1505EEF4(parameters[2] & 0xFFF);\n            camera = &D_800DBFF0[view];')}
    # The parameter-word control is restricted to the lookup call so all native
    # array accesses remain defined while the captured lookup key changes.
    controls['wrong-parameter-word']=('func_1505EEF4(parameters[2] & 0xFFF)','func_1505EEF4(parameters[1] & 0xFFF)')
    functions=[source.replace('func_1509759C(','selected(',1)];checks=[]
    for i,(label,(a,b))in enumerate(controls.items()):
     assert a in source,label;functions.append(source.replace(a,b).replace('func_1509759C(','bad_'+str(i)+'(',1));checks.append('if(check(bad_'+str(i)+'))return '+str(20+i)+';')
    rows=[];seen=set()
    for c in guest.corpus():
     if c.view not in(0,3)or c.key not in(0,1)or c.pattern>=5 or(c.command==32 and c.pattern==3):continue
     row=tuple(guest.u32(v)for v in(c.view,c.limit,c.command,c.key,c.pattern,c.outcome,c.mutation))
     if row in seen:continue
     seen.add(row);rows.append('{'+','.join('0x%Xu'%v for v in row)+'}')
    text=Path(__file__).with_name('game_camera_query_1509759c_native.c.in').read_text().replace('@@TYPES@@',typedefs).replace('@@HELPER@@',helper).replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CASES@@',',\n'.join(rows)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt);command=native_command(opt)+['-fno-builtin','-fstrict-aliasing','-o',str(exe),str(file)]
     q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':len(rows),'effective_controls':list(controls),'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'SDK_offset_and_extent_assertions':True,'actual_delta_C':True,'limits':'Lookup and sin/cos are explicit effectful contracts with argument capture. Real SDK32 camera/actor storage and valid signed point arrays are used. Default rounded multiply/add and SSE square root represent the primitive; actual delta/dot instructions are connected separately in guest checks. Invalid indices and out-of-range/NaN float casts are guest-only; FCSR/hardware/gameplay are outside scope.','source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
