from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_owner_ground_effect_15191be0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def run():
 owner=(out/'qualified-source/selected-owner.c').read_text();source=body(owner,'func_15191BE0')
 decl=owner.split('void func_15131C84',1)[0].replace('#include <ultra64.h>\n','',1)
 controls={'identity':('owner[0x3B]','owner[0x3A]'),'channel':('channel << 6','channel << 5'),'lifetime':('lifetime == -1','lifetime < 0'),'kind':('-1, 29, -1','-1, 28, -1'),'surface-offset':('&packet.surface','(HeightResult71820 *)&packet.value48'),'copy-short':('memcpy(created + 0x28, &packet, sizeof(packet))','memcpy(created + 0x28, &packet, 100)'),'wrong-return':('return created;','return NULL;')}
 # A wrong surface pointer would overrun the real object: use a safe field error instead.
 controls.pop('surface-offset');controls['final-byte']=('packet.value64 = value64','packet.value64 = value55')
 functions=[source.replace('func_15191BE0(','selected(',1)];checks=[]
 for i,(label,(old,new))in enumerate(controls.items()):
  assert old in source,label;name='bad_'+str(i);functions.append(source.replace(old,new).replace('func_15191BE0(',name+'(',1));checks.append('if(!check('+name+'))return '+str(20+i)+';')
 text=Path(__file__).with_name('game_owner_ground_effect_15191be0_native.c.in').read_text().replace('@@DECL@@',decl).replace('@@FUNCTIONS@@','\n'.join(functions)).replace('@@CONTROLS@@',''.join(checks)).replace('@@START@@',START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
 # These support functions intentionally use byte-wise object representations.
 text=text.replace('static int equal(const void*a,const void*b,u32 n){for(u32 i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}','')
 where=out/'native';where.mkdir(exist_ok=True);file=where/'cases.c';file.write_text(text);reports=[]
 for opt in ('-O0','-O2','-O3'):
  exe=where/('selected'+opt);q=subprocess.run(native_command(opt)+['-fstrict-aliasing','-o',str(exe),str(file)],cwd=root,capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,q.stdout,q.stderr)
  reports.append({'optimization':opt,'cases':12288,'effective_controls':list(controls),'strict_aliasing':True,'UBSan':True})
 r={'valid':reports,'SDK_offset_and_extent_assertions':True,'limits':'SDK32 valid owner/result objects, exact factory declaration and surface output extent. Compare all defined packet bytes; parent C padding is deliberately excluded. Helpers use bounded side-effect contracts; no hardware/gameplay claim.','source_installed':packet.installed(),'matching_credit':0}
 (out/'native-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':run()
