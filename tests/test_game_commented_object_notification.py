"""Complete notification C, relocation-safe schedule and immutable history."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_commented_notification_candidates as source
from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments.alternative_source_draft_word_screen import emit_function, nm_anchors
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_one_shot_timer_match import canonical_symbols
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout
from tools.tests import commented_notification_checkpoint as checkpoint


class CommentedObjectNotificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.out.mkdir(exist_ok=True)
        source.freeze(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.original = cls.root / 'conker/asm/nonmatchings/game_83300/func_15063168.s'

    def assemble(self, text, label):
        path = self.out / (label + '.s')
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + text)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)],
            capture_output=True, text=True, check=True)
        return obj

    def test_01_complete_owner_raw_schedule_pools_and_both_padders(self):
        before = (self.out / 'before-owner').read_text()
        old, w0 = build.compile_owner(self.root, self.out, before, 'owner-before')
        new, w1 = build.compile_owner(self.root, self.out, source.recover(before), 'owner-after')
        t0, f0, r0 = parse_object(old)
        t1, f1, r1 = parse_object(new)
        self.assertEqual(set(f0), set(f1))
        for name in set(f0) - {source.FUNCTION}:
            a, b = f0[name], f1[name]
            self.assertEqual(a['size'], b['size'], name)
            self.assertEqual(t0[a['value']:a['value'] + a['size']], t1[b['value']:b['value'] + b['size']], name)
            relative = lambda table, info: {at - info['value']: value for at, value in table.items()
                if info['value'] <= at < info['value'] + info['size']}
            self.assertEqual(relative(r0, a), relative(r1, b), name)
        self.assertEqual(normalized_pools(old), normalized_pools(new))
        self.assertLessEqual(w1.count('cfe: Warning'), w0.count('cfe: Warning'))
        linked, functions = build.link_owner(self.root, self.out, new, source.OWNER)
        info = functions[source.FUNCTION]
        raw = list(struct.unpack('>59I', linked[info['value']:info['value'] + 236]))
        truth = list(struct.unpack_from('>59I', self.rom, 0x90618))
        self.assertEqual([i for i, (a, b) in enumerate(zip(raw, truth)) if a != b], [12, 14])
        self.assertEqual(raw[12], truth[14])
        self.assertEqual(raw[14], truth[12])
        guards = self.out / 'guards.csv'
        guards.write_bytes((self.out / 'before-guards').read_bytes() + source.GUARD_ROWS.encode())
        primary = pad_c_object.emit_padded_assembly(new, self.root / 'conker/retail_layout.us.txt', source.OWNER,
            word_patches_path=guards)
        primary_obj = self.assemble(primary, 'primary-padded')
        extracted, unresolved = emit_function(t1, info, r1, source.FUNCTION, nm_anchors(self.root / 'conker/build/conker.us.elf'))
        self.assertFalse(unresolved)
        compact = self.assemble(extracted, 'selected-compact')
        selected_guards = self.out / 'selected-guards.csv'
        selected_guards.write_text(guards.read_text().splitlines()[0] + '\n' + source.GUARD_ROWS)
        generated = emit_padded_assembly(compact, self.original, filename=source.OWNER, word_patches_path=selected_guards)
        generated_obj = self.assemble(generated, 'generated-padded')
        for artifact in (primary_obj, generated_obj):
            text, functions = build.link_owner(self.root, self.out, artifact, source.OWNER)
            info = functions[source.FUNCTION]
            self.assertEqual(text[info['value']:info['value'] + 236], self.rom[0x90618:0x90704])
        (self.out / 'owners.json').write_text(json.dumps(dict(neighbors=len(f0) - 1, raw_words=59,
            raw_different_words=2, final_exact_words=59, guards=2, both_padders=True,
            normalized_pools_and_neighbor_relocations_fixed=True), indent=2) + '\n')

    def test_02_original_and_rebased_independent_links(self):
        original = self.assemble(self.original.read_text() + '\n.type ' + source.FUNCTION + ',@function\n.size ' +
            source.FUNCTION + ',236\n', 'original-retail')
        artifacts = (original, self.out / 'primary-padded.o', self.out / 'generated-padded.o')
        anchors = nm_anchors(self.root / 'conker/build/conker.us.elf')
        anchors.update(build.load_symbol_addrs(str(self.root / 'conker/symbol_addrs.us.txt')))
        for phase, base in enumerate((0x15004000, 0x16004000)):
            spans = []
            for index, artifact in enumerate(artifacts):
                _, functions, relocations = parse_object(artifact)
                symbols = {symbol for at, entries in relocations.items()
                    if functions[source.FUNCTION]['value'] <= at < functions[source.FUNCTION]['value'] + 236
                    for _, symbol in entries}
                # Extract the target again, so neighboring calls cannot affect
                # external-symbol enumeration or independent link placement.
                text, f, r = parse_object(artifact)
                asm, unresolved = emit_function(text, f[source.FUNCTION], r, source.FUNCTION, anchors)
                self.assertFalse(unresolved)
                single = self.assemble(asm, 'rebase-input-%d-%d' % (phase, index))
                order = {symbol: i for i, symbol in enumerate(sorted(symbols))}
                values = {symbol: (0x17008000 if symbol.startswith('func_') else
                    0x90007FFC + order[symbol] * 4) for symbol in symbols} if phase else {symbol: anchors[symbol] for symbol in symbols}
                script = single.with_suffix('.ld')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % base)
                elf = single.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in values.items()], '-o', str(elf), str(single)],
                    capture_output=True, text=True, check=True)
                spans.append(sections(elf)['.text'][1][:236])
            self.assertEqual(spans[0], spans[1])
            self.assertEqual(spans[0], spans[2])

    def test_03_effective_raw_word_relocation_and_semantic_controls(self):
        primary = self.out / 'owner-after.o'
        guards = self.out / 'guards.csv'
        before = (self.out / 'before-owner').read_text()
        changed = source.recover(before).replace('if (index == selfIndex)', 'if (index != selfIndex)')
        negative, _ = build.compile_owner(self.root, self.out, changed, 'negative-self')
        text, functions = build.link_owner(self.root, self.out, negative, source.OWNER)
        info = functions[source.FUNCTION]
        self.assertNotEqual(text[info['value']:info['value'] + 236], self.rom[0x90618:0x90704])
        for old, new in (('0x00008025,0x25CE0000', '0x00008024,0x25CE0000'),
                ('0x25CE0000,0x00008025,R_MIPS_LO16:D_800CC2D0', '0x25CE0000,0x00008025,R_MIPS_LO16:D_800CC2D4')):
            bad = self.out / 'negative-guards.csv'
            changed = guards.read_text().replace(old, new)
            self.assertNotEqual(changed, guards.read_text())
            bad.write_text(changed)
            with self.assertRaises(ValueError):
                pad_c_object.emit_padded_assembly(primary, self.root / 'conker/retail_layout.us.txt', source.OWNER, word_patches_path=bad)

    def test_04_native32_live_mask_self_attachment_and_callback_updates(self):
        native = '''typedef unsigned char u8;typedef signed char s8;typedef int s32;
typedef struct { u8 bytes[0x1AD]; } struct126;
typedef struct { u8 bytes[0x31C];struct126 *unk31C;u8 rest[12]; } struct127;
static struct127 D_800CC2D0[8];static struct126 attached[8];
static s8 D_8008FD8C;static s32 D_800CC268;static int calls[8],n,mode;
s32 func_15194FF4(struct127 *a,struct127 *b,s32 event){
 if(a<D_800CC2D0||a>=D_800CC2D0+8||event!=1)return 90;
 calls[n++]=b-D_800CC2D0;
 if(n==1&&mode==1){D_8008FD8C=3;D_800CC268^=0xAA;}
 if(n==1&&mode==2)D_8008FD8C=-1;
 return 0;}
''' + source.BODY + '''
static int run(void){int self,mask,pattern,count,i,expected[8],en,live,bound,j;
 if(sizeof(void*)!=4||sizeof(struct127)!=0x32C)return 80;
 for(self=0;self<8;self++)for(mask=0;mask<256;mask++)for(pattern=0;pattern<4;pattern++)
 for(count=-1;count<=8;count++)for(mode=0;mode<3;mode++){
  for(i=0;i<8;i++){D_800CC2D0[i].unk31C=((i+pattern)%3==0)?0:&attached[i];attached[i].bytes[0x1AC]=(i+pattern)&1;}
  live=mask;bound=count;en=0;
  for(i=0;i<bound;i++)if(i!=self&&(live&(1<<i))&&D_800CC2D0[i].unk31C&&attached[i].bytes[0x1AC]==0){
   expected[en++]=i;if(en==1&&mode==1){bound=3;live^=0xAA;}if(en==1&&mode==2)bound=-1;}
  D_8008FD8C=count;D_800CC268=mask;n=0;func_15063168(&D_800CC2D0[self]);
  if(n!=en||D_8008FD8C!=bound||D_800CC268!=live)return 1;
  for(j=0;j<n;j++)if(calls[j]!=expected[j])return 2;
 }return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
        for label, profile, body, status in (('O2', '-O2', source.BODY, 0), ('O0', '-O0', source.BODY, 0),
                ('negative', '-O2', source.BODY.replace('index == selfIndex', 'index != selfIndex'), 1)):
            path = self.out / ('native-' + label + '.c')
            path.write_text(native.replace(source.BODY, body))
            binary = path.with_suffix('')
            result = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing', '-ffreestanding',
                '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([str(binary)], capture_output=True).returncode, status, label)

    def test_05_installed_source_guards_progress_and_closed_image(self):
        source.freeze(self.root, self.out)
        self.assertEqual((self.root / 'conker/src/game_83300.c').read_text(), source.recover((self.out / 'before-owner').read_text()))
        self.assertEqual(checkpoint.codec_refill_checkpoint.previous_input((self.root / 'conker/retail_word_patches.us.csv').read_bytes(), 'conker/retail_word_patches.us.csv', self.root),
            (self.out / 'before-guards').read_bytes() + source.GUARD_ROWS.encode())
        self.assertEqual(checkpoint.codec_refill_checkpoint.previous_input((self.root / 'conker/Makefile').read_bytes(), 'conker/Makefile', self.root), (self.out / 'before-makefile').read_bytes())
        progress = (self.out / 'before-progress').read_bytes()
        row = next(line for line in progress.splitlines(keepends=True) if b',func_15063168,' in line)
        self.assertTrue(row.endswith(b',asm\n'))
        self.assertEqual((self.root / 'conker/progress.csv').read_bytes(), progress.replace(row, row.replace(b',asm\n', b',c\n')))
        before = (self.out / 'before-elf').read_bytes()
        current = checkpoint.codec_refill_checkpoint.previous_input((self.root / 'conker/build/conker.us.elf').read_bytes(), 'conker/build/conker.us.elf', self.root)
        # The original assembly already occupied its complete matching slot.
        self.assertEqual(current, before)
        self.assertEqual(canonical_symbols(current), canonical_symbols(before))
        data = audit_layout(self.root / 'conker/build/conker.us.elf', self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        (self.out / 'image.json').write_text(json.dumps(dict(ELF_sha256=hashlib.sha256(current).hexdigest(),
            identical_complete_ELF=True, new_C_rows=1, new_guards=2, protected_data=data), indent=2) + '\n')

    def test_06_effective_installed_and_immutable_input_controls(self):
        read = Path.read_bytes
        for filename in ('conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv', 'conker/progress.csv', 'conker/Makefile'):
            path = self.root / filename
            bad = read(path) + b'\n'
            with patch.object(Path, 'read_bytes', lambda p, value=bad: value if p == path else read(p)):
                with self.assertRaises(AssertionError):
                    self.test_05_installed_source_guards_progress_and_closed_image()
        read_text = Path.read_text
        path = self.root / 'conker/src/game_83300.c'
        bad = read_text(path) + '\n'
        with patch.object(Path, 'read_text', lambda p, *a, **k: bad if p == path else read_text(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_05_installed_source_guards_progress_and_closed_image()
        path = self.out / 'before-owner'
        with patch.object(Path, 'read_bytes', lambda p: b'bad baseline' if p == path else read(p)):
            with self.assertRaisesRegex(ValueError, 'immutable input'):
                self.test_05_installed_source_guards_progress_and_closed_image()

    def test_07_closed_historical_projection_and_unknown_input_controls(self):
        self.test_05_installed_source_guards_progress_and_closed_image()
        checkpoint.freeze_after(self.root)
        for path, key in checkpoint.PATHS.items():
            data = (self.root / path).read_bytes()
            self.assertEqual(checkpoint.previous_input(data, path, self.root), checkpoint.fixture(self.root, 'before', key))
            bad = data + b'\n'
            self.assertEqual(checkpoint.previous_input(bad, path, self.root), bad)


if __name__ == '__main__':
    unittest.main()
