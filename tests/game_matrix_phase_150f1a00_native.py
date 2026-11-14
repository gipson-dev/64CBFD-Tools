"""Native32 UB-trapping tests for the uncredited matrix-phase candidate."""
import json,subprocess
from tools.experiments import game_matrix_phase_150f1a00_screen as source
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

HARNESS='''
PhaseRates D_80088B00;
s16 D_800CC298[12];
s32 D_800BE9E4;
f32 D_800A18E8 = .125f, D_800A18EC = 2.0f, D_800A18F0 = .5f;
static u32 actorWords[0x330 / 4];
static f32 matrixA[16], matrixB[16], expectedA[16], expectedB[16];
static f32 cosResult, expectedArgument;
static int doMutation, calls, badArgument;
static u32 floatbits(f32 value) { union { f32 f; u32 u; } v; v.f = value; return v.u; }
f32 cosf(f32 angle) {
    calls++;
    if (floatbits(angle) != floatbits(expectedArgument)) badArgument = 1;
    if (doMutation) actorWords[0x1d4 / 4] = (u32)matrixB - 0xf80u;
    return cosResult;
}
static int run(void) {
    static const u32 flags[] = {0,3,12,15,7};
    static const s16 phases[] = {-32768,-1,0,32767};
    static const u32 ticks[] = {0,1,0x7fffffffu,0xffffffffu};
    static const f32 cosines[] = {-1.0f,0.0f,1.0f};
    int cases = 0;
    D_80088B00.values[0]=3; D_80088B00.values[1]=19; D_80088B00.values[2]=0xfffe;
    for (int fi=0;fi<5;fi++) for (int p=0;p<4;p++) for (int t=0;t<4;t++)
    for (int c=0;c<3;c++) for (int mutation=0;mutation<2;mutation++) {
        u32 f=flags[fi]; int index=(f&12u)==12u?2:(f&3u)==3u?1:0;
        s16 phase=(s16)((u32)(s32)phases[p]+(u32)D_80088B00.values[index]*ticks[t]);
        f32 scale=((cosines[c]+1.0f)*.5f*D_800A18EC)+D_800A18F0;
        f32 *expected=mutation?expectedB:expectedA;
        for(int i=0;i<16;i++) matrixA[i]=matrixB[i]=expectedA[i]=expectedB[i]=(f32)(i-7)*.25f;
        for(int row=0;row<3;row++)for(int col=0;col<3;col++)expected[row*4+col]*=scale;
        actorWords[0x2e4/4]=f; actorWords[0x1d4/4]=(u32)matrixA-0xf80u;
        D_800CC298[10]=phases[p]; D_800BE9E4=(s32)ticks[t];
        cosResult=cosines[c];expectedArgument=(f32)phase*D_800A18E8;
        doMutation=mutation; calls=badArgument=0;
        func_150F1A00((u8 *)actorWords);
        if (calls!=1 || badArgument || D_800CC298[10]!=phase) return 1;
        for(int i=0;i<16;i++)
            if(floatbits(matrixA[i])!=floatbits(expectedA[i]) || floatbits(matrixB[i])!=floatbits(expectedB[i])) return 2;
        cases++;
    }
    return cases==480?0:3;
}
'''

def run_variant(label,body,opt,alias):
    path=source.OUT/(label+'.c');exe=source.OUT/(label+'-'+opt[1:]+'-'+alias)
    path.write_text('#include <ultra64.h>\n'+body+'\n'+HARNESS+START)
    cmd=native_command(opt)+['-fstrict-aliasing' if alias=='strict' else '-fno-strict-aliasing',str(path),'-o',str(exe)]
    build=subprocess.run(cmd,capture_output=True,text=True)
    if build.returncode:raise ValueError((label,build.stderr))
    return subprocess.run([str(exe)],capture_output=True,text=True).returncode

def verify():
    scale='    scale = ((cosf((f32)D_800CC298[10] * D_800A18E8) + 1.0f) * 0.5f * D_800A18EC) + D_800A18F0;'
    matrix='    matrix = (f32 *)(*(u32 *)(actor + 0x1d4) + 0xf80);'
    controls={
      'priority':('(flags & 12) == 12','(flags & 12) == 8'),
      'rate':('rates.values[kind] * (u32)D_800BE9E4','(rates.values[kind] + 1u) * (u32)D_800BE9E4'),
      'early-matrix':(scale+'\n'+matrix,matrix+'\n'+scale),
      'four-columns':('col < 3','col < 4'),
    }
    for opt in ('-O0','-O2','-O3'):
      for alias in ('strict','no-strict'):
        assert run_variant('native-candidate',source.NEW,opt,alias)==0,(opt,alias)
        for name,(old,new) in controls.items():
          assert source.NEW.count(old)==1
          assert run_variant('native-'+name,source.NEW.replace(old,new),opt,alias)!=0,(opt,alias,name)
    return {'cases_per_configuration':480,'optimizations':3,'alias_modes':2,'negative_controls':list(controls),'ubsan':True,'uncredited':True}

if __name__=='__main__':print(json.dumps(verify()),flush=True)
