"""Direct actor/camera forwarding: homes, truncation, original callees and callers."""
from dataclasses import dataclass,replace
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest
from tools.experiments import game_actor_camera_position_candidates as candidate
from tools.experiments import game_actor_camera_position_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_frame_timing_oracle import TimingOracle,STACK
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests import test_game_envelope_gates_match as windows

ROOT=candidate.ROOT
ACTOR,CAMERA,BASE,ACTORS=0x30000,0x60000,0x800DBFF0,0x800CC2D0
LOOKUP,FIRST,SECOND=0x1505EEF4,0x15022190,0x150221E8
POINTS=(0,0x80000000,bits(.75),bits(-.75),bits(32767.75),bits(32768.75),bits(-32769.75),
        bits(65535.75),bits(65536.75),bits(-65536.75),bits(2147483520.),bits(-2147483648.))
HEADINGS=(bits(0.),bits(-0.),bits(-180.),bits(180.),bits(.125),bits(-360.5),bits(1e20),bits(-1e20))
u32=lambda n:n&0xFFFFFFFF
def narrow(n):return u32(((n&65535)^32768)-32768)
def integer(word):
    value=floating(word)
    return math.trunc(value)&0xFFFFFFFF if math.isfinite(value)and -(2**31)<=value<2**31 else 0x80000000

@dataclass(frozen=True)
class Case:
    key:int=0xA5A520A5
    alternate:int=0
    flags:int=0
    point:int=0
    heading:int=0
    null:bool=False
    mutation:int=0
    phase:int=0
    actor:int=ACTOR

def symbols(base=BASE):return dict(D_800DBFF0=base,func_1505EEF4=LOOKUP,func_15022190=FIRST,func_150221E8=SECOND)
def fixture(c=Case(),s=None):
    s=s or symbols();m={STACK+i:(i*17+165)&255 for i in range(-1024,1024)}
    for a,n in((c.actor,0x32C),(CAMERA,0x800),(s['D_800DBFF0'],4),(0x800C3500,0x180)):
        m.update({a+i:(i*13+91)&255 for i in range(n)})
    put(m,s['D_800DBFF0'],CAMERA);put(m,CAMERA+0x2C,c.flags)
    put(m,CAMERA+0x37C,HEADINGS[c.heading%8]);put(m,CAMERA+0x760,HEADINGS[(c.heading+3)%8])
    for i in range(3):put(m,c.actor+0x14+i*4,POINTS[(c.point+i)%len(POINTS)])
    return m

def mutation(m,c,home,s):
    if c.mutation==1:
        put(m,CAMERA+0x2C,read(m,CAMERA+0x2C)^0x100)
        for i in range(3):put(m,c.actor+0x14+i*4,POINTS[(c.point+i+4)%len(POINTS)])
    elif c.mutation==2:put(m,home+4,0 if c.alternate else 0x80000000)
    elif c.mutation==3:put(m,s['D_800DBFF0'],CAMERA+0x100);put(m,CAMERA+0x100+0x2C,0);put(m,CAMERA+0x100+0x37C,bits(27.5))

def reference(initial,c,ra,s=None,home=None,connected=False):
    s=s or symbols();home=STACK+c.phase if home is None else home;m=dict(initial)
    put(m,home-4,ra);put(m,home+4,c.alternate);calls=[(s['func_1505EEF4'],(c.key&4095,))]
    if not connected:mutation(m,c,home,s)
    if not c.null:
        camera=read(m,s['D_800DBFF0']);flag=read(m,camera+0x2C)
        heading=read(m,camera+(0x760 if flag&256 else 0x37C))
        coords=tuple(narrow(integer(read(m,c.actor+0x14+4*i)))for i in range(3))
        angle=bits(floating(heading)+180.)
        alternate=read(m,home+4);target=s['func_150221E8']if alternate else s['func_15022190']
        calls.append((target,(*coords,angle)))
        for i,v in enumerate(coords):put(m,home-24+i*4,v)
        dest=0x800C3598 if alternate else 0x800C358C
        for i,v in enumerate(coords):put(m,dest+i*2,v,2)
        put(m,dest+8,angle)
        if not alternate:m[0x800C3663]=1
    return m,calls

class Oracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),entry=match.ENTRY,s=None,connected=None):
        self.case,self.syms=c,s or symbols()
        super().__init__(words,memory,phase=c.phase,entry=entry,arguments=(c.key,c.alternate),connected=connected)
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,True
        self.home=STACK+c.phase
    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==13:
            self.f[word>>6&31]=integer(self.f[word>>11&31])
        else:super().execute(word)
    def record_call(self,target):
        s=self.syms
        count=2 if target==match.ENTRY else 1 if target==s['func_1505EEF4'] else 4
        if target not in(match.ENTRY,s['func_1505EEF4'],s['func_15022190'],s['func_150221E8']):raise AssertionError(('unbounded camera helper',hex(target)))
        args=self.arguments(count);self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==match.ENTRY:self.home=self.r[29]
    def hook(self,target):
        c,s=self.case,self.syms;args=self.calls[-1][1]
        if target==s['func_1505EEF4']:
            mutation(self.memory,c,self.home,s);value=0 if c.null else c.actor
        else:
            alt=target==s['func_150221E8'];dest=0x800C3598 if alt else 0x800C358C
            for i,v in enumerate(args[:3]):self.put(self.r[29]+4*i,v,4);self.put(dest+2*i,v,2)
            self.put(dest+8,args[3],4)
            if not alt:self.put(0x800C3663,1,1)
            value=0xDEADBEEF
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=value

def helper_code(rom):
    code={}
    for entry,offset,words in((LOOKUP,0x8C3A4,55),(FIRST,0x4F640,22),(SECOND,0x4F698,19)):
        code.update(zip(range(entry,entry+4*words,4),struct.unpack_from('>%dI'%words,rom,offset)))
    return code

def controls():
    b=candidate.SELECTED
    return {'wrong-key-mask':b.replace('key & 0xFFF','key & 0xFF'),
        'wrong-mode':b.replace('if (alternate)','if (!alternate)'),
        'wrong-camera-flag':b.replace('& 0x100','& 0x80'),
        'wrong-camera-field':b.replace('+ 0x760','+ 0x764'),
        'wrong-angle':b.replace('+ 180.0f','+ 90.0f'),
        'wrong-axis':b.replace('(s32)actor->z_position','(s32)actor->x_position')}

class GameActorCameraPositionMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT)
        cls.rom=(ROOT/match.ROM_IMAGE).read_bytes();cls.retail=list(struct.unpack_from('>66I',cls.rom,match.ROM))
        linked,functions=candidate.link_owner(ROOT,cls.out,cls.prepared['qualified_compact'],candidate.OWNER)
        cls.words=list(struct.unpack_from('>66I',linked,functions[match.FUNCTION]['value']))
    def receipt(self,name,value):(self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    def compare(self,c,initial=None,images=None,entry=match.ENTRY,s=None,connected=None,allow_redirect=False):
        initial=fixture(c,s)if initial is None else initial
        models=[];outcomes=[]
        for w in images or(self.retail,self.words):
            model=Oracle(w,initial,c,entry,s,connected)
            outcome=None
            try:model.run()
            except AssertionError as exc:
                if not allow_redirect or not exc.args or not isinstance(exc.args[0],tuple):raise
                outcome=exc.args[0]
                if outcome[0]=='unowned jump':
                    self.assertNotEqual(model.r[31],model.before[31])
                    self.assertEqual(outcome[1],read(model.memory,STACK+c.phase-4))
                elif outcome[0]!='unmapped read':raise
            models.append(model);outcomes.append(outcome)
        self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(complete(models[0]),complete(models[1]))
        if outcomes[0]and outcomes[0][0]=='unmapped read':
            # A pointer/coordinate alias may redirect the camera read outside
            # mapped guest memory. Compare the fired partial state and require
            # the independent reference to encounter the same missing byte.
            with self.assertRaises(KeyError)as error:reference(initial,c,models[0].before[31],s)
            self.assertTrue(outcomes[0][1]<=error.exception.args[0]<outcomes[0][1]+outcomes[0][2])
            return models
        expected,calls=reference(initial,c,models[0].before[31],s,connected=bool(connected))
        for model in models:
            self.assertEqual(model.memory,expected,c);self.assertEqual(model.calls,calls,c)
            self.assertEqual(model.r[29],STACK+c.phase)
        self.assertEqual(complete(models[0]),complete(models[1]));return models
    def test_01_direct_body_complete_slot_bindings_and_literal_image(self):
        self.assertEqual(self.words,self.retail);r=self.prepared['report']
        self.assertEqual((r['words'],r['slot_words'],r['frame'],r['guards'],r['neighbors'],r['relocations']),(66,69,24,0,2,5))
        raw,bindings=match.function_blob(self.prepared['qualified_compact'])
        self.assertEqual(bindings,match.BINDINGS)
        before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
        for at in(0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,match.SLOT_SIZE)+match.SIZE):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),match.original_bytes(ROOT))
        self.assertEqual(r['strict_changed_bytes'],202)
    def test_02_key_mode_float_boundaries_and_postlookup_mutations(self):
        count=0;visits=set()
        for key,alt,flag,point,phase,mode in itertools.product((0,0xA5A520A5,0xFFFFF123),
                (0,1,0x80000000),(0,0x100,0xFFFFFF7F),range(len(POINTS)),(0,8),range(4)):
            c=Case(key,alt,flag,point,point%8,False,mode,phase)
            models=self.compare(c);visits.update(models[0].visits);count+=1
        for key in range(4096):self.compare(Case(key=0xF0000000|key,null=True));count+=1
        # Both duplicate LWC1 words follow unconditional branches; their live
        # equivalents are branch-likely delay slots at +0x38 and +0x4C.
        unreachable={match.ENTRY+0x44,match.ENTRY+0xA8}
        self.assertEqual(visits,set(range(match.ENTRY,match.ENTRY+match.SIZE,4))-unreachable)
        self.receipt('guest-contract',dict(cases_per_body=count,body_words_visited=len(visits),unreachable_shadow_words=list(map(hex,sorted(unreachable))),all_12bit_keys=True,
            floats_within_signed32_domain=True,finite_coordinates_beyond_signed16=True,full_mode_words=True))
    def test_03_incoming_homes_stack_aliases_and_null_short_circuit(self):
        count=0
        for actor,alt,flag,point,mode,phase in itertools.product((STACK+4-0x14,STACK-4-0x14,STACK-24-0x14,BASE-0x14,CAMERA+0x2C-0x14),
                (0,1),(0,256),(0,4,7),range(3),(0,8)):
            self.compare(Case(alternate=alt,flags=flag,point=point,mutation=mode,phase=phase,actor=actor),allow_redirect=True);count+=1
        c=Case(null=True);initial=fixture(c)
        for a in list(initial):
            if CAMERA<=a<CAMERA+0x800 or BASE<=a<BASE+4 or ACTOR<=a<ACTOR+0x32C:del initial[a]
        self.compare(c,initial);self.receipt('aliases',dict(cases_per_body=count,null_needs_no_camera_or_actor_mapping=True))
    def test_04_connected_original_lookup_and_both_output_helpers(self):
        count=0;visits=set();code=helper_code(self.rom)
        for slot,alt,flag,phase in itertools.product(range(-1,26),(0,1),(0,256),(0,8)):
            # Slot 25 remains reserved; all 25 eligible actor slots are exercised.
            c=Case(key=0xF00000A5,alternate=alt,flags=flag,phase=phase,null=slot in(-1,25),actor=ACTORS+max(slot,0)*0x32C)
            initial=fixture(c)
            for i in range(26):put(initial,ACTORS+i*0x32C,1);initial[ACTORS+i*0x32C+0x13F]=0xA5 if i==slot else 0x5A
            models=self.compare(c,initial,connected=code);visits.update(models[0].visits);count+=1
        self.receipt('connected',dict(cases_per_body=count,lookup_eligible_slots=25,reserved_slot25_excluded=True,
            connected_word_count=len(code),connected_visited=len(visits-set(range(match.ENTRY,match.ENTRY+match.SIZE,4)))))
    def test_05_both_authentic_caller_windows(self):
        counts=[0,0]
        for which,opcode,null,flag,phase in itertools.product(range(2),(0,1,2,3,15),(False,True),(0,256),(0,8)):
            entry,body_end,end,offset=(0x1509C4E8,0x1509C514,0x1509C514,0xC9998)if which==0 else(0x1509C70C,0x1509C73C,0x1509C7B8,0xC9BBC)
            key=0xABCD0000|(opcode<<12)|0xA5;c=Case(key=key,alternate=which,flags=flag,null=null,phase=phase)
            initial=fixture(c);command=0x50000
            for i in range(32):initial[command+i]=165
            put(initial,command+8,key);put(initial,STACK+phase+0x3C,0x76543210)
            models=[];expected=None
            for words in(self.retail,self.words):
                connected={match.ENTRY+i*4:w for i,w in enumerate(words)}
                parent=list(struct.unpack_from('>%dI'%((body_end-entry)//4),self.rom,offset))
                model=Oracle(parent,initial,c,entry=entry,connected=connected);model.r[16]=command;model.r[5]=0x800C35C3
                model.code=windows.WindowCode(model.code,model,end)
                with self.assertRaises(windows.WindowBoundary):model.run()
                if expected is None:
                    expected=dict(initial)
                    if opcode==2:
                        # JAL return address is call PC + 8 in each original window.
                        expected,calls=reference(initial,c,0x1509C504 if which==0 else 0x1509C728)
                        calls=[(match.ENTRY,(key,which))]+calls
                    else:
                        calls=[]
                        if which==0:put(expected,STACK+phase+0x3C,key)
                        else:expected[0x800C35C3]=key&255
                self.assertEqual(model.memory,expected,(which,opcode));self.assertEqual(model.calls,calls)
                if which==0:self.assertEqual(model.r[4],read(expected,STACK+phase+0x3C))
                models.append(model)
            self.assertEqual(complete(models[0]),complete(models[1]));counts[which]+=1
        self.receipt('callers',dict(cases_per_body=counts,window_words=[11,12],parent_earlier_mode_gate_assumed=True,parent_not_credited=True))
    def test_06_literal_fault_prefixes(self):
        count=0
        for alt,flag,null,mode,phase in itertools.product((0,1),(0,256),(False,True),range(3),(0,8)):
            c=Case(alternate=alt,flags=flag,null=null,mutation=mode,phase=phase);initial=fixture(c)
            done=Oracle(self.retail,initial,c).run()
            for cut in range(done.root_accesses):
                models=[Oracle(w,initial,c)for w in(self.retail,self.words)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt('fault-prefixes',dict(fired_root_prefixes=count,complete_private_state_equal=True))
    def test_07_independent_GNU_rebases_and_bindings(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('CameraOriginal',(),dict(root=ROOT,out=self.out))
        original=ViewListSetupTests.original.__func__(context,'original-camera',(ROOT/match.ASM).read_text(),match.FUNCTION)
        count=links=0
        for index,(entry,base,delta)in enumerate(((match.ENTRY,BASE,0),(0x18017FFC,0x800A7FFC,0x03000000),(0x1A028000,0x800A8000,0x05000000))):
            s=symbols(base)
            for name in('func_1505EEF4','func_15022190','func_150221E8'):s[name]+=delta
            images=[]
            for ordinal,obj in enumerate((original,self.prepared['qualified_compact'])):
                text,functions,relocations=parse_object(obj)
                asm,unknown=emit_function(text,functions[match.FUNCTION],relocations,match.FUNCTION,s);self.assertFalse(unknown)
                path=self.out/('rebase-%d-%d'%(index,ordinal));path.with_suffix('.s').write_text(asm)
                path.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(path.with_suffix('.o')),str(path.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(path.with_suffix('.ld')),'-e',match.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in s.items()],'-o',str(path.with_suffix('.elf')),str(path.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>66I',sections(path.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1])
            for alt,flag,mode in itertools.product((0,1),(0,256),range(4)):
                self.compare(Case(alternate=alt,flags=flag,mutation=mode),images=images,entry=entry,s=s);count+=1
        self.receipt('rebases',dict(GNU_links=links,cases_per_body=count,HI_LO_carry_edges=True,all_three_call_targets_relocated=True))
    def test_08_native32_typed_calls_finite_domain_and_negative_controls(self):
        rows=[('positive-'+opt[1:],candidate.SELECTED,opt,0)for opt in('-O0','-O2','-O3')]
        rows.extend((name,body,'-O2',1)for name,body in controls().items())
        for label,body,opt,expected in rows:
            path=self.out/('native-'+label+'.c');binary=path.with_suffix('.elf');path.write_text(native_source(body))
            built=subprocess.run([*native_command(opt),'-fsanitize=float-cast-overflow','-mstackrealign',str(path),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            result=subprocess.run([str(binary)],capture_output=True,timeout=60)
            self.assertEqual(result.returncode,expected,(label,result.stderr))
        self.receipt('native-contract',dict(profiles=['O0','O2','O3'],direct_cases_per_profile=65536,typed_cases_per_profile=65536,
            controls=sorted(controls()),UBSan=True,float_cast_overflow_traps=True,
            only_finite_signed32_convertible_coordinates=True,actual_SDK_actor_and_camera_layouts=True))
    def test_09_actual_IDO_negative_controls(self):
        found={}
        for label in('wrong-key-mask','wrong-mode','wrong-camera-flag','wrong-camera-field','wrong-angle','wrong-axis'):
            obj,_=candidate.compile_owner(ROOT,self.out,candidate.source_with(controls()[label]),'negative-'+label)
            text,functions=candidate.link_owner(ROOT,self.out,obj,candidate.OWNER);f=functions[match.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),text,f['value']))
            witness=False
            for c in(Case(key=0xA5A521A5,point=3),Case(flags=256,point=5),Case(alternate=1,point=7)):
                initial=fixture(c);model=Oracle(words,initial,c).run()
                expected,calls=reference(initial,c,model.before[31])
                if model.memory!=expected or model.calls!=calls:witness=True;break
            self.assertTrue(witness,label);found[label]=True
        self.receipt('compiled-controls',found)

def native_source(body):
    return '#include <ultra64.h>\n'+candidate.DECLARATIONS+r'''
typedef void (*Handler)(s32,s32);
static struct127 actor;
static u8 *cameraStorage;
struct108 *D_800DBFF0;
static u32 keyWord,alternateWord,seed,expectedArgs[4];
static s32 absent,calls,error,mutate;
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 coordinates[]={0.f,-0.f,.75f,-.75f,32767.75f,32768.75f,-32769.75f,65535.75f,65536.75f,-65536.75f,2147483520.f,-2147483648.f};
static f32 headings[]={0.f,-0.f,-180.f,180.f,.125f,-360.5f,1e20f,-1e20f};
struct127 *func_1505EEF4(s32 key){
 if((u32)key!=(keyWord&4095u))error=1;calls++;
 if(mutate){D_800DBFF0->unk2C^=256;actor.x_position=coordinates[(seed+4)%12];actor.y_position=coordinates[(seed+5)%12];actor.z_position=coordinates[(seed+6)%12];}
 return absent?0:&actor;
}
static void output(s16 x,s16 y,s16 z,f32 angle,s32 alt){
 u32 actual[4]={(u32)(s32)x,(u32)(s32)y,(u32)(s32)z,word(angle)},i;
 calls++;if((alternateWord!=0)!=alt)error=1;
 for(i=0;i<4;i++)if(actual[i]!=expectedArgs[i])error=1;
}
void func_15022190(s16 x,s16 y,s16 z,f32 angle){output(x,y,z,angle,0);}
void func_150221E8(s16 x,s16 y,s16 z,f32 angle){output(x,y,z,angle,1);}
'''+body+r'''
__attribute__((noinline))static void invoke(Handler fn,s32 a,s32 b){fn(a,b);}
static s32 run(void){
 u32 args[6]={0,4096,3,0x22,0xFFFFFFFFu,0},address,n,indirect,i;f32 selected;
 if(sizeof(void*)!=4||__builtin_offsetof(struct127,x_position)!=0x14||__builtin_offsetof(struct127,z_position)!=0x1C||__builtin_offsetof(struct108,unk2C)!=0x2C||__builtin_offsetof(struct108,unk37C)!=0x37C)return 9;
 __asm__ volatile("int $0x80":"=a"(address):"a"(90),"b"(args):"memory");
 if(address>=0xFFFFF000u)return 10;cameraStorage=(u8*)address;D_800DBFF0=(struct108*)cameraStorage;
 for(n=0;n<65536;n++)for(indirect=0;indirect<2;indirect++){
  seed=n;error=calls=0;keyWord=0xA5000000u|n;alternateWord=(u32[]){0,1,0x80000000u,0xFFFFFFFFu}[n&3];
  absent=(n&15)==0;mutate=(n>>4)&1;
  D_800DBFF0->unk2C=(s32)(n*0x1234567u);D_800DBFF0->unk37C=headings[n&7];
  *(f32*)(cameraStorage+0x760)=headings[(n+3)&7];*(f32*)(cameraStorage+0x764)=27.5f;
  actor.x_position=coordinates[n%12];actor.y_position=coordinates[(n+1)%12];actor.z_position=coordinates[(n+2)%12];
  for(i=0;i<3;i++)expectedArgs[i]=(u32)(s32)(s16)(s32)coordinates[(n+i+(mutate?4:0))%12];
  selected=(((u32)D_800DBFF0->unk2C^(mutate?256u:0))&256u)?headings[(n+3)&7]:headings[n&7];
  expectedArgs[3]=word(selected+180.f);
  if(indirect)invoke(func_1509C8FC,(s32)keyWord,(s32)alternateWord);else func_1509C8FC((s32)keyWord,(s32)alternateWord);
  if(error||calls!=(absent?1:2))return 1;
 }
 return 0;
}
void _start(void){s32 result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''

if __name__=='__main__':unittest.main()
