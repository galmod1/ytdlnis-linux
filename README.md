# YTDLnis Linux

واجهة لينكس أصلية (GTK4) للتحميل من يوتيوب وأكثر من ألف موقع، فوق محرّك [yt-dlp](https://github.com/yt-dlp/yt-dlp).
مستوحاة من تطبيق [YTDLnis](https://github.com/deniscerri/ytdlnis) للأندرويد (GPL-3.0).

**الإصدار:** 0.1.0 — [سجل التغييرات](CHANGELOG.md)

## المتطلبات

| الأداة | الحاجة | ملاحظات |
|---|---|---|
| Python 3 + GTK4 (PyGObject) | أساسي | متوفرة افتراضياً في دبيان/أوبونتو الحديثة |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | أساسي | المحرّك |
| [ffmpeg](https://ffmpeg.org) | أساسي | لدمج الصوت مع الفيديو وتحويل الصيغ |
| [aria2c](https://aria2.github.io) | اختياري | فقط إن فعّلت محرّك التسريع |

على دبيان/أوبونتو:

```
sudo apt install python3-gi gir1.2-gtk-4.0 ffmpeg aria2c
pipx install yt-dlp   # أو أي طريقة تفضّلها لتثبيت yt-dlp
```

## التشغيل

```
./run.sh
```

أو من قائمة التطبيقات: **YTDLnis Linux**.

## الاستخدام السريع

1. الصق رابطاً أو أكثر في الشريط الأعلى (كل رابط في سطر) واضغط «إضافة» — أو اكتب عبارة بحث
2. العناصر تظهر في تبويب «الرئيسية» جاهزة
3. اضغط «تنزيل» لتحميلها بأفضل جودة، أو «الصيغة…» لاختيار دقيق
4. تابع التقدّم في تبويب «جارٍ التحميل الآن»؛ وعند الاكتمال تجد الملف في تبويب «مكتملة» بزرّي «فتح الملف» و«فتح المجلد»

## المزايا الحالية

- تحميل فيديو وصوت من كل موقع يدعمه yt-dlp
- روابط متعددة دفعة واحدة، أو بحث مباشر
- قوائم التشغيل: تفكيك، «تحميل الكل»، صيغة واحدة لكل القائمة، «إيقاف الكل»
- اختيار الصيغة: أفضل جودة، 1080p/720p، MP3/M4A، أو تنسيق محدّد
- طابور بتقدّم وسرعة ووقت متبقٍّ؛ إيقاف/متابعة/إلغاء/إعادة؛ تحميلات متزامنة (1–8)
- تبويبات حالة: الرئيسية، قوائم التشغيل، جارٍ التحميل، في الانتظار، موقوفة، مكتملة، فاشلة، ملغاة
- **ثلاث لغات**: العربية، English، Français (تُختار من الإعدادات، تُطبَّق بعد إعادة التشغيل)
- مظهر داكن / فاتح / تلقائي (حسب النظام) من الإعدادات ويُطبَّق فوراً
- محرّك aria2c اختياري (حتى 16 اتصالاً للملف) وأجزاء متزامنة للبث المقطّع
- حدّ سرعة عام
- تضمين الصورة والبيانات الوصفية، الترجمة، إزالة SponsorBlock
- كوكيز المتصفح **أو ملف كوكيز (cookies.txt) مستقل يتقدّم عليه**، مع منتقي ملفات داخلي وزر «استيراد من Firefox» يصدّر كوكيز يوتيوب/جوجل إلى ملف محلي بصلاحيات 600
- بروكسي، وسائط yt-dlp إضافية
- منتقي مجلدات داخلي لتغيير مسار الحفظ، وقالب اسم ملف
- قصّ الفيديو بالثواني، وتقسيمه إلى ملف لكل فصل
- فتح الملف/المجلد مباشرة من صف التحميل المكتمل

## الإعدادات والملفات

- الإعدادات: `~/.config/ytdlnis-linux/config.json`
- سجلّ التشخيص: `~/.config/ytdlnis-linux/app.log` و`save.log`
- التحميلات: المجلد الذي تختاره من الإعدادات (افتراضياً `~/Downloads`)

## الخصوصية

البرنامج محلي بالكامل: لا حسابات، لا تحليلات، لا تتبّع، ولا خوادم لنا.
التفاصيل في [PRIVACY.md](PRIVACY.md).

## الترخيص

- الشيفرة: **GNU GPL v3.0** — راجع [LICENSE](LICENSE)
- مستوحى من YTDLnis للمطوّر Denis Çerri (GPL-3.0) — هذا المشروع مستقل وغير مرتبط رسمياً به
- أيقونة التطبيق: Flaticon (رخصة Flaticon المجانية، تتطلب الإسناد) — راجع [CREDITS.md](CREDITS.md)

## بنية المشروع

```
main.py              نقطة الدخول (Gtk.Application)
core/version.py      رقم الإصدار
core/i18n.py         الترجمات (ar/en/fr)
core/settings.py     الإعدادات
core/models.py       عنصر التحميل والأدوات
core/ytdlp.py        أوامر yt-dlp وقراءة المعلومات
core/downloader.py   الطابور والعمليات والتقدّم
ui/window.py         النافذة الرئيسية والتبويبات وصفوف التحميل
ui/dialogs.py        الإعدادات، منتقي الصيغة، منتقي المجلدات
assets/style.css     التنسيقات
run.sh               ملف التشغيل
```

## المراحل القادمة

- تاريخ التحميلات ومنع التكرار، جلب الترجمة ومقاطع الفصول
- جدولة زمنية، مراقبة الحافظة، ملف روابط txt
- قصّ الفيديو بالثواني والفصول، تقسيمه، حرق الترجمة
- مراقبة القنوات وقوائم التشغيل الجديدة
- النسخ الاحتياطي والاستعادة
- تغليف Flatpak

## Flatpak

حزمة جاهزة للبناء الذاتي:

```
flatpak/org.galmod.ytdlnis.linux.yaml   وصفة البناء
flatpak/build.sh                        بناء وتثبيت للمستخدم الحالي (بلا كلمة مرور)
```

المتطلبات مرة واحدة: أدوات البناء من Flathub:

```
flatpak install --user flathub org.flatpak.Builder org.gnome.Platform//50 org.gnome.Sdk//50
```

ثم:

```
./flatpak/build.sh
flatpak run org.galmod.ytdlnis.linux
```

الصلاحيات الممنوحة: الشبكة، Wayland/X11، القرص الرسومي، مجلد التحميلات (xdg-download)، وقراءة فقط لمجلدَي Firefox وLibreWolf لزر استيراد الكوكيز. لا وصول لباقي ملفات المنزل.

لإخراج ملف واحد قابل للمشاركة:

```
flatpak build-bundle exportrepo org.galmod.ytdlnis.linux-0.1.0.flatpak org.galmod.ytdlnis.linux master
```

المستلم يثبّته بـ `flatpak install org.galmod.ytdlnis.linux-0.1.0.flatpak` (يحتاج Flathub لتنزيل طبقة GNOME//50 مرة واحدة).

ملاحظة: داخل الحزمة، ثيم النظام من GNOME (Adwaita) وليس ثيم سطح المكتب؛ اختر «داكن/فاتح» من الإعدادات.


## إخلاء المسؤولية

- هذا البرنامج أداة تقنية محايدة لتحميل المحتوى من المواقع التي يدعمها محرّك yt-dlp.
- يقع على عاتق المستخدم وحده التأكد من أن استخدامه يوافق قوانين بلده، وشروط خدمة المواقع، وحقوق أصحاب المحتوى.
- المطوّر غير مسؤول عن أي استخدام مخالف، ولا عن أي محتوى يُحمَّل بواسطة البرنامج.
- المقصود بالبرنامج الاستخدام الشخصي؛ ولا يجوز استخدامه لإعادة نشر أو بيع محتوى محمي بحقوق النشر.
- البرنامج لا يتجاوز حماية DRM ولا يفكّ تشفير المحتوى المدفوع.
- البرنامج غير مرتبط ولا مدعوم من أي منصة محتوى، ولا من مشروع YTDLnis الأصلي.

### Disclaimer (English)

This software is a neutral technical tool. Users are solely responsible for ensuring their use complies with local laws, the terms of service of the sites involved, and copyright. The developer is not liable for any misuse or for content downloaded with it. It is intended for personal use; redistributing or selling copyrighted content is prohibited. The software does not circumvent DRM. Not affiliated with any content platform or with the original YTDLnis project.

## التحديثات واستمرارية المشروع

البرنامج مصمّم ليبقى يعمل حتى لو توقّف مطوّره الأصلي عن النشر:

1. **محرّك yt-dlp يُحدَّث ذاتياً**: عند البدء (أو بزر «تحديث المحرك الآن» في الإعدادات ← الشبكة والكوكيز) يتحقق البرنامج من أحدث إصدار رسمي على GitHub، وينزّله إلى مجلد بيانات التطبيق القابل للكتابة، **ويتحقق من بصمة SHA-256** قبل تشغيله. يعمل داخل عزل Flatpak بلا صلاحيات إضافية، ويعود للنسخة المجمّدة إن فشل التنزيل.
   - المسار: `~/.var/app/org.galmod.ytdlnis.linux/data/ytdlnis-linux/bin/yt-dlp` (داخل Flatpak)، أو `~/.local/share/ytdlnis-linux/bin/yt-dlp` (محلياً).
2. **ffmpeg وطبقة GNOME** تتحدّث مع `flatpak update` — لا علاقة لها بالمطوّر.
3. **تحديث الحزمة نفسها**: عند نشر التطبيق على Flathub يصل التحديث للمستخدم تلقائياً عبر Discover/GNOME Software أو `flatpak update`.
4. **لو غاب المطوّر**: المستودع GPL-3.0، وخطوات الإصدار موثّقة في `CONTRIBUTING.md`، وملف Flatpak يحتوي `x-checker-data` ليفتح بوت Flathub طلب تحديث تلقائي عند كل إصدار yt-dlp. أي شخص يمكنه تبنّي المستودع، أو إضافة مصانين، أو نقل ملكية تطبيق Flathub.

## Contributing

Pull requests and issues are welcome. The UI is translated in `core/i18n.py`.

---

## English

A native GTK4 desktop front-end for yt-dlp (inspired by YTDLnis for Android), with a download queue, per-item and whole-playlist format selection, aria2c acceleration, speed limiting, and an Arabic/English/French UI.

**Requirements:** Python 3 + PyGObject/GTK4, yt-dlp, ffmpeg (aria2c optional).
Run with `./run.sh`. Licensed GPL-3.0; see LICENSE. Privacy: PRIVACY.md.
