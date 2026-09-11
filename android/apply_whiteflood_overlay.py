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
    text = replace_once(text, "versionCode 52", "versionCode 3", "versionCode")
    text = replace_once(text, "versionName '1.13.2'", "versionName '0.1.2'", "versionName")
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

    old_initial_preview = '''        titleFile = new File(dir, "img/realsr.png");
        showImage(titleFile, getString(R.string.default_log));'''
    new_initial_preview = '''        titleFile = new File(dir, "img/realsr.png");
        imageView.setVisibility(View.VISIBLE);
        logTextView.setText("Pilih foto untuk mulai. Pemrosesan tetap lokal di perangkat.");'''
    text = replace_once(text, old_initial_preview, new_initial_preview, "initial preview")

    old_picker = '''            } else {

                Intent i = new Intent(Intent.ACTION_PICK);
                i.setType("image/*");
                startActivityForResult(i, SELECT_IMAGE);
            }'''
    new_picker = '''            } else {
                Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT);
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.setType("image/*");
                i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                startActivityForResult(i, SELECT_IMAGE);
            }'''
    text = replace_once(text, old_picker, new_picker, "single photo picker")

    old_uri_loader = '''    private boolean whiteFileFromUri(Uri uri, String path) {
        if (uri != null) {
            try {
                InputStream in = getContentResolver().openInputStream(uri);
                if (null != in)
                    saveInputImage(in, path);
                else
                    Toast.makeText(this, R.string.share_is_null, Toast.LENGTH_SHORT).show();
                return true;
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
        return false;
    }'''
    new_uri_loader = '''    private boolean whiteFileFromUri(Uri uri, String path) {
        if (uri == null) {
            return false;
        }
        try {
            InputStream in = getContentResolver().openInputStream(uri);
            if (in == null) {
                logTextView.setText("Foto tidak dapat dibuka. Pilih JPG atau PNG lain.");
                Toast.makeText(this, "Foto tidak dapat dibuka", Toast.LENGTH_SHORT).show();
                return false;
            }
            boolean saved = saveInputImage(in, path);
            if (!saved) {
                logTextView.setText("Gagal memuat foto ke penyimpanan lokal aplikasi.");
                Toast.makeText(this, "Gagal memuat foto", Toast.LENGTH_SHORT).show();
            }
            return saved;
        } catch (Exception e) {
            Log.e("whiteFileFromUri", "Failed to materialize selected image", e);
            logTextView.setText("Gagal membaca foto yang dipilih.");
            Toast.makeText(this, "Gagal membaca foto", Toast.LENGTH_SHORT).show();
            return false;
        }
    }'''
    text = replace_once(text, old_uri_loader, new_uri_loader, "content URI materialization")

    old_single_result = '''            if (requestCode == SELECT_IMAGE && null != url) {
                deleteFile(inputFile);
                inputFileName = getFileName(url, this).replaceFirst("\\\\.[^.]+$", "");
                Log.i("input file name", inputFileName);
                InputStream in;

                try {
                    in = getContentResolver().openInputStream(url);
                    if (null != in)
                        saveInputImage(in, "");
                    else
                        Toast.makeText(this, "input == null", Toast.LENGTH_SHORT).show();
                } catch (Exception e) {
                    e.printStackTrace();
                    return;
                }
            } else if (requestCode == SELECT_MULTI_IMAGE) {'''
    new_single_result = '''            if (requestCode == SELECT_IMAGE && null != url) {
                deleteFile(inputFile);
                String selectedName = getFileName(url, this);
                inputFileName = selectedName == null
                        ? "foto"
                        : selectedName.replaceFirst("\\\\.[^.]+$", "");
                Log.i("input file name", inputFileName);

                if (!whiteFileFromUri(url, "")) {
                    imageView.setVisibility(View.VISIBLE);
                    return;
                }
            } else if (requestCode == SELECT_MULTI_IMAGE) {'''
    text = replace_once(text, old_single_result, new_single_result, "single picker result")

    old_first_read = '''            if ((read = in.read(buffer)) != -1) {
                if (prePng) {
                    match = PreprocessToPng.match(buffer);
                    if (match >= 0) {
                        file = new File(dir + "/tmp");
                        if (file.exists()) {
                            file.delete();
                        }
                    }
                }
            }

            file.createNewFile();
            OutputStream outStream = new FileOutputStream(file);
            outStream.write(buffer, 0, read);'''
    new_first_read = '''            read = in.read(buffer);
            if (read < 0) {
                in.close();
                runOnUiThread(() -> logTextView.setText("File foto kosong atau tidak dapat dibaca."));
                return false;
            }
            if (prePng) {
                match = PreprocessToPng.match(buffer);
                if (match >= 0) {
                    file = new File(dir + "/tmp");
                    if (file.exists()) {
                        file.delete();
                    }
                }
            }

            file.createNewFile();
            OutputStream outStream = new FileOutputStream(file);
            outStream.write(buffer, 0, read);'''
    text = replace_once(text, old_first_read, new_first_read, "empty input guard")

    old_update_tail = '''        updateImage(dir + "/input.png", getString(R.string.lr), false);
        return true;
    }'''
    new_update_tail = '''        File materializedInput = new File(dir + "/input.png");
        if (inputOneImage && !inputIsGifAnimation
                && (!materializedInput.isFile() || materializedInput.length() <= 0)) {
            runOnUiThread(() -> {
                imageView.setVisibility(View.VISIBLE);
                logTextView.setText("Foto gagal dimuat. Coba JPG/PNG lain atau pilih ulang foto.");
            });
            return false;
        }

        updateImage(dir + "/input.png", getString(R.string.lr), false);
        return true;
    }'''
    text = replace_once(text, old_update_tail, new_update_tail, "materialized input validation")

    text = replace_once(
        text,
        'imageView.setImage(ImageSource.uri(file.listFiles()[0].getPath()));',
        'imageView.setImage(ImageSource.uri(Uri.fromFile(file.listFiles()[0])));',
        "directory preview URI",
    )
    text = replace_once(
        text,
        'imageView.setImage(ImageSource.uri(path));',
        'imageView.setImage(ImageSource.uri(Uri.fromFile(file)));',
        "file preview URI",
    )

    old_run_start = '''        findViewById(R.id.btn_run).setOnClickListener(view -> {
            menuProgress.setTitle("");
            {'''
    new_run_start = '''        findViewById(R.id.btn_run).setOnClickListener(view -> {
            boolean missingInput = !inputFile.exists()
                    || (inputFile.isFile() && inputFile.length() <= 0)
                    || (inputFile.isDirectory()
                        && (inputFile.listFiles() == null || inputFile.listFiles().length == 0));
            if (missingInput) {
                logTextView.setText("Pilih foto yang berhasil dimuat sebelum menjalankan Upscale.");
                Toast.makeText(this, "Pilih foto dulu", Toast.LENGTH_SHORT).show();
                return;
            }

            menuProgress.setTitle("");
            {'''
    text = replace_once(text, old_run_start, new_run_start, "upscale input guard")

    old_output_delete = '''                deleteFile(outputFile);
                if (inputIsGifAnimation) {'''
    new_output_delete = '''                if (cmd.toString().startsWith("./realsr-ncnn")) {
                    File engineFile = new File(dir, "realsr-ncnn");
                    if (!engineFile.isFile() || engineFile.length() <= 0) {
                        logTextView.setText("Engine Upscale belum siap. Tutup lalu buka kembali aplikasi agar asset lokal dipasang ulang.");
                        Toast.makeText(this, "Engine Upscale tidak ditemukan", Toast.LENGTH_SHORT).show();
                        return;
                    }

                    String requiredModel = "";
                    if (cmd.toString().contains("models-Real-ESRGAN-SourceBook")) {
                        requiredModel = "models-Real-ESRGAN-SourceBook";
                    } else if (cmd.toString().contains("models-Real-ESRGANv3-general")) {
                        requiredModel = "models-Real-ESRGANv3-general";
                    }

                    if (!requiredModel.isEmpty()) {
                        File modelDir = new File(dir, requiredModel);
                        File[] modelFiles = modelDir.listFiles();
                        if (!modelDir.isDirectory() || modelFiles == null || modelFiles.length == 0) {
                            logTextView.setText("Model Upscale lokal tidak lengkap: " + requiredModel + ". Instal ulang APK agar asset dipulihkan.");
                            Toast.makeText(this, "Model Upscale tidak lengkap", Toast.LENGTH_SHORT).show();
                            return;
                        }
                    }
                }

                deleteFile(outputFile);
                if (inputIsGifAnimation) {'''
    text = replace_once(text, old_output_delete, new_output_delete, "engine/model preflight")

    old_execution_chain = '''        CommandBuilder builder = new CommandBuilder();
        builder.append(finalCmd);

        if (save) {
            String export_cmd = saveOutputCmd();
            if (inputIsGifAnimation)
                builder.append(";./magick -delay " + inputGifDelay + " output.png/* -loop 0 " + ShellUtils.escapeShellArgument(outputSavePath));
            else
                builder.append(";" + export_cmd);
        } else {
            outputSavePath = "";
        }'''
    new_execution_chain = '''        CommandBuilder builder = new CommandBuilder();
        builder.append(finalCmd);

        boolean whiteFloodSingleOutput = run_ncnn && !inputIsGifAnimation
                && !export_dir && cmd.contains("output.png");
        if (whiteFloodSingleOutput) {
            builder.append("&& { test -s output.png || { echo \\\"WhiteFlood: engine selesai tanpa membuat output.png.\\\"; exit 74; }; }");
        }

        if (save) {
            String export_cmd = saveOutputCmd();
            if (inputIsGifAnimation)
                builder.append("&& ./magick -delay " + inputGifDelay + " output.png/* -loop 0 " + ShellUtils.escapeShellArgument(outputSavePath));
            else
                builder.append("&& " + export_cmd);
        } else {
            outputSavePath = "";
        }'''
    text = replace_once(text, old_execution_chain, new_execution_chain, "engine/output/save command chain")

    old_completion = '''                    String logResult = progressLogHelper.getCompletionSummary(success, modelName, run_ncnn);

                    if (bench_mark_mode) {'''
    new_completion = '''                    String logResult = progressLogHelper.getCompletionSummary(success, modelName, run_ncnn);
                    if (!success && run_ncnn && !inputIsGifAnimation) {
                        File expectedOutput = new File(dir, "output.png");
                        if (!expectedOutput.isFile() || expectedOutput.length() <= 0) {
                            logResult = "\\nWhiteFlood: Upscale berhenti sebelum file hasil dibuat. Detail engine ada di log di atas.\\n"
                                    + logResult;
                        }
                    }

                    if (bench_mark_mode) {'''
    text = replace_once(text, old_completion, new_completion, "user-facing runtime failure summary")

    path.write_text(text, encoding="utf-8")


def patch_image_processor(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old_exit = '''            int exitCode = currentProcess.waitFor();
            success = (exitCode == 0);
            Log.d(TAG, "Process finished with exit code: " + exitCode);'''
    new_exit = '''            int exitCode = currentProcess.waitFor();
            success = (exitCode == 0);
            if (!success) {
                String exitLine = "WhiteFlood: proses berhenti dengan exit code " + exitCode;
                callback.onProgress(exitLine);
                resultBuilder.append(exitLine).append("\\n");
            }
            Log.d(TAG, "Process finished with exit code: " + exitCode);'''
    text = replace_once(text, old_exit, new_exit, "process exit-code diagnostics")
    path.write_text(text, encoding="utf-8")


def patch_setting_activity(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'setTitle(getResources().getText(R.string.setting));',
        'setTitle("Setelan WhiteFlood");',
        "settings title",
    )
    path.write_text(text, encoding="utf-8")


def patch_theme(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "@color/purple_500", "#EF5B73", "primary color")
    text = replace_once(text, "@color/purple_700", "#0D1014", "primary variant")
    text = replace_once(text, "@color/teal_200", "#61BD9B", "secondary color")
    text = replace_once(text, "@color/teal_700", "#469579", "secondary variant")
    path.write_text(text, encoding="utf-8")


def patch_manifest(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'android:icon="@mipmap/ic_launcher"',
        'android:icon="@drawable/wf_logo"',
        "launcher icon",
    )
    text = replace_once(
        text,
        'android:roundIcon="@mipmap/ic_launcher_round"',
        'android:roundIcon="@drawable/wf_logo"',
        "round launcher icon",
    )
    path.write_text(text, encoding="utf-8")


def copy_whiteflood_logo(app_root: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    source = repo_root / "review-temp" / "WhiteFlood_BG_Remover_App" / "logo.png"
    if not source.is_file():
        raise RuntimeError(f"WhiteFlood logo from README not found: {source}")

    target = app_root / "src/main/res/drawable-nodpi/wf_logo.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def apply(upstream_root: Path, overlay_root: Path) -> None:
    app_root = upstream_root / "RealSR-NCNN-Android-GUI" / "app"
    if not app_root.is_dir():
        raise RuntimeError(f"Upstream Android app not found: {app_root}")

    patch_build_gradle(app_root / "build.gradle")
    patch_main_activity(
        app_root
        / "src/main/java/com/tumuyan/ncnn/realsr/MainActivity.java"
    )
    patch_image_processor(
        app_root
        / "src/main/java/com/tumuyan/ncnn/realsr/ImageProcessor.java"
    )
    patch_setting_activity(
        app_root
        / "src/main/java/com/tumuyan/ncnn/realsr/SettingActivity.java"
    )
    patch_theme(app_root / "src/main/res/values/themes.xml")
    patch_manifest(app_root / "src/main/AndroidManifest.xml")

    source_res = overlay_root / "res"
    target_res = app_root / "src/main/res"
    if not source_res.is_dir():
        raise RuntimeError(f"Overlay resources not found: {source_res}")
    shutil.copytree(source_res, target_res, dirs_exist_ok=True)
    logo_target = copy_whiteflood_logo(app_root)

    layout = target_res / "layout/activity_main.xml"
    settings_layout = target_res / "layout/activity_setting.xml"
    spinner = target_res / "layout/wf_spinner_item.xml"
    if not layout.is_file() or not settings_layout.is_file() or not spinner.is_file():
        raise RuntimeError("WhiteFlood UI resources were not copied")
    if not logo_target.is_file():
        raise RuntimeError("WhiteFlood launcher logo was not copied")

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

    settings_text = settings_layout.read_text(encoding="utf-8")
    required_settings_ids = (
        "editDefaultCommand",
        "editMagickFilters",
        "editClassicalFilters",
        "editTile",
        "editThread",
        "editExtraCommand",
        "editExtraPath",
        "editSavePath",
        "editMNNBackend",
        "toggle_keep_screen",
        "toggle_cpu",
        "toggle_mult_files",
        "toggle_pre_png",
        "toggle_pre_frames",
        "toggle_auto_save",
        "toggle_serarch_view",
        "toggle_final_command",
        "toggle_custom_label",
        "spinner_format",
        "spinner_name",
        "spinner_name2",
        "spinner_name3",
        "spinner_orientation",
        "spinner_notify",
        "spinner_dir_format",
        "check_hide_realsr",
        "check_hide_srmd",
        "check_hide_waifu2x",
        "check_hide_realcugan",
        "check_hide_mnnsr",
        "check_hide_resize",
        "check_hide_magick",
        "check_hide_anime4k",
        "btn_edit_labels",
        "btn_save",
        "btn_reset",
        "btn_reset_low",
    )
    missing_settings = [
        item for item in required_settings_ids if f"@+id/{item}" not in settings_text
    ]
    if missing_settings:
        raise RuntimeError(
            f"Settings layout missing upstream-required ids: {missing_settings}"
        )

    build_text = (app_root / "build.gradle").read_text(encoding="utf-8")
    main_text = (
        app_root / "src/main/java/com/tumuyan/ncnn/realsr/MainActivity.java"
    ).read_text(encoding="utf-8")
    processor_text = (
        app_root / "src/main/java/com/tumuyan/ncnn/realsr/ImageProcessor.java"
    ).read_text(encoding="utf-8")
    required_runtime_markers = (
        "versionName '0.1.2'",
        "test -s output.png",
        "Engine Upscale belum siap",
        "proses berhenti dengan exit code",
    )
    combined = build_text + main_text + processor_text
    missing_markers = [item for item in required_runtime_markers if item not in combined]
    if missing_markers:
        raise RuntimeError(f"WhiteFlood v0.1.2 runtime guards missing: {missing_markers}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--overlay-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.upstream_root.resolve(), args.overlay_root.resolve())
    print(f"WhiteFlood overlay applied to upstream {UPSTREAM_SHA}")
