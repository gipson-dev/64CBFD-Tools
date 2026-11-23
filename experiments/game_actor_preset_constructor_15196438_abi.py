"""Return-chain source repair with zero additional machine-code/match credit."""
from pathlib import Path
import hashlib,json,re,subprocess
from tools.experiments import game_actor_preset_constructor_15196438_match as p
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_texture_registration_15195dd4_objects import assemble
from tools.tests.test_game_projected_packet_draw import native_command
from tools import pad_c_object as pc
r,o=p.ROOT,p.OUT
def main():
 root=o/'ABI-qualified';root.mkdir(exist_ok=True);oldheader=(o/'baseline/conker/include/functions.h').read_text();newheader=p.MANIFEST['selected_sources']['conker/include/functions.h'];rows=[]
 for name in('conker/src/init_EB00.c','conker/src/game/generated_113D60.c','conker/src/game/generated_11C2B0.c','conker/src/game/generated_131620.c','conker/src/game_981E0.c'):
  source=(o/'baseline'/name).read_text();selected=p.MANIFEST['selected_sources'].get(name,source);w=root/Path(name).stem;w.mkdir(exist_ok=True)
  (w/'functions.h').write_text(oldheader);before,bd=compile_owner(r,w,source,'before');(w/'functions.h').write_text(newheader);after,ad=compile_owner(r,w,selected,'candidate');count=same_functions(before,after,());assert normalized_pools(before)==normalized_pools(after)and diagnostic_rows(bd)==diagnostic_rows(ad)
  filename=Path(name).stem;target='conker/build/src/'+('game/'if'/game/'in name else'')+filename+'.c.o';expected=(o/'baseline'/target).read_bytes()
  for label,f in(('before',before),('candidate',after)):
   out=w/(label+'-padded.o');assemble(pc.emit_padded_assembly(f,o/'baseline/conker/retail_layout.us.txt',filename,rodata_symbol='D_800A1350'if filename=='generated_113D60'else None,word_patches_path=o/'baseline/conker/retail_word_patches.us.csv'),out);assert out.read_bytes()==expected,(name,label)
  rows.append(dict(source=name,functions_equal=count,pools_and_diagnostics_equal=True,complete_padded_owner_equal=True,object_sha256=hashlib.sha256(expected).hexdigest()))
 # Compile the actual selected C forwarding bodies against a typed u16 voice
 # provider. The Game s32 callback promotes unsigned handles without sign loss.
 def body(source,name):
  match=re.search(r'^\w+[ *]*'+re.escape(name)+r'\([^;{}]*\)\s*\{',source,re.M);assert match;start=match.start();end=source.index('\n}',match.end())+2;return source[start:end]
 audio=body(p.MANIFEST['selected_sources']['conker/src/init_EB00.c'],'func_10010F30');sound=body(p.MANIFEST['selected_source'],'func_15198C60');assert audio.startswith('u16 ')and sound.startswith('s32 ')and 'return func_10010BE8'in audio and 'return func_10010F30'in sound
 text='#include <ultra64.h>\n'+r"""
u8 D_80041FD9;static u16 value;static int error,calls;
__attribute__((noinline,noclone))u16 func_10010BE8(u16 zero,s32 id,u16 volume,u8 pan,s16 pitch,u8 flags,u8 channel){calls++;if(zero||id!=0x1AA||volume!=0x7fff||pan!=0x40||pitch||flags||channel!=D_80041FD9)error=1;return value;}
"""+audio+'\n'+sound+r"""
static int run(void){u32 i,j;static const u16 edges[5]={0,1,0x7fff,0x8000,0xffff};for(i=0;i<256;i++)for(j=0;j<522;j++){D_80041FD9=i;value=j<517?j*127:edges[j-517];calls=error=0;if(func_15198C60()!=(s32)value||error||calls!=1)return 1;}return 0;}
__attribute__((force_align_arg_pointer))void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
""";src=root/'return-chain.c';src.write_text(text);profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=root/('return-chain'+opt);q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(src),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr;q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b'');profiles[opt]=dict(cases=256*522,UBSan=True,SDK32=True,explicit_unsigned16_boundaries=[0,1,32767,32768,65535])
 q=dict(shared_audio_return='u16',game_sound_callback_return='s32 unsigned promotion',existing_owners=rows,protected_existing_functions=sum(x['functions_equal']for x in rows)+68,native_actual_return_chain=profiles,source_installed=p.installed(),matching_credit=0);(o/'ABI-qualified.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
