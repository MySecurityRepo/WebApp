import os
import cv2
from PIL import Image
from server.blog import upload_logger
from datetime import datetime
from multiprocessing.dummy import Pool
from multiprocessing import cpu_count
import traceback
from .image import moderate_image
from threading import Event


BATCH_SIZE = 10

def process_batch(batch, username, ip, filename):
    images, frame_filenames = zip(*batch)
    return moderate_image(images=list(images), username=username, ip=ip, filename=filename)


_device_env = os.environ.get("CUDA_VISIBLE_DEVICES")
if _device_env and _device_env.strip() != "":
    use_gpu = True
else:
    use_gpu = False


def extract_video_frames(video_path, skip=7):
    frames = []
    cap = cv2.VideoCapture(video_path)
    frame_idx = 0
    success = True

    while success:
        success, frame = cap.read()
        if not success:
            break
        if frame_idx % skip == 0:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            frames.append((frame_idx, pil_image))
        frame_idx += 1

    cap.release()
    return frames

def moderate_video(path, username, ip, filename, skip=7):
    try:
        frames = extract_video_frames(path, skip=skip)
        frame_data = []
        for idx, (frame_idx, image) in enumerate(frames):
            frame_data.append((image, f"{filename} [frame {frame_idx}]"))

        batches = [frame_data[i:i + BATCH_SIZE] for i in range(0, len(frame_data), BATCH_SIZE)]

        abort_flag = Event()

        def guarded_process_batch(batch):
            if abort_flag.is_set():
                return []
            result = process_batch(batch, username, ip, filename)
            if result == "error" or result.count(False) >= 2:
                abort_flag.set()
                return []
            return result

        flat_results = []

        if use_gpu:
            for batch in batches:
                result = guarded_process_batch(batch)
                if abort_flag.is_set():
                    return False
                flat_results.extend(result)
        else:
            with Pool(processes=min(4, cpu_count())) as pool:
                for result in pool.imap(guarded_process_batch, batches):
                    if abort_flag.is_set():
                        return False
                    flat_results.extend(result)
                
        if flat_results.count(False) >= 2:
            return False
        elif len(flat_results)==1 and flat_results.count(False)==1:
            return False
        return True

    except Exception as e:
        upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\n TRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return "error"
