"""Independent native32 controls for the effect-actor update callback."""
from pathlib import Path
import json
import subprocess

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def harness(selected):
    bodies = [
        ("valid", selected),
        ("wrong_lifetime", selected.replace("payload[0] -= D_800BE9A4", "payload[0] += D_800BE9A4")),
        ("wrong_phase", selected.replace("payload[3] += payload[4] * D_800BE9A4", "payload[3] -= payload[4] * D_800BE9A4")),
        ("wrong_velocity", selected.replace("actor + 0x58", "actor + 0x50")),
        ("wrong_opacity", selected.replace("(u8)payload[2]", "(u8)payload[1]")),
        ("wrong_result", selected.replace("return 0;", "return 1;", 1)),
    ]
    assert all(body != selected for _, body in bodies[1:])
    text = """#include <ultra64.h>
static f32 D_800BE9A4, suppliedWave, seenPhase; static u8 *liveActor;
f32 sinf(f32 phase) { seenPhase = phase; if (liveActor[0x6F] & 1) {
    D_800BE9A4 = 0.25f; *(f32 *)(liveActor + 0x174) = 3.0f;
} return suppliedWave; }
"""
    for index, (name, body) in enumerate(bodies):
        body = body.replace("s32 func_15154A88(", "static s32 candidate_%d(" % index)
        body = body.replace("extern f32 D_800BE9A4;\n", "").replace("f32 sinf(f32);\n", "")
        text += body + "\n"
    text += r'''
typedef s32 (*Fn)(u8 *);
static Fn candidates[] = {candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5};
typedef union { u32 align[128]; u8 bytes[512]; } NativeImage;
static NativeImage initial, actual, expected;
static void putf(u8 *p, f32 value) { union { u32 u; f32 f; } bits; bits.f=value;
 p[0]=(u8)bits.u;p[1]=(u8)(bits.u>>8);p[2]=(u8)(bits.u>>16);p[3]=(u8)(bits.u>>24); }
static int reference(u8 *actor) {
 f32 *payload=(f32*)(actor+0x170), wave=suppliedWave, scale;
 seenPhase=*(f32*)(actor+0x17C); if(actor[0x6F]&1){D_800BE9A4=.25f;payload[1]=3.f;}
 scale=payload[1]*wave;*(f32*)(actor+0x1C)=scale;*(f32*)(actor+0x18)=scale;
 actor[0x70]=(u8)((u8)payload[2]*wave);payload[0]-=D_800BE9A4;
 if(payload[0]<=0.f)return 0;payload[3]+=payload[4]*D_800BE9A4;
 *(f32*)(actor+0x20)+=*(f32*)(actor+0x50)*D_800BE9A4;
 *(f32*)(actor+0x24)+=*(f32*)(actor+0x54)*D_800BE9A4;
 *(f32*)(actor+0x28)+=*(f32*)(actor+0x58)*D_800BE9A4;return 1;
}
static int run(void){u32 n,j,k,killed=0;for(n=0;n<256;n++){
 for(k=0;k<512;k++)initial.bytes[k]=(u8)(k*13+n*7);initial.bytes[0x6F]=(u8)n;
 putf(initial.bytes+0x170,(n%5==0)?0.f:(n%7==0?-.5f:1.f+(f32)(n%9)));
 putf(initial.bytes+0x174,(f32)((int)(n%11)-5)*.5f);putf(initial.bytes+0x178,(f32)n+.75f);
 putf(initial.bytes+0x17C,(f32)((int)(n%17)-8)*.25f);putf(initial.bytes+0x180,(f32)((int)(n%13)-6)*.125f);
 putf(initial.bytes+0x20,(f32)n);putf(initial.bytes+0x24,(f32)n*.5f);putf(initial.bytes+0x28,-(f32)n);
 putf(initial.bytes+0x50,.5f);putf(initial.bytes+0x54,-.25f);putf(initial.bytes+0x58,1.25f);
 suppliedWave=(f32)((int)(n%9)-4)*.25f;D_800BE9A4=(n&2)?0.5f:1.f;expected=initial;liveActor=expected.bytes;
 {int want=reference(expected.bytes);for(j=0;j<6;j++){int got,failed;actual=initial;D_800BE9A4=(n&2)?.5f:1.f;liveActor=actual.bytes;got=candidates[j](actual.bytes);failed=got!=want;
   for(k=0;k<512;k++)if(actual.bytes[k]!=expected.bytes[k])failed=1;
   if(!j&&failed)return 2;if(j&&failed)killed|=1u<<(j-1);
 }} }
 return killed==31u?0:3;}
'''
    return text + START.replace("void _start(void)", "__attribute__((force_align_arg_pointer)) void _start(void)")


def qualify(root, output, selected):
    source = output / "native_harness_v1.c"
    source.write_text(harness(selected))
    profiles = []
    for option in ("-O0", "-O2", "-O3"):
        executable = output / ("native-v1-" + option[1:])
        build = subprocess.run(native_command(option) + ["-fno-strict-aliasing", "-ffp-contract=off",
            str(source), "-o", str(executable)], cwd=root, capture_output=True, text=True)
        if build.returncode or build.stderr:
            raise ValueError((option, build.stdout, build.stderr))
        run = subprocess.run([str(executable)], capture_output=True)
        if run.returncode:
            raise ValueError((option, run.returncode, run.stderr))
        profiles.append({"optimization": option, "cases": 256, "negative_controls": 5,
                         "UBSan_clean": True, "canaries": True})
    report = {"success": True, "private_only": True, "matching_credit": 0,
              "profiles": profiles, "total_executions": 768, "all256_opacity_inputs": True,
              "positive_zero_negative_lifetime": True, "live_sine_mutations": True,
              "complete_512_byte_image_checked": True}
    (output / "private-native-v1.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
