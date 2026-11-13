def run():
 from pathlib import Path
 import sys,subprocess
 from tools.experiments import game_queue_append_1518abd0_match as packet
 root=packet.ROOT;out=packet.OUT
 from tools.experiments.game_remaining_donor_candidates import body
 from tools.tests.test_game_projected_packet_draw import native_command
 from tools.tests.test_game_row_destination_fill import START
 fn=body(packet.MANIFEST['selected_source'],'func_1518ABD0')
 controls={
  'allocation':('if (record == NULL)', 'if (record == NULL) return 0;\n    if (0)'),
  'selector':('if (selector != 0)', 'if (selector == 0)'),
  'count':(' + 1;', ' + 2;'),
  'limit':('limit < (s32)count','limit <= (s32)count'),
  'timer':('= duration;','= 0;'),
  'retirecount':('= count - 1;','= count;'),
  'tail':('tail = *(u8 **)(queue + 0x10);','tail = NULL;'),
  'link':('*(u8 **)(tail + 0x18) = (u8 *)record;','*(u8 **)(tail + 0x18) = NULL;'),
  'free':('func_1516972C((struct102 *)entry);','(void)entry;'),
  'return':('return 1;','return 0;'),
 }
 pre=r'''
 #include <ultra64.h>
 typedef struct Foo struct102;
 typedef struct {u8 pad0[0x10];s32 owner,unk14,unk18;u8 selector;u8 pad1D[3];} Generated1B7EC0Command1E;
 extern void (*D_8008D5C0[])(u8 *);
 void func_1516972C(struct102 *);
 Generated1B7EC0Command1E *func_1518AB60(s32,u8);
 '''
 code=pre+fn.replace('func_1518ABD0(','selected(',1)+'\n'
 for name,(old,new) in controls.items():
  assert old in fn,(name,old);code+=fn.replace('func_1518ABD0(','bad_'+name+'(',1).replace(old,new,1)+'\n'
 code+=r'''
 typedef union {u32 align;u8 data[128];} Buffer;
 static Buffer queue,head,tail,owner;static Generated1B7EC0Command1E created;
 void (*D_8008D5C0[256])(u8 *);
 static int callbackCount,freeCount,allocCount,allow;static u8 *callbackArg;static struct102 *freed;
 static void callback(u8 *p){callbackCount++;callbackArg=p;}
 void func_1516972C(struct102 *p){freeCount++;freed=p;}
 Generated1B7EC0Command1E *func_1518AB60(s32 arg,u8 selector){allocCount++;if(!allow)return NULL;created.owner=arg;created.unk14=0;created.unk18=0;created.selector=selector;return &created;}
 typedef s32 (*Fn)(u8 *,s32,u8);
 static int check(Fn fn){
  static const u32 counts[]={0,1,0x7fffffffu,0xffffffffu};static const s32 limits[]={-1,0,1,0x7fffffff};static const u8 sels[]={0,1,2,255};
  for(int q=0;q<2;q++)for(int ok=0;ok<2;ok++)for(int c=0;c<4;c++)for(int l=0;l<4;l++)for(int sel=0;sel<4;sel++)for(int filled=0;filled<2;filled++){
   u8 *qp=queue.data,*hp=head.data,*tp=tail.data;for(int i=0;i<128;i++){qp[i]=hp[i]=tp[i]=owner.data[i]=0;}for(int i=0;i<256;i++)D_8008D5C0[i]=callback;
   *(u8 **)(qp+0x10)=filled?tp:NULL;*(u8 **)(qp+0x14)=filled?hp:NULL;*(s32 *)(qp+0x18)=limits[l];*(u32 *)(qp+0x1c)=counts[c];*(s16 *)(qp+0x20)=(s16)0x8a9b;*(u16 *)(qp+0x22)=0xbeef;
   *(u8 **)(hp+0x10)=owner.data+8;*(u8 **)(hp+0x18)=tp;hp[0x1c]=1;*(u8 **)(tp+0x18)=NULL;
   callbackCount=freeCount=allocCount=0;callbackArg=NULL;freed=NULL;allow=ok;
   s32 ret=fn(q?qp:NULL,(s32)owner.data,sels[sel]);
   if(!q || !ok){if(ret!=0 || allocCount!=(q?1:0) || callbackCount!=(sels[sel]?1:0) || freeCount || (callbackCount && callbackArg!=owner.data))return 1;continue;}
   u32 n=counts[c]+1;int evict=limits[l]<(s32)n;u8 *expected_head=filled?hp:(u8 *)&created;
   if(ret!=1 || allocCount!=1 || *(u16 *)(qp+0x22)!=0x8a9b || *(u32 *)(qp+0x1c)!=(evict?n-1:n))return 2;
   if(evict){u8 *evicted=expected_head;u8 *newhead=filled?tp:NULL;if(freed!=(struct102*)evicted || freeCount!=1 || *(u8 **)(qp+0x14)!=newhead || *(u8 **)(qp+0x10)!=(filled?(u8 *)&created:NULL))return 3;
    int expected_cb=filled?1:(sels[sel]!=0);if(callbackCount!=expected_cb || (expected_cb && callbackArg!=(filled?owner.data+8:owner.data)))return 4;
   }else if(freeCount || callbackCount || *(u8 **)(qp+0x14)!=expected_head || *(u8 **)(qp+0x10)!=(u8 *)&created)return 5;
   if(filled && *(u8 **)(tp+0x18)!=(u8 *)&created)return 6;
  }
  return 0;
 }
 static int run(void){if(check(selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(bad_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');path=out/'native.c';path.write_text(code)
 for opt in ('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-Wno-unused-but-set-variable',str(path),'-o',str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
  print(opt,'1024 queue cases,',len(controls),'negative controls, UBSan',flush=True)
