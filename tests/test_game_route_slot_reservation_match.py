"""Slot reservation: signed bounds, mask wrap, actual reset and native32 backing."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_route_slot_reservation_candidates as source
from tools.experiments import game_route_slot_reservation_integration as integration
from tools.experiments.game_remaining_donor_candidates import body
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import test_game_route_record_copy_match as copy
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_projected_packet_draw import native_command

TABLE,MASK,BASE,COUNT,ACTORS,RESET=0x800872A0,0x800D2394,0x800D2398,0x800D2399,0x800CC2D0,0x15088824
ARENA,ALTERNATE=0x90000,0xA0000
PREFIX,RECORDS=128,288
CAPACITY=RECORDS*132
BANKS=(ARENA,ALTERNATE)
STACK,put,read=copy.STACK,copy.put,copy.read
HELPER_SHA='cbb3b53aeca2a5cd134b9e0e7da5d9a78e584c1901e93f7acf921ea2a5339363'
TYPED=((0,4),(4,4),(8,4),(12,4),(16,4),(20,4),(24,4),(28,4),(32,4),(36,2))


def signed8(value):return (value&255)-256 if value&128 else value&255


def choice(count,base,mask):
    bit=1
    for i in range(max(0,signed8(count))):
        if mask&bit==0:return i+signed8(base),bit
        bit=(bit<<1)&0xFFFFFFFF
    return None


def cases():
    for count in range(256):
        for mode in (0,1):yield (count,0,(0,1,0x80000000,0xFFFFFFFF)[count%4],count%26,mode,0,count&7)
    for base in range(256):
        for mode in (0,1):yield (1,base,0,base%26,mode,0,base&7)
    for free in range(33):
        for mode in (0,1):yield (free+1,0,(1<<free)-1,free%26,mode,0,3)
    for count in (0,1,2,16,31,32,33,127,128,255):
        for base in (0,127,128,255):
            for mask in (0,1,0x80000000,0xAAAAAAAA,0xFFFFFFFF):
                for mode in (0,1):yield (count,base,mask,25,mode,0,5)
    for actor in (0,1,25):
        for mode in (0,1):yield (127,128,0xFFFFFFFF,actor,mode,1,7)


def record_seed(memory,index,pattern):
    for bank,base in enumerate(BANKS):
        at=base+index*132
        memory.update({at+i:(((index+PREFIX)*132+i)*137+pattern*31+bank*53+19)&255 for i in range(-16,148)})


def fixture(case,phase=0,actor=None):
    count,base,mask,actor_slot,mode,null,pattern=case
    picked=None if null else choice(count,base,mask)
    index=picked[0] if picked else 0
    m={STACK+i:(i*17+0xA5)&255 for i in range(-0x300,0x100)}
    record_seed(m,index,pattern)
    m.update({TABLE+i:0xA5 for i in range(-16,20)})
    m.update({MASK+i:0xA5 for i in range(-4,20)})
    for a,v,n in ((TABLE,0 if null else ARENA,4),(MASK,mask,4),(BASE,base,1),(COUNT,count,1)):
        put(m,a,v,n)
    if mode==2 and picked:
        old=(TABLE-(index*132&0xFFFFFFFF)-0x30)&0xFFFFFFFF
        new=(old&0x00FFFFFF)|0x01000000
        address=(new+(index*132&0xFFFFFFFF))&0xFFFFFFFF
        m.update({address+i:0xA5 for i in range(0x40)})
    return m,((ACTORS+actor_slot*812)&0xFFFFFFFF if actor is None else actor&0xFFFFFFFF,)


def reset_reference(memory,record):
    for offset in (0x2B,0x2C,0x2D,0x2E,0x28,0x2F,0x26,0x27,0x31,0x30,0x49):put(memory,record+offset,0,1)
    for offset,value in ((0x1C,0),(0x18,0),(0x20,0xFFFFFFFF),(8,0),(0,0x3F000000),(4,0x3F000000),
                         (0xC,0),(0x14,0),(0x10,0x3F800000)):put(memory,record+offset,value,4)
    put(memory,record+0x24,0,2);put(memory,record+0x33,2,1);put(memory,record+0x2A,127,1)


def reference(memory,args,mode=0,phase=0):
    m=memory.copy();table=read(m,TABLE,4)
    if not table:return 0xFFFFFFFF,m,[],[]
    picked=choice(read(m,COUNT,1),read(m,BASE,1),read(m,MASK,4))
    if picked is None:return 0xFFFFFFFF,m,[],[]
    index,bit=picked;off=index*132&0xFFFFFFFF;record=(table+off)&0xFFFFFFFF
    put(m,MASK,read(m,MASK,4)|bit,4)
    capture=(record,read(m,MASK,4),read(m,COUNT,1),read(m,BASE,1))
    reset_reference(m,record)
    actor=args[0]
    if mode==1:
        put(m,TABLE,ALTERNATE,4);put(m,MASK,0x5A5A5A5A,4);put(m,COUNT,128,1);put(m,BASE,127,1)
    elif mode==2:put(m,TABLE,(TABLE-off-0x30)&0xFFFFFFFF,4)
    elif mode==3:
        actor=ACTORS+7*812;put(m,STACK+phase,actor,4)
    put(m,(read(m,TABLE,4)+off+0x30)&0xFFFFFFFF,1,1)
    delta=(actor-ACTORS)&0xFFFFFFFF;delta=delta if delta<0x80000000 else delta-0x100000000
    identity=(abs(delta)//812)*(-1 if delta<0 else 1)
    put(m,(read(m,TABLE,4)+off+0x31)&0xFFFFFFFF,identity,1)
    return index&0xFFFFFFFF,m,[(RESET,record)],[capture]


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x300<=a<STACK+0x100}


class SlotModel(copy.CopyModel):
    def __init__(self,words,memory,args,helper,phase=0,mode=0,entry=source.ENTRY):
        connected=dict(zip(range(RESET,RESET+len(helper)*4,4),helper)) if mode==0 else {}
        super().__init__(words,memory,args,connected,phase,mode,entry=entry)
        self.helper,self.captures=helper,[]

    def record_call(self,target):
        if target==source.ENTRY:
            self.caller_args.append((self.r[4],));return
        assert target==RESET,hex(target)
        record=self.r[4];self.calls.append((target,record));self.events.append(('CALL',target,(record,)))
        self.captures.append((record,read(self.memory,MASK,4),read(self.memory,COUNT,1),read(self.memory,BASE,1)))

    def hook(self,target):
        assert target==RESET
        self.in_hook=True
        try:
            # The frozen helper is straight-line up to its JR/NOP; execute its real data operations.
            for word in self.helper[:-2]:self.execute(word)
            if self.mode==1:
                for a,v,n in ((TABLE,ALTERNATE,4),(MASK,0x5A5A5A5A,4),(COUNT,128,1),(BASE,127,1)):
                    self.put(a,v,n)
            elif self.mode==2:
                off=self.peek(self.r[29]+0x18,4)
                self.put(TABLE,(TABLE-off-0x30)&0xFFFFFFFF,4)
            elif self.mode==3:self.put(self.r[29]+0x28,ACTORS+7*812,4)
            for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
            self.r[2]=0xDEADC0DE;self.f[:20]=[0xA5000000+i for i in range(20)]
        finally:self.in_hook=False


NATIVE=r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;
typedef unsigned int u32;typedef int s32;typedef float f32;
static u8 arena[2][288*132] __attribute__((aligned(16))),wanted[2][288*132] __attribute__((aligned(16)));
u8 D_800CC2D0[26*812] __attribute__((aligned(16)));
u8 *D_800872A0;s32 D_800D2394;s8 D_800D2398,D_800D2399;
static u32 mode,calls,expectedCalls,expectedMask,failure;static u8 *expectedRecord;
HELPER_BODY
void func_15088824(u8 *r) {
    calls++;if(!expectedCalls || r!=expectedRecord || (u32)D_800D2394!=expectedMask)failure=22;
    actual_reset(r);
    if(mode){D_800872A0=arena[1]+128*132;D_800D2394=0x5A5A5A5A;D_800D2399=(s8)128;D_800D2398=127;}
}
SOURCE_BODY
typedef struct {u32 input[7],result,calls,mask,count,base,maskAtCall,index,first,length;} Case;
static const u32 patches[]={PATCHES};static const Case cases[]={ROWS};
void _start(void) {
    u32 n,b,i,v,one=1;const Case *c;s32 result;
    if(sizeof(void*)!=4 || sizeof(f32)!=4 || *(u8 *)&one!=1)failure=29;
    for(n=0;!failure && n<sizeof(cases)/sizeof(cases[0]);n++) {
        c=cases+n;mode=c->input[4];calls=0;expectedCalls=c->calls;expectedMask=c->maskAtCall;
        expectedRecord=(u8 *)((u32)(arena[0]+128*132)+c->index*132U);
        for(b=0;b<2;b++)for(i=0;i<288*132;i++)arena[b][i]=wanted[b][i]=(u8)(i*137+c->input[6]*31+b*53+19);
        D_800872A0=c->input[5]?0:arena[0]+128*132;
        D_800D2394=c->input[2];D_800D2399=c->input[0];D_800D2398=c->input[1];
        for(i=0;i<c->length;i++){v=patches[c->first+i];wanted[v>>24][v>>8&65535]=(u8)v;}
        result=func_1508868C(D_800CC2D0+c->input[3]*812);
        if((u32)result!=c->result || calls!=c->calls)failure=23;
        if((u32)D_800D2394!=c->mask || (u8)D_800D2399!=c->count || (u8)D_800D2398!=c->base)failure=24;
        if(D_800872A0!=(c->input[5]?0:arena[mode&&c->calls]+128*132))failure=25;
        for(b=0;b<2;b++)for(i=0;i<288*132;i++)if(arena[b][i]!=wanted[b][i])failure=21;
    }
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''


class GameRouteSlotReservationMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out,'test-selected')
        rom=cls.values['conker/conker.us.bin'];cls.retail=list(struct.unpack_from('>61I',rom,source.ROM))
        cls.helper=list(struct.unpack_from('>33I',rom,0xB5CD4))
        image=cls.values['conker/build/conker.us.elf'];at=elf_slot_offset(image,RESET,132)
        if list(struct.unpack_from('>33I',image,at))!=cls.helper or cls.helper[-2:]!=[0x03E00008,0]:
            raise ValueError('Changed reset helper code or straight-line return')
        cls.helper_body=body(cls.values[source.SOURCE].decode(),'func_15088824')
        if hashlib.sha256(cls.helper_body.encode()).hexdigest()!=HELPER_SHA:raise ValueError('Changed reset C source')
        cls.cases=list(cases())

    def model(self,words,case,phase=0,memory=None,actor=None,entry=source.ENTRY):
        m,args=fixture(case,phase,actor)
        return SlotModel(words,m if memory is None else memory,args,self.helper,phase,case[4],entry)

    def test_direct_words_frame_bindings_and_initial_role_control(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(61,40,0,''))
        self.assertEqual(self.words,self.retail);integration.checked(self.obj)
        _,words,row=source.compile_candidate(self.root,self.out,'initial-control',source.INITIAL)
        self.assertEqual((row['words'],row['frame'],row['differences']),(61,40,5));self.assertNotEqual(words,self.retail)

    def test_signed_counts_bases_wrap_and_connected_reset(self):
        coverage=set();minus_one_success=False;wrapped=False
        for case in self.cases:
            for phase in (0,8):
                a=self.model(self.retail,case,phase).run();b=self.model(self.words,case,phase).run()
                m,args=fixture(case,phase);ret,wanted,calls,captures=reference(m,args,case[4],phase)
                self.assertEqual((a.r,a.f,a.lo,a.memory,a.events,a.calls,a.captures),
                    (b.r,b.f,b.lo,b.memory,b.events,b.calls,b.captures))
                self.assertEqual((a.r[2],public(a.memory),a.calls,a.captures),(ret,public(wanted),calls,captures))
                self.assertEqual(sum(e[0]=='R' and e[1]==COUNT for e in a.events),0 if case[5] else 1)
                self.assertEqual(sum(e[0]=='R' and e[1]==MASK for e in a.events),int(not case[5] and signed8(case[0])>0))
                self.assertEqual(sum(e[0]=='R' and e[1]==TABLE for e in a.events),3 if calls else 1)
                coverage.update(a.visits)
                minus_one_success |= ret==0xFFFFFFFF and bool(calls)
                wrapped |= bool(calls) and case[2]==0xFFFFFFFF
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+244,4))<=coverage)
        self.assertTrue(minus_one_success);self.assertTrue(wrapped)
        (self.out/'connected-cases.json').write_text(json.dumps(dict(cases=len(self.cases),phases=2,
            helper_words=33,all61_words_visited=True,negative_one_allocated_index_covered=True,unsigned_bit_wrap_covered=True))+'\n')

    def test_pointer_alias_private_home_and_real_helper_global_mutation(self):
        for mode in (2,3):
            case=(1,0,0,25,mode,0,3)
            for phase in (0,8):
                a=self.model(self.retail,case,phase).run();b=self.model(self.words,case,phase).run()
                m,args=fixture(case,phase);ret,wanted,calls,captures=reference(m,args,mode,phase)
                self.assertEqual((a.r,a.memory,a.events),(b.r,b.memory,b.events))
                self.assertEqual((a.r[2],public(a.memory),a.calls,a.captures),(ret,public(wanted),calls,captures))
        # A real reset writes through the allocation mask and the adjacent count/base bytes.
        case=(1,0,0,25,0,0,3);m,args=fixture(case);table=MASK-0x1C
        m.update({table+i:0xA5 for i in range(-16,148)})
        put(m,TABLE,table,4);put(m,MASK,0,4);put(m,COUNT,1,1);put(m,BASE,0,1)
        ret,wanted,calls,captures=reference(m,args)
        a=self.model(self.retail,case,memory=m).run();b=self.model(self.words,case,memory=m).run()
        self.assertEqual((a.r,a.memory,a.events),(b.r,b.memory,b.events))
        self.assertEqual((b.r[2],public(b.memory),b.calls,b.captures),(ret,public(wanted),calls,captures))
        self.assertEqual((read(b.memory,MASK,4),read(b.memory,COUNT,1),read(b.memory,BASE,1)),(0,255,255))

    def test_signed_full_word_actor_differences(self):
        pairs=0
        for delta in (-0x80000000,-26*812,-813,-812,-811,-1,0,1,811,812,813,0x7FFFFFFF):
            case=(1,0,0,0,0,0,3);actor=(ACTORS+delta)&0xFFFFFFFF
            a=self.model(self.retail,case,actor=actor).run();b=self.model(self.words,case,actor=actor).run()
            m,args=fixture(case,actor=actor);ret,wanted,calls,captures=reference(m,args)
            self.assertEqual((a.r,a.memory,a.events),(b.r,b.memory,b.events))
            self.assertEqual((b.r[2],public(b.memory),b.calls,b.captures),(ret,public(wanted),calls,captures));pairs+=1
        self.assertEqual(pairs,12)

    def test_fired_connected_access_fault_pairs(self):
        pairs=0
        selected=[(1,128,0,25,0,0,3),(32,127,0x7FFFFFFF,0,0,0,3),
            (33,255,0xFFFFFFFF,1,0,0,3),(32,0,0xFFFFFFFF,0,0,0,3),(128,0,0,0,0,0,3),
            (1,0,0,25,1,0,3),(1,0,0,25,2,0,3),(1,0,0,25,3,0,3),(127,0,0,0,0,1,3)]
        for case in selected:
            for phase in (0,8):
                done=self.model(self.retail,case,phase).run()
                for cut in range(done.accesses):
                    states=[]
                    for words in (self.retail,self.words):
                        model=self.model(words,case,phase);model.fault=cut
                        with self.assertRaises(copy.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut)
                        states.append((model.r,model.f,model.lo,model.memory,model.events,model.calls,model.captures))
                    self.assertEqual(*states);pairs+=1
        (self.out/'access-cuts.json').write_text(json.dumps(dict(fired_pairs=pairs,profiles=len(selected),phases=2,
            real_helper_accesses_included=True,provider_internal_accesses_excluded=True))+'\n')

    def test_native32_full_backing_actual_reset_c_and_endian_views(self):
        patches=[];rows=[]
        for case in self.cases:
            m,args=fixture(case);ret,wanted,calls,captures=reference(m,args,case[4])
            picked=None if case[5] else choice(case[0],case[1],case[2]);idx=picked[0] if picked else 0
            if calls:
                record=ARENA+idx*132
                for at,size in TYPED:
                    data=bytes(wanted[record+at+i] for i in range(size))
                    wanted.update({record+at+i:v for i,v in enumerate(data[::-1])})
            start=len(patches)
            for bank,base in enumerate(BANKS):
                for a,v in wanted.items():
                    if base-PREFIX*132<=a<base+(RECORDS-PREFIX)*132 and m.get(a)!=v:
                        patches.append((bank<<24)|((a-base+PREFIX*132)<<8)|v)
            fmt=lambda vs:','.join('0x%Xu'%(v&0xFFFFFFFF) for v in vs)
            observed=(ret,len(calls),read(wanted,MASK,4),read(wanted,COUNT,1),read(wanted,BASE,1),
                captures[0][1] if captures else 0,idx,start,len(patches)-start)
            rows.append('{{%s},%s}'%(fmt(case),fmt(observed)))
        helper=self.helper_body.replace('void func_15088824(','void actual_reset(')
        base=NATIVE.replace('HELPER_BODY',helper).replace('PATCHES',','.join('0x%Xu'%p for p in patches)).replace('ROWS',',\n'.join(rows))
        exits={}
        for name,opt,sanitize,unit,want in (('o0','-O0',False,source.SELECTED,0),('o2','-O2',False,source.SELECTED,0),
                ('ubsan','-O2',True,source.SELECTED,0),('negative-state','-O2',True,
                 source.SELECTED.replace('[0x30] = 1;','[0x30] = 2;'),21)):
            path=self.out/('native-'+name+'.c');path.write_text(base.replace('SOURCE_BODY',unit));exe=path.with_suffix('')
            command=[*native_command(opt,sanitize),'-mstackrealign','-fno-strict-aliasing',str(path),'-o',str(exe)]
            built=subprocess.run(command,cwd=self.root,capture_output=True,text=True)
            (self.out/('native-'+name+'-compile.json')).write_text(json.dumps(dict(command=command,
                exit=built.returncode,diagnostics=built.stdout+built.stderr),indent=2)+'\n')
            self.assertEqual((built.returncode,built.stdout,built.stderr),(0,'',''),name)
            run=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertEqual((run.returncode,run.stdout,run.stderr),(want,'',''),name);exits[name]=run.returncode
        (self.out/'native-cases.json').write_text(json.dumps(dict(cases=len(self.cases),bank_bytes=CAPACITY*2,
            expected_byte_patches=len(patches),all_bytes_compared=True,actual_reset_C=True,endian_typed_fields=TYPED,exits=exits))+'\n')

    def test_ordinary_executed_source_negative_controls(self):
        cached=source.SELECTED.replace('(u32)D_800872A0 +','(u32)table +')
        call='func_15088824((u8 *)((u32)recordIndex * 0x84 + (u32)table));'
        forms={
            'unsigned-count':source.SELECTED.replace('recordIndex < D_800D2399','recordIndex < (u8)D_800D2399'),
            'wrong-bit':source.SELECTED.replace('    bit = 1;','    bit = 2;'),
            'skip-mask':source.SELECTED.replace('            D_800D2394 |= bit;\n',''),
            'wrong-state':source.SELECTED.replace('[0x30] = 1;','[0x30] = 2;'),
            'cached-before':cached,
            'cached-after':cached.replace(call,call+'\n            table = D_800872A0;'),
        }
        for name,unit in forms.items():
            _,words,_=source.compile_candidate(self.root,self.out,'negative-'+name,unit)
            mode=1 if name=='cached-before' else 2 if name=='cached-after' else 0
            case=(128 if name=='unsigned-count' else 1,0,0,25,mode,0,3)
            a=self.model(self.retail,case).run();b=self.model(words,case).run()
            self.assertNotEqual((a.r[2],public(a.memory),a.calls,a.captures),(b.r[2],public(b.memory),b.calls,b.captures),name)

    def test_actual_caller_window_consumes_index_and_gates_negative_one(self):
        entry=0x150D78D8;rom=self.values['conker/conker.us.bin']
        # Four real words pass the actor and save the other index, then a small driver stops.
        window=list(struct.unpack_from('>4I',rom,0x104D88))+[0x02E00008,0]
        self.assertEqual(window[:3],[0x00A02025,0x0D4221A3,0xAFA20048])
        count=0
        for phase in (0,8):
            for case in ((1,0,0,25,0,0,3),(32,0,0xFFFFFFFF,0,0,0,3),(1,255,0,1,1,0,3),(1,0,0,0,0,1,3)):
                memory,args=fixture(case,phase);ret,_,_,_=reference(memory,args,case[4],phase);states=[]
                for words in (self.retail,self.words):
                    model=SlotModel(window,memory,(0xA5000004,args[0]),self.helper,phase,case[4],entry)
                    model.r[2]=7;model.r[23]=model.before[23]=0xDEAD0000;model.before[31]=entry+12
                    model.code.update(zip(range(source.ENTRY,source.ENTRY+244,4),words))
                    # The fourth real instruction is only AT=-1; the caller's following gate is checked statically.
                    model.run();self.assertEqual(model.caller_args,[(args[0],)])
                    self.assertEqual(model.r[2],ret);self.assertEqual(read(model.memory,STACK+phase+0x48,4),7)
                    states.append((model.r,model.memory,model.events))
                self.assertEqual(*states);count+=1
        gate=struct.unpack_from('>4I',rom,0x104D98)
        self.assertEqual(gate[1],0x10410003)
        (self.out/'caller-cases.json').write_text(json.dumps(dict(actual_four_word_windows=count,
            synthetic_stop_trampoline=True,whole_caller_not_executed=True,negative_one_gate_statically_verified=True))+'\n')

    def test_owner_profiles_padder_and_first_image_or_installed_audit(self):
        row=integration.qualify(self.root,self.out);self.assertEqual((row['words'],row['frame'],row['new_guards']),(61,40,0))
        if (self.root/source.SOURCE).read_bytes()==self.values[source.SOURCE]:
            self.assertTrue(integration.predict(self.root,self.out)['whole_ELF_unchanged'])
        else:self.assertTrue(integration.audit(self.root,self.out)['whole_ELF_unchanged'])

    def test_independent_assembly_gnu_maps_and_code_rebases(self):
        asm=self.out/'original.s';obj=asm.with_suffix('.o')
        asm.write_text((self.root/'conker/include/asm_processor_prelude.inc').read_text()+
            '\n.text\n.type '+source.FUNCTION+', @function\n'+
            self.values['conker/asm/nonmatchings/generated_B3020/func_1508868C.s'].decode()+
            '\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
            '-o',str(obj),str(asm)],check=True,capture_output=True)
        self.assertEqual(integration.checked(obj),integration.checked(self.obj))
        names=('D_800872A0','D_800D2394','D_800D2398','D_800D2399','D_800CC2D0','func_15088824')
        maps=((source.ENTRY,(TABLE,MASK,BASE,COUNT,ACTORS,RESET)),(0x1621FFF4,
            (0x8010FFF4,0x80218008,0x8033FFFE,0x80447FFD,0x80550010,0x1634FFF0)),
            (0x18FFF000,(0x80617FFC,0x80720004,0x8083FFF8,0x80948004,0x80A5FFF0,0x18F0003C)))
        for number,(entry,addresses) in enumerate(maps):
            images=[]
            for label,path in (('retail',obj),('source',self.obj)):
                script=self.out/(label+'-map-%d.ld'%number);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in zip(names,addresses)],'-o',str(elf),str(path)],check=True,capture_output=True)
                at,data=sections(elf)['.text'];self.assertEqual(at,entry);images.append(data[:244])
            self.assertEqual(*images)
        pairs=0
        for entry in (0x1621FFF4,0x18FFF000):
            for case in self.cases[:16]:
                a=self.model(self.retail,case,entry=entry).run();b=self.model(self.words,case,entry=entry).run()
                self.assertEqual((a.r,a.memory,a.events),(b.r,b.memory,b.events));pairs+=1
        (self.out/'relocation-maps.json').write_text(json.dumps(dict(GNU_maps=3,bindings=15,
            independent_assembly_equal=True,code_rebased_pairs=pairs,data_rebases_static_only=True))+'\n')


if __name__=='__main__':unittest.main()
