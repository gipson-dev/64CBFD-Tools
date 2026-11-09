"""Direct sequence-time advance, complete owners and strict linked-image audit."""
import hashlib,json,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments.game_active_record_lookup_match import compile_owner
from tools.experiments.game_remaining_donor_candidates import compile_owner as compile_default
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-sequence-time-advance-1501E400-match'
FUNCTION,OWNER='func_1501E400','generated_49D30'
SOURCE='conker/src/game/generated_49D30.c'
OBJECT='conker/build/src/game/generated_49D30.c.o'
CALLER_SOURCE='conker/src/game_45B80.c'
CALLER_OBJECT='conker/build/src/game_45B80.c.o'
ASM='conker/asm/49D30.s'
ELF='conker/build/conker.us.elf'
GUARDS='conker/retail_word_patches.us.csv'
ENTRY,ROM,SIZE=0x1501E400,0x4B8B0,320
STUB='s32 func_1501E400() {\n    return 0;\n}'
DECLARATIONS='extern u8 D_800BEAC0;\nextern s32 D_800BEA08;\ns32 func_151F2CDC(void);\nvoid func_15080228(void);\n'
HEADER='''#include <ultra64.h>
extern u8 D_800C3A58,D_800C35EA[],D_800BEAC0,D_800C35C0[];
extern s32 D_800C35B0[],D_800C35B8[],D_800C3640[],D_800BEA08;
extern s16 D_800C3C8E;
s32 func_1501E1B4(s32);
s32 func_151F2CDC(void);
void func_15080228(void);
'''
SELECTED='''/* Preserve the previous sequence time, advance it and clamp at the limit. */
void func_1501E400(s32 slot) {
    if (D_800C3A58 != 0) D_800C3A58--;
    D_800C35B8[slot] = D_800C35B0[slot];
    if (D_800C35EA[slot] == 1) {
        func_1501E1B4(slot);
        if (slot != 0 || D_800BEAC0 == 0) {
            D_800C35B0[slot] = (u32)D_800C35B0[slot] + (u32)D_800BEA08;
        }
        if (D_800C35C0[slot] == 0 &&
            (u16)D_800C3C8E == D_800C35B8[slot] &&
            (u16)D_800C3C8E != D_800C35B0[slot]) {
            D_800C35B8[slot] = -1;
        }
        if (func_151F2CDC() == 1) func_15080228();
        if (D_800C35B0[slot] >= D_800C3640[slot]) {
            D_800C35B0[slot] = D_800C3640[slot];
        }
    }
}
'''
FROZEN={'conker/src/game/generated_49D30.c': '989c6b8a550009877ee7ba40682cccfd7ac98e260caf2c27b09cfad7d6471dd1', 'conker/build/src/game/generated_49D30.c.o': '595930db56a17660e992f2d81e61fc379b983c3604acff7ddd83221ead0fd112', 'conker/asm/49D30.s': '745b8aaa3c4871d74f21c6cf2479a494cb5e01bcb2df1486c8dbc56004c3ae41', 'conker/src/game_45B80.c': 'b6fc9842850d1eadf5cb272f7c9cee60c41b8f8f582c82b52c60602c6dc97a9a', 'conker/build/src/game_45B80.c.o': '6f93d458b6a4991ee00a8d815534c58451aad5b9864fff79c9ceaf0c9533fafc', 'conker/asm/nonmatchings/game_45B80/func_15019130.s': 'ce3f6e240cec6e4e8ee5c74e979f0a2ce91c14e364b7a24e3f0781f77e67b619', 'conker/src/libultra/audio/game_21FC90.c': 'f967e897506b329bbc9c57d75aba01fb3c97d87367932e44d69748f49e36bbe6', 'conker/asm/nonmatchings/libultra/audio/game_21FC90/func_151F2CDC.s': '190d7cbff4e097be3a42287e32301982dac85e711ca8166f09a9c638a8e90ab4', 'conker/src/game/generated_AD6B0.c': 'fb62a3c3ddbc53616fc4c508d347756575c64124f81f765476e82220caf149e5', 'conker/asm/AD6B0.s': '377529547d952c63e47036eecc0364186cdf6ed0e54c7b8d387dea6f9f327696', 'conker/build/conker.us.elf': '8db9baee64ea34d6e1f084a23e247f83994faa3b950b284f05ab406a252cedc3', 'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382', 'conker/build/conker.ld': '6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5', 'conker/retail_word_patches.us.csv': '6a6094f04735cb3127833e50b21f98c3374916605acd7aa79ccdebd80d22dfe7', 'conker/retail_layout.us.txt': 'eb8145837da425d7a55080459d22f11e21e1ac69e8b9d8ad5100ed5750d814f1', 'conker/Makefile': '8e676e04318f8645e6b277ed60ed9f221d8901a5e6a02efd279d478d46a615f8', 'conker/progress.csv': '7658d1ff6c2e3ae94567606200fcae0b7d08f5752a9ec0484108dc8056c8bdc0', 'conker/include/structs.h': 'e97e1a98ebcc522d82b52215078780102e0dd5e47d614bb3a4d4f3bbc94b9653', 'conker/include/variables.h': '02650aa4bf9fd66156f4e2cbd1e49156b9655eed68c3fae1cab15b1f99063a7d', 'conker/include/functions.h': 'f01a41af0bdb2caaaeb2c198be68d91515efb39de98a34ba190e090503d5f10b', 'conker/conker.us.yaml': 'd31a14128e74793a2cc5fcb7ca3a65abefc7cafe01528268b0e0af76f94bff1f', 'conker/symbol_addrs.us.txt': '1e59d193c5aefcc13d14b5083ee80ee977a4a9dcf54b75db8595b192a223bafa', 'conker/undefined_syms.us.txt': 'd678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e', 'conker/undefined_funcs.us.txt': '92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a', 'conker/undefined_syms_auto.txt': 'a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd', 'conker/undefined_funcs_auto.txt': 'e2090d98c3a5450afc4a78aafd1a7f1f5114bd43c7bddecb6e79434f20955329', 'conker/include/asm_processor_prelude.inc': 'c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d', 'conker/include/macro.inc': 'd7366200752da1051aba7bf98e361ca4af662fb5e22c7107455fc06a34969f1e', 'conker/include/macros.h': 'dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769', 'conker/include/magic.h': '92d976e6596839e490234cb4f827f3d1156a1d535c3022c7152162ed11d08eea', 'conker/include/2.0L/assert.h': '99d2e0c96e7453fae576f879b64ac1bd9ea5c031541c041ee6111bdacbefb844', 'conker/include/2.0L/ultra64.h': '334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d', 'conker/include/2.0L/PR/abi.h': '9efe7ee3c940ff96d46f936ad95e9cc52b879ee8c4b5c264cb8f42e1cf1ce1bf', 'conker/include/2.0L/PR/gbi.h': '155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6', 'conker/include/2.0L/PR/gs2dex.h': 'e9d3519bb328f9ac60b60d119650e1e4d652eaaddcd9db009f9cbd44daecb398', 'conker/include/2.0L/PR/gt.h': '05e50d177fe2ae42b02bcb384452317029b919f53403a5be1a3d64d47f2e1296', 'conker/include/2.0L/PR/gu.h': 'bc7761b1d0688b009d82a17776e21782842b652eb5b257088458b9fee8c63cff', 'conker/include/2.0L/PR/leo.h': 'e8ad69061d2fb4ee2acbd4c48184b6cebb05b0f3e56087d18d92c3061c0b0b47', 'conker/include/2.0L/PR/leoappli.h': '902916bad5d2056117570acebaa28cf57c46c2a22bb7cdd111d48ccacc249532', 'conker/include/2.0L/PR/libaudio.h': '53a127fef608e66f7883fc1d76c6eab609c27a127aebc89e89c87757a9ef97b9', 'conker/include/2.0L/PR/mbi.h': '8a0b32eb3cc7844a38b1b3ed1b160036b203efac0dc3c0275c53354423e40960', 'conker/include/2.0L/PR/n_libaudio.h': '223f1db0cf93edeb1e1f03af299eb7aeab8c619e78111d2f59dba31280d6a618', 'conker/include/2.0L/PR/n_libaudio_s_to_n.h': '6cad54fa2252fad7cb476882c819515ccec2d4120c94f6488f052cfdf261fddf', 'conker/include/2.0L/PR/os.h': 'e0af7328cadb2164b18c61717d916396741cf053d32b96b0dea06f6d664ff7e2', 'conker/include/2.0L/PR/os_ai.h': '933e7fe35c87702a2137b9c575022e18bd72e6ce11d8a44035a7ffbddf71aeb6', 'conker/include/2.0L/PR/os_cache.h': 'a9455e20523c6915f26c05d5d399763f1e051c01eac85c10911b7b3a65c0d5c9', 'conker/include/2.0L/PR/os_cont.h': '8b486936ae60b8a486e87489e77f40f557a0bf59fddf9c1adc5c97aa18388c0b', 'conker/include/2.0L/PR/os_convert.h': '6d98f19765d055a7857398cc6d7bd7a2ac2e93a4a858f1c27aa22361e4f892f1', 'conker/include/2.0L/PR/os_debug.h': '260815777abca616a9783db7a57cd94881586c84ef0adcce26516ba50476a523', 'conker/include/2.0L/PR/os_eeprom.h': 'f1f0f50895c4505c3420674504b7868ff85fe08df42433389deeb407e68c5163', 'conker/include/2.0L/PR/os_error.h': 'eae3744bf9ee921d089714e81590226b56fca5ca2f0ef866532eb788e829b120', 'conker/include/2.0L/PR/os_exception.h': '953bf8361f5e756010c45dc5f823c12183838bd723ec691a99a9fcf682e0698c', 'conker/include/2.0L/PR/os_flash.h': '7206e87e62400994347ff2d84bd5f563894c9c18cdbe34c0c5dd9fb2bcfa758f', 'conker/include/2.0L/PR/os_gbpak.h': 'c13616c011c214aef601f6249ae12465dcb8a6edfe68df27aaf6d086e09bbc8f', 'conker/include/2.0L/PR/os_gio.h': 'c0197b2afd220c07028a972ca0d5903af3064d48d8657935e3c57fc9a55f3b92', 'conker/include/2.0L/PR/os_host.h': '3b990c99a18cba34c3d8a856e3e99691125ec8338df42198fe469ee7bb9f9bcc', 'conker/include/2.0L/PR/os_internal.h': '0103aa8359ff23c9ef0b248b0721ea9df0c4557271e4146ac264d0d998b7280d', 'conker/include/2.0L/PR/os_internal_debug.h': '3e4f1baa87602ad77163c15990625e1fd3b9ae6cffcaabb3424dafec6d638bd0', 'conker/include/2.0L/PR/os_internal_error.h': 'ab7537aef80c392dcf0010bde8078f1b5d1973740bc6d51e1f4df3d757e28356', 'conker/include/2.0L/PR/os_internal_exception.h': 'b8124a51000cb0608a34c56d0242e0373d845f0bd28b6fb9b95f7dd21cf9ea65', 'conker/include/2.0L/PR/os_internal_gio.h': '032d50b58fd0f3d8831430a7125cd039efd1f56affdd8cbeb8777ab464ecba15', 'conker/include/2.0L/PR/os_internal_host.h': '83dda0b09da200ab1be91aeda90c2d0f52b7a282979391e05a9f4feeff1fffd1', 'conker/include/2.0L/PR/os_internal_reg.h': 'bbfe19f64f9383dfbd4d2ee17d2556ad8e3ae29f0803580637d0df59aa110f39', 'conker/include/2.0L/PR/os_internal_rsp.h': '77f2c0f58ebe5384970a553cabf850841a679e97dbd049926d13b0cb29f18c58', 'conker/include/2.0L/PR/os_internal_si.h': '2d88a8388c9211646c446bcd936606b038f80f53c10b9674f48ad6f6dede5acc', 'conker/include/2.0L/PR/os_internal_thread.h': 'f7700e0bd2c22fb6716d656435b7431c6701cbfd518f2908d13845d11be5ddd9', 'conker/include/2.0L/PR/os_internal_tlb.h': 'e67bca1ce07a917679abb4094b087ee70bd01399576fe9d7c4e85c82f642ccf8', 'conker/include/2.0L/PR/os_libc.h': 'fb2f4e113eee01c1953aee8efea3b6eb450ea97e2a5af23ba868ca1059d26b6e', 'conker/include/2.0L/PR/os_message.h': '241238eea37d71382b7a3c994d5837e4482d77548a4cbdaeb30b9f67013cdfb7', 'conker/include/2.0L/PR/os_motor.h': '68103a1c114bc7e7c6decf847a5ec3c346e23e9de9c7488ca6bbedc39dae8ec4', 'conker/include/2.0L/PR/os_pfs.h': '6b14a950c344f7396bc1e58c9b6612f061053bd41b868dba32e13d904a3effd7', 'conker/include/2.0L/PR/os_pi.h': '3e29b28b596036ffbe86afa8bcec1126511b78fe862297c48061f97d42b747ea', 'conker/include/2.0L/PR/os_rdp.h': 'a85b9def6f64bf25e6aeb064e1f2626f7b2d4d0ef0821d21844a9eefb19f6e21', 'conker/include/2.0L/PR/os_reg.h': '2a14f15494cf3754f1fe0149a8c8cab4806e843f3be6a30ad0c726443edef52d', 'conker/include/2.0L/PR/os_rsp.h': 'ede13674c9af25912778dd077c3dd709929d43fcb9f135f6465553d0f9e8fa26', 'conker/include/2.0L/PR/os_si.h': 'ffd228b5b0e450efcf1756d778d701be958cce724d1912792c31b3cac26f74b9', 'conker/include/2.0L/PR/os_system.h': 'bc8afaa3362ff4851feee1feed818dd009a13c3de19435a2e09656a64bf531d8', 'conker/include/2.0L/PR/os_thread.h': 'b7c244ead94962a0ebcb0787a589e7b398eaf02d8fc6538698c7353b08dcbf7d', 'conker/include/2.0L/PR/os_time.h': '21bd983fa7b11daa6a06c053b5e9cd7c08420dd20657c4fd61be434389af3342', 'conker/include/2.0L/PR/os_tlb.h': '9bbb49127e7e2600f6dcceffe4a1d38f31d463327cfa384ce930ddfa63223893', 'conker/include/2.0L/PR/os_version.h': '66c2147d22b8ccf5b2eb4967c90b27dfb8c83ce07e08382fcd408c8ca0bc3873', 'conker/include/2.0L/PR/os_vi.h': 'f59a0d52ab0e2bc2ca0b8226bc9b9c1e58d3a9eb8df8c4e6d45aaa6ac51fb2b6', 'conker/include/2.0L/PR/os_voice.h': 'c0fb2f6f8eb68a6608a2401f6a2f4a38d1c65b5d1ae944d0b5999502a9cc432f', 'conker/include/2.0L/PR/PRimage.h': '25bac64b4d176598cedb468b437b8ac7c13c4f255b8573d6aa60058f0b86be1c', 'conker/include/2.0L/PR/R4300.h': 'bb8a7702ef8dfe94c389f0c411a4f2346c506ea8766e85c332a44486a97b7b44', 'conker/include/2.0L/PR/ramrom.h': 'fa009dd8676f0af0ed0f0339dfe6ac2f67ad1a1b8675bdff42f71b937608a370', 'conker/include/2.0L/PR/rcp.h': '61e531c5c93e7b71c167ac1d3d08254f67e5009408defa4fe5b941674c5a6b8e', 'conker/include/2.0L/PR/rdb.h': 'ce4b388d5bf24b869eaee1919fd81a0655006b2327a6f521d954cfc0e546dfeb', 'conker/include/2.0L/PR/region.h': 'd1f523d36ab27f28eea0ffa0d87875661c14844d12c9bf0142932aa38af5869f', 'conker/include/2.0L/PR/rmon.h': 'b646e7e7febea89d9bfed1c1b58ebbe40a7d5378ccb50a1063cc1de5e8d3d07a', 'conker/include/2.0L/PR/sched.h': '40a7e05e5e774a3cbc015d44bb8225f469937de178bfe84cd1de9ef3c5ff7572', 'conker/include/2.0L/PR/sp.h': '6d4dd33330efa090dcf438a5a05b82a8fa54e94db78bc7c8f4d32f16a638de18', 'conker/include/2.0L/PR/sptask.h': '12b0a593a7013076fb60cf7224f0bdf25da554076e8b6f2ffe3999769e737dc5', 'conker/include/2.0L/PR/ucode.h': '50201220d2f811d64e5e11611ec835f0c3bf1a79c3045a2dc40f7e46012765a4', 'conker/include/2.0L/PR/ucode_debug.h': '715bccc464d8dbaa1a421007b6bab49a303bf5d8eb75ed74c184dddf59e67661', 'conker/include/2.0L/PR/ultraerror.h': '979fbca1aee61876a524ff3825cfb9c6a18ef28c99eb100e8b9b751b5c266b86', 'conker/include/2.0L/PR/ultralog.h': '52564b52560297920881f56e81894cfd9d9ed22b4cba1f9298eb1e10b1cda449', 'conker/include/2.0L/PR/ultratypes.h': '1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd', 'conker/include/2.0L/PR/uportals.h': '76548ed2614bedba9c9236883ab236251a30995b12f96da1e7a8eee8cb1eca4e', 'conker/include/libc/math.h': 'e13f7c37cc5ea7cf75a93c4b45c6b96f321d67a70e8cdbfbba0edb7de0c3e226', 'conker/include/libc/stdarg.h': '759498a7844671810843e0715215b1ddb3b402d2465e96aa19b65494d71ac2b4', 'conker/include/libc/stddef.h': 'e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721', 'conker/include/libc/stdio.h': '060f3f7b91cde2ab969d3d04b40ed57ff2b61167ece52309b64f4c6ab9ebfae1', 'conker/include/libc/stdlib.h': '181e9dc382377ed777654ddbf8393f9244ac9dcee66f58e78b43d0dea53ebbe9', 'conker/include/libc/string.h': 'ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5', 'ido/ido5.3_recomp/cc': 'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a', 'ido/ido5.3_recomp/cfe': 'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9', 'ido/ido5.3_recomp/ugen': 'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d', 'ido/ido5.3_recomp/uopt': '23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d', 'tools/experiments/game_active_record_lookup_match.py': '977f7c1f86fbccb40daf204c533ade0d3b1f116f597e383bfa5297f8561f5224', 'tools/experiments/game_remaining_donor_candidates.py': '15cec3a86a8b4e5954d5efbc900f5e9d047000672845896633fbe389874de0a1', 'tools/experiments/game_embedded_dual_phase_position_update_match.py': '58d30d03fd8ec1e4cba3bcc74e3224b106d81372c143c9496baea4a5d6435305', 'tools/experiments/game_selector_table_payload_match.py': '00945692656e7199bab6c7c6a7cd1ca8fd8208fce8f2d7a3d4ed31c164a58f6a', 'tools/pad_c_object.py': 'd5e11a47650cbda9907672c381534ced6aac681d1f1333bac129038a685d9362', 'tools/pad_generated_object.py': 'ad513832cf991f3f04177faf8b22b1b434404d54168cd512e574e1921c349809', 'tools/asm-processor/asm_processor.py': 'b3d9afebcf8bcbf5bcb75a8baa6808dbd5036771aa41d3b1143175aa0c965911'}
RETAIL_SHA='2881f118369cab4d1278c20883d0e10c6e4ab10ff8d53e686cdc988b598376ca'
RAW_SHA='4c77b7b86a6e395a84b28d1701d2cae352fd03374585f9dfd70f81581502a94a'
BINDINGS={4: [('R_MIPS_HI16', 'D_800C3A58')], 8: [('R_MIPS_LO16', 'D_800C3A58')], 20: [('R_MIPS_HI16', 'D_800C35B8')], 24: [('R_MIPS_LO16', 'D_800C35B8')], 44: [('R_MIPS_HI16', 'D_800C35B0')], 48: [('R_MIPS_LO16', 'D_800C35B0')], 64: [('R_MIPS_HI16', 'D_800C35EA')], 76: [('R_MIPS_LO16', 'D_800C35EA')], 104: [('R_MIPS_26', 'func_1501E1B4')], 132: [('R_MIPS_HI16', 'D_800BEAC0')], 136: [('R_MIPS_LO16', 'D_800BEAC0')], 144: [('R_MIPS_HI16', 'D_800BEA08')], 148: [('R_MIPS_LO16', 'D_800BEA08')], 164: [('R_MIPS_HI16', 'D_800C35C0')], 172: [('R_MIPS_LO16', 'D_800C35C0')], 176: [('R_MIPS_HI16', 'D_800C3C8E')], 188: [('R_MIPS_LO16', 'D_800C3C8E')], 228: [('R_MIPS_26', 'func_151F2CDC')], 256: [('R_MIPS_26', 'func_15080228')], 272: [('R_MIPS_HI16', 'D_800C3640')], 280: [('R_MIPS_LO16', 'D_800C3640')]}
sha=lambda b:hashlib.sha256(b).hexdigest()

def source_states(live):
    old=(ROOT/BUILD/'frozen'/SOURCE).read_text()
    if sha((ROOT/BUILD/'frozen'/SOURCE).read_bytes())!=FROZEN[SOURCE]:raise ValueError('Sequence-time frozen source changed')
    if old.count(STUB)!=1 or old.count('s32 func_1501E400();')!=1:raise ValueError('Sequence-time predecessor interface changed')
    new=old.replace('s32 func_1501E400();','void func_1501E400(s32);').replace(STUB,DECLARATIONS+SELECTED.rstrip())
    if live not in(old,new):raise ValueError('Sequence-time live source changed')
    return old,new,live==new

def caller_states(live):
    old=(ROOT/BUILD/'frozen'/CALLER_SOURCE).read_text()
    if old.count('s32 func_1501E400(s32);')!=1:raise ValueError('Sequence-time caller prototype changed')
    new=old.replace('s32 func_1501E400(s32);','void func_1501E400(s32);')
    if live not in(old,new):raise ValueError('Sequence-time live caller changed')
    return old,new,live==new

def freeze(root,out):
    allowed={SOURCE,OBJECT,CALLER_SOURCE,ELF}
    for n,h in FROZEN.items():
        p=out/'frozen'/n
        if not p.exists():
            data=(root/n).read_bytes()
            if sha(data)!=h:raise ValueError('Sequence-time initial input changed: '+n)
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        if sha(p.read_bytes())!=h or n not in allowed and sha((root/n).read_bytes())!=h:raise ValueError('Sequence-time frozen input changed: '+n)
    return FROZEN

def payload(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{a-start:v for a,v in rs.items()if start<=a<start+size}

def checked(raw,refs):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Sequence-time raw body/bindings changed')
    return raw,refs

def padded(root,out,obj,label,generated=False):
    dest=out/(label+'.o');assembly=out/(label+'.s')
    if generated:text=emit_padded_assembly(obj,root/ASM,filename=OWNER,word_patches_path=root/GUARDS)
    else:
        from tools import pad_generated_object
        sys.modules.setdefault('pad_generated_object',pad_generated_object)
        from tools.pad_c_object import emit_padded_assembly as emit
        text=emit(obj,root/'conker/retail_layout.us.txt',OWNER,word_patches_path=root/GUARDS)
    assembly.write_text(text)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(dest),str(assembly)],check=True,capture_output=True)
    return dest

def strict_image(before,actual,truth):
    if sha(before)!=FROZEN[ELF] or len(truth)!=SIZE or sha(truth)!=RETAIL_SHA:raise ValueError('Sequence-time strict inputs changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);wanted[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,_ in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Sequence-time predecessor extent changed')
    struct.pack_into('>I',wanted,rows[0][0]+8,SIZE)
    if actual!=wanted:raise ValueError('Sequence-time entire image differs from the body/extent prediction')
    return sum(a!=b for a,b in zip(before,actual))

def make_shadow(root,out,proposal,wanted,compact,source,objname,label,diagnostics,unroll):
    shadow=out/(label+'-shadow');conker=root/'conker';target=shadow/objname.removeprefix('conker/build/');target.parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target.relative_to(conker).as_posix()],cwd=conker,capture_output=True,text=True,check=True)
    (out/(label+'-plan.txt')).write_text(plan.stdout+plan.stderr);commands=[];cc=0;expected=diagnostic_rows(diagnostics)
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown sequence-time Make command')
        args=[proposal.relative_to(conker).as_posix()if a==source.removeprefix('conker/')else a for a in args];redirect=None
        if '>'in args:
            if args.count('>')!=1 or args[-2]!='>':raise ValueError('Unknown sequence-time Make redirect')
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        p=subprocess.run(args,cwd=conker,capture_output=True,text=True);is_cc=args[0]=='../ido/ido5.3_recomp/cc'
        if p.returncode or diagnostic_rows(p.stderr)!=(expected if is_cc else Counter())or(redirect is None and p.stdout):raise ValueError(p.stdout+p.stderr)
        if is_cc:
            cc+=1
            if args.count('-O2')!=1 or args.count('-g3')!=1 or ('-Wo,-loopunroll,0'in args)!=unroll:raise ValueError('Sequence-time Make compiler profile changed')
        if redirect is not None:redirect.write_text(p.stdout)
        commands.append(args)
    if len(commands)!=3 or cc!=1 or target.read_bytes()!=wanted.read_bytes():raise ValueError('Sequence-time actual Make owner differs')
    count=same_functions(compact,Path(str(target)+'.compact'))
    (out/(label+'-commands.json')).write_text(json.dumps(commands,indent=2)+'\n')
    return dict(commands=3,functions=count,padded_object_equal=True,diagnostics=sum(expected.values()),inherited_Make_warnings=plan.stderr)

def caller(root,out,installed):
    before,after,live=caller_states((root/CALLER_SOURCE).read_text())
    if live!=installed:raise ValueError('Sequence-time caller phase differs')
    old,od=compile_default(root,out,before,'caller-old');new,nd=compile_default(root,out,after,'caller-new')
    if diagnostic_rows(od)!=diagnostic_rows(nd)or sum(diagnostic_rows(nd).values())!=3:raise ValueError('Sequence-time caller diagnostics changed')
    count=same_functions(old,new)
    if normalized_pools(old)!=normalized_pools(new):raise ValueError('Sequence-time caller pools changed')
    owners=[]
    for label,obj in(('caller-old',old),('caller-new',new)):
        assembly=out/(label+'-padded.s');owner=out/(label+'-padded.o')
        subprocess.run([sys.executable,str(root/'tools/pad_c_object.py'),str(obj),str(root/'conker/retail_layout.us.txt'),'game_45B80',str(assembly),'--word-patches',str(root/GUARDS)],check=True,capture_output=True)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(owner),str(assembly)],check=True,capture_output=True);owners.append(owner)
    if owners[0].read_bytes()!=owners[1].read_bytes()or owners[0].read_bytes()!=(root/CALLER_OBJECT).read_bytes():raise ValueError('Sequence-time caller entire object changed')
    proposal=out/'proposed-caller.c';proposal.write_text(after)
    recipe=make_shadow(root,out,proposal,owners[1],new,CALLER_SOURCE,CALLER_OBJECT,'caller-Make',nd,False)
    return dict(functions=count,diagnostics=3,padded_object_unchanged=True,sha256=sha(owners[1].read_bytes()),actual_Make=recipe)

def census(root):
    data=(root/'conker/conker.us.bin').read_bytes();calls=[];values=[]
    for i,(w,)in enumerate(struct.iter_unpack('>I',data)):
        if w>>26 in(2,3)and ENTRY<=((w&0x3FFFFFF)<<2|0x10000000)<ENTRY+SIZE:calls.append(i*4)
        if ENTRY<=w<ENTRY+SIZE:values.append(i*4)
    if calls!=[0x46610,0x4B848]or values:raise ValueError('Sequence-time aligned caller/address census changed')
    return dict(direct_calls=calls,address_values=[],interface='void(s32 slot)',both_callers_pass_zero_and_ignore_return=True)

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text());caller_report=caller(root,out,installed)
    old,od=compile_owner(root,out,before,'predecessor-owner');new,nd=compile_owner(root,out,after,'qualified-owner');single,sd=compile_owner(root,out,HEADER+SELECTED,'isolated')
    if od or nd or sd:raise ValueError('Sequence-time owner diagnostics changed')
    raw,refs=checked(*payload(new))
    if payload(single)!=(raw,refs):raise ValueError('Sequence-time isolated body differs')
    syms={n:int(n.split('_')[1],16)for rows in refs.values()for _,n in rows};truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE]
    if struct.pack('>80I',*bound_blob(raw,refs,syms))!=truth:raise ValueError('Sequence-time direct C differs from retail')
    raw_neighbors=same_functions(old,new,(FUNCTION,))
    register_rows=[struct.unpack('>6I',sections(p)['.reginfo'][1])for p in(old,new,single)]
    if register_rows[1]!=tuple(register_rows[0][i]|register_rows[2][i]if i<5 else register_rows[0][i]for i in range(6)):raise ValueError('Sequence-time register union changed')
    if normalized_pools(old)!=normalized_pools(new):raise ValueError('Sequence-time raw pools changed')
    old_pad=padded(root,out,old,'predecessor-padded');new_pad=padded(root,out,new,'qualified-padded');independent=padded(root,out,new,'independent-padded',True)
    if same_functions(new_pad,independent)!=57 or normalized_pools(new_pad)!=normalized_pools(independent):raise ValueError('Sequence-time independent padders differ')
    neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or payload(new_pad)!=(raw,refs):raise ValueError('Sequence-time padded pools/body changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes():raise ValueError('Sequence-time live owner differs')
    proposal=out/'proposed-owner.c';proposal.write_text(after)
    recipe=make_shadow(root,out,proposal,new_pad,new,SOURCE,OBJECT,'owner-Make',nd,True)
    with patch.multiple(linker,FILENAME=OWNER,OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        old_elf=linker.link_image(root,out,old_pad,'predecessor-image');new_elf=linker.link_image(root,out,new_pad,'qualified-image')
    if(root/ELF).read_bytes()!=(new_elf if installed else old_elf).read_bytes():raise ValueError('Sequence-time live ELF differs')
    delta=strict_image(old_elf.read_bytes(),new_elf.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in b if a[n]!=b[n]]!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>80I',truth)):raise ValueError('Sequence-time complete function/address census changed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Sequence-time protected data changed')
    report=dict(words=80,slot_words=80,frame=40,guards=0,direct_C=True,raw_neighbors=raw_neighbors,padded_neighbors=neighbors,diagnostics=0,actual_Make=recipe,caller=caller_report,register_union_exact=True,source_installed=installed,frozen_inputs=len(FROZEN),strict_changed_bytes=delta,exclusions=0,metadata_reorders=0,functions=len(a),all_addresses_fixed=True,changed_bodies=[FUNCTION],protected_data=data,ELF_sha256=sha(new_elf.read_bytes()),owner_sha256=sha(new_pad.read_bytes()),guard_sha256=sha((root/GUARDS).read_bytes()),registry=census(root))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,raw=raw,refs=refs,qualified_object=new_pad,predecessor_elf=old_elf,qualified_elf=new_elf)

if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
