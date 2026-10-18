"""Qualify the real frame/array improvement without claiming an installed match."""
import itertools
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import game_route_spline_payload_fitting as fit
from tools.experiments import game_route_spline_payload_frame as frame
from tools.tests import test_game_route_spline_payload_recovery as guest
from tools.tests.game_owner_pool import normalized_pools


class SplinePayloadFittingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/fit.BUILD
        cls.obj,cls.words,cls.row=fit.qualify(cls.root,cls.out)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.truth=list(struct.unpack_from('>305I',cls.rom,fit.source.ROM))
        elf=(cls.root/'conker/build/conker.us.elf').read_bytes();cls.helpers={}
        for entry,count in guest.HELPERS.items():
            at=fit.source.prior.prior.elf_slot_offset(elf,entry,count*4)
            if elf[at:at+count*4]!=cls.rom[entry-0x14FD2B50:entry-0x14FD2B50+count*4]:
                raise ValueError('Installed helper is not retail')
            cls.helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,elf,at)))
        at=fit.source.prior.prior.elf_slot_offset(elf,guest.SCALE,8)
        if elf[at:at+8]!=bytes.fromhex('3f91de69ad42c3ca'):raise ValueError('Retail double factor changed')

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def pair(self,kw,literal=True):
        initial,args=guest.fixture(**kw)
        return [guest.PayloadOracle(w,initial,args,self.helpers,retail=retail,front=True,literal=literal).run()
            for retail,w in ((False,self.words),(True,self.truth))]

    def test_01_complete_semantics_literal_homes_and_private_memories(self):
        total=traces=complete=0;full_by_mode={'null':[0,0],'stop':[0,0],'spline':[0,0]}
        for kw in guest.cases():
            initial,args=guest.fixture(**kw);expected=guest.reference(initial,args)
            a,b=self.pair(kw)
            self.assertEqual((guest.guest.public(a.memory),a.calls),(guest.guest.public(b.memory),b.calls),kw)
            normalized=guest.PayloadOracle(self.words,initial,args,self.helpers,front=True).run()
            self.assertEqual((guest.guest.public(normalized.memory),normalized.calls),expected,kw)
            self.assertEqual(a.trace,b.trace,kw)
            for offset in (-44,-60,-76,-92,-108,-124):
                self.assertEqual(bytes(a.memory[guest.STACK+offset+i] for i in range(16)),
                    bytes(b.memory[guest.STACK+offset+i] for i in range(16)),kw)
            mode='null' if kw.get('null') else 'stop' if kw.get('stop') else 'spline'
            full_by_mode[mode][0]+=a.memory==b.memory;full_by_mode[mode][1]+=1
            traces+=a.trace==b.trace;complete+=a.memory==b.memory;total+=1
        self.assertEqual((total,traces,complete),(1069,1069,1069))
        self.receipt('guest-frame',paired_cases=total,public_traces_equal=traces,complete_memories_equal=complete,
            full_by_mode=full_by_mode,literal_private_call_addresses_equal=True,all96_array_bytes_equal=True,
            actual_helper_words=sum(guest.HELPERS.values()),trig_providers_opaque=True,installed=False)

    def test_02_frame_save_layout_and_first_fired_boundaries(self):
        raw,_=fit.checked(self.obj);words=struct.unpack('>302I',raw)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(302,248,287))
        self.assertEqual(words[:17],tuple(self.truth[:17]))
        self.assertEqual(sum(w>>26==61 for w in words),3)
        homes={w>>16&31:(w&65535)-248 for w in words
            if w>>26==9 and w>>21&31==29 and w>>16&31 in range(16,23)}
        self.assertEqual(homes,{22:-44,17:-60,18:-76,19:-92,20:-108,16:-124})
        initial,args=guest.fixture(null=True);prefixes=[]
        for cut in range(16):
            machines=[]
            for retail,body in ((False,self.words),(True,self.truth)):
                m=guest.PayloadOracle(body,initial,args,self.helpers,retail=retail,front=True);m.access_fault=cut
                with self.assertRaises(guest.guest.base.faults.AccessBoundary):m.run()
                self.assertEqual(m.all_accesses,cut);machines.append(m)
            a,b=machines
            self.assertEqual(a.r[29],b.r[29])
            equal=(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls)
            self.assertTrue(equal,cut)
            prefixes.append(dict(cut=cut,equal=equal,SP_equal=True))
        self.receipt('private-prefixes',boundaries=prefixes,homes=homes,full_fault_parity=False,
            no_frame_guards=True,installed=False)

    def test_03_all_words_bindings_and_literal_pool_fail_closed(self):
        text,functions,bindings=fit.source.parse_object(self.obj);f=functions[fit.source.FUNCTION];total=0
        for i in range(302):
            altered=bytearray(text);altered[f['value']+i*4+3]^=1
            with patch.object(fit.source,'parse_object',return_value=(bytes(altered),functions,bindings)),self.assertRaises(ValueError):
                fit.checked(self.obj)
            total+=1
        for at in fit.BINDINGS:
            altered=dict(bindings);altered[f['value']+at]=[('R_MIPS_26','wrong_symbol')]
            with patch.object(fit.source,'parse_object',return_value=(text,functions,altered)),self.assertRaises(ValueError):
                fit.checked(self.obj)
            total+=1
        pools=fit.sections(self.obj)
        for i in range(16):
            changed=dict(pools);raw=bytearray(pools['.rodata'][1]);raw[i]^=1;changed['.rodata']=(0,bytes(raw))
            with patch.object(fit,'sections',return_value=changed),self.assertRaises(ValueError):
                fit.link_literal(self.root,self.out,self.obj)
        self.assertEqual(total,335)
        self.receipt('frame-guards',word_binding_controls=total,literal_pool_byte_controls=16)

    def test_04_real_helpers_stop_aliases_and_effective_source_controls(self):
        for stop,bank in itertools.product((1,-1),(0,1)):
            a,b=self.pair(dict(stop=stop,bank=bank,alias=2));self.assertEqual((a.memory,a.calls),(b.memory,b.calls))
        body=fit.selected();controls={
            'wrong-command':(body.replace('), 10, payload);','), 9, payload);'),dict(stop=1)),
            'signed-channel':(body.replace('(void *)(u32)((u8 *)xCursor)[0x23D]',
                '(void *)(s32)(s8)((u8 *)xCursor)[0x23D]'),dict(stop=1,bank=255)),
            'wrong-decrement':(body.replace('phase - 1.0f','phase - 2.0f'),dict(fraction=2.5,frames=0)),
            'float-scale':(body.replace('(f32)((f64)*(f32 *)(actor + 0x40) * 0.01745)',
                '*(f32 *)(actor + 0x40) * 0.01745f'),dict(valid=1,heading=.625)),
            'fresh-channel':(body.replace('((u8 *)xCursor)[0x23D]','(*(u8 **)(actor + 0x318))[0x23D]'),dict(stop=1,alias=2)),
        }
        rows=[]
        for name,(changed,kw) in controls.items():
            self.assertNotEqual(body,changed,name)
            obj,_,row=fit.source.measure(self.root,self.out,'negative-'+name,changed)
            if name=='float-scale':
                self.assertEqual(fit.sections(obj)['.rodata'][1],bytes.fromhex('3c8ef34d000000000000000000000000'))
                data,functions=fit.source.prior.prior.link_owner(self.root,self.out,obj,fit.source.OWNER)
                f=functions[fit.source.FUNCTION]
                words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            else:words=fit.link_literal(self.root,self.out,obj)
            initial,args=guest.fixture(**kw)
            if name=='float-scale':
                at,pool=fit.sections(obj.with_suffix('.elf'))['.rodata']
                initial.update({at+i:b for i,b in enumerate(pool)})
            m=guest.PayloadOracle(words,initial,args,self.helpers,front=True).run()
            self.assertNotEqual((guest.guest.public(m.memory),m.calls),guest.reference(initial,args),name)
            rows.append(dict(name=name,ordinary_mismatch=True,words=row['words']))
        self.receipt('frame-C-controls',effective_controls=rows,stop_queue_aliases=4)

    def test_05_unchanged_neighbors_and_declared_literal_only_pool_change(self):
        values=fit.source.freeze(self.root,self.out)
        before,diag=fit.source.prior.prior.compile_profile(self.root,self.out,
            values['conker/src/game/generated_B3020.c'].decode(),'frame-before')
        self.assertEqual(diag,'');self.assertEqual(fit.source.prior.same_functions(before,self.obj,(fit.source.FUNCTION,)),72)
        old,new=normalized_pools(before),normalized_pools(self.obj)
        self.assertIsNone(old['.rodata'])
        self.assertEqual(new['.rodata'],(bytes.fromhex('3f91de69ad42c3ca0000000000000000'),()))
        self.assertEqual({k:v for k,v in old.items() if k!='.rodata'},
            {k:v for k,v in new.items() if k!='.rodata'})
        self.assertEqual(fit.sections(self.obj)['.rodata'][1],bytes.fromhex('3f91de69ad42c3ca0000000000000000'))
        self.assertFalse(self.row['production_installed']);self.assertEqual(self.row['matching_credit'],0)
        self.receipt('frame-owner',unchanged_neighbors=72,pool_addition='one double literal plus alignment padding',
            production_inputs_unchanged=len(values),matching_credit=0,installed=False)

    def test_06_completed_compiler_trace_inputs_and_effective_corruptions(self):
        out=self.root/frame.BUILD;work=out/'trace-front';log=(work/'debugger.txt').read_text()
        baseline,_=frame.qualify(self.root,out)
        self.assertEqual(frame.frame.fingerprints(self.root),frame.frame.COMPILERS)
        self.assertIn('TRACE_EXIT inferior=1 code=0',log.splitlines())
        self.assertEqual(fit.source.parse_object(baseline),fit.source.parse_object(work/'trace.o'))
        self.assertEqual(normalized_pools(baseline),normalized_pools(work/'trace.o'))
        observation=frame.frame.validate_observations(work,log);events=observation['events']
        self.assertEqual([e['frame'] for e in events],[0,72,88,288])
        self.assertEqual(tuple(events[-1][k] for k in ('locals','saved','outgoing','temporary','temp_base','pool')),
            (200,72,16,0,0,[]))
        records=observation['records']
        self.assertEqual({k:len(v) for k,v in records.items()},{'frontend':1285,'optimizer':1193})
        self.assertEqual({k:[r['length'] for r in v if r['name']=='def' and r['storage']=='M']
            for k,v in records.items()},{'frontend':[189],'optimizer':[196]})
        controls=[log.replace('FRAME_TRACE ','IGNORED_FRAME_TRACE '),
            log.replace('TRACE_EXIT inferior=3 code=0','TRACE_EXIT inferior=3 code=9')]
        for bad in controls:
            with self.assertRaises(ValueError):frame.frame.validate_observations(work,bad)
        with tempfile.TemporaryDirectory() as tmp:
            copied=Path(tmp)
            for name in ('frontend.ucode','optimizer.ucode','ucode-table.json','ucode-types.json'):
                shutil.copyfile(work/name,copied/name)
            for name in ('frontend.ucode','optimizer.ucode'):
                original=(copied/name).read_bytes();data=bytearray(original);data[0]^=1;(copied/name).write_bytes(data)
                with self.assertRaises(ValueError):frame.frame.validate_observations(copied,log)
                (copied/name).write_bytes(original)
        with patch.object(frame.frame,'fingerprints',return_value={}),self.assertRaises(ValueError):frame.trace(self.root,out)
        self.receipt('frame-trace-tests',owned_trace_complete=True,normal_code_and_pools_equal=True,
            events=4,frames=[0,72,88,288],observed_UGEN_temporary_bytes=0,corruption_controls=5,
            compiler_restarted_by_tests=False,installed=False)

    def test_07_joint_extent_frame_semantics_and_strict_rejection(self):
        obj,words,row=fit.qualify(self.root,self.out,joint=True)
        self.assertEqual((row['words'],row['frame'],row['differences']),(305,248,140))
        raw,_=fit.checked(obj,True);packed=struct.unpack('>305I',raw)
        self.assertEqual(sum(w>>26==61 for w in packed),3)
        homes={w>>16&31:(w&65535)-248 for w in packed
            if w>>26==9 and w>>21&31==29 and w>>16&31 in range(16,24)}
        self.assertEqual(homes,{23:-44,17:-60,18:-76,19:-92,20:-108,16:-124})
        count=memories=traces=0
        for kw in guest.cases():
            initial,args=guest.fixture(**kw)
            a,b=[guest.PayloadOracle(w,initial,args,self.helpers,retail=retail,front=True,literal=True).run()
                for retail,w in ((False,words),(True,self.truth))]
            self.assertEqual((a.memory,a.calls,a.trace),(b.memory,b.calls,b.trace),kw)
            count+=1;memories+=a.memory==b.memory;traces+=a.trace==b.trace
        self.assertEqual((count,memories,traces),(1069,1069,1069))
        for kw in (dict(stop=1,alias=2),dict(stop=-1,bank=1,alias=2)):
            initial,args=guest.fixture(**kw)
            a,b=[guest.PayloadOracle(w,initial,args,self.helpers,retail=retail,front=True,literal=True).run()
                for retail,w in ((False,words),(True,self.truth))]
            self.assertEqual((a.memory,a.calls),(b.memory,b.calls))
        text,functions,bindings=fit.source.parse_object(obj);f=functions[fit.source.FUNCTION]
        for i in range(305):
            altered=bytearray(text);altered[f['value']+i*4+3]^=1
            with patch.object(fit.source,'parse_object',return_value=(bytes(altered),functions,bindings)),self.assertRaises(ValueError):
                fit.checked(obj,True)
        for at in fit.JOINT_BINDINGS:
            altered=dict(bindings);altered[f['value']+at]=[('R_MIPS_26','wrong_symbol')]
            with patch.object(fit.source,'parse_object',return_value=(text,functions,altered)),self.assertRaises(ValueError):
                fit.checked(obj,True)
        self.assertEqual(fit.source.prior.same_functions(self.out/'frame-before.o',obj,(fit.source.FUNCTION,)),72)
        self.assertEqual(normalized_pools(self.obj),normalized_pools(obj))
        initial,args=guest.fixture(null=True);states=[]
        for retail,w in ((False,words),(True,self.truth)):
            m=guest.PayloadOracle(w,initial,args,self.helpers,retail=retail,front=True);m.access_fault=1
            with self.assertRaises(guest.guest.base.faults.AccessBoundary):m.run()
            self.assertEqual(m.all_accesses,1);states.append(m)
        self.assertNotEqual(states[0].memory,states[1].memory)
        self.receipt('joint-qualification',words=305,frame=248,literal_differences=140,paired_cases=count,
            complete_memories_equal=memories,public_traces_equal=traces,literal_private_calls_equal=True,
            saved_FP_pairs=3,unchanged_neighbors=72,word_binding_controls=338,
            first_saved_register_fault_still_different=True,native32_qualified=False,installed=False,matching_credit=0)


if __name__=='__main__':unittest.main()
