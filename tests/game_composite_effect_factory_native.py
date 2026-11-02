"""Native32 semantic, extent and effective-control qualification for func_15152B38."""
from pathlib import Path
import json
import subprocess


def qualify(root, output, source, headers):
    prefix = (
        "typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;"
        "typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;\n"
        + "\n".join(headers.splitlines()[1:])
        + "\n"
    )
    suffix = r'''
typedef struct {u32 mode,extra,seed,mutation;CompositeEffectInput before;} TestCase;
static TestCase current;
static CompositeEffectInput live,expectedLive;
static CompositeEffectHeader expectedHeaders[8];
static CompositeEffectPacket expectedPackets[8];
static u32 expectedCount,expectedIntegers,expectedReals,integerIndex,realIndex,submitIndex,bad;
static u32 ub(f32 value){union{f32 f;u32 u;}x;x.f=value;return x.u;}
static u32 rngInteger(u32 index,u32 seed){static const u32 values[4]={0,1,255,0xFFFFFFFFu};return values[(index+seed)&3];}
static f32 rngReal(u32 index,u32 seed){static const f32 values[4]={0.0f,0.25f,0.5f,0.75f};return values[(index+seed)&3];}
static void setFields(CompositeEffectInput *p,u32 late){u32 i;
 p->baseCount=1+(s32)((current.seed+late)&1);p->countRange=1;
 p->position.x=late?-8.0f:1.25f;p->position.y=late?9.0f:-2.5f;p->position.z=late?-10.0f:3.75f;
 p->field14Base=late?1.0f:2.0f;p->field18Range=late?2.0f:4.0f;p->field1CBase=late?3.0f:.75f;p->field20Range=late?5.0f:3.0f;
 p->radiusBase=late?6.0f:1.5f;p->radiusRange=late?7.0f:2.5f;
 p->firstBase=late?-12:-30;p->firstRange=late?20:60;p->secondBase=late?6:15;p->secondRange=late?18:45;
 p->headerByteBase=late?17:7;p->headerByteRange=late?3:5;p->headerShortBase=late?-9:20;p->headerShortRange=late?7:8;
 p->field40=(u16)(late?0xB123:0x8123);p->fixed42=(u8)(late?0x31:0x11);p->fixed43=(u8)(late?0x42:0x22);p->fixed44=(u8)(late?0x53:0x33);
 p->byteBase45=(u8)(late?50:20);p->byteBase46=(u8)(late?51:21);p->byteBase47=(u8)(late?52:22);p->byteBase48=(u8)(late?53:23);
 p->byteRange49=3;p->byteRange4A=4;p->byteRange4B=5;p->byteRange4C=6;
 p->byteBase4D=(u8)(late?100:80);p->byteBase4E=(u8)(late?101:81);p->byteBase4F=(u8)(late?102:82);p->byteBase50=(u8)(late?103:83);
 p->byteRange51=4;p->byteRange52=5;p->byteRange53=6;p->byteRange54=7;p->byteBase55=(u8)(late?120:100);p->byteRange56=9;
 p->fixed57=(u8)(late?0x64:0x44);p->fixed58=(u8)(late?0x75:0x55);p->field5C=late?0x12345678:(s32)0x89ABCDEFu;p->field60=late?0x23456789:0x76543210;
 p->field64=(s16)(late?-1234:1234);p->field66=(s16)(late?2345:-2345);p->field68=(s16)(late?-3456:3456);p->field6A=(u8)(late?0x9A:0x6A);
 p->field6C=late?8.0f:4.5f;p->field70=(s8)(late?-17:17);p->field71=(s8)(late?29:-29);(void)i;
}
static void mutate(CompositeEffectInput *p,u32 late){if(current.mutation&(late?2u:1u))setFields(p,1);}
static void writeVector(s16 first,s16 second,f32 radius,f32 *out){out[0]=(f32)first*.125f;out[1]=(f32)second*.25f;out[2]=radius*.5f;}
static void reference(void){CompositeEffectInput input=current.before;CompositeEffectScratch scratch;u32 remaining,first,second,ni=0,nf=0,n=0;
 first=rngInteger(ni++,current.seed);mutate(&input,0);remaining=first%((u32)input.countRange+1u)+(u32)input.baseCount;
 scratch.header.position=input.position;scratch.header.fieldE=input.field40;scratch.header.constant10=10;
 scratch.packet.fixed14=input.fixed42;scratch.packet.fixed15=input.fixed43;scratch.packet.fixed16=input.fixed44;scratch.packet.fixed20=input.fixed57;scratch.packet.fixed21=input.fixed58;
 scratch.packet.field24=input.field5C;scratch.packet.field28=input.field60;scratch.packet.field2C=input.field64;scratch.packet.field2E=input.field66;scratch.packet.field38=input.field70;scratch.packet.field39=input.field71;scratch.packet.field30=input.field68;scratch.packet.field32=input.field6A;scratch.packet.field34=input.field6C;
 while(remaining){
  first=rngInteger(ni++,current.seed);scratch.header.random15=(s8)(first%((u32)input.headerByteRange+1u)+(u32)input.headerByteBase);
  first=rngInteger(ni++,current.seed);scratch.header.randomC=(s16)(first%(u32)(input.headerShortRange+1)+input.headerShortBase);
  scratch.packet.field0=rngReal(nf++,current.seed)*input.field18Range+input.field14Base;scratch.packet.field10=rngReal(nf++,current.seed)*input.field20Range+input.field1CBase;
  first=rngInteger(ni++,current.seed);second=rngInteger(ni++,current.seed);writeVector((s16)(first%(u32)(input.firstRange+1)+input.firstBase),(s16)(second%(u32)(input.secondRange+1)+input.secondBase),rngReal(nf++,current.seed)*input.radiusRange+input.radiusBase,scratch.packet.direction);
  first=rngInteger(ni++,current.seed);scratch.packet.random17=(s8)(first%((u32)input.byteRange49+1u)+input.byteBase45);
  first=rngInteger(ni++,current.seed);scratch.packet.random18=(s8)(first%((u32)input.byteRange4A+1u)+input.byteBase46);
  first=rngInteger(ni++,current.seed);scratch.packet.random19=(s8)(first%((u32)input.byteRange4B+1u)+input.byteBase47);
  first=rngInteger(ni++,current.seed);scratch.packet.random1A=(s8)(first%((u32)input.byteRange4C+1u)+input.byteBase48);
  first=rngInteger(ni++,current.seed);scratch.packet.random1B=(s8)(first%((u32)input.byteRange51+1u)+input.byteBase4D);
  first=rngInteger(ni++,current.seed);scratch.packet.random1C=(s8)(first%((u32)input.byteRange52+1u)+input.byteBase4E);
  first=rngInteger(ni++,current.seed);scratch.packet.random1D=(s8)(first%((u32)input.byteRange53+1u)+input.byteBase4F);
  first=rngInteger(ni++,current.seed);scratch.packet.random1E=(s8)(first%((u32)input.byteRange54+1u)+input.byteBase50);
  first=rngInteger(ni++,current.seed);scratch.packet.random1F=(s8)(first%((u32)input.byteRange56+1u)+input.byteBase55);
  expectedHeaders[n]=scratch.header;expectedPackets[n]=scratch.packet;n++;mutate(&input,1);remaining--;
 }
 expectedCount=n;expectedIntegers=ni;expectedReals=nf;expectedLive=input;
}
static int sameHeader(const CompositeEffectHeader *a,const CompositeEffectHeader *b){return ub(a->position.x)==ub(b->position.x)&&ub(a->position.y)==ub(b->position.y)&&ub(a->position.z)==ub(b->position.z)&&a->randomC==b->randomC&&a->fieldE==b->fieldE&&a->constant10==b->constant10&&a->random15==b->random15;}
static int samePacket(const CompositeEffectPacket *a,const CompositeEffectPacket *b){u32 i;
 if(ub(a->field0)!=ub(b->field0)||ub(a->field10)!=ub(b->field10)){return 0;}
 for(i=0;i<3;i++){if(ub(a->direction[i])!=ub(b->direction[i]))return 0;}
 if(a->fixed14!=b->fixed14||a->fixed15!=b->fixed15||a->fixed16!=b->fixed16||a->random17!=b->random17||a->random18!=b->random18||a->random19!=b->random19||a->random1A!=b->random1A||a->random1B!=b->random1B||a->random1C!=b->random1C||a->random1D!=b->random1D||a->random1E!=b->random1E||a->random1F!=b->random1F)return 0;
 return a->fixed20==b->fixed20&&a->fixed21==b->fixed21&&a->field24==b->field24&&a->field28==b->field28&&a->field2C==b->field2C&&a->field2E==b->field2E&&a->field30==b->field30&&a->field32==b->field32&&ub(a->field34)==ub(b->field34)&&a->field38==b->field38&&a->field39==b->field39;
}
s32 func_150ADA20(void){u32 value=rngInteger(integerIndex++,current.seed);if(integerIndex==1)mutate(&live,0);return(s32)value;}
f32 func_150ADA68(void){return rngReal(realIndex++,current.seed);}
void func_15143794(s16 first,s16 second,f32 radius,f32 *out){writeVector(first,second,radius,out);}
s32 func_1515C2F0(CompositeEffectHeader *header,s32 zeroA,CompositeEffectPacket *packet,s32 zeroB,u8 mode,s32 extra){
 if(submitIndex>=expectedCount||zeroA||zeroB||mode!=(u8)current.mode||(u32)extra!=current.extra||!sameHeader(header,&expectedHeaders[submitIndex])||!samePacket(packet,&expectedPackets[submitIndex]))bad=1;
 submitIndex++;mutate(&live,1);return 0x76543210;
}
static void initialize(u32 mode){u32 i;u8 *p=(u8*)&current.before;for(i=0;i<sizeof(current.before);i++)p[i]=(u8)(i*29+mode*13+91);current.mode=mode;current.extra=mode*0x87654321u;current.seed=mode&3;current.mutation=mode&3;setFields(&current.before,0);}
static void(*volatile invoke)(CompositeEffectInput*,u8,s32)=func_15152B38;
int run(void){u32 mode,i;u8 *a,*b;
 if(sizeof(void*)!=4||sizeof(CompositeEffectInput)!=116||sizeof(CompositeEffectPacket)!=60||sizeof(CompositeEffectHeader)!=24||sizeof(CompositeEffectScratch)!=88||__builtin_offsetof(CompositeEffectScratch,packet)!=0||__builtin_offsetof(CompositeEffectScratch,header)!=60||__builtin_offsetof(CompositeEffectScratch,privateTail54)!=84)return 9;
 for(mode=0;mode<256;mode++){initialize(mode);reference();live=current.before;integerIndex=realIndex=submitIndex=bad=0;invoke(&live,(u8)current.mode,(s32)current.extra);
  if(bad||submitIndex!=expectedCount||integerIndex!=expectedIntegers||realIndex!=expectedReals){return 1;}
  a=(u8*)&live;b=(u8*)&expectedLive;for(i=0;i<sizeof(live);i++){if(a[i]!=b[i])return 1;}
 }return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    cached = source.replace(
        "void func_15152B38(CompositeEffectInput *input, u8 mode, s32 extra) {",
        "void func_15152B38(CompositeEffectInput *input, u8 mode, s32 extra) {\n    CompositeEffectInput cached = *input;",
    ).replace("input->", "cached.")
    controls = {
        "selected": (source, headers),
        "unsigned-RNG": (source.replace("(u32)func_150ADA20()", "((u32)func_150ADA20() & 0x7FFFFFFFU)"), headers),
        "count": (source.replace("(u32)input->baseCount", "((u32)input->baseCount + 1U)"), headers),
        "header-byte": (source.replace("(u32)input->headerByteBase", "((u32)input->headerByteBase + 1U)"), headers),
        "header-short": (source.replace("input->headerShortBase", "(input->headerShortBase + 1)"), headers),
        "field0": (source.replace("input->field14Base", "input->field1CBase"), headers),
        "first-angle": (source.replace("input->firstBase", "(input->firstBase + 1)"), headers),
        "first-byte": (source.replace("input->byteBase45", "(input->byteBase45 + 1)"), headers),
        "mode": (
            source.replace(
                "void func_15152B38(CompositeEffectInput *input, u8 mode, s32 extra) {",
                "void func_15152B38(CompositeEffectInput *input, u8 mode, s32 extra) {\n    (void)mode;",
            ).replace("(u8)mode, extra", "(u8)0, extra"),
            headers,
        ),
        "extra": (
            source.replace(
                "void func_15152B38(CompositeEffectInput *input, u8 mode, s32 extra) {",
                "void func_15152B38(CompositeEffectInput *input, u8 mode, s32 extra) {\n    (void)extra;",
            ).replace("(u8)mode, extra", "(u8)mode, 0"),
            headers,
        ),
        "cached-input": (cached, headers),
        "scratch-extent": (source, headers.replace("privateTail54[4]", "privateTail54[8]")),
    }
    assert all(body != source or name in ("selected", "scratch-extent") for name, (body, _) in controls.items())
    results = []
    for opt in ("-O0", "-O2", "-O3"):
        for label, (body, head) in controls.items():
            path = output / ("native-{}-{}.c".format(label, opt[1:]))
            path.write_text(prefix.split("\n", 1)[0] + "\n" + "\n".join(head.splitlines()[1:]) + "\n" + body + "\n" + suffix)
            binary = path.with_suffix(".bin")
            command = [
                "cc", "-m32", opt, "-std=c11", "-msse2", "-mfpmath=sse", "-mstackrealign",
                "-fexcess-precision=standard", "-fno-builtin", "-fno-strict-aliasing", "-ffp-contract=off",
                "-ffreestanding", "-static", "-fno-stack-protector", "-fno-pie", "-no-pie", "-nostdlib",
                "-Wall", "-Wextra", "-Werror", "-fsanitize=undefined", "-fsanitize-undefined-trap-on-error",
                "-Wl,-e,_start", "-o", str(binary), str(path),
            ]
            compiled = subprocess.run(command, cwd=root, capture_output=True, text=True)
            assert compiled.returncode == 0, (opt, label, compiled.stderr[-8000:])
            executed = subprocess.run([str(binary)], capture_output=True, timeout=20)
            assert (executed.returncode == 0) == (label == "selected"), (opt, label, executed.returncode)
            results.append(dict(profile=opt, label=label, status=executed.returncode))
    report = dict(
        success=True,
        cases_per_profile=256,
        profiles=["O0", "O2", "O3"],
        effective_controls_each=len(controls) - 1,
        input_size=116,
        packet_visible_bytes=58,
        packet_private_extent=60,
        header_visible_bytes=22,
        header_private_extent=24,
        complete_scratch_bytes=88,
        private_tail_not_read_by_submit=True,
        all256_mode_bytes=True,
        full_32bit_extra=True,
        unsigned_count_and_RNG=True,
        signed_angle_and_header_short_fields=True,
        nine_random_byte_channels=True,
        live_input_after_first_RNG_and_submit=True,
        finite_float_domain=True,
        UBSan=True,
        results=results,
    )
    (output / "private-native-v7.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    output = Path(__file__).parent
    print(qualify(Path.cwd(), output, (output / "selected-input.c").read_text(), (output / "selected-headers.c").read_text()), flush=True)
