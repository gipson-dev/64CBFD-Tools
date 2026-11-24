"""SDK32 fade semantics, logical address codec and effective source controls."""
from dataclasses import replace
import json,subprocess
from tools.experiments import game_menu_fade_renderer_151e09dc_match as p
from tools.tests import game_menu_fade_renderer_151e09dc_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
def main():
 vectors=[replace(c,slot=c.slot&127,index=c.index&127)for c in g.cases()if not c.alias];literal=lambda x:'0x%08Xu'%(x&0xffffffff);rows=[];expected=[];images=[];starts=[]
 for c in vectors:
  initial=g.fixture(c)
  # Typed native backing includes all nonnegative row/mask indices.
  g.put(initial,g.S['D_800AB754']+c.index*4,g.mask_value(c.index))
  end,calls=g.reference(initial,c);starts.append(len(rows))
  for target,a in calls:rows.append((next(i for i,n in enumerate(g.NAMES)if g.S[n]==target),len(a),*a,*([0]*(5-len(a)))))
  expected.append((end[g.S['D_800E0A95']],end[g.S['D_800E0A96']],end[g.S['D_8008FDE0']],g.read(end,g.S['D_800BE9E4']),int(g.read(end,g.S['D_8008FDD4'])==g.OTHER),g.read(end,g.MENU+32,2),g.read(end,g.OTHER+32,2),end[g.S['D_800AB690']+c.slot*10],end[g.S['D_800AB690']+70],g.read(end,g.S['D_800AB754'])))
  images.append([[end[base+j]for j in range(-8,136)]for base in(g.MENU,g.OTHER)])
 starts.append(len(rows))
 header='static const struct {s32 alpha,ticks,direction,save,flags,slot,index,mode,seed;} vectors[]={'+','.join('{'+','.join(map(literal,(c.alpha,c.ticks,c.direction,c.save,c.flags,c.slot,c.index,c.mode,c.seed)))+'}'for c in vectors)+'};\n'
 header+='static const u32 expected[][10]={'+','.join('{'+','.join(map(literal,v))+'}'for v in expected)+'};\nstatic const u32 calls[][7]={'+','.join('{'+','.join(map(literal,v))+'}'for v in rows)+'};\nstatic const u32 starts[]={'+','.join(map(str,starts))+'};\n'
 header+='static const u8 images[][2][144]={'+','.join('{'+','.join('{'+','.join(map(str,v))+'}'for v in pair)+'}'for pair in images)+'};\n';(o/'native-vectors.h').write_bytes(header.encode())
 prefix='''#include <ultra64.h>
__attribute__((noreturn)) static void exit(s32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void *memset(void *to,s32 v,u32 n){u8 *d=to;u32 i;for(i=0;i<n;i++)d[i]=(u8)v;return to;}
_Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
s8 D_800AB690[1281],D_800E0A96,D_8008FDE0,*D_8008FDD4;u8 D_800E0A95;u32 D_800AB754[128];s32 D_800BE9E4;char D_800AB850[]="#";
static union {s8 bytes[144];u16 words[72];} menus[2];static u32 vector,row,mode;
static s8 *menu(u32 i){return menus[i].bytes+8;}
static u32 mask_value(s32 i){return 0x13579bdfU^((u32)i*0x100101U);}
'''+p.MANIFEST['declarations']+'\n#include "native-vectors.h"\n'+'''
static void record(u32 tag,u32 n,const u32 *a){u32 j;if(row>=starts[vector+1] || calls[row][0]!=tag || calls[row][1]!=n)exit(10);for(j=0;j<n;j++)if(calls[row][j+2]!=a[j])exit(11);row++;}
void func_1504332C(u8 r,u8 g,u8 b,u8 a){u32 args[]={r,g,b,a};record(0,4,args);if(mode==1){D_8008FDD4=menu(1);D_800E0A95=96;D_800E0A96=1;D_800BE9E4=2;}}
void func_15042D94(s32 x,s32 y,u8 style,s32 format,...){__builtin_va_list ap;u32 args[5];if((u32)format!=(u32)D_800AB850 || D_800AB850[0]!='#' || D_800AB850[1])exit(12);__builtin_va_start(ap,format);args[0]=x;args[1]=y;args[2]=style;args[3]=0x800ab850;args[4]=__builtin_va_arg(ap,int);__builtin_va_end(ap);record(1,5,args);if(mode==2){D_800E0A95=64;D_800E0A96=0;D_800BE9E4=1;}}
void func_15042D78(u8 font){u32 args[]={font};record(2,1,args);if(mode==3){D_8008FDD4=menu(1);D_800AB690[70]=127;}}
void func_151E2404(void){record(3,0,(const u32*)0);if(mode==6){D_8008FDD4=menu(1);D_800E0A96=12;D_8008FDE0=99;}}
s32 func_151E3344(u32 mask,s32 kind,s32 alternate,u32 opacity,s32 flags){u32 args[]={mask,kind,alternate,opacity,flags};record(4,5,args);if(mode==4){D_8008FDD4=menu(1);*(u16*)(menu(1)+32)=0x1234;D_800E0A96=127;}if(mode==5){*(u16*)(D_8008FDD4+32)=0xabdf;D_800E0A96=(s8)0x81;D_800AB754[0]=0xdeadbeef;}return -7;}
'''
 suffix='''
static int run(void){u32 i,j,b;for(vector=0;vector<sizeof(vectors)/sizeof(*vectors);vector++){
 memset(menus,0x6b,sizeof(menus));memset(D_800AB690,0x6b,sizeof(D_800AB690));for(i=0;i<128;i++)D_800AB754[i]=mask_value(i);
 menu(0)[0x42]=vectors[vector].slot;menu(1)[0x42]=7;*(u16*)(menu(0)+32)=vectors[vector].flags;*(u16*)(menu(1)+32)=0xa55a;
 D_800AB690[vectors[vector].slot*10]=vectors[vector].index;D_800AB690[70]=1;D_8008FDD4=menu(0);D_800E0A95=vectors[vector].alpha;D_800E0A96=vectors[vector].direction;D_8008FDE0=vectors[vector].save;D_800BE9E4=vectors[vector].ticks;mode=vectors[vector].mode;row=starts[vector];
 func_151E09DC();
 if(row!=starts[vector+1])return 13;
 if(D_800E0A95!=expected[vector][0] || (u8)D_800E0A96!=expected[vector][1] || (u8)D_8008FDE0!=expected[vector][2] || (u32)D_800BE9E4!=expected[vector][3])return 14;
 if(D_8008FDD4!=menu(expected[vector][4]) || *(u16*)(menu(0)+32)!=expected[vector][5] || *(u16*)(menu(1)+32)!=expected[vector][6])return 15;
 if((u8)D_800AB690[vectors[vector].slot*10]!=expected[vector][7] || (u8)D_800AB690[70]!=expected[vector][8] || D_800AB754[0]!=expected[vector][9])return 16;
 for(b=0;b<2;b++)for(j=0;j<144;j++)if(j!=40 && j!=41 && (u8)menus[b].bytes[j]!=images[vector][b][j])return 17;
 for(j=1;j<128;j++)if(D_800AB754[j]!=mask_value(j))return 18;
 }return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 def run(body,label,opt):
  f=o/label;src=f.with_suffix('.c');src.write_bytes((prefix+body+suffix).encode());q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(src),'-o',str(f)],capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,q.stderr
  q=subprocess.run([str(f)],capture_output=True,text=True,timeout=30);assert not q.stderr,q.stderr;return q.returncode
 body=p.MANIFEST['body'];profiles={}
 for opt in('-O0','-O2','-O3'):
  code=run(body,'native-'+opt[1:],opt);assert code==0,(opt,code);profiles[opt]=dict(cases=len(vectors),SDK32=True,UBSan=True,strict_aliasing=True,typed_nonnegative_table_domain=True,cross_global_aliases_guest_only=True,single_intentional_variadic_word=True)
 controls=[('tick-scale','<< 5','<< 4'),('zero-fade-bound','value <= 0','value < 0'),('clamp-bound','value >= 256','value > 256'),('full-value-test','if (value != 255)','if ((u8)value != 255)'),('completed-direction','D_800E0A96 = -1','D_800E0A96 = 0'),('menu-close','[0x3F] = 0','[0x3F] = 1'),('save-gate','D_8008FDE0 != 0','D_8008FDE0 == 0'),('stored-alpha','D_800E0A95 = value','D_800E0A95 = (u32)value + 1U'),('captured-mask','func_151E3344(mask,','func_151E3344(mask ^ 1U,'),('draw-opacity','(u8)value, 0','(u8)(value ^ 1), 0'),('flag-gate','& 0x20)','& 0x10)'),('flag-mask','0xFFDF','0xFFCF'),('late-menu','func_151E3344(mask, 1, 0, (u8)value, 0);\n    menu = D_8008FDD4;','func_151E3344(mask, 1, 0, (u8)value, 0);'),('text-payload','D_800AB850, 26','D_800AB850, 27'),('font','func_15042D78(0x81)','func_15042D78(0x80)'),('color','func_1504332C(255,','func_1504332C(254,')]
 outcomes=[]
 for name,old,new in controls:
  assert old in body,name;code=run(body.replace(old,new),'control-'+name,'-O2');assert code in range(10,19),(name,code);outcomes.append(dict(control=name,comparison_exit=code,source_sha256=p.sha(o/('control-'+name+'.c')),binary_sha256=p.sha(o/('control-'+name))))
 q=dict(profiles=profiles,effective_source_controls=outcomes,no_signal_or_UBSan_trap_counted=True,void_result_not_compared=True,format_address_codec_verified=True,helper_implementation_claim=False,source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(dict(native_cases=len(vectors),profiles=list(profiles),controls=len(outcomes))),flush=True);return q
if __name__=='__main__':main()
