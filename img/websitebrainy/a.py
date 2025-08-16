import os
import re
from moviepy.editor import CompositeVideoClip, ImageClip, VideoFileClip, AudioFileClip
from moviepy.video.fx.all import fadein, fadeout, resize
from PIL import Image
import numpy as np

# إعدادات
image_duration = 5      # مدة عرض كل صورة بالثواني
output_folder = "videos"
audios_folder = "audios"          # مجلد ملفات الصوت (1.wav، 2.wav، ...)
final_output_folder = "final_videos"  # مجلد الفيديوهات بعد دمج الصوت

# إنشاء مجلدات الإخراج لو مش موجودة
os.makedirs(output_folder, exist_ok=True)
os.makedirs(final_output_folder, exist_ok=True)

# جلب الصور وترتيبها
images = [img for img in os.listdir('.') if img.lower().endswith(".jpg")]
images.sort(key=lambda x: int(re.search(r'\d+', x).group()))

# ترتيب ملفات الصوت حسب الرقم في الاسم
audio_files = [f for f in os.listdir(audios_folder) if f.lower().endswith(('.wav', '.mp3'))]
audio_files.sort(key=lambda x: int(re.search(r'\d+', x).group()))

def create_effect_clip(img_array, effect_idx):
    clip = ImageClip(img_array, duration=image_duration)
    
    # تأثير التكبير (zoom)
    def zoom(t):
        if t < 1:  # دخول ناعم (زوم من 80% → 100%)
            return 0.8 + 0.2 * (t / 1)
        elif t < 4:  # ثبات
            return 1.0
        else:  # خروج ناعم
            return 1.0 + 0.05 * ((t - 4) / 1)
    
    zoomed = clip.fx(resize, lambda t: zoom(t))
    
    # تأثيرات حركة (slide)
    def slide_down(t):
        if t < 0.5:
            return ('center', -1.0 + 2.0 * t / 0.5)
        elif t < 4.5:
            return ('center', 0)
        else:
            return ('center', 0 - 2.0 * (t - 4.5) / 0.5)
    def slide_left(t):
        if t < 0.5:
            return (1.0 - 2.0 * t / 0.5, 'center')
        elif t < 4.5:
            return (0, 'center')
        else:
            return (0 + 2.0 * (t - 4.5) / 0.5, 'center')
    def slide_right(t):
        if t < 0.5:
            return (-1.0 + 2.0 * t / 0.5, 'center')
        elif t < 4.5:
            return (0, 'center')
        else:
            return (0 - 2.0 * (t - 4.5) / 0.5, 'center')
    def slide_up(t):
        if t < 0.5:
            return ('center', 1.0 - 2.0 * t / 0.5)
        elif t < 4.5:
            return ('center', 0)
        else:
            return ('center', 0 + 2.0 * (t - 4.5) / 0.5)
    
    slide_funcs = [slide_down, slide_left, slide_right, slide_up]
    slide_func = slide_funcs[effect_idx % 4]
    
    moved = zoomed.set_position(slide_func)
    final = moved.fx(fadein, 0.5).fx(fadeout, 0.5)
    return final

print("🚀 إنشاء الفيديوهات من الصور مع مراعاة مدة الصوت لكل فيديو...")

all_images = images.copy()
start_img_index = 0
video_paths = []

for idx, audio_file in enumerate(audio_files, start=1):
    audio_path = os.path.join(audios_folder, audio_file)
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    
    # حساب عدد الصور المطلوبة بناءً على مدة الصوت ومدة عرض الصورة
    num_images = int(audio_duration // image_duration)
    
    # لو عدد الصور المطلوب أكبر من المتبقي من الصور، نستخدم اللي موجود بس
    if start_img_index + num_images > len(all_images):
        num_images = len(all_images) - start_img_index
    
    part_images = all_images[start_img_index:start_img_index + num_images]
    start_img_index += num_images
    
    if not part_images:
        print(f"⚠️ لم يتبق صور للفيديو رقم {idx} مع ملف الصوت {audio_file}")
        audio_clip.close()
        break

    # تحديد الحجم الأكثر تكرارًا بين الصور المختارة
    sizes = {}
    for img_path in part_images:
        with Image.open(img_path) as img:
            sizes[img.size] = sizes.get(img.size, 0) + 1
    target_size = max(sizes, key=sizes.get)

    clips = []
    for i, img_path in enumerate(part_images):
        with Image.open(img_path) as img:
            if img.size != target_size:
                img = img.resize(target_size, Image.LANCZOS)
            img_array = np.array(img)

        clip = create_effect_clip(img_array, i)
        clips.append(clip.set_start(i * image_duration))

    video_clip = CompositeVideoClip(clips, size=target_size)
    video_clip.duration = len(part_images) * image_duration

    output_path = os.path.join(output_folder, f"video_{idx}.mp4")
    video_clip.write_videofile(output_path, fps=24)
    print(f"✅ تم إنشاء الفيديو {output_path}")
    video_paths.append(output_path)
    audio_clip.close()

print("🎬 بدء دمج الصوت مع الفيديوهات حسب الرقم في الاسم...")

for video_path in video_paths:
    base_name = os.path.basename(video_path)
    match = re.search(r'(\d+)', base_name)
    if not match:
        print(f"⚠️ لم أجد رقم في اسم الفيديو {base_name}، تم التخطي.")
        continue
    num = match.group(1)
    audio_file = f"{num}.wav"  # صيغة اسم ملف الصوت: 1.wav, 2.wav, ...
    audio_path = os.path.join(audios_folder, audio_file)
    if not os.path.exists(audio_path):
        print(f"⚠️ ملف الصوت {audio_file} غير موجود، تم تخطي دمجه مع {base_name}.")
        continue

    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)

    # ضبط مدة الفيديو حسب مدة الصوت (لو في فرق)
    video = video.set_duration(audio.duration)
    video = video.set_audio(audio)

    final_output_path = os.path.join(final_output_folder, base_name)
    video.write_videofile(final_output_path, fps=24)
    print(f"✅ تم دمج الفيديو {base_name} مع الصوت {audio_file} وحفظه في {final_output_path}")

print("🎉 تم الانتهاء من كل الفيديوهات مع الصوت!")


#  python a.py ; "(Roo/PS Workaround: 0)" > $null