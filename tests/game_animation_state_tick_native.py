"""Native32 tick fixture with byte-wise expected state and independent truncation."""
def source(body):
    return r'''
typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned short u16;typedef int s32;typedef unsigned int u32;
typedef struct {u8 bytes[64];} struct102;
static u8 *actor,*descriptor;static u8 expected[64],expectedDescriptor[8];static int alias,mutation,callbackCalls,releaseCalls,bad,which;
void(*D_8008CA20[256])(void*);
static int get16(u8*p){unsigned v=(unsigned)p[0]|(unsigned)p[1]<<8;return v<32768?(int)v:(int)v-65536;}
static void set16(u8*p,int v){p[0]=(u8)v;p[1]=(u8)((unsigned)v>>8);}
static int quotient(int v){return v<0?-((-v)>>8):v>>8;}
static u8 *countAt(u8*p,u8*d){return alias?p+(alias==1?0x14:alias==2?0x16:0x23):d+4;}
static void effect(u8*p,u8*d){if(mutation){set16(p+0x14,0x02FF);set16(p+0x16,0x0101);p[0x22]=0xFE;p[0x23]=129;*countAt(p,d)=2;p[0x24]=0;}}
static void update(void*p,int id){if(p!=actor||id!=which)bad=1;callbackCalls++;effect(actor,descriptor);}
static void cb0(void*p){update(p,0);}static void cb1(void*p){update(p,1);}
void func_1516972C(struct102*p){if((u8*)p!=actor)bad=1;releaseCalls++;((u8*)p)[0x3F]=0xEE;}
'''+body+r'''
typedef void(*Handler)(u8*);
__attribute__((noinline))static void invoke(Handler fn,u8*p){fn(p);}
static int run(void){u32 args[6]={0,4096,3,0x22,0xFFFFFFFFu,0},address,i,seed;int index,m,t,rate,remaining,phase,step,count,cost,expectedCallbacks,expectedReleases;
static int phases[]={-32768,-257,-256,-255,-1,0,1,255,256,257,32767};
static int steps[]={-32768,-257,-1,0,1,255,256,32767};
static int corners[][5]={{0,0,-1,0,0},{1,1,0,0,3},{-1,1,512,256,3},{-1,255,512,256,3},{0,0,512,256,3},{0,0,32767,1,1},{-128,128,256,256,2},{-128,129,256,256,2},{-1,255,-1,0,0},{1,0,0,0,255}};
__asm__ volatile("int $0x80":"=a"(address):"a"(90),"b"(args):"memory");if(address>=0xFFFFF000u||sizeof(void*)!=4)return 9;
actor=(u8*)address;descriptor=actor+128;for(i=0;i<256;i++)D_8008CA20[i]=i&1?cb1:cb0;
for(seed=0;seed<1034;seed++)for(index=0;index<2;index++)for(m=0;m<2;m++)for(t=0;t<2;t++){
for(i=0;i<64;i++)actor[i]=(u8)(i*29+seed);for(i=0;i<8;i++)descriptor[i]=(u8)(i*13+seed);
alias=seed<1024?(seed/17)%4:0;mutation=m;actor[0]=3;actor[0x22]=(u8)seed;actor[0x23]=(u8)(seed*37);actor[0x24]=index?(u8)((seed%255)+1):0;
*(u8**)(actor+0x10)=alias?actor+(alias==1?0x10:alias==2?0x12:0x1F):descriptor;
*(s16*)(actor+0x14)=(s16)phases[seed%11];*(s16*)(actor+0x16)=(s16)steps[seed%8];descriptor[4]=(u8)(seed*19);
if(seed>=1024){i=seed-1024;actor[0x22]=(u8)corners[i][0];actor[0x23]=(u8)corners[i][1];*(s16*)(actor+0x14)=(s16)corners[i][2];*(s16*)(actor+0x16)=(s16)corners[i][3];descriptor[4]=(u8)corners[i][4];}
for(i=0;i<64;i++)expected[i]=actor[i];for(i=0;i<8;i++)expectedDescriptor[i]=descriptor[i];
expectedCallbacks=actor[0x24]!=0;which=actor[0x24]&1;if(expectedCallbacks)effect(expected,expectedDescriptor);
rate=expected[0x22]<128?expected[0x22]:(int)expected[0x22]-256;
if(rate>0){remaining=expected[0x23];if(remaining>rate)expected[0x23]=(u8)(remaining-rate);else set16(expected+0x14,(int)*countAt(expected,expectedDescriptor)<<8);}
else if(rate<0){phase=get16(expected+0x14);count=*countAt(expected,expectedDescriptor);cost=-rate;
if(quotient(phase)>=count-1&&expected[0x23]>cost){expected[0x23]=(u8)(expected[0x23]-cost);set16(expected+0x14,phase-get16(expected+0x16));}}
phase=get16(expected+0x14);step=get16(expected+0x16);set16(expected+0x14,phase+step);
expectedReleases=quotient(get16(expected+0x14))>=*countAt(expected,expectedDescriptor);if(expectedReleases)expected[0x3F]=0xEE;
callbackCalls=releaseCalls=bad=0;if(t)invoke(func_15167B44,actor);else func_15167B44(actor);
if(bad||callbackCalls!=expectedCallbacks||releaseCalls!=expectedReleases)return 1;
for(i=0;i<64;i++)if(actor[i]!=expected[i])return 1;for(i=0;i<8;i++)if(descriptor[i]!=expectedDescriptor[i])return 1;
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
