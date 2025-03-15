import json
import os
import telebot
from telebot import types

# Load language files
def load_buttons(language="fa"):
    with open(os.path.join(os.path.dirname(__file__), "Json", "buttons.json"), "r", encoding="utf-8") as f:
        buttons = json.load(f)
    return buttons.get(language, buttons.get("fa", {}))

def get_button_text(key, language="fa"):
    """Get button text in the specified language"""
    buttons = load_buttons(language)
    return buttons.get(key, key)

def generate_glass_menu(buttons_data, language="fa", row_width=2):
    """
    Generate a glass-style inline keyboard markup
    
    Args:
        buttons_data: List of button dictionaries with keys:
            - text: Button text
            - callback_data: Callback data for button
            - url: URL for button (optional)
        language: Language code
        row_width: Number of buttons per row
    
    Returns:
        InlineKeyboardMarkup
    """
    markup = types.InlineKeyboardMarkup(row_width=row_width)
    buttons = []
    
    for btn in buttons_data:
        text = btn.get("text", "")
        callback_data = btn.get("callback_data")
        url = btn.get("url")
        
        if url:
            buttons.append(types.InlineKeyboardButton(text, url=url))
        else:
            buttons.append(types.InlineKeyboardButton(text, callback_data=callback_data))
    
    # Add buttons in rows based on row_width
    for i in range(0, len(buttons), row_width):
        row_buttons = buttons[i:i+row_width]
        markup.row(*row_buttons)
    
    return markup

def generate_main_menu(language="fa"):
    """Generate main menu for user bot"""
    buttons_data = [
        {"text": "🛍 " + get_button_text("SHOP", language), "callback_data": "shop"},
        {"text": "🔄 " + get_button_text("RENEW", language), "callback_data": "renew"},
        {"text": "📦 " + get_button_text("TRACK_ORDER", language), "callback_data": "track_order"},
        {"text": "👤 " + get_button_text("MY_ACCOUNT", language), "callback_data": "my_account"},
        {"text": "⚙️ " + get_button_text("SETTINGS", language), "callback_data": "settings"},
        {"text": "📞 " + get_button_text("SUPPORT", language), "callback_data": "support"}
    ]
    
    return generate_glass_menu(buttons_data, language)

def generate_shop_menu(products, language="fa"):
    """Generate shop menu with products"""
    buttons_data = []
    
    for product in products:
        buttons_data.append({
            "text": f"{product['name']} - {product['price']} تومان",
            "callback_data": f"buy_{product['id']}"
        })
    
    # Add back button
    buttons_data.append({
        "text": "🔙 " + get_button_text("BACK", language),
        "callback_data": "back_to_main"
    })
    
    return generate_glass_menu(buttons_data, language, row_width=1)

def generate_payment_methods(amount, order_id, language="fa"):
    """Generate payment methods menu"""
    buttons_data = [
        {"text": "💳 " + get_button_text("CARD_PAYMENT", language), "callback_data": f"pay_card_{amount}_{order_id}"},
        {"text": "💰 " + get_button_text("CRYPTO_PAYMENT", language), "callback_data": f"pay_crypto_{amount}_{order_id}"},
        {"text": "🔙 " + get_button_text("BACK", language), "callback_data": "back_to_shop"}
    ]
    
    return generate_glass_menu(buttons_data, language, row_width=1)

def generate_config_menu(uuid, language="fa"):
    """Generate config menu for a user"""
    buttons_data = [
        {"text": "🔗 " + get_button_text("SUBSCRIPTION_LINK", language), "callback_data": f"config_sub_{uuid}"},
        {"text": "📱 " + get_button_text("V2RAY", language), "callback_data": f"config_v2ray_{uuid}"},
        {"text": "🛡️ " + get_button_text("CLASH", language), "callback_data": f"config_clash_{uuid}"},
        {"text": "📲 " + get_button_text("SHADOWROCKET", language), "callback_data": f"config_shadowrocket_{uuid}"},
        {"text": "🔄 " + get_button_text("SINGBOX", language), "callback_data": f"config_singbox_{uuid}"},
        {"text": "🔙 " + get_button_text("BACK", language), "callback_data": "back_to_account"}
    ]
    
    return generate_glass_menu(buttons_data, language, row_width=2)

def generate_admin_main_menu(language="fa"):
    """Generate main menu for admin bot"""
    buttons_data = [
        {"text": "👥 " + get_button_text("USERS_MANAGEMENT", language), "callback_data": "admin_users"},
        {"text": "🛍 " + get_button_text("PRODUCTS_MANAGEMENT", language), "callback_data": "admin_products"},
        {"text": "📦 " + get_button_text("ORDERS_MANAGEMENT", language), "callback_data": "admin_orders"},
        {"text": "💰 " + get_button_text("PAYMENTS_MANAGEMENT", language), "callback_data": "admin_payments"},
        {"text": "🔄 " + get_button_text("SERVER_STATUS", language), "callback_data": "admin_server_status"},
        {"text": "📊 " + get_button_text("STATISTICS", language), "callback_data": "admin_statistics"},
        {"text": "📤 " + get_button_text("BACKUP", language), "callback_data": "admin_backup"},
        {"text": "📥 " + get_button_text("RESTORE", language), "callback_data": "admin_restore"},
        {"text": "⚙️ " + get_button_text("SETTINGS", language), "callback_data": "admin_settings"}
    ]
    
    return generate_glass_menu(buttons_data, language, row_width=2)

def generate_users_management_menu(language="fa"):
    """Generate users management menu for admin"""
    buttons_data = [
        {"text": "➕ " + get_button_text("ADD_USER", language), "callback_data": "admin_add_user"},
        {"text": "🔍 " + get_button_text("SEARCH_USER", language), "callback_data": "admin_search_user"},
        {"text": "📋 " + get_button_text("LIST_USERS", language), "callback_data": "admin_list_users"},
        {"text": "⏱️ " + get_button_text("EXPIRED_USERS", language), "callback_data": "admin_expired_users"},
        {"text": "🔙 " + get_button_text("BACK", language), "callback_data": "admin_back_to_main"}
    ]
    
    return generate_glass_menu(buttons_data, language, row_width=2)

def generate_products_management_menu(language="fa"):
    """Generate products management menu for admin"""
    buttons_data = [
        {"text": "➕ " + get_button_text("ADD_PRODUCT", language), "callback_data": "admin_add_product"},
        {"text": "📋 " + get_button_text("LIST_PRODUCTS", language), "callback_data": "admin_list_products"},
        {"text": "🔙 " + get_button_text("BACK", language), "callback_data": "admin_back_to_main"}
    ]
    
    return generate_glass_menu(buttons_data, language, row_width=2)

def generate_orders_management_menu(language="fa"):
    """Generate orders management menu for admin"""
    buttons_data = [
        {"text": "🆕 " + get_button_text("NEW_ORDERS", language), "callback_data": "admin_new_orders"},
        {"text": "✅ " + get_button_text("COMPLETED_ORDERS", language), "callback_data": "admin_completed_orders"},
        {"text": "❌ " + get_button_text("CANCELLED_ORDERS", language), "callback_data": "admin_cancelled_orders"},
        {"text": "🔍 " + get_button_text("SEARCH_ORDER", language), "callback_data": "admin_search_order"},
        {"text": "🔙 " + get_button_text("BACK", language), "callback_data": "admin_back_to_main"}
    ]
    
    return generate_glass_menu(buttons_data, language, row_width=2)

def generate_confirm_cancel_menu(callback_prefix, item_id, language="fa"):
    """Generate confirm/cancel menu"""
    buttons_data = [
        {"text": "✅ " + get_button_text("CONFIRM", language), "callback_data": f"{callback_prefix}_confirm_{item_id}"},
        {"text": "❌ " + get_button_text("CANCEL", language), "callback_data": f"{callback_prefix}_cancel_{item_id}"}
    ]
    
    return generate_glass_menu(buttons_data, language, row_width=2)

def generate_pagination_menu(current_page, total_pages, callback_prefix, language="fa"):
    """Generate pagination menu"""
    buttons_data = []
    
    # Previous page button
    if current_page > 1:
        buttons_data.append({
            "text": "◀️ " + get_button_text("PREV_PAGE", language),
            "callback_data": f"{callback_prefix}_page_{current_page - 1}"
        })
    
    # Page indicator
    buttons_data.append({
        "text": f"📄 {current_page}/{total_pages}",
        "callback_data": f"page_info_{current_page}_{total_pages}"
    })
    
    # Next page button
    if current_page < total_pages:
        buttons_data.append({
            "text": get_button_text("NEXT_PAGE", language) + " ▶️",
            "callback_data": f"{callback_prefix}_page_{current_page + 1}"
        })
    
    return generate_glass_menu(buttons_data, language, row_width=3)

