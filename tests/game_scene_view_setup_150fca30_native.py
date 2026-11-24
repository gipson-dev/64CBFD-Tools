"""SDK32 native request fields, exact call words and effective semantic controls."""
import hashlib,json,subprocess
from tools.experiments import game_scene_view_setup_150fca30_match as p
from tools.tests import game_scene_view_setup_150fca30_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
def main():
 vectors=list(g.cases());rows=[];starts=[];final=[]
 for c in vectors:
  starts.append(len(rows));expected,q=g.reference(g.fixture(c),c)
  for target,a in q.calls:
   tag=next(i for i,n in enumerate(g.NAMES)if g.S[n]==target);a=list(a)
   if tag==1:a[7]=0x1000ec24
   if tag==3:a[0]=0x440000
   rows.append((tag,len(a),*a,*([0]*(12-len(a)))))
  final.append(g.read(expected,g.S['D_80082FA0']))
 starts.append(len(rows))
 literal=lambda x:'0x%08Xu'%(x&0xffffffff)
 header='static const u32 expected[][14]={\n'+''.join('{'+','.join(map(literal,row))+'},\n'for row in rows)+'};\n'
 header+='static const u32 starts[]={'+','.join(map(str,starts))+'};\n'
 header+='static const u32 final_count[]={'+','.join(map(literal,final))+'};\n'
 header+='static const struct {u32 count,mode;} vectors[]={'+','.join('{'+literal(c.count)+','+str(c.mode)+'}'for c in vectors)+'};\n'
 (o/'native-vectors.h').write_bytes(header.encode())
 prefix='''#include <ultra64.h>
#define offsetof(t,m) __builtin_offsetof(t,m)
__attribute__((noreturn)) static void exit(s32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void *memcpy(void *to,const void *from,u32 n){u8 *d=to;const u8 *s=from;u32 i;for(i=0;i<n;i++)d[i]=s[i];return to;}
static void *memset(void *to,s32 value,u32 n){u8 *d=to;u32 i;for(i=0;i<n;i++)d[i]=(u8)value;return to;}
_Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
'''+p.MANIFEST['declarations']+'\n#include "native-vectors.h"\n'+'''
_Static_assert(sizeof(TimedViewRequest150FCA30)==8 && offsetof(TimedViewRequest150FCA30,lifetime)==2 && offsetof(TimedViewRequest150FCA30,callback)==6,"packet layout");
s32 D_80082FA0;static u32 vector,row,resets,sounds,views,mode,callback_calls;static u8 output[64];
static void record(u32 tag,u32 n,const u32 *a){
 u32 j;if(row>=starts[vector+1] || expected[row][0]!=tag || expected[row][1]!=n)exit(10);
 for(j=0;j<n;j++)if(expected[row][j+2]!=a[j])exit(11);row++;
}
s32 func_1000EC24(){callback_calls++;return 0;}
s32 func_150FCBC0(s32 index){u32 a[]={index};record(0,1,a);resets++;if(mode==1 && resets==1)D_80082FA0=3;return -1;}
u16 func_1000FA64(u16 kind,s16 x,s16 y,s16 z,s32 volume,u16 range,s16 pitch,s32 callback,void *angle,s32 a9,s32 a10,s32 a11){
 u32 a[]={kind,(u32)(s32)x,(u32)(s32)y,(u32)(s32)z,volume,range,(u32)(s32)pitch,0,(u32)angle,a9,a10,a11};
 if((u32)callback!=(u32)func_1000EC24)exit(12);a[7]=0x1000ec24;record(1,12,a);sounds++;
 if(mode==2 && sounds==3)D_80082FA0=-1;if(mode==6)D_80082FA0=(s32)sounds-1;return 0x8001;
}
void func_15164F0C(u8 kind,u8 index,s32 a2,u8 slot,s32 context){u32 a[]={kind,index,a2,slot,context};record(2,5,a);views++;
 if(mode==3 && views==1)D_80082FA0=-1;if(mode==4 && views==1)D_80082FA0=3;if(mode==5 && views==256)D_80082FA0=255;
}
u8 *func_151D8868(u8 *owner,s32 bytes,u8 slot,s32 context){
 TimedViewRequest150FCA30 *q=(TimedViewRequest150FCA30*)owner;u32 a[]={0x440000,bytes,slot,context};record(3,4,a);
 if(q->flags!=1 || q->lifetime!=100 || q->level!=8 || q->players!=15 || q->callback!=-1)exit(13);
 memcpy(output+14,owner,8);return output;
}
'''
 suffix='''
static int run(void){u32 j;for(vector=0;vector<sizeof(vectors)/sizeof(*vectors);vector++){
 D_80082FA0=(s32)vectors[vector].count;mode=vectors[vector].mode;row=starts[vector];resets=sounds=views=callback_calls=0;memset(output,0x6b,sizeof(output));
 func_150FCA30();if(row!=starts[vector+1] || (u32)D_80082FA0!=final_count[vector] || callback_calls) return 14;
 for(j=0;j<64;j++)if((j<14 || j>=22) && output[j]!=0x6b)return 15;
 if(output[14]!=1 || output[18]!=8 || output[19]!=15 || output[20]!=255)return 16;
 }return 0;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 def run(body,label,opt):
  f=o/label;source=f.with_suffix('.c');source.write_bytes((prefix+body+suffix).encode());command=native_command(opt)+['-fstrict-aliasing',str(source),'-o',str(f)]
  q=subprocess.run(command,capture_output=True,text=True);(o/(label+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0,q.stderr
  q=subprocess.run([str(f)],capture_output=True,text=True,timeout=30);assert not q.stderr,q.stderr;return q.returncode
 body=p.MANIFEST['body'];profiles={}
 for opt in('-O0','-O2','-O3'):
  assert run(body,'native-'+opt[1:],opt)==0
  profiles[opt]=dict(cases=len(vectors),SDK32=True,UBSan=True,strict_aliasing=True,initialized_packet_fields_and_all_call_words_compared=True,actual_eight_byte_memcpy=True,portable_unwritten_byte_identity_claim=False)
 controls=[('first-reset','func_150FCBC0(0);','func_150FCBC0(1);'),('sound-kind','0x2B8','0x2B9'),('sound-coordinate','-2038','-2037'),('sound-angle','(void *)45','(void *)44'),('sound-callback','(s32)(u32)func_1000EC24','0'),('count-overflow-edge','(s32)((u32)D_80082FA0 + 1U) > 0','D_80082FA0 >= 0'),('stale-count','        do {','        s32 captured = D_80082FA0;\n        do {'),('index-width','    u32 index;','    u8 index;'),('loop-boundary','(s32)index <= D_80082FA0','(s32)index < D_80082FA0'),('view-context','0, 0xFF, 1','0, 0xFF, 0'),('packet-lifetime','request.lifetime = 100','request.lifetime = 101'),('packet-mask','request.players = 15','request.players = 7'),('packet-callback','request.callback = -1','request.callback = 0')]
 outcomes=[]
 for name,old,new in controls:
  assert old in body,name;bad=body.replace(old,new)
  if name=='stale-count':bad=bad.replace('(s32)index <= D_80082FA0','(s32)index <= captured')
  code=run(bad,'control-'+name,'-O2');assert code in range(10,17),(name,code)
  outcomes.append(dict(control=name,comparison_exit=code,source_sha256=p.sha(o/('control-'+name+'.c')),binary_sha256=p.sha(o/('control-'+name))))
 q=dict(profiles=profiles,effective_source_controls=outcomes,no_signal_or_UBSan_trap_counted=True,void_result_not_compared=True,callback_address_codec_verified=True,source_installed=p.installed(),matching_credit=0)
 (o/'native.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(dict(native_cases=len(vectors),profiles=list(profiles),controls=len(outcomes))),flush=True);return q
if __name__=='__main__':main()
