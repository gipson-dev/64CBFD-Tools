"""Compile the actual C with SDK32 layouts and serialized independent results."""
import subprocess
from tools.experiments import game_sound_countdown_15103910_match as match
from tools.tests import game_sound_countdown_15103910_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def native_checks(out):
    rows=[]
    values=lambda a:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in a)+'}'
    def fields(m,c):return[g.read(m,g.u32(c.address+off),n)for off,n in g.FIELDS]
    def word_kind(at):
        if at==g.VALUE:return 0,0
        if at==g.VOLUME:return 1,0
        if at-g.STATE in(12,16,24):return 2,at-g.STATE
        return None
    for c in g.cases():
        if c.address!=g.STATE or c.phase or c.mutation&8:continue
        vk,wk=word_kind(c.callbackValue),word_kind(c.volume)
        if vk is None or wk is None:continue
        if not c.pending:pk,po=0,0
        elif c.pending==g.PENDING:pk,po=1,0
        elif c.pending-g.STATE in(0,2,4,6,8,10,36,38):pk,po=2,c.pending-g.STATE
        else:continue
        initial=g.fixture(c);snaps=[];memory,calls,result=g.reference(initial,c,snaps);assert len(calls)<=1
        snap=snaps[0]if snaps else dict(memory=initial,target=0,args=())
        args=list(snap['args'])+[0]*(5-len(snap['args']))
        scalars=[g.read(initial,g.PENDING,2),g.read(memory,g.PENDING,2),c.ticks,g.read(memory,g.TICKS),pk,po,*vk,*wk,
                 g.read(initial,g.VALUE),g.read(memory,g.VALUE),g.read(initial,g.VOLUME),g.read(memory,g.VOLUME),
                 g.read(initial,g.ACTOR+0x8C,2),g.read(memory,g.ACTOR+0x8C,2),g.read(snap['memory'],g.ACTOR+0x8C,2),
                 snap['target'],len(snap['args']),c.mutation,len(calls),result]
        rows.append('{'+','.join([values(fields(initial,c)),values(fields(memory,c)),values(fields(snap['memory'],c)),values(c.coordinates),values(args),*('0x%Xu'%(v&0xFFFFFFFF)for v in scalars)])+'},')
    program=match.HEADER+match.SELECTED+'''
    typedef char Layout[(sizeof(void*)==4&&sizeof(SoundTimerState130CB0)==40&&
     __builtin_offsetof(SoundTimerState130CB0,volume)==12&&__builtin_offsetof(SoundTimerState130CB0,flags)==16&&
     __builtin_offsetof(SoundTimerState130CB0,packedTimer)==24&&__builtin_offsetof(SoundTimerState130CB0,actor)==28&&
     __builtin_offsetof(SoundTimerState130CB0,handle)==36&&__builtin_offsetof(struct127,x_position)==0x14&&
     __builtin_offsetof(struct127,y_position)==0x18&&__builtin_offsetof(struct127,z_position)==0x1C&&
     __builtin_offsetof(struct127,unk8C)==0x8C)?1:-1];
    s32 D_800BE9E4;
    typedef struct {u32 initial[14],expected[14],before[14],coordinates[3],args[5];
      u32 initialOut,expectedOut,ticks,expectedTicks,pk,po,vk,vo,wk,wo,
          initialValue,expectedValue,initialVolume,expectedVolume,
          initialHandle,expectedHandle,beforeHandle,target,argCount,mutation,calls,result;} Row;
    static const Row rows[]={
    '''+'\n'.join(rows)+'''
    };
    static SoundTimerState130CB0 state,expected,before;
    static struct127 actor,other;
    static u16 pending;
    static s32 callbackValue,volume,pan,cents,fx;
    static u32 error,called;
    static const Row *row;
    static const u32 offsets[14]={0,2,4,6,8,10,12,16,20,24,28,32,36,38};
    static const u32 widths[14]={2,2,2,2,2,2,4,4,4,4,4,4,2,2};
    static void store(u8*p,u32 v,u32 n){u32 i;for(i=0;i<n;i++)p[i]=(u8)(v>>(i*8));}
    static int equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
    static void setup(SoundTimerState130CB0*p,const u32*fields){
      u32 i,value;for(i=0;i<14;i++){
        value=fields[i];if(i==10)value=value==0x70000?(u32)&actor:(u32)&other;
        store((u8*)p+offsets[i],value,widths[i]);
      }
    }
    static __attribute__((noinline,noclone)) void observe(u32 target,const u32*args,u32 count){
      u32 i,expectedArg;
      if(called++||row->calls!=1||target!=row->target||count!=row->argCount||
         !equal((u8*)&state,(u8*)&before,sizeof(state))||(u32)D_800BE9E4!=row->ticks||actor.unk8C!=row->beforeHandle)error=1;
      for(i=0;i<count;i++){
        expectedArg=row->args[i];if(target==0x10010344&&i==1)expectedArg=(u32)&actor;
        if(args[i]!=expectedArg)error=1;
      }
      if(row->mutation&1)state.flags^=0xFFFFFFFF;
      if(row->mutation&2){state.packedTimer=(s32)0xDEADBEEF;D_800BE9E4=-1;}
      if(row->mutation&4){state.token=0x1357;state.parameter8=0x9876;state.parameterA=-12345;state.volume=(s32)0x89ABCDEF;}
      if(row->mutation&16)state.actor=&other;
      if(row->mutation&32)state.handle=0xCAFE;
      if(row->mutation&64)actor.unk8C=0xDEAD;
    }
    s32 func_10010344(u16 command,void*p,s32 attenuation,s16 a,u16 b){
      u32 args[5]={command,(u32)p,(u32)attenuation,(u32)(s32)a,b};observe(0x10010344,args,5);return (s32)0x98765432;
    }
    void func_100111C8(u16 handle){u32 args[1]={handle};observe(0x100111C8,args,1);}
    static s32 *word(u32 kind,u32 offset){return kind==0?&callbackValue:kind==1?&volume:(s32*)((u8*)&state+offset);}
    static int run(void){
      u32 i,j,result;u16 *out;
      for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
        row=&rows[i];setup(&state,row->initial);setup(&expected,row->expected);setup(&before,row->before);
        for(j=0;j<3;j++)store((u8*)&actor+0x14+j*4,row->coordinates[j],4);
        actor.unk8C=(u16)row->initialHandle;
        pending=(u16)row->initialOut;D_800BE9E4=(s32)row->ticks;called=error=0;
        callbackValue=(s32)row->initialValue;volume=(s32)row->initialVolume;
        pan=0x12345678;cents=-123456;fx=-1;
        out=row->pk==0?0:row->pk==1?&pending:(u16*)((u8*)&state+row->po);
        result=(u32)func_15103910(&state,word(row->vk,row->vo),word(row->wk,row->wo),&pan,&cents,&fx,out);
        if(error||called!=row->calls||result!=row->result||pending!=row->expectedOut||actor.unk8C!=row->expectedHandle||
           (u32)callbackValue!=row->expectedValue||(u32)volume!=row->expectedVolume||pan!=0x12345678||cents!=-123456||fx!=-1||
           (u32)D_800BE9E4!=row->expectedTicks||!equal((u8*)&state,(u8*)&expected,sizeof(state)))return 1;
      }return 0;
    }
    '''+START
    replacements={
        'unsigned_countdown':('s16 remaining;','u16 remaining;'),
        'expiry_boundary':('remaining <= 0','remaining < 0'),
        'expiry_token':('state->token = *pending;','state->token = 0;'),
        'callback_value':('*callbackValue = 1;','*callbackValue = 2;'),
        'return_value':('return 1;','return 0;'),
        'flag_mask':('state->flags &= ~0x80;','state->flags &= ~0x40;'),
        'post_stop_reload':('actor->unk8C = state->handle;','actor->unk8C = 1;'),
        'emit_parameter':('25000, 100, 120','25000, 100, 121'),
    }
    controls={name:match.SELECTED.replace(a,b)for name,(a,b)in replacements.items()};assert all(s!=match.SELECTED for s in controls.values())
    profiles=[]
    for opt in ('-O0','-O2','-O3'):
        for name,body in [('selected',match.SELECTED),*controls.items()]:
            source=out/('native'+opt+'-'+name+'.c');exe=source.with_suffix('')
            source.write_text(program.replace(match.HEADER+match.SELECTED,match.HEADER+body,1))
            result=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fsanitize=float-cast-overflow',str(source),'-o',str(exe)],cwd=match.ROOT,capture_output=True,text=True)
            if result.returncode or result.stdout or result.stderr:raise ValueError(result.stdout+result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=30)
            assert result.returncode==(0 if name=='selected'else 1),(opt,name,result.returncode,result.stderr[:200])
        profiles.append(dict(profile=opt,cases=len(rows),controls=len(controls),UBSan=True,float_cast_overflow=True,strict_aliasing=True))
    return dict(profiles=profiles,actual_selected_source=True,independent_serialized_reference=True,
                guest_only_sparse_and_incompatible_aliases_excluded=True)
