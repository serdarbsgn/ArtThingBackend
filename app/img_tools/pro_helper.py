import numpy as np
from pyprocreate import Project
from PIL import ImageDraw, ImageFont,Image
#Copy of the psd_helper, not checked yet.
def pro_check(filename):
    try:
        pro = Project(filename)
        print(pro.name)
        return pro
    except Exception as e:
        print(e)
        return None
    
def layered_images(filepath,artist,save_location):
    pro = pro_check(filepath)
    if pro is None:
        return None
    watermark_text = artist
    images = []
    viewbox = pro.bounding_rect
    viewbox_x_min, viewbox_y_min, viewbox_x_max, viewbox_y_max = viewbox

    for i, layer in enumerate(pro):
        if layer.visible:
            pil_image = layer.get_image_data()
            if pil_image.mode == "CMYK": #CMYK TO RGBA conversion needs a little help with alpha channels.
                try:
                    alpha_channel  = (layer.numpy()[..., 4] * 255).astype(np.uint8)
                    alpha_channel_image = Image.new('L', pil_image.size)  
                    alpha_channel_image.putdata(alpha_channel.flatten())
                    pil_image = pil_image.convert("RGB")
                    pil_image.putalpha(alpha_channel_image)
                except:
                    pil_image = pil_image.convert("RGBA")
            else:
                pil_image = pil_image.convert("RGBA")
            layer_bbox = layer.bbox 
            layer_x_min, layer_y_min, layer_x_max, layer_y_max = layer_bbox

            crop_left = max(viewbox_x_min, layer_x_min)
            crop_top = max(viewbox_y_min, layer_y_min)
            crop_right = min(viewbox_x_max, layer_x_max)
            crop_bottom = min(viewbox_y_max, layer_y_max)

            crop_box = (
                crop_left - layer_x_min,
                crop_top - layer_y_min,
                crop_right - layer_x_min,
                crop_bottom - layer_y_min
            )
            pil_image = pil_image.crop(crop_box)
            draw = ImageDraw.Draw(pil_image)

            width, height = pil_image.size
            font_size = min(width, height) // 16
            font = ImageFont.load_default()

            text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])

            text_x = width - text_size[0] - 10
            text_y = height - text_size[1] - 10

            draw.rectangle(
                [text_x - 5, text_y - 5, text_x + text_size[0] + 5, text_y + font_size + 5],
                fill=(0, 0, 0, 128)
            )

            draw.text((text_x, text_y), watermark_text, fill="white", font=font)
            new_position_x = crop_left - viewbox_x_min
            new_position_y = crop_top - viewbox_y_min
            images.append((pil_image, new_position_x, new_position_y))

    canvas_width = viewbox_x_max - viewbox_x_min
    canvas_height = viewbox_y_max - viewbox_y_min        
    final_image = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 0))
    min_x = min(img[1] for img in images)
    min_y = min(img[2] for img in images)

    for i, (image, x, y) in enumerate(images):
        new_x = x - min_x
        new_y = y - min_y
        final_image.alpha_composite(image, (new_x, new_y))
        image.save(f'{save_location}/{i}_{new_x}_{new_y}.png')
    final_image.thumbnail((300,300))
    final_image.save(f'{save_location}/thumbnail.png')
    return len(images)