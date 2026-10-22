"""Captured byte-state, post-RNG counter reads and the retained 64-bit RNG."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_randomized_byte_state as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_random_selector_outputs_match import RandomOutputsOracle,next_seed,SEEDS
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_command_stream_relocator import StopCode,WindowEnd
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
SLOT,RNG,SEED=0x800D154C,0x150ADA20,0x800885B0
ACTORS=(0x20000,0x21000);ROWS=(0x28000,0x29000)
WORDS=(0,1,2,3,4,7,0x80000000,0xFFFFFFFF)
COUNTERS=(0,2,3,7,8,9,10,11,255)


@dataclass(frozen=True)
class Case:
    state:int=1
    counter:int=3
    random:int=0xFFFFFFFF
    mode:int=0
    alias:object=None
    seed:int=0x123456789ABCDEF0


def row(c):return ROWS[0]if c.alias is None else SEED+c.alias-0x64


def fixture(c,phase=0,slot=SLOT):
    m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x500,0x200)}
    for base,n in((ACTORS[0]+0x314,24),(ACTORS[1]+0x314,24),(row(c)-16,160),(ROWS[1]-16,160),(slot-8,20),(SEED-8,24)):
        for i in range(n):m.setdefault(base+i,(i*13+37)&255)
    put(m,slot,ACTORS[0]);put(m,ACTORS[0]+0x31C,row(c));put(m,ACTORS[1]+0x31C,ROWS[1])
    m[row(c)+0x64]=c.state;m[row(c)+0x65]=c.counter;put(m,SEED,c.seed,8)
    return m


def public(m):return {a:v for a,v in m.items()if not STACK-0x500<=a<STACK+0x208}


def mutation(m,c,slot):
    if c.mode&1:put(m,slot,ACTORS[1])
    if c.mode&2:put(m,ACTORS[0]+0x31C,ROWS[1])
    if c.mode&4:m[row(c)+0x64]=0xA7
    if c.mode&8:m[row(c)+0x65]^=255


def reference(c,phase=0,slot=SLOT,rng=RNG,memory=None,real=False):
    m=dict(fixture(c,phase,slot)if memory is None else memory);state=read(m,read(m,slot)+0x31C)+0x58
    original=m[state+12];calls=[]
    if original==0:m[state+12]=1;m[state+13]=0
    else:
        calls.append((rng,()))
        if real:
            seed=next_seed(read(m,SEED,8));put(m,SEED,seed,8);value=seed&0xFFFFFFFF
        else:mutation(m,c,slot);value=c.random
        threshold=3 if original==1 else(value&3)+8
        if m[state+13]>=threshold:m[state+12]=2 if original==1 else 1;m[state+13]=0
    return m,calls


class StateOracle(RandomOutputsOracle,TimingOracle):
    def __init__(self,words,c=Case(),phase=0,slot=SLOT,rng=RNG,entry=source.ENTRY,connected=None,memory=None):
        self.state_case=c;self.slot=slot;self.rng=rng;self.visits=set()
        TimingOracle.__init__(self,words,fixture(c,phase,slot)if memory is None else memory,phase=phase,entry=entry,arguments=(),connected=connected)
    def record_call(self,target):
        assert target in(source.ENTRY,self.rng),hex(target)
        self.calls.append((target,()));self.events.append(('CALL',target,()))
    def hook(self,target):
        assert target==self.rng
        mutation(self.memory,self.state_case,self.slot)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678
        value=self.state_case.random&0xFFFFFFFF;self.r[2]=value|(0xFFFFFFFF00000000 if value&0x80000000 else 0)


def corpus():
    for state,count,residue in itertools.product(range(256),COUNTERS,range(4)):
        yield Case(state,count,(WORDS[(state+count)%8]&0xFFFFFFFC)|residue,(state+count+residue)%16)


def controls():
    b=source.SELECTED
    return dict(selected=b,
        wrongInitial=b.replace('state[0xC] = 1;','state[0xC] = 3;',1),
        wrongClear=b.replace('state[0xD] = 0;','state[0xD] = 1;'),
        wrongNext=b.replace('state[0xC] = 2;','state[0xC] = 1;'),
        strictThree=b.replace('state[0xD] >= 3','state[0xD] > 3'),
        strictRandom=b.replace('state[0xD] >= threshold','state[0xD] > threshold'),
        wideMask=b.replace('& 3','& 7'),signedRemainder=b.replace('& 3','% 4'),
        omitStateOneRng=b.replace('        func_150ADA20();','',1),
        omitOtherRng=b.replace('(func_150ADA20() & 3) + 8','8'),
        cachedCounter=b.replace('    s32 threshold;','    s32 threshold;\n    u8 cached = state[0xD];').replace('state[0xD] >=','cached >='),
        recheckState=b.replace('state[0xD] >= 3','state[0xC] == 1 && state[0xD] >= 3'),
        recapture=b.replace('        func_150ADA20();','        func_150ADA20();\n        state = *(u8 **)(D_800D154C + 0x31C) + 0x58;',1).replace('        threshold = (func_150ADA20() & 3) + 8;','        threshold = (func_150ADA20() & 3) + 8;\n        state = *(u8 **)(D_800D154C + 0x31C) + 0x58;'))


def native_harness():
    bodies=[];checks=[]
    for label,body in controls().items():
        bodies.append(body.replace(source.FUNCTION,label))
        checks.append(('if(variant(%s)!=0)return 30;'if label=='selected'else'if(variant(%s)!=23)return 31;')%label)
    return """typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
typedef void(*Callback)(void);typedef struct{u8 header[0x31C];u8*nested;}Player;
typedef char player_size[sizeof(Player)==0x320?1:-1];
typedef char player_field[__builtin_offsetof(Player,nested)==0x31C?1:-1];
static struct{u32 left[4];Player player;u32 right[4];}actors[2];
static struct{u32 left[4];u8 bytes[128];u32 right[4];}blocks[2];
static u8 expected[2][128];u8*D_800D154C;static u32 calls,mode,rng;
__attribute__((noinline,noclone)) s32 func_150ADA20(void){
 calls++;if(mode&1)D_800D154C=(u8*)&actors[1].player;
 if(mode&2)actors[0].player.nested=blocks[1].bytes;
 if(mode&4)blocks[0].bytes[0x64]=0xA7;
 if(mode&8)blocks[0].bytes[0x65]^=255;
 return(s32)rng;
}
""" + '\n'.join(bodies) + """
static int one(Callback fn,u32 state,u32 count,u32 value,u32 change){
 u32 i,j,wantedCalls=state!=0,threshold;calls=0;mode=change;rng=value;
 for(j=0;j<2;j++){
  for(i=0;i<128;i++)blocks[j].bytes[i]=expected[j][i]=(u8)(i*13+j*29+37);
  for(i=0;i<4;i++){actors[j].left[i]=blocks[j].left[i]=0xA5A50000+j*16+i;actors[j].right[i]=blocks[j].right[i]=0x5A5A0000+j*16+i;}
  actors[j].player.nested=blocks[j].bytes;
 }
 D_800D154C=(u8*)&actors[0].player;
 blocks[0].bytes[0x64]=expected[0][0x64]=(u8)state;blocks[0].bytes[0x65]=expected[0][0x65]=(u8)count;
 if(!state){expected[0][0x64]=1;expected[0][0x65]=0;}
 else{
  if(change&4)expected[0][0x64]=0xA7;if(change&8)expected[0][0x65]^=255;
  threshold=state==1?3:(value&3)+8;
  if(expected[0][0x65]>=threshold){expected[0][0x64]=(u8)(state==1?2:1);expected[0][0x65]=0;}
 }
 fn();
 if(calls!=wantedCalls||D_800D154C!=(u8*)&actors[state!=0&&(change&1)?1:0].player
   ||actors[0].player.nested!=blocks[state!=0&&(change&2)?1:0].bytes||actors[1].player.nested!=blocks[1].bytes)return 23;
 for(j=0;j<2;j++){
  for(i=0;i<128;i++)if(blocks[j].bytes[i]!=expected[j][i])return 23;
  for(i=0;i<4;i++)if(actors[j].left[i]!=0xA5A50000+j*16+i||blocks[j].left[i]!=0xA5A50000+j*16+i
   ||actors[j].right[i]!=0x5A5A0000+j*16+i||blocks[j].right[i]!=0x5A5A0000+j*16+i)return 23;
 }return 0;
}
static int variant(Callback fn){
 const u32 words[]={0,1,2,3,4,7,0x80000000,0xFFFFFFFF},states[]={0,1,2,255};
 u32 s,c,m,r,n=0;
 for(s=0;s<256;s++)for(c=0;c<256;c++)for(m=0;m<2;m++){if(one(fn,s,c,words[(s+c)%8],m?15:0))return 23;n++;}
 for(s=0;s<4;s++)for(c=0;c<16;c++)for(m=0;m<16;m++)for(r=0;r<8;r++){if(one(fn,states[s],c,words[r],m))return 23;n++;}
 return n==139264?0:24;
}
static int run(void){
""" + '\n'.join(checks) + """
 return 0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
"""


class RandomizedByteStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        data,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER);cls.rom=cls.values['conker/conker.us.bin']
        cls.words=list(struct.unpack_from('>43I',data,fs[source.FUNCTION]['value']));cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM));cls.receipt=dict(installed=cls.installed)
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def compare(self,c,phase=0,images=None,slot=SLOT,rng=RNG,entry=source.ENTRY,connected=None,real=False):
        expected,calls=reference(c,phase,slot,rng,real=real);models=[]
        for words in images or(self.truth,self.words):
            m=StateOracle(words,c,phase,slot,rng,entry,connected).run()
            self.assertEqual((public(m.memory),m.calls),(public(expected),calls));models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]));return models
    def test_01_direct_words_owner_Make_and_effective_stub(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(source.payload(self.obj),source.payload(source.original(ROOT,self.out)))
        q=json.loads((self.out/'qualification.json').read_text());m=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['relocations'],q['preserved_neighbors']),(43,32,4,15));self.assertEqual(m['actual_Make_commands'],3)
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.ENTRY,172)
        stale=StateOracle(struct.unpack_from('>43I',old,at),Case(state=0)).run();self.assertFalse(stale.calls)
        self.assertNotEqual(public(stale.memory),public(self.compare(Case(state=0))[0].memory))
        self.receipt.update(words=43,frame=32,bindings=4,neighbors=15,new_guards=0,compiler_only=True,old_stub_rejected=True,actual_Make_commands=3)
    def test_02_all_state_bytes_counter_boundaries_effects_and_saved_pointer(self):
        phases=0;visits=set()
        for c,phase in itertools.product(corpus(),(0,8)):
            m=self.compare(c,phase)[0];visits.update(m.visits);phases+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+172,4)))
        self.receipt.update(guest_phases=phases,all43_words_visited=True,captured_player_and_attachment_preserved=True,late_counter_and_original_branch=True)
    def test_03_native32_three_optimizations_and_twelve_defined_wrong_C(self):
        body=native_harness()
        for opt in('-O0','-O2','-O3'):
            p=self.out/('native'+opt);c=p.with_suffix('.c');c.write_text(body)
            q=subprocess.run([*native_command(opt),str(c),'-o',str(p)],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native'+opt+'-diagnostics.txt')).write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr)
            result=subprocess.run([str(p)],capture_output=True);self.assertEqual(result.returncode,0,result.stderr)
        self.receipt.update(native_cases_per_optimization=139264,native_optimizations=['O0','O2','O3'],defined_wrong_C_controls=12,trap_UBSan=True,typed_player_offset_and_full_row_fences=True)
    def linked(self,obj,entry,slot,rng,label):
        data,fs,rs=source.parse_object(obj);asm,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,dict(D_800D154C=slot,func_150ADA20=rng));self.assertFalse(unknown)
        p=self.out/label;a=p.with_suffix('.s');o=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        a.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(o),str(a)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,'--defsym=D_800D154C=0x%X'%slot,'--defsym=func_150ADA20=0x%X'%rng,'-o',str(elf),str(o)],capture_output=True,check=True)
        return struct.unpack_from('>43I',sections(elf)['.text'][1])
    def test_04_independent_rebases_and_fired_root_access_prefixes(self):
        phases=cuts=0
        for i,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            slot=(SLOT,0x80348000,0x80457FFC)[i];rng=RNG+i*0x10004
            images=[self.linked(obj,entry,slot,rng,'rebase-%d-%d'%(i,j))for j,obj in enumerate((source.original(ROOT,self.out),self.obj,self.out/'qualified-padded.o'))]
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for state,mode,phase in itertools.product((0,1,255),(0,15),(0,8)):
                self.compare(Case(state,9,mode=mode),phase,images[:2],slot,rng,entry);phases+=1
        for c,phase in itertools.product((Case(0),Case(1,2),Case(1,3,mode=15),Case(2,8),Case(255,255,mode=8)),(0,8)):
            good=StateOracle(self.truth,c,phase).run()
            for cut in range(good.root_accesses):
                models=[StateOracle(w,c,phase)for w in(self.truth,self.words)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=9,rebase_phases=phases,fired_root_access_prefixes=cuts,portable_C_fault_claimed=False)
    def test_05_actual_caller_window_and_unchanged_parent_stub(self):
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF));ptr=struct.pack('>I',source.ENTRY)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0xAC638])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[])
        window=struct.unpack_from('>5I',self.rom,0xAC638);count=0
        for state,mode,phase in itertools.product((0,1,2,255),(0,15),(0,8)):
            c=Case(state,9,mode=mode);initial=fixture(c,phase);expected,calls=reference(c,phase,memory=initial);models=[]
            for w in(self.truth,self.words):
                m=StateOracle(window,c,phase,entry=0x1507F188,connected={source.ENTRY+i*4:v for i,v in enumerate(w)},memory=initial)
                m.r[29]-=0x98;m.code=StopCode(m.code,m,0x1507F198)
                with self.assertRaises(WindowEnd):m.run()
                self.assertEqual((public(m.memory),m.calls),(public(expected),[(source.ENTRY,())]+calls))
                self.assertEqual(m.r[4],read(expected,SLOT));models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,0x1507EFD0,12)
        self.assertEqual(struct.unpack_from('>3I',old,at),(0x00001025,0x03E00008,0))
        self.receipt.update(actual_caller_window_phases=count,actual_caller_words=4,parent_stub_bytes=12,full_parent_execution_claimed=False)
    def test_06_original_current_64bit_rng_and_guest_seed_aliases(self):
        helper=self.rom[0xDAED0:0xDAED0+72];old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,RNG,72)
        self.assertEqual(old[at:at+72],helper);connected={RNG+i*4:w for i,w in enumerate(struct.unpack('>18I',helper))}
        count=aliases=0;visits=set()
        for state,counter,seed,phase in itertools.product((0,1,2,255),COUNTERS,SEEDS,(0,8)):
            m=self.compare(Case(state,counter,seed=seed),phase,connected=connected,real=True)[0];count+=1;visits.update(m.visits)
        for alias,seed,phase in itertools.product(range(8),SEEDS,(0,8)):
            self.compare(Case(alias=alias,seed=seed),phase,connected=connected,real=True);aliases+=1
        self.assertTrue(set(connected)<=visits)
        self.receipt.update(actual_rng_phases=count,guest_seed_alias_phases=aliases,retained_rng_words=18,all_rng_words_visited=True,portable_native_seed_alias_or_rng_recovery_claimed=False)
    def test_07_explicit_counter_sequence_and_local_order_fit(self):
        c=Case(state=1,counter=0,mode=15);m=self.compare(c)[0]
        self.assertEqual((m.memory[ROWS[0]+0x64],m.memory[ROWS[0]+0x65]),(2,0))
        self.assertEqual(read(m.memory,SLOT),ACTORS[1]);self.assertEqual(read(m.memory,ACTORS[0]+0x31C),ROWS[1])
        self.assertIn('threshold = (func_150ADA20() & 3) + 8;',source.SELECTED)
        self.assertLess(source.SELECTED.index('u8 *state'),source.SELECTED.index('s32 threshold'))
        self.receipt.update(explicit_rng_before_counter=True,natural_local_order_retains_SP1C=True,no_dummy_padding_or_guards=True)
    def test_08_history_strict_image_and_guard_identity(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+172];pred=source.predicted_image(before,truth)
        source.check_image(before,pred,truth);at=source.elf_slot_offset(before,source.ENTRY,172)
        for pos in(0,at-1,at,at+168,at+172,len(before)-1):
            wrong=bytearray(pred);wrong[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        with self.assertRaises(ValueError):source.check_image(before,pred[:-1],truth)
        for name,wanted in source.INPUTS.items():
            old=self.values[name];self.assertEqual(source.digest(old),wanted)
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else pred if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name)
        self.receipt.update(pinned_inputs=len(source.INPUTS),strict_image_negatives=7,guard_manifest_unchanged=True)
