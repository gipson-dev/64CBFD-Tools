"""Burst descriptor snapshot, byte ABI, scheduling guards and complete image."""
from dataclasses import dataclass,replace
import csv,hashlib,itertools,json,struct,subprocess,unittest
from tools.experiments import game_point_burst_configuration_candidates as candidate
from tools.experiments import game_point_burst_configuration_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
ROOT=candidate.ROOT
POINT,CALLEE,RANDOM=0x20000,0x15152190,0x150ADA20
PATTERNS=(0,0x80000000,1,0x007FFFFF,0x3F800000,0xBF800000,0x7F7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    point:int=POINT
    channel:int=0xABCD00FF
    context:int=0x80000000
    pattern:int=0
    phase:int=0
    mutation:int=0
    result:int=0x81234560

def symbols(base=0x800AB558,selector=0x800AB550,scale=0x800AB554,callee=CALLEE):
    return dict(zip(('D_800AB558','D_800AB55C','D_800AB560','D_800AB564'),(base+i*4 for i in range(4))),
        D_800AB550=selector,D_800AB554=scale,func_15152190=callee)

def fixture(c=Case(),s=None):
    s=s or symbols();m={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
    m.update({POINT+i:(i*13+91)&255 for i in range(64)})
    for j,name in enumerate(('D_800AB558','D_800AB55C','D_800AB560','D_800AB564','D_800AB550','D_800AB554')):
        put(m,s[name],PATTERNS[(c.pattern+j)%len(PATTERNS)])
    for j in range(3):put(m,POINT+4*j,PATTERNS[(c.pattern+j+2)%len(PATTERNS)])
    return m

def packet(m,p):return bytes(m[p+i]for i in range(60))
def expected_packet(m,p,s):
    return struct.pack('>2I',12,5)+bytes(m[p+i]for i in range(12))+struct.pack('>4h2I',0,255,-64,49,0x40400000,0x41100000)+\
        bytes(m[s['D_800AB55C']+i]for i in range(4))+bytes(m[s['D_800AB560']+i]for i in range(4))+\
        struct.pack('>2h',25,20)+bytes(m[s['D_800AB558']+i]for i in range(4))*2+bytes(m[s['D_800AB564']+i]for i in range(4))

def bound(obj,s):
    raw,rs=match.function_blob(obj);words=list(struct.unpack('>66I',raw))
    for at,rows in rs.items():
        if len(rows)!=1:raise ValueError('Unexpected packet relocation pair')
        kind,name=rows[0];value=s[name]
        if kind=='R_MIPS_HI16':words[at//4]=(words[at//4]&0xFFFF0000)|((value+0x8000)>>16&65535)
        elif kind=='R_MIPS_LO16':words[at//4]=(words[at//4]&0xFFFF0000)|(value&65535)
        elif kind=='R_MIPS_26':words[at//4]=(words[at//4]&0xFC000000)|(value>>2&0x3FFFFFF)
        else:raise ValueError('Unexpected packet relocation kind')
    return words

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=match.ENTRY,connected=None,arguments=None):
        self.s=s or symbols();self.observations=[];self.prefix=False
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,
            arguments=arguments or(c.point,u32(c.channel),u32(c.context)))
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,False
    def record_call(self,t):
        if t==self.s['func_15152190']:
            a=tuple(map(u32,self.arguments(8)))
            self.observations.append((packet(self.memory,a[0]),a[1:],read(self.memory,a[1]),read(self.memory,a[2])))
        elif t==match.ENTRY:a=tuple(map(u32,self.arguments(3)))
        elif t==RANDOM:
            self.observations.append(('original-callee-prefix',self.r[29],read(self.memory,self.r[29]+0xC0),
                self.memory[self.r[29]+0x107]));raise WindowBoundary
        else:raise AssertionError(('Unbounded configuration helper',hex(t)))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        assert t==self.s['func_15152190']
        a=self.calls[-1][1]
        if self.case.mutation:
            for p in(self.case.point,*self.s.values(),a[0],a[1],a[2]):
                if p!=self.s['func_15152190']:put(self.memory,p,0xFEDC1234)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(self.case.result)

def controls():
    b=candidate.SELECTED
    return dict(count=b.replace('packet.count = 12','packet.count = 11'),
        pitch=b.replace('packet.pitch = -64','packet.pitch = 64'),
        scale=b.replace('f32 scale = D_800AB558','f32 scale = D_800AB55C'),
        byte=b.replace('0, channel, context','0, channel + 1, context'),
        mode=b.replace('26.0f, 0, channel','26.0f, 1, channel'),
        context=b.replace('channel, context);','channel, context ^ 1);'),
        pointer=b.replace('&D_800AB554, 1','&D_800AB558, 1'),
        position=b.replace('    packet.angle = 0;','    packet.position.z = 0.0f;\n    packet.angle = 0;'))

def native_source(body):
    return '''typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;
'''+candidate.PACKET+'''
f32 D_800AB558,D_800AB55C,D_800AB560,D_800AB564,D_800AB554;s32 D_800AB550;
static Position20A290 point;static u32 inputs[3],anchors[4];static s32 wantedContext;static u8 wantedChannel;static int calls,error,mutation;
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 number(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
void func_15152190(Configuration20A290 *p,s32 *selector,f32 *scale,s32 count,f32 zero,u8 mode,u8 channel,s32 context){
calls++;
if(p->count!=12||p->countRange!=5||word(p->position.x)!=inputs[0]||word(p->position.y)!=inputs[1]||word(p->position.z)!=inputs[2])error=1;
if(p->angle||p->angleRange!=255||p->pitch!=-64||p->pitchRange!=49||word(p->speed)!=0x40400000||word(p->speedRange)!=0x41100000||p->lifetime!=25||p->lifetimeRange!=20)error=2;
if(word(p->vertical)!=anchors[1]||word(p->verticalRange)!=anchors[2]||word(p->scale)!=anchors[0]||word(p->scaleRange)!=anchors[0]||word(p->spread)!=anchors[3])error=3;
if(selector!=&D_800AB550||scale!=&D_800AB554||count!=1||word(zero)!=0x41D00000||mode!=0||channel!=wantedChannel||context!=wantedContext)error=4;
if(mutation){point.x=number(0xFEDC1234);D_800AB558=number(0xFEDC1234);D_800AB550=-1;D_800AB554=0;p->count=0;p->position.z=0;}
}
'''+body+'''
static u32 patterns[]={0,0x80000000,0x3F800000,0xBF800000,0x7FC12345};
static int test(void){unsigned value,pattern;int m,i,indirect;Configuration20A290 packet;
void(*typed)(Position20A290 *,u8,s32)=func_151DCDE0;
if(sizeof(void*)!=4||sizeof(packet)!=60||(u8*)&packet.position-(u8*)&packet!=8||(u8*)&packet.angle-(u8*)&packet!=20||(u8*)&packet.speed-(u8*)&packet!=28||(u8*)&packet.lifetime-(u8*)&packet!=44||(u8*)&packet.scale-(u8*)&packet!=48||(u8*)&packet.spread-(u8*)&packet!=56)return 9;
for(value=0;value<256;value++)for(pattern=0;pattern<5;pattern++)for(m=0;m<2;m++)for(indirect=0;indirect<2;indirect++){
for(i=0;i<3;i++)inputs[i]=patterns[(pattern+i)%5];for(i=0;i<4;i++)anchors[i]=patterns[(pattern+i+1)%5];
point.x=number(inputs[0]);point.y=number(inputs[1]);point.z=number(inputs[2]);
D_800AB558=number(anchors[0]);D_800AB55C=number(anchors[1]);D_800AB560=number(anchors[2]);D_800AB564=number(anchors[3]);D_800AB550=19;D_800AB554=2.0f;
wantedChannel=(u8)value;wantedContext=(s32)(value*0x9E3779B9u);mutation=m;calls=error=0;
if(indirect)typed(&point,wantedChannel,wantedContext);else func_151DCDE0(&point,wantedChannel,wantedContext);
if(calls!=1||error)return 1;
if(word(point.x)!=(m?0xFEDC1234:inputs[0])||word(point.y)!=inputs[1]||word(point.z)!=inputs[2]||word(D_800AB558)!=(m?0xFEDC1234:anchors[0])||D_800AB550!=(m?-1:19)||word(D_800AB554)!=(m?0:0x40000000))return 2;
}return 0;}
void _start(void){int status=test();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''

class PointBurstConfigurationMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT);cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>66I',cls.rom,match.ROM))
        linked,fs=candidate.link_owner(ROOT,cls.out,cls.prepared['qualified_compact'],candidate.OWNER)
        cls.raw=list(struct.unpack_from('>66I',linked,fs[match.FUNCTION]['value']))
        linked,fs=candidate.link_owner(ROOT,cls.out,cls.prepared['qualified_owner'],candidate.OWNER)
        cls.words=list(struct.unpack_from('>66I',linked,fs[match.FUNCTION]['value']))
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        ctx=type('PacketOriginal',(),dict(root=ROOT,out=cls.out))
        cls.original=ViewListSetupTests.original.__func__(ctx,'original-packet',(ROOT/match.ASM).read_text(),match.FUNCTION)
        assert bound(cls.original,symbols())==cls.retail
        assert bound(cls.prepared['qualified_compact'],symbols())==cls.raw
        assert bound(cls.prepared['qualified_owner'],symbols())==cls.words
    def receipt(self,n,r):(self.out/(n+'.json')).write_text(json.dumps(r,indent=2)+'\n')
    def compare(self,c,initial=None,images=None,s=None,entry=match.ENTRY,redirect=False):
        initial=fixture(c,s)if initial is None else initial;models=[]
        for words in images or(self.retail,self.words):
            m=Oracle(words,initial,c,s,entry)
            try:m.run()
            except AssertionError as e:
                if not redirect or not e.args or not isinstance(e.args[0],tuple)or e.args[0][0]!='unowned jump':raise
            models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].observations,models[1].observations)
        return models[0]
    def test_01_complete_owner_bindings_and_checked_instruction_permutations(self):
        q=self.prepared['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['relocations'],q['raw_neighbors'],q['neighbors']),(66,104,16,13,0,0))
        self.assertEqual(self.retail,self.words);self.assertEqual(len(match.PERMUTATION),16)
        self.assertEqual(set(match.PERMUTATION),set(match.PERMUTATION.values()))
        raw,rs=match.function_blob(self.prepared['qualified_compact']);truth=self.rom[match.ROM:match.ROM+264]
        for i in range(264):
            bad=bytearray(raw);bad[i]^=1
            with self.assertRaises(ValueError):match.normalized(bytes(bad),rs,truth)
        for i in rs:
            bad=dict(rs);bad[i]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):match.normalized(raw,bad,truth)
        self.receipt('guard-rejections',dict(byte_controls=264,binding_controls=13,closed_permutations=2))
    def test_02_complete_packet_guest_cases_and_live_provider_mutations(self):
        count=0;coverage=set()
        for pattern,point,channel,context,phase,mutation,result in itertools.product(range(5),(POINT,0x800AB558),
                (0,0xABCD0080,0xFEDC00FF),(0,0x80000000,0x7FFFFFFF),(0,8),(0,1),(0,0x81234560)):
            c=Case(point,channel,context,pattern,phase,mutation,result);initial=fixture(c);s=symbols()
            for body in(self.retail,self.raw,self.words):
                m=Oracle(body,initial,c).run();a=(s['D_800AB550'],s['D_800AB554'],1,0x41D00000,0,channel&255,context)
                self.assertEqual(m.observations,[(expected_packet(initial,point,s),a,read(initial,a[0]),read(initial,a[1]))])
                self.assertEqual(m.r[2],result);coverage.update(m.visits)
                for p in range(POINT,POINT+12):self.assertEqual(m.memory[p],(0xFEDC1234>>(8*(3-(p-POINT))))&255 if mutation and point==POINT and p<POINT+4 else initial[p])
            self.compare(c,initial);count+=1
        self.assertEqual(coverage,set(range(match.ENTRY,match.ENTRY+264,4)))
        self.receipt('guest-contract',dict(cases_per_body=count,bodies=3,reachable_words=66,return_ignored=True))
    def test_03_all_byte_values_and_special_float_transport(self):
        count=0
        for channel,pattern in itertools.product(range(256),range(10)):
            c=Case(channel=0xFEDC0000|channel,pattern=pattern,phase=(channel&1)*8);initial=fixture(c)
            m=self.compare(c,initial);self.assertEqual(m.observations[0][0],expected_packet(initial,c.point,symbols()));count+=1
        self.receipt('byte-transport',dict(cases_per_body=count,all_unsigned_byte_values=True,float_patterns=10))
    def test_04_private_stack_and_global_aliases(self):
        count=0
        for phase,point_offset in itertools.product((0,8),(-104,-100,-96,-80,-68,-60,-56,-52,-48,-44,-40,-16,-12,-8,-4,0,4,8,32)):
            c=Case(point=STACK+phase+point_offset,phase=phase);self.compare(c,redirect=True);count+=1
        for phase,offset in itertools.product((0,8),(-104,-100,-96,-88,-84,-80,-76,-68,-60,-56,-52,-48,-44,-40,-16,-12,-8,-4,0,4,8)):
            s=symbols(base=STACK+phase+offset);c=Case(phase=phase)
            images=(bound(self.original,s),bound(self.prepared['qualified_owner'],s))
            self.compare(c,fixture(c,s),images=images,s=s,redirect=True);count+=1
        self.receipt('aliases',dict(original_fitted_cases=count,natural_private_stack_alias_parity_not_claimed=True))
    def test_05_fired_fault_prefixes(self):
        count=0
        for c in(Case(),Case(point=0x800AB558,phase=8),Case(point=STACK-52)):
            initial=fixture(c);done=Oracle(self.retail,initial,c).run()
            for cut in range(done.all_accesses):
                models=[]
                for body in(self.retail,self.words):
                    m=Oracle(body,initial,c);m.cut=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(models[0].trace,models[1].trace);count+=1
        self.receipt('fault-prefixes',dict(fired_prefixes=count,scope='original and fitted; natural reordered fault parity not claimed'))
    def test_06_original_height_gate_call_window_and_callee_prefix(self):
        from tools.tests.game_animation_timeline_oracle import bits,floating
        count=0;start,end=0x15055838,0x15055888
        body=list(struct.unpack_from('>20I',self.rom,0x82CE8));actor=0x50000
        for phase,gate,pattern,result in itertools.product((0,8),range(5),range(3),(0,0x81234560)):
            h=STACK+phase;point=h+0x4C;c=Case(point=point,phase=phase,result=result,pattern=pattern)
            initial=fixture(c);initial.update({actor+i:(i*13+89)&255 for i in range(0x130)})
            surface,y=((bits(0.),bits(1.)),(bits(1.),bits(1.)),(bits(2.),bits(1.)),(0x7FC12345,bits(1.)),(bits(0.),0x7FC12345))[gate]
            for at,value in((0x118,surface),(0x14,PATTERNS[pattern]),(0x18,y),(0x1C,PATTERNS[pattern+2])):put(initial,actor+at,value)
            called=floating(surface)<floating(y);prepared=dict(initial)
            if called:
                for i,value in enumerate((read(initial,actor+0x14),bits(floating(y)+20.),read(initial,actor+0x1C))):put(prepared,point+4*i,value)
            models=[]
            for target in(self.retail,self.raw,self.words):
                code=dict(zip(range(match.ENTRY,match.ENTRY+264,4),target));m=Oracle(body,initial,c,entry=start,connected=code)
                m.r[16]=actor;m.code[end]=0;m.code=WindowCode(m.code,m);m.code.ends=(end,)
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual(len(m.observations),int(called));self.assertEqual(m.r[4],actor)
                if called:
                    self.assertEqual(m.calls[0],(match.ENTRY,(point,255,1)))
                    self.assertEqual(m.observations[0][0],expected_packet(prepared,point,symbols()))
                    self.assertEqual(m.observations[0][1],(symbols()['D_800AB550'],symbols()['D_800AB554'],1,0x41D00000,0,255,1))
                models.append(m)
            self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        prefix=list(struct.unpack_from('>56I',self.rom,0x17F640));connected=dict(zip(range(CALLEE,CALLEE+224,4),prefix));runs=0
        for target,phase in itertools.product((self.retail,self.raw,self.words),(0,8)):
            c=Case(phase=phase);m=Oracle(target,fixture(c),c,connected=connected)
            with self.assertRaises(WindowBoundary):m.run()
            self.assertEqual(m.observations[-1][0],'original-callee-prefix')
            self.assertEqual(m.observations[-1][1],m.before[29]-104-240)
            self.assertEqual(m.observations[-1][3],0);runs+=1
        self.receipt('callers',dict(cases_per_body=count,original_caller_window_words=20,height_ties_and_NaNs=True,callee_prefix_words=56,callee_prefix_runs=runs,full_parents_not_claimed=True))
    def test_07_independent_GNU_links_and_relocation_carry_edges(self):
        original=self.original
        links=count=0
        for j,(entry,s)in enumerate(((match.ENTRY,symbols()),(0x18017FFC,symbols(0x800B7FF8,0x800C8000,0x800C7FFC,0x18038000)),
                (0x1A028000,symbols(0x800C8000,0x800B7FFC,0x800B8000,0x1A048000)))):
            images=[]
            for k,obj in enumerate((original,self.prepared['qualified_compact'],self.prepared['qualified_owner'])):
                text,fs,rs=parse_object(obj);asm,unknown=emit_function(text,fs[match.FUNCTION],rs,match.FUNCTION,s);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(j,k));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',match.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>66I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2])
            for channel,phase,mutation in itertools.product((0,0xABCD0080,0xFEDC00FF),(0,8),(0,1)):
                c=Case(channel=channel,phase=phase,mutation=mutation);m=self.compare(c,images=(images[0],images[2]),s=s,entry=entry)
                self.assertEqual(m.observations[0][0],expected_packet(fixture(c,s),c.point,s));count+=1
        self.receipt('rebases',dict(GNU_links=links,original_fitted_cases=count,raw_GNU_links_retained=True,carry_edges=True))
    def test_08_native_layout_typed_calls_and_effective_controls(self):
        for label,body,opt,wanted in [('positive-'+opt[1:],candidate.SELECTED,opt,0)for opt in('-O0','-O2','-O3')]+[(n,b,'-O2',1)for n,b in controls().items()]:
            p=self.out/('native-'+label+'.c');p.write_text(native_source(body));exe=p.with_suffix('.elf')
            result=subprocess.run([*native_command(opt),'-mstackrealign',str(p.relative_to(ROOT)),'-o',str(exe.relative_to(ROOT))],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native-'+label+'-diagnostics.txt')).write_text(result.stdout+result.stderr)
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[:4000]);self.assertEqual(subprocess.run([str(exe)]).returncode,wanted,label)
        self.receipt('native-contract',dict(positive_executions=15360,profiles=['O0','O2','O3'],typed_and_direct=True,controls=8))
        initial=fixture();wanted=Oracle(self.retail,initial).run().observations
        for name,body in controls().items():
            obj,_=candidate.compile_owner(ROOT,self.out,candidate.source_with(body),'negative-'+name)
            linked,fs=candidate.link_owner(ROOT,self.out,obj,candidate.OWNER);f=fs[match.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),linked,f['value']))
            self.assertNotEqual(Oracle(words,initial).run().observations,wanted,name)
        self.receipt('compiled-controls',dict(effective_IDO_controls=8))
    def test_09_literal_image_alignment_and_actual_padder_controls(self):
        from unittest.mock import patch
        before=self.prepared['predecessor_elf'].read_bytes();after=self.prepared['qualified_elf'].read_bytes();truth=self.rom[match.ROM:match.ROM+264]
        self.assertEqual(match.strict_image(before,after,truth),360)
        self.assertEqual(self.rom[match.ROM+264:match.ROM+272],bytes(8))
        at=match.elf_slot_offset(after,match.ENTRY,272);self.assertEqual(after[at+264:at+272],bytes(8))
        offsets=(0,*[row[0]for row in match.SYMBOL_GROUPS],0x2EC4C5,at+264,len(after)-1)
        for offset in offsets:
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)
        rows=self.prepared['qualified_rows'];fields=self.prepared['fields'];checked=0
        for index,row in enumerate(rows):
            if row['function']!=match.FUNCTION:continue
            bad=[dict(r)for r in rows];bad[index]['expected']='0x00000000'
            with patch.multiple(match.harness,FILENAME=match.FILENAME,ASM=match.ASM):
                with self.assertRaises(ValueError):match.harness.assemble_owner(ROOT,self.out,self.prepared['qualified_compact'],bad,fields,'bad-owner')
            checked+=1
        self.assertEqual(checked,16);self.receipt('strict-controls',dict(whole_image_corruptions=len(offsets),padder_preimages=16,alignment_words=2,named_symbol_serialization_bytes=147,exclusions=0))

if __name__=='__main__':unittest.main()
