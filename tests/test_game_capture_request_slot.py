"""Public C reconstruction and explicit remaining private-state mismatch."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_capture_request_slot as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.tests import test_game_actor_mask_scan_match as machine
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object,emit_padded_assembly

EXTERNAL=0x21000
STATES=list(itertools.product((0,1,128,255),repeat=3))
CALLBACKS=(0,127,128,255,256,0xFFFFFF80,0x7FFFFFFF)
VECTORS=((0,0x80000000,0x3F800000),(0xC0200000,0x7F800000,0xFF800000),
    (0x7FC12345,0x7FA00001,0xFFFFFFFF),(0x3E800000,0x3F000000,0x40800000))


def fixture(states,callback,vector,mode,phase=0):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-128,160)}
    memory.update({source.BASE+i:(i*13+0x5A)&255 for i in range(-16,196)})
    memory.update({EXTERNAL+i:(i*7+0x31)&255 for i in range(-16,52)})
    for i,value in enumerate(states):
        put(memory,source.BASE+i*60+12,value,1)
    put(memory,STACK+phase+16,callback)
    value=(callback^0xBEEFCAFE)&0xFFFFFFFF
    put(memory,STACK+phase+20,value)
    first=next((i for i,state in enumerate(states) if state==0),0)
    payload=(0,EXTERNAL,source.BASE+first*60+16,source.BASE+((first+1)%3)*60+16)[mode]
    return memory,payload,value


def reference(memory,states,callback,vector,payload,value,phase=0):
    result=dict(memory)
    put(result,STACK+phase+8,vector[2])
    index=next((i for i,state in enumerate(states) if state==0),None)
    if index is None:
        return result,1
    base=source.BASE+index*60
    for offset,bits in zip((0,4,8),vector):
        put(result,base+offset,bits)
    put(result,base+12,3,1)
    put(result,base+52,callback&255,1)
    put(result,base+56,value)
    if payload:
        for offset in range(0,36,4):
            put(result,base+16+offset,read(result,payload+offset))
    return result,0


class RequestOracle(machine.MaskOracle):
    def __init__(self,words,memory,vector,payload,phase=0,fault=None):
        super().__init__(words,memory,phase=phase,entry=source.ENTRY,
            arguments=(0x12345678,0xFEDCBA98,vector[2],payload),fault=fault)
        self.f[12],self.f[14]=vector[:2]
        self.current_pc=self.delay_of=None
        self.code=faults.TrackedCode(self.code,self)

    def execute(self,word):
        if word>>26!=0x20:
            return super().execute(word)
        rs,rt,offset=(word>>21)&31,(word>>16)&31,word&65535
        offset=offset-65536 if offset&32768 else offset
        self.dispatched_word,self.own_instruction=word,True
        try:
            value=self.get((self.r[rs]+offset)&0xFFFFFFFF,1)
        finally:
            self.own_instruction=False
        self.r[rt]=(value-256 if value&128 else value)&0xFFFFFFFF
        self.r[0]=0


def state(instance):
    return (tuple(instance.r),tuple(instance.f),dict(instance.memory),tuple(instance.events),
        instance.lo,instance.condition,instance.current_pc,instance.delay_of,instance.accesses,tuple(instance.calls))


def native_program(body,rows):
    literal=lambda values:'{'+','.join('0x%Xu'%(v&0xFFFFFFFF) for v in values)+'}'
    cases=[]
    for states,callback,vector,mode in rows:
        memory=bytearray().join(struct.pack('<I',0xA55A1234^(i*0x10203)) for i in range(53))
        for index,value in enumerate(states):
            memory[16+index*60+12]=value
        index=next((i for i,value in enumerate(states) if value==0),None)
        value=(callback^0xBEEFCAFE)&0xFFFFFFFF
        if index is not None:
            base=16+index*60
            for offset,bits in zip((0,4,8),vector):
                struct.pack_into('<I',memory,base+offset,bits)
            memory[base+12],memory[base+52]=3,callback&255
            struct.pack_into('<I',memory,base+56,value)
            if mode:
                if mode==1:
                    payload=b''.join(struct.pack('<I',0xAC000000+i*0x10203) for i in range(9))
                else:
                    at=16+(index if mode==2 else (index+1)%3)*60+16
                    payload=memory[at:at+36]
                memory[base+16:base+52]=payload
        expected=struct.unpack('<53I',memory)
        cases.append('{%s,%s,0x%Xu,0x%Xu,%d,%d,%s}'%(literal(states),literal(vector),callback&0xFFFFFFFF,value,mode,
            1 if index is None else 0,literal(expected)))
    types=source.TYPES[:source.TYPES.index('extern CaptureRequest1A11B0')]
    return '''typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;typedef float f32;
#define NULL ((void*)0)
'''+types+'''
typedef struct{u32 before[4];CaptureRequest1A11B0 requests[3];u32 after[4];}Bank;
typedef struct{u32 states[3],xyz[3],callback,value,mode,result,expected[53];}Case;
static Bank bank;static CapturePayload1A11B0 externalPayload;
static Case cases[]={'''+',\n'.join(cases)+'''};
/* Native storage bridge binds both original symbols to one real three-record array. */
#define D_800DD348 (bank.requests)
#define D_800DD3FC (bank.requests+3)
'''+body+'''
static int run(void){u32 n,i,first,result,*words=(u32*)&bank;const CapturePayload1A11B0 *payload;
 union{u32 bits;f32 value;}x,y,z;
 if(sizeof(void*)!=4||sizeof(bank)!=212||sizeof(CaptureRequest1A11B0)!=60||sizeof(CapturePayload1A11B0)!=36)return 90;
 if(__builtin_offsetof(CaptureRequest1A11B0,state)!=12||__builtin_offsetof(CaptureRequest1A11B0,payload)!=16||
    __builtin_offsetof(CaptureRequest1A11B0,callback)!=52||__builtin_offsetof(CaptureRequest1A11B0,value)!=56)return 91;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  for(i=0;i<53;i++)words[i]=0xA55A1234u^(i*0x10203u);
  for(i=0;i<9;i++)externalPayload.words[i]=0xAC000000u+i*0x10203u;
  first=0;for(i=0;i<3;i++){bank.requests[i].state=cases[n].states[i];}
  for(i=0;i<3;i++){if(bank.requests[i].state==0){first=i;break;}}
  payload=cases[n].mode==0?NULL:cases[n].mode==1?&externalPayload:
    &bank.requests[cases[n].mode==2?first:(first+1)%3].payload;
  x.bits=cases[n].xyz[0];y.bits=cases[n].xyz[1];z.bits=cases[n].xyz[2];
  result=func_151745F0(x.value,y.value,z.value,payload,(s8)cases[n].callback,(s32)cases[n].value);
  if(result!=cases[n].result)return 2;
  for(i=0;i<53;i++){if(words[i]!=cases[n].expected[i])return 2;}
  for(i=0;i<9;i++){if(externalPayload.words[i]!=(0xAC000000u+i*0x10203u))return 3;}
 }return 0;}
void _start(void){int value=run();__asm__ volatile("int $0x80"::"a"(1),"b"(value));__builtin_unreachable();}
'''


class CaptureRequestSlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.record=source.qualify(cls.root,cls.out)
        cls.retail=list(struct.unpack_from('>40I',(cls.root/'conker/conker.us.bin').read_bytes(),source.ROM))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def native(self,label,body,rows):
        path=self.out/('native-'+label+'.c')
        path.write_text(native_program(body,rows))
        statuses=[]
        for profile in ('O2','O0'):
            binary=path.with_suffix('.'+profile)
            result=subprocess.run(['cc','-m32','-'+profile,'-std=c11','-fno-strict-aliasing','-fno-builtin',
                '-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector',
                '-Wall','-Wextra','-Werror','-fmax-errors=3',str(path),'-o',str(binary)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr[:4000])
            self.assertEqual(result.stderr,'')
            statuses.append(subprocess.run([str(binary)],capture_output=True).returncode)
        return statuses

    def test_01_real_copy_body_and_all_bounded_screens(self):
        self.assertEqual((self.record['body_words'],self.record['slot_words'],self.record['differences']),(39,40,22))
        self.assertEqual(self.record['diagnostics'],'')
        self.assertFalse(self.record['installable'])
        original=(self.out/'before-request_original').read_text()
        block=original.split('glabel '+source.FUNCTION,1)[1].split('endlabel '+source.FUNCTION,1)[0]
        body=[int(x,16) for x in re.findall(r'/\* [0-9A-F]+ [0-9A-F]+ ([0-9A-F]{8}) \*/',block)]
        self.assertEqual(body,self.retail[:39])
        self.assertEqual(self.retail[-1],0)
        counts=(('screens.json',7),('schedule-screens.json',10),('address-screens.json',8),
            ('interface-screens.json',9),('layout-screens.json',6),('return-screens.json',5),('profile-screens.json',9))
        rows=[]
        for name,count in counts:
            record=json.loads((self.out/name).read_text())
            self.assertEqual(len(record),count)
            self.assertTrue(all(row['diagnostics']=='' for row in record))
            self.assertTrue(all(row['differences']>0 for row in record))
            rows+=record
        self.assertEqual(len(rows),54)
        self.receipt('shape',complete_owner_controls=45,isolated_profile_controls=9,body_words=39,
            real_alignment_nops=1,raw_differences=22,no_pseudo_calls_or_frame=True,not_a_byte_match=True)

    def test_02_guest_complete_public_memory_and_FP_abi(self):
        coverage=set()
        cases=private_differences=0
        for states,callback,vector,mode in itertools.product(STATES,CALLBACKS,VECTORS,range(4)):
            for phase in (0,8):
                memory,payload,value=fixture(states,callback,vector,mode,phase)
                expected,result=reference(memory,states,callback,vector,payload,value,phase)
                instances=[RequestOracle(words,memory,vector,payload,phase).run() for words in (self.retail,self.words)]
                for instance in instances:
                    self.assertEqual((instance.memory,instance.r[2],instance.calls),(expected,result,[]))
                coverage.update(instances[0].visits)
                private_differences+=state(instances[0])!=state(instances[1])
                cases+=1
        self.assertEqual(len(coverage),38)
        missing={source.ENTRY+i*4 for i in range(40)}-coverage
        self.assertEqual(missing,{0x15174674,0x1517468C})
        self.assertEqual(self.retail[33],0x2463003C)
        self.assertGreater(private_differences,0)
        self.receipt('guest',paired_SP_cases=cases,all_38_reachable_words=True,
            unreachable_duplicate_increment=0x15174674,alignment_nop=0x1517468C,
            complete_memory_and_result_equal=True,FP_bit_patterns_and_signed_byte_narrowing=True,
            null_external_self_other_payloads=True,private_state_differences=private_differences,
            not_FCSR_or_hardware_or_installed_acceptance=True)

    def test_03_native_real_C_and_all_record_bytes(self):
        rows=list(itertools.product(STATES,(-128,-1,0,127),(VECTORS[0],VECTORS[3]),range(4)))
        self.assertEqual(self.native('selected',source.SELECTED,rows),[0,0])
        self.receipt('native',cases_per_profile=len(rows),profiles=['O2','O0'],zero_diagnostics=True,
            all_212_bank_bytes_and_external_payload=True,all_layout_offsets_checked=True,
            finite_FP_cases_and_explicit_native_storage_bridge=True,not_private_MIPS_or_endian_equivalence=True)

    def test_04_three_effective_returned_controls(self):
        negatives=dict(state=source.SELECTED.replace('request->state = 3','request->state = 2'),
            z=source.SELECTED.replace('request->z = z','request->z = y'),
            partial_copy=source.SELECTED.replace('request->payload = *payload','request->payload.words[0] = payload->words[0]'))
        states,callback,vector,mode=(0,1,128),-1,VECTORS[3],1
        memory,payload,value=fixture(states,callback,vector,mode)
        expected,result=reference(memory,states,callback,vector,payload,value)
        for label,body in negatives.items():
            self.assertNotEqual(body,source.SELECTED)
            _,words,_=source.measure(self.root,self.out,'negative-'+label,body)
            instance=RequestOracle(words,memory,vector,payload).run()
            self.assertEqual(instance.r[2],result)
            self.assertNotEqual(instance.memory,expected)
            native_body=body.replace('request->z = y;','(void)z; request->z = y;') if label=='z' else body
            self.assertEqual(self.native(label,native_body,[(states,callback,vector,mode)]),[2,2])
        self.receipt('controls',returned_guest_and_native_mismatches=3,native_statuses=[2,2],not_crash_acceptance=True)

    def test_05_paired_fired_prefixes_preserve_the_mismatch(self):
        total=different=0
        for states,mode in itertools.product(((0,1,255),(1,0,128),(1,255,0),(1,128,255)),range(4)):
            memory,payload,_=fixture(states,-1,VECTORS[3],mode)
            count=RequestOracle(self.retail,memory,VECTORS[3],payload).run().accesses
            for cut in range(count):
                instances=[]
                for words in (self.retail,self.words):
                    instance=RequestOracle(words,memory,VECTORS[3],payload,fault=cut)
                    with self.assertRaises(machine.AccessFault):
                        instance.run()
                    self.assertEqual(instance.accesses,cut)
                    instances.append(instance)
                different+=state(instances[0])!=state(instances[1])
                total+=1
        self.assertGreater(different,0)
        self.receipt('prefixes',paired_fired_prefixes=total,private_differences=different,
            not_private_exact_or_hardware_exceptions=True)

    def test_06_owner_neighbors_pools_and_real_padder(self):
        old_obj,diagnostics=build.compile_owner(self.root,self.out,(self.out/'before-request_owner').read_text(),'legacy')
        self.assertEqual(diagnostics,'')
        a,af,ar=parse_object(old_obj)
        b,bf,br=parse_object(self.obj)
        relative=lambda rel,f:{at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
        for name in set(af)-{source.FUNCTION}:
            x,y=af[name],bf[name]
            self.assertEqual((x['size'],a[x['value']:x['value']+x['size']],relative(ar,x)),
                (y['size'],b[y['value']:y['value']+y['size']],relative(br,y)),name)
        self.assertEqual(normalized_pools(old_obj),normalized_pools(self.obj))
        assembly=emit_padded_assembly(self.obj,self.root/source.PATHS['request_original'],filename=source.OWNER,
            word_patches_path=self.root/source.PATHS['guards'])
        path=self.out/'padded.s'
        path.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+'"\n'+assembly)
        obj=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
        data,functions=build.link_owner(self.root,self.out,obj,source.OWNER)
        f=functions[source.FUNCTION]
        self.assertEqual(f['size'],156)
        self.assertEqual(list(struct.unpack_from('>40I',data,f['value'])),self.words)
        self.receipt('neighbors',unchanged_raw_neighbors=2,all_sizes_bytes_relative_relocations_and_pools_fixed=True,
            production_padder_retains_raw_22_differences=True,no_guards_or_installation=True)

    def test_07_all_production_inputs_and_frozen_corruption_controls(self):
        for key,path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(),source.BASELINE[key],key)
        rb=Path.read_bytes
        for key in source.PATHS:
            target=self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:rb(p)+b'\n' if p==target else rb(p)):
                with self.assertRaisesRegex(ValueError,'immutable capture request'):
                    source.freeze(self.root,self.out)
        self.receipt('preservation',unchanged_production_inputs=len(source.PATHS),all_before_capture_controls=True,
            production_stub_guards_headers_profiles_progress_and_ELF_fixed=True)


if __name__=='__main__':
    unittest.main()
