"""Direct actor-event C: complete words, ABI, mutations, aliases and relocation."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_route_actor_event_candidates as source
from tools.experiments import game_route_actor_event_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_projected_packet_draw import native_command

BASE, MASK, CURRENT, INDEX, SUBMIT = 0x800CC2D0,0x800D18A0,0x800D154C,0x800C3E78,0x1507BB28
RECORD, STATE = 0x20000,0x22000
REASONS = (0,13,255,256,0xFFFFFF00,0xFFFFFFFF,0x80000000,0x7FFFFFFF)


def cases():
    for slot in range(26):
        for mask in (0,65535,1<<(slot&15),0x8000,1,0x5555):
            for flag in (0,255):
                yield slot,mask,flag,(slot*13+128)&255,REASONS[(slot+mask)%8]
    for flag in range(256):
        yield 3,0,flag,255,13
    for index in range(256):
        yield 25,0,0,index,0xFFFFFEFF
    for reason in range(256):
        yield 16,65535,0,128,0x81234500|reason
    for slot in (0,15,16,25):
        for reason in REASONS:
            yield slot,0,0,127,reason


def fixture(case, phase=0, record=RECORD, state=STATE):
    slot,mask,flag,index,reason = case
    actor = (BASE+slot*0x32C)&0xFFFFFFFF
    memory = {}
    for base,length in ((STACK-0x100,0x240),(actor-16,0x350),(record-16,0xA0),(state-16,0x160),
                        (MASK-4,12),(CURRENT-4,12),(INDEX-4,12)):
        memory.update({(base+i)&0xFFFFFFFF:(i*13+0xA5)&255 for i in range(length)})
    for address,value,size in ((actor+0x31C,state,4),(state+0x120,flag,1),
            (record+0x31,index,1),(MASK,mask,2),(CURRENT,0x12345678,4),(INDEX,0xA5,1)):
        put(memory,address,value,size)
    return memory,(record,actor,reason)


class AccessFault(Exception):
    pass


class EventOracle(TriangleOracle):
    def __init__(self, words, memory, arguments, phase=0, result=0xDEADBEEF, mutate=False,
                 entry=source.ENTRY, connected=None):
        self.fault,self.accesses,self.in_hook = None,0,False
        super().__init__(words,memory,phase=phase,entry=entry,arguments=arguments,connected=connected)
        self.result,self.mutate = result,mutate
        self.records,self.captures = [],[]
        self.record,self.actor = arguments[:2]

    def gate(self):
        if self.recording and not self.in_hook:
            if self.fault==self.accesses:
                raise AccessFault()
            self.accesses += 1

    def get(self,address,size):
        self.gate()
        return super().get(address,size)

    def put(self,address,value,size):
        self.gate()
        super().put(address,value,size)

    def execute(self,word):
        op,rs,rt=word>>26,word>>21&31,word>>16&31
        if op==32:
            immediate=word&65535
            address=(self.r[rs]+(immediate if immediate<32768 else immediate-65536))&0xFFFFFFFF
            value=self.get(address,1)
            if value&128:
                value-=256
            self.r[rt]=value&0xFFFFFFFF
            self.r[0]=0
        else:
            super().execute(word)

    def record_call(self,target):
        if target==source.ENTRY:
            self.record,self.actor = self.r[4:6]
            self.records.append(('caller',tuple(self.r[4:7])))
            return
        assert target==SUBMIT,hex(target)
        args=tuple(self.r[4:6])
        state=read(self.memory,self.actor+0x31C,4)
        self.captures.append((args,read(self.memory,CURRENT,4),read(self.memory,INDEX,1),
            read(self.memory,self.actor,4),read(self.memory,self.actor+0x232,1),read(self.memory,state+0x84,1)))
        self.records.append(('submit',args))
        self.events.append(('CALL',target,args))

    def hook(self,target):
        assert target==SUBMIT
        self.in_hook=True
        try:
            if self.mutate:
                for a,v,n in ((self.actor+0x125,0x12,1),(self.actor+0x21C,0x1234,2),
                              (self.record+0x31,0x77,1),(CURRENT,0,4),(INDEX,0x66,1)):
                    self.put(a,v,n)
            for register in (1,2,3,*range(4,16),24,25):
                self.r[register]=0xA5000000+register
            self.f[:20]=[0xA5000000+i for i in range(20)]
            self.r[2]=self.result
        finally:
            self.in_hook=False


def reference(memory, arguments, result, mutate):
    m=memory.copy()
    record,actor,reason=arguments
    state=read(m,actor+0x31C,4)
    slot=signed((actor-BASE)&0xFFFFFFFF)
    slot=(abs(slot)//0x32C)*(-1 if slot<0 else 1)
    if read(m,state+0x120,1) or read(m,MASK,2)&(1<<(slot&31)):
        return 1,m,[]
    for a,v,n in ((state+0x84,1,1),(actor,12,4),(actor+0x232,reason,1),(CURRENT,actor,4)):
        put(m,a,v,n)
    put(m,INDEX,read(m,record+0x31,1),1)
    capture=((0,reason),read(m,CURRENT,4),read(m,INDEX,1),read(m,actor,4),
             read(m,actor+0x232,1),read(m,state+0x84,1))
    if mutate:
        for a,v,n in ((actor+0x125,0x12,1),(actor+0x21C,0x1234,2),
                      (record+0x31,0x77,1),(CURRENT,0,4),(INDEX,0x66,1)):
            put(m,a,v,n)
    for a,v,n in ((actor+0x218,result,4),(actor+0x21C,0,2),(actor+0x125,255,1),(record+0x30,2,1)):
        put(m,a,v,n)
    return 0,m,[capture]


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x100<=a<STACK+0x140}


def summary(model):
    m,r,a=model.memory,model.record,model.actor
    state=read(m,a+0x31C,4)
    capture=model.captures[0] if model.captures else None
    return [model.r[2],len(model.captures),read(m,a,4),read(m,a+0x232,1),read(m,state+0x84,1),
        read(m,a+0x218,4),read(m,a+0x21C,2),read(m,a+0x125,1),read(m,r+0x30,1),
        int(read(m,CURRENT,4)==a),read(m,INDEX,1),capture[2] if capture else 0,
        capture[0][1] if capture else 0,capture[0][0] if capture else 0]


NATIVE = r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;
typedef unsigned int u32;typedef int s32;
u8 D_800CC2D0[26*0x32C] __attribute__((aligned(16)));
u16 D_800D18A0;u8 *D_800D154C;s8 D_800C3E78;
static u8 record[0xA0] __attribute__((aligned(16))),state[0x160] __attribute__((aligned(16)));
static u32 result,mutation,calls,callReason,callFirst,capturedIndex,failure;
static u8 *actor;
s32 func_1507BB28(s32 first,s32 reason) {
    calls++;callFirst=first;callReason=reason;capturedIndex=(u8)D_800C3E78;
    if(*(s32 *)actor!=12 || actor[0x232]!=(u8)reason || state[0x84]!=1 || D_800D154C!=actor)
        failure=22;
    if(mutation) {actor[0x125]=0x12;*(u16 *)(actor+0x21C)=0x1234;
        record[0x31]=0x77;D_800D154C=0;D_800C3E78=0x66;}
    return result;
}
SOURCE_BODY
typedef struct {u32 input[7],expected[14];} Case;
static const Case cases[]={ROWS};
void _start(void) {
    u32 n,i,actual[14];const Case *c;int status;
    for(n=0;!failure && n<sizeof(cases)/sizeof(cases[0]);n++) {
        c=cases+n;actor=D_800CC2D0+c->input[0]*0x32C;
        for(i=0;i<0x32C;i++)actor[i]=0xA5;
        for(i=0;i<sizeof(record);i++)record[i]=0xA5;
        for(i=0;i<sizeof(state);i++)state[i]=0xA5;
        *(u8 **)(actor+0x31C)=state;state[0x120]=c->input[2];record[0x31]=c->input[3];
        D_800D18A0=c->input[1];D_800D154C=(u8 *)0x12345678;D_800C3E78=(s8)0xA5;
        result=c->input[5];mutation=c->input[6];
        calls=callReason=callFirst=capturedIndex=0;
        status=func_1508802C(record,actor,c->input[4]);
        actual[0]=status;actual[1]=calls;actual[2]=*(u32 *)actor;actual[3]=actor[0x232];
        actual[4]=state[0x84];actual[5]=*(u32 *)(actor+0x218);actual[6]=*(u16 *)(actor+0x21C);
        actual[7]=actor[0x125];actual[8]=record[0x30];actual[9]=D_800D154C==actor;
        actual[10]=(u8)D_800C3E78;actual[11]=capturedIndex;actual[12]=callReason;actual[13]=callFirst;
        for(i=0;i<14;i++)if(actual[i]!=c->expected[i])failure=21;
    }
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''


class GameRouteActorEventMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out)
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out,'test-selected')
        cls.retail=list(struct.unpack_from('>51I',cls.values['conker/conker.us.bin'],source.ROM))
        cls.cases=list(cases())

    def test_direct_words_frame_bindings_and_masked_shape_control(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(51,24,0,''))
        self.assertEqual(self.words,self.retail)
        integration.checked(self.obj)
        _,words,row=source.compile_candidate(self.root,self.out,'masked-control',source.MASKED)
        self.assertEqual((row['words'],row['frame'],row['differences']),(52,24,36))
        self.assertNotEqual(words,self.retail)

    def test_public_reference_full_ram_calls_and_saved_state(self):
        coverage=set()
        for i,case in enumerate(self.cases):
            for phase in (0,8):
                memory,args=fixture(case,phase)
                result=(0,0x80000000,0xDEADBEEF)[i%3]
                mutate=bool(i&1)
                a=EventOracle(self.retail,memory,args,phase,result,mutate).run()
                b=EventOracle(self.words,memory,args,phase,result,mutate).run()
                expected,ram,capture=reference(memory,args,result,mutate)
                self.assertEqual((a.r,a.f,a.lo,a.memory,a.events,a.captures),(b.r,b.f,b.lo,b.memory,b.events,b.captures))
                self.assertEqual((a.r[2],public(a.memory),a.captures),(expected,public(ram),capture))
                coverage.update(a.visits)
        self.assertEqual(coverage,set(range(source.ENTRY,source.ENTRY+204,4)))
        (self.out/'guest-cases.json').write_text(json.dumps(dict(cases=len(self.cases),phases=2,all51_words_visited=True))+'\n')

    def test_aliases_and_fired_own_access_fault_prefixes(self):
        count=0
        for phase in (0,8):
            for record,state in ((RECORD,STATE),(BASE,BASE),(BASE+0x201,STATE),(CURRENT-0x31,STATE),
                                 (STACK+phase-0x2D,STATE)):
                for case in ((0,0,0,128,0x1234568D),(0,0,1,128,13),(0,1,0,128,13)):
                    memory,args=fixture(case,phase,record,state)
                    mutate=record!=STACK+phase-0x2D
                    complete=EventOracle(self.retail,memory,args,phase,mutate=mutate).run()
                    for cut in range(complete.accesses):
                        pair=[]
                        for words in (self.retail,self.words):
                            model=EventOracle(words,memory,args,phase,mutate=mutate)
                            model.fault=cut
                            with self.assertRaises(AccessFault):model.run()
                            self.assertEqual(model.accesses,cut)
                            pair.append((model.r,model.f,model.lo,model.memory,model.events,model.captures))
                        self.assertEqual(*pair)
                        count+=1
        (self.out/'access-cuts.json').write_text(json.dumps(dict(fired_pairs=count,profiles=15,phases=2))+'\n')

    def test_all_signed_caller_slot_bytes_are_guest_only_outside_c_domain(self):
        for byte in range(256):
            slot=byte if byte<128 else byte-256
            case=(slot,0xA55A,0,byte,0x8123458D)
            memory,args=fixture(case)
            a=EventOracle(self.retail,memory,args).run()
            b=EventOracle(self.words,memory,args).run()
            ret,ram,capture=reference(memory,args,0xDEADBEEF,False)
            self.assertEqual((a.r,a.memory,a.events),(b.r,b.memory,b.events))
            self.assertEqual((a.r[2],public(a.memory),a.captures),(ret,public(ram),capture))

    def test_public_alias_order_against_independent_reference(self):
        for phase in (0,8):
            for record,state in ((RECORD,STATE),(BASE,BASE),(BASE+0x201,STATE),(CURRENT-0x31,STATE)):
                for mutate in (False,True):
                    memory,args=fixture((0,0,0,128,0x1234568D),phase,record,state)
                    model=EventOracle(self.words,memory,args,phase,mutate=mutate).run()
                    ret,ram,captures=reference(memory,args,0xDEADBEEF,mutate)
                    self.assertEqual((model.r[2],public(model.memory),model.captures),(ret,public(ram),captures))

    def test_actual_parent_caller_and_return_consumption(self):
        rom=self.values['conker/conker.us.bin']
        caller=list(struct.unpack_from('>53I',rom,0xB55A8))
        # Use the symbol's actual 0xD4-byte extent, including its return delay word.
        self.assertEqual(caller[-2:],[0x03E00008,0])
        pairs=0
        for slot in (0,15,16,25):
            for status in (0,1,2):
                for mask,flag in ((0,0),(65535,0),(0,1)):
                    for phase in (0,8):
                        memory,args=fixture((slot,mask,flag,slot,0x1234568D),phase)
                        for a,v,n in ((0x800872A0,RECORD,4),(RECORD+0x30,status,1),(0x800D239A,255,1)):
                            for i in range(n):memory[a+i]=0
                            put(memory,a,v,n)
                        pair=[]
                        for words in (self.retail,self.words):
                            connected=dict(zip(range(source.ENTRY,source.ENTRY+204,4),words))
                            model=EventOracle(caller,memory,(0,0x1234568D),phase,
                                entry=0x150880F8,connected=connected).run()
                            pair.append((model.r,model.memory,model.events,model.captures))
                            self.assertEqual(model.r[2],int(status==0 and (flag!=0 or bool(mask&(1<<slot)))))
                            self.assertEqual(read(model.memory,0x800D239A,1),0)
                            self.assertEqual(read(model.memory,RECORD+0x2A,1),255)
                        self.assertEqual(*pair)
                        pairs+=1
        (self.out/'caller-cases.json').write_text(json.dumps(dict(actual_caller_pairs=pairs))+'\n')

    def test_native32_o0_o2_and_ubsan_same_connected_corpus(self):
        rows=[]
        for i,case in enumerate(self.cases):
            result=(0,0x80000000,0xDEADBEEF)[i%3]
            mutation=i&1
            memory,args=fixture(case)
            model=EventOracle(self.words,memory,args,result=result,mutate=mutation).run()
            # Native fixtures seed uninterpreted bytes uniformly; normalize only those values.
            row=summary(model)
            if not model.captures:
                row[2]=0xA5A5A5A5;row[3]=row[4]=row[7]=row[8]=0xA5
                row[5]=0xA5A5A5A5;row[6]=0xA5A5
            fmt=lambda values:','.join('0x%Xu'%v for v in values)
            rows.append('{{%s},{%s}}'%(fmt((*case,result,mutation)),fmt(row)))
        text=NATIVE.replace('SOURCE_BODY',source.SELECTED).replace('ROWS',',\n'.join(rows))
        path=self.out/'native.c';path.write_text(text)
        profiles=(('o0','-O0',False,text,0),('o2','-O2',False,text,0),('ubsan','-O2',True,text,0),
            ('negative-return','-O2',True,text.replace('    return 0;','    return 1;'),21),
            ('outside-shift-domain','-O2',True,text.replace('1U << slot','1U << (slot + 32)'),-4))
        exits={}
        for name,opt,sanitize,unit,want in profiles:
            path=self.out/('native-'+name+'.c');path.write_text(unit)
            exe=self.out/('native-'+name)
            command=[*native_command(opt,sanitize),'-mstackrealign','-fno-strict-aliasing',str(path),'-o',str(exe)]
            built=subprocess.run(command,cwd=self.root,text=True,capture_output=True)
            (self.out/('native-'+name+'-compile.json')).write_text(json.dumps(dict(command=command,
                exit=built.returncode,diagnostics=built.stdout+built.stderr),indent=2)+'\n')
            self.assertEqual((built.returncode,built.stdout,built.stderr),(0,'',''),name)
            run=subprocess.run([str(exe)],text=True,capture_output=True)
            self.assertEqual((run.returncode,run.stdout,run.stderr),(want,'',''),name)
            exits[name]=run.returncode
        (self.out/'native-cases.json').write_text(json.dumps(dict(cases=len(self.cases),
            profiles=['O0','O2','O2+UBSan'],exits=exits,effective_semantic_controls=1,separate_sanitizer_boundary_control=True))+'\n')

    def test_ordinary_executed_semantic_negative_controls(self):
        forms={
            'success-return':source.SELECTED.replace('    return 0;','    return 1;'),
            'narrow-reason':source.SELECTED.replace('s32 reason)', 'u8 reason)'),
            'signed-mask':source.SELECTED.replace('D_800D18A0 &', '(s32)(s16)D_800D18A0 &'),
            'early-index':source.SELECTED.replace('    s32 slot;','    s32 slot;\n    s8 savedIndex = *(s8 *)(record + 0x31);').replace(
                'D_800C3E78 = *(s8 *)(record + 0x31);','D_800C3E78 = savedIndex;'),
        }
        for name,body in forms.items():
            _,words,_=source.compile_candidate(self.root,self.out,'negative-'+name,body)
            case=(16,0x8000,0,255,0x1234568D)
            memory,args=fixture(case,record=BASE+16*0x32C+0x201 if name=='early-index' else RECORD)
            a=EventOracle(self.retail,memory,args).run()
            b=EventOracle(words,memory,args).run()
            self.assertNotEqual((a.r[2],public(a.memory),a.captures),(b.r[2],public(b.memory),b.captures),name)

    def test_both_owner_profiles_and_actual_mixed_padder(self):
        row=integration.qualify(self.root,self.out)
        self.assertEqual(row['padded_functions_fixed'],73)
        self.assertEqual(row['new_guards'],0)

    def test_independent_assembly_and_gnu_relocation_maps(self):
        assembly=self.out/'original.s'
        assembly.write_text((self.root/'conker/include/asm_processor_prelude.inc').read_text()+
            '\n.text\n.type '+source.FUNCTION+', @function\n'+
            self.values['conker/asm/nonmatchings/generated_B3020/func_1508802C.s'].decode()+
            '\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        original=self.out/'original.o'
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
            '-o',str(original),str(assembly)],check=True,capture_output=True)
        self.assertEqual(integration.checked(original),integration.checked(self.obj))
        symbols=dict(D_800CC2D0=BASE,D_800D18A0=MASK,D_800D154C=CURRENT,
                     D_800C3E78=INDEX,func_1507BB28=SUBMIT)
        maps=[(source.ENTRY,symbols),(0x1621FFF4,dict(D_800CC2D0=0x80108010,D_800D18A0=0x8021FFF4,
            D_800D154C=0x8033FFF8,D_800C3E78=0x8045FFFC,func_1507BB28=0x16340034)),
            (0x18FFF000,dict(D_800CC2D0=0x8051FFF0,D_800D18A0=0x80628008,
            D_800D154C=0x80730004,D_800C3E78=0x80847FFC,func_1507BB28=0x18F0003C))]
        for number,(entry,bindings) in enumerate(maps):
            images=[]
            for label,obj in (('retail',original),('source',self.obj)):
                script=self.out/(label+'-map-%d.ld'%number)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in bindings.items()],'-o',str(elf),str(obj)],
                    check=True,capture_output=True)
                at,data=sections(elf)['.text']
                self.assertEqual(at,entry)
                images.append(data[:204])
            self.assertEqual(*images)
        # Execute code rebases with the original data/provider map; data rebases above are static only.
        paired=0
        for entry in (0x1621FFF4,0x18FFF000):
            for case in ((0,0,0,128,0x8123458D),(15,0x8000,0,255,13),(25,0,255,0,13)):
                memory,args=fixture(case)
                a=EventOracle(self.retail,memory,args,entry=entry).run()
                b=EventOracle(self.words,memory,args,entry=entry).run()
                self.assertEqual((a.r,a.memory,a.events),(b.r,b.memory,b.events))
                paired+=1
        (self.out/'relocation-maps.json').write_text(json.dumps(dict(GNU_maps=3,bindings=9,
            independent_assembly_equal=True,code_rebased_pairs=paired,data_rebases_static_only=True))+'\n')

    def test_first_whole_image_or_installed_audit(self):
        if (self.root/source.SOURCE).read_bytes()==self.values[source.SOURCE]:
            integration.qualify(self.root,self.out)
            self.assertTrue(integration.predict(self.root,self.out)['whole_ELF_unchanged'])
        else:
            self.assertTrue(integration.audit(self.root,self.out)['whole_ELF_unchanged'])


if __name__=='__main__':unittest.main()
