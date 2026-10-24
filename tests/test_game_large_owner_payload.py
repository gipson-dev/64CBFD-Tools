"""Owner payload: explicit returns, unspecified storage and derived scheduling."""
from dataclasses import dataclass
from pathlib import Path
import csv,io,itertools,json,struct,subprocess,unittest
from tools.experiments import game_large_owner_payload as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
OWNER,RESULT,CREATE,COPY,ALLOC,CONSTANT=0x30000,0x40000,0x1515FF74,0x10022EC0,0x15167A68,0x800A07FC
WINDOW,END,WINDOW_ROM=0x15027444,0x1502746C,0x548F4
DURATIONS=(0,1,0x7FFF,0x8000,0xFFFF,0x87654321)
CATEGORIES=(0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF)
@dataclass(frozen=True)
class Case:
    owner:int=OWNER
    duration:int=0x87654321
    selector:int=0xA5A5A5FF
    category:int=0xFFFFFFFF
    identity:int=0x81
    result:int=RESULT
    mode:int=0
    phase:int=0
    constant:int=0x46EA6000

def fixture(c):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-0x2000,0x1000)}
    for base in (OWNER,RESULT):
        m.update({base+i:(i*13+0xA5)&255 for i in range(-64,0x1000)})
    put(m,OWNER+0x3B,c.identity,1);put(m,CONSTANT,c.constant)
    return m

def reference(initial,c):
    m=dict(initial);sp=STACK+c.phase-0x918;payload,header=sp+0x20,sp+0x910
    for a,v in ((sp+0x918,c.owner),(sp+0x91C,c.duration),(sp+0x920,c.selector)):put(m,a,v)
    if not c.owner:return m
    for off,v,n in ((0,1,1),(1,1,1),(2,0,1),(4,c.duration,2),(6,2,1)):put(m,header+off,v,n)
    for off,v,n in ((0,c.owner,4),(4,m[c.owner+0x3B],1),(8,read(m,CONSTANT),4),
            (12,read(m,CONSTANT),4),(16,10000,4),(20,0,1)):put(m,payload+off,v,n)
    if c.mode:
        put(m,c.owner+0x3B,0xE7,1);put(m,CONSTANT,0x80000000)
    if c.mode==2:put(m,header+2,0x82,1)
    if c.result:
        for i in range(8):put(m,c.result+0xE+i,m[header+i],1)
        for i in range(0x8F0):put(m,c.result+0x18+i,m[payload+i],1)
    return m

def public(m):return {a:b for a,b in m.items()if not STACK-0x2000<=a<STACK+0x1000}
def observable(m):return public(m.memory),m.r[2],m.f,m.calls,tuple(m.r[i]for i in (*range(16,24),28,29,30,31))

class PayloadOracle(RayOracle):
    def __init__(self,words,memory,c,connected=None,entry=source.ENTRY):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,
            arguments=(c.owner,c.duration,c.selector,c.category),connected=connected)
        self.case=c;self.copy_sizes=[];self.header=None
    def record_call(self,t):
        counts={CREATE:4,COPY:3,ALLOC:6,source.ENTRY:4}
        assert t in counts,hex(t)
        args=self.arguments(counts[t]);self.calls.append((t,args));self.events.append(('CALL',t,args))
        if t==CREATE:self.header=args[0]
        if t==ALLOC and self.case.mode:
            self.put(self.case.owner+0x3B,0xE7,1);self.put(CONSTANT,0x80000000,4)
            if self.case.mode==2:self.put(self.header+2,0x82,1)
    def hook(self,t):
        value=self.case.result if t==ALLOC else 0
        if t==COPY:
            dst,src,n=self.arguments(3);assert n in (8,0x8F0)
            self.copy_sizes.append(n)
            for i in range(n):self.put(dst+i,self.get(src+i,1),1)
            value=dst
        else:assert t==ALLOC,hex(t)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=value

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==END:raise WindowBoundary
        return super().__getitem__(pc)

def controls():
    b=source.SELECTED[source.FUNCTION]
    return dict(identity=b.replace('owner[0x3B]','owner[0x3A]'),
        lifetime=b.replace('header.duration = duration','header.duration = duration ^ 1'),
        category=b.replace('header.category = 2','header.category = 3'),
        callback=b.replace('header.callback = 1','header.callback = 0'),
        flags=b.replace('header.flags = 0','header.flags = 1'),
        first=b.replace('payload.first = D_800A07FC','payload.first = 0.0f'),
        enabled=b.replace('payload.enabled = 0','payload.enabled = 1'),
        extent=b.replace('sizeof(payload)','sizeof(payload)-1'),
        destination=b.replace('record + 0x18','record + 0x19'),
        result=b.replace('    return record;','    return NULL;'))

class LargeOwnerPayloadTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.root=ROOT;cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.before=cls.values['conker/build/conker.us.elf']
        cls.retail=list(struct.unpack_from('>44I',cls.rom,source.ROM))
        cls.bodies=[]
        for obj in ('after-owner.o','qualified-padded.o'):
            data,fs=source.link_owner(ROOT,cls.out,cls.out/obj,source.OWNER);v=fs[source.FUNCTION]
            cls.bodies.append(list(struct.unpack_from('>%dI'%(v['size']//4),data,v['value'])))
        cls.raw,cls.words=cls.bodies
        cls.create=list(struct.unpack_from('>30I',cls.rom,0x18D424))
        cls.copy=list(struct.unpack_from('>11I',cls.rom,0x22EC0))
        for va,rom,n in ((CREATE,0x18D424,30),(COPY,0x22EC0,11)):
            at=source.elf_slot_offset(cls.before,va,n*4)
            assert cls.before[at:at+n*4]==cls.rom[rom:rom+n*4]
        cls.connected={CREATE+i*4:w for i,w in enumerate(cls.create)}
    def compare(self,c,real_copy=False):
        initial=fixture(c);expected=reference(initial,c);code=dict(self.connected)
        if real_copy:code.update({COPY+i*4:w for i,w in enumerate(self.copy)})
        models=[PayloadOracle(words,initial,c,code).run()for words in (self.retail,self.words,self.raw)]
        for m in models:
            self.assertEqual(public(m.memory),public(expected),c)
            self.assertEqual(m.r[2],c.result+0x18 if c.owner and c.result else 0)
            if c.owner:
                self.assertIn((ALLOC,(0x34,c.category,0x908,1,c.selector&255,1)),m.calls)
                self.assertEqual(sum(t==COPY for t,_ in m.calls),2 if c.result else 0)
            else:self.assertFalse(m.calls)
        self.assertEqual(complete(models[0]),complete(models[1]))
        self.assertEqual(observable(models[0]),observable(models[2]))
        return models[0]
    def test_01_words_owner_and_actual_make(self):
        raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION)
        self.assertEqual(source.normalized(raw,rs),source.payload(self.out/('original-'+source.FUNCTION+'.o'),source.FUNCTION))
        self.assertEqual(self.words,self.retail);self.assertEqual(len(self.raw),46)
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['preserved_neighbors'],q['new_guards'],q['omitted_redundant_words']),(4,12,2))
        mk=json.loads((self.out/'make-shadow.json').read_text())[0]
        self.assertEqual((mk['actual_Make_commands'],mk['compact_functions_equal']),(5,5))
        self.assertTrue(mk['complete_padded_object_equal'])
        self.receipt['words']=dict(raw=46,fitted=44,frame=0x918,guards=12,omitted_redundant_copies=2,neighbors=4,actual_Make_commands=5)
    def test_02_guest_defined_fields_and_unspecified_storage(self):
        count=0
        for owner,result,duration,category,phase in itertools.product((0,OWNER),(0,RESULT),DURATIONS,CATEGORIES,(0,8)):
            self.compare(Case(owner=owner,result=result,duration=duration,category=category,phase=phase));count+=1
        for byte,mode in itertools.product(range(256),range(3)):
            self.compare(Case(selector=0xA5A50000|byte,identity=255-byte,mode=mode,result=RESULT if byte&1 else 0));count+=1
        for constant,result in itertools.product((0,0x80000000,0x7F812345,0xFF800000),(0,RESULT,OWNER-0x18)):
            self.compare(Case(constant=constant,result=result));count+=1
        self.receipt['guest']=dict(cases=count,all_selector_and_identity_bytes=True,
            complete_guest_poison_storage_preserved=True,raw_public_return_saved_states_equal=True,
            opaque_bytes_not_portably_fixed=True)
    def test_03_original_caller_window_and_discarded_result(self):
        # The instruction window begins after the VM helper returns its duration endpoint.
        parent=self.values['conker/src/game/generated_50D80.c'].decode()
        self.assertIn('s32 func_150265CC() {\n    return 0;\n}',parent)
        jal=0x0C000000|((source.ENTRY>>2)&0x3FFFFFF)
        literals=[];calls=[]
        for i in range(0,len(self.rom)-3,4):
            w=struct.unpack_from('>I',self.rom,i)[0]
            if w==source.ENTRY:literals.append(i)
            if w==jal:calls.append(i)
        self.assertEqual(literals,[]);self.assertEqual(calls,[0x5490C])
        window=list(struct.unpack_from('>10I',self.rom,WINDOW_ROM))
        count=0
        for owner,result,duration in itertools.product((0,OWNER),(0,RESULT),DURATIONS):
            c=Case(owner=owner,result=result,duration=duration,category=0)
            memory=fixture(c);sp=STACK
            put(memory,sp+0x75C,0x87654321);put(memory,sp+0x764,owner);put(memory,sp+0x770,0xA5A500FF)
            models=[]
            for words in (self.retail,self.words,self.raw):
                code=dict(self.connected);code.update({source.ENTRY+i*4:w for i,w in enumerate(words)})
                code[0x15029BA4]=0
                m=PayloadOracle(window,memory,c,code,entry=WINDOW)
                m.r[2]=(0x87654321+duration)&0xFFFFFFFF
                # The branch after the call overwrites V0 with one regardless of target result.
                class CallerCode(faults.TrackedCode):
                    def __getitem__(self,pc):
                        if pc==0x15029BA4:raise WindowBoundary
                        return super().__getitem__(pc)
                m.code=CallerCode(m.code,m)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(m.r[2],1)
                a=[a for t,a in m.calls if t==source.ENTRY][0]
                low=duration&65535;signed=low if low<32768 else low-65536
                self.assertEqual(a,(owner,signed&0xFFFFFFFF,255,0))
                models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt['caller']=dict(cases=count,sole_direct_JAL=True,no_literal_registrations=True,
            original_window_words=10,caller_overwrites_result=True,full_parent_C_uncredited=True)
    def test_04_native32_defined_fields_returns_and_controls(self):
        body=source.SELECTED[source.FUNCTION]
        fixture_c=source.HEADERS+source.DECLARATIONS+"""
f32 D_800A07FC=30000.0f;
static u8 owner[128],storage[0x1000];static int failed,mode,error,calls,copies,identity;
static s16 expectedDuration;static u8 expectedSelector;static s32 expectedCategory;
static void bytes(void *d,const void *s,u32 n){u32 i;for(i=0;i<n;i++)((u8 *)d)[i]=((const u8 *)s)[i];}
void *func_1515FF74(void *p,s32 size,u8 selector,s32 category){
 OwnerPayloadHeaderFB600 *h=p;calls++;
 if(size!=0x8F0||selector!=expectedSelector||category!=expectedCategory||
 h->active!=1||h->callback!=1||h->flags!=0||h->duration!=expectedDuration||h->category!=2)error=1;
 if(mode){owner[0x3B]=0xE7;D_800A07FC=-0.0f;}if(mode==2)h->flags=0x82;
 if(failed)return NULL;bytes(storage+0xE,p,8);return storage;
}
void *memcpy(void *d,const void *s,size_t n){
 const LargeOwnerPayloadFB600 *p=s;copies++;
 if(d!=storage+0x18||n!=0x8F0||p->owner!=owner||p->identity!=identity||
 p->first!=30000.0f||p->second!=30000.0f||p->limit!=10000||p->enabled!=0)error=2;
 bytes(d,s,n);return d;
}
"""+body+"""
int run(void){int nullOwner,byte,i;void *value;
 if(sizeof(void*)!=4||sizeof(OwnerPayloadHeaderFB600)!=8||sizeof(LargeOwnerPayloadFB600)!=0x8F0)return 9;
 for(nullOwner=0;nullOwner<2;nullOwner++)for(failed=0;failed<2;failed++)for(mode=0;mode<3;mode++)for(byte=0;byte<256;byte++){
  calls=copies=error=0;D_800A07FC=30000.0f;identity=255-byte;owner[0x3B]=(u8)identity;
  expectedDuration=(s16)((u32)byte*257u);expectedSelector=(u8)byte;expectedCategory=(s32)((u32)byte*0x80000001u);
  for(i=0;i<0x1000;i++)storage[i]=0xA5;
  value=func_150CE150(nullOwner?NULL:owner,expectedDuration,expectedSelector,expectedCategory);
  if(error||calls!=!nullOwner||copies!=(!nullOwner&&!failed))return 10;
  if(value!=(!nullOwner&&!failed?storage+0x18:NULL))return 11;
  for(i=0;i<0x1000;i++){
   int payload=i>=0x18&&i<0x908,header=i>=0xE&&i<0x16;
   if((nullOwner||failed||(!payload&&!header))&&storage[i]!=0xA5)return 12;
  }
 }return 0;
}
"""+START
        for opt in ('-O0','-O2','-O3'):
            p=self.out/('native-'+opt[1:]+'.c');p.write_text(fixture_c);binary=p.with_suffix('')
            subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=self.root,capture_output=True,check=True)
            self.assertEqual(subprocess.run([str(binary)],timeout=30).returncode,0,opt)
        for name,b in controls().items():
            p=self.out/('native-negative-'+name+'.c');p.write_text(fixture_c.replace(body,b));binary=p.with_suffix('')
            subprocess.run(native_command('-O2')+['-mstackrealign',str(p),'-o',str(binary)],cwd=self.root,capture_output=True,check=True)
            self.assertNotEqual(subprocess.run([str(binary)],timeout=30).returncode,0,name)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],cases_per_profile=3072,trap_UBSan=True,
            controls=len(controls()),explicit_return_values=True,opaque_payload_and_header_bytes_not_asserted=True)
    def test_05_fired_root_access_prefixes(self):
        count=0
        for c in (Case(),Case(owner=0),Case(result=0),Case(mode=2)):
            m=self.compare(c);initial=fixture(c)
            for fault in range(m.root_accesses):
                models=[]
                for words in (self.retail,self.words):
                    x=PayloadOracle(words,initial,c,self.connected);x.root_fault=fault
                    with self.assertRaises(faults.AccessBoundary):x.run()
                    self.assertEqual(x.root_accesses,fault);models.append(x)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt['faults']=dict(pairs=count,emitted_guest_prefixes_only=True)
    def test_06_normalizer_and_actual_padder_controls(self):
        raw,rs=source.payload(self.out/'after-owner.o',source.FUNCTION);count=0
        for i in range(46):
            bad=bytearray(raw);bad[i*4+3]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),rs)
            count+=1
        for at in rs:
            bad=dict(rs);bad[at]=[(rs[at][0][0],'wrong_symbol')]
            with self.assertRaises(ValueError):source.normalized(raw,bad)
            count+=1
        old=self.values['conker/retail_word_patches.us.csv'];new=source.guard_bytes(old,raw,rs)
        self.assertTrue(new.startswith(old));rows=list(csv.DictReader(io.StringIO(new[len(old):].decode()),fieldnames=list(csv.DictReader(io.StringIO(old.decode())).fieldnames)))
        self.assertEqual(len(rows),12);self.assertEqual(sum(x['omit']=='true'for x in rows),2)
        bad=self.out/'bad-guards.csv';bad.write_bytes(new.replace(b'0x00601025,0x00601025',b'0x00601024,0x00601025'))
        with self.assertRaises(ValueError):
            source.emit_padded_assembly(self.out/'after-owner.o',self.root/source.ASM,word_patches_path=bad,filename=source.OWNER)
        fitted,fr=source.normalized(raw,rs)
        anchors=dict(D_800A07FC=CONSTANT,func_1515FF74=CREATE,memcpy=COPY)
        assembly,missing=emit_function(fitted,dict(value=0,size=176),fr,source.FUNCTION,anchors)
        self.assertFalse(missing)
        path=self.out/'fitted-independent.s';path.write_text(assembly);obj=path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
        for index,constant in enumerate((CONSTANT,0x800AFFF0,0x81238004)):
            delta=index*0x200000;symbols=dict(anchors,D_800A07FC=constant,func_1515FF74=CREATE+delta,memcpy=COPY+delta)
            script=self.out/('rebase-'+str(index)+'.ld')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(source.ENTRY+delta))
            outputs=[]
            for label,p in (('original',self.out/('original-'+source.FUNCTION+'.o')),('fitted',obj)):
                elf=self.out/('rebase-%d-%s.elf'%(index,label))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%(k,v)for k,v in symbols.items()],'-o',str(elf),str(p)],capture_output=True,check=True)
                outputs.append(sections(elf)['.text'][:176])
            self.assertEqual(*outputs)
        self.receipt['guards']=dict(word_and_binding_controls=count,rows=12,omissions=2,actual_padder_control=True,
            historical_prefix_unchanged=True,independent_GNU_links=6,layouts=3,HI16_carry_boundaries=True)
    def test_07_connected_original_factory_and_copy(self):
        visits=set();count=0
        for owner,result,mode in itertools.product((0,OWNER),(0,RESULT),(0,2)):
            m=self.compare(Case(owner=owner,result=result,mode=mode),real_copy=True)
            visits.update(m.visits);count+=1
        for va,n in ((CREATE,30),(COPY,11)):
            self.assertTrue(set(range(va,va+4*n,4))<=visits,hex(va))
        self.receipt['connected']=dict(cases=count,original_factory_words=30,original_memcpy_words=11,
            every_helper_word_visited=True,allocator_bounded=True,no_full_parent_or_hardware_claim=True)
    def test_08_strict_image_and_frozen_inputs(self):
        truth=source.truths(self.values);predicted=source.predicted_image(self.before,truth)
        source.check_image(self.before,(self.out/'first-linked.elf').read_bytes(),truth)
        self.assertEqual(sum(a!=b for a,b in zip(self.before,predicted)),149)
        for at in (0,source.elf_slot_offset(predicted,source.ENTRY,176),
                   source.elf_slot_offset(predicted,0x150CE740,4),len(predicted)-1):
            bad=bytearray(predicted);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(self.before,bytes(bad),truth)
        installed=(self.root/source.SOURCE).read_text()!=self.values[source.SOURCE].decode()
        source.check_inputs(self.root,self.out,installed)
        self.receipt['strict']=dict(changed_bytes=149,code_bytes=148,metadata_bytes=1,exclusions=0,controls=4,focused_inputs=35)

if __name__=='__main__':unittest.main()
