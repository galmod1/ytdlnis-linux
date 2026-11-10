# المساهمة والإصدارات — YTDLnis Linux

شكراً لاهتمامك. هذا الملف يوضّح كيف يُصدر أي شخص نسخة جديدة، وكيف يبقى المشروع حياً دون الاعتماد على مطوّر واحد.

## بيئة التطوير

- Python 3 + PyGObject/GTK4
- `yt-dlp` و`ffmpeg` (وaria2c اختيارياً) على النظام
- التشغيل: `./run.sh`
- فحص سريع قبل أي دفع: `python3 -m compileall -q main.py core ui`

## الإصدار (خطوات كاملة)

1. حدّث `CHANGELOG.md` ورقم النسخة في `core/version.py`.
2. تأكد أن الترجمة والاختبارات اليدوية تعمل (تشغيل، تنزيل، قص، ترجمة، إعدادات).
3. أنشئ وسم الإصدار:
   ```
   git tag vX.Y.Z
   git push origin main --tags
   ```
4. أنشئ Release على GitHub مع ملاحظات التغيير.
5. ابنِ حزمة Flatpak:
   ```
   flatpak-builder --user --install --force-clean builddir flatpak/org.galmod.ytdlnis.linux.yaml
   flatpak build-bundle builddir org.galmod.ytdlnis.linux-X.Y.Z.flatpak org.galmod.ytdlnis.linux master
   ```
   وأرفق ملف `.flatpak` بالإصدار.

## النشر على Flathub

1. أنشئ fork لمستودع `flathub/flathub` وأضف ملف manifest.
2. أضف `x-checker-data` (موجود مسبقاً لمكوّن yt-dlp) ليفتح البوت طلبات تحديث تلقائية عند كل إصدار yt-dlp.
3. بعد القبول، التحديثات اللاحقة تكون بطلب تغيير (PR) على مستودع التطبيق في Flathub: تحديث رقم الإصدار/الوسم ثم الدمج.

## ضمان استمرارية المشروع (Bus factor)

- **أضف مصانين**: أي شخص لديه صلاحية على مستودع GitHub يمكنه إصدار نسخ. أضف مصانين موثوقين من إعدادات المستودع.
- **ملكية Flathub**: يمكن نقل ملكية تطبيق Flathub أو إضافة مصانين من صفحة التطبيق على Flathub.
- **الاعتماد على محدّث المحرك**: حتى لو توقفت إصدارات الحزمة، محدّث yt-dlp الداخلي يبقي التنزيلات تعمل. راجع `core/engine_update.py`.
- **الترخيص GPL-3.0**: يسمح لأي طرف بعمل fork وإكمال المشروع.

## أسلوب الكود

- Python مسطّح بلا اعتماديات ثقيلة، GTK4/PyGObject فقط.
- النصوص كلها في `core/i18n.py` (عربي/إنجليزي/فرنسي) — لا نصوص مكتوبة مباشرة في الواجهة.
- أزرار الإجراءات توضع في جسم النافذة لا في `Gtk.HeaderBar` (بعض بيئات KDE تخفيها).
- أي تغيير في الواجهة يُختبر بتشغيل فعلي، لا بالاكتفاء بالتجميع.
