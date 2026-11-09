"""Native camera/actor layouts, wide conversion and alias controls."""
import json,subprocess
from tools.experiments import game_secondary_camera_position_1512e4b0_match as match
from tools.tests import game_secondary_camera_position_1512e4b0_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
root=match.ROOT;out=root/match.BUILD;selected=match.SELECTED;header=match.HEADER
def controls():
 pairs={
 'selector':('camera->unk23D == 3','camera->unk23D == 2'),
 'actor_slot':('D_800CC2D0[slot]','D_800CC2D0[slot + 1]'),
 'height':('150.0f','149.0f'),
 'speed_scale':('actor->unk40*10.0f','actor->unk40*9.0f'),
 'denominator':('/1800.0f','/180.0f'),
 'sine_radius':('sinf(angle)*60.0f','sinf(angle)*59.0f'),
 'cosine_radius':('cosf(angle)*60.0f','cosf(angle)*59.0f'),
 'heading_offset':('actor + 0x2E4','actor + 0x2E6'),
 'initial_wrap':('(s16)-*(ActorHeadingHalfword15B960 *)','-*(ActorHeadingHalfword15B960 *)'),
 'final_wrap':('    heading = (s16)heading;\n',''),
 'unsigned_adjusted':('heading = (s16)heading','heading = (u16)heading'),
 'sine_direction':('camera->unk2BC - offset','camera->unk2BC + offset'),
 }
 rows={name:selected.replace(a,b)for name,(a,b)in pairs.items()}
 rows['cached_x']=selected.replace('    f32 angle;','    f32 angle;\n    f32 cachedX;').replace('    offset = sinf(angle)*60.0f;','    cachedX = camera->unk2BC;\n    offset = sinf(angle)*60.0f;').replace('camera->unk2BC - offset','cachedX - offset')
 rows['cached_z']=selected.replace('    f32 angle;','    f32 angle;\n    f32 cachedZ;').replace('    offset = cosf(angle)*60.0f;','    cachedZ = camera->unk2C4;\n    offset = cosf(angle)*60.0f;').replace('camera->unk2C4 - offset','cachedZ - offset')
 assert all(v!=selected for v in rows.values());return rows


def narrow_control():
    return selected.replace('    s32 heading;','    s16 heading;').replace('    heading = (s16)heading;\n','')

def native_checks():
    cases=list(guest.native_cases())
    rows='\n'.join('{'+','.join('0x%Xu'%v for v in(c.view,c.heading,c.speed,c.x,c.y,c.z,c.results[0],c.results[1],c.mutation,c.pi))+'},'for c in cases)
    program=header+'''
    typedef char Layout[(sizeof(void*)==4&&sizeof(struct127)==812&&sizeof(struct108)==0x9A0&&
     __builtin_offsetof(struct127,x_position)==20&&__builtin_offsetof(struct127,y_position)==24&&
     __builtin_offsetof(struct127,z_position)==28&&__builtin_offsetof(struct127,unk40)==64&&
     __builtin_offsetof(struct127,unk2E4)==0x2E4&&__builtin_offsetof(struct108,unk23D)==0x23D&&
     __builtin_offsetof(struct108,unk2BC)==0x2BC&&__builtin_offsetof(struct108,unk2C0)==0x2C0&&
     __builtin_offsetof(struct108,unk2C4)==0x2C4&&__builtin_offsetof(struct108,unk2F8)==0x2F8&&
     __builtin_offsetof(struct108,unk2FC)==0x2FC&&__builtin_offsetof(struct108,unk300)==0x300)?1:-1];
    typedef struct {u32 view,heading,speed,x,y,z,sine,cosine,mutation,pi;} Row;
    static const Row rows[]={
    '''+rows+'''
    };
    struct127 D_800CC2D0[26];f32 D_800A3730;
    static struct108 camera,alternate;
    static u8 expectedCamera[sizeof(camera)],expectedAlt[sizeof(camera)],expectedActors[sizeof(D_800CC2D0)];
    static u8 snapCamera[2][sizeof(camera)],snapAlt[2][sizeof(camera)],snapActors[2][sizeof(D_800CC2D0)];
    static u32 snapPi[2],angleWord,currentStage,error,expectedPi;
    static const Row*row;
    static u32 word(f32 f){union{f32 f;u32 w;}v;v.f=f;return v.w;}
    static f32 value(u32 w){union{f32 f;u32 w;}v;v.w=w;return v.f;}
    static u32 rd32(const u8*p){return(u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
    static u32 rd16(const u8*p){return(u32)p[0]|(u32)p[1]<<8;}
    static void wr32(u8*p,u32 w){u32 i;for(i=0;i<4;i++)p[i]=(u8)(w>>(i*8));}
    static void wr16(u8*p,u32 w){p[0]=(u8)w;p[1]=(u8)(w>>8);}
    static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
    static int equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
    static s32 signedHalf(u32 w){w&=65535;return w&32768?(s32)w-65536:(s32)w;}
    static void effect(u8*cam,u8*alt,u8*actors,u32*pi,u32 stage){
     u8*a=actors+(row->view==3?812:0);
     if(stage==0){
      if(row->mutation&1){wr32(cam+0x2BC,0xC2FA0000);wr32(cam+0x2C0,0x41D00000);wr32(cam+0x2C4,0x43430000);}
      if(row->mutation&2){wr32(a+20,0x3F800000);wr32(a+64,0x7F800000);wr16(a+0x2E4,0x8000);}
      if(row->mutation&4)*pi=0x3F000000;
      if(row->mutation&8)cam[0x23D]=row->view==3?0:3;
      if(row->mutation&16){wr32(alt+0x2BC,0x41A80000);wr32(alt+0x2C0,0xC2100000);wr32(alt+0x2C4,0x42E00000);}
     }else if(row->mutation&32){wr32(cam+0x2C4,0xC2C00000);wr32(alt+0x2C4,0xC2C00000);}
    }
    static void model(void){
     u32 stage;u8*a=expectedActors+(row->view==3?812:0);s32 h,adjusted;f32 scaled,sum,angle,offset;
     wr32(expectedCamera+0x2BC,rd32(a+20));wr32(expectedCamera+0x2C0,word(value(rd32(a+24))+150.0f));wr32(expectedCamera+0x2C4,rd32(a+28));
     h=signedHalf((u32)-signedHalf(rd16(a+0x2E4)));scaled=value(rd32(a+64))*10.0f;sum=(f32)h+scaled;
     adjusted=(s32)sum;h=signedHalf((u32)adjusted);angle=((f32)h*value(expectedPi))/1800.0f;angleWord=word(angle);
     for(stage=0;stage<2;stage++){
      copy(snapCamera[stage],expectedCamera,sizeof(camera));copy(snapAlt[stage],expectedAlt,sizeof(camera));copy(snapActors[stage],expectedActors,sizeof(D_800CC2D0));snapPi[stage]=expectedPi;
      effect(expectedCamera,expectedAlt,expectedActors,&expectedPi,stage);offset=value(stage?row->cosine:row->sine)*60.0f;
      if(!stage){wr32(expectedCamera+0x2FC,rd32(expectedCamera+0x2C0));wr32(expectedCamera+0x2F8,word(value(rd32(expectedCamera+0x2BC))-offset));}
      else wr32(expectedCamera+0x300,word(value(rd32(expectedCamera+0x2C4))-offset));
     }
    }
    static __attribute__((noinline,noclone)) f32 provider(u32 stage,f32 angle){
     u32 pi=word(D_800A3730);
     if(stage!=currentStage++||word(angle)!=angleWord||!equal((u8*)&camera,snapCamera[stage],sizeof(camera))||!equal((u8*)&alternate,snapAlt[stage],sizeof(camera))||!equal((u8*)D_800CC2D0,snapActors[stage],sizeof(D_800CC2D0))||pi!=snapPi[stage])error=1;
     effect((u8*)&camera,(u8*)&alternate,(u8*)D_800CC2D0,&pi,stage);D_800A3730=value(pi);return value(stage?row->cosine:row->sine);
    }
    __attribute__((noinline,noclone)) f32 sinf(f32 angle){return provider(0,angle);}
    __attribute__((noinline,noclone)) f32 cosf(f32 angle){return provider(1,angle);}
    '''+selected+'\n'
    for name,b in controls().items():program+=b.replace('func_1512E4B0(','negative_'+name+'(',1)+'\n'
    program+='''
    typedef void(*CameraUpdate)(struct108*);
    static int test(CameraUpdate fn){
     u32 n,i,j;u8*a;
     for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
      row=&rows[n];
      for(i=0;i<sizeof(camera);i++){((u8*)&camera)[i]=(u8)(i*29+0x5A);((u8*)&alternate)[i]=(u8)(i*29+0x5A);}
      for(i=0;i<sizeof(D_800CC2D0);i++)((u8*)D_800CC2D0)[i]=(u8)(i*29+0x5A);
      for(j=0;j<26;j++){a=(u8*)&D_800CC2D0[j];wr32(a+20,word(j+1.0f));wr32(a+24,word((f32)j-3.0f));wr32(a+28,word(-(f32)j-5.0f));wr32(a+64,word((f32)j/4.0f));wr16(a+0x2E4,j*13);}
      a=(u8*)&D_800CC2D0[row->view==3?1:0];wr32(a+20,row->x);wr32(a+24,row->y);wr32(a+28,row->z);wr32(a+64,row->speed);wr16(a+0x2E4,row->heading);wr16(a+0x2E6,0x7ABC);
      camera.unk23D=(u8)row->view;D_800A3730=value(row->pi);
      copy(expectedCamera,(u8*)&camera,sizeof(camera));copy(expectedAlt,(u8*)&alternate,sizeof(camera));copy(expectedActors,(u8*)D_800CC2D0,sizeof(D_800CC2D0));expectedPi=row->pi;model();
      error=currentStage=0;fn(&camera);
      if(error||currentStage!=2||!equal((u8*)&camera,expectedCamera,sizeof(camera))||!equal((u8*)&alternate,expectedAlt,sizeof(camera))||!equal((u8*)D_800CC2D0,expectedActors,sizeof(D_800CC2D0))||word(D_800A3730)!=expectedPi)return 1;
     }
     return 0;
    }
    static __attribute__((noinline,noclone)) int aliasProbe(struct127*a,ActorHeadingHalfword15B960*h){a->unk2E4=0;*h=0x1234;return a->unk2E4==0x1234;}
    static int run(void){
     if(!aliasProbe(D_800CC2D0,(ActorHeadingHalfword15B960*)((u8*)D_800CC2D0+0x2E4)))return 2;
     if(test(func_1512E4B0))return 3;
    '''
    for j,name in enumerate(controls()):program+=' if(!test(negative_%s))return %d;\n'%(name,10+j)
    program+=' return 0;\n}\n'+START
    (out/'native.c').write_text(program)
    profiles=[]
    for opt in('-O0','-O2','-O3'):
     binary=out/('native'+opt);cmd=native_command(opt)+['-fstrict-aliasing','-Wstrict-aliasing=2','-fsanitize=float-cast-overflow','-fno-builtin','-mstackrealign',str(out/'native.c'),'-o',str(binary)]
     p=subprocess.run(cmd,cwd=root,capture_output=True,text=True);(out/('native'+opt+'-build.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
     p=subprocess.run([str(binary)],capture_output=True);assert p.returncode==0,(opt,p.returncode)
     profiles.append(dict(profile=opt,cases=len(cases),semantic_controls=len(controls()),strict_aliasing=True,UBSan_and_float_cast_overflow_traps=True));print(json.dumps(profiles[-1]),flush=True)
    alias_program=program.replace('__attribute__((__may_alias__))','');(out/'native-no-alias-control.c').write_text(alias_program)
    narrow=selected.replace('    s32 heading;','    s16 heading;').replace('    heading = (s16)heading;\n','')
    (out/'narrow-IDO.c').write_text(header+narrow)
    narrow_program=program.replace(selected,narrow,1);(out/'native-narrow-control.c').write_text(narrow_program)
    extra=[]
    for opt in('-O0','-O2','-O3'):
     row=dict(profile=opt)
     for label in('no-alias','narrow'):
      binary=out/('native-'+label+'-control'+opt);p=subprocess.run(native_command(opt)+['-fstrict-aliasing','-fsanitize=float-cast-overflow','-fno-builtin','-mstackrealign',str(out/('native-'+label+'-control.c')),'-o',str(binary)],cwd=root,capture_output=True,text=True);assert p.returncode==0,p.stderr
      rc=subprocess.run([str(binary)],capture_output=True).returncode
      if label=='no-alias':assert rc==(0 if opt=='-O0'else 2),(label,opt,rc)
      else:assert rc!=0,(label,opt,rc)
      row[label]=rc
     extra.append(row)
    v=dict(cases_per_profile=len(cases),profiles=profiles,semantic_controls=len(controls()),native_only_controls=extra,typed_void_camera_callback=True,struct127_size=812,records=26,struct108_size=0x9A0,all_actor_camera_and_PI_bytes=True,fullword_float_conversion_domain=True,halfword_representation_explicit=True,generic_ISO_portability_claim=False)
    (out/'native-contract.json').write_text(json.dumps(v,indent=2)+'\n');return v
