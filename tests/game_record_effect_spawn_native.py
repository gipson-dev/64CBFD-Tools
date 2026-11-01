from pathlib import Path
import itertools,json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def qualify(r,o):
 body=(o/'selected-input.c').read_text();headers=(o/'selected-headers.c').read_text()
 controls=(('added-buffer-clear',body.replace('    record[0x16] |= 4;','    bzero(data, sizeof(data));\n    record[0x16] |= 4;')),
  ('missing-record-flag',body.replace('record[0x16] |= 4;','record[0x16] |= 0;')),
  ('unsigned-coordinate',body.replace('*(s16 *)(record + 0)','*(u16 *)(record + 0)')),
  ('wrong-payload-flag-value',body.replace('data[0x2C] = 0','data[0x2C] = 1')),
  ('wrong-copy-size',body.replace('data, 0x34','data, 0x30')),
  ('wrong-effect-kind',body.replace('0x21, -1','0x22, -1')),
  ('cached-coordinate',body.replace('    u8 *effect;','    u8 *effect;\n    s32 first = *(s16 *)record;').replace('func_1510FD20(*(s16 *)(record + 0),','func_1510FD20(first,')))
 assert all(text!=body for _,text in controls)
 code=headers+r'''
 static union {u32 align;u8 bytes[96];} recordStorage,outputStorage;
 static u32 outcome,mode,seed,ordinal,error,flags,height,key,first,second;
 static u8 *rec;static u32 packetSeen,clears;
 static u32 load32(const void *p){const u8 *v=p;return (u32)v[0]|(u32)v[1]<<8|(u32)v[2]<<16|(u32)v[3]<<24;}
 static void put16(u8 *p,u32 v){p[0]=v;p[1]=v>>8;}
 static u32 sext(u32 v){return (u32)(s32)(s16)v;}
 f32 func_15144598(struct134 *record){union{u32 u;f32 f;}v;v.u=height;if(ordinal++!=0||(u8*)record!=rec||rec[0x16]!=(u8)(flags|4))error=1;return v.f;}
 void func_1510F800(s32 zero){if(ordinal++!=1||zero)error=1;if(mode){put16(rec,65535);put16(rec+4,32768);rec[0x16]^=128;}}
 s32 func_1510FD20(s32 a,s32 b){if(ordinal++!=2||(u32)a!=sext(mode?65535:first)||(u32)b!=sext(mode?32768:second))error=1;return key;}
 struct260 *func_15149130(s16 a,s8 b,s8 c,s8 d,u8 e,u8 f,struct37 *g,u8 h,s32 i){
  if(ordinal++!=3||a!=300||b!=-1||c!=33||d!=-1||e||f||(u32)g!=52||h!=255||i!=1)error=1;
  return outcome?(struct260*)(outputStorage.bytes+8):0;
 }
 void bzero(void *p,int n){int i;clears++;for(i=0;i<n;i++)((u8*)p)[i]=0;}
 void *memcpy(void *dst,const void *src,u32 n){u32 i;const u8 *p=src;u8 *q=dst;packetSeen++;
  if(ordinal++!=4||q!=outputStorage.bytes+48||n!=52||load32(p)!=(u32)rec||load32(p+4)!=height||load32(p+8)||load32(p+12)!=key||p[44])error=1;
  for(i=0;i<n;i++)q[i]=p[i];return dst;
 }
 '''
 # The payload extends to outputStorage+100; give it additional trailing canaries.
 code=code.replace('outputStorage;','outputStorage;').replace('u8 bytes[96]','u8 bytes[128]')
 for i,(_,text) in enumerate((('valid',body),)+controls):code+=text.replace('func_15014094(','root_%d('%i)+'\n'
 code+='static s32 (*roots[])(u8*)={'+','.join('root_%d'%i for i in range(8))+'};\n'
 code+=r'''
 static int run(void){u32 i,j,k,failed,killed=0,cases=0;static const u32 ends[]={0,32767,32768,65535};static const u32 heights[]={0,0x80000000u,0x41480000u};
  for(seed=0;seed<4;seed++)for(outcome=0;outcome<2;outcome++)for(mode=0;mode<2;mode++)for(i=0;i<4;i++)for(j=0;j<3;j++){
   first=ends[i];second=ends[3-i];height=heights[j];key=seed*0x1020304u;flags=(seed*73u)&255;cases++;
   for(k=0;k<8;k++){
    u32 at;for(at=0;at<128;at++){recordStorage.bytes[at]=(at*29+seed*11+90)&255;outputStorage.bytes[at]=(at*31+seed*7+165)&255;}
    rec=recordStorage.bytes+8;put16(rec,first);put16(rec+4,second);rec[22]=flags;ordinal=error=packetSeen=clears=0;
    roots[k](rec);failed=error||clears||ordinal!=(outcome?5u:4u)||packetSeen!=outcome||rec[22]!=(u8)((flags|4)^(mode?128:0));
    for(at=0;at<128;at++){
     if(!(at>=8&&at<10)&&!(at>=12&&at<14)&&at!=30&&recordStorage.bytes[at]!=(u8)(at*29+seed*11+90))failed=1;
     if((!outcome||at<48||at>=100)&&outputStorage.bytes[at]!=(u8)(at*31+seed*7+165))failed=1;
    }
    if(!k&&failed)return 2;if(k&&failed)killed|=1u<<(k-1);
   }
  }
  return killed==127u&&cases==192?0:3;
 }
 '''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 rows=[]
 for opt in ('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]);p.with_suffix('.c').write_text(code)
  cmd=native_command(opt)+['-Wno-return-type','-Wno-maybe-uninitialized','-Wno-uninitialized','-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)]
  q=subprocess.run(cmd,cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  rows.append(dict(profile=opt,cases=192,executions=1536,controls=[n for n,_ in controls],all_seven_controls_effective=True,UBSan=True,whole_record_and_destination_canaries=True,initialized_payload_fields_checked=True,untouched_stack_payload_bytes_not_asserted=True,return_value_unused=True,guest_private_stack_mutations_excluded=True))
 (o/'private-native-runtime.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows,flush=True)
 return rows
