"""Actual SDK32 wrapper with the factory's measured mixed-width ABI."""
from pathlib import Path
import json,re,subprocess,sys
from tools.experiments import game_opposed_effect_spawn_150bef7c_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_opposed_effect_spawn_150bef7c_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
def controls(body):
 result={'byte-only-parameter':body.replace('parameter, 50','(u8)parameter, 50'),
 'wrong-position':body.replace('position = 380;','position = 381;'),
 'missing-mirror':body.replace('position = -position;','position = position;'),
 'one-request':body.replace('count != 2','count != 1'),
 'wrong-kind':body.replace('(s16)position, 0xD','(s16)position, 0xC'),
 'wrong-first-color':body.replace('0x50, 0x8F','0x51, 0x8F')}
 assert all(v!=body for v in result.values());return result
def program():
 prototype=(o/'selected-final/declarations.c').read_text().strip().removesuffix(';');names=re.findall(r'\barg(\d+)\b',prototype);assert list(map(int,names))==list(range(49))
 initializer=','.join('(u32)arg'+str(i)for i in range(49));expected=','.join(hex(x)+'u'for x in g.packet(0,0))
 provider='__attribute__((noinline,noclone)) '+prototype+''' {
 u32 values[49]={INITIALIZER},i,want;
 if(calls>=2){failure=1;calls++;return;}
 for(i=0;i<49;i++){
  want=i==2?(calls==0?380u:(u32)-380):i==31?(current&65535):expected[i];
  if(values[i]!=want)failure=1;
 }
 calls++;
}'''.replace('INITIALIZER',initializer)
 body=(o/'selected-final/body.c').read_text().replace('func_150BEF7C(','subject(')
 src='#include <ultra64.h>\n_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(s32)==4,"SDK32 ABI");\n'+(o/'selected-final/declarations.c').read_text()+'static u32 calls,failure,current;\nstatic const u32 expected[49]={'+expected+'};\n'+provider+'\n'+body+r'''
static int run(void){u32 i,j,high[3]={0,0x80000000u,0xCAFE0000u};
 for(j=0;j<3;j++)for(i=0;i<65536;i++){
  current=high[j]|i;calls=failure=0;subject((s32)current);
  if(calls!=2||failure)return 1;
 }
 return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 return src,body
def main():
 src,body=program();profiles={}
 def run(text,label,opt):
  p=o/(label+'.c');p.write_text(text);exe=o/(label+opt);q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
  return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in('-O0','-O2','-O3'):
  q=run(src,'native',opt);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b''),(opt,q.returncode,q.stderr);profiles[opt]=dict(cases=196608,SDK32=True,UBSan=True,strict_aliasing=True,all_49_typed_arguments_compared=True)
 effective=[]
 for label,changed in controls((o/'selected-final/body.c').read_text()).items():
  altered=changed.replace('func_150BEF7C(','subject(')
  q=run(src.replace(body,altered),'control-'+label,'-O2');assert q.returncode==1,(label,q.returncode,q.stderr);effective.append(label)
 report=dict(profiles=profiles,effective_output_comparison_controls=effective,source_installed=packet.installed(),matching_credit=0,limits='Complete SDK32 wrapper and typed 49-argument factory boundary. The actual factory C retains a big-endian byte-home read for arg47; its unmodified native execution is not claimed here. The complete original/current factory is exercised in the guest chain instead.')
 (o/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
