#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 SHEIN Price Calculator Bot v2.0 - Advanced Edition (Render & USD Supported)
نسخة متقدمة مع فئات منتجات وإدارة شاملة ودعم حساب الدولار ومنصة Render
"""

import os
import logging
import json
import asyncio
import ssl
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# حاول استيراد pymongo، إن لم تكن مثبتة استخدم JSON
try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

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

# ملفات التخزين والقاعدة البيانات
CONFIG_FILE = 'config.json'
MONGO_URI = os.getenv('MONGO_URI', None)

# حالات المحادثة (تمت إضافة حالة سعر الدولار)
CATEGORY_SELECTION, PRICE_INPUT, ADMIN_MENU, SET_RATE, SET_USD_RATE, SET_CATEGORY_FEE, SET_OTHER_FEE, SET_WHATSAPP = range(8)

# الإعدادات الافتراضية (تمت إضافة usd_rate الافتراضي)
DEFAULT_CONFIG = {
    'exchange_rate': 3400,   # سعر صرف الريال السعودي مقابل السوري
    'usd_rate': 15000,       # سعر صرف الدولار مقابل السوري (قيمة افتراضية يمكن تعديلها)
    'clothing_fee': 5000,
    'other_fee': 3000,
    'whatsapp': '+963123456789'
}

# قاعدة البيانات
mongo_client = None
mongo_db = None

# ==================== خادم ويب وهمي لإرضاء منصة Render ====================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot is running successfully!".encode("utf-8"))

    def log_message(self, format, *args):
        # تعطيل طباعة الطلبات في الـ Terminal لتجنب امتلاء السجلات
        return

def run_health_server():
    """تشغيل خادم الويب على المنفذ المطلوب بواسطة Render"""
    port = int(os.getenv("PORT", 8080))
    try:
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logger.info(f"🚀 خادم فحص الحالة (Health Check) يعمل على المنفذ: {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"⚠️ فشل تشغيل خادم فحص الحالة: {e}")

# =========================================================================

def connect_to_mongo():
    """الاتصال بـ MongoDB مع دعم SSL"""
    global mongo_client, mongo_db
    try:
        if MONGO_AVAILABLE and MONGO_URI:
            mongo_client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                retryWrites=True,
                ssl=True,
                tlsAllowInvalidCertificates=True  # ✅ حل SSL errors
            )
            mongo_client.admin.command('ping')
            mongo_db = mongo_client['shein_bot']
            logger.info("✅ تم الاتصال بـ MongoDB")
            return True
    except Exception as e:
        logger.warning(f"⚠️ خطأ MongoDB: {e}. سيتم استخدام JSON بديل")
    return False


def load_config():
    """تحميل الإعدادات من MongoDB أو JSON"""
    # المحاولة الأولى: MongoDB
    if mongo_db:
        try:
            config_doc = mongo_db['config'].find_one({'_id': 'settings'})
            if config_doc:
                config_doc.pop('_id', None)
                config = DEFAULT_CONFIG.copy()
                config.update(config_doc)
                return config
        except Exception as e:
            logger.warning(f"خطأ في قراءة MongoDB: {e}")
    
    # المحاولة الثانية: JSON local
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(loaded)
                return config
        except Exception as e:
            logger.warning(f"خطأ في قراءة JSON: {e}")
    
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """حفظ الإعدادات في MongoDB و JSON معاً"""
    # حفظ في MongoDB
    if mongo_db:
        try:
            config_to_save = config.copy()
            config_to_save['_id'] = 'settings'
            mongo_db['config'].update_one(
                {'_id': 'settings'},
                {'$set': config_to_save},
                upsert=True
            )
            logger.info("✅ تم حفظ البيانات في MongoDB")
        except Exception as e:
            logger.warning(f"خطأ في حفظ MongoDB: {e}")
    
    # حفظ في JSON أيضاً (احتياطي)
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info("✅ تم حفظ البيانات في JSON")
    except Exception as e:
        logger.error(f"خطأ في حفظ JSON: {e}")


def format_currency(amount: float) -> str:
    """تنسيق العملة"""
    return f"{amount:,.0f}"


def calculate_final_price(base_price: float, category: str, config: dict) -> float:
    """حساب السعر النهائي بالليرة السورية حسب الفئة"""
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
        [InlineKeyboardButton("💱 تحديث سعر صرف (الريال)", callback_data='set_rate')],
        [InlineKeyboardButton("💵 تحديث سعر صرف (الدولار)", callback_data='set_usd_rate')],
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
        await query.edit_message_text("💱 أرسل سعر صرف الريال السعودي الجديد بالليرة (مثال: 3400)")
        return SET_RATE
    
    elif query.data == 'set_usd_rate':
        await query.edit_message_text("💵 أرسل سعر صرف الدولار الأمريكي الجديد بالليرة (مثال: 15000)")
        return SET_USD_RATE
    
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
        usd_rate = config.get('usd_rate', DEFAULT_CONFIG['usd_rate'])
        
        msg = f"""
📊 <b>الإعدادات الحالية</b>

💱 صرف الريال: <b>1 ر.س = {format_currency(config['exchange_rate'])} ل.س</b>
💵 صرف الدولار: <b>1 $ = {format_currency(usd_rate)} ل.س</b>

👕 أجور الملابس والأحذية والحقائب: <b>{format_currency(config['clothing_fee'])} ل.س</b>
🎁 أجور المنتجات الأخرى: <b>{format_currency(config['other_fee'])} ل.س</b>

📱 رقم الواتس: <code>{config['whatsapp']}</code>

📐 <b>أمثلة على الحسابات (شاملة السوري والدولار):</b>
• ملابس بـ 150 ر.س = {format_currency(calculate_final_price(150, 'clothing', config))} ل.س ({calculate_final_price(150, 'clothing', config) / usd_rate:.2f} $)
• منتج آخر بـ 150 ر.س = {format_currency(calculate_final_price(150, 'other', config))} ل.س ({calculate_final_price(150, 'other', config) / usd_rate:.2f} $)
        """
        await query.edit_message_text(msg, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    
    elif query.data == 'cancel':
        await query.edit_message_text("❌ تم الإلغاء")
        return ConversationHandler.END


async def set_rate_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال سعر صرف الريال الجديد"""
    try:
        new_rate = float(update.message.text)
        if new_rate <= 0:
            await update.message.reply_text("❌ السعر يجب أن يكون أكبر من صفر")
            return SET_RATE
        
        config = load_config()
        old_rate = config['exchange_rate']
        config['exchange_rate'] = new_rate
        save_config(config)
        
        msg = f"✅ <b>تم تحديث سعر صرف الريال!</b>\n\n❌ القديم: 1 ر.س = {old_rate} ل.س\n✅ الجديد: 1 ر.س = {new_rate} ل.س"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ يجب أن تكون قيمة صحيحة")
        return SET_RATE


async def set_usd_rate_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال سعر صرف الدولار الجديد"""
    try:
        new_rate = float(update.message.text)
        if new_rate <= 0:
            await update.message.reply_text("❌ السعر يجب أن يكون أكبر من صفر")
            return SET_USD_RATE
        
        config = load_config()
        old_rate = config.get('usd_rate', DEFAULT_CONFIG['usd_rate'])
        config['usd_rate'] = new_rate
        save_config(config)
        
        msg = f"✅ <b>تم تحديث سعر صرف الدولار!</b>\n\n❌ القديم: 1 $ = {format_currency(old_rate)} ل.س\n✅ الجديد: 1 $ = {format_currency(new_rate)} ل.س"
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ يجب أن تكون قيمة صحيحة")
        return SET_USD_RATE


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
        
        msg = f"✅ <b>تم تحديث أجور الملابس والأحذية والحقائب!</b>\n\n❌ القديم: {format_currency(old_fee)} ل.س\n✅ الجديد: {format_currency(new_fee)} ل.س"
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
        
        msg = f"✅ <b>تم تحديث أجور المنتجات الأخرى!</b>\n\n❌ القديم: {format_currency(old_fee)} ل.س\n✅ الجديد: {format_currency(new_fee)} ل.س"
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
    
    msg = f"✅ <b>تم تحديث رقم الواتس!</b>\n\n❌ القديم: <code>{old_whatsapp}</code>\n✅ الجديد: <code>{whatsapp}</code>\n\nسيتم إرسال هذا الرقم للمستخدمين عند حسابهم للسعر"
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    return ConversationHandler.END


# ==================== User Handlers ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالج /start"""
    user_name = update.message.from_user.first_name or "المستخدم"
    config = load_config()
    usd_rate = config.get('usd_rate', DEFAULT_CONFIG['usd_rate'])
    
    welcome = f"""
════════════════════════════════════
🛍️ <b>بوت حاسبة أسعار SHEIN</b> 🛍️
════════════════════════════════════

مرحباً يا {user_name}! 👋

📝 <b>كيفية الاستخدام:</b>

1️⃣ اختر <b>فئة المنتج</b>
2️⃣ تأكد من <b>الإعدادات</b> في التطبيق
3️⃣ أرسل <b>السعر</b> من متجر SHEIN
4️⃣ احصل على <b>السعر النهائي (بالسوري والدولار)</b>
5️⃣ تواصل معنا عبر <b>الواتس</b>

════════════════════════════════════

⚠️ <b>تنبيه مهم جداً!</b>

للحصول على السعر الدقيق تأكد من:
✓ تطبيق SHEIN <b>الرسمي</b>
✓ الدول: <b>المملكة العربية السعودية 🇸🇦</b>
✓ العملة: <b>الريال السعودي (SAR)</b>

════════════════════════════════════

💰 <b>الأسعار الحالية الشحن:</b>
👕 الملابس والأحذية: {format_currency(config['clothing_fee'])} ل.س (~ {config['clothing_fee']/usd_rate:.2f} $)
🎁 المنتجات الأخرى: {format_currency(config['other_fee'])} ل.س (~ {config['other_fee']/usd_rate:.2f} $)

جاهز؟ اختر فئة المنتج! 👇
    """
    
    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)
    
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

✓ <b>فتحت تطبيق SHEIN الرسمي</b>
✓ <b>اخترت الدول:</b> المملكة العربية السعودية 🇸🇦
✓ <b>اخترت العملة:</b> الريال السعودي (SAR) 💱
✓ <b>المنتج المختار:</b> {category_name}

════════════════════════════════════

📝 <b>الآن أرسل سعر المنتج كما يظهر بالتطبيق بالضبط</b>

مثال: أرسل <code>150</code> أو <code>99.99</code>
    """
    
    await query.edit_message_text(warning, parse_mode=ParseMode.HTML)
    return PRICE_INPUT


async def price_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال سعر المنتج وحساب القيمة بالسوري والدولار"""
    try:
        base_price = float(update.message.text.strip())
        if base_price <= 0:
            await update.message.reply_text("❌ السعر يجب أن يكون أكبر من صفر!")
            return PRICE_INPUT
        
        category = context.user_data.get('category', 'other')
        config = load_config()
        
        # حساب السعر النهائي بالليرة السورية
        final_price_syp = calculate_final_price(base_price, category, config)
        price_without_fee = base_price * config['exchange_rate']
        
        # حساب ما يقابله بالدولار بناءً على سعر الدولار المدخل من الإدارة
        usd_rate = config.get('usd_rate', DEFAULT_CONFIG['usd_rate'])
        final_price_usd = final_price_syp / usd_rate
        
        if category == 'clothing':
            fee = config['clothing_fee']
            fee_type = '👕 أجور الملابس والأحذية والحقائب'
        else:
            fee = config['other_fee']
            fee_type = '🎁 أجور المنتجات الأخرى'
        
        result = f"""
════════════════════════════════════
💸 <b>السعر النهائي للطلب</b> 💸
════════════════════════════════════

📝 <b>السعر من SHEIN (SAR):</b>
{format_currency(base_price)} ريال سعودي 🇸🇦

📊 <b>تفصيل الحساب السوري:</b>
┌─────────────────────────────────
├─ السعر الأصلي: {format_currency(base_price)} ر.س
├─ × سعر الصرف: {format_currency(config['exchange_rate'])} ل.س
├─ = ({format_currency(price_without_fee)} ل.س)
├─ + {fee_type}
├─ {format_currency(fee)} ل.س
└─────────────────────────────────

💰 <b>🎯 السعر النهائي بالليرة السورية:</b>
<b>{format_currency(final_price_syp)} ليرة سورية 🇸🇾</b>

💵 <b>🎯 ما يعادله بالدولار الأمريكي:</b>
<b>{final_price_usd:.2f} دولار أمريكي 💵</b>
*(محسوب على سعر صرف: {format_currency(usd_rate)} ل.س/$)*

════════════════════════════════════

✅ <b>الخطوات التالية:</b>

1️⃣ <b>خذ لقطة شاشة (Screenshot) للسعر الذي ظهر أعلاه</b>
2️⃣ <b>افتح تطبيق SHEIN وانسخ رابط المنتج</b>
3️⃣ <b>افتح الواتس واضغط على الرقم أدناه</b>

📱 <b>رقم الواتس للتواصل:</b>
<a href="https://wa.me/{config['whatsapp'].replace('+', '')}">{config['whatsapp']}</a>

💬 <b>مثال الرسالة للطلب:</b>
"أريد طلب هذا المنتج
السعر: {format_currency(final_price_syp)} ل.س ({final_price_usd:.2f} $)"

════════════════════════════════════
        """
        
        await update.message.reply_text(result, parse_mode=ParseMode.HTML)
        
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
            "❌ هذا ليس رقماً صحيحاً!\n\nأرسل السعر بالأرقام فقط (مثال: <code>150</code>)",
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
        await query.edit_message_text("👋 شكراً لاستخدامك البوت! استقبلك بسرور لاحقاً.")
        return ConversationHandler.END


def main() -> None:
    """تشغيل البوت"""
    if not TELEGRAM_TOKEN:
        logger.error("❌ لم يتم تعيين TELEGRAM_BOT_TOKEN")
        return
    
    # الاتصال بـ MongoDB
    connect_to_mongo()
    
    # 🚀 تشغيل السيرفر الوهمي في الخلفية (Daemon Thread) لإبقاء الخدمة مستقرة على Render
    threading.Thread(target=run_health_server, daemon=True).start()
    
    logger.info("✅ بدء البوت واستدعاء محرك المحادثات...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
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
            SET_USD_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_usd_rate_input)],
            SET_CATEGORY_FEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_clothing_fee_input)],
            SET_OTHER_FEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_other_fee_input)],
            SET_WHATSAPP: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_whatsapp_input)],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("admin", admin_menu),
            CallbackQueryHandler(callback_handler, pattern='^(start_again|exit)$')
        ]
    )
    
    app.add_handler(conv_handler)
    logger.info("✅ البوت يعمل الآن ويستمع للرسائل بنجاح...")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("🛑 البوت توقف")


if __name__ == '__main__':
    main()
