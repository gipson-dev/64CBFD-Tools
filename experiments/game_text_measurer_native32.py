"""Native 32-bit measurer with full recovered helpers and byte-addressed fixtures."""
from tools.experiments import game_character_normalizer_candidates as lookup
from tools.experiments import game_extended_character_metrics_candidates as metrics
from tools.tests.test_game_row_destination_fill import START


FIXTURE = r'''
typedef unsigned char u8;typedef int s32;typedef unsigned int u32;typedef float f32;
#define NULL ((void *)0)
typedef char widths[(sizeof(void *)==4 && sizeof(s32)==4 && sizeof(f32)==4)?1:-1];
static u8 textStorage[320] __attribute__((aligned(16)));
static u8 fontStorage[1088] __attribute__((aligned(16)));
static u8 outputsStorage[128] __attribute__((aligned(16)));
static u8 parameters[28] __attribute__((aligned(16)));
#define nativeText (textStorage+32)
#define nativeFont (fontStorage+32)
#define nativeOutputs (outputsStorage+32)
#define D_800380A0 (*(f32 *)(parameters+0))
#define D_800380A4 (*(f32 *)(parameters+4))
#define D_80098AFC (*(f32 *)(parameters+8))
#define D_80098B00 (*(f32 *)(parameters+12))
#define D_80098B04 (*(f32 *)(parameters+16))
#define D_80098B08 (*(f32 *)(parameters+20))
#define D_80098B0C (*(f32 *)(parameters+24))
static u8 *D_80085994;
static u8 normalizerStorage[160]={INITIAL_TABLE};
static const u8 expectedNormalizer[160]={INITIAL_TABLE};
#define normalizer (normalizerStorage+32)
#define D_80085930 normalizer[0]
#define D_80085931 normalizer[1]
#define D_80085932 normalizer[2]
#define D_80085933 (normalizer+3)
typedef struct {
    u8 textBytes[256],fontBytes[1024],outputsBytes[64],parametersBytes[28];
    u8 expectedText[256],expectedFont[1024],expectedOutputs[64],expectedParameters[28];
    u32 nullText;s32 *pointers[3];
} Case;
static void copy(u8 *to,const u8 *from,u32 size) {u32 i;for(i=0;i<size;i++)to[i]=from[i];}
static void fill(u8 *to,u32 size) {u32 i;for(i=0;i<size;i++)to[i]=0xA5;}
static int report(u32 code,u32 c,u32 i) {
    u32 data[3]={code,c,i};s32 result;
    __asm__ volatile("int $0x80":"=a"(result):"a"(4),"b"(2),"c"(data),"d"(sizeof(data)):"memory");
    return (s32)code;
}
'''

RUNNER = r'''
int run(void) {
    u32 c,i;const Case *test;
    for(c=0;c<sizeof(cases)/sizeof(cases[0]);c++) {
        test=cases+c;
        fill(textStorage,sizeof(textStorage));fill(fontStorage,sizeof(fontStorage));
        fill(outputsStorage,sizeof(outputsStorage));
        copy(nativeText,test->textBytes,256);copy(nativeFont,test->fontBytes,1024);
        copy(nativeOutputs,test->outputsBytes,64);copy(parameters,test->parametersBytes,28);
        D_80085994=nativeFont;
        func_150428D4(test->nullText?NULL:nativeText,test->pointers[0],test->pointers[1],test->pointers[2]);
        for(i=0;i<256;i++)if(nativeText[i]!=test->expectedText[i])return report(1,c,i);
        for(i=0;i<1024;i++)if(nativeFont[i]!=test->expectedFont[i])return report(2,c,i);
        for(i=0;i<64;i++)if(nativeOutputs[i]!=test->expectedOutputs[i])return report(3,c,i);
        for(i=0;i<28;i++)if(parameters[i]!=test->expectedParameters[i])return report(4,c,i);
        if(D_80085994!=nativeFont)return report(5,c,0);
        for(i=0;i<160;i++)if(normalizerStorage[i]!=expectedNormalizer[i])return report(9,c,i);
        for(i=0;i<32;i++) {
            if(textStorage[i]!=0xA5 || textStorage[288+i]!=0xA5)return report(6,c,i);
            if(fontStorage[i]!=0xA5 || fontStorage[1056+i]!=0xA5)return report(7,c,i);
            if(outputsStorage[i]!=0xA5 || outputsStorage[96+i]!=0xA5)return report(8,c,i);
        }
    }
    return 0;
}
'''


def source(body,table,cases,regions,parameters):
    assert len(table)==96 and len(parameters)==7
    def array(memory,addresses):
        return '{'+','.join(str(memory[a]) for a in addresses)+'}'
    def pointer(address):
        for base,size,name in regions:
            if base<=address<base+size:
                assert address%4==0
                return '(s32 *)('+name+'+%d)'%(address-base)
        assert address in parameters
        return '(s32 *)(parameters+%d)'%(parameters.index(address)*4)
    addresses=[[base+i for i in range(size)] for base,size,name in regions]
    addresses.append([a+i for a in parameters for i in range(4)])
    initial=[]
    for memory,args,expected in cases:
        fields=[array(data,region) for data in (memory,expected) for region in addresses]
        fields.extend((str(int(args[0]==0)),'{'+','.join(pointer(a) for a in args[1:])+'}'))
        initial.append('{'+','.join(fields)+'}')
    fixture=FIXTURE.replace('INITIAL_TABLE',','.join(str(v) for v in bytes([0xA5]*32)+table+bytes([0xA5]*32)))
    # These are the complete recovered C helper bodies, not result hooks.
    helpers=lookup.SELECTED+'\n'+metrics.SELECTED+'\n'
    # Keep retail's redundant upper-bound test on the narrowed byte.
    measured='#pragma GCC diagnostic push\n#pragma GCC diagnostic ignored "-Wtype-limits"\n'+body+'\n#pragma GCC diagnostic pop\n'
    return fixture+helpers+measured+'\nstatic const Case cases[]={\n'+',\n'.join(initial)+'\n};\n'+RUNNER+START
