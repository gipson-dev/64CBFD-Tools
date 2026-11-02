from pathlib import Path
import json
import os
import subprocess


def qualify(output):
    source = output / "native_harness_v2.c"
    profiles = []
    environment = dict(os.environ)
    environment["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    for optimization in ("O0", "O2", "O3"):
        executable = output / ("native-v2-" + optimization)
        command = [
            "gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
            "-fno-strict-aliasing", "-ffp-contract=off", "-fsanitize=undefined",
            "-fno-sanitize-recover=all", "-" + optimization,
            "-o", str(executable), str(source),
        ]
        compiled = subprocess.run(command, capture_output=True, text=True)
        assert compiled.returncode == 0, (optimization, compiled.stdout, compiled.stderr)
        ran = subprocess.run([str(executable)], capture_output=True, text=True, env=environment)
        assert ran.returncode == 0, (optimization, ran.stdout, ran.stderr)
        row = json.loads(ran.stdout)
        assert row == {"success": True, "cases": 256}
        profiles.append({
            "optimization": optimization,
            "cases": row["cases"],
            "UBSan_clean": True,
            "compiler_stderr": compiled.stderr,
            "runtime_stderr": ran.stderr,
        })
    report = {
        "success": True,
        "private_only": True,
        "matching_credit": 0,
        "profiles": profiles,
        "cases_per_profile": 256,
        "total_executions": 768,
        "input_natural_bytes": 68,
        "input_required_bytes": 65,
        "input_private_padding_bytes": ["0x35", "0x36", "0x37"],
        "transform_natural_bytes": 44,
        "transform_required_bytes": 41,
        "transform_private_padding_bytes": ["0x1", "0x2", "0x3"],
        "scratch_visible_bytes": 12,
        "all18_provider_arguments_and_complete_snapshots": True,
        "live_input_after_transform_and_provider": True,
        "count_RNG_mutation_is_guest_only_due_to_C_operand_evaluation_order": True,
        "all256_target_channels_with_endian_neutral_repeated_input_bytes": True,
        "whole_input_transform_fences": True,
        "independent_native_control": True,
        "UBSan_clean": True,
    }
    (output / "private-native-v2.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    print(json.dumps(qualify(Path(__file__).parent), indent=2), flush=True)
