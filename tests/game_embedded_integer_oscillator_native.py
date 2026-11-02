"""Native32 typed owner, live RNG effects, modulo arithmetic and float steps."""
import json
import subprocess

def qualify(root, output, source, headers, oracle):
    rows = []
    for c in oracle.cases():
        if c.alias or c.phase or c.mutation & ~3:
            continue
        _, s, _ = oracle.programs(output, 0, 0)
        initial = oracle.fixture(c, s)
        expected, calls, result = oracle.reference(initial, c, s)
        p = oracle.OWNER
        offsets = ((0xB4,1),(0xC4,2),(0xC6,2),(0xC8,2),(0xB8,4),(0xBC,4),(0xC0,4),(0xCC,4),(0x24,4))
        values = [oracle.read(initial,p+at,n) for at,n in offsets]
        wanted = [oracle.read(expected,p+at,n) for at,n in offsets]
        values += [c.rng,c.random,c.mutation,c.ticks]
        wanted += [result,len(calls),oracle.read(expected,s['clock'])]
        rows.append('{{%s},{%s}}' % (','.join('0x%Xu'%v for v in values),','.join('0x%Xu'%v for v in wanted)))
    prefix = headers.replace('#include <ultra64.h>', 'typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned short u16;typedef int s32;typedef unsigned int u32;typedef float f32;')
    prefix += r'''
typedef struct {u8 head[0x24];s32 value;u8 middle[0x88];EmbeddedIntegerOscillator oscillator;} Owner;
struct Packet {u32 before[4];Owner owner;u32 after[4];};
struct Case {u32 initial[13],wanted[12];};
static const struct Case cases[]={ROWS};
static struct Packet packet;
static const struct Case *current;
static u32 calls,bad;
s32 D_800BE9E4;
static f32 fl(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static u32 ub(f32 v){union{u32 u;f32 f;}x;x.f=v;return x.u;}
__attribute__((noipa)) s32 func_150ADA20(void){
 EmbeddedIntegerOscillator *o=&packet.owner.oscillator;
 if(calls++!=0||o->notification!=0)bad=1;
 if(current->initial[11]&1){o->notification=165;o->minimum=-123;o->range=7;o->amplitude=6.;o->base=-17.;packet.owner.value=77;o->gain=.125;D_800BE9E4=(s32)0x87654321u;}
 return (s32)current->initial[9];
}
__attribute__((noipa)) f32 func_150ADA68(void){
 EmbeddedIntegerOscillator *o=&packet.owner.oscillator;
 if(calls++!=1)bad=1;
 if(current->initial[11]&2){o->base=11.;o->amplitude=-8.;o->gain=.25;packet.owner.value=1000;o->remaining=-7;}
 return fl(current->initial[10]);
}
'''.replace('ROWS', ','.join(rows))
    suffix = r'''
static int report(u32 category,u32 i,u32 k,s32 result){
 u32 v[19]={category,i,k,(u32)result,calls,bad,(u32)D_800BE9E4,packet.owner.oscillator.notification,(u16)packet.owner.oscillator.remaining,(u16)packet.owner.oscillator.minimum,(u16)packet.owner.oscillator.range,ub(packet.owner.oscillator.base),ub(packet.owner.oscillator.amplitude),ub(packet.owner.oscillator.target),ub(packet.owner.oscillator.gain),(u32)packet.owner.value,0,0,0};
 __asm__ volatile("int $0x80"::"a"(4),"b"(1),"c"(v),"d"(sizeof(v)):"memory");return 1;
}
static s32 (*volatile functions[2])(u8*)={func_150C5E0C,func_151AB090};
int run(void){u32 i,j,k;u8 *bytes=(u8*)&packet;EmbeddedIntegerOscillator *o=&packet.owner.oscillator;
 if(sizeof(void*)!=4||sizeof(s32)!=4||sizeof(EmbeddedIntegerOscillator)!=32||sizeof(Owner)!=0xD0||__builtin_offsetof(Owner,value)!=0x24||__builtin_offsetof(Owner,oscillator)!=0xB0||__builtin_offsetof(EmbeddedIntegerOscillator,remaining)!=0x14)return 9;
 for(k=0;k<2;k++)for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  current=&cases[i];const u32 *v=current->initial,*w=current->wanted;
  for(j=0;j<sizeof(packet);j++)bytes[j]=(u8)(j*29+i*13+90);
  o->notification=v[0];o->remaining=(s16)v[1];o->minimum=(s16)v[2];o->range=(s16)v[3];
  o->base=fl(v[4]);o->amplitude=fl(v[5]);o->target=fl(v[6]);o->gain=fl(v[7]);packet.owner.value=(s32)v[8];D_800BE9E4=(s32)v[12];
  calls=bad=0;s32 result=functions[k]((u8*)&packet.owner);
  if(bad||(u32)result!=w[9]||calls!=w[10]||(u32)D_800BE9E4!=w[11])return report(1,i,k,result);
  if(o->notification!=w[0]||(u16)o->remaining!=w[1]||(u16)o->minimum!=w[2]||(u16)o->range!=w[3]||ub(o->base)!=w[4]||ub(o->amplitude)!=w[5]||ub(o->target)!=w[6]||ub(o->gain)!=w[7]||(u32)packet.owner.value!=w[8])return report(2,i,k,result);
  for(j=0;j<sizeof(packet);j++){
   u32 rel=j-16;
   if(rel==0xB4||(rel>=0xC4&&rel<0xCA)||(rel>=0xB8&&rel<0xC4)||(rel>=0xCC&&rel<0xD0)||(rel>=0x24&&rel<0x28))continue;
   if(bytes[j]!=(u8)(j*29+i*13+90))return report(3,i,k,result);
  }
 }
 return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    controls = {
        'selected': source,
        'lost-notification': source.replace('return notified;', 'return 0;'),
        'uncleared-notification': source.replace('oscillator->notification = 0;', ';'),
        'unsigned-remaining-gate': source.replace('oscillator->remaining < 0', '(u16)oscillator->remaining > 0'),
        'signed-random-remainder': source.replace('randomValue %', '((s32)randomValue) %'),
        'wrong-span-endpoint': source.replace('oscillator->range + 1', 'oscillator->range + 2'),
        'early-range': source.replace('u32 randomValue;', 'u32 randomValue; s32 cachedRange;').replace('randomValue = (u32)func_150ADA20();', 'cachedRange = oscillator->range;\n        randomValue = (u32)func_150ADA20();').replace('oscillator->range + 1', 'cachedRange + 1'),
        'wrong-float-order': source.replace('oscillator->target * oscillator->amplitude + oscillator->base', '(oscillator->target + oscillator->base) * oscillator->amplitude'),
        'wrong-gain': source.replace(' * oscillator->gain)', ' * 1.0f)'),
        'signed-add-overflow': source.replace('(u32)(s32)', '(s32)').replace('+ (u32)*(s32 *)(input + 0x24)', '+ *(s32 *)(input + 0x24)'),
    }
    assert all(v != source for k,v in controls.items() if k != 'selected')
    results = []
    for opt in ('-O0','-O2','-O3'):
        for label,body in controls.items():
            if label == 'lost-notification':
                body = body.replace('return 0;', 'return notified & 0;')
            path = output / ('native-%s-%s.c' % (label,opt[1:]))
            path.write_text(prefix + body + '\n' + body.replace('func_150C5E0C','func_151AB090') + suffix)
            binary = path.with_suffix('.bin')
            command = ['cc','-m32',opt,'-std=c11','-msse2','-mfpmath=sse','-mstackrealign','-fno-builtin','-fno-strict-aliasing','-ffp-contract=off','-ffreestanding','-static','-fno-stack-protector','-fno-pie','-no-pie','-nostdlib','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wl,-e,_start','-o',str(binary),str(path)]
            q = subprocess.run(command,cwd=root,capture_output=True,text=True)
            assert q.returncode == 0,(label,q.stderr)
            q = subprocess.run([str(binary)],capture_output=True,timeout=20)
            assert (q.returncode == 0) == (label == 'selected'),(opt,label,q.returncode,q.stdout.hex(),q.stderr)
            assert q.returncode in (0,1,-4),(opt,label,q.returncode)
            results.append(dict(profile=opt,label=label,status=q.returncode))
    report = dict(success=True,private_only=True,matching_credit=0,targets=2,cases_each_target_profile=len(rows),profiles=['O0','O2','O3'],effective_controls_each=9,typed_owner_and_32byte_payload=True,all_untouched_bytes_and_fences=True,UBSan=True,defined_unsigned_countdown_and_output_wrap=True,guest_clock_aliases_and_incoming_home_mutations_excluded=True,results=results)
    (output/'private-native-v14.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
