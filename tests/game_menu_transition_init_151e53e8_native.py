"""SDK32 menu/actor ABI, code-address codec and effective source controls."""
import json,subprocess
from dataclasses import replace
from tools.experiments import game_menu_transition_init_151e53e8_match as p
from tools.tests import game_menu_transition_init_151e53e8_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
def main():
 vectors=[replace(c,slot=c.slot&127)for c in g.cases()if not c.alias];literal=lambda x:'0x%08Xu'%(x&0xffffffff)
 header='static const struct {s32 count,tag,defer,gate,slot,seed;} vectors[]={'+','.join('{'+','.join(map(literal,(c.count,c.tag,c.defer,c.gate,c.slot,c.seed)))+'}'for c in vectors)+'};\n'
 (o/'native-vectors.h').write_bytes(header.encode())
 prefix='''#include <ultra64.h>
#include "structs.h"
#define offsetof(t,m) __builtin_offsetof(t,m)
__attribute__((noreturn)) static void exit(s32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void *memset(void *to,s32 v,u32 n){u8 *d=to;u32 i;for(i=0;i<n;i++)d[i]=(u8)v;return to;}
_Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
_Static_assert(sizeof(struct127)==0x32c && offsetof(struct127,unk31C)==0x31c && offsetof(struct126,unk1AA)==0x1aa,"actor ABI");
u8 D_8008FE2C,D_80087270[8],D_800BE616,D_800E0B94,D_8008FD74,D_800E0A86;
s8 D_8008FD90,*D_8008FDD4,D_800AB68C[1287];u16 D_8008FDC0;s32 D_800E0A90,D_800E0A88;
struct127 D_800CC2D0[256];static struct126 data[256];
static union {s8 bytes[0xc80];s16 words[0x640];} menu;
static u32 callback_calls;static s32 expected_state,expected_handler;
s32 func_151E4BD8(){if(menu.bytes[0x3f]!=expected_state || D_800E0A88!=expected_handler || D_800E0A90 || D_8008FE2C || D_80087270[0] || D_800E0B94!=7)exit(10);callback_calls++;return -7;}
void func_151DDBA0(void){exit(11);}
'''+p.MANIFEST['declarations']+'\n#include "native-vectors.h"\n'
 suffix='''
static int run(void){u32 v,j;for(v=0;v<sizeof(vectors)/sizeof(*vectors);v++){
 const s32 count=vectors[v].count,tag=vectors[v].tag,defer=vectors[v].defer,gate=vectors[v].gate,slot=vectors[v].slot,seed=vectors[v].seed;
 const s16 values[]={0,(s16)0x8000,0x7fff,-1,0x1234};
 memset(&menu,0x6b,sizeof(menu));memset(D_800AB68C,0x6b,sizeof(D_800AB68C));
 menu.bytes[0x42]=slot;D_800AB68C[slot*10+7]=tag;D_8008FDD4=menu.bytes;D_8008FD90=count;D_800BE616=gate;
 D_800E0A90=0x89abcdef;D_8008FE2C=0x91;D_80087270[0]=0x82;D_800E0B94=0x73;D_8008FD74=0x64;D_800E0A86=0x55;D_8008FDC0=0xffff^(seed*0xa55a);D_800E0A88=0x12345678;callback_calls=0;
 for(j=0;j<256;j++){D_800CC2D0[j].unk31C=&data[j];data[j].unk1AA=values[(j+seed)%5];}
 expected_state=tag==-1?3:4;expected_handler=(s32)(tag==-1?(void*)func_151DDBA0:(void*)func_151E4BD8);
 func_151E53E8(defer);
 if(D_800E0A90 || D_8008FE2C || D_80087270[0])return 12;
 if(D_800E0B94!=(gate?7:4) || D_8008FD74!=(gate?8:0x64) || D_800E0A86!=(gate?(u8)defer:0x55) || D_8008FDC0!=(u16)((0xffff^(seed*0xa55a))&(gate?0xe35f:0xffff)))return 13;
 if(callback_calls!=(u32)(gate && tag==-2 && defer==0))return 14;
 if(gate && tag==-2 && defer!=0){expected_state=3;expected_handler=(s32)func_151DDBA0;}
 if(!gate){expected_state=0x6b;expected_handler=0x12345678;}
 if(menu.bytes[0x3f]!=expected_state || D_800E0A88!=expected_handler)return 15;
 for(j=0;j<sizeof(menu);j++){
  if(j==0x3f || j==0x42)continue;
  if(gate && count>0 && j>=0x6c && (j-0x6c)/12<(u32)count && (j-0x6c)%12<2)continue;
  if((u8)menu.bytes[j]!=0x6b)return 16;
 }
 for(j=0;gate && j<(u32)(count>0?count:0);j++)if(menu.words[(0x6c+j*12)/2]!=values[(j+seed)%5])return 17;
 if(menu.bytes[0x42]!=slot || D_8008FDD4!=menu.bytes || D_8008FD90!=count || D_800BE616!=gate)return 18;
 }return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 def run(body,label,opt):
  f=o/label;src=f.with_suffix('.c');src.write_bytes((prefix+body+suffix).encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(src),'-o',str(f)],capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,q.stderr
  q=subprocess.run([str(f)],capture_output=True,text=True,timeout=30);assert not q.stderr,q.stderr;return q.returncode
 body=p.MANIFEST['body'];profiles={}
 for opt in('-O0','-O2','-O3'):
  code=run(body,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(cases=len(vectors),SDK32=True,UBSan=True,strict_aliasing=True,real_actor_views=True,nonnegative_slot_typed_domain=True,public_alias_cases_guest_only=True)
 controls=[('gate','D_800BE616 != 0','D_800BE616 == 0'),('clear','D_800E0A90 = 0','D_800E0A90 = 1'),('signed-count','index < D_8008FD90','index < (u8)D_8008FD90'),('loop-bound','index < D_8008FD90','index + 1 < D_8008FD90'),('stride','index * 12','index * 10'),('actor-value','->unk1AA;','->unk1AA + 1;'),('mask','0xE35F','0xE35E'),('defer-width','if (defer == 0)','if ((u8)defer == 0)'),('row-test','== -2','== -1'),('handler','D_800E0A88 = (s32)func_151E4BD8','D_800E0A88 = (s32)func_151DDBA0'),('state','[0x3F] = 4','[0x3F] = 5')]
 outcomes=[]
 for name,old,new in controls:
  assert old in body,name;code=run(body.replace(old,new),'control-'+name,'-O2');assert code in range(10,19),(name,code);outcomes.append(dict(control=name,comparison_exit=code,source_sha256=p.sha(o/('control-'+name+'.c')),binary_sha256=p.sha(o/('control-'+name))))
 q=dict(profiles=profiles,effective_source_controls=outcomes,no_signal_or_UBSan_trap_counted=True,void_result_not_compared=True,callback_address_codec_verified=True,unmatched_helper_not_executed=True,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(dict(native_cases=len(vectors),profiles=list(profiles),controls=len(outcomes))),flush=True);return q
if __name__=='__main__':main()
