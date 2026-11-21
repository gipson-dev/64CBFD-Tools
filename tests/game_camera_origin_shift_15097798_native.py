from pathlib import Path
import hashlib,json,re,subprocess,sys
from tools.experiments import game_camera_origin_shift_15097798_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_origin_shift_15097798_guest as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
    source=body((out/'qualified-source/selected-owner.c').read_text(),'func_15097798')
    owner=(out/'qualified-source/selected-owner.c').read_text();view=re.search(r'typedef struct \{.*?\} CameraShiftC3E20;',owner,re.S).group(0)
    helper_path='conker/src/game_75FC0.c';expected=json.loads((out/'baseline/fingerprints.json').read_text())['inputs'][helper_path]
    assert hashlib.sha256((root/helper_path).read_bytes()).hexdigest()==expected
    helper_source=(root/helper_path).read_text();helpers='\n'.join(body(helper_source,n).replace(n+'(',alias+'(',1)for n,alias in(('func_15048F90','delta_real'),('func_1504917C','normalize_real')))
    controls={
     'inverted-gate':('D_800D2DB4 != 0','D_800D2DB4 == 0'),
     'unsigned-scale':('D_800D2E30[view]','(u32)D_800D2E30[view]'),
     'x-scale':('direction.unk0 * -2.5f','direction.unk0 * -2.0f'),
     'y-scale':('direction.unk4 * -2.0f','direction.unk4 * -2.5f'),
     'omitted-normalization':('        func_1504917C(&direction, &direction);',''),
     'wrong-target-output':('camera->target.unk0 +=','camera->origin.unk0 +='),
     'cached-scale':('D_800D2E30[view]','cachedScale'),
     'refreshed-camera':('        func_1504917C(&direction, &direction);','        func_1504917C(&direction, &direction);\n        camera = &D_800DBFF0[view];')}
    functions=[source.replace('func_15097798(','selected(',1)];checks=[]
    for i,(name,(a,b))in enumerate(controls.items()):
     assert a in source,name;changed=source.replace(a,b)
     if name=='cached-scale':changed=changed.replace('    struct17 direction;','    struct17 direction;\n    s32 cachedScale = D_800D2E30[view];')
     identifier='bad_'+str(i);functions.append(changed.replace('func_15097798(',identifier+'(',1));checks.append('if(!check('+identifier+'))return '+str(20+i)+';')
    rows=[];seen=set()
    for c in guest.corpus():
     if c.alias or not 0<=c.view<4:continue
     row=(c.gate&0xFFFFFFFF,c.view,c.scale&0xFFFFFFFF,c.pattern,c.mutation)
     if row in seen:continue
     seen.add(row);rows.append('{'+','.join('0x%Xu'%v for v in row)+'}')
    text=Path(__file__).with_name('game_camera_origin_shift_15097798_native.c.in').read_text().replace('@@VIEW@@',view).replace('@@HELPERS@@',helpers).replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CASES@@',',\n'.join(rows)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
    where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
    for opt in('-O0','-O2','-O3'):
     exe=where/('selected'+opt);command=native_command(opt)+['-fstrict-aliasing','-o',str(exe),str(file)]
     q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
     q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
     reports.append({'optimization':opt,'cases':len(rows),'effective_controls':list(controls),'strict_aliasing':True,'UBSan':True})
    r={'valid':reports,'SDK_offset_and_extent_assertions':True,'actual_delta_and_normalizer_C':True,'length_primitive':'Rounded single products/sums and native SSE sqrt; original handwritten length code is connected separately in guest checks.',
     'limits':'Actual SDK/view union extent and six offsets; valid view arrays and separate signed scale storage. Helper wrappers add explicit bounded global mutations after real recovered helper C. Guest-only overlap/extreme-view probes, FCSR exceptions, hardware and gameplay are outside native acceptance.',
     'source_installed':packet.installed(),'matching_credit':0}
    (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
