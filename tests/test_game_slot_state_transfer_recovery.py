"""Complete public recovery, native32 controls and explicit nonmatch witnesses."""
from dataclasses import astuple,replace
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_slot_state_transfer_candidates as source
from tools.experiments import game_route_projection_integration as mixed
from tools.tests import game_slot_state_transfer_oracle as oracle
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_projected_packet_draw import native_command


NATIVE=r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;
typedef unsigned int u32;typedef int s32;
u8 D_800D18A4[256],D_800CC2D0[256*812] __attribute__((aligned(16)));
u16 D_800D18A0,D_800D18A2;s32 D_800D23B0,D_800BE9F0,D_800D2E48;s8 D_8008FD94;
static u8 banks[2][0x1800] __attribute__((aligned(16))),states[3][0x200] __attribute__((aligned(16)));
static u8 script[0x3000] __attribute__((aligned(16))),child[16] __attribute__((aligned(16)));
typedef struct {u32 in[14],out[71];} Row;
static const Row rows[]={ROWS};static const Row *active;
static u32 calls,records[24],capture[3];
static u8 *actor(u32 slot){return D_800CC2D0+slot*812;}
static u32 word(u8 *base,u32 off){return *(u32 *)(base+off);}
static void setword(u8 *base,u32 off,u32 value){*(u32 *)(base+off)=value;}
static void record(u32 id,u32 a,u32 b,u32 c){u32 at=calls++*4;records[at]=id;records[at+1]=a;records[at+2]=b;records[at+3]=c;}
s32 __attribute__((noinline)) func_150859AC(s16 slot,s32 kind){
    record(1,(s32)slot,kind,0);capture[0]=D_800D18A0;capture[1]=D_800D18A2;capture[2]=D_800D18A4[active->in[0]];
    if(active->in[13]){D_800D18A0^=0x55AA;D_800D18A2^=0x0F0F;D_800D18A4[active->in[0]]=0;D_800D23B0=(s32)banks[1];}
    return (s32)(0xCAFE0000U|(u16)slot);
}
void __attribute__((noinline)) func_15085710(s16 slot,s32 kind,s32 value){record(2,(s32)slot,kind,value);}
void __attribute__((noinline)) func_15062800(u8 *source,u8 *destination){
    record(3,(source-D_800CC2D0)/812,(destination-D_800CC2D0)/812,0);
    if(active->in[13]){*(u8 **)(destination+0x31C)=states[1];*(s16 *)(states[1]+0x1AA)=0x5555;}
}
u8 *__attribute__((noinline)) func_1509B570(s32 value){
    u8 *destination=actor(active->in[0]);record(4,value,0,0);
    if(active->in[13]){destination[0x13C]=0;actor((active->in[7]-100)&255)[0x3B]=active->in[8]^0x80;
        *(u8 **)(destination+0x31C)=states[2];*(s16 *)(states[2]+0x1AA)=0x6666;}
    return active->in[10]?script:0;
}
void __attribute__((noinline)) func_15128774(u8 *first,u8 *second){
    record(5,first==child?0xF0000010U:(u32)first,(second-D_800CC2D0)/812,0);
    if(active->in[13])D_8008FD94=127;
}
SOURCE_BODY
void _start(void){
    static const u32 fields[]={0x9C,0x39C,0x3DC,0xEB0,0x16C0};
    u32 n,i,j,b,slot,v,at,output[71],failure=0;const u32 *c;u8 *destination,*state;s32 offset;
    if(sizeof(void*)!=4 || sizeof(s16)!=2)failure=29;
    for(n=0;!failure && n<sizeof(rows)/sizeof(rows[0]);n++){
        active=rows+n;c=active->in;calls=0;
        for(i=0;i<24;i++)records[i]=0;for(i=0;i<3;i++)capture[i]=0;
        for(b=0;b<2;b++)for(i=0;i<0x1800;i++)banks[b][i]=0xA5;
        for(b=0;b<3;b++)for(i=0;i<0x200;i++)states[b][i]=0xA5;
        for(i=0;i<sizeof(script);i++)script[i]=0xA5;
        for(i=0;i<sizeof(D_800CC2D0);i++)D_800CC2D0[i]=0xA5;
        for(slot=0;slot<256;slot++)actor(slot)[0x3B]=(u8)(slot*7+29);
        for(b=0;b<2;b++){
            setword(banks[b],0x18,c[5]);
            for(i=0;i<5;i++)for(j=0;j<2;j++){
                slot=c[j];v=fields[i]==0xEB0?c[9]:0x12000000+b*0x10000+fields[i]+slot*17;
                setword(banks[b],fields[i]+slot*4,v);
            }
        }
        D_800D18A0=c[4];D_800D18A2=c[3];D_800D18A4[c[0]]=c[2];D_800D23B0=(s32)banks[0];
        D_800BE9F0=c[6];D_800D2E48=0x12345678;D_8008FD94=c[12];destination=actor(c[0]);
        *(u8 **)(destination+0x31C)=states[0];*(u8 **)(destination+0x318)=child;destination[0x13C]=c[7];
        *(s16 *)(states[0]+0x1AA)=c[11];actor((c[7]-100)&255)[0x3B]=c[8];
        if(func_1508E89C(c[0],c[1])!=0)failure=21;
        at=0;output[at++]=D_800D18A0;output[at++]=D_800D18A2;output[at++]=D_800D18A4[c[0]];
        output[at++]=D_800D23B0==(s32)banks[1];output[at++]=(u8)D_8008FD94;output[at++]=calls;
        for(b=0;b<2;b++){
            output[at++]=word(banks[b],0x18);
            for(i=0;i<5;i++)for(j=0;j<2;j++)output[at++]=word(banks[b],fields[i]+c[j]*4);
            output[at++]=word(banks[b],0xF70+((s32)c[9]<0?0:c[9])*4);
        }
        state=*(u8 **)(destination+0x31C);output[at++]=destination[0x125];output[at++]=destination[0x13C];
        output[at++]=state==states[0]?0:state==states[1]?1:2;
        for(i=0;i<3;i++){output[at++]=(u16)*(s16 *)(states[i]+0x1AA);output[at++]=states[i][0x84];output[at++]=states[i][0x1AF];}
        offset=(s32)actor((c[7]-100)&255)[0x3B]-20;
        output[at++]=word(script,0x24B8+offset*4);output[at++]=word(script,0x24DC+offset*4);
        for(i=0;i<3;i++)output[at++]=capture[i];for(i=0;i<24;i++)output[at++]=records[i];
        if(at!=71)failure=29;for(i=0;i<71;i++)if(output[i]!=active->out[i])failure=21;
    }
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''


class GameSlotStateTransferRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD;cls.values=source.freeze(cls.root,cls.out)
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out,'qualified')
        cls.retail=list(struct.unpack_from('>189I',cls.values['conker/conker.us.bin'],source.ROM));cls.cases=list(oracle.cases())

    def model(self,words,case,phase=0,bank=None,entry=source.ENTRY):
        memory,args=oracle.fixture(case,phase,bank)
        return oracle.TransferModel(words,memory,args,case,phase,entry)

    def test_01_complete_shape_and_explicit_matching_boundary(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(189,80,100,''))
        self.assertEqual(self.row['raw_SHA256'],'6614844cb6c0714ad69f73adab4fa0214a709c66aeefac7aea114d0fcdc127fe')
        self.assertEqual(len(self.row['bindings']),26);self.assertNotEqual(self.words,self.retail)
        for left,right,want in ((0,0,0xFFFFFFFF),(0xFFFFFFFF,0,0),(0x80000000,1,0x7FFFFFFE),(0x55555555,0xAAAAAAAA,0)):
            model=self.model(self.retail,oracle.Case());model.r[9],model.r[10]=left,right
            model.execute((9<<21)|(10<<16)|(11<<11)|39);self.assertEqual((model.r[11],model.r[0]),(want,0))

    def test_02_independent_public_algorithm_and_provider_mutations(self):
        visits=[set(),set()];pairs=0
        for case in self.cases:
            for phase in (0,8):
                memory,args=oracle.fixture(case,phase);wanted,calls,captures=oracle.reference(memory,args,case)
                for index,words in enumerate((self.retail,self.words)):
                    model=self.model(words,case,phase).run();self.assertEqual(model.r[2],0)
                    self.assertEqual((oracle.public(model.memory),model.calls,model.captures),
                        (oracle.public(wanted),calls,captures),case)
                    visits[index].update(model.visits)
                pairs+=1
        target=set(range(source.ENTRY,source.ENTRY+756,4))
        coverage=[len(target&seen) for seen in visits]
        self.assertEqual(coverage,[185,185])
        (self.out/'public-cases.json').write_text(json.dumps(dict(cases=len(self.cases),phases=2,paired_runs=pairs,
            retail_visited_words=coverage[0],candidate_visited_words=coverage[1],
            independent_reference=True,bounded_providers_only=True))+'\n')

    def test_03_guest_only_modular_slots_and_computed_null_guards(self):
        cases=[]
        for destination in (0,15,31,32,0x10000,0x80000000,0xFFFFFFFF):
            for source_slot in (0,15,31,32,0x10001,0xFFFFFFFF):
                cases.append((oracle.Case(destination=destination,source=source_slot,mode=0,owner=-1),None))
        for field in (0x9C,0x39C,0x3DC,0xEB0):cases.append((oracle.Case(mode=0,owner=-1),oracle.u32(-field)))
        for case,bank in cases:
            memory,args=oracle.fixture(case,bank=bank);wanted,calls,captures=oracle.reference(memory,args,case)
            for words in (self.retail,self.words):
                model=self.model(words,case,bank=bank).run()
                self.assertEqual((oracle.public(model.memory),model.calls,model.captures),(oracle.public(wanted),calls,captures))
        (self.out/'guest-boundaries.json').write_text(json.dumps(dict(paired_cases=len(cases),native_cases=False))+'\n')

    def test_04_native32_named_observables_and_effective_controls(self):
        fmt=lambda values:','.join('0x%Xu'%oracle.u32(v) for v in values)
        rows=[]
        for case in self.cases:
            memory,args=oracle.fixture(case);wanted,calls,captures=oracle.reference(memory,args,case)
            observed=oracle.observation(wanted,calls,captures,case);self.assertEqual(len(observed),71)
            rows.append('{{%s},{%s}}'%(fmt(astuple(case)),fmt(observed)))
        base=NATIVE.replace('ROWS',',\n'.join(rows));unit=source.FITTED
        controls={'o0':unit,'o2':unit,'ubsan':unit,
            'wrong-mask':unit.replace('sourceBit = 1U << sourceSlot;','sourceBit = 1U << destinationSlot;'),
            'wrong-half':unit.replace('= savedHalfword;','= savedHalfword ^ 1;'),
            'wrong-final-actor':unit.replace('func_15128774(*(u8 **)(destination + 0x318), destination);',
                'func_15128774(*(u8 **)(destination + 0x318), ((SlotTransferActor *)D_800CC2D0)[sourceSlot].bytes);')}
        exits={}
        for name,body in controls.items():
            path=self.out/('native-'+name+'.c');path.write_text(base.replace('SOURCE_BODY',body));exe=path.with_suffix('')
            command=[*native_command('-O0' if name=='o0' else '-O2',name not in ('o0','o2')),
                '-mstackrealign','-fno-strict-aliasing',str(path),'-o',str(exe)]
            compiled=subprocess.run(command,cwd=self.root,capture_output=True,text=True)
            self.assertEqual((compiled.returncode,compiled.stdout,compiled.stderr),(0,'',''),name)
            result=subprocess.run([str(exe)],capture_output=True,text=True);want=0 if name in ('o0','o2','ubsan') else 21
            self.assertEqual((result.returncode,result.stdout,result.stderr),(want,'',''),name);exits[name]=result.returncode
        (self.out/'native-cases.json').write_text(json.dumps(dict(cases=len(self.cases),observables_per_case=71,
            actor_backing_records=256,bounded_providers=True,exits=exits))+'\n')

    def test_05_private_homes_and_first_fired_nonmatch(self):
        case=oracle.Case();a=self.model(self.retail,case).run();b=self.model(self.words,case).run()
        self.assertEqual(a.private,[(case.source,1<<case.source,oracle.u32(~(1<<case.destination)),case.destination,case.source)])
        self.assertNotEqual(a.private,b.private)
        first=None;equal=0
        for cut in range(min(a.accesses,b.accesses)):
            states=[]
            for words in (self.retail,self.words):
                model=self.model(words,case);model.fault=cut
                with self.assertRaises(oracle.core.AccessFault):model.run()
                self.assertEqual(model.accesses,cut);states.append((model.r,model.f,model.lo,model.memory,model.events))
            if states[0]==states[1]:equal+=1
            elif first is None:first=cut
        self.assertIsNotNone(first)
        (self.out/'private-boundary.json').write_text(json.dumps(dict(first_unequal_cut=first,equal_states=equal,
            compared_cuts=min(a.accesses,b.accesses),retail_first_helper_homes=a.private,source_first_helper_homes=b.private,
            raw_is_not_private_or_fault_exact=True))+'\n')

    def test_06_both_owner_profiles_preserve_other_routines_and_pools(self):
        same=mixed.candidate.source.neighbor.same_functions
        for label,normal in (('primary',False),('normal',True)):
            old,diag=source.compile_profile(self.root,self.out,self.values[source.SOURCE].decode(),'before-'+label,normal)
            new,_,row=source.compile_candidate(self.root,self.out,'after-'+label,normal=normal,whole=True)
            self.assertEqual((diag,row['diagnostics'],row['words'],row['frame'],row['differences']),('','',189,80,100))
            self.assertEqual(same(old,new,(source.FUNCTION,)),72);self.assertEqual(normalized_pools(old),normalized_pools(new))
        for name,value in self.values.items():self.assertEqual((self.root/name).read_bytes(),value,name)

    def test_07_actual_three_word_caller_window(self):
        entry=0x1509E14C;rom=self.values['conker/conker.us.bin'];window=list(struct.unpack_from('>3I',rom,0xCB5FC))+[0x02E00008,0]
        self.assertEqual(window[:3],[0x8E040008,0x0D423A27,0x8E05000C]);pairs=0
        for case in (oracle.Case(),oracle.Case(mutate=1),oracle.Case(level=50),oracle.Case(locked=65535),
                oracle.Case(lookup=0),oracle.Case(mode=0),oracle.Case(tag=99),oracle.Case(destination=5,source=5)):
            for phase in (0,8):
                memory,args=oracle.fixture(case,phase);oracle.put(memory,0xB0008,args[0],4);oracle.put(memory,0xB000C,args[1],4)
                wanted,calls,captures=oracle.reference(memory,args,case)
                for words in (self.retail,self.words):
                    model=oracle.TransferModel(window,memory,args,case,phase,entry);model.r[16]=model.before[16]=0xB0000
                    model.r[23]=model.before[23]=0xDEAD0000;model.before[31]=entry+12
                    model.code.update(zip(range(source.ENTRY,source.ENTRY+756,4),words));model.run()
                    self.assertEqual(model.caller_args,[args]);self.assertEqual((model.r[2],oracle.public(model.memory),model.calls,model.captures),
                        (0,oracle.public(wanted),calls,captures))
                pairs+=1
        (self.out/'caller-cases.json').write_text(json.dumps(dict(actual_three_word_windows=pairs,
            synthetic_stop_trampoline=True,whole_caller_not_executed=True))+'\n')

    def test_08_typed_field_screens_do_not_improve_matching(self):
        seen=[]
        for name,body in source.candidates():
            if not name.startswith('address-table-'):continue
            _,words,row=source.compile_candidate(self.root,self.out,name,body)
            self.assertEqual(words,self.words)
            self.assertEqual((row['diagnostics'],row['words'],row['frame'],row['differences']),('',189,80,100))
            self.assertEqual(row['raw_SHA256'],self.row['raw_SHA256']);seen.append(name)
        self.assertEqual(seen,['address-table-fields','address-table-elements'])


if __name__=='__main__':unittest.main()
