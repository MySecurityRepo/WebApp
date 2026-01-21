import torch
import tensorflow as tf
import numpy as np
from PIL import Image, ImageOps
from transformers import CLIPProcessor, CLIPModel
import logging
from datetime import datetime
import traceback
from flask import g
from server.blog import upload_logger
import opennsfw2 as n2
import io
import time
import os
from contextlib import contextmanager


_device_env = os.environ.get("CUDA_VISIBLE_DEVICES")

if _device_env and _device_env.strip() != "" and torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

clip_model = CLIPModel.from_pretrained("/home/webserver/local_models/clip-vit-base-patch32/models--openai--clip-vit-base-patch32/snapshots/3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268", local_files_only=True).eval().to(device)
clip_processor = CLIPProcessor.from_pretrained("/home/webserver/local_models/clip-vit-base-patch32/models--openai--clip-vit-base-patch32/snapshots/3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268", local_files_only=True)


def prepare_image_for_clip(image):
    image = image.convert("RGB")
    image = image.copy()
    image = ImageOps.fit(image, (224, 224), method=Image.BICUBIC)
    return image


def img_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()
    
    
def open_nsfw_score(image):
    with tf.device("/CPU:0"):
        prediction = n2.predict_image(image)
    return float(prediction)
    
    
def clip_score(images, prompts):
    
    if not isinstance(images, list):
        images = [images]
        
    inputs = clip_processor(text=prompts, images=images, return_tensors="pt", padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    start = time.time()
    outputs = clip_model(**inputs)
    end = time.time()
    probs = outputs.logits_per_image.softmax(dim=1).detach().cpu().numpy()
    results = [dict(zip(prompts, p)) for p in probs] 
    return results
    
        
def moderate_image(path=None, images=None, username=None, ip=None, filename=None):

    results = []
    try:
        if images is None:
            if path is None:
                raise ValueError("Either 'path' or 'images' must be provided.")
            images = [Image.open(path).convert("RGB")]
        elif isinstance(images, Image.Image):
            images = [images]
        
        num_images = len(images)
        filenames = [f"{filename} [frame {i}]" for i in range(num_images)]
        usernames = [username] * num_images
        ips = [ip] * num_images   
        resized_images = [prepare_image_for_clip(img) for img in images]
        
        porn_prompts = "...this is private..."
        safe_porn_prompts = "...this is private..."
        p_prompts = porn_prompts + safe_porn_prompts
        clip_results_porn = clip_score(resized_images, p_prompts)
        
        violence_prompts = "...this is private..."
        safe_violence_prompts = "...this is private..."              
        v_prompts = violence_prompts + safe_violence_prompts
        clip_results_violence = clip_score(resized_images, v_prompts)  
             
        violence_prompts2 = "...this is private..."
        safe_violence_prompts2 = "...this is private..."
        v_prompts2 = violence_prompts2 + safe_violence_prompts2
        clip_results_violence2 = clip_score(resized_images, v_prompts2)
         
        violence_prompts3 = "...this is private..."
        safe_violence_prompts3 = "...this is private..."
        v_prompts3 = violence_prompts3 + safe_violence_prompts3
        clip_results_violence3 = clip_score(resized_images, v_prompts3)
        
        violence_prompts4 = "...this is private..."
        safe_violence_prompts4 = "...this is private..."
        v_prompts4 = violence_prompts4 + safe_violence_prompts4
        clip_results_violence4 = clip_score(resized_images, v_prompts4)
        
        horror_prompts = "...this is private..."
        safe_horror_prompts = "...this is private..."
        h_prompts = horror_prompts + safe_horror_prompts
        clip_results_horror = clip_score(resized_images, h_prompts)
        
        

        for clip_result_porn, clip_result_violence, clip_result_violence2, clip_result_violence3, clip_result_violence4, clip_result_horror,  image, fname, resized_image in zip(clip_results_porn, clip_results_violence, clip_results_violence2, clip_results_violence3, clip_results_violence4, clip_results_horror, images, filenames, resized_images):
            
            porn_mean = sum(clip_result_porn[p] for p in porn_prompts)  / len(porn_prompts)           
            safe_porn_mean = sum(clip_result_porn[p] for p in safe_porn_prompts) / len(safe_porn_prompts)
            porn_ratio = porn_mean/safe_porn_mean           
                    
            violence_media = sum(clip_result_violence[p] for p in violence_prompts) #/ len(violence_prompts)            
            safe_violence_media = sum(clip_result_violence[p] for p in safe_violence_prompts) #/ len(safe_violence_prompts)
            violence_ratio = violence_media/safe_violence_media          
                    
            violence_media2 = sum(clip_result_violence2[p] for p in violence_prompts2) #/ len(violence_prompts2)            
            safe_violence_media2 = sum(clip_result_violence2[p] for p in safe_violence_prompts2) #/ len(safe_violence_prompts2)
            violence_ratio2 = violence_media2/safe_violence_media2        
                      
            violence_media3 = sum(clip_result_violence3[p] for p in violence_prompts3) #/ len(violence_prompts3)            
            safe_violence_media3 = sum(clip_result_violence3[p] for p in safe_violence_prompts3) #/ len(safe_violence_prompts3)
            violence_ratio3 = violence_media3/safe_violence_media3         
                     
            violence_media4 = sum(clip_result_violence4[p] for p in violence_prompts4) #/ len(violence_prompts4)            
            safe_violence_media4 = sum(clip_result_violence4[p] for p in safe_violence_prompts4) #/ len(safe_violence_prompts4)
            violence_ratio4 = violence_media4/safe_violence_media4          
                      
            horror_media = sum(clip_result_horror[p] for p in horror_prompts) / len(horror_prompts)            
            safe_horror_media = sum(clip_result_horror[p] for p in safe_horror_prompts) / len(safe_horror_prompts)
            horror_ratio = horror_media/safe_horror_media
            if porn_ratio > 10 or horror_ratio > 2.81 or violence_ratio > 2.90 or violence_ratio2 > 2.80 or violence_ratio3 > 2.5 or violence_ratio4 > 2.5:                                
                if num_images ==1:
                    return [False]
                else:
                    results.append(False)
                    if results.count(False) >= 2:
                        return results
                
            if  1.55<= porn_ratio <=10: 
                porn_prompts2 = "...this is private..."
                safe_porn_prompts2 = "...this is private..."
                p_prompts2 = porn_prompts2 + safe_porn_prompts2
                clip_result_porn2 = clip_score(resized_image, p_prompts2)[0]
                porn_mean2 = sum(clip_result_porn2[p] for p in porn_prompts2)/ len(porn_prompts2)           
                safe_porn_mean2 = sum(clip_result_porn2[p] for p in safe_porn_prompts2)/ len(safe_porn_prompts2)
                porn_ratio2 = porn_mean2/safe_porn_mean2
                if porn_ratio2 > 4:
                    if num_images ==1:
                        return [False]
                    else:
                        results.append(False)
                        if results.count(False) >= 2:
                            return results
                if 1.40 <= porn_ratio2 <= 4 :
                    porn_prompts3 = "...this is private..."
                    safe_porn_prompts3 = "...this is private..."
                    p_prompts3 = porn_prompts3 + safe_porn_prompts3
                    clip_result_porn3 = clip_score(resized_image, p_prompts3)[0]
                    porn_mean3 = sum(clip_result_porn3[p] for p in porn_prompts3)/ len(porn_prompts3)           
                    safe_porn_mean3 = sum(clip_result_porn3[p] for p in safe_porn_prompts3)/ len(safe_porn_prompts3)
                    porn_ratio3 = porn_mean3/safe_porn_mean3
                    print(f"porn_ratio3={porn_ratio3}")
                    if porn_ratio3 > 2.7:
                        if num_images ==1:
                            return [False]
                        else:
                            results.append(False)
                            if results.count(False) >= 2:
                                return results
                    if porn_ratio >2 and porn_ratio2 >2 and porn_ratio3 > 2:
                        if num_images ==1:
                            return [False]
                        else:
                            results.append(False)
                            if results.count(False) >= 2:
                                return results
                    if 1.65 <= porn_ratio3 <= 3:
                        nsfw_score = open_nsfw_score(image) 
                        print(f"nsfw_score={nsfw_score}")
                        if nsfw_score > 0.70:
                            if num_images ==1:
                                return [False]
                            else:
                                results.append(False)
                                if results.count(False) >= 2:
                                    return results
           
            
            results.append(True)
        return results[0] if path and len(results) == 1 else results     

    except Exception as e:
        upload_logger.error(f"[{datetime.utcnow()}] | USER: {username} | IP: {ip} | FILE: {filename} | ERROR: {str(e)}\nTRACEBACK:\n{traceback.format_exc()}\n{'-'*60}")  
        return "error"
