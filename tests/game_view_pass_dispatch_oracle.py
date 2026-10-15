"""Independent selected-view pass contract and opaque-provider execution model."""
import struct

from tools.experiments import game_view_pass_dispatch as source
from tools.tests import test_game_actor_mask_scan_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_table_range_loader import STACK

OUTPUT=0x24000
PLANE=(0x800D35E0,0x800D35E4)
SIZES=dict(base=4,page=1,disabled=1,blocked=2,kind=4,mask=2)
ORDER=('select','initial','transform','query','overlay','final')
VIEWS=(0,1,2,3,7,15,16,31,0x10001,0xFFFF0002,0xFFFFFFFF,0x80008000)


def signed16(value):
    value&=65535
    return value-65536 if value&32768 else value


def fixture(flags,pattern):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x100,0x140)}
    for i in range(-4,132):
        put(memory,OUTPUT+i*4,0xA55A1234^(i&0xFFFFFFFF))
    values=dict(base=(0x80050000,0x7FFFFF80,0xFFFFFFF0)[pattern%3],page=(flags*13)&255,
        disabled=bool(flags&1),blocked=0xFFFF if flags&2 else 0,kind=0x14,mask=0xFFFF if flags&8 else 0)
    for key,value in values.items():
        put(memory,source.GLOBALS[key],value,SIZES[key])
    for address in PLANE:
        put(memory,address,0xA5A51234)
    return memory


def effects(stage,memory,pattern,args):
    if stage=='select':
        for address,value in zip(PLANE,(0x3F000000,0x3F800000)):
            put(memory,address,value)
    elif stage in ('initial','transform','overlay','final'):
        put(memory,args[0],0xAA000000|ORDER.index(stage))
        put(memory,args[0]+4,args[1] if len(args)>1 else 0)
    if stage=='initial':
        if pattern==1:
            put(memory,source.GLOBALS['disabled'],1,1)
        elif pattern==2:
            put(memory,source.GLOBALS['blocked'],0xFFFF,2)
        elif pattern==4:
            put(memory,source.GLOBALS['kind'],7)
    elif stage=='query' and pattern==3:
        put(memory,source.GLOBALS['mask'],read(memory,source.GLOBALS['mask'],2)^65535,2)


def result(stage,flags):
    if stage=='query':
        return 0x80000000 if flags&4 else 0
    return OUTPUT+dict(select=0,initial=0x40,transform=0x80,overlay=0xC0,final=0x100)[stage]


def reference(memory,view,flags,pattern):
    m=dict(memory)
    calls=[]
    narrowed=signed16(view)
    value=narrowed&0xFFFFFFFF
    def call(stage,args):
        calls.append((source.CALLEES[stage],*args))
        effects(stage,m,pattern,args)
        return result(stage,flags)
    call('select',(value,))
    viewport=(read(m,source.GLOBALS['base'])+narrowed*384+read(m,source.GLOBALS['page'],1)*16+64)&0xFFFFFFFF
    put(m,OUTPUT,0xDC080008)
    put(m,OUTPUT+4,viewport)
    cursor=call('initial',(OUTPUT+8,value,0,0,0,0))
    if read(m,source.GLOBALS['disabled'],1) or read(m,source.GLOBALS['blocked'],2):
        return m,cursor,calls
    cursor=call('transform',(cursor,read(m,source.GLOBALS['kind'])))
    if call('query',(value,)):
        return m,cursor,calls
    if read(m,source.GLOBALS['mask'],2)&(1<<(narrowed&31)):
        return m,cursor,calls
    cursor=call('overlay',(cursor,value))
    cursor=call('final',(cursor,value))
    return m,cursor,calls


class DispatchOracle(machine.MaskOracle):
    def __init__(self,words,memory,view,flags,pattern,phase=0,fault=None,connected=None):
        super().__init__(words,memory,phase=phase,entry=source.ENTRY,
            arguments=(OUTPUT,view&0xFFFFFFFF),fault=fault,connected=connected)
        self.flags,self.pattern=flags,pattern
        self.current_pc=self.delay_of=None
        self.code=faults.TrackedCode(self.code,self)
        self.connected_select=bool(connected)

    def access(self):
        if self.own_instruction and source.ENTRY<=self.current_pc<source.ENTRY+source.WORDS*4:
            if self.accesses==self.fault:
                raise machine.AccessFault
            self.accesses+=1

    def record_call(self,target):
        stage=next(name for name,address in source.CALLEES.items() if address==target)
        count=6 if stage=='initial' else 1 if stage in ('select','query') else 2
        args=tuple(self.arguments(count))
        self.calls.append((target,*args))
        self.events.append(('CALL',target,args))

    def hook(self,target):
        stage=next(name for name,address in source.CALLEES.items() if address==target)
        args=self.calls[-1][1:]
        effects(stage,self.memory,self.pattern,args)
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=result(stage,self.flags)


def state(instance):
    return (tuple(instance.r),tuple(instance.f),dict(instance.memory),tuple(instance.events),
        tuple(instance.calls),instance.lo,instance.condition,instance.current_pc,instance.delay_of,instance.accesses)


def external(memory):
    return {a:v for a,v in memory.items() if not STACK-0x100<=a<STACK+0x140}


def native_rows(rows):
    # Preserve C's variable-shift domain; guest cases separately cover low-five-bit MIPS shifts.
    return [(view,flags,pattern) for view,flags,pattern in rows
        if 0<=signed16(view)<32 or flags&7 or pattern in (1,2)]


def native_program(body,rows):
    literal=lambda values:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF) for v in values)+'}'
    cases=[]
    for view,flags,pattern in rows:
        initial=fixture(flags,pattern)
        memory,cursor,calls=reference(initial,view,flags,pattern)
        packets=[]
        for packet in calls:
            arguments=[*packet[1:],*([0]*(7-len(packet)))]
            packets.append('{0x%Xu,%du,%s}'%(packet[0],len(packet)-1,literal(arguments)))
        packets+=['{0,0,{0}}']*(6-len(packets))
        writes=[(i,read(memory,OUTPUT+i*4)) for i in range(128)
            if read(initial,OUTPUT+i*4)!=read(memory,OUTPUT+i*4)]
        assert len(writes)<=10
        changed=','.join(literal(pair) for pair in writes)+(',' if writes else '')+','.join(['{0}']*(10-len(writes)))
        globals_out=[read(memory,source.GLOBALS[key],SIZES[key]) for key in SIZES]
        cases.append('{%s,%s,%s,%s,%s,%s,%s,{%s},%s,{%s},%s}'%(view&0xFFFFFFFF,flags,pattern,
            read(initial,source.GLOBALS['base']),read(initial,source.GLOBALS['page'],1),cursor,len(calls),
            ','.join(packets),len(writes),changed,literal(globals_out)))
    return '''typedef unsigned char u8;typedef short s16;typedef unsigned short u16;typedef int s32;typedef unsigned int u32;
typedef struct{struct{u32 w0,w1;}words;}Gfx;
typedef struct{u32 target,count,args[6];} Packet;
typedef struct{u32 view,flags,pattern,base,page,result,count;Packet calls[6];u32 writes;u32 changes[10][2];u32 globals[6];}Case;
static Case cases[]={'''+',\n'.join(cases)+'''};
static u32 bank[136],calls;static int error;static Case *current;
static s32 D_800BE628,D_800BE9F0;static u8 D_800BE9C0,D_800BEAC0;static s16 D_80084480;static u16 D_800D18A0;
static u32 guest(u32 value){u32 base=(u32)(bank+4);return value>=base&&value<base+512?0x24000u+value-base:value;}
static void packet(u32 target,u32 count,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f){u32 actual[6]={a,b,c,d,e,f},i;
 if(calls>=current->count){error=1;return;}
 if(current->calls[calls].target!=target||current->calls[calls].count!=count)error=2;
 for(i=0;i<count;i++){if(current->calls[calls].args[i]!=actual[i])error=3;}
 calls++;
}
static void paint(s32 cursor,u32 tag,u32 value){u32 *p=(u32*)(u32)cursor;p[0]=0xAA000000u|tag;p[1]=value;}
void func_1510B958(s32 view){packet(0x1510B958,1,(u32)view,0,0,0,0,0);}
s32 func_1501A490(s32 cursor,s16 view,s32 a,s32 b,s32 c,s32 d){
 packet(0x1501A490,6,guest((u32)cursor),(u32)(s32)view,a,b,c,d);paint(cursor,1,(u32)(s32)view);
 if(current->pattern==1)D_800BEAC0=1;else if(current->pattern==2)D_80084480=-1;else if(current->pattern==4)D_800BE9F0=7;
 return (s32)(bank+4+16);}
s32 func_1510FEA0(s32 cursor,s32 kind){packet(0x1510FEA0,2,guest((u32)cursor),(u32)kind,0,0,0,0);paint(cursor,2,(u32)kind);return (s32)(bank+4+32);}
s32 func_1517EFAC(s32 view){packet(0x1517EFAC,1,(u32)view,0,0,0,0,0);if(current->pattern==3)D_800D18A0^=65535;return current->flags&4?(s32)0x80000000u:0;}
s32 func_1515D6D0(s32 cursor,s32 view){packet(0x1515D6D0,2,guest((u32)cursor),(u32)view,0,0,0,0);paint(cursor,4,(u32)view);return (s32)(bank+4+48);}
Gfx *func_1510B9D0(Gfx *cursor,s16 view){packet(0x1510B9D0,2,guest((u32)cursor),(u32)(s32)view,0,0,0,0);paint((s32)cursor,5,(u32)(s32)view);return (Gfx*)(bank+4+64);}
/* Native bridge preserves the SDK viewport command's two integer words, not RDRAM byte order. */
#define gSPViewport(pkt,address) do{Gfx *_g=(pkt);_g->words.w0=0xDC080008u;_g->words.w1=(u32)(address);}while(0)
'''+body+'''
static int run(void){u32 n,i,j,value,result,globals[6];
 if(sizeof(void*)!=4||sizeof(Gfx)!=8)return 90;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  current=&cases[n];calls=0;error=0;
  for(i=0;i<136;i++)bank[i]=0xCAFE1234u;
  for(i=0;i<128;i++)bank[4+i]=0xA55A1234u^i;
  D_800BE628=(s32)current->base;D_800BE9C0=current->page;D_800BEAC0=!!(current->flags&1);
  D_80084480=current->flags&2?-1:0;D_800BE9F0=0x14;D_800D18A0=current->flags&8?65535:0;
  result=guest((u32)func_15019464((Gfx*)(bank+4),(s16)current->view));
  if(error||calls!=current->count||result!=current->result)return 2;
  globals[0]=(u32)D_800BE628;globals[1]=D_800BE9C0;globals[2]=D_800BEAC0;
  globals[3]=(u16)D_80084480;globals[4]=(u32)D_800BE9F0;globals[5]=D_800D18A0;
  for(i=0;i<6;i++)if(globals[i]!=current->globals[i])return 2;
  for(i=0;i<128;i++){value=0xA55A1234u^i;
   for(j=0;j<current->writes;j++)if(current->changes[j][0]==i)value=current->changes[j][1];
   if(bank[4+i]!=value)return 2;}
  for(i=0;i<4;i++)if(bank[i]!=0xCAFE1234u||bank[132+i]!=0xCAFE1234u)return 3;
 }return 0;}
void _start(void){int value=run();__asm__ volatile("int $0x80"::"a"(1),"b"(value));__builtin_unreachable();}
'''
