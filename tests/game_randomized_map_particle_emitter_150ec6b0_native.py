"""SDK32 semantic C checks using defined packet fields and independent vectors."""
from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_randomized_map_particle_emitter_150ec6b0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_randomized_map_particle_emitter_150ec6b0_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
FIELDS=[(0,4),(4,4),(8,2),(10,2),(12,4),(16,4)]+[(i,1)for i in range(20,30)]+[(i,2)for i in(30,32,34)]+[(i,4)for i in range(36,92,4)]+[(i,1)for i in range(96,102)]
EXTRA=[(0,1),(1,1),(2,1),(3,1),(4,4),(8,4),(12,4)]
def values(data,fields):return [int.from_bytes(bytes(data[o:o+n]),'big')for o,n in fields]
def hash_output(memory):
    h=2166136261
    for i in range(8):
        p=g.OUTPUT+192*i
        words=values([memory[p+16+j]for j in range(112)],FIELDS)+values([memory[p+168+j]for j in range(16)],EXTRA)+[memory[p+156]]
        for word in words:
            for byte in word.to_bytes(4,'big'):h=((h^byte)*16777619)&0xFFFFFFFF
    return h
def vectors():
    rows=[];steps=[]
    for c in [c for c in g.cases()if c.fcsr==0 and c.phase==0]:
        memory=g.fixture(c);final,calls,observations,fcsr=g.reference(memory,c);start=len(steps)
        for (target,args),obs in zip(calls,observations):
            args=list(args)+[0]*(6-len(args))
            if target==g.FACTORY:args[0]=1
            if target==g.COPY:args[1]=1
            record=obs[2];before=[int.from_bytes(bytes(record[i:i+4]),'big')for i in(40,44,48,52)]+[record[12],record[1],obs[3]]
            data=values(obs[0],FIELDS)if target==g.FACTORY else [0]*len(FIELDS)
            extra=values(obs[1],EXTRA)if target==g.COPY else [0]*7
            steps.append((target,args,before,data,extra))
        rows.append((c,start,len(calls),g.read(final,g.RECORD+52),hash_output(final)))
    arr=lambda a:'{'+','.join('0x%Xu'%g.u32(x)for x in a)+'}'
    text=f'typedef struct{{u32 target,args[6],before[7],data[{len(FIELDS)}],extra[7];}}Step;\n'
    text+='typedef struct{u32 accumulator,timestep,floats[5],floatCount,integers[10],integerCount,mask,mode,priority,context,start,count,finalAccumulator,outputHash;}Row;\n'
    text+='static const Step steps[]={'+','.join('{'+f'0x{t:X}u,'+','.join(map(arr,(a,b,d,e)))+'}'for t,a,b,d,e in steps)+'};\n'
    text+='static const Row rows[]={'+','.join('{'+','.join((f'0x{c.accumulator:X}u',f'0x{c.timestep:X}u',arr(list(c.float_draws)+[0]*(5-len(c.float_draws))),str(len(c.float_draws)),arr(list(c.integer_draws)+[0]*(10-len(c.integer_draws))),str(len(c.integer_draws)),str(c.allocation_mask),str(c.mode),str(c.priority),str(c.context),str(start),str(count),f'0x{final:X}u',f'0x{h:X}u'))+'}'for c,start,count,final,h in rows)+'};\n'
    text+='static const u32 fields[][2]={'+','.join('{%d,%d}'%v for v in FIELDS)+'};\n'
    text+='static const u32 extraFields[][2]={'+','.join('{%d,%d}'%v for v in EXTRA)+'};\n'
    (out/'native-vectors.h').write_text(text);return len(rows)
HARNESS=r'''
#define OFF __builtin_offsetof
typedef char layouts[sizeof(void*)==4&&sizeof(struct260)==36&&sizeof(RandomParticleRecord1199D0)==56&&OFF(RandomParticleRecord1199D0,emitter)==40&&sizeof(RandomParticleDefinition1199D0)==112&&sizeof(RandomParticleExtra1199D0)==16?1:-1];
static RandomParticleRecord1199D0 record;static u32 outputWords[8][48];
static u32 rowIndex,stepIndex,floatCount,integerCount,factoryCount,copyCount,bad;
static RandomParticleDefinition1199D0*captured;f32 D_800BE9A4;
typedef union{u32 word;f32 number;}FloatBits;
static u32 raw(f32 v){FloatBits x;x.number=v;return x.word;}
static f32 number(u32 v){FloatBits x;x.word=v;return x.number;}
static void check(int ok){if(!ok)bad=1;}
static u32 field(const void*p,u32 at,u32 bytes){const u8*b=(const u8*)p;u32 value=0,i;for(i=0;i<bytes;i++)value|=(u32)b[at+i]<<(8*i);return value;}
static void copyBytes(void*to,const void*from,u32 n){u32 i;for(i=0;i<n;i++)((u8*)to)[i]=((const u8*)from)[i];}
static u32 hashWord(u32 h,u32 word){s32 i;for(i=24;i>=0;i-=8)h=(h^((word>>i)&255))*16777619u;return h;}
static u32 outputHash(void){u32 h=2166136261u,i,j;for(i=0;i<8;i++){u8*p=(u8*)outputWords[i];for(j=0;j<sizeof(fields)/sizeof(fields[0]);j++)h=hashWord(h,field(p+16,fields[j][0],fields[j][1]));for(j=0;j<7;j++)h=hashWord(h,field(p+168,extraFields[j][0],extraFields[j][1]));h=hashWord(h,p[156]);}return h;}
static const Step*call(u32 target,const u32*args,u32 n){const Row*r=&rows[rowIndex];u32 i;check(stepIndex<r->count);if(bad)return &steps[0];const Step*s=&steps[r->start+stepIndex++];check(s->target==target);for(i=0;i<n;i++)check(args[i]==s->args[i]);check(raw(record.emitter.position.x)==s->before[0]&&raw(record.emitter.position.y)==s->before[1]&&raw(record.emitter.position.z)==s->before[2]&&raw(record.emitter.accumulator)==s->before[3]);check(((u8*)&record)[12]==s->before[4]&&((u8*)&record)[1]==s->before[5]&&raw(D_800BE9A4)==s->before[6]);return s;}
f32 func_150ADA68(void){const Row*r=&rows[rowIndex];call(0x150ADA68,0,0);if(floatCount==0&&(r->mode&1)){D_800BE9A4=.5f;record.emitter.accumulator=2.5f;}return number(r->floats[floatCount++%r->floatCount]);}
u32 func_150ADA20(void){const Row*r=&rows[rowIndex];call(0x150ADA20,0,0);++integerCount;if(r->mode&8){((u8*)&record)[12]=(u8)(r->priority+integerCount);((u8*)&record)[1]=(u8)(r->context^integerCount);}return r->integers[(integerCount-1)%r->integerCount];}
void*func_15130280(RandomParticleDefinition1199D0*definition,u8 kind,void*data,s32 bytes,u8 priority,s32 context){const Row*r=&rows[rowIndex];u32 i,args[6]={1,kind,(u32)data,(u32)bytes,priority,(u32)context};const Step*s=call(0x15130280,args,6);captured=definition;for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++)check(field(definition,fields[i][0],fields[i][1])==s->data[i]);++factoryCount;check(factoryCount<=8);if(bad)return 0;if(r->mode&2)++definition->rgba14[0];if(!(r->mask&(1u<<(factoryCount-1))))return 0;u8*p=(u8*)outputWords[factoryCount-1];copyBytes(p+16,definition,112);p[156]=0;return p;}
void*memcpy(void*destination,const void*source,u32 bytes){const Row*r=&rows[rowIndex];u32 i,index=8;for(i=0;i<8;i++)if(destination==(u8*)outputWords[i]+168)index=i;u32 args[3]={0x60000u+192*index+168,1,bytes};const Step*s=call(0x10022EC0,args,3);check(index<8&&bytes==16);for(i=0;i<7;i++)check(field(source,extraFields[i][0],extraFields[i][1])==s->extra[i]);++copyCount;if(bad)return destination;copyBytes(destination,source,bytes);if(r->mode&2)++((RandomParticleExtra1199D0*)source)->first;if((r->mode&4)&&copyCount==1)record.emitter.accumulator=.5f;return destination;}
static int run(void){u32 i;for(rowIndex=0;rowIndex<sizeof(rows)/sizeof(rows[0]);rowIndex++){const Row*r=&rows[rowIndex];stepIndex=floatCount=integerCount=factoryCount=copyCount=bad=0;captured=0;for(i=0;i<sizeof(record);i++)((u8*)&record)[i]=0xA5;for(i=0;i<sizeof(outputWords);i++)((u8*)outputWords)[i]=0xA5;((u8*)&record)[12]=(u8)r->priority;((u8*)&record)[1]=(u8)r->context;record.emitter.position.x=1.f;record.emitter.position.y=-2.f;record.emitter.position.z=3.f;record.emitter.accumulator=number(r->accumulator);D_800BE9A4=number(r->timestep);func_150EC6B0(&record.header);check(stepIndex==r->count&&raw(record.emitter.accumulator)==r->finalAccumulator&&outputHash()==r->outputHash);if(bad)return 1;}return 0;}
'''
def main():
    count=vectors();body=packet.MANIFEST['selected_source'];body=body[body.index('typedef struct { f32 x, y, z; } RandomParticlePoint1199D0;'):body.index('/* Capture the owner and effect settings;')]
    pre='#include <ultra64.h>\n#include "structs.h"\nf32 func_150ADA68(void);\nu32 func_150ADA20(void);\nvoid*memcpy(void*,const void*,u32);\nextern f32 D_800BE9A4;\n'
    profiles={}
    def execute(name,selected,opt):
        path=out/(name+'.c');exe=path.with_suffix('')
        path.write_text(pre+selected+'\n#include "native-vectors.h"\n'+HARNESS+START)
        q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(path),'-o',str(exe)],cwd=root,capture_output=True,text=True)
        assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.stdout,q.stderr)
        return subprocess.run([str(exe)],capture_output=True,text=True)
    for opt in ('-O0','-O2','-O3'):
        q=execute('native'+opt[1:],body,opt);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
        profiles[opt]={'cases':count,'SDK_layout':True,'strict_aliasing':True,'UBSan':True}
    controls={
        'inclusive-threshold':body.replace('accumulator > 1.0f','accumulator >= 1.0f'),
        'wrong-dimensions':body.replace('% 5U + 4','% 6U + 4'),
        'wrong-lifetime':body.replace('% 51U + 80','% 50U + 80'),
        'wrong-extra-destination':body.replace('effect + 0xA8','effect + 0xA4'),
        'wrong-extra-size':body.replace('sizeof(extra)','12'),
        'wrong-first-flag':body.replace('? 0x80 : 0','? 0x40 : 0'),
        'wrong-cached-position':body.replace('definition.position = emitter->position;','definition.position = emitter->position; definition.position.x += 1.0f;'),
        'reset-escaped-extra':body.replace('        do {','        do {\n            extra.first = 0;')}
    effective=[]
    for name,mutant in controls.items():
        assert mutant!=body,name
        q=execute('control-'+name,mutant,'-O2');assert q.returncode!=0,('Ineffective native control',name)
        effective.append(name)
    r={'profiles':profiles,'only_defined_packet_fields_read':True,'common_header_entry':True,
       'finite_nearest_rounding_domain':True,'effective_source_controls':effective,'native_source_controls_completed':True,'source_installed':packet.installed(),'matching_credit':0}
    (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
