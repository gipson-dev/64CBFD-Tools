"""Run valid, non-overlapping 32-bit source cases and negative controls."""
import subprocess
from tools.experiments import game_camera_state_15125924_direct as packet
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def run():
    function = body(packet.MANIFEST['selected_source'], 'func_15125924')
    controls = {
        'gate': ('+ 0x2C) & 0x40', '+ 0x2C) & 0x20'),
        'camera_gate': ('+ 0x84) & 0x4000', '+ 0x84) & 0x8000'),
        'state_byte': ('+ 0x3D4)[0x4E]', '+ 0x3D4)[0x4F]'),
        'activation': ('camera, 0x80, 1, 1, 13', 'camera, 0x80, 1, 1, 14'),
        'cleanup': ('+ 0x2C) & 0x80', '+ 0x2C) & 0x100'),
        'offset': ('+ 0x344) = offset', '+ 0x344) = 0.0f'),
    }
    # The state pointer is a named field; the remaining camera accesses are byte offsets.
    controls['state_byte'] = ('camera->unk3D4)[0x4E]', 'camera->unk3D4)[0x4F]')
    header = '''#include <ultra64.h>
typedef struct struct108 { u8 pad[0x3D4]; u8 *unk3D4; } struct108;
void *func_15125490(struct108 *);
s32 func_15123934(struct108 *,s32,s32,s32,s32);
void func_15124B18(struct108 *);
s32 func_151239CC(struct108 *,s32);
'''
    code = header + function.replace('func_15125924(', 'selected(', 1)+'\n'
    for name, (old, new) in controls.items():
        assert old in function, name
        code += function.replace('func_15125924(', 'bad_'+name+'(', 1).replace(old, new, 1)+'\n'
    code += r'''
static u32 camera_data[512], expected_data[512], state_data[128], actor_data[128];
static u8 *camera,*state,*actor;static int first,second,mutation,busy,trace[8],count,bad;
void *func_15125490(struct108 *p) {
    if ((u8 *)p != camera) bad=1;
    trace[count++]=1;
    if (mutation) *(u32 *)(camera+0x2C)=0x80;
    return first ? camera : (void *)0;
}
s32 func_15123934(struct108 *p,s32 a,s32 b,s32 c,s32 d) {
    if ((u8 *)p!=camera || a!=0x80 || b!=1 || c!=1 || d!=13) bad=1;
    trace[count++]=2;
    if (mutation) *(u32 *)(camera+0x6C8)=busy;
    return second;
}
void func_15124B18(struct108 *p) {
    if ((u8 *)p!=camera) bad=1;
    trace[count++]=3;
    if (mutation) *(u32 *)(camera+0x5F0)=0x55;
}
s32 func_151239CC(struct108 *p,s32 a) {
    if ((u8 *)p!=camera || a!=13) bad=1;
    trace[count++]=4;
    if (mutation) *(u32 *)(camera+0x5F0)=0x1100;
    return 0;
}
typedef void (*Fn)(struct108 *);
static int check(Fn fn) {
    static const f32 coordinates[]={-1.25f,0.0f,0.9f,1.25f};
    static const u32 flags_values[]={0,0x40,0x80};
    for(int present=0;present<2;present++)for(int flag=0;flag<3;flag++)
    for(int camera_gate=0;camera_gate<2;camera_gate++)for(int enabled=0;enabled<2;enabled++)
    for(int status=0;status<2;status++)for(int coordinate=0;coordinate<4;coordinate++)
    for(int f=0;f<2;f++)for(int s=0;s<2;s++)for(int b=0;b<2;b++)for(int mut=0;mut<2;mut++) {
        for(int i=0;i<512;i++) camera_data[i]=expected_data[i]=0;
        for(int i=0;i<128;i++) state_data[i]=actor_data[i]=0;
        camera=(u8 *)camera_data;state=(u8 *)state_data;actor=(u8 *)actor_data;
        *(u8 **)(camera+0x3D4)=present?state:(u8 *)0;
        *(u8 **)(camera+0x3D0)=actor; *(u32 *)(camera+0x2C)=flags_values[flag];
        *(u32 *)(camera+0x84)=camera_gate?0x4000:0;
        *(u32 *)(camera+0x6C8)=b; *(u32 *)(camera+0x5F0)=0x1000;
        *(f32 *)(camera+0x2FC)=5.5f; *(f32 *)(camera+0x354)=2.25f;
        *(f32 *)(camera+0x344)=-1.f; *(f32 *)(camera+0x348)=-2.f; *(f32 *)(camera+0x190)=3.f;
        *(f32 *)(state+0x1C)=coordinates[coordinate];state[0x4E]=status;actor[0x102]=enabled;
        for(int i=0;i<512;i++)expected_data[i]=camera_data[i];
        u8 *expected=(u8 *)expected_data;int etrace[8],ecount=0;
        first=f;second=s;busy=b;mutation=mut;count=bad=0;
        if (!(flags_values[flag]&0x40) && (camera_gate || enabled)) {
            etrace[ecount++]=1;
            if(mut)*(u32 *)(expected+0x2C)=0x80;
            if(f && (!present || (!status && (s32)coordinates[coordinate]==0))) {
                etrace[ecount++]=2;
                if(mut)*(u32 *)(expected+0x6C8)=b;
                if(s && !*(u32 *)(expected+0x6C8)) {
                    etrace[ecount++]=3;
                    if(mut)*(u32 *)(expected+0x5F0)=0x55;
                    *(u32 *)(expected+0x5F0)|=0x1000;
                }
            } else {
                if(*(u32 *)(expected+0x2C)&0x80) {
                    etrace[ecount++]=4;
                    if(mut)*(u32 *)(expected+0x5F0)=0x1100;
                    *(f32 *)(expected+0x190)=0.f;
                }
                if(*(u32 *)(expected+0x5F0)&0x1000) {
                    f32 x=*(f32 *)(expected+0x2FC)-*(f32 *)(expected+0x354);
                    *(u32 *)(expected+0x5F0)&=~0x1000;
                    *(f32 *)(expected+0x344)=x;*(f32 *)(expected+0x348)=x;
                }
            }
        }
        fn((struct108 *)camera);
        if(bad || count!=ecount)return 1;
        for(int i=0;i<count;i++)if(trace[i]!=etrace[i])return 1;
        for(int i=0;i<512;i++)if(camera_data[i]!=expected_data[i])return 1;
    }
    return 0;
}
static int run(void) {
    if(check(selected))return 10;
'''
    for i, name in enumerate(controls):
        code += 'if(!check(bad_'+name+'))return '+str(20+i)+';\n'
    code += 'return 0; }\n'+START.replace('void _start(void)', '__attribute__((force_align_arg_pointer)) void _start(void)')
    path = packet.OUT/'native.c'
    path.write_text(code)
    for opt in ('-O0', '-O2', '-O3'):
        executable = packet.OUT/('native'+opt)
        result = subprocess.run(native_command(opt)+['-fno-strict-aliasing', str(path), '-o', str(executable)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        result = subprocess.run([str(executable)], capture_output=True)
        assert result.returncode == 0, (opt, result.returncode, result.stderr)
