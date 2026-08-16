import threading
import secrets
import smtplib
from email.message import EmailMessage

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory
import pandas as pd
import os
from datetime import datetime, timedelta
import uuid
import time
from werkzeug.security import generate_password_hash, check_password_hash
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'eato_secret_key_2026')

SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')

VERIFICATION_TOKEN_TTL = timedelta(hours=24)
VERIFICATION_RESEND_COOLDOWN = timedelta(seconds=60)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_FILE = os.path.join(BASE_DIR, 'products.xlsx')
USERS_FILE = os.path.join(BASE_DIR, 'users.xlsx')
USER_CARTS_FILE = os.path.join(BASE_DIR, 'user_carts.xlsx')
COLLECTIONS_FILE = os.path.join(BASE_DIR, 'collections.xlsx')
ORDERS_FILE = os.path.join(BASE_DIR, 'orders.xlsx')
ORDERS_TEMP_FILE = os.path.join(BASE_DIR, 'orders_temp.xlsx')
ORDERS_PENDING_FILE = os.path.join(BASE_DIR, 'orders_pending.xlsx')


def static_url(endpoint, **values):
    """url_for that stamps static assets with their mtime.

    nginx serves /static with a 30-day Expires header, so a redeployed file
    keeps its old URL and returning visitors stay pinned to the copy they
    cached. Appending the mtime changes the URL whenever the file changes,
    which forces the fetch instead of waiting a month for the cache to lapse.
    """
    if endpoint == 'static':
        filename = values.get('filename')
        if filename:
            try:
                values['v'] = int(os.stat(os.path.join(app.static_folder, filename)).st_mtime)
            except OSError:
                pass
    return url_for(endpoint, **values)


@app.context_processor
def inject_static_url():
    return {'url_for': static_url}


def init_files():
    if not os.path.exists(PRODUCTS_FILE):
        df = pd.DataFrame(columns=[
            'id', 'name', 'collection', 'price', 'description',
            'sizes', 'image', 'sold_out', 'bestseller'
        ])
        df.to_excel(PRODUCTS_FILE, index=False, engine='openpyxl')

    if not os.path.exists(USERS_FILE):
        df = pd.DataFrame(columns=[
            'id', 'name', 'email', 'phone', 'password',
            'email_verified', 'verification_token', 'verification_sent_at'
        ])
        df.to_excel(USERS_FILE, index=False, engine='openpyxl')

    if not os.path.exists(USER_CARTS_FILE):
        df = pd.DataFrame(columns=['user_id', 'cart_data'])
        df.to_excel(USER_CARTS_FILE, index=False, engine='openpyxl')


init_files()


ORDERS = {}

def init_collections():
    if not os.path.exists(COLLECTIONS_FILE):
        df = pd.DataFrame(columns=['id', 'name', 'image', 'description', 'product_ids'])
        df.to_excel(COLLECTIONS_FILE, index=False, engine='openpyxl')

init_collections()

def get_products():
    try:
        df = pd.read_excel(PRODUCTS_FILE, engine='openpyxl')

        print("Columns in Excel:", df.columns.tolist())  # Debug
        print("First row:", df.iloc[0].to_dict())  # Debug

        products = []
        for _, row in df.iterrows():
            product = {
                'id': int(row.get('id', 0)),
                'name': str(row.get('name', '')),
                'collection': str(row.get('collection', '')),
                'price': int(row.get('price', 0)),
                'description': str(row.get('description', '')),
                'description_card': str(row.get('description_card', '')) if 'description_card' in df.columns else '',
                'sizes': str(row.get('sizes', 'S,M,L,XL')),
                'image': str(row.get('image', '')),
                'sold_out': str(row.get('sold_out', 'False')).upper() == 'TRUE',
                'bestseller': str(row.get('bestseller', 'False')).upper() == 'TRUE'
            }
            print(f"Product {product['id']} description_card:", product['description_card'])  # Debug
            products.append(product)
        return products
    except Exception as e:
        print(f"Error reading Excel: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_users():
    try:
        df = pd.read_excel(USERS_FILE, engine='openpyxl')
        users = []
        for _, row in df.iterrows():
            email_verified = row.get('email_verified', 1)
            token = row.get('verification_token', '')
            sent_at = row.get('verification_sent_at', '')
            user = {
                'id': int(row.get('id', 0)),
                'name': str(row.get('name', '')),
                'email': str(row.get('email', '')),
                'phone': str(row.get('phone', '')),
                'password': str(row.get('password', '')),
                'email_verified': bool(int(email_verified)) if pd.notna(email_verified) else True,
                'verification_token': str(token) if pd.notna(token) else '',
                'verification_sent_at': str(sent_at) if pd.notna(sent_at) else ''
            }
            users.append(user)
        return users
    except:
        return []


def save_user(user_data):
    df = pd.read_excel(USERS_FILE, engine='openpyxl')
    new_df = pd.DataFrame([user_data])
    df = pd.concat([df, new_df], ignore_index=True)
    df.to_excel(USERS_FILE, index=False, engine='openpyxl')


def update_user(user_id, updates):
    df = pd.read_excel(USERS_FILE, engine='openpyxl')
    for key, value in updates.items():
        df.loc[df['id'] == user_id, key] = value
    df.to_excel(USERS_FILE, index=False, engine='openpyxl')


def send_verification_email(to_email, name, token):
    verify_url = url_for('verify_email', token=token, _external=True)

    if not SMTP_USER:
        print(f'[verify-email] SMTP_USER не задан — ссылка для {to_email}: {verify_url}')
        return

    message = EmailMessage()
    message['Subject'] = 'Подтверждение регистрации — Е.А.Т.О.'
    message['From'] = SMTP_USER
    message['To'] = to_email
    message.set_content(
        f'{name}, привет!\n\n'
        f'Подтвердите ваш email, перейдя по ссылке:\n{verify_url}\n\n'
        f'Ссылка действительна 24 часа. Если вы не регистрировались на еато.store, просто проигнорируйте это письмо.'
    )

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(message)


def get_user_cart(user_id):
    try:
        df = pd.read_excel(USER_CARTS_FILE, engine='openpyxl')
        user_cart = df[df['user_id'] == user_id]
        if not user_cart.empty:
            return json.loads(user_cart.iloc[0]['cart_data'])
        return []
    except:
        return []


def save_user_cart(user_id, cart_data):
    df = pd.read_excel(USER_CARTS_FILE, engine='openpyxl')
    cart_json = json.dumps(cart_data)

    user_cart = df[df['user_id'] == user_id]
    if not user_cart.empty:
        df.loc[df['user_id'] == user_id, 'cart_data'] = cart_json
    else:
        new_df = pd.DataFrame([{'user_id': user_id, 'cart_data': cart_json}])
        df = pd.concat([df, new_df], ignore_index=True)

    df.to_excel(USER_CARTS_FILE, index=False, engine='openpyxl')


def init_orders():
    if not os.path.exists(ORDERS_FILE):
        df = pd.DataFrame(columns=[
            'order_id', 'user_id', 'items', 'total',
            'processing', 'production', 'shipping',
            'created_at'
        ])
        df.to_excel(ORDERS_FILE, index=False, engine='openpyxl')

    if not os.path.exists(ORDERS_PENDING_FILE):
        df = pd.DataFrame(columns=[
            'order_id', 'user_id', 'items', 'total',
            'processing', 'production', 'shipping',
            'created_at'
        ])
        df.to_excel(ORDERS_PENDING_FILE, index=False, engine='openpyxl')


init_orders()


def is_file_locked(filepath):
    try:
        with open(filepath, 'a'):
            return False
    except IOError:
        return True


def merge_pending_orders():
    try:
        if not os.path.exists(ORDERS_PENDING_FILE):
            return

        df_pending = pd.read_excel(ORDERS_PENDING_FILE, engine='openpyxl')

        if df_pending.empty:
            return

        # Проверяем, заблокирован ли основной файл
        if is_file_locked(ORDERS_FILE):
            print(f"⏳ Основной файл заблокирован, жду следующей попытки...")
            return

        print(f"🔄 Найдено {len(df_pending)} pending заказов, объединяю...")

        df_main = pd.read_excel(ORDERS_FILE, engine='openpyxl')

        # Объединяем
        df_merged = pd.concat([df_main, df_pending], ignore_index=True)

        # Сохраняем
        df_merged.to_excel(ORDERS_FILE, index=False, engine='openpyxl')

        df_empty = pd.DataFrame(columns=[
            'order_id', 'user_id', 'items', 'total',
            'processing', 'production', 'shipping',
            'created_at'
        ])
        df_empty.to_excel(ORDERS_PENDING_FILE, index=False, engine='openpyxl')

        print(f"✅ Pending заказы объединены с основным файлом")

    except Exception as e:
        print(f"❌ Ошибка объединения pending: {e}")


def background_sync():
    while True:
        try:
            merge_pending_orders()
        except Exception as e:
            print(f"❌ Ошибка фоновой синхронизации: {e}")

        time.sleep(30)  # Ждём 30 секунд


def save_order(order_data):
    try:
        if is_file_locked(ORDERS_FILE):
            print(f"⚠️ Файл orders.xlsx заблокирован, записываю в pending...")

            # Записываем в pending файл
            df = pd.read_excel(ORDERS_PENDING_FILE, engine='openpyxl')
            new_row = pd.DataFrame([order_data])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_excel(ORDERS_PENDING_FILE, index=False, engine='openpyxl')

            print(f"✅ Заказ {order_data.get('order_id')} сохранён в pending")
            return True
        else:
            df = pd.read_excel(ORDERS_FILE, engine='openpyxl')
            new_row = pd.DataFrame([order_data])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_excel(ORDERS_FILE, index=False, engine='openpyxl')

            print(f"✅ Заказ {order_data.get('order_id')} сохранён в основной файл")
            return True
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False


def get_user_orders(user_id):
    try:
        all_orders = []

        # Читаем основной файл
        try:
            df_main = pd.read_excel(ORDERS_FILE, engine='openpyxl')
            for _, row in df_main.iterrows():
                if int(row.get('user_id', 0)) == user_id:
                    order = {
                        'order_id': str(row.get('order_id', '')),
                        'user_id': int(row.get('user_id', 0)),
                        'items': str(row.get('items', '')),
                        'total': int(row.get('total', 0)),
                        'processing': int(row.get('processing', 0)),
                        'production': int(row.get('production', 0)),
                        'shipping': int(row.get('shipping', 0)),
                        'created_at': str(row.get('created_at', ''))
                    }
                    all_orders.append(order)
        except Exception as e:
            print(f"Ошибка чтения основного файла: {e}")

        try:
            df_pending = pd.read_excel(ORDERS_PENDING_FILE, engine='openpyxl')
            for _, row in df_pending.iterrows():
                if int(row.get('user_id', 0)) == user_id:
                    order = {
                        'order_id': str(row.get('order_id', '')),
                        'user_id': int(row.get('user_id', 0)),
                        'items': str(row.get('items', '')),
                        'total': int(row.get('total', 0)),
                        'processing': int(row.get('processing', 0)),
                        'production': int(row.get('production', 0)),
                        'shipping': int(row.get('shipping', 0)),
                        'created_at': str(row.get('created_at', ''))
                    }
                    all_orders.append(order)
        except Exception as e:
            print(f"Ошибка чтения pending файла: {e}")

        all_orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return all_orders
    except Exception as e:
        print(f"Ошибка получения заказов: {e}")
        return []


# Запускаем фоновую синхронизацию
sync_thread = threading.Thread(target=background_sync, daemon=True)
sync_thread.start()


def get_collections():
    try:
        df = pd.read_excel(COLLECTIONS_FILE, engine='openpyxl')
        print(f"\n=== Collections Excel ===")
        print(f"Columns: {df.columns.tolist()}")
        print(f"Rows: {len(df)}")
        print(df)
        print("========================\n")

        collections = []
        for _, row in df.iterrows():
            # Преобразуем product_ids в список чисел (поддержка и запятых, и точек)
            product_ids_str = str(row.get('product_ids', ''))
            product_ids = []

            if product_ids_str and product_ids_str.strip():
                # Заменяем точку на запятую для единообразия
                product_ids_str = product_ids_str.replace('.', ',')
                try:
                    product_ids = [int(x.strip()) for x in product_ids_str.split(',') if x.strip()]
                except Exception as e:
                    print(f"Error parsing product_ids '{product_ids_str}': {e}")
                    product_ids = []

            collection = {
                'id': int(row.get('id', 0)),
                'name': str(row.get('name', '')),
                'image': str(row.get('image', '')),
                'description': str(row.get('description', '')),
                'product_ids': product_ids
            }
            print(f"Collection {collection['id']}: {collection['name']}, products: {collection['product_ids']}")
            collections.append(collection)

        print(f"Total collections loaded: {len(collections)}")
        return collections
    except Exception as e:
        print(f"Error reading collections: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_collection(collection_id):
    collections = get_collections()
    return next((c for c in collections if c.get('id') == collection_id), None)


def get_collection_by_id(collection_id):
    """Получает коллекцию по её ID"""
    print(f"Looking for collection with ID: {collection_id} (type: {type(collection_id)})")

    collections = get_collections()
    print(f"Total collections: {len(collections)}")

    for collection in collections:
        coll_id = collection.get('id')
        print(f"Checking collection ID: {coll_id} (type: {type(coll_id)}), name: {collection.get('name')}")

        # Сравниваем как числа
        if int(coll_id) == int(collection_id):
            print(f"Found collection: {collection.get('name')}")
            return collection

    print("Collection not found!")
    return None


def get_lookbook_images():
    """Получает все изображения из папки лукбука"""
    lookbook_path = os.path.join(BASE_DIR, 'static', 'images', 'lookbook')

    if not os.path.exists(lookbook_path):
        os.makedirs(lookbook_path)
        return []

    # Получаем все файлы с расширениями изображений
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    images = []

    for filename in os.listdir(lookbook_path):
        ext = os.path.splitext(filename)[1].lower()
        if ext in valid_extensions:
            images.append(filename)

    # Сортируем по имени файла
    images.sort()

    return images


@app.route('/favicon.ico')
def favicon():
    # nginx отдаёт только /static/, а браузеры и превью-боты (Telegram и пр.)
    # запрашивают /favicon.ico в корне — без этого там 404.
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


@app.route('/site.webmanifest')
def site_webmanifest():
    # nginx не знает расширение .webmanifest и отдаёт его как
    # application/octet-stream — поэтому раздаём через Flask с верным типом.
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'site.webmanifest',
        mimetype='application/manifest+json'
    )


@app.route('/')
def index():
    products = get_products()
    bestsellers = [p for p in products if p.get('bestseller')]
    collections = get_collections()
    return render_template('index.html', bestsellers=bestsellers, collections=collections)


@app.route('/catalog')
def catalog():
    collections = get_collections()
    products = get_products()
    return render_template('catalog.html', collections=collections, products=products)


@app.route('/collections')
def collections_page():
    collections = get_collections()
    return render_template('collections.html', collections=collections)


@app.route('/collection/<int:collection_id>')
def collection(collection_id):
    collection = get_collection(collection_id)
    if not collection:
        return redirect(url_for('collections_page'))

    all_products = get_products()

    collection_products = [p for p in all_products if p.get('id') in collection.get('product_ids', [])]

    return render_template('collection_detail.html', collection=collection, products=collection_products)


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return render_template('cart_login.html')

    cart_items = session.get('cart', [])
    total = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart_items)

    user_orders = get_user_orders(session['user_id'])

    return render_template('cart.html',
                           cart_items=cart_items,
                           total=total,
                           user_orders=user_orders)

@app.route('/lookbook')
def lookbook():
    images = get_lookbook_images()
    return render_template('lookbook.html', images=images)


@app.route('/product/<int:product_id>')
def product(product_id):
    products = get_products()
    product = next((p for p in products if p.get('id') == product_id), None)
    if not product:
        return redirect(url_for('catalog'))

    # Получаем список фотографий товара
    import os
    product_images_path = os.path.join(BASE_DIR, 'static', 'images', 'clothes', str(product_id))
    if os.path.exists(product_images_path):
        images = [f for f in os.listdir(product_images_path) if f.endswith(('.jpg', '.jpeg', '.png', '.gif'))]
        images.sort()
    else:
        images = []

    # Получаем информацию о коллекции товара
    collection_id = product.get('collection')
    print(f"Product {product_id} has collection: {collection_id} (type: {type(collection_id)})")

    collection = get_collection_by_id(collection_id) if collection_id else None

    return render_template('product.html', product=product, images=images, collection=collection)


@app.context_processor
def inject_gallery():
    albom_path = os.path.join(BASE_DIR, 'static', 'images', 'albom')
    if os.path.exists(albom_path):
        images = [f for f in os.listdir(albom_path) if f.endswith(('.jpg', '.jpeg', '.png', '.gif'))]
        images.sort()
    else:
        images = []
    return dict(gallery_images=images)


@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'login':
            # Авторизация
            login_input = request.form.get('login_input')  # email или телефон
            password = request.form.get('password')

            users = get_users()
            user = None
            for u in users:
                if (u['email'] == login_input or u['phone'] == login_input) and check_password_hash(u['password'],
                                                                                                    password):
                    user = u
                    break

            if user and not user['email_verified']:
                flash('Email ещё не подтверждён. Проверьте почту или отправьте письмо ещё раз ниже.', 'error')
            elif user:
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                # Загружаем корзину пользователя
                user_cart = get_user_cart(user['id'])
                session['cart'] = user_cart
                flash('Вход выполнен успешно!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неверный логин или пароль', 'error')

        elif action == 'register':
            # Регистрация
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            password = request.form.get('password')
            password_confirm = request.form.get('password_confirm')

            # Валидация
            errors = []

            if not name or len(name) < 2:
                errors.append('Имя должно содержать минимум 2 символа')
            if len(name) > 50:
                errors.append('Имя не должно превышать 50 символов')

            if not email or '@' not in email:
                errors.append('Некорректный email')

            if not phone or len(phone) < 10:
                errors.append('Некорректный телефон')

            if not password or len(password) < 6:
                errors.append('Пароль должен содержать минимум 6 символов')

            if password != password_confirm:
                errors.append('Пароли не совпадают')

            # Проверка существующего пользователя
            users = get_users()
            for u in users:
                if u['email'] == email:
                    errors.append('Пользователь с таким email уже существует')
                    break
                if u['phone'] == phone:
                    errors.append('Пользователь с таким телефоном уже существует')
                    break

            if errors:
                for error in errors:
                    flash(error, 'error')
            else:
                # Создаем нового пользователя
                new_user_id = len(users) + 1
                hashed_password = generate_password_hash(password)
                token = secrets.token_urlsafe(32)
                new_user = {
                    'id': new_user_id,
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'password': hashed_password,
                    'email_verified': 0,
                    'verification_token': token,
                    'verification_sent_at': datetime.now().isoformat()
                }
                save_user(new_user)

                try:
                    send_verification_email(email, name, token)
                    flash('Регистрация почти завершена — мы отправили письмо со ссылкой для подтверждения на ваш email.', 'success')
                except Exception:
                    flash('Аккаунт создан, но письмо отправить не удалось. Отправьте его ещё раз ниже.', 'error')

        elif action == 'resend_verification':
            email = request.form.get('email', '').strip()
            users = get_users()
            user = next((u for u in users if u['email'] == email), None)

            if user and not user['email_verified']:
                sent_at = user['verification_sent_at']
                on_cooldown = False
                if sent_at:
                    try:
                        on_cooldown = datetime.now() - datetime.fromisoformat(sent_at) < VERIFICATION_RESEND_COOLDOWN
                    except ValueError:
                        pass

                if on_cooldown:
                    flash('Письмо уже отправлено, подождите немного и проверьте почту.', 'error')
                else:
                    token = secrets.token_urlsafe(32)
                    update_user(user['id'], {
                        'verification_token': token,
                        'verification_sent_at': datetime.now().isoformat()
                    })
                    try:
                        send_verification_email(user['email'], user['name'], token)
                    except Exception:
                        pass
                    flash('Если такой аккаунт существует и email ещё не подтверждён, письмо отправлено.', 'success')
            else:
                flash('Если такой аккаунт существует и email ещё не подтверждён, письмо отправлено.', 'success')

    return render_template('auth.html')


@app.route('/verify-email/<token>')
def verify_email(token):
    users = get_users()
    user = next((u for u in users if u['verification_token'] and u['verification_token'] == token), None)

    if not user:
        flash('Ссылка недействительна или уже использована.', 'error')
        return redirect(url_for('auth'))

    sent_at = user['verification_sent_at']
    expired = True
    if sent_at:
        try:
            expired = datetime.now() - datetime.fromisoformat(sent_at) > VERIFICATION_TOKEN_TTL
        except ValueError:
            expired = True

    if expired:
        flash('Срок действия ссылки истёк. Отправьте письмо ещё раз ниже.', 'error')
        return redirect(url_for('auth'))

    update_user(user['id'], {'email_verified': 1, 'verification_token': ''})

    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['cart'] = get_user_cart(user['id'])
    flash('Email подтверждён, добро пожаловать!', 'success')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    # Сохраняем корзину перед выходом
    if 'user_id' in session and 'cart' in session:
        save_user_cart(session['user_id'], session['cart'])

    session.clear()
    flash('Вы вышли из аккаунта', 'success')
    return redirect(url_for('index'))




@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    data = request.json
    cart = session.get('cart', [])

    # Создаем уникальный ID для товара с размером
    item_id = f"{data.get('id')}-{data.get('size', 'M')}"

    # Проверяем, есть ли уже такой товар с таким размером
    found = False
    for item in cart:
        if item.get('id') == data.get('id') and item.get('size') == data.get('size'):
            item['quantity'] = item.get('quantity', 1) + 1
            found = True
            break

    if not found:
        cart.append({
            'id': data.get('id'),
            'name': data.get('name'),
            'price': data.get('price'),
            'size': data.get('size', 'M'),
            'image': data.get('image', ''),
            'quantity': 1
        })

    session['cart'] = cart

    if 'user_id' in session:
        save_user_cart(session['user_id'], cart)

    return jsonify({'success': True, 'cart_count': len(cart)})


@app.route('/api/cart/remove', methods=['POST'])
def remove_from_cart():
    try:
        data = request.json
        product_id = data.get('product_id')
        size = data.get('size')

        cart = session.get('cart', [])

        cart = [item for item in cart if not (item.get('id') == product_id and item.get('size') == size)]

        session['cart'] = cart

        if 'user_id' in session:
            save_user_cart(session['user_id'], cart)

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error removing from cart: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/cart/update', methods=['POST'])
def update_cart():
    try:
        data = request.json
        product_id = data.get('product_id')
        size = data.get('size')
        quantity = data.get('quantity')

        cart = session.get('cart', [])

        # Находим и обновляем товар
        for item in cart:
            if item.get('id') == product_id and item.get('size') == size:
                item['quantity'] = quantity
                break

        session['cart'] = cart

        if 'user_id' in session:
            save_user_cart(session['user_id'], cart)

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating cart: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Для оформления заказа необходимо авторизоваться', 'error')
        return redirect(url_for('auth'))

    if request.method == 'POST':
        data = request.json
        order_id = str(uuid.uuid4())[:8].upper()

        # Формируем строку с товарами
        cart_items = session.get('cart', [])
        items_str = ', '.join(
            [f"{item.get('name', '')} ({item.get('size', '')}) x{item.get('quantity', 1)}" for item in cart_items])

        # Создаём заказ
        order_data = {
            'order_id': order_id,
            'user_id': session['user_id'],
            'items': items_str,
            'total': data.get('total', 0),
            'processing': 1,  # Первый статус - принято в обработку
            'production': 0,
            'shipping': 0,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Сохраняем в Excel
        save_order(order_data)

        # Очищаем корзину
        session['cart'] = []
        if 'user_id' in session:
            save_user_cart(session['user_id'], [])

        return jsonify({'success': True, 'order_id': order_id})

    cart_items = session.get('cart', [])
    total = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/order-status/<order_id>')
def order_status(order_id):
    order = ORDERS.get(order_id)
    if not order:
        return render_template('order_status.html', order=None, order_id=order_id)

    now = datetime.now()
    if now < order['preorder_end']:
        current_step = 1
    elif now < order['production_start']:
        current_step = 2
    elif now < order['shipping']:
        current_step = 3
    else:
        current_step = 4

    return render_template('order_status.html', order=order, current_step=current_step)


@app.context_processor
def inject_user():
    return {
        'current_user': {
            'id': session.get('user_id'),
            'name': session.get('user_name')
        } if 'user_id' in session else None
    }


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)