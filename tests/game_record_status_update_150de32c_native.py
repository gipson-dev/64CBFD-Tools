"""Native32 defined-C contract with strict aliasing, UBSan and effective controls."""
import json,subprocess,sys
from pathlib import Path
from tools.experiments.game_record_status_update_150de32c_match import ROOT,BUILD,NEW_SOURCE
root=ROOT;out=root/BUILD
from tools.tests import game_record_status_update_150de32c_oracle as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
source=NEW_SOURCE;selected=body(source,'func_150DE32C');header=source[:source.index('/* Query eight')]
def controls():
 rows={
 'seven_records':selected.replace('i < 8','i < 7'),
 'wrong_stride':selected.replace('&D_800D3098[*entry]','((u8*)D_800D3098+51*(*entry))'),
 'swapped_coordinates':selected.replace(', x, y, z)',', z, y, x)'),
 'coordinate_truncation':selected.replace(', x, y, z)',', (s16)x, (s16)y, (s16)z)'),
 'signed_tag':selected.replace('if (((u8 *)&tags)[i])','if ((s8)((u8 *)&tags)[i] > 0)'),
 'wrong_flag_mask':selected.replace('& ~3','& ~7'),
 'wrong_status':selected.replace('func_150A2864(*entry, 1)','func_150A2864(*entry, 0)'),
 'positive_only':selected.replace(', x, y, z))',', x, y, z) > 0)'),
 'live_tags':selected.replace('((u8 *)&tags)[i]','((u8 *)&D_80088958)[i]'),
 'live_indices':selected.replace('entry = (u8 *)&indices','entry = (u8 *)&D_80088950'),
 }
 cached=selected.replace('    RouteBytes10B7D0 indices;','    GeneratedCDE80Record *base = D_800D3098;\n    RouteBytes10B7D0 indices;').replace('&D_800D3098[*entry]','&base[*entry]');rows['cached_record_base']=cached
 rows['live_tags']=rows['live_tags'].replace('    tags = D_80088958;','    tags = D_80088958;\n    (void)tags;')
 rows['live_indices']=rows['live_indices'].replace('    indices = D_80088950;','    indices = D_80088950;\n    (void)indices;')
 assert all(v!=selected for v in rows.values());return rows
def main():
 cases=list(guest.cases())+[guest.Case(pattern=p,mutation=p%4)for p in range(256)]
 rows='\n'.join('{'+','.join('0x%Xu'%guest.u32(v)for v in(c.x,c.y,c.z,c.mask,c.mutation,c.pattern,c.result))+'},'for c in cases)
 program=header+r'''
_Static_assert(sizeof(void*)==4,"native32");
_Static_assert(sizeof(GeneratedCDE80Record)==52,"record stride");
_Static_assert(__builtin_offsetof(GeneratedCDE80Record,disabled)==20,"status byte");
typedef struct {s32 x,y,z;u32 mask,mutation,pattern; s32 result;} Fixture;
static const Fixture fixtures[]={
'''+rows+r'''
};
RouteBytes10B7D0 D_80088950,D_80088958;
static GeneratedCDE80Record banks[2][256];GeneratedCDE80Record *D_800D3098;
static u8 actors[256][160],expectedActors[256][160],expectedStatus[2][256],expectedIndices[8],expectedTags[8],ids[8],tt[8];
static u64 active[112],expectedActive[112];static u32 q,error,events,expectedEvents;static const Fixture*c;
static void effect(u32 i){u32 j;if(c->mutation&1)D_800D3098=banks[i%2?0:1];if(c->mutation&2)for(j=0;j<8;j++){((u8*)&D_80088950)[j]^=(17+i);((u8*)&D_80088958)[j]^=(17+i);}}
__attribute__((noinline,noclone)) s32 func_150A32B4(s32 address,s32 x,s32 y,s32 z){u32 i=q;if(i>=8){error=1;return 0;}
 if(address!=(s32)&banks[(c->mutation&1)&&i?i%2:0][ids[i]]||x!=c->x||y!=c->y||z!=c->z)error=2;
 effect(i);q++;events++;return(c->mask>>i&1)?c->result:0;}
__attribute__((noinline,noclone)) u8*func_151149AC(u8 tag){u32 i=q-1;if(i>=8||tag!=tt[i]||!tag||!(c->mask>>i&1))error=3;events++;return actors[tag];}
__attribute__((noinline,noclone)) void func_150A2864(u32 id,s32 status){u32 i=q-1,j;if(i>=8||tt[i]||id!=ids[i]||status!=1||!(c->mask>>i&1))error=4;
 if(id<256)D_800D3098[id].disabled=(u8)status;if(status==1)for(j=0;j<16;j++)active[j*3+(id>>6)]&=~(1ULL<<(id&63));events++;}
'''+selected+'\n'
 for name,b in controls().items():program+=b.replace('func_150DE32C(','negative_'+name+'(',1)+'\n'
 program+=r'''
typedef void(*Update)(s32,s32,s32);
static int check(Update fn){u32 n,i,j,bank;for(n=0;n<sizeof(fixtures)/sizeof(fixtures[0]);n++){c=fixtures+n;q=error=events=expectedEvents=0;D_800D3098=banks[0];
 for(i=0;i<2;i++)for(j=0;j<256;j++){banks[i][j].disabled=(u8)(j*13+i*17);expectedStatus[i][j]=banks[i][j].disabled;}
 for(i=0;i<sizeof(actors);i++)((u8*)actors)[i]=((u8*)expectedActors)[i]=(u8)(i*29+0x59+c->pattern*11);
 for(i=0;i<112;i++)active[i]=expectedActive[i]=0xFEDCBA9876543210ULL^((u64)i*0x1030507090B0D0FULL);
 for(i=0;i<8;i++){ids[i]=c->pattern?(u8)(c->pattern*31+i*37):((u8[]){24,25,26,27,13,48,49,50})[i];tt[i]=c->pattern?(i%3?(u8)(c->pattern*43+i*29):0):((u8[]){246,243,240,237,0,0,0,0})[i];
 ((u8*)&D_80088950)[i]=expectedIndices[i]=ids[i];((u8*)&D_80088958)[i]=expectedTags[i]=tt[i];}
 bank=0;for(i=0;i<8;i++){expectedEvents++;if(c->mutation&1)bank=i%2?0:1;
 if(c->mutation&2)for(j=0;j<8;j++){expectedIndices[j]^=(17+i);expectedTags[j]^=(17+i);}
 if(c->mask>>i&1){expectedEvents++;if(tt[i])expectedActors[tt[i]][115]=(expectedActors[tt[i]][115]&252)|3;
 else{expectedStatus[bank][ids[i]]=1;for(j=0;j<16;j++)expectedActive[j*3+(ids[i]>>6)]&=~(1ULL<<(ids[i]&63));}}}
 fn(c->x,c->y,c->z);if(error||q!=8||events!=expectedEvents||D_800D3098!=banks[bank])return 1;
 for(i=0;i<8;i++)if(((u8*)&D_80088950)[i]!=expectedIndices[i]||((u8*)&D_80088958)[i]!=expectedTags[i])return 2;
 for(i=0;i<2;i++)for(j=0;j<256;j++)if(banks[i][j].disabled!=expectedStatus[i][j])return 3;
 for(i=0;i<sizeof(actors);i++)if(((u8*)actors)[i]!=((u8*)expectedActors)[i])return 4;
 for(i=0;i<112;i++)if(active[i]!=expectedActive[i])return 5;
 }return 0;}
static int run(void){if(check(func_150DE32C))return 10;
'''
 for i,k in enumerate(controls()):program+='if(!check(negative_'+k+'))return '+str(20+i)+';\n'
 program+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=out/'native.c';p.write_text(program);profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr)
  profiles[opt]=dict(exit=0,cases=len(cases),UBSan=True,strict_aliasing=True,effective_controls=len(controls()))
 report=dict(profiles=profiles,cases_per_profile=len(cases),effective_semantic_controls=list(controls()),all_actor_bytes_checked=True,record_status_and_active_set_checked=True,record_address_argument_s32=True,signed_coordinates=True,unsigned_tags=True)
 (out/'native-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
