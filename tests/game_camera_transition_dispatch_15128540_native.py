"""Native camera layout and GCC alias-contract checks with effective controls."""
import json,subprocess
from tools.experiments import game_camera_transition_dispatch_15128540_match as match
from tools.tests import game_camera_transition_dispatch_15128540_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=match.ROOT;out=root/match.BUILD;selected=match.SELECTED
def controls():
 pairs={
 'signed_first':('if (func_151253CC((struct108 *)address))','if (func_151253CC((struct108 *)address)>0)'),
 'signed_busy':('if (func_15128030(address))','if (func_15128030(address)>0)'),
 'signed_fallback':('if (func_15126378(address))','if (func_15126378(address)>0)'),
 'wrong_first_bit':('& 0x80000','& 0x100000'),
 'copy_source':('+ 0x2A4)', '+ 0x2A8)'),
 'copy_destination':('+ 0x2BC)', '+ 0x2B8)'),
 'omit_initialize':('        func_151256BC(address);\n',''),
 'omit_update':('        func_151236D0(address);\n',''),
 'omit_finish':('        func_151284C4((struct108 *)address);\n',''),
 'return_two':('return 1;', 'return 2;'),
 'wrong_second_helper':('func_1512E4B0(address);','func_151219D0(address);'),
 }
 result={n:selected.replace(a,b)for n,(a,b)in pairs.items()}
 a='        func_1512A360((u8 *)address);\n';b='        *(CameraPositionBits14FF90 *)((u8 *)address + 0x2BC) = *(CameraPositionBits14FF90 *)((u8 *)address + 0x2A4);\n'
 assert a+b in selected
 result['early_copy']=selected.replace(a+b,b+a)
 assert all(v!=selected for v in result.values())
 return result


def native_checks():
    cases=[c for c in guest.cases()if c.address==guest.ADDRESS and not c.mutation&32 and c.phase==0]
    rows='\n'.join('{'+','.join('0x%Xu'%v for v in(c.flags,c.first,c.busy,c.fallback,c.mutation,c.override,c.pattern))+'},'for c in cases)
    header=match.HEADER
    program=header+'''
    typedef char Layout[(sizeof(void*)==4&&sizeof(CameraPositionBits14FF90)==12&&
     __alignof__(CameraPositionBits14FF90)==4&&__builtin_offsetof(struct108,unk2C)==0x2C&&
     __builtin_offsetof(struct108,unk2A4)==0x2A4&&__builtin_offsetof(struct108,unk2A8)==0x2A8&&
     __builtin_offsetof(struct108,unk2AC)==0x2AC&&__builtin_offsetof(struct108,unk2BC)==0x2BC&&
     __builtin_offsetof(struct108,unk2C0)==0x2C0&&__builtin_offsetof(struct108,unk2C4)==0x2C4)?1:-1];
    typedef struct {u32 flags,first,busy,fallback,mutation,override,pattern;} Row;
    static const Row rows[]={
    '''+rows+'''
    };
    static struct108 camera;
    static u8 initial[sizeof(camera)],expected[sizeof(camera)],snapshots[8][sizeof(camera)];
    static u32 calls[8],callCount,currentCall,error,expectedResult;
    static const Row *row;
    static u32 read32(const u8*p){return (u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
    static void write32(u8*p,u32 v){u32 i;for(i=0;i<4;i++)p[i]=(u8)(v>>(i*8));}
    static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
    static int equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
    static void effect(u8*p,u32 target){
     u32 i;
     if((target==0x151253CC&&(row->mutation&1))||(target==0x15128030&&(row->mutation&2)))write32(p+0x2C,row->override);
     if(target==0x1512A360){
      if(row->mutation&4){write32(p+0x2A4,0xFFFFFFFF);write32(p+0x2A8,0x7F800001);write32(p+0x2AC,0x80000000);}
      if(row->mutation&64)for(i=0;i<3;i++)write32(p+0x2BC+i*4,0x12345678+i);
     }
     if(target==0x151236D0&&(row->mutation&8)){write32(p+0x2C,0xFFFFFFFF);write32(p+0x2C0,0xABCDEF01);}
     if(target==0x151284C4&&(row->mutation&16))write32(p+0x2C4,0x7FA12345);
     write32(p+0x300,target^row->mutation);
    }
    static u32 returned(u32 t){return t==0x151253CC?row->first:t==0x15128030?row->busy:t==0x15126378?row->fallback:0xDEADBEEF;}
    static u32 modelCall(u32 t){calls[callCount]=t;copy(snapshots[callCount++],expected,sizeof(camera));effect(expected,t);return returned(t);}
    static u32 model(void){
     u32 flags,pick=0,words[3],i;
     if(modelCall(0x151253CC))return 1;
     if(modelCall(0x15128030))return 0;
     flags=read32(expected+0x2C);
     if(flags&0x80000)pick=0x1512A360;
     else if(flags&0x100000)pick=0x1512E4B0;
     else if(flags&0x200000)pick=0x151219D0;
     else if(flags&0x400000)pick=0x1512D380;
     if(pick){
      modelCall(pick);
      if(pick==0x1512A360){for(i=0;i<3;i++)words[i]=read32(expected+0x2A4+i*4);for(i=0;i<3;i++)write32(expected+0x2BC+i*4,words[i]);modelCall(0x151256BC);}
      modelCall(0x151236D0);modelCall(0x151284C4);return 1;
     }
     if(modelCall(0x15126378)){modelCall(0x151284C4);return 1;}return 0;
    }
    static __attribute__((noinline,noclone)) s32 provider(u32 t,s32 address){
     if((u8*)address!=(u8*)&camera||currentCall>=callCount||calls[currentCall]!=t||!equal((u8*)&camera,snapshots[currentCall],sizeof(camera)))error=1;
     currentCall++;effect((u8*)&camera,t);return (s32)returned(t);
    }
    s32 func_151253CC(struct108*p){return provider(0x151253CC,(s32)p);}
    s32 func_15128030(s32 p){return provider(0x15128030,p);}
    void func_1512A360(u8*p){(void)provider(0x1512A360,(s32)p);}
    s32 func_1512E4B0(s32 p){return provider(0x1512E4B0,p);}
    s32 func_151219D0(s32 p){return provider(0x151219D0,p);}
    void func_1512D380(s32 p){(void)provider(0x1512D380,p);}
    s32 func_151256BC(s32 p){return provider(0x151256BC,p);}
    s32 func_151236D0(s32 p){return provider(0x151236D0,p);}
    void func_151284C4(struct108*p){(void)provider(0x151284C4,(s32)p);}
    s32 func_15126378(s32 p){return provider(0x15126378,p);}
    '''
    program+=selected+'\n'
    for name,b in controls().items():program+=b.replace('func_15128540(','negative_'+name+'(',1)+'\n'
    program+='''
    typedef s32(*Dispatch)(s32);
    static int test(Dispatch f){
     u32 n,i;int mismatch=0;
     for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
      row=&rows[n];
      for(i=0;i<sizeof(camera);i++)initial[i]=(u8)(i*29+row->pattern*37+0x5A);
      write32(initial+0x2C,row->flags);
      write32(initial+0x2A4,row->pattern&1?0x7FA12345:0x3F800001);
      write32(initial+0x2A8,row->pattern&1?0x80000000:0x80000001);
      write32(initial+0x2AC,row->pattern&1?0xFFFFFFFF:0x87654321);
      copy(expected,initial,sizeof(camera));callCount=currentCall=error=0;expectedResult=model();
      copy((u8*)&camera,initial,sizeof(camera));
      if((u32)f((s32)&camera)!=expectedResult||error||currentCall!=callCount||!equal((u8*)&camera,expected,sizeof(camera)))mismatch=1;
     }
     return mismatch;
    }
    static __attribute__((noinline,noclone)) int aliasProbe(struct108*c,CameraPositionBits14FF90*words){
     c->unk2C4=1.0f;words->words[2]=0x40000000;return c->unk2C4==2.0f;
    }
    static int run(void){
     if(!aliasProbe(&camera,(CameraPositionBits14FF90*)((u8*)&camera+0x2BC)))return 2;
     if(test(func_15128540))return 3;
    '''
    for j,name in enumerate(controls()):program+=' if(!test(negative_%s))return %d;\n'%(name,j+10)
    program+=' return 0;\n}\n'+START
    (out/'native.c').write_text(program)
    results=[]
    for opt in ('-O0','-O2','-O3'):
     binary=out/('native'+opt)
     command=native_command(opt)+['-fstrict-aliasing','-Wstrict-aliasing=2','-fno-builtin','-mstackrealign',str(out/'native.c'),'-o',str(binary)]
     p=subprocess.run(command,cwd=root,capture_output=True,text=True);(out/('native'+opt+'-build.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
     p=subprocess.run([str(binary)],capture_output=True);assert p.returncode==0,(opt,p.returncode)
     results.append(dict(profile=opt,cases=len(cases),semantic_controls=len(controls()),strict_aliasing=True,alias_probe=True,UBSan_traps=True))
     print(json.dumps(results[-1]),flush=True)
    alias_control=program.replace('__attribute__((__may_alias__))','')
    (out/'native-no-alias-control.c').write_text(alias_control)
    negative=[]
    for opt in ('-O0','-O2','-O3'):
     binary=out/('native-no-alias-control'+opt);p=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fno-builtin','-mstackrealign',str(out/'native-no-alias-control.c'),'-o',str(binary)],cwd=root,capture_output=True,text=True);assert p.returncode==0,p.stderr
     rc=subprocess.run([str(binary)],capture_output=True).returncode
     assert rc==(0 if opt=='-O0'else 2),(opt,rc)
     negative.append(dict(profile=opt,exit=rc,alias_control_only_effective_with_optimization=True))
    (out/'native-contract.json').write_text(json.dumps(dict(results=results,alias_control=negative,
     typed_s32_address_callback=True,actual_struct108_backing=True,all_camera_bytes=True,
     GCC_may_alias_documentation='https://gcc.gnu.org/onlinedocs/gcc/Common-Attributes.html#index-may_005falias-type-attribute',
     generic_ISO_C_portability_claim=False),indent=2)+'\n')
    return dict(cases_per_profile=len(cases),profiles=results,alias_control=negative,semantic_controls=len(controls()))
