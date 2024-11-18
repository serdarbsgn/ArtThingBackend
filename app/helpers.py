import os
import hashlib
from fastapi import HTTPException, UploadFile
from .img_tools.psd_helper import layered_images


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_UPLOAD_SIZE = 20*1024*1024+1
IMAGE_DIRECTORY = PROJECT_DIR+"/static/projects/"

def listify(map):
    templist = []
    for row in map:
        dicx = {}
        for key,val in row.items():
            dicx[key] = val
        templist.append(dicx)
    return templist

async def check_file_size(file: UploadFile):
    if file.size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large.")
    return file

def get_file_md5(content: bytes) -> str:
    md5_hash = hashlib.md5(content).hexdigest()
    return md5_hash

def save_file(filepath,filename,content,artist):
    with open(filepath,"wb") as fp:
        fp.write(content)
    save_location = f'{PROJECT_DIR}/static/projects/{filename}'
    os.makedirs(save_location, exist_ok=True)
    layered_images(filepath,artist,save_location)

def limit_line_breaks(content:str, max_line_breaks=255):
    lines = content.splitlines()
    new_content = ""
    for i,line in enumerate(lines):
        if i<max_line_breaks:
            new_content += f'{line}<br>'
        else:
            new_content += ' '.join(lines[i:])
            break
    return new_content.rstrip('<br>')
