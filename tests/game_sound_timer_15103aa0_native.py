"""Actual SDK32 C checked against serialized independent guest-model results."""
import subprocess
from tools.experiments import game_sound_timer_15103aa0_match as match
from tools.tests import game_sound_timer_15103aa0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def native_checks(out):
    rows=[]
    def fields(m,c):return [g.read(m,g.u32(c.address+off),n)for off,n in g.FIELDS]
    values=lambda a:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF)for v in a)+'}'
    for c in g.cases():
        if c.address!=g.STATE or c.phase or c.mutation&8:continue
        if c.pending==0:kind,offset=0,0
        elif c.pending==g.PENDING:kind,offset=1,0
        elif c.pending-g.STATE in(0,2,4,6,8,10,36,38):kind,offset=2,c.pending-g.STATE
        else:continue
        initial=g.fixture(c);snaps=[];memory,calls,value=g.reference(initial,c,snaps);assert len(calls)<=1
        snap=snaps[0]if snaps else dict(memory=initial,target=0,args=())
        args=list(snap['args'])+[0]*(5-len(snap['args']))
        row=[values(fields(initial,c)),values(fields(memory,c)),values(fields(snap['memory'],c)),values(c.coordinates),values(args),
             *('0x%Xu'%(v&0xFFFFFFFF)for v in(g.read(initial,g.PENDING,2),g.read(memory,g.PENDING,2),c.ticks,g.read(memory,g.TICKS),kind,offset,snap['target'],len(snap['args']),c.mutation,len(calls),value))]
        rows.append('{'+','.join(row)+'},')
    program=match.HEADER+match.SELECTED+'''
    typedef char Layout[(sizeof(void*)==4&&sizeof(SoundTimerState130CB0)==40&&
     __builtin_offsetof(SoundTimerState130CB0,x)==2&&__builtin_offsetof(SoundTimerState130CB0,flags)==16&&
     __builtin_offsetof(SoundTimerState130CB0,packedTimer)==24&&__builtin_offsetof(SoundTimerState130CB0,actor)==28&&
     __builtin_offsetof(SoundTimerState130CB0,handle)==36&&__builtin_offsetof(struct127,x_position)==0x14&&
     __builtin_offsetof(struct127,y_position)==0x18&&__builtin_offsetof(struct127,z_position)==0x1C)?1:-1];
    s32 D_800BE9E4;
    typedef struct {u32 initial[14],expected[14],before[14],coordinates[3],args[5];
      u32 initialOut,expectedOut,ticks,expectedTicks,kind,offset,target,argCount,mutation,calls,result;} Row;
    static const Row rows[]={
    '''+'\n'.join(rows)+'''
    };
    static SoundTimerState130CB0 state,expected,before;
    static struct127 actor,other;
    static u16 pending;
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
         !equal((u8*)&state,(u8*)&before,sizeof(state))||(u32)D_800BE9E4!=row->ticks)error=1;
      for(i=0;i<count;i++){
        expectedArg=row->args[i];if(target==0x10010344&&i==1)expectedArg=(u32)&actor;
        if(args[i]!=expectedArg)error=1;
      }
      if(row->mutation&1)state.flags^=0xFFFFFFFF;
      if(row->mutation&2){state.packedTimer=(s32)0xDEADBEEF;D_800BE9E4=-1;}
      if(row->mutation&4){state.token=0x1357;state.parameter8=0x9876;state.parameterA=-12345;}
      if(row->mutation&16)state.actor=&other;
    }
    s32 func_10010344(u16 command,void*p,s32 attenuation,s16 a,u16 b){
      u32 args[5]={command,(u32)p,(u32)attenuation,(u32)(s32)a,b};observe(0x10010344,args,5);return (s32)0x98765432;
    }
    void func_1000F85C(u16 handle,s16 command,s32 value){
      u32 args[3]={handle,(u32)(s32)command,(u32)value};observe(0x1000F85C,args,3);
    }
    static int run(void){
      u32 i,j,result;u16 *out;
      for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
        row=&rows[i];setup(&state,row->initial);setup(&expected,row->expected);setup(&before,row->before);
        for(j=0;j<3;j++)store((u8*)&actor+0x14+j*4,row->coordinates[j],4);
        pending=(u16)row->initialOut;D_800BE9E4=(s32)row->ticks;called=error=0;
        out=row->kind==0?0:row->kind==1?&pending:(u16*)((u8*)&state+row->offset);
        result=(u32)func_15103AA0(&state,(s32)0x7FA12345,(s32)0x80000000,-1,0x13579BDF,0x2468ACE0,out);
        if(error||called!=row->calls||result!=row->result||pending!=row->expectedOut||
           (u32)D_800BE9E4!=row->expectedTicks||!equal((u8*)&state,(u8*)&expected,sizeof(state)))return 1;
      }return 0;
    }
    '''+START
    replacements={
        'timer_mask':('0x7FFF','0xFFFF'),
        'expiry_boundary':('<= (u32)D_800BE9E4','< (u32)D_800BE9E4'),
        'expiry_token':('state->token = *pending;','state->token = 0;'),
        'return_value':('return 1;','return 0;'),
        'flag_mask':('state->flags &= ~0x80;','state->flags &= ~0x40;'),
        'control_value':('func_1000F85C(state->handle, -0x8000, 2);','func_1000F85C(state->handle, -0x8000, 3);'),
        'emit_parameter':('state->parameterA, state->parameter8','state->parameterA, (u16)state->parameterA'),
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
            assert result.returncode==(0 if name=='selected'else 1),(opt,name,result.returncode)
        profiles.append(dict(profile=opt,cases=len(rows),controls=len(controls),UBSan=True,float_cast_overflow=True,strict_aliasing=True))
    return dict(profiles=profiles,actual_selected_source=True,independent_serialized_reference=True,guest_only_sparse_and_word_aliases_excluded=True)
