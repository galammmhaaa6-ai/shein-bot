#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 SHEIN Price Calculator Bot v2.0 - Advanced Edition
نسخة متقدمة مع فئات منتجات وإدارة شاملة
"""

import os
import logging
import json
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# تحميل المتغيرات
load_dotenv()

# إعدادات الـ Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# المتغيرات
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# محاولة الحصول على ADMIN_ID بشكل آمن
try:
    admin_id_str = os.getenv('ADMIN_ID', '0')
    ADMIN_ID = int(admin_id_str) if admin_id_str and admin_id_str.isdigit() else None
except (ValueError, TypeError):
    ADMIN_ID = None

# ملفات التخزين
CONFIG_FILE = 'config.json'

# حالات المحادثة
CATEGORY_SELECTION, PRICE_INPUT, ADMIN_MENU, SET_RATE, SET_CATEGORY_FEE, SET_OTHER_FEE, SET_WHATSAPP = range(7)

# الإعدادات الافتراضية
DEFAULT_CONFIG = {
    'exchange_rate': 3400,
    'clothing_fee': 5000,
    'other_fee': 3000,
    'whatsapp': '+963123456789'
}


def load_config():
    """تحميل الإعدادات"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # تأكد أن جميع المفاتيح موجودة
                config = DEFAULT_CONFIG.copy()
                config.update(loaded)
                return config
        except Exception as e:
            logger.warning(f"خطأ في تحميل config.json: {e}")
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """حفظ الإعدادات"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def format_currency(amount: float) -> str:
    """تنسيق العملة"""
    return f"{amount:,.0f}"


def calculate_final_price(base_price: float, category: str, config: dict) -> float:
    """حساب السعر النهائي حسب الفئة"""
    exchange_rate = config.get('exchange_rate', DEFAULT_CONFIG['exchange_rate'])
    
    if category == 'clothing':
        fee = config.get('clothing_fee', DEFAULT_CONFIG['clothing_fee'])
    else:
        fee = config.get('other_fee', DEFAULT_CONFIG['other_fee'])
    
    final_price = (base_price * exchange_rate) + fee
    return final_price


# ==================== Admin Handlers ====================

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """قائمة الإدارة للمسؤول"""
    if ADMIN_ID and update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ أنت لا تملك صلاحية الوصول إلى قائمة الأدمن")
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("💱 تحديث سعر الصرف", callback_data='set_rate')],
        [InlineKeyboardButton("👕 أجور الملابس والأحذية والحقائب", callback_data='set_clothing_fee')],
        [InlineKeyboardButton("🎁 أجور المنتجات الأخرى", callback_data='set_other_fee')],
        [InlineKeyboardButton("📱 رقم الواتس", callback_data='set_whatsapp')],
        [InlineKeyboardButton("📊 عرض الإعدادات الحالية", callback_data='show_config')],
        [InlineKeyboardButton("❌ إلغاء", callback_data='cancel')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 <b>قائمة الإدارة</b>\n\nاختر ما تريد تعديله:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    return ADMIN_MENU


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة أزرار الإدارة"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'set_rate':
        await query.edit_message_text("💱 أرسل سعر الصرف الجديد (مثال: 3500)")
        return SET_RATE
    
    elif query.data == 'set_clothing_fee':
        await query.edit_message_text("👕 أرسل أجور الملابس والأحذية والحقائب بالليرة السورية")
        return SET_CATEGORY_FEE
    
    elif query.data == 'set_other_fee':
        await query.edit_message_text("🎁 أرسل أجور المنتجات الأخرى بالليرة السورية")
        return SET_OTHER_FEE
    
    elif query.data == 'set_whatsapp':
        await query.edit_message_text("📱 أرسل رقم الواتس (مثال: +963123456789)")
        return SET_WHATSAPP
    
    elif query.data == 'show_config':
        config = load_config()
        msg = f"""
📊 <b>الإعدادات الحالية</b>

💱 سعر الصرف: <b>1 ر.س = {format_currency(config['exchange_rate'])} ل.س</b>

👕 أجور الملابس والأحذية والحقائب: <b>{format_currency(config['clothing_fee'])} ل.س</b>

🎁 أجور المنتجات الأخرى: <b>{format_currency(config['other_fee'])} ل.س</b>

📱 رقم الواتس: <code>{config['whatsapp']}</code>

📐 <b>أمثلة على الحسابات:</b>
• منتج ملابس بـ 150 ر.س = {format_currency(calculate_final_price(150, 'clothing', config))} ل.س
• منتج آخر بـ 150 ر.س = {format_currency(calculate_final_price(150, 'other', config))} ل.س
        """
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    
    elif query.data == 'cancel':
        await query.edit_message_text("❌ تم الإلغاء")
        return ConversationHandler.END


async def set_rate_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال سعر الصرف الجديد"""
    try:
        new_rate = float(update.message.text)
        
        if new_rate <= 0:
            await update.message.reply_text("❌ السعر يجب أن يكون أكبر من صفر")
            return SET_RATE
        
        config = load_config()
        old_rate = config['exchange_rate']
        config['exchange_rate'] = new_rate
        save_config(config)
        
        msg = f"""
✅ <b>تم تحديث سعر الصرف!</b>

❌ القديم: 1 ر.س = {old_rate} ل.س
✅ الجديد: 1 ر.س = {new_rate} ل.س
        """
        
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ يجب أن تكون قيمة صحيحة")
        return SET_RATE


async def set_clothing_fee_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال أجور الملابس"""
    try:
        new_fee = float(update.message.text)
        
        if new_fee < 0:
            await update.message.reply_text("❌ الأجور لا يمكن أن تكون سالبة")
            return SET_CATEGORY_FEE
        
        config = load_config()
        old_fee = config['clothing_fee']
        config['clothing_fee'] = new_fee
        save_config(config)
        
        msg = f"""
✅ <b>تم تحديث أجور الملابس والأحذية والحقائب!</b>

❌ القديم: {format_currency(old_fee)} ل.س
✅ الجديد: {format_currency(new_fee)} ل.س
        """
        
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ يجب أن تكون قيمة صحيحة")
        return SET_CATEGORY_FEE


async def set_other_fee_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال أجور المنتجات الأخرى"""
    try:
        new_fee = float(update.message.text)
        
        if new_fee < 0:
            await update.message.reply_text("❌ الأجور لا يمكن أن تكون سالبة")
            return SET_OTHER_FEE
        
        config = load_config()
        old_fee = config['other_fee']
        config['other_fee'] = new_fee
        save_config(config)
        
        msg = f"""
✅ <b>تم تحديث أجور المنتجات الأخرى!</b>

❌ القديم: {format_currency(old_fee)} ل.س
✅ الجديد: {format_currency(new_fee)} ل.س
        """
        
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ يجب أن تكون قيمة صحيحة")
        return SET_OTHER_FEE


async def set_whatsapp_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال رقم الواتس"""
    whatsapp = update.message.text.strip()
    
    if not whatsapp or len(whatsapp) < 5:
        await update.message.reply_text("❌ رقم الواتس غير صحيح")
        return SET_WHATSAPP
    
    config = load_config()
    old_whatsapp = config['whatsapp']
    config['whatsapp'] = whatsapp
    save_config(config)
    
    msg = f"""
✅ <b>تم تحديث رقم الواتس!</b>

❌ القديم: <code>{old_whatsapp}</code>
✅ الجديد: <code>{whatsapp}</code>

سيتم إرسال هذا الرقم للمستخدمين عند حسابهم للسعر
    """
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    return ConversationHandler.END


# ==================== User Handlers ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالج /start"""
    user_name = update.message.from_user.first_name or "المستخدم"
    config = load_config()
    
    welcome = f"""
════════════════════════════════════
🛍️ <b>بوت حاسبة أسعار SHEIN</b> 🛍️
════════════════════════════════════

مرحباً يا {user_name}! 👋

📝 <b>كيفية الاستخدام:</b>

1️⃣ اختر <b>فئة المنتج</b>
2️⃣ تأكد من <b>الإعدادات</b> في التطبيق
3️⃣ أرسل <b>السعر</b> من متجر SHEIN
4️⃣ احصل على <b>السعر النهائي</b>
5️⃣ تواصل معنا عبر <b>الواتس</b>

════════════════════════════════════

⚠️ <b>تنبيه مهم جداً!</b>

للحصول على السعر الدقيق تأكد من:
✓ تطبيق SHEIN <b>الرسمي</b>
✓ الدول: <b>المملكة العربية السعودية 🇸🇦</b>
✓ العملة: <b>الريال السعودي (SAR)</b>

════════════════════════════════════

💰 <b>الأسعار الحالية:</b>
👕 الملابس والأحذية: {format_currency(config['clothing_fee'])} ل.س
🎁 المنتجات الأخرى: {format_currency(config['other_fee'])} ل.س

جاهز؟ اختر فئة المنتج! 👇
    """
    
    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)
    
    # عرض اختيار الفئة
    keyboard = [
        [InlineKeyboardButton("👕 ملابس وأحذية وحقائب", callback_data='cat_clothing')],
        [InlineKeyboardButton("🎁 منتجات أخرى", callback_data='cat_other')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛍️ <b>اختر فئة المنتج الذي تريد حساب سعره:</b>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    return CATEGORY_SELECTION


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة اختيار الفئة"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cat_clothing':
        category = 'clothing'
        category_name = '👕 ملابس وأحذية وحقائب'
    else:
        category = 'other'
        category_name = '🎁 منتجات أخرى'
    
    context.user_data['category'] = category
    
    config = load_config()
    
    warning = f"""
════════════════════════════════════
⚠️ <b>تنبيه مهم جداً!</b> ⚠️
════════════════════════════════════

لكي تحصل على <b>السعر الدقيق</b> تأكد من:

✓ <b>فتحت تطبيق SHEIN الرسمي</b> (لا التطبيق المقلد)
✓ <b>اخترت الدول:</b> المملكة العربية السعودية 🇸🇦
✓ <b>اخترت العملة:</b> الريال السعودي (SAR) 💱
✓ <b>المنتج المختار:</b> {category_name}

════════════════════════════════════

💰 <b>أسعار الشحن الحالية:</b>
👕 الملابس والأحذية والحقائب: {format_currency(config['clothing_fee'])} ل.س
🎁 المنتجات الأخرى: {format_currency(config['other_fee'])} ل.س

════════════════════════════════════

📝 <b>الآن أرسل سعر المنتج كما يظهر بالتطبيق بالضبط</b>

مثال: أرسل <code>150</code> أو <code>99.99</code> أو <code>250.5</code>
    """
    
    await query.edit_message_text(warning, parse_mode=ParseMode.HTML)
    return PRICE_INPUT


async def price_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال سعر المنتج"""
    try:
        base_price = float(update.message.text.strip())
        
        if base_price <= 0:
            await update.message.reply_text("❌ السعر يجب أن يكون أكبر من صفر!")
            return PRICE_INPUT
        
        category = context.user_data.get('category', 'other')
        config = load_config()
        
        final_price = calculate_final_price(base_price, category, config)
        price_without_fee = base_price * config['exchange_rate']
        
        if category == 'clothing':
            fee = config['clothing_fee']
            fee_type = '👕 أجور الملابس والأحذية والحقائب'
        else:
            fee = config['other_fee']
            fee_type = '🎁 أجور المنتجات الأخرى'
        
        result = f"""
════════════════════════════════════
💸 <b>السعر النهائي</b> 💸
════════════════════════════════════

📝 <b>السعر من SHEIN (SAR):</b>
{format_currency(base_price)} ريال سعودي 🇸🇦

📊 <b>تفصيل الحساب:</b>
┌─────────────────────────────────
├─ السعر الأصلي: {format_currency(base_price)} ر.س
├─ × سعر الصرف: {format_currency(config['exchange_rate'])} ل.س/ر.س
├─ = ({format_currency(price_without_fee)} ل.س)
├─ + {fee_type}
├─ {format_currency(fee)} ل.س
└─────────────────────────────────

💰 <b>🎯 السعر النهائي:</b>
<b>{format_currency(final_price)} ليرة سورية 🇸🇾</b>

════════════════════════════════════

✅ <b>الخطوات التالية:</b>

1️⃣ <b>خذ لقطة شاشة (Screenshot) للسعر الذي ظهر أعلاه</b>
   (من هذه الرسالة)

2️⃣ <b>افتح تطبيق SHEIN وانسخ رابط المنتج</b>
   (أي منتج من رابط المشاركة)

3️⃣ <b>افتح الواتس واضغط على الرقم أدناه</b>

📱 <b>رقم الواتس للتواصل:</b>
<a href="https://wa.me/{config['whatsapp'].replace('+', '')}">{config['whatsapp']}</a>

4️⃣ <b>أرسل رسالة تتضمن:</b>
   ✓ لقطة الشاشة (السعر من البوت)
   ✓ صورة المنتج من SHEIN
   ✓ رابط المنتج من SHEIN

💬 <b>مثال الرسالة:</b>
"أريد طلب هذا المنتج
السعر: {format_currency(final_price)} ل.س
[أرسل لقطة الشاشة من البوت + صورة المنتج + رابطه]"

════════════════════════════════════
    """
        
        await update.message.reply_text(result, parse_mode=ParseMode.HTML)
        
        # عرض خيار لحساب منتج آخر
        keyboard = [
            [InlineKeyboardButton("🔄 حساب منتج آخر", callback_data='start_again')],
            [InlineKeyboardButton("❌ إنهاء", callback_data='exit')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "ماذا تريد أن تفعل الآن؟",
            reply_markup=reply_markup
        )
        
        return CATEGORY_SELECTION
        
    except ValueError:
        await update.message.reply_text(
            "❌ هذا ليس رقم صحيح!\n\n"
            "أرسل السعر بالأرقام فقط (مثال: <code>150</code>)",
            parse_mode=ParseMode.HTML
        )
        return PRICE_INPUT


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة أزرار إضافية"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start_again':
        keyboard = [
            [InlineKeyboardButton("👕 ملابس وأحذية وحقائب", callback_data='cat_clothing')],
            [InlineKeyboardButton("🎁 منتجات أخرى", callback_data='cat_other')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🛍️ <b>اختر فئة المنتج الجديد:</b>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return CATEGORY_SELECTION
    
    elif query.data == 'exit':
        await query.edit_message_text("👋 شكراً لاستخدامك البوت! استقبلك بسرور لاحقاً")
        return ConversationHandler.END


def main() -> None:
    """تشغيل البوت"""
    if not TELEGRAM_TOKEN:
        logger.error("❌ لم يتم تعيين TELEGRAM_BOT_TOKEN")
        return
    
    logger.info("✅ بدء البوت...")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # مسار المحادثة العام
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("admin", admin_menu)
        ],
        states={
            CATEGORY_SELECTION: [CallbackQueryHandler(category_callback, pattern='^cat_')],
            PRICE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, price_input)],
            ADMIN_MENU: [CallbackQueryHandler(admin_callback)],
            SET_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_rate_input)],
            SET_CATEGORY_FEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_clothing_fee_input)],
            SET_OTHER_FEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_other_fee_input)],
            SET_WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_whatsapp_input)],
        },
        fallbacks=[CallbackQueryHandler(callback_handler, pattern='^(start_again|exit)$')]
    )
    
    app.add_handler(conv_handler)
    
    logger.info("✅ البوت يعمل الآن... (Ctrl+C للإيقاف)")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("🛑 البوت توقف")


if __name__ == '__main__':
    main()
