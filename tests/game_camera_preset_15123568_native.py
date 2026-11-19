"""Run the actual recovered C with SDK layout, strict aliasing and UBSan."""
import subprocess
from tools.experiments import game_camera_preset_15123568_match as match
from tools.tests import game_camera_preset_15123568_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def native_checks(out):
    cases=[c for c in guest.cases() if c.address==0x30000 and c.phase==0 and not c.mutation&4]
    fields=('kind','state','disabled','flags','buttons','mode','active','activeState','actorMode','preset','enabled','cooldown','ticks','distance','mutation')
    rows='\n'.join('{'+','.join('0x%Xu'%(getattr(c,k)&0xFFFFFFFF) for k in fields)+'},' for c in cases)
    program=match.HEADER+'''
    typedef char Layout[(sizeof(void*)==4 && sizeof(struct108)==0x9A0 &&
      __builtin_offsetof(struct108,unk1B4)==0x1B4 && __builtin_offsetof(struct108,unk1E0)==0x1E0 &&
      __builtin_offsetof(struct108,unk36A)==0x36A && __builtin_offsetof(struct108,unk3D0)==0x3D0 &&
      __builtin_offsetof(struct108,unk3D4)==0x3D4 && __builtin_offsetof(struct108,unk7B8)==0x7B8)?1:-1];
    f32 D_800A34D8;
    s32 D_800BE9E4;
    typedef struct {u32 kind,state,disabled,flags,buttons,mode,active,activeState,actorMode,preset,enabled,cooldown,ticks,distance,mutation;} Row;
    static const Row rows[]={
    '''+rows+'''
    };
    static struct108 camera;
    static u8 actor[0x400],attached[0x400],expected[sizeof(camera)],snapshots[2][sizeof(camera)];
    static u32 calls[2],count,current,error;
    static const Row *row;
    static u32 load(const u8*p,u32 n){u32 v=0,i;for(i=0;i<n;i++)v|=(u32)p[i]<<(i*8);return v;}
    static void store(u8*p,u32 v,u32 n){u32 i;for(i=0;i<n;i++)p[i]=(u8)(v>>(i*8));}
    static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
    static int equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
    static s32 half(const u8*p){u32 v=load(p,2);return v&0x8000?(s32)v-65536:(s32)v;}
    static void effect(u8*p,u32 t){
      if(row->mutation&1)store(p+0x1B4,2,2);
      if(row->mutation&2)store(p+0x190,0x7FA12345,4);
      store(p+0x7CC,t,4);
    }
    static void modelCall(u32 t){calls[count]=t;copy(snapshots[count++],expected,sizeof(camera));effect(expected,t);}
    static void model(void){
      u8 *p=expected;u32 cooldown,difference; s32 preset;
      if(attached[0x120]==4 && load(p+0x2C,4)!=0x40 && p[0x92C]==0){
        store(p+0x1B4,1,2);store(p+0x7C0,row->distance,4);modelCall(0x15124B18);
        store(p+0x198,0,4);store(p+0x190,0,4);return;
      }
      cooldown=load(p+0x7B8,4);
      if(cooldown && !(cooldown&0x80000000)){
        difference=cooldown-row->ticks;store(p+0x7B8,difference&0x80000000?0:difference,4);return;
      }
      if(!(load(p+0x84,4)&4)||!(load(p+0x36A,2)&8)||load(p+0xDC,4)==4)return;
      if(load(p+0x6C8,4) && load(p+0x6FC,4)!=4)return;
      if(actor[0xAD]==1 && half(p+0x1B4)==1)return;
      if(half(p+0x1B4)==1)return;
      do {
        preset=half(p+0x1B4)-1;store(p+0x1B4,(u32)preset,2);preset=half(p+0x1B4);
        if(preset<=0){preset=3;store(p+0x1B4,3,2);}
      }while(!((1U<<((u32)preset&31))&(u32)half(p+0x1E0)));
      modelCall(0x15124B18);modelCall(0x15125608);store(p+0x7B8,20,4);
    }
    static __attribute__((noinline,noclone)) void provider(struct108*p,u32 t){
      if(p!=&camera || current>=count || calls[current]!=t || !equal((u8*)p,snapshots[current],sizeof(camera)))error=1;
      current++;effect((u8*)p,t);
    }
    void func_15124B18(struct108*p){provider(p,0x15124B18);}
    void func_15125608(struct108*p){provider(p,0x15125608);}
    '''
    driver='''
    static int run(void){u32 i,j;u8 *p=(u8*)&camera;
      for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
        row=&rows[i];for(j=0;j<sizeof(camera);j++)p[j]=(u8)(j*29+0x5A);
        for(j=0;j<sizeof(actor);j++)actor[j]=attached[j]=(u8)(j*29+0x5A);
        actor[0xAD]=(u8)row->actorMode;attached[0x120]=(u8)row->kind;
        store(p+0x2C,row->state,4);p[0x92C]=(u8)row->disabled;store(p+0x84,row->flags,4);
        store(p+0x36A,row->buttons,2);store(p+0xDC,row->mode,4);store(p+0x6C8,row->active,4);store(p+0x6FC,row->activeState,4);
        store(p+0x1B4,row->preset,2);store(p+0x1E0,row->enabled,2);store(p+0x7B8,row->cooldown,4);
        camera.unk3D0=(struct127*)actor;camera.unk3D4=(struct127*)attached;
        store((u8*)&D_800A34D8,row->distance,4);store((u8*)&D_800BE9E4,row->ticks,4);
        copy(expected,p,sizeof(camera));count=current=error=0;model();func_15123568(&camera);
        if(error||current!=count||!equal(p,expected,sizeof(camera)))return 1;
      }return 0;
    }
    '''+START
    controls={
        'cooldown':match.SELECTED.replace('->cooldown = 20;', '->cooldown = 21;'),
        'preset':match.SELECTED.replace('camera->unk1B4 = 1;', 'camera->unk1B4 = 2;'),
        'omit_update':match.SELECTED.replace('        func_15125608(camera);\n',''),
        'clamp':match.SELECTED.replace('->cooldown < 0','->cooldown > 0'),
        'clear':match.SELECTED.replace('camera->unk198 = 0.0f;','camera->unk198 = 1.0f;'),
    }
    assert all(s!=match.SELECTED for s in controls.values())
    reports=[]
    for opt in ('-O0','-O2','-O3'):
        for label,selected in [('selected',match.SELECTED),*controls.items()]:
            source=out/('native'+opt+'-'+label+'.c');exe=source.with_suffix('')
            source.write_text(program+selected+driver)
            cmd=native_command(opt)+['-fstrict-aliasing',str(source),'-o',str(exe)]
            result=subprocess.run(cmd,cwd=match.ROOT,capture_output=True,text=True)
            if result.returncode or result.stdout or result.stderr:raise ValueError(result.stdout+result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=30)
            assert result.returncode==(0 if label=='selected' else 1),(opt,label,result.returncode)
        reports.append(dict(profile=opt,cases=len(cases),controls=len(controls),UBSan=True,strict_aliasing=True))
    return dict(profiles=reports,actual_selected_source=True,guest_home_and_sparse_alias_cases_excluded=True)
