from __future__ import annotations

import argparse
import shutil
from pathlib import Path

UPSTREAM_SHA = "0eb16763761e46f55c6223439ca1ad20216bc4ab"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def patch_build_gradle(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'applicationId "com.tumuyan.ncnn.realsr"',
        'applicationId "com.bimachakti.whiteflood"',
        "applicationId",
    )
    text = replace_once(text, "versionCode 52", "versionCode 1", "versionCode")
    text = replace_once(text, "versionName '1.13.2'", "versionName '0.1.0'", "versionName")
    text = replace_once(
        text,
        'resValue "string", "app_name", "RealSR Debug"',
        'resValue "string", "app_name", "WhiteFlood Pilot"',
        "debug app name",
    )
    text = replace_once(
        text,
        'outputFileName = "RealSR-NCNN-Android-GUI-armv8a-${variant.versionName}.apk"',
        'outputFileName = "WhiteFlood-Android-Pilot-${variant.versionName}.apk"',
        "APK filename",
    )
    path.write_text(text, encoding="utf-8")


def patch_main_activity(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'selectCommand = mySharePerferences.getInt("selectCommand", 2);',
        'selectCommand = mySharePerferences.getInt("selectCommand", 0);',
        "default preset",
    )

    old_commands = '''        Set<String> hiddenPrograms = mySharePerferences.getStringSet("hiddenPrograms", new HashSet<String>());
        command = commandListManager.getFilteredCommands(hiddenPrograms);
        String[] displayLabels = commandListManager.getFilteredLabels(hiddenPrograms, useCustomLabel);

        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, displayLabels);
        spinner.setAdapter(adapter);'''
    new_commands = '''        // WhiteFlood Android pilot intentionally exposes only two photo presets.
        // The underlying upstream engine remains pinned and unchanged.
        command = new String[] {
                "./realsr-ncnn -i input.png -o output.png -m models-Real-ESRGAN-SourceBook -s 2",
                "./realsr-ncnn -i input.png -o output.png -m models-Real-ESRGANv3-general -s 4"
        };
        String[] displayLabels = new String[] {
                "2× Photo · hemat",
                "4× Photo · detail"
        };

        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, R.layout.wf_spinner_item, displayLabels);
        adapter.setDropDownViewResource(R.layout.wf_spinner_item);
        spinner.setAdapter(adapter);'''
    text = replace_once(text, old_commands, new_commands, "WhiteFlood preset block")

    text = replace_once(
        text,
        '        showImage(titleFile, getString(R.string.default_log));',
        '        imageView.setVisibility(View.GONE);\n        logTextView.setText("Pilih foto untuk mulai. Pemrosesan tetap lokal di perangkat.");',
        "initial preview",
    )
    path.write_text(text, encoding="utf-8")


def patch_theme(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "@color/purple_500", "#EF5B73", "primary color")
    text = replace_once(text, "@color/purple_700", "#0D1014", "primary variant")
    text = replace_once(text, "@color/teal_200", "#61BD9B", "secondary color")
    text = replace_once(text, "@color/teal_700", "#469579", "secondary variant")
    path.write_text(text, encoding="utf-8")


def apply(upstream_root: Path, overlay_root: Path) -> None:
    app_root = upstream_root / "RealSR-NCNN-Android-GUI" / "app"
    if not app_root.is_dir():
        raise RuntimeError(f"Upstream Android app not found: {app_root}")

    patch_build_gradle(app_root / "build.gradle")
    patch_main_activity(
        app_root
        / "src/main/java/com/tumuyan/ncnn/realsr/MainActivity.java"
    )
    patch_theme(app_root / "src/main/res/values/themes.xml")

    source_res = overlay_root / "res"
    target_res = app_root / "src/main/res"
    if not source_res.is_dir():
        raise RuntimeError(f"Overlay resources not found: {source_res}")
    shutil.copytree(source_res, target_res, dirs_exist_ok=True)

    layout = target_res / "layout/activity_main.xml"
    spinner = target_res / "layout/wf_spinner_item.xml"
    if not layout.is_file() or not spinner.is_file():
        raise RuntimeError("WhiteFlood UI resources were not copied")

    required_ids = (
        "btn_open",
        "btn_setting",
        "btn_run",
        "btn_save",
        "spinner",
        "serarch_view",
        "photo_view",
        "tv_log",
    )
    layout_text = layout.read_text(encoding="utf-8")
    missing = [item for item in required_ids if f"@+id/{item}" not in layout_text]
    if missing:
        raise RuntimeError(f"Layout missing upstream-required ids: {missing}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--overlay-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.upstream_root.resolve(), args.overlay_root.resolve())
    print(f"WhiteFlood overlay applied to upstream {UPSTREAM_SHA}")
