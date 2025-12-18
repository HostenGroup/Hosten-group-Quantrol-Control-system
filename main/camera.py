####################################################################
# Author: Alexei Gurchenko, Hosten group
# Date: 14 November 2025
####################################################################


from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
import traceback
from pathlib import Path
from time import perf_counter
from typing import Dict, Optional

import PySpin

import config


def load_experiment_entry(repo_root: Path, experiment_code: int) -> Dict[str, object]:
    experiments_file = repo_root / "experiment_specific_files" / config.which_project / "experiment_names.json"
    if not experiments_file.exists():
        raise FileNotFoundError(f"Experiment list not found at {experiments_file}")

    with experiments_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not data:
        raise ValueError("Experiment list is empty")

    if str(experiment_code) not in data:
        # Fall back to the first entry if the requested code is missing
        first_key = sorted(data.keys(), key=lambda item: int(item))[0]
        experiment_code = int(first_key)

    entry = data[str(experiment_code)]
    entry["code"] = experiment_code
    return entry


def initialise_cameras(cam_list: PySpin.CameraList) -> Dict[str, PySpin.Camera]:
    camera_dict: Dict[str, PySpin.Camera] = {}
    for cam in cam_list:
        cam.Init()
        # Stop acquisition if running (ignore errors if it wasn't active)
        try:
            cam.BeginAcquisition()
            cam.EndAcquisition()
        except PySpin.SpinnakerException:
            pass

        nodemap_tldevice = cam.GetTLDeviceNodeMap()
        node_serial = PySpin.CStringPtr(nodemap_tldevice.GetNode("DeviceSerialNumber"))
        if not PySpin.IsAvailable(node_serial) or not PySpin.IsReadable(node_serial):
            raise RuntimeError("Unable to read camera serial number.")

        serial_number = node_serial.GetValue()
        for label, expected_serial in config.camera_serial_numbers_dict.items():
            if serial_number == expected_serial:
                camera_dict[label] = cam
                break
        else:
            raise RuntimeError(f"Unknown camera serial {serial_number}. Update config.camera_serial_numbers_dict")

    return camera_dict


def configure_camera(
    cam: PySpin.Camera,
    exposure_us: float,
    gain_db: float,
    format_name: str,
    info: Dict[str, object],
) -> None:
    nodemap = cam.GetNodeMap()

    # Exposure configuration
    node_exposure_auto = PySpin.CEnumerationPtr(nodemap.GetNode("ExposureAuto"))
    if not PySpin.IsAvailable(node_exposure_auto) or not PySpin.IsWritable(node_exposure_auto):
        raise RuntimeError("ExposureAuto node not writable.")
    node_exposure_auto_off = node_exposure_auto.GetEntryByName("Off")
    node_exposure_auto.SetIntValue(node_exposure_auto_off.GetValue())

    node_exposure_time = PySpin.CFloatPtr(nodemap.GetNode("ExposureTime"))
    if not PySpin.IsAvailable(node_exposure_time) or not PySpin.IsWritable(node_exposure_time):
        raise RuntimeError("ExposureTime node not writable.")
    min_exposure = node_exposure_time.GetMin()
    max_exposure = node_exposure_time.GetMax()
    exposure_us = max(min(exposure_us, max_exposure), min_exposure)
    node_exposure_time.SetValue(exposure_us)
    print(f"Exposure set to {exposure_us:.1f} us (range {min_exposure:.1f} - {max_exposure:.1f} us)")

    # Gain configuration
    node_gain_auto = PySpin.CEnumerationPtr(nodemap.GetNode("GainAuto"))
    if not PySpin.IsAvailable(node_gain_auto) or not PySpin.IsWritable(node_gain_auto):
        raise RuntimeError("GainAuto node not writable.")
    node_gain_auto_off = node_gain_auto.GetEntryByName("Off")
    node_gain_auto.SetIntValue(node_gain_auto_off.GetValue())

    node_gain = PySpin.CFloatPtr(nodemap.GetNode("Gain"))
    if not PySpin.IsAvailable(node_gain) or not PySpin.IsWritable(node_gain):
        raise RuntimeError("Gain node not writable.")
    min_gain = node_gain.GetMin()
    max_gain = node_gain.GetMax()
    gain_db = max(min(gain_db, max_gain), min_gain)
    node_gain.SetValue(gain_db)
    print(f"Gain set to {gain_db:.2f} dB (range {min_gain:.2f} - {max_gain:.2f} dB)")

    # Automatic frame rate
    node_acq_fr_enable = PySpin.CBooleanPtr(nodemap.GetNode("AcquisitionFrameRateEnable"))
    if PySpin.IsAvailable(node_acq_fr_enable) and PySpin.IsWritable(node_acq_fr_enable):
        node_acq_fr_enable.SetValue(False)
    print("Frame rate is now automatic")

    # Disable gamma
    node_gamma_enable = PySpin.CBooleanPtr(nodemap.GetNode("GammaEnable"))
    if PySpin.IsAvailable(node_gamma_enable) and PySpin.IsWritable(node_gamma_enable):
        node_gamma_enable.SetValue(False)
        print("Gamma disabled")

    # EV compensation
    node_ev = PySpin.CFloatPtr(nodemap.GetNode("AutoExposureEVCompensation"))
    if not PySpin.IsAvailable(node_ev) or not PySpin.IsWritable(node_ev):
        raise RuntimeError("EV compensation not available on this camera.")
    ev_value = 0.0
    ev_value = max(min(ev_value, node_ev.GetMax()), node_ev.GetMin())
    node_ev.SetValue(ev_value)
    print(f"EV compensation set to {ev_value:.2f}")

    # Black level
    node_bl = PySpin.CFloatPtr(nodemap.GetNode("BlackLevel"))
    if not PySpin.IsAvailable(node_bl) or not PySpin.IsWritable(node_bl):
        raise RuntimeError("BlackLevel not available or not writable on this camera.")
    black_level_value = max(min(0.0, node_bl.GetMax()), node_bl.GetMin())
    node_bl.SetValue(black_level_value)
    print(f"Black level set to {black_level_value:.2f} %")

    # Pixel format
    pf_node = PySpin.CEnumerationPtr(nodemap.GetNode("PixelFormat"))
    if not PySpin.IsAvailable(pf_node) or not PySpin.IsWritable(pf_node):
        raise RuntimeError("PixelFormat node not writable (camera acquiring or node locked).")
    entry = pf_node.GetEntryByName(format_name)
    if not PySpin.IsAvailable(entry) or not PySpin.IsReadable(entry):
        raise RuntimeError(f"Pixel format {format_name} not supported by this camera.")
    pf_node.SetIntValue(entry.GetValue())
    print(f"Pixel format set to {format_name}")

    # ADC depth
    adc_depth = 10
    adc_node = PySpin.CEnumerationPtr(nodemap.GetNode("AdcBitDepth"))
    if not PySpin.IsAvailable(adc_node) or not PySpin.IsWritable(adc_node):
        raise RuntimeError("AdcBitDepth not available or not writable on this camera.")
    entry_adc = adc_node.GetEntryByName(f"Bit{int(adc_depth)}")
    if not PySpin.IsAvailable(entry_adc) or not PySpin.IsReadable(entry_adc):
        raise RuntimeError(f"ADC depth {adc_depth}-bit not supported on this camera.")
    adc_node.SetIntValue(entry_adc.GetValue())
    print(f"ADC depth set to {adc_depth} bit")

    # Binning
    node_bin_h = PySpin.CIntegerPtr(nodemap.GetNode("BinningHorizontal"))
    if PySpin.IsAvailable(node_bin_h) and PySpin.IsWritable(node_bin_h):
        node_bin_h.SetValue(max(min(1, node_bin_h.GetMax()), node_bin_h.GetMin()))
        print("Horizontal binning set to 1")
    else:
        print("Horizontal binning not available on this camera.")

    node_bin_v = PySpin.CIntegerPtr(nodemap.GetNode("BinningVertical"))
    if PySpin.IsAvailable(node_bin_v) and PySpin.IsWritable(node_bin_v):
        node_bin_v.SetValue(max(min(1, node_bin_v.GetMax()), node_bin_v.GetMin()))
        print("Vertical binning set to 1")
    else:
        print("Vertical binning not available on this camera.")

    # Full ROI
    node_width = PySpin.CIntegerPtr(nodemap.GetNode("Width"))
    if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width):
        max_width = node_width.GetMax()
        node_width.SetValue(max_width)
        info["width"] = max_width
        print(f"Width set to maximum: {max_width}")
    else:
        print("Width not available or not writable.")

    node_height = PySpin.CIntegerPtr(nodemap.GetNode("Height"))
    if PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):
        max_height = node_height.GetMax()
        node_height.SetValue(max_height)
        info["height"] = max_height
        print(f"Height set to maximum: {max_height}")
    else:
        print("Height not available or not writable.")

    node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode("OffsetX"))
    if PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):
        node_offset_x.SetValue(node_offset_x.GetMin())
        print(f"OffsetX set to {node_offset_x.GetValue()}")

    node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode("OffsetY"))
    if PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):
        node_offset_y.SetValue(node_offset_y.GetMin())
        print(f"OffsetY set to {node_offset_y.GetValue()}")

    # Decimation
    node_dec_h = PySpin.CIntegerPtr(nodemap.GetNode("DecimationHorizontal"))
    if PySpin.IsAvailable(node_dec_h) and PySpin.IsWritable(node_dec_h):
        node_dec_h.SetValue(max(min(1, node_dec_h.GetMax()), node_dec_h.GetMin()))
        print("Horizontal decimation set to 1")
    else:
        print("Horizontal decimation not available on this camera.")

    node_dec_v = PySpin.CIntegerPtr(nodemap.GetNode("DecimationVertical"))
    if PySpin.IsAvailable(node_dec_v) and PySpin.IsWritable(node_dec_v):
        node_dec_v.SetValue(max(min(1, node_dec_v.GetMax()), node_dec_v.GetMin()))
        print("Vertical decimation set to 1")
    else:
        print("Vertical decimation not available on this camera.")

    # Acquisition mode
    node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionMode"))
    if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
        raise RuntimeError("Unable to access AcquisitionMode node")
    node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName("Continuous")
    node_acquisition_mode.SetIntValue(node_acquisition_mode_continuous.GetValue())
    print("Acquisition mode set to continuous")

    # Trigger configuration
    trig_mode = PySpin.CEnumerationPtr(nodemap.GetNode("TriggerMode"))
    trig_mode_off = trig_mode.GetEntryByName("Off")
    trig_mode.SetIntValue(trig_mode_off.GetValue())

    trig_sel = PySpin.CEnumerationPtr(nodemap.GetNode("TriggerSelector"))
    trig_sel.SetIntValue(trig_sel.GetEntryByName("FrameStart").GetValue())

    trig_src = PySpin.CEnumerationPtr(nodemap.GetNode("TriggerSource"))
    trig_src.SetIntValue(trig_src.GetEntryByName("Line0").GetValue())

    trig_act = PySpin.CEnumerationPtr(nodemap.GetNode("TriggerActivation"))
    if PySpin.IsAvailable(trig_act) and PySpin.IsWritable(trig_act):
        trig_act.SetIntValue(trig_act.GetEntryByName("RisingEdge").GetValue())

    trig_ovl = PySpin.CEnumerationPtr(nodemap.GetNode("TriggerOverlap"))
    if PySpin.IsAvailable(trig_ovl) and PySpin.IsWritable(trig_ovl):
        ent_off = trig_ovl.GetEntryByName("Off")
        if PySpin.IsAvailable(ent_off) and PySpin.IsReadable(ent_off):
            trig_ovl.SetIntValue(ent_off.GetValue())

    line_sel = PySpin.CEnumerationPtr(nodemap.GetNode("LineSelector"))
    line_mode = PySpin.CEnumerationPtr(nodemap.GetNode("LineMode"))
    line_inv = PySpin.CBooleanPtr(nodemap.GetNode("LineInverter"))
    if PySpin.IsAvailable(line_sel) and PySpin.IsWritable(line_sel):
        ent_line0 = line_sel.GetEntryByName("Line0")
        if PySpin.IsAvailable(ent_line0) and PySpin.IsReadable(ent_line0):
            line_sel.SetIntValue(ent_line0.GetValue())
            if PySpin.IsAvailable(line_mode) and PySpin.IsWritable(line_mode):
                mode_in = line_mode.GetEntryByName("Input")
                if PySpin.IsAvailable(mode_in) and PySpin.IsReadable(mode_in):
                    line_mode.SetIntValue(mode_in.GetValue())
            if PySpin.IsAvailable(line_inv) and PySpin.IsWritable(line_inv):
                line_inv.SetValue(False)

    exp_mode = PySpin.CEnumerationPtr(nodemap.GetNode("ExposureMode"))
    if PySpin.IsAvailable(exp_mode) and PySpin.IsWritable(exp_mode):
        timed = exp_mode.GetEntryByName("Timed")
        if PySpin.IsAvailable(timed) and PySpin.IsReadable(timed):
            exp_mode.SetIntValue(timed.GetValue())

    trigger_delay_us = 12.0
    trig_delay = PySpin.CFloatPtr(nodemap.GetNode("TriggerDelay"))
    if PySpin.IsAvailable(trig_delay) and PySpin.IsWritable(trig_delay):
        trigger_delay_us = max(min(trigger_delay_us, trig_delay.GetMax()), trig_delay.GetMin())
        trig_delay.SetValue(trigger_delay_us)
    else:
        if trigger_delay_us not in (0, 0.0):
            raise RuntimeError("TriggerDelay not available on this camera.")

    trig_mode_on = trig_mode.GetEntryByName("On")
    trig_mode.SetIntValue(trig_mode_on.GetValue())

    print(
        "Hardware trigger configured: FrameStart, Line0, RisingEdge, "
        "Overlap = Off, Inverter = False, delay = "
        f"{trigger_delay_us:.1f} us"
    )


def run_acquisition(args: argparse.Namespace) -> None:
    repo_root = Path(args.repo_root).resolve()
    experiment_entry = load_experiment_entry(repo_root, args.experiment_code)
    experiment_name = experiment_entry.get("name", f"experiment_{experiment_entry['code']}")
    scan_caption = experiment_entry.get("plot_x_caption", "")

    if args.target_dir:
        directory = Path(args.target_dir).resolve()
        parents = directory.parents
        if len(parents) >= 3:
            output_root = parents[2]
        elif parents:
            output_root = parents[-1]
        else:
            output_root = directory
        output_root = output_root.resolve()
    else:
        output_root = Path(args.output_root) if args.output_root else Path(
            rf"G:/Experimental Data/Hybrid/MOT_images/{experiment_name}"
        )
        output_root = output_root.resolve()
        timestamp = dt.datetime.now()
        directory = output_root / timestamp.strftime("%Y_%m_%d") / timestamp.strftime("%H_%M_%S") / args.camera

    # Optional: stage images to a local directory for fast saving, then move to the final directory at the end.
    final_directory = directory
    stage_local = bool(getattr(args, "stage_local", False)) or bool(getattr(config, "camera_stage_locally", False))
    stage_dir_raw = getattr(args, "stage_dir", None) or getattr(config, "camera_stage_dir", None)
    stage_base = Path(stage_dir_raw).resolve() if stage_dir_raw else (repo_root / "temp_images").resolve()
    stage_directory: Optional[Path] = None
    if stage_local:
        try:
            # Preserve the run folder structure (<date>/<time>/<camera>) where possible.
            date_part = directory.parents[1].name if len(directory.parents) >= 2 else dt.datetime.now().strftime("%Y_%m_%d")
            time_part = directory.parent.name if directory.parent else dt.datetime.now().strftime("%H_%M_%S")
        except Exception:
            date_part = dt.datetime.now().strftime("%Y_%m_%d")
            time_part = dt.datetime.now().strftime("%H_%M_%S")
        stage_directory = stage_base / str(experiment_name) / date_part / time_part / args.camera
        directory = stage_directory
        print(f"Staging enabled: saving locally to {stage_directory}")
        print(f"Final destination: {final_directory}")

    # Parameters you want to put to the info file (ALL VALUES IN SI)
    # Legacy reference (kept for clarity):
    # {
    #     'min': 0,
    #     'max': 360,
    #     'text': 'MOT jiggle',
    #     't_storage': 500e-3,
    #     't_loading': 200e-3,
    #     'freq': 10,
    #     'scan': <x caption from experiment_names.json>
    # }
    parameters = {
        "min": 0,
        "max": 360,
        "text": "MOT jiggle",
        "t_storage": 500e-3,
        "t_loading": 200e-3,
        "freq": 10,
        "scan": scan_caption,
    }

    serial_numbers = config.camera_serial_numbers_dict
    if args.camera not in serial_numbers:
        raise ValueError(f"Camera label '{args.camera}' is not configured")

    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    if cam_list.GetSize() == 0:
        cam_list.Clear()
        system.ReleaseInstance()
        raise RuntimeError("No FLIR cameras detected.")

    camera_dict: Dict[str, PySpin.Camera] = {}
    cam: Optional[PySpin.Camera] = None
    file_directory: Optional[Path] = None
    final_file_directory: Optional[Path] = None
    info: Optional[Dict[str, object]] = None
    saved_images = 0
    time_start: Optional[dt.datetime] = None
    last_saved_at: Optional[float] = None
    drop_initial = 0
    interrupted = False
    try:
        camera_dict = initialise_cameras(cam_list)
        if args.camera not in camera_dict:
            raise RuntimeError(f"Requested camera '{args.camera}' not detected.")

        cam = camera_dict[args.camera]
        exposure_us = max(args.exposure_ms, 0.0) * 1000.0
        info = {
            "format": args.format,
            "gain": args.gain_db,
            "exposure": exposure_us,
            "image_number": None,
            "camera": args.camera,
            "camera_serial_number": serial_numbers[args.camera],
            "experiment": experiment_name,
            "comments": args.info_text,
            "parameters": parameters,
        }

        configure_camera(cam, exposure_us, args.gain_db, args.format, info)

        file_directory = directory
        final_file_directory = final_directory
        file_directory.mkdir(parents=True, exist_ok=True)

        cam.BeginAcquisition()

        timeout_ms = 5000
        short_timeout = 50
        num_of_timeouts = int(timeout_ms / short_timeout)
        timeout_counter = 0
        drop_initial = max(int(getattr(args, "drop_initial_count", 0) or 0), 0)
        remaining_warmup = drop_initial

        print("Use hardware to trigger image acquisition. Press Ctrl+C to interrupt.")
        while True:
            if timeout_counter >= num_of_timeouts and saved_images > 0:
                raise RuntimeError("Camera timeout. Acquisition finished successfully.")

            try:
                t_get_start = perf_counter()
                image = cam.GetNextImage(short_timeout)
                t_get_end = perf_counter()
            except PySpin.SpinnakerException as ex:
                if "[-1011]" in str(ex):
                    timeout_counter += 1
                    continue
                raise

            try:
                if image.IsIncomplete():
                    raise RuntimeError(f"Image CAM {args.camera} incomplete with status {image.GetImageStatus()}")

                if time_start is None:
                    time_start = dt.datetime.now()
                    last_saved_at = perf_counter()

                timeout_counter = 0

                get_ms = (t_get_end - t_get_start) * 1000.0

                if remaining_warmup > 0:
                    remaining_warmup -= 1
                    skipped = drop_initial - remaining_warmup
                    print(f"Discarded warm-up image {skipped}/{drop_initial} | GetNextImage={get_ms:.1f} ms")
                else:
                    filename = file_directory / f"{args.camera}_{saved_images}.tif"
                    t_save_start = perf_counter()
                    if not getattr(args, "no_save", False):
                        image.Save(str(filename))
                    t_save_end = perf_counter()
                    save_ms = (t_save_end - t_save_start) * 1000.0

                    saved_images += 1

                    now = perf_counter()
                    since_last_s = (now - last_saved_at) if last_saved_at is not None else float("nan")
                    last_saved_at = now

                    output_note = "skipped save" if getattr(args, "no_save", False) else "saved"

                    # Always print timing breakdown (this is what varies strongly between machines).
                    if getattr(args, "profile", False):
                        total_ms = get_ms + save_ms
                        print(
                            f"#{saved_images:05d} {output_note} | "
                            f"GetNextImage={get_ms:7.1f} ms | Save={save_ms:7.1f} ms | "
                            f"Loop~{total_ms:7.1f} ms | since_last={since_last_s*1000.0:7.1f} ms | "
                            f"{filename}"
                        )
                    else:
                        print(
                            f"Saved image {saved_images} ({output_note}) | "
                            f"GetNextImage={get_ms:.1f} ms | Save={save_ms:.1f} ms | "
                            f"since_last={since_last_s*1000.0:.1f} ms"
                        )

                    time_el = dt.datetime.now() - time_start
                    print(f"Elapsed since first frame: {time_el.total_seconds():.3f} s")
                    print("Use hardware to trigger image acquisition. Press Ctrl+C to interrupt.")
            finally:
                image.Release()

    except KeyboardInterrupt:
        print("Stopped by user.")
        interrupted = True
    except Exception as exc:
        print(str(exc))
        interrupted = False
        raise

    finally:
        if cam is not None:
            try:
                cam.EndAcquisition()
                del cam
            except PySpin.SpinnakerException:
                pass
            except Exception:
                pass

        


        if info is not None:
            info["skipped_images"] = drop_initial

        if not interrupted and file_directory is not None and info is not None and saved_images >= 1:
            destination_dir = final_file_directory or file_directory
            staging_used = stage_local and stage_directory is not None and destination_dir != file_directory

            if staging_used:
                destination_dir.mkdir(parents=True, exist_ok=True)
                print(f"Moving staged images to final destination: {destination_dir}")
                try:
                    moved = 0
                    for source_path in sorted(file_directory.iterdir()):
                        if not source_path.is_file():
                            continue
                        shutil.move(str(source_path), str(destination_dir / source_path.name))
                        moved += 1
                    print(f"Moved {moved} file(s) from staging.")

                    # Remove the now-empty staging folder for this run (and prune empty parents up to stage_base).
                    shutil.rmtree(file_directory, ignore_errors=True)
                    parent = (file_directory.parent if file_directory is not None else None)
                    while parent is not None and parent != stage_base and parent.exists():
                        try:
                            next_parent = parent.parent
                            parent.rmdir()
                            parent = next_parent
                        except OSError:
                            break
                except Exception as exc:
                    print(f"Warning: failed to move staged images: {exc}")
                    print(f"Images remain in staging directory: {file_directory}")
                    destination_dir = file_directory

            # info["image_number"] = saved_images
            # file_directory.mkdir(parents=True, exist_ok=True)
            # with (file_directory / "info.json").open("w", encoding="utf-8") as file:
            #     json.dump(info, file, indent=4)
            print(rf"Files saved at {destination_dir}")

            if time_start is not None:
                time_elapsed = dt.datetime.now() - time_start
                print(f"Elapsed time: {time_elapsed.total_seconds():.1f} s")

            try:
                data_root = Path(getattr(config, "experiment_data_root", "")).resolve()
                last_path_file = data_root / "last_path.txt"
                last_path_file.parent.mkdir(parents=True, exist_ok=True)
                last_path_file.write_text(str(destination_dir))
                path_list_file = data_root / "path_list.txt"
                with path_list_file.open("a", encoding="utf-8") as file:
                    file.write(str(destination_dir) + "\n")
            except Exception:
                print("Warning: unable to update last_path.txt or path_list.txt")

            if args.process_images:
                try:
                    data_root = Path(getattr(config, "experiment_data_root", "")).resolve()
                    processing_script = data_root.parent / "image_processing.py"
                    if processing_script.exists():
                        exec(processing_script.read_text(encoding="utf-8"), {})
                except Exception:
                    print("Warning: image processing script failed")

        for cam_obj in cam_list:
            try:
                cam_obj.DeInit()
            except Exception as ex:
                print(str(ex))
        
        cam_list.Clear()
        del cam_list
        del cam_obj
        del camera_dict



        try:
            system.ReleaseInstance()
        except PySpin.SpinnakerException as release_exc:
            print(f"Warning: unable to release camera system cleanly: {release_exc}")
        else:
            print("Acquisition ended. Camera deinitialised. System released.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run FLIR camera acquisition with parameters provided by Quantrol."
    )
    # Analog gain and exposure mirror the legacy defaults (e.g. gain_db=20, exposure=350 us)
    parser.add_argument("--camera", required=True, help="Camera label as defined in config.camera_serial_numbers_dict")
    parser.add_argument("--format", required=True, help="Pixel format name, e.g. Mono8")
    parser.add_argument("--gain-db", required=True, type=float, help="Analog gain in dB")
    parser.add_argument("--exposure-ms", required=True, type=float, help="Exposure time in milliseconds")
    parser.add_argument("--experiment-code", type=int, default=0, help="Index of the experiment in experiment_names.json")
    parser.add_argument("--repo-root", type=str, default=str(Path(__file__).resolve().parents[1]), help="Repository root path")
    parser.add_argument("--output-root", type=str, default=None, help="Root directory for saving captures. Defaults to Hybrid MOT path")
    parser.add_argument("--target-dir", type=str, default=None, help="Exact directory for this acquisition run")
    parser.add_argument("--info-text", type=str, default="", help="Optional comment stored in info.json")
    parser.add_argument("--process-images", action="store_true", help="Run legacy post-processing once acquisition finishes")
    parser.add_argument("--drop-initial-count", type=int, default=0, help="Number of initial hardware triggers to ignore when saving")
    parser.add_argument("--profile", action="store_true", help="Print per-frame timing breakdown for acquisition vs save")
    parser.add_argument("--no-save", action="store_true", help="Acquire frames but skip saving to disk (for debugging)")
    parser.add_argument("--stage-local", action="store_true", help="Save images to a local staging directory and move to the target at the end")
    parser.add_argument("--stage-dir", type=str, default=None, help="Base directory for staging when --stage-local is enabled")
    args = parser.parse_args()
    try:
        run_acquisition(args)
    except Exception as exc:
        print(f"Camera acquisition failed: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
