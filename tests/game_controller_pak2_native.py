from pathlib import Path
import subprocess,json
from tools.tests.test_game_row_destination_fill import START
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-controller-pak2-durable'
prefix=r'''
typedef unsigned char u8; typedef unsigned short u16; typedef unsigned int u32; typedef int s32;
typedef struct { int unused; } OSMesgQueue;
typedef struct { u32 ramarray[15],pifstatus; } OSPifRam;
typedef struct { u8 dummy,txsize,rxsize,cmd; u16 address; u8 data[32],datacrc; } __OSContRamReadFormat;
OSPifRam __osPfsPifRam; u8 __osContLastCmd;
#define D_80042A0C __osPfsPifRam.pifstatus
#define NULL ((void*)0)
#define ARRLEN(x) ((s32)(sizeof(x)/sizeof((x)[0])))
#define CHNL_ERR(x) (((x).rxsize & 0xc0)>>4)
#define CONT_CMD_NOP 255
#define CONT_CMD_EXE 1
#define CONT_CMD_END 254
#define CONT_CMD_READ_MEMPACK 2
#define CONT_CMD_WRITE_MEMPACK 3
#define CONT_CMD_READ_MEMPACK_TX 3
#define CONT_CMD_READ_MEMPACK_RX 33
#define CONT_CMD_WRITE_MEMPACK_TX 35
#define CONT_CMD_WRITE_MEMPACK_RX 1
#define OS_READ 0
#define OS_WRITE 1
#define OS_MESG_BLOCK 1
#define PFS_ERR_CONTRFAIL 4
void __osSiGetAccess(void); void __osSiRelAccess(void); int __osSiRawStartDma(int,OSPifRam*);
int osRecvMesg(OSMesgQueue*,void*,int); int __osPfsGetStatus(OSMesgQueue*,int);
u8 __osContAddressCrc(u16); u8 __osContDataCrc(u8*);
'''
models=r'''
static int scenario,attempts,locks,unlocks,dmas,received,statuses,crc_calls;
static u8 expected_data[32];
void *__attribute__((noinline)) memcpy(void*d,const void*s,unsigned n){unsigned i;u8*a=d;const u8*b=s;for(i=0;i<n;i++)a[i]=b[i];return d;}
void __osSiGetAccess(void){locks++;} void __osSiRelAccess(void){unlocks++;}
u8 __osContAddressCrc(u16 v){u8 r=0,t;int i;for(i=0;i<16;i++){t=(r&16)?21:0;r=(u8)((r<<1)|((v&1024)!=0));v=(u16)(v<<1);r^=t;}return r&31;}
u8 __osContDataCrc(u8*p){(void)p;crc_calls++;return 0x5a;}
int __osPfsGetStatus(OSMesgQueue*m,int ch){(void)m;(void)ch;statuses++;return scenario==3?7:0;}
int osRecvMesg(OSMesgQueue*m,void*msg,int mode){(void)m;(void)msg;(void)mode;received++;return 0;}
int __osSiRawStartDma(int dir,OSPifRam*p){int i;__OSContRamReadFormat*q=(void*)p;dmas++;if(dir==0){attempts++;q->rxsize=scenario==4?0x80:scenario==5?0x40:0;for(i=0;i<32;i++)q->data[i]=expected_data[i];q->datacrc=(scenario==2||scenario==3||(scenario==1&&attempts==1))?0xa5:0x5a;}return 0;}
'''
test=r'''
int run(void){int kind,sc,a,force,i,ret,early,n,want;u8 buffer[32];OSMesgQueue mq;
 if(sizeof(void*)!=4||sizeof(__OSContRamReadFormat)!=40||sizeof(OSPifRam)!=64)return 10;
 for(i=0;i<32;i++)expected_data[i]=(u8)(i*7+0x29);
 for(kind=0;kind<2;kind++)for(sc=0;sc<6;sc++)for(a=0;a<8;a++)for(force=0;force<2;force++){
  scenario=sc;attempts=locks=unlocks=dmas=received=statuses=crc_calls=0;
  for(i=0;i<32;i++)buffer[i]=(u8)(i*11+3);
  ret=kind?__osContRamWrite2(&mq,0,(u16)a,buffer,force):__osContRamRead2(&mq,0,(u16)a,buffer);
  early=kind&&force!=1&&a>0&&a<7;n=early?0:(sc==2||sc==5)?4:sc==1?2:1;
  want=early||sc==0||sc==1?0:sc==3?7:sc==4?8:4;
  if(ret!=want||attempts!=n||locks!=!early||unlocks!=!early||dmas!=(n?n+1:0)||received!=dmas)return 11;
  for(i=0;i<32;i++){u8 v=!kind&&!want?expected_data[i]:(u8)(i*11+3);if(buffer[i]!=v)return 12;}
 }
 return 0;
}
'''
sources=[]
for kind in ('read','write'):
 text=(out/f'generated_contram{kind}2-selected.c').read_text()
 sources.append('\n'.join(line for line in text.splitlines() if not line.startswith('#include') and not line.startswith('extern u32 D_80042A0C;')))
source=out/'native.c';source.write_text(prefix+'\n'.join(sources)+models+test+START)
reports=[]
for opt in ('-O0','-O2','-O3'):
 exe=out/('native'+opt[1:]);argv=['cc','-m32',opt,'-std=gnu99','-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-fno-strict-aliasing','-fsanitize=undefined','-fsanitize-undefined-trap-on-error',str(source),'-o',str(exe)]
 p=subprocess.run(argv,capture_output=True,text=True);assert p.returncode==0,(argv,p.stderr)
 r=subprocess.run([str(exe)]);assert r.returncode==0,(opt,r.returncode)
 reports.append(opt)
report={'optimizations':reports,'cases_each':192,'ubsan_trapping':True,'aligned_channel_only':True,'si_and_crc_modeled':True}
(out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
