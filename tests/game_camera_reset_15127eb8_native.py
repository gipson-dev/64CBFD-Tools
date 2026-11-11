"""SDK32 native camera reset against independent reference and controls."""
import itertools,json,subprocess
from tools.experiments import game_camera_reset_15127eb8_match as p
from tools.tests import game_camera_reset_15127eb8_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 source=(p.out/'selected-source.c').read_text();selected=p.body(source,p.NAME)
 controls={'enable':('func_151239CC(camera, 1);','func_151239CC(camera, 2);'),'child':('unk197 = 0','unk197 = 1'),'reset':('func_151C9ED4(camera);','(void)0;'),'position':('camera->unk19C = 0.0f','camera->unk19C = 1.0f'),'direction':('0.0f, 0.0f, 1.0f);','0.0f, 0.0f, 2.0f);'),'view':('+ 0x84) = 1.0f','+ 0x80) = 1.0f'),'slot':('] = 2;','] = 3;'),'actor_index':('original->unk65 - 1','original->unk65'),'mask1':('~(1 << camera->unk23D)','~(2 << camera->unk23D)'),'mask2':('actor->unk74 &= ~(1 << camera->unk23D)','actor->unk74 &= ~(2 << camera->unk23D)'),'active':('camera->unk23C = 1','camera->unk23C = 0')}
 def digest(calls):
  h=2166136261
  for target,args in calls:
   tag={g.ENABLE:1,g.RESET:2,g.DIRECTION:3,g.RELEASE:4}[target];a=list(args)+[0]*(4-len(args))
   if target in(g.ENABLE,g.RESET):a[0]=1
   if target==g.RELEASE:a[0]={g.ACTOR0:1,g.ACTOR1:2}[a[0]]
   for x in (tag,*a):h=((h^g.u32(x))*16777619)&0xffffffff
  return h
 rows=[]
 for i,(slot,idx,mut) in enumerate(itertools.product(range(4),range(4),(0,1,2,4,8,3,12,15))):
  c=g.Case(slot,idx,mut,0,i%3);m,calls=g.reference(c,g.fixture(c));flags=[]
  for actor in (g.ACTOR0,g.ACTOR1,*(g.ACTORS+i*0x32c for i in range(4))):flags.extend((m[actor+0x74],m[actor+0x2fc]))
  views=[g.read(m,base+slot2*0x180+0x84)for base in (g.VIEW0,g.VIEW1)for slot2 in range(4)]
  vals=(digest(calls),len(calls),m[g.CHILD0+0x197],m[g.CHILD1+0x197],m[g.CAMERA+0x23c],m[g.CAMERA+0x23d],int(g.read(m,g.CAMERA+0x3d4)==g.CHILD1),int(g.read(m,g.CAMERA+0x3d0)==g.ACTOR1));positions=[g.read(m,g.CAMERA+o)for o in (0x19c,0x1a0,0x1a4,0x1a8)];slots=[m[g.SLOTS+k]for k in range(4)];rows.append((c,vals,positions,flags,views,slots))
 code='#include <ultra64.h>\n#include "structs.h"\n'+r'''
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(struct127)==0x32c,"SDK32 layout");
 typedef struct {u32 slot,idx,mutation,seed,hash,calls,child0,child1,active,finalslot,whichchild,whichactor,pos[4],flags[12],views[8],slots[4];} Fixture;
 static struct108 camera;static struct127 child0,child1,actor0,actor1;struct127 D_800CC2D0[26];static f32 view0[512],view1[512];s32 D_800BE628;u8 D_800DBFF4[32];static const Fixture *cur;static u32 h,calls,bad;
 static void fill(void *p,u32 n,u32 seed){u8 *q=p;u32 i;for(i=0;i<n;i++)q[i]=(u8)(i*29+seed*11+0x5a);}
 static u32 read32(void *p){u8 *q=p;return ((u32)q[0]<<24)|((u32)q[1]<<16)|((u32)q[2]<<8)|q[3];}
 /* Native is little-endian; read integer bit patterns directly through a union. */
 static u32 word(void *p){union {u32 u;u8 b[4];}v;u8 *q=p;u32 i;for(i=0;i<4;i++)v.b[i]=q[i];return v.u;}
 static void setword(void *p,u32 n){union {u32 u;u8 b[4];}v;u8 *q=p;u32 i;v.u=n;for(i=0;i<4;i++)q[i]=v.b[i];}
 static u32 patternword(u32 off,u32 seed){u32 j,v=0;for(j=0;j<4;j++)v=(v<<8)|((off*29+j*29+seed*11+0x5a)&255);return v;}
 static void event(u32 t,u32 a,u32 b,u32 c,u32 d){u32 v[5],i;v[0]=t;v[1]=a;v[2]=b;v[3]=c;v[4]=d;for(i=0;i<5;i++)h=(h^v[i])*16777619u;calls++;}
 static u32 actorid(struct127 *p){if(p==&actor0)return 1;if(p==&actor1)return 2;return 99;}
 void func_151239CC(struct108 *p,s32 v){event(1,(u32)(p==&camera),(u32)v,0,0);if(cur->mutation&1)camera.unk3D4=&child1;}
 void func_151C9ED4(struct108 *p){event(2,(u32)(p==&camera),0,0,0);if(cur->mutation&2)camera.unk23D=(cur->slot+1)%4;}
 void func_1510B32C(s32 n,f32 x,f32 y,f32 z){union{f32 f;u32 u;}a,b,c;a.f=x;b.f=y;c.f=z;event(3,n,a.u,b.u,c.u);if(cur->mutation&4){D_800BE628=(s32)view1;camera.unk23D=(cur->slot+2)%4;}}
 void func_150627D4(struct127 *p){event(4,actorid(p),0,0,0);if(cur->mutation&8){camera.unk3D0=&actor1;camera.unk23D=(cur->slot+3)%4;}}
 '''
 # read32 is deliberately not needed: all native values are read in host order.
 code=code.replace('static u32 read32(void *p){u8 *q=p;return ((u32)q[0]<<24)|((u32)q[1]<<16)|((u32)q[2]<<8)|q[3];}\n','')
 for name,text in {'selected':selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if name!='selected':assert text!=selected,name
  code+='\n'+text.replace(p.NAME,'test_'+name,1)+'\n'
 code+='\nstatic const Fixture fixtures[]={\n'
 arr=lambda a:','.join(str(x&0xffffffff)+'u' for x in a)
 for c,vals,pos,flags,views,slots in rows:code+='{'+arr((c.slot,c.actor_index,c.mutation,c.seed,*vals))+',{'+arr(pos)+'},{'+arr(flags)+'},{'+arr(views)+'},{'+arr(slots)+'}},\n'
 code+='};\n'+r'''
 typedef void(*Update)(struct108*);
 static int check(Update fn){u32 n,i;u8 *cb=(u8*)&camera,*a[6],*v[2]={(u8*)view0,(u8*)view1};for(n=0;n<CASE_COUNT;n++){cur=fixtures+n;fill(&camera,sizeof(camera),cur->seed);fill(&child0,sizeof(child0),cur->seed);fill(&child1,sizeof(child1),cur->seed);fill(&actor0,sizeof(actor0),cur->seed);fill(&actor1,sizeof(actor1),cur->seed);fill(D_800CC2D0,sizeof(struct127)*4,cur->seed);fill(view0,sizeof(view0),cur->seed);fill(view1,sizeof(view1),cur->seed);for(i=0;i<4;i++){u32 off=i*0x180+0x84;setword((u8*)view0+off,patternword(off,cur->seed));setword((u8*)view1+off,patternword(off,cur->seed));}fill(D_800DBFF4,sizeof(D_800DBFF4),cur->seed);camera.unk3D4=&child0;camera.unk3D0=&actor0;camera.unk23D=cur->slot;actor0.unk65=actor1.unk65=cur->idx;D_800BE628=(s32)view0;h=2166136261u;calls=bad=0;fn(&camera);
 if(h!=cur->hash||calls!=cur->calls||bad||((u8*)&child0)[0x197]!=cur->child0||((u8*)&child1)[0x197]!=cur->child1||cb[0x23c]!=cur->active||cb[0x23d]!=cur->finalslot||(u32)(camera.unk3D4==&child1)!=cur->whichchild||(u32)(camera.unk3D0==&actor1)!=cur->whichactor)return 1;
 for(i=0;i<4;i++)if(word(cb+0x19c+4*i)!=cur->pos[i]||D_800DBFF4[i]!=cur->slots[i])return 1;a[0]=(u8*)&actor0;a[1]=(u8*)&actor1;for(i=0;i<4;i++)a[i+2]=(u8*)&D_800CC2D0[i];for(i=0;i<6;i++)if(a[i][0x74]!=cur->flags[2*i]||a[i][0x2fc]!=cur->flags[2*i+1])return 1;for(i=0;i<8;i++)if(word(v[i/4]+(i%4)*0x180+0x84)!=cur->views[i])return 1;}return 0;}
 static int run(void){if(check(test_selected))return 10;
 '''.replace('CASE_COUNT',str(len(rows)))
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');src=p.out/'native.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
  exe=p.out/('native'+opt);v=subprocess.run(native_command(opt)+[str(src),'-o',str(exe)],cwd=p.root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr);v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(rows),negative_controls=len(controls),UBSan=True)
 result=dict(profiles=reports,slot_range='0..3',helpers_modeled=True,source_installed=False);(p.out/'native.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
