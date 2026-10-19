"""Route dispatch: null/byte/counter boundaries and connected real child code."""
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_route_event_dispatch_candidates as source
from tools.experiments import game_route_event_dispatch_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import test_game_route_actor_event_match as child
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset

TABLE,COUNTER=0x800872A0,0x800D239A
BASE,RECORD,STATE,STACK=child.BASE,child.RECORD,child.STATE,child.STACK
put,read,public=child.put,child.read,child.public


def cases():
    for slot in range(26):
        for status in (0,1,2,127,128,255):
            for mask,flag in ((0,0),(65535,0),(0,255)):
                yield (slot%4,slot,status,(slot*19+status)&255,mask,flag,child.REASONS[slot%8],0,slot&1)
    for status in range(256):
        yield (17,3,status,127,0,0,0x8123458D,0,status&1)
    for status in (0,1,2):
        for counter in range(256):
            yield (31,16,status,counter,65535,0,0xFFFFFFFF,0,0)
    for reason in range(256):
        yield (0,25,0,255,0,0,0x81234500|reason,0,reason&1)
    for index in (0,0x7FFFFFFF,0x80000000,0xFFFFFFFF):
        for reason in (0,13,0xFFFFFFFF):
            yield (index,0,0,255,0,0,reason,1,1)


def fixture(case,phase=0,record=None):
    index,slot,status,counter,mask,flag,reason,null,mutate=case
    record=(RECORD+(index*132&0xFFFFFFFF))&0xFFFFFFFF if record is None else record
    memory,args=child.fixture((slot,mask,flag,slot,reason),phase,record)
    actor=args[1]
    for start,length in ((actor-16,0x350),(record-16,0xA0),(STATE-16,0x160)):
        memory.update({(start+i)&0xFFFFFFFF:0xA5 for i in range(length)})
    for a,v,n in ((actor+0x31C,STATE,4),(STATE+0x120,flag,1),(record+0x31,slot,1),
                  (record+0x30,status,1),(TABLE,0 if null else (record-index*132)&0xFFFFFFFF,4),
                  (COUNTER,counter,1)):
        memory.update({a+i:0 for i in range(n)})
        put(memory,a,v,n)
    return memory,(index,reason),record,actor


class DispatchOracle(child.EventOracle):
    def __init__(self,words,memory,args,record,actor,connected,phase=0,result=0xDEADBEEF,mutate=False,entry=source.ENTRY):
        super().__init__(words,memory,args,phase,result,mutate,entry,connected)
        self.record,self.actor=record,actor

    def hook(self,target):
        super().hook(target)
        if self.mutate:
            self.in_hook=True
            try:
                self.put(TABLE,0,4)
                self.put(COUNTER,128,1)
            finally:self.in_hook=False


def reference(memory,args,result,mutate):
    m=memory.copy();table=read(m,TABLE,4);records=[];captures=[]
    if table==0:return 0,m,records,captures
    record=(table+args[0]*132)&0xFFFFFFFF
    byte=read(m,record+0x31,1)
    slot=byte if byte<128 else byte-256
    actor=(BASE+slot*812)&0xFFFFFFFF
    state=read(m,record+0x30,1)
    ret=0
    if state==0:
        records.append(('caller',(record,actor,args[1])))
        ret,m,captures=child.reference(m,(record,actor,args[1]),result,mutate)
        if captures:
            records.append(('submit',(0,args[1])))
            if mutate:
                put(m,TABLE,0,4);put(m,COUNTER,128,1)
    elif state==1:
        put(m,record+0x30,2,1);put(m,actor+0x125,255,1)
    put(m,record+0x2A,read(m,COUNTER,1),1)
    put(m,COUNTER,read(m,COUNTER,1)+1,1)
    return ret,m,records,captures


def summary(model):
    m,r,a=model.memory,model.record,model.actor
    calls=[v for k,v in model.records if k=='caller']
    capture=model.captures[0] if model.captures else None
    return [model.r[2],len(calls),len(model.captures),read(m,r+0x30,1),read(m,r+0x2A,1),read(m,COUNTER,1),
        read(m,a+0x125,1),read(m,a,4),read(m,a+0x232,1),read(m,a+0x218,4),read(m,a+0x21C,2),
        read(m,STATE+0x84,1),int(read(m,child.CURRENT,4)==a),read(m,child.INDEX,1),
        capture[0][1] if capture else 0,capture[2] if capture else 0,calls[0][2] if calls else 0,
        int(read(m,TABLE,4)==0)]


NATIVE=r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;
typedef unsigned int u32;typedef int s32;
u8 D_800CC2D0[26*812] __attribute__((aligned(16)));u16 D_800D18A0;
u8 *D_800D154C,*D_800872A0;s8 D_800C3E78,D_800D239A;
static u8 records[32*132] __attribute__((aligned(16))),state[0x160] __attribute__((aligned(16)));
static u8 *record,*actor;
static u32 result,mutation,childCalls,submitCalls,callReason,capturedIndex,childReason,failure;
s32 func_1507BB28(s32 first,s32 reason) {
    submitCalls++;callReason=reason;capturedIndex=(u8)D_800C3E78;
    if(first || *(s32 *)actor!=12 || actor[0x232]!=(u8)reason || state[0x84]!=1 || D_800D154C!=actor)failure=22;
    if(mutation) {actor[0x125]=0x12;*(u16 *)(actor+0x21C)=0x1234;record[0x31]=0x77;
        D_800D154C=0;D_800C3E78=0x66;D_800872A0=0;D_800D239A=(s8)128;}
    return result;
}
CHILD_BODY
s32 func_1508802C(u8 *r,u8 *a,s32 reason) {
    childCalls++;childReason=reason;
    if(r!=record || a!=actor)failure=23;
    return actual_child(r,a,reason);
}
SOURCE_BODY
typedef struct {u32 input[10],expected[18];} Case;
static const Case cases[]={ROWS};
void _start(void) {
    u32 n,i,actual[18];const Case *c;s32 ret;
    for(n=0;!failure && n<sizeof(cases)/sizeof(cases[0]);n++) {
        c=cases+n;actor=D_800CC2D0+c->input[1]*812;
        record=records+(c->input[7]?0:c->input[0])*132;
        for(i=0;i<sizeof(records);i++)records[i]=0xA5;
        for(i=0;i<812;i++)actor[i]=0xA5;
        for(i=0;i<sizeof(state);i++)state[i]=0xA5;
        *(u8 **)(actor+0x31C)=state;state[0x120]=c->input[5];
        record[0x31]=c->input[1];record[0x30]=c->input[2];
        D_800872A0=c->input[7]?0:records;D_800D239A=c->input[3];D_800D18A0=c->input[4];
        D_800D154C=(u8 *)0x12345678;D_800C3E78=(s8)0xA5;
        mutation=c->input[8];result=c->input[9];childCalls=submitCalls=callReason=capturedIndex=childReason=0;
        ret=func_150880F8(c->input[0],c->input[6]);
        actual[0]=ret;actual[1]=childCalls;actual[2]=submitCalls;actual[3]=record[0x30];
        actual[4]=record[0x2A];actual[5]=(u8)D_800D239A;actual[6]=actor[0x125];actual[7]=*(u32 *)actor;
        actual[8]=actor[0x232];actual[9]=*(u32 *)(actor+0x218);actual[10]=*(u16 *)(actor+0x21C);
        actual[11]=state[0x84];actual[12]=D_800D154C==actor;actual[13]=(u8)D_800C3E78;
        actual[14]=callReason;actual[15]=capturedIndex;actual[16]=childReason;actual[17]=D_800872A0==0;
        for(i=0;i<18;i++)if(actual[i]!=c->expected[i])failure=21;
    }
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''


class GameRouteEventDispatchMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out)
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out,'test-selected')
        cls.retail=list(struct.unpack_from('>53I',cls.values['conker/conker.us.bin'],source.ROM))
        original=list(struct.unpack_from('>51I',cls.values['conker/conker.us.bin'],child.source.ROM))
        image=cls.values['conker/build/conker.us.elf'];at=elf_slot_offset(image,child.source.ENTRY,204)
        if list(struct.unpack_from('>51I',image,at))!=original:
            raise ValueError('Connected child is not the exact installed routine')
        cls.connected=dict(zip(range(child.source.ENTRY,child.source.ENTRY+204,4),original))
        cls.cases=list(cases())

    def model(self,words,case,phase=0,record=None,result=0xDEADBEEF,entry=source.ENTRY):
        memory,args,record,actor=fixture(case,phase,record)
        return DispatchOracle(words,memory,args,record,actor,self.connected,phase,result,bool(case[8]),entry)

    def test_direct_words_frame_bindings_and_initial_shape_controls(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(53,32,0,''))
        self.assertEqual(self.words,self.retail);integration.checked(self.obj)
        for name,expected in (('initial',(53,48,7)),('record-table-lifetime',(53,32,31))):
            _,words,row=source.compile_candidate(self.root,self.out,'control-'+name,dict(source.candidates())[name])
            self.assertEqual((row['words'],row['frame'],row['differences']),expected)
            self.assertNotEqual(words,self.retail)

    def test_connected_public_reference_full_ram_and_null_path(self):
        coverage=set()
        for i,case in enumerate(self.cases):
            for phase in (0,8):
                result=(0,0x80000000,0xDEADBEEF)[i%3]
                a=self.model(self.retail,case,phase,result=result).run()
                b=self.model(self.words,case,phase,result=result).run()
                memory,args,_,_=fixture(case,phase)
                expected,ram,records,captures=reference(memory,args,result,bool(case[8]))
                self.assertEqual((a.r,a.f,a.lo,a.memory,a.events,a.records,a.captures),
                                 (b.r,b.f,b.lo,b.memory,b.events,b.records,b.captures))
                self.assertEqual((a.r[2],public(a.memory),a.records,a.captures),(expected,public(ram),records,captures))
                self.assertEqual(sum(e[0]=='R' and e[1]==COUNTER for e in a.events),0 if case[7] else 2)
                if case[7]:self.assertFalse(any(e[0]=='W' and e[1]==COUNTER for e in a.events))
                coverage.update(a.visits)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+212,4))<=coverage)
        (self.out/'connected-cases.json').write_text(json.dumps(dict(cases=len(self.cases),phases=2,
            child_words=51,all53_target_words_visited=True))+'\n')

    def test_aliases_and_fired_own_access_fault_pairs(self):
        pairs=0
        for phase in (0,8):
            for record in (RECORD,BASE,COUNTER-0x30,COUNTER-0x2A,STACK+phase-0x2D):
                for status in (0,1,2):
                    case=(0,0,status,status if record==COUNTER-0x30 else 127,0,0,13,0,0)
                    a=self.model(self.retail,case,phase,record).run()
                    b=self.model(self.words,case,phase,record).run()
                    self.assertEqual((a.r,a.memory,a.events),(b.r,b.memory,b.events))
                    if record!=STACK+phase-0x2D:
                        memory,args,_,_=fixture(case,phase,record)
                        ret,ram,records,captures=reference(memory,args,0xDEADBEEF,False)
                        self.assertEqual((a.r[2],public(a.memory),a.records,a.captures),(ret,public(ram),records,captures))
                    for cut in range(a.accesses):
                        models=[]
                        for words in (self.retail,self.words):
                            model=self.model(words,case,phase,record);model.fault=cut
                            with self.assertRaises(child.AccessFault):model.run()
                            self.assertEqual(model.accesses,cut)
                            models.append((model.r,model.f,model.lo,model.memory,model.events,model.records))
                        self.assertEqual(*models);pairs+=1
        (self.out/'access-cuts.json').write_text(json.dumps(dict(fired_pairs=pairs,profiles=15,phases=2))+'\n')

    def test_guest_signed_slot_and_modular_index_artifacts(self):
        pairs=0
        for byte in range(256):
            slot=byte if byte<128 else byte-256
            case=(0,slot,1,255,0,0,13,0,0)
            a=self.model(self.retail,case).run();b=self.model(self.words,case).run()
            self.assertEqual((a.r,a.memory,a.events),(b.r,b.memory,b.events));pairs+=1
        for index in (0x40000000,0x80000000,0xC0000000,0x40000001,0xFFFFFFFF):
            case=(index,0,0,255,0,0,0x8123458D,0,1)
            a=self.model(self.retail,case).run();b=self.model(self.words,case).run()
            self.assertEqual((a.r,a.memory,a.events),(b.r,b.memory,b.events));pairs+=1
        self.assertEqual(pairs,261)

    def test_native32_o0_o2_ubsan_with_real_child_c(self):
        rows=[]
        for i,case in enumerate(self.cases):
            result=(0,0x80000000,0xDEADBEEF)[i%3]
            # Null-table arguments need no backing record at their potentially huge index.
            record=RECORD if case[7] else None
            model=self.model(self.words,case,record=record,result=result).run()
            fmt=lambda values:','.join('0x%Xu'%(v&0xFFFFFFFF) for v in values)
            rows.append('{{%s},{%s}}'%(fmt((*case,result)),fmt(summary(model))))
        child_body=child.source.SELECTED.replace('s32 func_1508802C(', 's32 actual_child(')
        unit=NATIVE.replace('CHILD_BODY',child_body).replace('SOURCE_BODY',source.SELECTED).replace('ROWS',',\n'.join(rows))
        negative=NATIVE.replace('CHILD_BODY',child_body).replace('SOURCE_BODY',
            source.SELECTED.replace('record[0x30] = 2;','record[0x30] = 3;')).replace('ROWS',',\n'.join(rows))
        results={}
        for name,opt,sanitize,body,want in (('o0','-O0',False,unit,0),('o2','-O2',False,unit,0),
                ('ubsan','-O2',True,unit,0),('negative-state','-O2',True,
                 negative,21)):
            path=self.out/('native-'+name+'.c');path.write_text(body);exe=path.with_suffix('')
            command=[*native_command(opt,sanitize),'-mstackrealign','-fno-strict-aliasing',str(path),'-o',str(exe)]
            built=subprocess.run(command,cwd=self.root,capture_output=True,text=True)
            (self.out/('native-'+name+'-compile.json')).write_text(json.dumps(dict(command=command,
                exit=built.returncode,diagnostics=built.stdout+built.stderr),indent=2)+'\n')
            self.assertEqual((built.returncode,built.stdout,built.stderr),(0,'',''),name)
            run=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertEqual((run.returncode,run.stdout,run.stderr),(want,'',''),name);results[name]=run.returncode
        (self.out/'native-cases.json').write_text(json.dumps(dict(cases=len(self.cases),exits=results,
            connected_real_child_C=True,observations_per_case=18))+'\n')

    def test_ordinary_executed_source_negative_controls(self):
        forms={
            'narrow-reason':source.SELECTED.replace('s32 reason)', 'u8 reason)'),
            'ignore-return':source.SELECTED.replace('result = func_1508802C','func_1508802C'),
            'early-counter':source.SELECTED.replace('    s32 result;',
                '    s32 result;\n    s8 sequence = D_800D239A;').replace(
                'record[0x2A] = D_800D239A;', 'record[0x2A] = sequence;').replace('D_800D239A++;','D_800D239A = sequence + 1;'),
            'wrong-state':source.SELECTED.replace('record[0x30] = 2;', 'record[0x30] = 3;'),
        }
        for name,body in forms.items():
            _,words,_=source.compile_candidate(self.root,self.out,'negative-'+name,body)
            case=(0,0,1 if name in ('early-counter','wrong-state') else 0,1,1 if name=='ignore-return' else 0,
                  0,0x1234568D,0,0)
            record=COUNTER-0x30 if name=='early-counter' else None
            a=self.model(self.retail,case,record=record).run();b=self.model(words,case,record=record).run()
            self.assertNotEqual((a.r[2],public(a.memory),a.records),(b.r[2],public(b.memory),b.records),name)

    def test_owner_profiles_padder_and_first_image_or_installed_audit(self):
        row=integration.qualify(self.root,self.out)
        self.assertEqual((row['words'],row['frame'],row['new_guards'],row['padded_functions_fixed']),(53,32,0,73))
        if (self.root/source.SOURCE).read_bytes()==self.values[source.SOURCE]:
            self.assertTrue(integration.predict(self.root,self.out)['whole_ELF_unchanged'])
        else:self.assertTrue(integration.audit(self.root,self.out)['whole_ELF_unchanged'])

    def test_independent_assembly_relocations_and_code_rebases(self):
        asm=self.out/'original.s';obj=asm.with_suffix('.o')
        asm.write_text((self.root/'conker/include/asm_processor_prelude.inc').read_text()+
            '\n.text\n.type '+source.FUNCTION+', @function\n'+
            self.values['conker/asm/nonmatchings/generated_B3020/func_150880F8.s'].decode()+
            '\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
            '-o',str(obj),str(asm)],check=True,capture_output=True)
        self.assertEqual(integration.checked(obj),integration.checked(self.obj))
        symbols=dict(D_800872A0=TABLE,D_800CC2D0=BASE,D_800D239A=COUNTER,func_1508802C=child.source.ENTRY)
        maps=[(source.ENTRY,symbols),(0x1621FFF4,dict(D_800872A0=0x8010FFF4,D_800CC2D0=0x80218010,
            D_800D239A=0x8033FFF8,func_1508802C=0x1634FFF0)),(0x18FFF000,dict(D_800872A0=0x8045FFFC,
            D_800CC2D0=0x80517FFC,D_800D239A=0x80628008,func_1508802C=0x18F0003C))]
        for number,(entry,bindings) in enumerate(maps):
            images=[]
            for label,path in (('retail',obj),('source',self.obj)):
                script=self.out/(label+'-map-%d.ld'%number)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in bindings.items()],'-o',str(elf),str(path)],check=True,capture_output=True)
                at,data=sections(elf)['.text'];self.assertEqual(at,entry);images.append(data[:212])
            self.assertEqual(*images)
        paired=0
        for entry in (0x1621FFF4,0x18FFF000):
            for case in list(cases())[:18]:
                a=self.model(self.retail,case,entry=entry).run();b=self.model(self.words,case,entry=entry).run()
                self.assertEqual((a.r,a.memory,a.events),(b.r,b.memory,b.events));paired+=1
        (self.out/'relocation-maps.json').write_text(json.dumps(dict(GNU_maps=3,bindings=7,
            independent_assembly_equal=True,code_rebased_pairs=paired,data_rebases_static_only=True))+'\n')


if __name__=='__main__':unittest.main()
