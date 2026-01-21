import os
from PIL import Image
from server.blog import upload_logger
from datetime import datetime
from multiprocessing.dummy import Pool 
from multiprocessing import cpu_count
import traceback
import io
from .image import moderate_image
from threading import Event

BATCH_SIZE = 10

_device_env = os.environ.get("CUDA_VISIBLE_DEVICES")
if _device_env and _device_env.strip() != "":
    use_gpu = True
else:
    use_gpu = False


def process_batch(batch, username, ip, filename):
    images, frame_filenames = zip(*batch) 
    return moderate_image(images = list(images), username = username, ip = ip, filename = filename) 

def extract_gif_frames(gif_path, skip=7):
    frames = []
    with Image.open(gif_path) as im:
        frame_idx = 0
        try:
            while True:
                if frame_idx % skip == 0:
                    
                    buf = io.BytesIO()
                    im.copy().convert("RGB").save(buf, format="PNG")
                    frames.append((frame_idx, buf.getvalue()))
                frame_idx += 1
                im.seek(im.tell() + 1)
        except EOFError:
            pass
    return frames    

def moderate_gif(path, username, ip, filename, skip=7):
    try:
        frames = extract_gif_frames(path, skip=skip) 
        frame_data = []
        for idx, (frame_idx, image_bytes) in enumerate(frames):
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            frame_data.append((img, f"{filename} [frame {idx}]")) 

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
        upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")
        return "error"

