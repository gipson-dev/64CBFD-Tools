"""Native 32-bit source-contract checks with independent expected payloads."""
import struct,subprocess
from tools.experiments import game_random_paired_constructor_match as packet
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import game_random_paired_constructor_match_oracle as model
from tools.tests import game_random_paired_constructor_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
DESC=[(0,4),(4,4),(8,2),(10,2),(12,4),(16,4),*[(x,1)for x in range(20,30)],(30,2),(32,2),(34,2),*[(x,4)for x in range(36,92,4)],*[(x,1)for x in range(96,100)]]
PAYLOAD=[(0,4),*[(x,1)for x in range(4,8)],*[(x,4)for x in (8,12,16,20)],*[(x,1)for x in range(24,28)],*[(x,4)for x in (28,32,36)]]
def run():
 report={}
 for spec in packet.MANIFEST['targets']:
  name=spec['name'];first=name.endswith('60D8');fn=body(spec['selected_source'],name)
  start=spec['selected_source'].index('typedef struct {\n    f32 scale;');end=spec['selected_source'].index('void '+name+'(',start);decl=spec['selected_source'][start:end]
  controls={'flags':('local.descriptor.flags = 0x200005','local.descriptor.flags = 0x200004'),
            'size':('% 51U) + 106','% 51U) + 105'),
            'height':('owner + 0x60','owner + 0x64'),
            'direction':('-dx *','dx *'),
            'scale':('* 62.0f + 41.0f','* 61.0f + 41.0f'),
            'copy':('&local.payload, 40','&local.payload, 39')}
  text='#include <ultra64.h>\ns32 func_150ADA20(void);\nf32 func_150ADA68(void);\nvoid *memcpy(void *,const void *,u32);\n'+decl+'\n'+fn.replace(name+'(','selected(',1)+'\n'
  for label,(old,new) in controls.items():
   assert fn.count(old)==1,(label,old);text+=fn.replace(name+'(','bad_'+label+'(',1).replace(old,new,1)+'\n'
  names=[f'D_800A{x:04X}' for x in range(0x41c if first else 0x45c,0x43c if first else 0x47c,4)]
  text+='\nf32 '+','.join(names)+';\n'
  rows=[]
  for seed in range(8):
   c=g.Case(seed=seed);d,p=model.expected(c,name)
   values=[int.from_bytes(d[off:off+size],'big') for off,size in DESC]+[int.from_bytes(p[off:off+size],'big') for off,size in PAYLOAD]
   rows.append('{'+','.join(str(x)+'u' for x in values)+'}')
  text+='\nstatic const u32 expected[][{}]={{\n'.format(len(DESC)+len(PAYLOAD))+',\n'.join(rows)+'\n};\n'
  text+='''
 static u32 owner_words[64],out_words[128];static u8 descriptor[112];static u32 seed,success,ni,nf,nfactory,ncopy,broken;
 static u32 ints[8]={0xffffffffu,0,0xffffffffu,100,0,5,123456789u,0x80000000u};
 static f32 floats[5]={0.0f,0.25f,0.5f,0.75f,1.0f};
 s32 func_150ADA20(void){u32 v=ints[(ni+seed)%8];ni++;return (s32)v;}
 f32 func_150ADA68(void){f32 v=floats[(nf+seed)%5];nf++;return v;}
 void *func_151303BC(void *p,u8 a,s32 b){u32 i;u8 *src=p;nfactory++;if(a!=2||b!=40)broken=1;for(i=0;i<112;i++)descriptor[i]=src[i];return success?(void*)out_words:(void*)0;}
 void *memcpy(void *d,const void *s,u32 n){u32 i;u8 *dst=d;const u8 *src=s;ncopy++;if(n!=40)broken=2;for(i=0;i<n;i++)dst[i]=src[i];return d;}
 static u32 word(const u8*p){return (u32)p[0]|((u32)p[1]<<8)|((u32)p[2]<<16)|((u32)p[3]<<24);}
 static u32 half(const u8*p){return (u32)p[0]|((u32)p[1]<<8);}
 typedef void (*Routine)(f32,f32,f32,f32,s32,f32,u8*);
 static int check(Routine f){u32 i;u8 *owner=(u8*)owner_words,*out=(u8*)out_words;
 for(seed=0;seed<8;seed++)for(success=0;success<2;success++){
  for(i=0;i<sizeof(owner_words);i++)owner[i]=(u8)(i*13+seed);for(i=0;i<sizeof(out_words);i++)out[i]=0xa5;
  *(f32*)(owner+0x60)=12.5f;*(f32*)(owner+0x64)=-12.5f;ni=nf=nfactory=ncopy=broken=0;
 '''
  for i,n in enumerate(names):text+=n+' = '+str((i+1)*.125)+'f;\n'
  text+='f(1.5f,-4.0f,3.5f,1.25f,0x12345678,-2.5f,owner);\n if(broken||ni!=8||nf!=6||nfactory!=1||ncopy!=success)return 1;\n'
  for i,(off,size) in enumerate(DESC):
   expression={1:f'descriptor[{off}]',2:f'half(descriptor+{off})',4:f'word(descriptor+{off})'}[size];text+='if('+expression+'!=expected[seed]['+str(i)+'])return 2;\n'
  text+='if(success){\n'
  for i,(off,size) in enumerate(PAYLOAD):
   expression={1:f'out[0xa8+{off}]',2:f'half(out+0xa8+{off})',4:f'word(out+0xa8+{off})'}[size];text+='if('+expression+'!=expected[seed]['+str(len(DESC)+i)+'])return 3;\n'
  text+='}\n}return 0;}\nstatic int run(void){if(check(selected))return 10;\n'
  for i,label in enumerate(controls):text+='if(!check(bad_'+label+'))return '+str(20+i)+';\n'
  text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
  file=packet.OUT/(name+'-native.c');file.write_text(text);profiles={}
  for opt in ('-O0','-O2','-O3'):
   exe=packet.OUT/(name+'-native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-fno-builtin-memcpy',str(file),'-o',str(exe)],cwd=packet.ROOT,capture_output=True,text=True);assert r.returncode==0,(r.stdout,r.stderr)
   r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0,(name,opt,r.returncode,r.stderr)
   profiles[opt]={'cases':16,'effective_negative_controls':len(controls),'ubsan':True}
  report[name]=profiles
 return report
