"""Route copy: real SDK overlap, saved metadata, table aliases and caller ABI."""
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_route_record_copy_candidates as source
from tools.experiments import game_route_record_copy_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle as SDKOracle
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_queued_segment_writer import SegmentQueueOracle,STACK
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_projected_packet_draw import native_command

TABLE,COPY,ARENA,ALTERNATE=0x800872A0,0x10023A10,0x20000,0x24000
BANKS=(ARENA,ALTERNATE)
CAPACITY=1024
INVERSE=pow(33,-1,1<<30)


def offset(index):return index*132&0xFFFFFFFF
def index_for(byte_offset):return (byte_offset//4*INVERSE)%(1<<30)


def cases():
    for value in range(256):yield (0,1,value&3,value,255-value,value&7,value&1,0)
    for first in range(4):
        for second in range(4):
            for alignment in range(4):
                for mode in (0,1):yield (first,second,alignment,128,255,(first+second)&7,mode,0)
    for first,second in ((0,4),(4,0),(0,128),(128,0),(0,0),(0,132),(132,0)):
        for alignment in range(4):
            for mode in (0,1):yield (index_for(first),index_for(second),alignment,255,128,3,mode,0)
    for index in (0,0x7FFFFFFF,0x80000000,0xFFFFFFFF):
        for alignment in (0,3):yield (index,index,alignment,128,255,7,0,1)


def fixture(case,phase=0):
    first,second,alignment,identity,state,pattern,mode,null=case
    m={STACK+i:(i*17+0xA5)&255 for i in range(-0x300,0x100)}
    for bank,base in enumerate(BANKS):
        m.update({base+i:(i*137+pattern*31+bank*53+19)&255 for i in range(CAPACITY)})
    m.update({TABLE+i:0xA5 for i in range(-16,20)})
    d=ARENA+alignment+(0 if null else offset(second))
    put(m,d+0x31,identity,1);put(m,d+0x30,state,1)
    put(m,TABLE,0 if null else ARENA+alignment,4)
    if mode==2:
        # The ID restore clears the table pointer's high byte; map its next state destination.
        at=(TABLE-offset(second)-0x31)&0xFFFFFFFF
        next_base=at&0x00FFFFFF
        m.update({next_base+offset(second)+i:0xA5 for i in range(0x40)})
    return m,(first,second)


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x300<=a<STACK+0x100}


def reference(memory,args,mode=0,alignment=0,phase=0):
    m=memory.copy();table=read(m,TABLE,4)
    if table==0:return m,[]
    first,second=args;s=(table+offset(first))&0xFFFFFFFF;d=(table+offset(second))&0xFFFFFFFF
    identity,state=read(m,d+0x31,1),read(m,d+0x30,1)
    data=bytes(m[s+i] for i in range(132));m.update({d+i:v for i,v in enumerate(data)})
    if mode==1:put(m,TABLE,ALTERNATE+alignment,4)
    elif mode==2:put(m,TABLE,(TABLE-offset(second)-0x31)&0xFFFFFFFF,4)
    elif mode==3:
        put(m,STACK+phase,0x7FFFFFFF,4);put(m,STACK+phase+4,0x80000000,4)
    put(m,(read(m,TABLE,4)+offset(second)+0x31)&0xFFFFFFFF,identity,1)
    put(m,(read(m,TABLE,4)+offset(second)+0x30)&0xFFFFFFFF,state,1)
    return m,[(COPY,s,d,132)]


class AccessFault(Exception):pass


class CopyModel(SDKOracle):
    run=TriangleOracle.run

    def __init__(self,words,memory,args,connected=None,phase=0,mode=0,alignment=0,entry=source.ENTRY):
        self.fault,self.accesses,self.in_hook=None,0,False
        SegmentQueueOracle.__init__(self,words,entry,memory,args)
        self.r[29]=self.before[29]=STACK+phase
        self.saved_f=self.f[20:].copy()
        self.tail=False
        self.code.update(connected or {})
        self.events,self.calls,self.caller_args=[],[],[]
        self.mode,self.alignment,self.phase=mode,alignment,phase

    def gate(self):
        if self.recording and not self.in_hook:
            if self.fault==self.accesses:raise AccessFault()
            self.accesses+=1

    def get(self,address,size):
        self.gate()
        if size in (2,4):assert address%size==0,('unaligned SDK read',address,size)
        return super().get(address,size)

    def put(self,address,value,size):
        self.gate()
        if size in (2,4):assert address%size==0,('unaligned SDK store',address,size)
        super().put(address,value,size)

    def record_call(self,target):
        if target==source.ENTRY:
            self.caller_args.append(tuple(self.r[4:6]));return
        assert target==COPY,hex(target)
        args=tuple(self.r[4:7]);self.calls.append((target,*args));self.events.append(('CALL',target,args))

    def hook(self,target):
        assert target==COPY
        self.in_hook=True
        try:
            s,d,n=self.r[4:7]
            assert 0<=n<=132
            data=bytes(self.get(s+i,1) for i in range(n))
            for i,v in enumerate(data):self.put(d+i,v,1)
            if self.mode==1:self.put(TABLE,ALTERNATE+self.alignment,4)
            elif self.mode==2:self.put(TABLE,(TABLE-offset(self.before[5])-0x31)&0xFFFFFFFF,4)
            elif self.mode==3:
                self.put(self.r[29]+0x28,0x7FFFFFFF,4);self.put(self.r[29]+0x2C,0x80000000,4)
            for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
            self.r[2]=0xDEADC0DE
            self.f[:20]=[0xA5000000+i for i in range(20)]
        finally:self.in_hook=False


NATIVE=r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;
static u8 arena[2][1024] __attribute__((aligned(16))),wanted[2][1024] __attribute__((aligned(16)));
u8 *D_800872A0;
static u32 mode,alignment,sourceOffset,destinationOffset,calls,failure;
void bcopy(const void *from,void *to,int n) {
    u8 snapshot[132];const u8 *s=from;u8 *d=to;int i;
    calls++;if(s!=arena[0]+alignment+sourceOffset || d!=arena[0]+alignment+destinationOffset || n!=132)failure=22;
    if(n<0 || n>132)return;
    for(i=0;i<n;i++)snapshot[i]=s[i];for(i=0;i<n;i++)d[i]=snapshot[i];
    if(mode)D_800872A0=arena[1]+alignment;
}
SOURCE_BODY
typedef struct {u32 input[8],first,count;} Case;
static const u32 patches[]={PATCHES};
static const Case cases[]={ROWS};
void _start(void) {
    u32 n,b,i,value;const Case *c;u8 *d;
    for(n=0;!failure && n<sizeof(cases)/sizeof(cases[0]);n++) {
        c=cases+n;alignment=c->input[2];mode=c->input[6];calls=0;
        sourceOffset=c->input[0]*132U;destinationOffset=c->input[1]*132U;
        for(b=0;b<2;b++)for(i=0;i<1024;i++)arena[b][i]=wanted[b][i]=(u8)(i*137+c->input[5]*31+b*53+19);
        d=arena[0]+alignment+(c->input[7]?0:destinationOffset);
        d[0x31]=c->input[3];d[0x30]=c->input[4];
        wanted[0][alignment+(c->input[7]?0:destinationOffset)+0x31]=c->input[3];
        wanted[0][alignment+(c->input[7]?0:destinationOffset)+0x30]=c->input[4];
        D_800872A0=c->input[7]?0:arena[0]+alignment;
        for(i=0;i<c->count;i++){value=patches[c->first+i];wanted[value>>24][value>>8&65535]=(u8)value;}
        func_150885EC(c->input[0],c->input[1]);
        if(calls!=(c->input[7]?0:1))failure=23;
        if(D_800872A0!=(c->input[7]?0:arena[mode]+alignment))failure=24;
        for(b=0;b<2;b++)for(i=0;i<1024;i++)if(arena[b][i]!=wanted[b][i])failure=21;
    }
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''


class GameRouteRecordCopyMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out)
        cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out,'test-selected')
        rom=cls.values['conker/conker.us.bin'];cls.retail=list(struct.unpack_from('>40I',rom,source.ROM))
        cls.sdk=list(struct.unpack_from('>193I',rom,0x23A10))
        image=cls.values['conker/build/conker.us.elf'];at=elf_slot_offset(image,COPY,193*4)
        if list(struct.unpack_from('>193I',image,at))!=cls.sdk:raise ValueError('SDK bcopy differs from ROM')
        cls.connected=dict(zip(range(COPY,COPY+193*4,4),cls.sdk));cls.cases=list(cases())

    def model(self,words,case,phase=0,memory=None,entry=source.ENTRY):
        seed,args=fixture(case,phase)
        return CopyModel(words,seed if memory is None else memory,args,
            self.connected if case[6]==0 else {},phase,case[6],case[2],entry)

    def test_direct_words_frame_bindings_and_shape_controls(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(40,40,0,''))
        self.assertEqual(self.words,self.retail);integration.checked(self.obj)
        for name,expected in (('initial',(39,48,32)),('offset-unsigned',(40,48,13))):
            _,words,row=source.compile_candidate(self.root,self.out,'control-'+name,dict(source.candidates())[name])
            self.assertEqual((row['words'],row['frame'],row['differences']),expected);self.assertNotEqual(words,self.retail)

    def test_real_sdk_and_redirected_provider_corpus(self):
        coverage=set();real=provider=0
        for case in self.cases:
            for phase in (0,8):
                a=self.model(self.retail,case,phase).run();b=self.model(self.words,case,phase).run()
                memory,args=fixture(case,phase);want,calls=reference(memory,args,case[6],case[2],phase)
                self.assertEqual((a.r,a.f,a.lo,a.memory,a.events,a.calls),(b.r,b.f,b.lo,b.memory,b.events,b.calls))
                self.assertEqual((public(a.memory),a.calls),(public(want),calls))
                self.assertEqual(sum(e[0]=='R' and e[1]==TABLE for e in a.events),1 if case[7] else 3)
                coverage.update(a.visits)
            if case[6]==0:real+=1
            else:provider+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+160,4))<=coverage)
        (self.out/'connected-cases.json').write_text(json.dumps(dict(cases=len(self.cases),phases=2,
            real_SDK_profiles=real,bounded_redirect_profiles=provider,SDK_words=193,all40_target_words_visited=True))+'\n')

    def test_actual_sdk_overlap_alignment_matrix(self):
        count=0
        for source_align in range(4):
            for destination_align in range(4):
                for delta in (-132,-128,-4,-1,0,1,4,128,132):
                    m={ARENA+i:(i*137+19)&255 for i in range(CAPACITY)}
                    m.update({STACK+i:0xA5 for i in range(-0x100,0x100)})
                    s=ARENA+256+source_align;d=ARENA+256+delta+destination_align
                    wanted=m.copy();wanted.update({d+i:v for i,v in enumerate(bytes(m[s+i] for i in range(132)))})
                    model=CopyModel(self.sdk,m,(s,d,132),entry=COPY).run()
                    self.assertEqual(model.memory,wanted);self.assertEqual(model.r[2],d);count+=1
        self.assertEqual(count,144)

    def test_table_pointer_aliases_and_incoming_home_mutation(self):
        for mode in (2,3):
            case=(0,1,0,0,128,3,mode,0)
            for phase in (0,8):
                a=self.model(self.retail,case,phase).run();b=self.model(self.words,case,phase).run()
                m,args=fixture(case,phase);want,calls=reference(m,args,mode,0,phase)
                self.assertEqual((a.r,a.memory,a.events),(b.r,b.memory,b.events))
                self.assertEqual((public(a.memory),a.calls),(public(want),calls))
        # An actual SDK destination overwrites the global pointer during the copy.
        table=TABLE-0x50;src=table+132;m={STACK+i:0xA5 for i in range(-0x100,0x100)}
        for base in (table-16,ALTERNATE):m.update({base+i:(i*13+0xA5)&255 for i in range(512)})
        put(m,TABLE,table,4);put(m,table+0x31,255,1);put(m,table+0x30,128,1)
        put(m,src+0x50,ALTERNATE,4)
        wanted,calls=reference(m,(1,0))
        pair=[CopyModel(words,m,(1,0),self.connected).run() for words in (self.retail,self.words)]
        self.assertEqual((pair[0].r,pair[0].memory,pair[0].events),(pair[1].r,pair[1].memory,pair[1].events))
        self.assertEqual((public(pair[1].memory),pair[1].calls),(public(wanted),calls))

    def test_fired_connected_access_fault_pairs(self):
        pairs=0
        selected=[self.cases[i] for i in (0,1,64,128,256,300,384,392,440,447)]
        for case in selected:
            for phase in (0,8):
                complete=self.model(self.retail,case,phase).run()
                for cut in range(complete.accesses):
                    states=[]
                    for words in (self.retail,self.words):
                        model=self.model(words,case,phase);model.fault=cut
                        with self.assertRaises(AccessFault):model.run()
                        self.assertEqual(model.accesses,cut)
                        states.append((model.r,model.f,model.lo,model.memory,model.events,model.calls))
                    self.assertEqual(*states);pairs+=1
        (self.out/'access-cuts.json').write_text(json.dumps(dict(fired_pairs=pairs,profiles=len(selected),phases=2,
            SDK_accesses_included_for_real_profiles=True,provider_internal_accesses_excluded=True))+'\n')

    def test_native32_full_banks_and_expected_byte_patches(self):
        patches=[];rows=[]
        for case in self.cases:
            m,args=fixture(case);wanted,calls=reference(m,args,case[6],case[2]);first=len(patches)
            for bank,base in enumerate(BANKS):
                patches.extend((bank<<24)|(i<<8)|wanted[base+i] for i in range(CAPACITY) if m[base+i]!=wanted[base+i])
            fmt=lambda values:','.join('0x%Xu'%(v&0xFFFFFFFF) for v in values)
            rows.append('{{%s},%d,%d}'%(fmt(case),first,len(patches)-first))
        base=NATIVE.replace('PATCHES',','.join('0x%Xu'%p for p in patches)).replace('ROWS',',\n'.join(rows))
        units=[('o0','-O0',False,source.SELECTED,0),('o2','-O2',False,source.SELECTED,0),
            ('ubsan','-O2',True,source.SELECTED,0),('negative-id','-O2',True,
             source.SELECTED.replace('] = savedId;','] = savedId ^ 1;'),21)]
        exits={}
        for name,opt,sanitize,body,want in units:
            path=self.out/('native-'+name+'.c');path.write_text(base.replace('SOURCE_BODY',body));exe=path.with_suffix('')
            command=[*native_command(opt,sanitize),'-mstackrealign','-fno-strict-aliasing',str(path),'-o',str(exe)]
            built=subprocess.run(command,cwd=self.root,capture_output=True,text=True)
            (self.out/('native-'+name+'-compile.json')).write_text(json.dumps(dict(command=command,
                exit=built.returncode,diagnostics=built.stdout+built.stderr),indent=2)+'\n')
            self.assertEqual((built.returncode,built.stdout,built.stderr),(0,'',''),name)
            run=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertEqual((run.returncode,run.stdout,run.stderr),(want,'',''),name);exits[name]=run.returncode
        (self.out/'native-cases.json').write_text(json.dumps(dict(cases=len(self.cases),bank_bytes=2048,
            expected_byte_patches=len(patches),all_bytes_compared=True,exits=exits))+'\n')

    def test_ordinary_executed_source_negatives(self):
        call='bcopy((u8 *)((u32)sourceIndex * 0x84 + (u32)table),\n              table + ((u32)destinationIndex * 0x84), 0x84);'
        self.assertIn(call,source.SELECTED)
        cached=source.SELECTED.replace('        D_800872A0[','        table[')
        forms={
            'reverse-copy':source.SELECTED.replace(call,'bcopy(table + ((u32)destinationIndex * 0x84), (u8 *)((u32)sourceIndex * 0x84 + (u32)table), 0x84);'),
            'short-copy':source.SELECTED.replace(', 0x84);',', 0x80);'),
            'wrong-id':source.SELECTED.replace('] = savedId;','] = savedId ^ 1;'),
            'cached-before-copy':cached,
            'cached-after-copy':cached.replace(
                call,call+'\n        table = D_800872A0;'),
        }
        for name,body in forms.items():
            _,words,_=source.compile_candidate(self.root,self.out,'negative-'+name,body)
            mode=1 if name=='cached-before-copy' else 2 if name=='cached-after-copy' else 0
            case=(0,1,0,0,128,3,mode,0)
            a=self.model(self.retail,case).run();b=self.model(words,case).run()
            self.assertNotEqual((public(a.memory),a.calls),(public(b.memory),b.calls),name)

    def test_actual_four_word_caller_window_ignores_v0(self):
        entry=0x150D78F4;rom=self.values['conker/conker.us.bin']
        window=list(struct.unpack_from('>4I',rom,0x104DA4))+[0x02E00008,0]
        self.assertEqual(window[:2],[0x0D42217B,0x00C02025])
        count=0
        for phase in (0,8):
            for first,second in ((0,1),(1,0),(1,1),(index_for(4),0)):
                for mode in (0,3):
                    case=(first,second,0,255,128,3,mode,0);m,args=fixture(case,phase)
                    m.update({STACK+phase+0x50+i:0 for i in range(4)})
                    m.update({0x60000+0x31C+i:0 for i in range(4)})
                    put(m,STACK+phase+0x50,0x60000,4);put(m,0x6031C,0x12345678,4)
                    states=[]
                    for words in (self.retail,self.words):
                        connected=dict(self.connected) if mode==0 else {}
                        connected.update(zip(range(source.ENTRY,source.ENTRY+160,4),words))
                        model=CopyModel(window,m,(0xA5000004,second,first),connected,phase,mode,entry=entry)
                        model.r[23]=model.before[23]=0xDEAD0000;model.before[31]=entry+8
                        model.run();self.assertEqual(model.caller_args,[(first,second)])
                        self.assertEqual(model.r[2],0x12345678)
                        states.append((model.r,model.memory,model.events))
                    self.assertEqual(*states);count+=1
        (self.out/'caller-cases.json').write_text(json.dumps(dict(actual_four_word_windows=count,
            synthetic_stop_trampoline=True,whole_caller_not_executed=True,poisoned_copy_return_profiles=True))+'\n')

    def test_owner_profiles_padder_and_first_image_or_installed_audit(self):
        row=integration.qualify(self.root,self.out);self.assertEqual((row['words'],row['frame'],row['new_guards']),(40,40,0))
        if (self.root/source.SOURCE).read_bytes()==self.values[source.SOURCE]:
            self.assertTrue(integration.predict(self.root,self.out)['whole_ELF_unchanged'])
        else:self.assertTrue(integration.audit(self.root,self.out)['whole_ELF_unchanged'])

    def test_independent_assembly_and_gnu_maps(self):
        asm=self.out/'original.s';obj=asm.with_suffix('.o')
        asm.write_text((self.root/'conker/include/asm_processor_prelude.inc').read_text()+
            '\n.text\n.type '+source.FUNCTION+', @function\n'+
            self.values['conker/asm/nonmatchings/generated_B3020/func_150885EC.s'].decode()+
            '\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
            '-o',str(obj),str(asm)],check=True,capture_output=True)
        self.assertEqual(integration.checked(obj),integration.checked(self.obj))
        for i,(entry,table,copy) in enumerate(((source.ENTRY,TABLE,COPY),(0x1621FFF4,0x8010FFF4,0x10018010),
                (0x18FFF000,0x80218008,0x10027FFC))):
            images=[]
            for label,path in (('retail',obj),('source',self.obj)):
                script=self.out/(label+'-map-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                elf=script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=D_800872A0=0x%X'%table,'--defsym=bcopy=0x%X'%copy,'-o',str(elf),str(path)],check=True,capture_output=True)
                at,data=sections(elf)['.text'];self.assertEqual(at,entry);images.append(data[:160])
            self.assertEqual(*images)
        pairs=0
        for entry in (0x1621FFF4,0x18FFF000):
            for case in self.cases[:16]:
                a=self.model(self.retail,case,entry=entry).run();b=self.model(self.words,case,entry=entry).run()
                self.assertEqual((a.r,a.memory,a.events),(b.r,b.memory,b.events));pairs+=1
        (self.out/'relocation-maps.json').write_text(json.dumps(dict(GNU_maps=3,bindings=5,
            independent_assembly_equal=True,code_rebased_pairs=pairs,data_rebases_static_only=True))+'\n')


if __name__=='__main__':unittest.main()
