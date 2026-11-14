"""Native32 wave banks, aliased views, live providers and semantic controls."""
from pathlib import Path
import json,os,subprocess
from tools.tests import game_wave_vertices_15179db0_oracle as b
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/b.source.BUILD;body=b.source.SELECTED
    controls={
        'wrong_bank':body.replace('vertices[1] = D_800DDE80[index].first','vertices[1] = D_800DDE80[index].second'),
        'wrong_center':body.replace('vertices[i][2]','vertices[i][1]'),
        'wrong_negative_half':body.replace('displacement >> 1','displacement / 2'),
        'missing_seventh_index':body.replace('j < 7','j < 6'),
        'wrong_wrap_equality':body.replace('>= 360.0f','> 360.0f'),
        'uncached_factor':body.replace('* factor','* D_800A7218').replace('    f32 factor;\n','').replace('    factor = D_800A7218;\n',''),
    }
    assert all(v!=body for v in controls.values())
    arr=lambda v:'{'+','.join('0x%Xu'%b.u32(x) for x in v)+'}'
    code='#include <ultra64.h>\n'+b.source.EXTRA+r'''
typedef union{u32 u;f32 f;}Bits;
typedef struct{u32 bank,offset,value;}Patch;
typedef struct{u32 index,alias,mutation,seed,phases[2],steps[2],amplitude,samples[2],factor,indices[7];
u8 state[56],resources[20],lastIndices[7];u32 lastFactor,patches;Patch changes[48];u32 args[2],observations[2];}Case;
static const Case cases[]={
'''
    rows=[]
    for c in b.cases():
        if c.phase or c.mutation&2 or c.index&255 not in (8,9) or any(v>19 for v in c.indices):continue
        initial=b.fixture(c);final,calls,obs,boundary=b.reference(initial,c)
        if boundary is not None:continue
        changes=[]
        for bank,base in enumerate((b.FIRST,b.SECOND,b.ALT)):
            for i in range(512):
                if initial[base+i]!=final[base+i]:changes.append('{%d,%d,%d}'%(bank,i,final[base+i]))
        assert len(changes)<=48 and len(calls)==2
        fields=(c.index,c.alias,c.mutation,c.seed)
        rows.append('{'+','.join('0x%Xu'%b.u32(v) for v in fields)+','+','.join(arr(v) for v in (c.phases,c.steps))+','+
                    '0x%Xu,'%c.amplitude+arr(c.samples)+',0x%Xu,'%c.factor+arr(c.indices)+','+
                    ','.join(arr(v) for v in ([final[b.address(c)+i] for i in range(56)],
                    [final[b.resource(c)+i] for i in range(20)],[final[b.INDICES+i] for i in range(7)]))+
                    ',0x%Xu,%d,{%s},%s,%s}'%(b.read(final,b.FACTOR),len(changes),','.join(changes),
                    arr([a[0] for _,a in calls]),arr(obs)))
    code+=',\n'.join(rows)+'\n};\n'+r'''
WaveBuffers15179DB0 D_800DDE80[11];WaveState15179DB0 D_8008D0B0[11];
u8 D_800A7210[7];f32 D_800A7218;static Vtx storage[3][32];static const Case*current;static u32 calls,error;
static u32 slot(void){return current->index&255;}static f32 real(u32 u){Bits b;b.u=u;return b.f;}
static u32 word(f32 f){Bits b;b.f=f;return b.u;}
static u32 bankIndex(u32 k){return k%16<2?k^1u:k;}
static u32 stateIndex(u32 k){return k>=0x18&&k<0x2c?k^3u:k;}
static u32 canon(u32 p){u32 i,start;for(i=0;i<3;i++){start=(u32)storage[i];if(p>=start&&p<start+512)return 0x50000u+i*0x10000u+p-start;}return p;}
static u32 resourceByte(u32 k){WaveBuffers15179DB0*r=&D_800DDE80[slot()];u32 v=k/4==0?r->owner:k/4==1?(u32)r->first:k/4==2?(u32)r->second:r->retained0C[k/4-3];
if(k/4==1||k/4==2)v=canon(v);return v>>(24-(k%4)*8)&255u;}
static u32 digest(void){u32 i,j,h=2166136261u,v;u8*s=(u8*)&D_8008D0B0[slot()];
for(j=0;j<3;j++)for(i=0;i<512;i++)h=(h^((u8*)storage[j])[bankIndex(i)])*16777619u;
for(i=0;i<56;i++)h=(h^s[stateIndex(i)])*16777619u;
for(i=0;i<20;i++)h=(h^resourceByte(i))*16777619u;
for(i=0;i<7;i++)h=(h^D_800A7210[i])*16777619u;
v=word(D_800A7218);for(i=0;i<4;i++)h=(h^(v>>(24-i*8)&255u))*16777619u;return h;}
__attribute__((noinline)) f32 sinf(f32 argument){u32 i,n=calls++;WaveState15179DB0*s=&D_8008D0B0[slot()];
if(n>=2){error=1;return 0.0f;}if(word(argument)!=current->args[n]||digest()!=current->observations[n])error=1;
if(current->mutation&1){s->amplitude=-21.5f+n*.5f;s->phase[n]=720.0f+n+.5f;s->step[0]=30.0f+n;s->step[1]=-1.25f+n;
D_800A7218=2.0f+n;D_800DDE80[slot()].first=storage[2];D_800DDE80[slot()].second=storage[2];
for(i=0;i<7;i++)D_800A7210[i]=(u8[]){2,3,6,8,19,1,17}[i];
((u8*)storage[0])[bankIndex(0x1f1)]^=(u8)(n+1);((u8*)storage[1])[bankIndex(0x1f2)]^=(u8)(n+1);}
return real(current->samples[n]);}
'''
    for i,candidate in enumerate([body,*controls.values()]):code+='\n'+candidate.replace(b.source.NAME,'candidate_'+str(i))+'\n'
    code+='\nstatic void(*tests[])(u8)={'+','.join('candidate_'+str(i) for i in range(7))+'};\n'+r'''
static int run(void){u32 n,t,i,j,k,v,killed=0;WaveState15179DB0*s;WaveBuffers15179DB0*r;u8*bytes;
if(sizeof(WaveState15179DB0)!=56||sizeof(WaveBuffers15179DB0)!=20||sizeof(Vtx)!=16)return 20;
for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){current=cases+n;for(t=0;t<7;t++){
for(j=0;j<3;j++)for(i=0;i<512;i++)((u8*)storage[j])[bankIndex(i)]=(u8)(i*29+current->seed*11+0x5a);
s=&D_8008D0B0[slot()];bytes=(u8*)s;for(i=0;i<56;i++)bytes[stateIndex(i)]=(u8)(i*19+current->seed+0xa5);
r=&D_800DDE80[slot()];bytes=(u8*)r;for(i=0;i<20;i++)bytes[i^3u]=(u8)(i*23+current->seed+0x5a);
r->first=storage[0];r->second=current->alias==1?storage[0]:current->alias==2?storage[0]+1:storage[1];
for(i=0;i<2;i++){s->phase[i]=real(current->phases[i]);s->step[i]=real(current->steps[i]);}
s->amplitude=real(current->amplitude);D_800A7218=real(current->factor);
for(i=0;i<7;i++)D_800A7210[i]=(u8)current->indices[i];calls=error=0;tests[t]((u8)current->index);
if(calls!=2)error=1;for(j=0;j<3;j++)for(i=0;i<512;i++){v=(u8)(i*29+current->seed*11+0x5a);
for(k=0;k<current->patches;k++)if(current->changes[k].bank==j&&current->changes[k].offset==i)v=current->changes[k].value;
if(((u8*)storage[j])[bankIndex(i)]!=v)error=1;}
bytes=(u8*)s;for(i=0;i<56;i++)if(bytes[stateIndex(i)]!=current->state[i])error=1;
for(i=0;i<20;i++)if(resourceByte(i)!=current->resources[i])error=1;
for(i=0;i<7;i++)if(D_800A7210[i]!=current->lastIndices[i])error=1;if(word(D_800A7218)!=current->lastFactor)error=1;
if(error){if(!t)return 10;killed|=1u<<(t-1);}}}return killed==63u?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    p=out/'native.c';p.write_text(code)
    for opt in ('-O0','-O2','-O3'):
        exe=out/('native'+opt);q=subprocess.run(native_command(opt)+['-o',str(exe),str(p)],cwd=root,capture_output=True,text=True)
        assert q.returncode==0,(q.stdout,q.stderr)
        q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr)
    report=dict(native32=True,cases=len(rows),profiles=['-O0','-O2','-O3'],ubsan=True,
                negative_controls=list(controls),all_controls_detected=True,vertex_bytes=1536,
                configuration_bytes=56,resource_bytes=20,alias_layouts=3,provider_observations=True,
                invalid_conversions_and_guest_only_indices_excluded=True)
    (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=='__main__':main()
