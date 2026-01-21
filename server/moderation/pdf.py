import fitz  # PyMuPDF
from PIL import Image, ImageFilter
import io
from datetime import datetime
import traceback
from flask import g
from .image import moderate_image
from server.blog import upload_logger

    
def moderate_pdf(pdf_path, username, ip, filename):
    try:
    
        doc = fitz.open(pdf_path)
        seen_bbox_keys = set()
        for page_index in range(len(doc)):
            page = doc[page_index]
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                
                xref = img[0]
                img_infos = page.get_image_info(xref)
                if not img_infos:
                    continue
                     
                for info in img_infos:
                    bbox = info.get("bbox") 
                    
                    if not bbox or len(bbox) != 4:
                        continue           
                
                    bbox_key = tuple(round(v, 2) for v in bbox)
                    page_bbox_key = (page_index, bbox_key)
                    
                    if page_bbox_key in seen_bbox_keys:
                        continue
                    seen_bbox_keys.add(page_bbox_key)
                    
                    print(f"bbox={bbox}")
                    rect = fitz.Rect(bbox)
                    
                    zoom = 1  
                    mat = fitz.Matrix(zoom, zoom) 
                    pix = page.get_pixmap(matrix=mat, clip=rect) 
                    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                              
                    virtual_name = f"{filename} [page {page_index} image {img_index}]"
                    result = moderate_image(images=[image], username=username, ip=ip, filename=virtual_name)
                        
                    if result == "error":
                        return False
                    if isinstance(result, list) and not result[0]:
                        return False    

        return True  # no flagged images found

    except Exception as e:
        upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}") 
        return "error"
