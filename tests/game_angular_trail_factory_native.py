"""Independent host-native control for the angular localized-trail factory."""
from pathlib import Path
import json
import os
import subprocess


def qualify(output):
    source = output / "native_harness_v1.c"
    profiles = []
    environment = dict(os.environ)
    environment["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    for optimization in ("O0", "O2", "O3"):
        executable = output / ("native-v1-" + optimization)
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
            "optimization": optimization, "cases": row["cases"], "UBSan_clean": True,
            "compiler_stderr": compiled.stderr, "runtime_stderr": ran.stderr,
        })
    report = {
        "success": True, "private_only": True, "matching_credit": 0,
        "profiles": profiles, "cases_per_profile": 256, "total_executions": 768,
        "descriptor_natural_bytes": 76, "angular_required_bytes": 8,
        "localized_input_natural_bytes": 68, "localized_input_required_bytes": 65,
        "localized_private_padding_bytes": ["0x35", "0x36", "0x37"],
        "scratch_visible_bytes": 12,
        "all18_provider_arguments_and_complete_descriptor_scratch_snapshots": True,
        "live_descriptor_after_direction_and_provider": True,
        "all256_target_channels_with_endian_neutral_repeated_input_bytes": True,
        "whole_descriptor_fences": True, "independent_native_control": True, "UBSan_clean": True,
    }
    (output / "private-native-v1.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    output = Path.cwd() / "conker/build/game-angular-trail-factory-15153F18-match"
    print(json.dumps(qualify(output), indent=2))
