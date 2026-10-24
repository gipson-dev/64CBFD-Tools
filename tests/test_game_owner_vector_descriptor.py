"""Direct owner-vector descriptor, typed forwarding ABI and bounded constructor."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_owner_vector_descriptor as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_owner_descriptor_preset import PresetOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
OWNER,RECORD,MATRIX=0x28000,0x30000,0x38000
HELPER,ALLOC,COPY,DELETE,TRANSFORM=0x1513418C,0x15167A68,0x10022EC0,0x1516972C,0x15143134
PARENT,PARENT_ROM=0x1506A6FC,0x97BAC
SYMBOLS=dict(D_800A5480=0x800A5480,D_800A0FB4=0x800A0FB4,D_800A0FB8=0x800A0FB8,func_1513418C=HELPER)
PATTERNS=(0,0x80000000,0x3F800000,0x7F800000,0x7FC12345,0x7FA12345,0xFFFFFFFF,0x00800000)
CATEGORIES=(0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF)
@dataclass(frozen=True)
class Case:
    selector:int=255
    category:int=1
    identity:int=0xA7
    vector:tuple=(0,0,0)
    first:int=0x412E6667
    second:int=0x3E6CC250
    effects:int=0
    result:int=RECORD
    alias:int=-1
    allocated:bool=True
    valid:bool=True
    matrix:bool=False
    actor_type:int=0

def packet(phase):return STACK+phase-48
def actor(c,phase):return OWNER if c.alias<0 else packet(phase)+c.alias-0x3B
def fixture(c,phase=0,s=None):
    s=s or SYMBOLS;m={STACK+i:(i*17+0xA5)&255 for i in range(-0x800,0x400)}
    for base in (OWNER,RECORD,MATRIX):
        m.update({base+i:(i*13+0x5A)&255 for i in range(-64,0x240)})
    put(m,OWNER,1 if c.valid else 0);put(m,OWNER+0x3B,c.identity,1)
    put(m,OWNER+0x1D4,MATRIX if c.matrix else 0);put(m,OWNER+0x74,c.actor_type,1)
    for i,v in enumerate(c.vector):put(m,s['D_800A5480']+4*i,v)
    put(m,s['D_800A0FB4'],c.first);put(m,s['D_800A0FB8'],c.second)
    return m
def packet_reference(initial,c,phase=0,s=None):
    s=s or SYMBOLS;m=dict(initial);p=packet(phase);owner=actor(c,phase)
    put(m,STACK+phase,owner);put(m,STACK+phase+4,c.selector)
    put(m,p,0);put(m,p+4,0);identity=read(m,owner+0x3B,1)
    put(m,p+16,0,1);put(m,p+12,owner);put(m,p+8,identity,1)
    a=read(m,s['D_800A5480']);b=read(m,s['D_800A5480']+4);put(m,p+20,a)
    d=read(m,s['D_800A5480']+8);put(m,p+24,b);put(m,p+28,d)
    a=read(m,s['D_800A0FB4']);b=read(m,s['D_800A0FB8'])
    put(m,p+40,300,2)
    for off,v in ((42,0x1B),(43,0x0B),(44,255),(45,0)):put(m,p+off,v,1)
    put(m,p+32,a);put(m,p+36,b)
    return m,bytes(m[p+i]for i in range(48))
def public(m):return {a:v for a,v in m.items()if not STACK-0x800<=a<STACK+0x400}
def effect(m,owner,s):
    put(m,owner+0x3B,read(m,owner+0x3B,1)^1,1)
    for i in range(3):put(m,s['D_800A5480']+4*i,0x76543210+i)
    put(m,s['D_800A0FB4'],0x87654321);put(m,s['D_800A0FB8'],0xFEDCBA98)

class VectorOracle(PresetOracle):
    def __init__(self,words,memory,c=Case(),phase=0,s=None,entry=source.ENTRY,connected=None,parent=False):
        self.case,self.bindings=c,s or SYMBOLS
        self.owner_pointer=actor(c,phase-24 if parent else phase)
        self.packets,self.trace=[],[]
        args=(self.owner_pointer,0x87654321)if parent else(self.owner_pointer,c.selector,c.category)
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=args,connected=connected)
    def record_call(self,target):
        counts={source.ENTRY:3,self.bindings['func_1513418C']:4,ALLOC:6,COPY:3,DELETE:1,TRANSFORM:4}
        args=self.arguments(counts[target]);self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==self.bindings['func_1513418C']:
            self.packets.append(bytes(self.memory[args[0]+i]for i in range(48)))
        if target==ALLOC and self.case.effects&1:effect(self.memory,self.owner_pointer,self.bindings)
    def hook(self,target):
        c=self.case;s=self.bindings
        if target==s['func_1513418C']:
            if c.effects:effect(self.memory,self.owner_pointer,s)
            value=c.result
        elif target==ALLOC:value=RECORD if c.allocated else 0
        elif target==COPY:
            dst,src,n=self.arguments(3);assert n==48
            for i in range(n):self.put(dst+i,self.get(src+i,1),1)
            value=dst
        elif target==DELETE:value=0x87654321
        else:
            assert target==TRANSFORM
            src,dst,matrix,record=self.arguments(4)
            assert(src,dst,matrix,record)==(RECORD+0x24,RECORD+0x40,MATRIX,RECORD)
            for i in range(3):self.put(dst+i*4,0x3F800000+i*0x800000,4)
            if c.effects&2:self.put(RECORD+0x30,0x3F000000,4)
            value=0x87654321
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True
        self.r[2]=value

def controls():
    b=source.SELECTED[source.FUNCTION]
    return dict(zero=b.replace('descriptor.zero4 = 0','descriptor.zero4 = 1'),
        identity=b.replace('owner[0x3B]','owner[0x3A]'),
        owner=b.replace('descriptor.owner = owner','descriptor.owner = NULL'),
        attachment=b.replace('descriptor.attachment = 0','descriptor.attachment = 1'),
        vector=b.replace('descriptor.vector = D_800A5480','descriptor.vector = D_800A5480;\n    descriptor.vector.y = D_800A5480.x'),
        first=b.replace('descriptor.value20 = D_800A0FB4','descriptor.value20 = 0.0f'),
        second=b.replace('descriptor.value24 = D_800A0FB8','descriptor.value24 = 0.0f'),
        duration=b.replace('descriptor.duration = 300','descriptor.duration = 301'),
        flags=b.replace('descriptor.flags = 0x1B','descriptor.flags = 0x19'),
        kind=b.replace('descriptor.kind = 0x0B','descriptor.kind = 0x0A'),
        sentinel=b.replace('descriptor.callback = -1','descriptor.callback = 0'),
        selector=b.replace('0, selector, category','0, selector ^ 1, category'),
        category=b.replace('0, selector, category','0, selector, category ^ 1'),
        result=b.replace('    return func_1513418C(&descriptor, 0, selector, category);',
            '    func_1513418C(&descriptor, 0, selector, category);\n    return NULL;'))

class OwnerVectorDescriptorTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.root=ROOT;cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.before=cls.values['conker/build/conker.us.elf']
        cls.truth=list(struct.unpack_from('>44I',cls.rom,source.ROM))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER)
        cls.words=list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value']))
        cls.parent=list(struct.unpack_from('>10I',cls.rom,PARENT_ROM))
        cls.helper=list(struct.unpack_from('>76I',cls.rom,0x16163C))
        cls.copy=list(struct.unpack_from('>11I',cls.rom,0x22EC0))
        cls.alias_cache={}
        for va,rom,n in ((HELPER,0x16163C,76),(COPY,0x22EC0,11)):
            at=source.elf_slot_offset(cls.before,va,n*4)
            assert cls.before[at:at+n*4]==cls.rom[rom:rom+n*4]
    def linked(self,obj,entry,s,label,name=source.FUNCTION):
        script=self.out/(label+'.ld');elf=script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,
            *['--defsym=%s=0x%X'%(k,v)for k,v in s.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
        data=sections(elf)['.text'][1]
        return list(struct.unpack('>%dI'%(len(data)//4),data))
    def compare(self,c=Case(),phase=0,s=None,images=None,entry=source.ENTRY):
        s=s or SYMBOLS;m=fixture(c,phase,s);expected,p=packet_reference(m,c,phase,s)
        models=[VectorOracle(w,m,c,phase,s,entry).run()for w in images or(self.truth,self.words)]
        for x in models:
            self.assertEqual(x.packets,[p]);self.assertEqual(x.calls,[(s['func_1513418C'],(packet(phase),0,c.selector&255,c.category))])
            if c.effects:effect(expected,actor(c,phase),s)
            self.assertEqual(public(x.memory),public(expected));self.assertEqual(x.r[2],c.result)
            expected,p=packet_reference(m,c,phase,s)
        self.assertEqual(complete(models[0]),complete(models[1]))
        return models[0]
    def test_01_direct_owner_caller_and_make(self):
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['total_words'],q['new_guards'],q['preserved_neighbors']),(44,0,12))
        self.assertEqual(q['caller']['all_functions_identical'],16)
        self.assertTrue(q['caller']['complete_padded_object_equal']);self.assertEqual(self.words,self.truth)
        for name in ('selected-'+source.FUNCTION+'.o','after-owner.o','qualified-padded.o','original-'+source.FUNCTION+'.o'):
            self.assertEqual(source.payload(self.out/name,source.FUNCTION),source.payload(self.out/'after-owner.o',source.FUNCTION))
        mk=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual([x['actual_Make_commands']for x in mk],[3,5])
        self.assertEqual([x['compact_functions_equal']for x in mk],[13,16])
        self.assertTrue(all(x['complete_padded_object_equal']for x in mk))
        data,rs=source.payload(self.out/'after-owner.o',source.FUNCTION);self.assertEqual(rs,source.BINDINGS)
        # The preset lies inside protected initialized Game data, not a fabricated zero literal.
        at=source.elf_slot_offset(self.before,0x800A5480,12);self.assertEqual(self.before[at:at+12],bytes(12))
        self.assertEqual(self.rom[0x245A74:0x245A7C],bytes.fromhex('412e66673e6cc250'))
        self.receipt['direct']=dict(words=44,frame=72,bindings=7,new_guards=0,neighbors=12,caller_functions_unchanged=16,actual_Make_commands=8)
    def test_02_packets_bytes_mutations_and_guest_aliases(self):
        count=0
        for byte,phase in itertools.product(range(256),(0,8)):
            c=Case(selector=0xA5A50000|byte,category=CATEGORIES[byte%5],identity=255-byte,
                vector=tuple(PATTERNS[(byte+i)%8]for i in range(3)),first=PATTERNS[byte%8],
                second=PATTERNS[(byte+3)%8],effects=byte%4,result=RECORD if byte&1 else 0)
            self.compare(c,phase);count+=1
        for category,result,phase in itertools.product(CATEGORIES,(0,RECORD,1,0xFFFFFFFF),(0,8)):
            self.compare(Case(category=category,result=result),phase);count+=1
        for alias,phase in itertools.product((0,4,8,9,12,16,20,32),(0,8)):
            self.compare(Case(alias=alias),phase);count+=1
        for off,phase in itertools.product((0,12,16,20,24,28,32,40),(0,8)):
            c=Case();s=dict(SYMBOLS,D_800A5480=packet(phase)+off)
            key=tuple(s.items())
            if key not in self.alias_cache:
                self.alias_cache[key]=[self.linked(self.out/obj,source.ENTRY,s,'alias-%d-%s'%(off,label))[:44]
                    for label,obj in (('original','original-'+source.FUNCTION+'.o'),('C','selected-'+source.FUNCTION+'.o'))]
            self.compare(c,phase,s,self.alias_cache[key]);count+=1
        self.receipt['guest']=dict(cases=count,all_selector_and_identity_bytes=True,complete_48_byte_packet=True,
            private_aliases_guest_only=True,provider_mutations=True,full_states_equal=True)
    def test_03_actual_typed_forwarder(self):
        # Preserve both the ordinary C cleanup and its complete ten-word retail wrapper.
        m=self.values[source.CALLER_SOURCE].decode();new=source.recovered_caller(m)
        self.assertIn(source.CALLER_BODY,new)
        obj,diag=source.compile_owner(self.root,self.out,'#include <ultra64.h>\nvoid *func_150E0348(u8 *,u8,s32);\n'+source.CALLER_BODY,'isolated-caller')
        self.assertFalse(diag)
        code,fs=source.link_owner(self.root,self.out,obj,'generated_97AA0')
        self.assertEqual(list(struct.unpack_from('>10I',code,fs['func_1506A6FC']['value'])),self.parent)
        jal=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
        calls=[];literals=[]
        for i in range(0,len(self.rom)-3,4):
            w=struct.unpack_from('>I',self.rom,i)[0]
            if w==jal:calls.append(i)
            if w==source.ENTRY:literals.append(i)
        self.assertEqual(calls,[0x97BBC]);self.assertFalse(literals)
        count=0
        for phase,result,effects in itertools.product((0,8),(0,RECORD,0xFFFFFFFF),(0,3)):
            c=Case(result=result,effects=effects);memory=fixture(c,phase);root_phase=phase-24
            _,expected=packet_reference(memory,c,root_phase)
            models=[]
            for words in (self.truth,self.words):
                code={source.ENTRY+i*4:w for i,w in enumerate(words)}
                x=VectorOracle(self.parent,memory,c,phase,entry=PARENT,connected=code,parent=True).run()
                self.assertEqual(x.packets,[expected]);self.assertEqual(x.r[2],result)
                self.assertIn((source.ENTRY,(OWNER,255,1)),x.calls);models.append(x)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt['caller']=dict(cases=count,words=10,frame=24,sole_direct_JAL=True,typed_prototype=True,explicit_return_preserved=True)
    def test_04_native32_actual_callee_and_wrapper(self):
        b=source.SELECTED[source.FUNCTION]
        text=source.HEADERS+source.DECLARATIONS+"""
OwnerVector10CD70 D_800A5480;f32 D_800A0FB4,D_800A0FB8;
static union{u32 alignment;u8 bytes[512];}owner,record;
static u32 v[3],first,second,expectSelector,expectCategory,expectIdentity;
static int calls,error,failed;
static void setword(void *p,u32 v){u32 i;for(i=0;i<4;i++)((u8 *)p)[i]=((u8 *)&v)[i];}
static u32 getword(const void *p){u32 v,i;for(i=0;i<4;i++)((u8 *)&v)[i]=((const u8 *)p)[i];return v;}
void *func_1513418C(void *source,s32 size,u8 selector,s32 category){
 OwnerVectorDescriptor10CD70 *p=source;calls++;
 if(size||selector!=expectSelector||(u32)category!=expectCategory||p->zero0||p->zero4||
 p->owner!=owner.bytes||p->ownerIdentity!=expectIdentity||p->attachment||
 getword(&p->vector.x)!=v[0]||getword(&p->vector.y)!=v[1]||getword(&p->vector.z)!=v[2]||
 getword(&p->value20)!=first||getword(&p->value24)!=second||p->duration!=300||
 p->flags!=0x1B||p->kind!=0xB||p->callback!=-1||p->mode)error=1;
 owner.bytes[0x3B]^=1;setword(&D_800A5480.x,0x87654321);setword(&D_800A0FB4,0xFEDCBA98);
 return failed?NULL:record.bytes;
}
"""+b+'\n'+source.CALLER_BODY+"""
int run(void){
 u32 values[8]={0,0x80000000,0x3F800000,0x7F800000,0x7FC12345,0x7FA12345,0xFFFFFFFF,0x00800000};
 u32 category[5]={0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF};int form,byte,mode,i;void *returned;
 if(sizeof(void*)!=4||sizeof(OwnerVector10CD70)!=12||sizeof(OwnerVectorDescriptor10CD70)!=48)return 9;
 for(form=0;form<2;form++)for(byte=0;byte<256;byte++)for(mode=0;mode<3;mode++)for(failed=0;failed<2;failed++){
  for(i=0;i<512;i++)owner.bytes[i]=record.bytes[i]=(u8)(i*13+0x5A);
  expectIdentity=(u8)(255-byte);owner.bytes[0x3B]=(u8)expectIdentity;calls=error=0;
  expectSelector=form?255:(u32)byte;expectCategory=form?1:category[byte%5];
  for(i=0;i<3;i++)v[i]=values[(byte+i+mode)%8];
  first=values[(byte+3)%8];second=values[(byte+5)%8];
  setword(&D_800A5480.x,v[0]);setword(&D_800A5480.y,v[1]);setword(&D_800A5480.z,v[2]);
  setword(&D_800A0FB4,first);setword(&D_800A0FB8,second);
  returned=form?func_1506A6FC(owner.bytes,(s32)((u32)byte*0x80000001u)):func_150E0348(owner.bytes,(u8)byte,(s32)expectCategory);
  if(error||calls!=1||returned!=(failed?NULL:record.bytes))return 10;
  for(i=0;i<512;i++){
   u8 expected=(u8)(i*13+0x5A);if(i==0x3B)expected=(u8)(expectIdentity^1);
   if(owner.bytes[i]!=expected||record.bytes[i]!=(u8)(i*13+0x5A))return 11;
  }
 }return 0;
}
"""+START
        for opt in ('-O0','-O2','-O3'):
            path=self.out/('native-'+opt[1:]+'.c');path.write_text(text);binary=path.with_suffix('')
            subprocess.run(native_command(opt)+['-mstackrealign',str(path),'-o',str(binary)],cwd=self.root,capture_output=True,check=True)
            self.assertEqual(subprocess.run([str(binary)],timeout=30).returncode,0,opt)
        for label,body in controls().items():
            path=self.out/('native-negative-'+label+'.c');path.write_text(text.replace(b,body));binary=path.with_suffix('')
            subprocess.run(native_command('-O2')+['-mstackrealign',str(path),'-o',str(binary)],cwd=self.root,capture_output=True,check=True)
            self.assertNotEqual(subprocess.run([str(binary)],timeout=30).returncode,0,label)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],cases_per_profile=3072,controls=len(controls()),
            trap_UBSan=True,actual_recovered_root_and_forwarder=True,unspecified_padding_not_asserted=True)
    def test_05_fired_root_access_prefixes_and_null_contract(self):
        count=0
        for c in (Case(),Case(effects=3),Case(alias=12)):
            m=self.compare(c);initial=fixture(c)
            for fault in range(m.root_accesses):
                models=[]
                for words in (self.truth,self.words):
                    x=VectorOracle(words,initial,c);x.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,fault);models.append(x)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        models=[]
        for words in (self.truth,self.words):
            x=VectorOracle(words,fixture(Case()));x.r[4]=0
            with self.assertRaisesRegex(AssertionError,'unmapped read'):x.run()
            self.assertFalse(x.calls);models.append(x)
        self.assertEqual(complete(models[0]),complete(models[1]))
        self.receipt['faults']=dict(pairs=count,emitted_guest_order_only=True,retail_null_owner_fault_preserved=True)
    def test_06_padding_negative_and_independent_links(self):
        body=source.SELECTED[source.FUNCTION]
        bad=body.replace('    descriptor.mode = 0;','''    descriptor.mode = 0;
    descriptor.reserved09[0] = descriptor.reserved09[1] = descriptor.reserved09[2] = 0;
    descriptor.reserved11[0] = descriptor.reserved11[1] = descriptor.reserved11[2] = 0;
    ((u8 *)&descriptor)[46] = ((u8 *)&descriptor)[47] = 0;''')
        obj,diag=source.compile_owner(self.root,self.out,source.HEADERS+source.DECLARATIONS+bad,'negative-padding')
        self.assertFalse(diag)
        words=self.linked(obj,source.ENTRY,SYMBOLS,'negative-padding-linked')
        c=Case();memory=fixture(c);_,expected=packet_reference(memory,c)
        actual=VectorOracle(words,memory,c).run().packets[0]
        self.assertNotEqual(actual,expected)
        self.assertEqual([actual[i]for i in (9,10,11,17,18,19,46,47)],[0]*8)
        links=0
        for i,vector in enumerate((SYMBOLS['D_800A5480'],0x800AFFF8,0x81238004)):
            s=dict(SYMBOLS,D_800A5480=vector,D_800A0FB4=vector+32,D_800A0FB8=vector+36,func_1513418C=HELPER+i*0x200000)
            images=[self.linked(self.out/p,source.ENTRY+i*0x200000,s,'rebase-%d-%s'%(i,label))[:44]
                for label,p in (('original','original-'+source.FUNCTION+'.o'),('C','selected-'+source.FUNCTION+'.o'))]
            self.assertEqual(*images);links+=2
            self.compare(Case(),0,s,images,source.ENTRY+i*0x200000)
        self.receipt['links']=dict(independent_GNU_links=links,layouts=3,HI16_carry_boundaries=True,
            defined_padding_zeroing_control_effective_in_guest=True)
    def test_07_original_constructor_owner_gates_and_matrix_call(self):
        connected={HELPER+i*4:w for i,w in enumerate(self.helper)}
        connected.update({COPY+i*4:w for i,w in enumerate(self.copy)})
        count=0;visits=set()
        for allocated,valid,matrix,actor_type,effects,first in itertools.product(
                (False,True),(False,True),(False,True),(0,15),(0,1,2),(0x3F800000,0x40000000)):
            c=Case(allocated=allocated,valid=valid,matrix=matrix,actor_type=actor_type,effects=effects,first=first)
            initial=fixture(c);expected,p=packet_reference(initial,c);models=[]
            if effects&1:effect(expected,OWNER,SYMBOLS)
            accepted=allocated and valid and not(effects&1)
            if allocated:
                for i,v in enumerate(p):put(expected,RECORD+16+i,v,1)
                if accepted:
                    if matrix and actor_type!=15:
                        for i in range(3):put(expected,RECORD+0x40+i*4,0x3F800000+i*0x800000)
                        if effects&2:put(expected,RECORD+0x30,0x3F000000)
                    value=floating(read(expected,RECORD+0x30))
                    put(expected,RECORD+0x4C,bits(1.0/floating(bits(value+value))));put(expected,RECORD+0x50,0)
            for words in (self.truth,self.words):
                x=VectorOracle(words,initial,c,connected=connected).run()
                self.assertEqual(x.packets,[p]);self.assertEqual(public(x.memory),public(expected))
                self.assertEqual(x.r[2],RECORD if accepted else 0)
                self.assertIn((ALLOC,(0x28,c.category,0x58,1,c.selector&255,1)),x.calls)
                self.assertEqual(any(t==DELETE for t,_ in x.calls),allocated and not accepted)
                self.assertEqual(any(t==TRANSFORM for t,_ in x.calls),accepted and matrix and actor_type!=15)
                visits.update(x.visits);models.append(x)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        missing=set(range(HELPER,HELPER+304,4))-visits
        self.assertEqual(missing,{0x15134234,0x15134284})
        self.assertTrue(set(range(COPY,COPY+44,4))<=visits)
        self.receipt['connected']=dict(cases=count,original_constructor_words=76,reachable_words_visited=74,
            unreachable_duplicate_load_and_flag2_false_arm=True,original_copy_words=11,
            owner_rejection_and_finite_reciprocal=True,allocator_delete_matrix_bounded=True,general_FCSR_and_full_matrix_not_claimed=True)
    def test_08_strict_image_cycles_and_frozen_inputs(self):
        truth=source.truths(self.values);pred=source.predicted_image(self.before,truth)
        source.check_image(self.before,(self.out/'first-linked.elf').read_bytes(),truth)
        self.assertEqual(sum(a!=b for a,b in zip(self.before,pred)),201)
        controls=[0,len(pred)-1,source.elf_slot_offset(pred,source.ENTRY,176),source.elf_slot_offset(pred,PARENT,40)]
        for offset,name,fields,location in source.symbol_rows(pred):
            if name in ('D_800A0FB4','D_80090AD0','D_800A2D90','D_800A0FB8','func_1515F10C'):
                controls.extend((offset+4,location+2))
        for at in controls:
            wrong=bytearray(pred);wrong[at]^=1
            with self.assertRaises(ValueError):source.check_image(self.before,bytes(wrong),truth)
        installed=(self.root/source.SOURCE).read_text()!=self.values[source.SOURCE].decode()
        source.check_inputs(self.root,self.out,installed)
        self.receipt['strict']=dict(changed_bytes=201,code_bytes=136,metadata_bytes=65,exclusions=0,
            closed_symbol_cycles=[3,2],controls=len(controls),focused_inputs=34)

if __name__=='__main__':unittest.main()
