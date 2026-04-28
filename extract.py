import os
import re

def extract_files(text_file_path):
    print(f"🔍 جاري قراءة الملف: {text_file_path}")
    
    try:
        with open(text_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ لم يتم العثور على الملف '{text_file_path}'. تأكد من وجوده في نفس المجلد.")
        return

    # البحث عن كل بلوك كود محصور بين <file path="..."> و </file>
    pattern = r'<file path="(.*?)">\n?(.*?)\n?</file>'
    matches = re.finditer(pattern, content, re.DOTALL)

    count = 0
    for match in matches:
        file_path = match.group(1).strip()
        file_content = match.group(2)

        # إنشاء المجلدات الفرعية تلقائياً إذا لم تكن موجودة (مثل engine/ أو tools/)
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        # كتابة الكود داخل الملف المخصص له
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content + '\n')
        
        print(f"✅ تم إنشاء: {file_path}")
        count += 1
    
    if count > 0:
        print(f"\n🎉 السحر اكتمل! تم بناء المعمارية واستخراج {count} ملف بنجاح.")
    else:
        print("\n⚠️ لم يتم العثور على أي ملفات. تأكد أن الملف يحتوي على صيغة <file path=...>")

if __name__ == "__main__":
    # اسم الملف النصي الذي حصلنا عليه من كلود
    extract_files("Claud_Output.txt")
