from math import ceil
import struct
import zipfile
from plistlib import loads,UID
import lz4.block
import numpy as np
from PIL import ImageDraw, ImageFont,Image
import os

#Works? At least for one .procreate example.
def pro_check(file):
    with zipfile.ZipFile(file, 'r') as zip_ref:
        try:
            doc_archive = zip_ref.read("Document.archive")
            doc_archive_bytes = bytes(doc_archive)
            arc_dict = loads(doc_archive_bytes)
            objects = arc_dict.get("$objects")
            chunk_size = objects[1].get('tileSize')
            image_size = [int(x) for x in objects[objects[1]["size"].data].strip("{").strip("}").split(", ")]
            v_flip = objects[1].get('flippedVertically')
            h_flip = objects[1].get('flippedHorizontally')
            grid_dimensions = [int(ceil(dim/chunk_size)) for dim in image_size]
            layers_info = resolve_layers_uid(objects,objects[1]["layers"])
            bounding_rect = (0,0,image_size[0],image_size[1])
            orientation = objects[1].get('orientation')
            return True
        except Exception as e:
            print(e)
            return None
    
def resolve_layers_uid(objects,layers_uid):
    info_dict = objects[layers_uid.data]
    if not isinstance(info_dict,dict):
        print("This is not looking like a layer info array.")
    if not "NS.objects" in info_dict:
        print("This is not looking like a layer info array.")
    layer_uid_array = objects[layers_uid.data].get("NS.objects")
    layer_dict_array = []
    for uid in layer_uid_array:
        resolved_dict = {}
        for key,value in objects[uid.data].items():
            if isinstance(value,UID):
                resolved_dict[key] = objects[value.data]
            else:
                resolved_dict[key] = value
        layer_dict_array.append(resolved_dict)
    return layer_dict_array

def layered_images(filepath,artist,save_location):
    with zipfile.ZipFile(filepath, 'r') as zip_ref:
        try:
            doc_archive = zip_ref.read("Document.archive")
            doc_archive_bytes = bytes(doc_archive)
            arc_dict = loads(doc_archive_bytes)
            objects = arc_dict.get("$objects")
            chunk_size = objects[1].get('tileSize')
            image_size = [int(x) for x in objects[objects[1]["size"].data].strip("{").strip("}").split(", ")]
            v_flip = objects[1].get('flippedVertically')
            h_flip = objects[1].get('flippedHorizontally')
            grid_dimensions = [int(ceil(dim/chunk_size)) for dim in image_size]
            layers_info = resolve_layers_uid(objects,objects[1]["layers"])
            bounding_rect = (0,0,image_size[0],image_size[1])
            orientation = objects[1].get('orientation')
        except:
            return None
        
        final_image = Image.new("RGBA", (image_size[0], image_size[1]), (255, 255, 255, 0))
        for i,layer in enumerate(reversed(layers_info)):
            if not layer["hidden"]:
                image,new_x,new_y = uuid_folder_to_png(zip_ref,layer,chunk_size=chunk_size,
                                grid_dimensions=grid_dimensions,
                                project_bb=bounding_rect,orientation=orientation,flips = [h_flip,v_flip],watermark=artist)
                output_image_path = os.path.join(save_location, f"{i}_{new_x}_{new_y}.png")
                image.save(output_image_path)
                final_image.alpha_composite(image, (new_x, new_y))

        final_image.thumbnail((300,300))
        final_image.save(f'{save_location}/thumbnail.png')
        return len(layers_info)

def find_crop_bounds(image):
    """
    Finds the number of fully transparent rows (top/bottom) and columns (left/right) to crop.
    """
    # Find top crop
    top_crop = 0
    for i in range(image.shape[0]):  # Iterate over rows
        if np.all(image[i] == 0):
            top_crop += 1
        else:
            break

    # Find bottom crop
    bottom_crop = 0
    for i in range(image.shape[0] - 1, -1, -1):
        if np.all(image[i] == 0):
            bottom_crop += 1
        else:
            break

    # Find left crop
    left_crop = 0
    for i in range(image.shape[1]):  # Iterate over columns
        if np.all(image[:, i] == 0):
            left_crop += 1
        else:
            break

    # Find right crop
    right_crop = 0
    for i in range(image.shape[1] - 1, -1, -1):
        if np.all(image[:, i] == 0):
            right_crop += 1
        else:
            break

    return top_crop, bottom_crop, left_crop, right_crop

# Function to extract image data from an lz4 file
def extract_images_from_lz4(data):
    decompressed_data = b""

    chunk_start = 0
    last_uncompressed = b""
    while chunk_start < len(data):
        header = data[chunk_start:chunk_start + 4]

        if header == b"bv41":  # LZ4 Compressed Chunk
            uncompressed_size, compressed_size = struct.unpack("<II", data[chunk_start + 4: chunk_start + 12])
            compressed_data = data[chunk_start + 12: chunk_start + 12 + compressed_size]

            try:
                last_uncompressed = lz4.block.decompress(compressed_data, uncompressed_size, dict=last_uncompressed)
                decompressed_data += last_uncompressed
            except lz4.block.LZ4BlockError as e:
                print(f"Error decompressing chunk: {e}")
                break

            chunk_start += 12 + compressed_size

        elif header == b"bv4-":  # Uncompressed Chunk
            uncompressed_size = struct.unpack("<I", data[chunk_start + 4: chunk_start + 8])[0]
            decompressed_data += data[chunk_start + 8: chunk_start + 8 + uncompressed_size]
            chunk_start += 8 + uncompressed_size

        elif header == b"bv4$":  # End of compressed data
            break

        else:
            print(f"Unknown header {header} at {chunk_start} in")
            break

    return decompressed_data

def uuid_folder_to_png(zip_ref,layer,chunk_size = 256,
                       grid_dimensions=(0,0),project_bb=(0,0,1920,1080),orientation = 3,flips = [False,False],watermark = "Test-Artist"):
    # Step 1: Extract the UUID-named folder for the layer
    layer_folder = f"{layer['UUID']}/"  # The folder within the zip

    # Step 2: Extract the chunk positions (x, y) from the layer folder
    lz4_files = [f for f in zip_ref.namelist() if f.startswith(layer_folder) and f.endswith(".lz4")]

    # Step 3: Extract chunk positions (x, y) from filenames like "2~3.lz4"
    chunk_positions = {}
    for filename in lz4_files:
        if "~" in filename:
            chunk_name = filename.split(".lz4")[0].split("/")[-1]  # Get the chunk name
            x, y = map(int, chunk_name.split("~"))
            chunk_positions[(x, y)] = filename

    # Step 4: Create a 2D grid for the chunks, with initial empty data
    grid_width = grid_dimensions[0]
    grid_height = grid_dimensions[1]
    grid = np.zeros((grid_height, grid_width), dtype=object)  # Each cell holds chunk data

    # Step 5: Place chunks in the grid
    for (x, y), chunk_file in chunk_positions.items():
        file_data = zip_ref.read(chunk_file)
        decompressed_data = extract_images_from_lz4(file_data)

        try:
            img_array = np.frombuffer(decompressed_data, dtype=np.uint8).reshape((chunk_size, chunk_size, 4))
        except:
            pass
        grid[y, x] = img_array
    # Step 6: Fill missing chunks with empty data (transparent pixels)
    
    for row in range(grid_height):
        for col in range(grid_width):
            if np.all(grid[row, col] == 0):
                grid[row, col] = np.zeros((chunk_size, chunk_size, 4), dtype=np.uint8)

    # Step 7: Combine the chunks into a final image
    final_image = []

    for row in range(grid_height):
        row_data = []
        for col in range(grid_width):
            chunk = grid[row, col]
            row_data.append(chunk)
        final_image.append(np.concatenate(row_data, axis=1))  # Concatenate horizontally

    # Concatenate all rows vertically
    final_image = np.concatenate(final_image, axis=0)
    

    # Step 8: Convert to PIL image and save
    img = Image.fromarray(final_image, "RGBA")
    
    # Correct rotation and flips, needs more testing
    if orientation == 3:
        img = img.rotate(90, expand=True)
    elif orientation == 4:
        img = img.rotate(-90, expand=True)
    elif orientation == 2:
        img = img.rotate(180, expand=True)

    if flips[0] and (orientation == 1 or orientation == 2):
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if flips[0] and (orientation == 3 or orientation == 4):
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    if flips[1] and (orientation == 1 or orientation == 2):
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    if flips[1] and (orientation == 3 or orientation == 4):
        img = img.transpose(Image.FLIP_LEFT_RIGHT)

    img = img.crop(project_bb)
    img = img.transpose(Image.FLIP_LEFT_RIGHT)

    #Remove transparent pixels from 4 sides to reduce layer size, while retaining correct layer position.
    final_image = np.array(img)
    top_crop, bottom_crop, left_crop, right_crop = find_crop_bounds(final_image)
    img = Image.fromarray(final_image, "RGBA")
    img = img.crop((left_crop, top_crop, img.width - right_crop, img.height - bottom_crop))

    #Draw the watermark
    draw = ImageDraw.Draw(img)

    width, height = img.size
    font_size = min(width, height) // 8
    font = ImageFont.load_default()

    text_bbox = draw.textbbox((0, 0), watermark, font=font)
    text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])

    text_x = width - text_size[0] - 10
    text_y = height - text_size[1] - 10

    draw.rectangle(
        [text_x - 5, text_y - 5, text_x + text_size[0] + 5, text_y + font_size + 5],
        fill=(0, 0, 0, 128)
    )

    draw.text((text_x, text_y), watermark, fill="white", font=font)
    
    #Return image and starting coordinates on layer

    return (img,left_crop,top_crop)