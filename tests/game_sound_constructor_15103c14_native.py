"""Actual SDK32 constructor checked against serialized independent call snapshots."""
import subprocess
from tools.experiments import game_sound_constructor_15103c14_match as match
from tools.tests import game_sound_constructor_15103c14_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def native_checks(out):
    rows=[];values=lambda a:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in a)+'}'
    def actor_fields(m):return[g.read(m,a+off)for a in(g.ACTOR,g.OTHER)for off in(0x14,0x18,0x1C,0x318)]
    def timers(m):return[g.read(m,g.TIMERS+i*2,2)for i in range(4)]
    for c in g.cases():
        if c.phase or not 0<=c.index<4 or c.mutation&56:continue
        initial=g.fixture(c);snaps=[];memory,calls=g.reference(initial,c,snaps)
        pads=snaps+[dict(memory=initial,target=0,args=())]*(4-len(snaps))
        row=[values(actor_fields(initial)),values(actor_fields(memory)),values(timers(initial)),values(timers(memory)),
             '{'+','.join(values(actor_fields(s['memory']))for s in pads)+'}',
             '{'+','.join(values(timers(s['memory']))for s in pads)+'}',
             values(s['target']for s in pads),values(len(s['args'])for s in pads),
             '{'+','.join(values([*s['args'],*[0]*(12-len(s['args']))])for s in pads)+'}',
             *('0x%Xu'%(v&0xFFFFFFFF)for v in(*g.arguments(c),c.actor,c.reject,c.random,c.handle,c.mutation,c.stages,len(calls)))]
        rows.append('{'+','.join(row)+'},')
    program=match.HEADER+match.SELECTED+'''
    typedef char Layout[(sizeof(void*)==4&&sizeof(struct127)==0x32C&&
     __builtin_offsetof(struct127,x_position)==0x14&&__builtin_offsetof(struct127,y_position)==0x18&&
     __builtin_offsetof(struct127,z_position)==0x1C&&__builtin_offsetof(struct127,camera)==0x318)?1:-1];
    u16 D_800D9AB0[4];
    typedef struct {u32 initial[8],expected[8],timers[4],expectedTimers[4],before[4][8],beforeTimers[4][4],
        targets[4],counts[4],args[4][12],sound,key,variants,index,paired,actor,reject,random,handle,mutation,stages,calls;} Row;
    static const Row rows[]={
    '''+'\n'.join(rows)+'''
    };
    static struct127 actor,other;
    static u32 cameraToken,called,error;
    static const Row *row;
    static void store(u8*p,u32 v){u32 i;for(i=0;i<4;i++)p[i]=(u8)(v>>(i*8));}
    static u32 load(const u8*p){u32 i,v=0;for(i=0;i<4;i++)v|=(u32)p[i]<<(i*8);return v;}
    static void *pointer(u32 v){return v==0x70000?&actor:v==0x80000?&other:0;}
    static void setup(const u32*fields){
      u32 i,j;struct127 *p;
      for(i=0;i<2;i++){p=i?&other:&actor;for(j=0;j<3;j++)store((u8*)p+0x14+j*4,fields[i*4+j]);
        p->camera=fields[i*4+3]?(struct108*)&cameraToken:0;}
    }
    static int equal(const u32*fields,const u32*timers){
      u32 i,j,v;struct127 *p;
      for(i=0;i<2;i++){p=i?&other:&actor;for(j=0;j<3;j++){
        v=load((u8*)p+0x14+j*4);if(v!=fields[i*4+j])return 0;
      }if((p->camera!=0)!=(fields[i*4+3]!=0))return 0;}
      for(i=0;i<4;i++)if(D_800D9AB0[i]!=timers[i])return 0;return 1;
    }
    static __attribute__((noinline,noclone)) void observe(u32 target,const u32*args,u32 count,u32 stage){
      u32 i,wanted,n=called++,bits=(row->stages>>stage&1)?row->mutation:0;
      if(n>=row->calls||n>=4||target!=row->targets[n]||count!=row->counts[n]||!equal(row->before[n],row->beforeTimers[n])){error=1;return;}
      for(i=0;i<count;i++){
        wanted=row->args[n][i];
        if((target==0x10010894&&i==0)||(target==0x1000FA64&&i==9))wanted=(u32)pointer(wanted);
        if(target==0x1000FA64&&i==7)wanted=wanted==0x15103910?(u32)func_15103910:(u32)func_15103AA0;
        if(args[i]!=wanted)error=1;
      }
      if(bits&1){u32 fields[8]={0xC2F78000,0x43280000,0xBF400000,0,0xC2F78000,0x43280000,0xBF400000,0};
        fields[3]=actor.camera!=0;fields[7]=other.camera!=0;setup(fields);}
      if(bits&2){actor.camera=actor.camera?0:(struct108*)&cameraToken;other.camera=other.camera?0:(struct108*)&cameraToken;}
      if(bits&4){D_800D9AB0[row->index]=0x4321;D_800D9AB0[3]=0x8765;}
    }
    s32 func_15103910(void){return 0;}
    s32 func_15103AA0(void){return 0;}
    struct127 *func_1505EEF4(s32 key){u32 args[1]={(u32)key};observe(0x1505EEF4,args,1,0);return pointer(row->actor);}
    s32 func_10010894(struct127*p){u32 args[1]={(u32)p};observe(0x10010894,args,1,1);return(s32)row->reject;}
    s32 func_150ADA20(void){observe(0x150ADA20,0,0,2);return(s32)row->random;}
    u16 func_1000FA64(u16 id,s16 x,s16 y,s16 z,s32 volume,u16 a,s16 b,s32 callback,void*packed,s32 owner,s32 flags,s32 cents){
      u32 args[12]={id,(u32)(s32)x,(u32)(s32)y,(u32)(s32)z,(u32)volume,a,(u32)(s32)b,(u32)callback,(u32)packed,(u32)owner,(u32)flags,(u32)cents};
      observe(0x1000FA64,args,12,3);return(u16)row->handle;
    }
    static int run(void){u32 i,j;
      for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
        row=&rows[i];setup(row->initial);for(j=0;j<4;j++)D_800D9AB0[j]=(u16)row->timers[j];called=error=0;
        func_15103C14(row->sound,(s32)row->key,row->variants,(s32)row->index,(s32)row->paired);
        if(error||called!=row->calls||!equal(row->expected,row->expectedTimers))return 1;
      }return 0;
    }
    '''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    changes={
        'cooldown_exception':('soundId != 0x58D','soundId != 0x58C'),
        'paired_stride':(' % variants) * 2',' % variants) * 3'),
        'actor_gate':('func_10010894(actor) != 0','func_10010894(actor) == 0'),
        'camera_mode':('actor->camera != NULL','actor->camera == NULL'),
        'primary_callback':('(s32)func_15103910','(s32)func_15103AA0'),
        'primary_volume':('30000, 32767','30001, 32767'),
        'packed_flag':('paired << 15','paired << 14'),
        'cooldown_value':('*cooldown = 600;','*cooldown = 601;'),
    }
    controls={name:match.SELECTED.replace(a,b)for name,(a,b)in changes.items()};assert all(s!=match.SELECTED for s in controls.values())
    profiles=[]
    for opt in('-O0','-O2','-O3'):
        for name,body in[('selected',match.SELECTED),*controls.items()]:
            source=out/('native'+opt+'-'+name+'.c');exe=source.with_suffix('');source.write_text(program.replace(match.HEADER+match.SELECTED,match.HEADER+body,1))
            result=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fsanitize=float-cast-overflow',str(source),'-o',str(exe)],cwd=match.ROOT,capture_output=True,text=True)
            if result.returncode or result.stdout or result.stderr:raise ValueError(result.stdout+result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=30);assert result.returncode==(0 if name=='selected'else 1),(opt,name,result.returncode,result.stderr[:200])
        profiles.append(dict(profile=opt,cases=len(rows),effective_controls=len(controls),UBSan=True,float_cast_overflow=True,strict_aliasing=True))
    return dict(profiles=profiles,actual_selected_source=True,independent_serialized_reference=True,
                guest_only_incoming_home_mutations_and_sparse_addresses_excluded=True)
