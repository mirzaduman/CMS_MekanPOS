import datetime
import json
import os
import pytz

from dotenv import load_dotenv

from random import randint
from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse

from ninja import NinjaAPI, Form, File, Query
from ninja.files import UploadedFile

from controller.schemas import Login, GetTable, AddOrder, GetProduct, GetProducts, PostEditOrder, GetBasket, \
    GetEditOrder, SendBasket, ApproveBasket, DeclineBasket, SpamBasket, AssignTables, GetWorkerTables, GetTables, \
    GetOrder, GetNotifications, AcceptWaiterCall, GetApproveBasket, GetWorkersTables, ResetAllTables, \
    ChangeSessionTable, DeleteOrdersOfBasket, GetTablesIds, ChangeOrderTable, DeleteOrder, GetWorkers, DeleteWorker, \
    AddWorker, CreateProduct, GetCreateProductData, EditProduct, GetEditProduct, EditExtra, \
    DeleteExtra, GetAreas, GetAreaTables, ChangeTableArea, CreateTable, EditTable, DeleteTable, ChangeAreaTables, \
    GetChangeAreaTables, CreateArea, RemoveOrderFromBasket, GetSession, MakePayment, GetBaskets, FinishBasket, \
    GetProductsManager, DeleteArea, NotificationTest, CreateDevice

from model.models import User, Notification
from model.locations import Table, TableStatus, Area
from model.order import Basket, Order, Session, Payment
from model.products import Product, AvailableExtra, Category, Allergen, ProductStatus, ContentDisclaimer
from model.device import Device

from FCMManager import send_to_token

load_dotenv()

api = NinjaAPI(title='MekanPOS API', version='2023.03')

root = 'https://www.mekan-pos.de'

auth_key = os.getenv('AUTH_KEY')


def get_picture_url(ref):
    if ref.picture:
        return f'{root}{ref.picture.url}'
    else:
        return None


def session_nr_generator():
    test = randint(1000000, 9999999)
    while Session.objects.filter(session_nr=test).exists():
        test = randint(1000000, 9999999)
    return test


# APP NOTIFICATION
@api.post('/notificaiton-test', tags=['Test'])
def notification_test(request, data: NotificationTest = Form(...)):
    send_to_token(data.token, data.title, data.body)
    return 200


@api.post("/create-device", tags=["Device"])
def create_device(request, data: CreateDevice = Form(...)):
    Device.objects.create(token=data.token)
    return 200


# AUTHENTICATION

@api.post('/login', tags=['Authentication'],
          description='Kullanıcı username ve şifreyi gönderir, eğer bilgileri doğruysa, id ve rol geri döner.')
def login(request, data: Login = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, username=data.username)
        device = get_object_or_404(Device, token=data.token)
        if user.check_password(data.password):
            if user.is_waiter:
                role = 'waiter'
            elif user.is_waiter_chef:
                role = 'waiter_chef'
            elif user.is_manager:
                role = 'manager'
            else:
                role = 'None'
            device.user = user
            device.save()
            return {'id': user.id, 'role': role}
        else:
            return 400
    else:
        return 401


# TABLES

@api.get('/get-tables', tags=['Tables'],
         description="Cihazı kullanan kullanıcının id'si gönderilir. Kullanıcının rolüne göre masaların dönüşü gelir.")
def get_tables(request, query: GetTables = Query(...)):
    if query.key == auth_key:
        response = []
        user = get_object_or_404(User, id=query.user_id)
        if user.is_waiter:
            for table in Table.objects.filter(waiter=user).order_by('status_change'):
                table_details = {'id': table.id, 'table_nr': table.nr, 'status': table.status.name,
                                 'status_border_color': table.status.border_color,
                                 'status_fill_color': table.status.border_color,
                                 'last_action_time': table.status_change}
                response.append(table_details)
        if user.is_waiter_chef or user.is_manager:
            for table in Table.objects.all():
                def get_user():
                    if table.waiter:
                        return table.waiter.first_name
                    else:
                        return None

                def get_timestamp():
                    if table.status_change:
                        return round(table.status_change.timestamp())
                    else:
                        return None

                table_details = {'id': table.id, 'table_nr': table.nr, 'waiter': get_user(),
                                 'status': table.status.name,
                                 'status_border_color': table.status.border_color,
                                 'status_fill_color': table.status.border_color,
                                 'last_action_time': get_timestamp()}
                response.append(table_details)
        return response
    else:
        return 401


@api.get('/get-table', tags=['Tables'],
         description="Kullanıcı id'si ve işlem yapılacak masanın id'si gönderilir. O masada eğer 'Bestellung' yani sipariş durumu mevcutsa, sepetlerin saatlerini ve içeriklerini görüntüler.")
def get_table(request, query: GetTable = Query(...)):
    if query.key == auth_key:
        user = get_object_or_404(User, id=query.user_id)
        table = get_object_or_404(Table, id=query.table_id)
        response = {'id': table.id, 'table_nr': table.nr}
        if table.status:
            response['status'] = table.status.name
            if table.status_change:
                response['status_change'] = round(table.status_change.timestamp())
            else:
                response['status_change'] = None
            if user.is_waiter_chef or user.is_manager:
                if table.waiter:
                    response['waiter'] = table.waiter.first_name
                else:
                    response['waiter'] = None
            if table.status.name == 'Inaktiv':
                return response
            else:
                if table.status != TableStatus.objects.get(name='Inaktiv'):
                    sessions = Session.objects.filter(table=table, end__isnull=True)
                    if sessions:
                        session = Session.objects.filter(table=table, end__isnull=True).last()
                    else:
                        session = Session.objects.create(table=table, start=datetime.datetime.now(
                            pytz.timezone('Europe/Berlin')), session_nr=session_nr_generator())
                else:
                    if Session.objects.filter(table=table, end__isnull=True).exists():
                        session = Session.objects.filter(table=table, end__isnull=True).last()
                        time_since = datetime.datetime.now() - session.start
                        if time_since > datetime.timedelta(minutes=15):
                            session.delete()
                            session = Session.objects.create(table=table, start=datetime.datetime.now(
                                pytz.timezone('Europe/Berlin')), session_nr=session_nr_generator())
                            session.save()
                    else:
                        session = Session.objects.create(table=table, start=datetime.datetime.now(
                            pytz.timezone('Europe/Berlin')), session_nr=session_nr_generator())
                if user.is_manager:
                    response['session_id'] = session.id
                baskets_list = []
                subtotal = 0
                for basket in Basket.objects.filter(session=session, approved=True, finished=True):
                    orders_list = []
                    for order in basket.orders.all():
                        order_details = {'id': order.id, 'product': order.product.name_de, 'price': order.price}
                        orders_list.append(order_details)
                        subtotal += order.price
                    basket_details = {'basket_id': basket.id, 'order_time': round(basket.finished_time.timestamp()),
                                      'orders': orders_list}
                    baskets_list.append(basket_details)
                response['baskets'] = baskets_list
                response['subtotal'] = subtotal
                return response
        else:
            return 'table_no_status'
    else:
        return 401


@api.get('/get-products', tags=['Tables'])
def get_products(request, query: GetProducts = Query(...)):
    if query.key == auth_key:
        response = {'basket_status': False}
        table = get_object_or_404(Table, id=query.table_id)
        session = Session.objects.filter(table=table).last()
        products = []
        for product in Product.objects.all():
            status = None
            status_description = None
            if product.status:
                if product.status.name == 'Aktiv':
                    status = 'active'
                elif product.status.name == 'Demnächst':
                    status = 'coming_soon'
                    status_description = 'Bald verfügbar!'
                elif product.status.name == 'Ausverkauft':
                    status = 'out_of_stock'
                    status_description = 'Dieses Produkt ist derzeit nicht verfügbar.'
            content_disclaimers = []
            for content_disclaimer in product.content_disclaimer.all():
                content_disclaimers.append(content_disclaimer.name_de)
            product_details = {'id': product.id, 'status': status, 'status_description': status_description,
                               'category': product.category.name_de, 'name': product.name_de,
                               'product_nr': product.product_nr,
                               'content_disclaimers': content_disclaimers,
                               'picture_url': get_picture_url(product), 'description': product.description_de,
                               'price': product.price}
            products.append(product_details)
        if session:
            if not session.end:
                basket = Basket.objects.filter(session=session, finished=False).last()
                if basket:
                    if basket.orders:
                        response['basket_status'] = True
                        for order in basket.orders.all():
                            for product in products:
                                if order.product.id == product['id']:
                                    if 'in_basket_amount' in product:
                                        product['in_basket_amount'] += 1
                                    else:
                                        product['in_basket_amount'] = 1
        response['products'] = products
        return response
    else:
        return 401


@api.get('/get-product', tags=['Tables'],
         description="Masa ve ürün id'si gönderilir. Eğer masada açılmış bir sepet var ise ve bu sepette bu üründen var ise, kaç tane olduğunu gösterir. Ürünün genel bilgilerini verir.")
def get_product(request, query: GetProduct = Query(...)):
    if query.key == auth_key:
        response = {'basket_status': False}
        table = get_object_or_404(Table, id=query.table_id)
        product = get_object_or_404(Product, id=query.product_id)
        session = Session.objects.filter(table=table).last()
        n = 0
        if session:
            if not session.end:
                basket = Basket.objects.filter(session=session, finished=False).last()
                if basket:
                    if basket.orders:
                        response['basket_status'] = True
                        for order in basket.orders.all():
                            if order.product == product:
                                n += 1
                        response['in_basket_amount'] = n
        extras = []
        for extra in product.extras.all():
            extra_details = {'id': extra.id, 'name': extra.name_de, 'price': extra.price}
            extras.append(extra_details)
        good_withs = []
        for good_with in product.good_with.all():
            good_with_details = {'id': good_with.id, 'name': good_with.name_de, 'price': good_with.price}
            good_withs.append(good_with_details)
        allergens = []
        for allergen in product.allergens.all():
            allergens.append(f'{allergen.code} - {allergen.name_de}')
        content_disclaimers = []
        for content_disclaimer in product.content_disclaimer.all():
            content_disclaimers.append(content_disclaimer.name_de)
        response.update(
            {'name': product.name_de, 'picture_url': get_picture_url(product), 'description': product.description_de,
             'price': product.price,
             'available_extras': extras, 'good_with': good_withs, 'allergens': allergens,
             'content_disclaimers': content_disclaimers, 'status': product.status.name})
        return response
    else:
        return 401


@api.get('/get-basket', tags=['Tables'])
def get_basket(request, query: GetBasket = Query(...)):
    if query.key == auth_key:
        table = get_object_or_404(Table, id=query.table_id)
        response = {'in_basket': False, 'table_nr': table.nr, 'table_id': table.id}
        session = Session.objects.filter(table=table, end__isnull=True).last()
        if session:
            basket = Basket.objects.filter(session=session, finished=False).last()
            if basket:
                basket_orders = basket.orders.all()
                if basket_orders.exists():
                    response['in_basket'] = True
                    response['basket_id'] = basket.id
                    orders = []

                    def add_order(order_object):
                        extras = None
                        order_extras = order_object.chosen_extras.all()
                        if order_extras.exists():
                            extras = ''
                            n = 0
                            length = len(order_extras)
                            for extra in order_extras:
                                n += 1
                                if n == length:
                                    extras += f'{extra.name_de}'
                                else:
                                    extras += f'{extra.name_de}, '

                        def get_picture():
                            if order_object.product.picture:
                                return root + order_object.product.picture.url
                            else:
                                return None

                        order_details = {'order_id': order_object.id, 'product': order_object.product.name_de,
                                         'extras': extras,
                                         'amount': 1, 'order_group_id': order_object.order_group_id,
                                         'order_price': order_object.price, 'picture': get_picture()}
                        orders.append(order_details)

                    group_ids = []
                    for order in basket.orders.all():
                        if order.order_group_id:
                            try:
                                aim = [group_id for group_id in group_ids if order.order_group_id in group_id][0]
                                aim_index = aim[1]
                                if orders[aim_index]['amount'] == 1:
                                    orders[aim_index]['amount'] += 2
                                else:
                                    orders[aim_index]['amount'] += 1
                            except IndexError:
                                add_order(order)
                                group_ids.append((order.order_group_id, len(orders) - 1))
                        else:
                            add_order(order)
                    for order in orders:
                        order.pop('order_group_id')
                        if order['extras'] is None:
                            order.pop('extras')
                    response['orders'] = orders
            return response
        else:
            return 'no_session'
    else:
        return 401


@api.get('/get-order', tags=['Tables'])
def get_order(request, query: GetOrder = Query(...)):
    if query.key == auth_key:
        order = get_object_or_404(Order, id=query.order_id)
        allergens_query = order.product.allergens.all()
        allergens = ''
        n = 0
        length = len(allergens_query)
        for allergen in allergens_query:
            n += 1
            if n == length:
                allergens += f'{allergen.code} - {allergen.name_de}'
            else:
                allergens += f'{allergen.code} - {allergen.name_de}, '
        extras = []
        extras_price = 0
        for extra in order.chosen_extras.all():
            extra_details = {'name': extra.name_de, 'price': extra.price}
            extras.append(extra_details)
            extras_price += extra.price
        response = {'id': order.id, 'product': order.product.name_de, 'allergens': allergens, 'notes': order.notes,
                    'extras': extras,
                    'product_price': order.product.price, 'extras_price': extras_price, 'subtotal': order.price}
        return response
    else:
        return 401


@api.post('/delete-order', tags=['Tables'])
def remove_order_from_basket(request, data: RemoveOrderFromBasket = Form(...)):
    if data.key == auth_key:
        order = get_object_or_404(Order, id=data.order_id)
        if order.order_group_id:
            orders = Order.objects.filter(order_group_id=order.order_group_id)
            for order in orders:
                order.delete()
        else:
            order.delete()
        return 200
    else:
        return 401


@api.post('/add-order-to-basket', tags=['Tables'],
          description="Kullanıcı, masa ve ürün id'leri gönderilir. Ürünün miktarı ve hangi aşamaya ait olduğu bilgisiyle beraber o üründe seçilebilen ekstraların id'leri, ve eğer garson custom ekstra eklediyse 'ekstraismi_ekstrafiyatı(euro ve cent nokta ile ayrılarak)' şeklinde liste halinde gönderilir. Bu ürünle iyi giden seçili ürünler varsa o ürünlerin id'leri liste halinde gönderilir.")
def add_order_to_basket(request, data: AddOrder = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        table = get_object_or_404(Table, id=data.table_id)
        session = Session.objects.filter(table=table).last()
        product = get_object_or_404(Product, id=data.product_id)
        orders = []
        order_group_id = None
        if data.amount > 1:
            try:
                order_group_id = Order.objects.filter(order_group_id__isnull=False).order_by(
                    '-order_group_id').first().order_group_id + 1
            except:
                order_group_id = 1
        for n in range(data.amount):
            order = Order.objects.create(user=user, product=product, notes=data.additional_info, gang=data.gang,
                                         price=product.price)
            if order_group_id:
                order.order_group_id = order_group_id
                order.save()
            orders.append(order)
        if data.extras:
            extras = [i.split(',') for i in data.extras][0]
            for extra in extras:
                extra_object = get_object_or_404(AvailableExtra, id=int(extra))
                for order in orders:
                    order.chosen_extras.add(extra_object)
                    order.price += Decimal(extra_object.price)
                    order.save()
        if data.additional_extras:
            extras = [i.split(',') for i in data.additional_extras][0]
            for extra in extras:
                split = extra.split('_')
                added_extra = AvailableExtra.objects.create(name_de=split[0], name_en=split[0], name_tr=split[0],
                                                            price=split[1])
                for order in orders:
                    order.chosen_extras.add(added_extra)
                    order.price += Decimal(added_extra.price)
                    order.save()
        if session:
            if not session.end:
                test_basket = Basket.objects.filter(session=session, finished=False).last()
                if test_basket:
                    basket = test_basket
                else:
                    basket = Basket.objects.create(session=session)
            else:
                session = Session.objects.create(table=table, start=datetime.datetime.now(
                    pytz.timezone('Europe/Berlin')),
                                                 session_nr=session_nr_generator())
                basket = Basket.objects.create(session=session)
        else:
            session = Session.objects.create(table=table, start=datetime.datetime.now(
                pytz.timezone('Europe/Berlin')),
                                             session_nr=session_nr_generator())
            basket = Basket.objects.create(session=session)
        if data.good_withs:
            good_withs = [i.split(',') for i in data.good_withs][0]
            for good_with in good_withs:
                product = get_object_or_404(Product, id=int(good_with))
                good_with_order = Order.objects.create(user=user, product=product, price=product.price)
                orders.append(good_with_order)
        for order in orders:
            basket.orders.add(order)
        return 200
    else:
        return 401


@api.get('/get-edit-order', tags=['Tables'],
         description="Basketteki düzenlenmesi istenilen orderin order id'si gönderilir. Order ile ilgili detaylar gelir.")
def get_edit_order(request, query: GetEditOrder = Query(...)):
    if query.key == auth_key:
        response = {'in_basket': True}
        order = get_object_or_404(Order, id=query.order_id)
        if order.order_group_id:
            amount = 0
            order_group = Order.objects.filter(order_group_id=order.order_group_id)
            for order in order_group:
                amount += 1
        else:
            amount = 1
        extras = []
        for extra in order.chosen_extras.all():
            extra_details = {'id': extra.id, 'name': extra.name_de, 'price': extra.price}
            extras.append(extra_details)
        order_details = {'name': order.product.name_de, 'picture': get_picture_url(order.product),
                         'description': order.product.description_de, 'price': order.product.price, 'amount': amount,
                         'additional_info': order.notes, 'extras': extras,
                         'gang': order.gang}
        response.update(order_details)
        return response
    else:
        return 401


@api.post('/post-edit-order', tags=['Tables'],
          description="Gönderici user id ve değiştirilmesi istenilen orderın id'si gönderilir. Değişmeyecek olan fieldlar None/Null olarak gönderilir. Amount eğer get-edit-orderdaki sayıdan farklı bir amount ise gönderilir.(Min. 1) Extras eğer değişiklik yapıldıysa tüm istenilen extralar listesi olarak gönderilir. Additional extra da sadece yeni additional extra eklendiyse gönderilir.")
def post_edit_order(request, data: PostEditOrder = Form(...)):
    if data.key == auth_key:
        # user will be used for log
        # user = get_object_or_404(User, id=data.user_id)
        order = get_object_or_404(Order, id=data.order_id)
        extras = order.chosen_extras.all()
        orders = []
        if order.order_group_id:
            for order in Order.objects.filter(order_group_id=order.order_group_id):
                orders.append(order)
        else:
            orders.append(order)
        orders.reverse()
        if data.amount:
            if data.amount > len(orders):
                if not order.order_group_id:
                    try:
                        order.order_group_id = Order.objects.filter(
                            order_group_id__isnull=False).last().order_group_id + 1
                    except:
                        order.order_group_id = 1
                    order.save()
                n = data.amount - len(orders)
                for i in range(n):
                    order.pk = None
                    order.save()
                    for extra in extras:
                        order.chosen_extras.add(extra)
                    orders.append(order)
            if data.amount < len(orders):
                n = len(orders) - data.amount
                while n != 0:
                    o = orders[0]
                    print(o.id)
                    o.delete()
                    orders.pop(0)
                    n -= 1
                if data.amount == 1:
                    orders[0].order_group_id = None
                    orders[0].save()
        if data.additional_info:
            for order in orders:
                order.notes = data.additional_info
                order.save()
        if data.extras:
            if data.extras != ['']:
                extras = [i.split(',') for i in data.extras][0]
                for order in orders:
                    order.price = order.product.price
                    order.chosen_extras.clear()
                    for extra in extras:
                        extra_object = get_object_or_404(AvailableExtra, id=int(extra))
                        order.chosen_extras.add(extra_object)
                        order.price += Decimal(extra_object.price)
                    order.save()
            else:
                for order in orders:
                    order.chosen_extras.clear()
                    order.price = order.product.price
                    order.save()
        if data.additional_extras:
            extras = [i.split(',') for i in data.additional_extras][0]
            for extra in extras:
                split = extra.split('_')
                added_extra = AvailableExtra.objects.create(name_de=split[0], name_en=split[0], name_tr=split[0],
                                                            price=split[1])
                for order in orders:
                    order.chosen_extras.add(added_extra)
                    order.price += Decimal(added_extra.price)
                    order.save()
        if data.gang:
            for order in orders:
                order.gang = data.gang
                order.save()
        return 200
    else:
        return 401


@api.post('/send-basket', tags=['Tables'],
          description="user ve table id gönderilir. O masadaki son hazırlanan sepet mutfağa gönderilir.")
def send_basket(request, data: SendBasket = Form(...)):
    if data.key == auth_key:
        if data.orders:
            orders_data = json.loads(data.orders)
            for o in orders_data:
                order = get_object_or_404(Order, id=o.get('order_id'))
                extras = order.chosen_extras.all()
                orders = []
                if order.order_group_id:
                    for order in Order.objects.filter(order_group_id=order.order_group_id):
                        orders.append(order)
                else:
                    orders.append(order)
                orders.reverse()
                amount = o.get('amount')
                if amount > len(orders):
                    if not order.order_group_id:
                        try:
                            order.order_group_id = Order.objects.filter(
                                order_group_id__isnull=False).last().order_group_id + 1
                        except:
                            order.order_group_id = 1
                        order.save()
                    n = amount - len(orders)
                    for i in range(n):
                        order.pk = None
                        order.save()
                        for extra in extras:
                            order.chosen_extras.add(extra)
                        orders.append(order)
                if amount < len(orders):
                    n = len(orders) - amount
                    while n != 0:
                        o = orders[0]
                        print(o.id)
                        o.delete()
                        orders.pop(0)
                        n -= 1
                    if amount == 1:
                        orders[0].order_group_id = None
                        orders[0].save()

        user = get_object_or_404(User, id=data.user_id)
        table = get_object_or_404(Table, id=data.table_id)
        session = Session.objects.filter(table=table, end__isnull=True).last()
        basket = Basket.objects.filter(session=session, finished=False).last()
        basket.finished = True
        basket.finished_time = datetime.datetime.now(
            pytz.timezone('Europe/Berlin'))
        basket.user = user
        basket.approved = True
        basket.approved_by = user
        basket.save()
        table.status = get_object_or_404(TableStatus, name='Bestellung')
        table.save()
        return 200
    else:
        return 401


# NOTIFICATIONS


@api.get('/get-notifications', tags=['Notifications'],
         description="user id'si verilen kullanıcın o güne ait bildirimleri geri döner.")
def get_notifications(request, query: GetNotifications = Query(...)):
    if query.key == auth_key:
        response = []
        for notification in Notification.objects.filter(user=get_object_or_404(User, id=query.user_id),
                                                        timestamp__day=datetime.datetime.now(
                                                            pytz.timezone('Europe/Berlin')).date().day):
            def get_basket_id():
                if notification.assigned_basket:
                    return notification.assigned_basket.id
                else:
                    return None

            notification_details = {'id': notification.id, 'log': notification.log,
                                    'time': notification.timestamp.time().strftime('%H:%M'),
                                    'action_made': notification.action_made, 'basket_id': get_basket_id()}
            response.append(notification_details)
        return response
    else:
        return 401


@api.post('/accept-waiter-call', tags=['Notifications'],
          description="Garson çağırma bildirimi geldiğinde o çağrıyı garson kabul edildiğinde gönderilir.")
def accept_waiter_call(request, data: AcceptWaiterCall = Form(...)):
    if data.key == auth_key:
        notification = get_object_or_404(Notification, id=data.notification_id)
        notification.action_made = True
        notification.save()
        return 200
    else:
        return 401


@api.get('/get-basket-approve', tags=['Notifications'],
         description="Müşteri Webten sipariş geldiğinde o masaya bağlı garsonda ve yöneticilerde gelen onay bekleme bildirimine basıldığında, öncesinde o bildirimde bulunan basket id verilerek, onaylanacak sepetle ilgili bilgiler gelir.")
def get_basket_approve(request, query: GetApproveBasket = Query(...)):
    if query.key == auth_key:
        basket = get_object_or_404(Basket, id=query.basket_id)
        orders = []
        total = 0
        for order in basket.orders.all():
            order_details = {'name': order.product.name_de, 'price': order.price}
            total += order.price
            orders.append(order_details)
        response = {'basket_id': query.basket_id, 'table_nr': basket.session.table.nr,
                    'status': basket.session.table.status.name,
                    'status_border_color': basket.session.table.status.border_color,
                    'status_fill_color': basket.session.table.status.fill_color,
                    'status_change': basket.session.table.status_change.timestamp(),
                    'order_time': basket.created_time.strftime("%H:%M"), 'orders': orders, 'total': total}
        return response
    else:
        return 401


@api.post('/approve-basket', tags=['Notifications'],
          description="Müşteri Webten gelen siparişi onaylamak için userın id'si ve onaylanacak basketın id'si gönderilir.")
def approve_basket(request, data: ApproveBasket = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        basket = get_object_or_404(Basket, id=data.basket_id)
        basket.approved = True
        basket.approved_by = user
        basket.save()
        return 200
    else:
        return 401


@api.post('/decline-basket', tags=['Notifications'],
          description="Müşteri Webten gelen siparişi reddetmek için userın id'si ve reddedilecek basketın id'si gönderilir.")
def decline_basket(request, data: DeclineBasket = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        basket = get_object_or_404(Basket, id=data.basket_id)
        basket.canceled = True
        basket.canceled_by = user
        basket.save()
        return 200
    else:
        return 401


@api.post('/spam-basket', tags=['Notifications'],
          description="Müşteri Webten gelen siparişi spamlemek için userın id'si ve spamlenecek basketın id'si gönderilir.")
def spam_basket(request, data: SpamBasket = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        basket = get_object_or_404(Basket, id=data.basket_id)
        basket.spam = True
        basket.spammed_by = user
        basket.save()
        return 200
    else:
        return 401


# WAITER CHEF

@api.get('/get-workers-tables', tags=['Waiter Chef'], description="Garsonlara ait atanmış masalar görüntülenir.")
def get_workers_table(request, query: GetWorkersTables = Query(...)):
    if query.key == auth_key:
        response = []
        user = get_object_or_404(User, id=query.user_id)
        if user.is_waiter_chef or user.is_manager:
            tables = Table.objects.all()
            if user.is_waiter_chef or user.is_manager:
                for waiter in User.objects.filter(is_waiter=True):
                    waiter_tables = []
                    for table in tables.filter(waiter=waiter):
                        waiter_tables.append(table.nr)
                    waiter_details = {'id': waiter.id, 'name': waiter.first_name, 'tables': waiter_tables}
                    response.append(waiter_details)
            return response
        else:
            return 'user_is_not_waiter_chef_or_manager'
    else:
        return 401


@api.post('/reset-all-tables', tags=['Waiter Chef'], description="Tüm masa atamalarını sıfırlar.")
def reset_all_tables(request, data: ResetAllTables = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_waiter_chef or user.is_manager:
            for table in Table.objects.all():
                table.waiter = None
                table.save()
            return 200
        else:
            return 'user_is_not_waiter_chef_or_manager'
    else:
        return 401


@api.get('/get-worker-tables', tags=['Waiter Chef'],
         description="Seçilen garsona(id) ait atanmış ve hiç bir ataması olmayan, seçilmeye uygun masaları görüntüler.")
def get_worker_tables(request, query: GetWorkerTables = Query(...)):
    if query.key == auth_key:
        user = get_object_or_404(User, id=query.user_id)
        if user.is_waiter_chef or user.is_manager:
            waiter = get_object_or_404(User, id=query.waiter_id)
            tables_query = Table.objects.all()
            waiter_tables = []
            available_tables = []
            for table in tables_query.filter(waiter=waiter):
                def area_none():
                    if table.area:
                        return table.area.name
                    else:
                        return None

                table_details = {'id': table.id, 'table_nr': table.nr, 'area': area_none()}
                waiter_tables.append(table_details)
            for table in tables_query.filter(waiter__isnull=True):
                def area_none():
                    if table.area:
                        return table.area.name
                    else:
                        return None

                table_details = {'id': table.id, 'table_nr': table.nr, 'area': area_none()}
                available_tables.append(table_details)
            response = {'waiter': waiter.first_name, 'assigned_tables': waiter_tables,
                        'available_tables': available_tables}
            return response
        else:
            return 'user_is_not_waiter_chef_or_manager'
    else:
        return 401


@api.post('/assign-tables', tags=['Waiter Chef'],
          description="Seçilen garsona atanacak ve atanmış masaların id'leri liste halinde gönderilir. (user_id requesti gönderen kullanıcının id'si, waiter_id bir önceki sayfada seçilen masa atanılacak garsonun id'si.)")
def assign_tables(request, data: AssignTables = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_waiter_chef or user.is_manager:
            waiter = get_object_or_404(User, id=data.waiter_id)
            for table in Table.objects.filter(waiter=waiter):
                table.waiter = None
                table.save()
            tables = []
            tables_data = [i.split(',') for i in data.tables][0]
            for table in tables_data:
                table_object = get_object_or_404(Table, id=int(table))
                table_object.waiter = waiter
                table_object.save()
            return 200
        else:
            return 'user_is_not_waiter_chef_or_manager'
    else:
        return 401


# MANAGER

@api.get('/get-tables-ids', tags=['Manager'],
         description="change-session-table için gerekli masa numaraları ve id'leri verir.")
def get_tables_ids(request, query: GetTablesIds = Query(...)):
    if query.key == auth_key:
        user = get_object_or_404(User, id=query.user_id)
        if user.is_manager:
            response = []
            for table in Table.objects.all():
                table_details = {'id': table.id, 'nr': table.nr}
                response.append(table_details)
            return response
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/change-session-table', tags=['Manager'],
          description="get-table'dan gelen session_id ve aktarılması istenilen masanın id'si verilir.")
def change_session_table(request, data: ChangeSessionTable = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            session = get_object_or_404(Session, id=data.session_id)
            old_table = session.table
            old_table.status = get_object_or_404(TableStatus, name='Inaktiv')
            old_table.status_change = datetime.datetime.now()
            new_table = get_object_or_404(Table, id=data.table_id)
            session.table = new_table
            new_table.status = get_object_or_404(TableStatus, name='Bestellung')
            new_table.status_change = datetime.datetime.now()
            new_table.save()
            session.save()
            old_table.save()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/delete-orders-of-basket', tags=['Manager'],
          description="get-table'dan gelen silinmesi istenilen basketin id'si gönderilir.")
def delete_orders_of_basket(request, data: DeleteOrdersOfBasket = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            basket = get_object_or_404(Basket, id=data.basket_id)
            basket.delete()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/change-order-table', tags=['Manager'],
          description="Aktarılacak orderın id'si ve aktarılması istenilen masanın id'si gönderili")
def change_order_table(request, data: ChangeOrderTable = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            order = get_object_or_404(Order, id=data.order_id)
            basket = Basket.objects.filter(orders=order)[0]
            table = get_object_or_404(Table, id=data.table_id)
            old_table = None
            if Session.objects.filter(table=table, end__isnull=True).exists():
                session = Session.objects.filter(table=table, end__isnull=True).last()
                old_table = session.table
            else:
                session = Session.objects.create(table=table, start=datetime.datetime.now(
                    pytz.timezone('Europe/Berlin')), session_nr=session_nr_generator())
            if Basket.objects.filter(session=session, finished=False).exists():
                aim_basket = Basket.objects.filter(session=session, finished=False).last()
            else:
                aim_basket = Basket.objects.create(session=session, approved=True, approved_by=user)
            aim_basket.orders.add(order)
            basket.orders.remove(order)
            if old_table:
                session.end = datetime.datetime.now(pytz.timezone('Europe/Berlin'))
                old_table.status = get_object_or_404(TableStatus, name='Inaktiv')
                old_table.status_change = datetime.datetime.now(pytz.timezone('Europe/Berlin'))
                session.save()
                old_table.save()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/delete-order', tags=['Manager'], description="Silinecek orderin id'si verilir.")
def delete_order(request, data: DeleteOrder = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            order = get_object_or_404(Order, id=data.order_id)
            order.delete()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.get('/get-workers', tags=['Manager'])
def get_workers(request, query: GetWorkers = Query(...)):
    if query.key == auth_key:
        user = get_object_or_404(User, id=query.user_id)
        if user.is_manager:
            response = []
            workers = User.objects.filter(Q(is_waiter=True) | Q(is_waiter_chef=True))
            for worker in workers:
                if worker.is_waiter:
                    role = 'Kellner'
                elif worker.is_waiter_chef:
                    role = 'Chefkellner'
                worker_details = {'id': worker.id, 'name': worker.first_name, 'role': role, 'phone': worker.phone,
                                  'username': worker.username, 'pin': worker.pin}
                response.append(worker_details)
            return response
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/delete-worker', tags=['Manager'], description="Silinmesi istenilen işçinin id'si verilir.")
def delete_worker(request, data: DeleteWorker = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            worker = get_object_or_404(User, id=data.worker_id)
            worker.delete()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/add-worker', tags=['Manager'],
          description="Yeni oluşturulcak işçinin bilgileri gönderilir. Oluşturulacak işçi için role bilgisine eğer garsonsa 'waiter' eğer şef garsonsa 'waiter_chef' girilir. Kullanıcı adı eğer kullanıldıysa 'username_taken' geri döner.")
def add_worker(request, data: AddWorker = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            if data.role == 'waiter':
                try:
                    User.objects.create(username=data.username, password='A132kjnaSAkfa2', pin=randint(1000, 9999),
                                        is_waiter=True, phone=data.phone, first_name=data.worker_name)
                except IntegrityError:
                    return 'username_taken'
            if data.role == 'waiter_chef':
                try:
                    User.objects.create(username=data.username, password='A132kjnaSAkfa2', pin=randint(1000, 9999),
                                        is_waiter_chef=True, phone=data.phone, first_name=data.worker_name)
                except IntegrityError:
                    return 'username_taken'
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.get('/get-products-manager', tags=['Manager'])
def get_products_manager(request, query: GetProductsManager = Query(...)):
    if query.key == auth_key:
        user = get_object_or_404(User, id=query.user_id)
        if user.is_manager:
            response = []
            for product in Product.objects.all():
                response.append(
                    {'id': product.id, 'product_nr': product.product_nr, 'category': product.category.name_de,
                     'name': product.name_de,
                     'picture_url': get_picture_url(product), 'description': product.description_de,
                     'price': product.price})
            return response
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.get('/get-create-product-data', tags=['Manager'],
         description="Ürün oluşturmadan önce seçilebilecek seçenekleri verir.")
def get_create_product_data(request, query: GetCreateProductData = Query(...)):
    if query.key == auth_key:
        user = get_object_or_404(User, id=query.user_id)
        if user.is_manager:
            categories = []
            for category in Category.objects.all():
                category_details = {'id': category.id, 'name': category.name_de}
                categories.append(category_details)
            allergens = []
            for allergen in Allergen.objects.all():
                allergen_details = {'id': allergen.id, 'name': f'{allergen.code} - {allergen.name_de}'}
                allergens.append(allergen_details)
            products = []
            for product in Product.objects.all():
                product_details = {'id': product.id, 'name': product.name_de}
                products.append(product_details)
            statuses = []
            for status in ProductStatus.objects.all():
                statuses.append({'id': status.id, 'name': status.name})
            content_disclaimers = []
            for content_disclaimer in ContentDisclaimer.objects.all():
                content_disclaimers.append({'id': content_disclaimer.id, 'name': content_disclaimer.name_de})
            response = {'categories': categories, 'allergens': allergens, 'products': products,
                        'available_content_disclaimers': content_disclaimers, 'available_statuses': statuses}
            return response
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/create-product', tags=['Manager'],
          description="Ürün oluşturmak için istenilen bilgiler gönderilir. get-create-product-data'dan gelen ve seçilmiş olan objelerin id'leri string olarak virgülle ayrılarak gönderilir.")
def create_product(request, data: CreateProduct = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            allergens = []
            if data.allergens:
                allergens_list = [i.split(',') for i in data.allergens][0]
                for allergen in allergens_list:
                    o = get_object_or_404(Allergen, id=int(allergen))
                    allergens.append(o)
            extras = []
            if data.extras:
                extras_data = json.loads(data.extras)
                for extra in extras_data:
                    created_extra = AvailableExtra.objects.create(name_de=extra['name_de'], name_tr=extra['name_tr'],
                                                                  name_en=extra['name_en'], price=extra['price'])
                    extras.append(created_extra)
            good_withs = []
            if data.good_with:
                good_withs_list = [i.split(',') for i in data.good_with][0]
                for good_with in good_withs_list:
                    o = get_object_or_404(Product, id=int(good_with))
                    good_withs.append(o)
            content_disclaimers = []
            if data.content_disclaimers:
                content_disclaimers_list = [i.split(',') for i in data.content_disclaimers][0]
                for content_disclaimer in content_disclaimers_list:
                    o = get_object_or_404(ContentDisclaimer, id=int(content_disclaimer))
                    content_disclaimers.append(o)
            status = get_object_or_404(ProductStatus, id=data.product_status)
            category = get_object_or_404(Category, id=data.category_id)
            try:
                product = Product.objects.create(name_de=data.name_de, name_tr=data.name_tr, name_en=data.name_en,
                                                 product_nr=data.product_nr,
                                                 category=category, price=data.price,
                                                 description_de=data.description_de,
                                                 description_tr=data.description_tr, description_en=data.description_en,
                                                 status=status)
            except IntegrityError:
                return HttpResponse('Es existiert bereits ein Produkt mit dieser Produkt Nr.', status=406)
            for allergen in allergens:
                product.allergens.add(allergen)
            for good_with in good_withs:
                product.good_with.add(good_with)
            for content_disclaimer in content_disclaimers:
                product.content_disclaimer.add(content_disclaimer)
            for extra in extras:
                product.extras.add(extra)
            return product.id
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/add-picture-to-product', tags=['Manager'], description="Ürüne fotoğraf eklenir.")
def add_picture_to_product(request, key: str = Form(...), user_id: int = Form(...), product_id: int = Form(...),
                           picture: UploadedFile = File(...)):
    if key == auth_key:
        user = get_object_or_404(User, id=user_id)
        if user.is_manager:
            product = get_object_or_404(Product, id=product_id)
            product.picture = picture
            product.save()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.get('/get-edit-product', tags=['Manager'],
         description="Ürün düzenlemeden önce o ürünle ilgili bilgileri görüntüler.")
def get_edit_product(request, query: GetEditProduct = Query(...)):
    if query.key == auth_key:
        user = get_object_or_404(User, id=query.user_id)
        if user.is_manager:
            product = get_object_or_404(Product, id=query.product_id)
            response = {'id': product.id, 'name_de': product.name_de, 'name_tr': product.name_tr,
                        'name_en': product.name_en, 'product_nr': product.product_nr,
                        'category_id': product.category.id,
                        'category': product.category.name_de, 'picture': get_picture_url(product),
                        'price': product.price,
                        'description_de': product.description_de, 'description_tr': product.description_tr,
                        'description_en': product.description_en, 'status_id': product.status.id,
                        'status': product.status.name}

            allergens = []
            for allergen in product.allergens.all():
                allergens.append({'id': allergen.id, 'name': f'{allergen.code} - {allergen.name_de}'})
            response['allergens'] = allergens
            extras = []
            for extra in product.extras.all():
                extras.append(
                    {'id': extra.id, 'name_de': extra.name_de, 'name_tr': extra.name_tr, 'name_en': extra.name_en,
                     'price': extra.price})
            response['extras'] = extras
            good_withs = []
            for good_with in product.good_with.all():
                good_withs.append({'id': good_with.id, 'name': good_with.name_de})
            response['good_with'] = good_withs
            content_disclaimers = []
            for content_disclaimer in product.content_disclaimer.all():
                content_disclaimers.append({'id': content_disclaimer.id, 'name': content_disclaimer.name_de})
            response['content_disclaimer'] = content_disclaimers
            return response
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/edit-product', tags=['Manager'],
          description="Aynı create-product gibi çalışır, düzenlenmeyecek kısımlar null gönderilir. Çoklu seçilen objelerde her hangi bir değişiklik varsa sadece değiştirilmiş objelerin değil, o üründe bulunması istenilen tüm objelerin id'leri gönderilir.")
def edit_product(request, data: EditProduct = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            product = get_object_or_404(Product, id=data.product_id)
            if data.name_de:
                product.name_de = data.name_de
            if data.name_tr:
                product.name_tr = data.name_tr
            if data.name_en:
                product.name_en = data.name_en
            if data.product_nr:
                if Product.objects.filter(product_nr=data.product_nr).exists():
                    return HttpResponse('Es existiert bereits ein Produkt mit dieser Produkt Nr.', status=406)
                product.product_nr = data.product_nr
            if data.category_id:
                product.category = get_object_or_404(Category, id=data.category_id)
            if data.price:
                product.price = data.price
            if data.allergens:
                if data.allergens != ['']:
                    allergens_list = [i.split(',') for i in data.allergens][0]
                    product.allergens.clear()
                    for allergen in allergens_list:
                        product.allergens.add(get_object_or_404(Allergen, id=int(allergen)))
                else:
                    product.allergens.clear()
            if data.description_de:
                product.description_de = data.description_de
            if data.description_tr:
                product.description_tr = data.description_tr
            if data.description_en:
                product.description_en = data.description_en
            if data.good_with:
                if data.good_with != ['']:
                    good_with_list = [i.split(',') for i in data.good_with][0]
                    product.good_with.clear()
                    for gw in good_with_list:
                        product.good_with.add(get_object_or_404(Product, id=int(gw)))
                else:
                    product.good_with.clear()
            if data.content_disclaimers:
                if data.content_disclaimers != ['']:
                    content_disclaimer_list = [i.split(',') for i in data.content_disclaimers][0]
                    product.content_disclaimer.clear()
                    for content_disclaimer in content_disclaimer_list:
                        product.content_disclaimer.add(get_object_or_404(ContentDisclaimer, id=int(content_disclaimer)))
                else:
                    product.content_disclaimer.clear()
            if data.product_status:
                product.status = get_object_or_404(ProductStatus, id=int(data.product_status))
            if data.extras:
                extras_data = json.loads(data.extras)
                for ed in extras_data:
                    e_id = ed.get('id')
                    if e_id == 0:
                        new_e = AvailableExtra.objects.create(name_de=ed.get('name_de'), name_tr=ed.get('name_tr'),
                                                              name_en=ed.get('name_en'), price=ed.get('price'))
                        product.extras.add(new_e)
                    else:
                        e = get_object_or_404(AvailableExtra, id=e_id)
                        e.name_de = ed.get('name_de')
                        e.name_tr = ed.get('name_tr')
                        e.name_en = ed.get('name_en')
                        e.price = ed.get('price')
                        e.save()
            product.save()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/edit-extra', tags=['Manager'],
          description="Ürün düzenlendiğinde düzenlenen extra varsa bu endpoint kullanılır.")
def edit_extra(request, data: EditExtra = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            extra = get_object_or_404(AvailableExtra, id=data.extra_id)
            if data.name_de:
                extra.name_de = data.name_de
            if data.name_tr:
                extra.name_tr = data.name_tr
            if data.name_en:
                extra.name_en = data.name_en
            if data.price:
                extra.price = data.price
            extra.save()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/delete-extra', tags=['Manager'],
          description="Ürün düzenlemede silinmesi istenilen extra varsa bu endpoint kullanılır.")
def delete_extra(request, data: DeleteExtra = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            extra = get_object_or_404(AvailableExtra, id=data.extra_id)
            extra.delete()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.get('/get-areas', tags=['Manager'])
def get_areas(request, query: GetAreas = Query(...)):
    if query.key == auth_key:
        user = get_object_or_404(User, id=query.user_id)
        if user.is_manager:
            response = []
            for area in Area.objects.all():
                response.append({'id': area.id, 'name': area.name})
            return response
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.get('/get-area-tables', tags=['Manager'])
def get_area_tables(request, query: GetAreaTables = Query(...)):
    if query.key == auth_key:
        user = get_object_or_404(User, id=query.user_id)
        if user.is_manager:
            area = get_object_or_404(Area, id=query.area_id)
            response = []
            for table in Table.objects.filter(area=area):
                response.append({'id': table.id, 'nr': table.nr})
            return response
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/change-table-area', tags=['Manager'])
def change_table_area(request, data: ChangeTableArea = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            area = get_object_or_404(Area, id=data.area_id)
            table = get_object_or_404(Table, id=data.table_id)
            table.area = area
            table.save()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/edit-table', tags=['Manager'])
def edit_table(request, data: EditTable = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            table = get_object_or_404(Table, id=data.table_id)
            table.area = get_object_or_404(Area, id=data.area)
            table.save()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/delete-table', tags=['Manager'])
def delete_table(request, data: DeleteTable = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            table = get_object_or_404(Table, id=data.table_id)
            table.delete()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/create-table', tags=['Manager'])
def create_table(request, data: CreateTable = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            area = get_object_or_404(Area, id=data.area_id)
            if Table.objects.filter(nr=data.table_nr).exists():
                return 'table_nr_exists'
            else:
                Table.objects.create(area=area, nr=data.table_nr, status=get_object_or_404(TableStatus, name='Inaktiv'))
                return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.get('/get-change-area-tables', tags=['Manager'])
def get_change_area_tables(request, query: GetChangeAreaTables = Query(...)):
    if query.key == auth_key:
        user = get_object_or_404(User, id=query.user_id)
        if user.is_manager:
            area = get_object_or_404(Area, id=query.area_id)
            area_tables = []
            other_tables = []
            for table in Table.objects.filter(area=area):
                area_tables.append({'id': table.id, 'nr': table.nr})
            for table in Table.objects.filter(~Q(area=area)):
                other_tables.append({'id': table.id, 'nr': table.nr})
            response = {'area_tables': area_tables, 'other_tables': other_tables}
            return response
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/change-area-tables', tags=['Manager'])
def change_area_tables(request, data: ChangeAreaTables = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            area = get_object_or_404(Area, id=data.area_id)
            if data.name:
                area.name = data.name
                area.save()
            for table in Table.objects.filter(area=area):
                table.area = None
                table.save()
            tables_list = [i.split(',') for i in data.tables][0]
            for table in tables_list:
                o = get_object_or_404(Table, id=int(table))
                o.area = area
                o.save()
            return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/create-area', tags=['Manager'])
def create_area(request, data: CreateArea = Form(...)):
    if data.key == auth_key:
        user = get_object_or_404(User, id=data.user_id)
        if user.is_manager:
            if Area.objects.filter(name=data.area_name).exists():
                return 'area_name_exists'
            else:
                area = Area.objects.create(name=data.area_name)
                if data.tables:
                    tables_list = [i.split(',') for i in data.tables][0]
                    for table in tables_list:
                        o = get_object_or_404(Table, id=int(table))
                        o.area = area
                        o.save()
                return 200
        else:
            return 'user_is_not_manager'
    else:
        return 401


@api.post('/delete-area', tags=['Manager'])
def delete_area(request, data: DeleteArea = Form(...)):
    area = get_object_or_404(Area, id=data.area_id)
    area.delete()
    return 200


# REGISTER

@api.get('/get-session', tags=['Register'],
         description="get-tables requestinden alınan masanın id'si gönderilir. Eğer session var ise bilgileri, yoksa 'no_session' döner.")
def get_session(request, query: GetSession = Query(...)):
    if query.key == auth_key:
        table = get_object_or_404(Table, id=query.table_id)
        session = Session.objects.filter(table=table, end__isnull=True).last()
        if session:
            orders = []
            total = 0
            for basket in Basket.objects.filter(session=session):
                for order in basket.orders.filter(paid=False):
                    total += order.price
                    orders.append({'id': order.id, 'name': order.product.name_de, 'price': order.price})
            response = {'session_id': session.id, 'total': total, 'orders': orders}
            return response
        else:
            return 'no_session'
    else:
        return 401


@api.post('/make-payment', tags=['Register'],
          description="get-sesssion'dan alınan id, ödeme yöntemi ('cash' veya 'card') ve get-sessiondan gelen ve ödemesi yapılacak olan orderların id'leri gönderilir.")
def make_payment(request, data: MakePayment = Form(...)):
    if data.key == auth_key:
        session = get_object_or_404(Session, id=data.session_id)
        orders_list = [i.split(',') for i in data.orders][0]
        orders = []
        total = 0
        customer_order = 1
        for payment in Payment.objects.filter(session=session):
            customer_order += 1
        for order in orders_list:
            o = get_object_or_404(Order, id=int(order))
            total += o.price
            orders.append(o)
        payment = Payment.objects.create(customer_order=customer_order, method=data.payment_method, session=session,
                                         total=total)
        for order in orders:
            order.paid = True
            order.save()
            payment.orders.add(order)
        unpaid_orders = 0
        for basket in Basket.objects.filter(session=session):
            for order in basket.orders.filter(paid=False):
                unpaid_orders += 1
        if unpaid_orders == 0:
            session.end = datetime.datetime.now(
                pytz.timezone('Europe/Berlin'))
            session.table.status = TableStatus.objects.get(name='Inaktiv')
            session.table.save()
            session.save()
        return 200
    else:
        return 401


# KITCHEN
@api.get('/get-baskets', tags=['Kitchen'])
def get_baskets(request, query: GetBaskets = Query(...)):
    if query.key == auth_key:
        today = datetime.datetime.now(
            pytz.timezone('Europe/Berlin')).day
        baskets = Basket.objects.filter(created_time__day=today, finished=True, finished_time__day=today, approved=True,
                                        cooked=False).order_by('finished_time')
        todays_baskets = Basket.objects.filter(created_time__day=today, finished=True, finished_time__day=today,
                                               approved=True,
                                               cooked=True).order_by('finished_time')
        cooked_baskets = []

        for basket in todays_baskets:
            orders = []
            used_group_ids = []
            gang_order_basket = False
            for order in basket.orders.all():
                if order.gang == 2 or order.gang == 3:
                    gang_order_basket = True
                if order.order_group_id:
                    if order.order_group_id not in used_group_ids:
                        amount = 0
                        for order_item in Order.objects.filter(order_group_id=order.order_group_id):
                            amount += 1
                        used_group_ids.append(order.order_group_id)
                        extras = []
                        for extra in order.chosen_extras.all():
                            extras.append(f'{extra.name_de}')
                        if gang_order_basket:
                            orders.append({'id': order.id, 'category': order.product.category.name_de,
                                           'category_id': order.product.category.id, 'name': order.product.name_de,
                                           'amount': amount, 'extras': extras, 'gang': order.gang})
                        else:
                            orders.append({'id': order.id, 'category': order.product.category.name_de,
                                           'category_id': order.product.category.id, 'name': order.product.name_de,
                                           'amount': amount, 'extras': extras})
                else:
                    amount = 1
                    extras = []
                    for extra in order.chosen_extras.all():
                        extras.append(f'{extra.name_de}')
                    if gang_order_basket:
                        orders.append({'id': order.id, 'category': order.product.category.name_de,
                                       'category_id': order.product.category.id, 'name': order.product.name_de,
                                       'amount': amount, 'extras': extras, 'gang': order.gang})
                    else:
                        orders.append({'id': order.id, 'category': order.product.category.name_de,
                                       'category_id': order.product.category.id, 'name': order.product.name_de,
                                       'amount': amount, 'extras': extras})
            cooked_baskets.append(
                {'id': basket.id, 'table_nr': basket.session.table.nr,
                 'timestamp': round(basket.finished_time.timestamp()),
                 'orders': orders})
        baskets_response = []
        response = {'active_baskets': baskets_response, 'cooked_baskets': cooked_baskets}
        for basket in baskets:
            orders = []
            used_group_ids = []
            for order in basket.orders.all():
                if order.order_group_id:
                    if order.order_group_id not in used_group_ids:
                        amount = 0
                        for order_item in Order.objects.filter(order_group_id=order.order_group_id):
                            amount += 1
                        used_group_ids.append(order.order_group_id)
                        extras = []
                        for extra in order.chosen_extras.all():
                            extras.append(f'{extra.name_de}')
                        orders.append({'id': order.id, 'category': order.product.category.name_de,
                                       'category_id': order.product.category.id, 'name': order.product.name_de,
                                       'amount': amount, 'extras': extras, 'gang': order.gang})
                else:
                    amount = 1
                    extras = []
                    for extra in order.chosen_extras.all():
                        extras.append(f'{extra.name_de}')
                    orders.append({'id': order.id, 'category': order.product.category.name_de,
                                   'category_id': order.product.category.id, 'name': order.product.name_de,
                                   'amount': amount, 'extras': extras, 'cooked': order.cooked, 'gang': order.gang})
            baskets_response.append(
                {'id': basket.id, 'table_nr': basket.session.table.nr,
                 'timestamp': round(basket.finished_time.timestamp()),
                 'orders': orders})
        return response
    else:
        return 401


@api.post('/finish-basket', tags=['Kitchen'])
def finish_basket(request, data: FinishBasket = Form(...)):
    if data.key == auth_key:
        basket = get_object_or_404(Basket, id=data.basket_id)
        for order in basket.orders.all():
            order.cooked = True
            order.cook_time = datetime.datetime.now(
                pytz.timezone('Europe/Berlin'))
            order.save()
        basket.cooked = True
        basket.cooked_time = datetime.datetime.now(
            pytz.timezone('Europe/Berlin'))
        basket.save()
        table = basket.session.table
        notification_data = {
            'title': 'Bestellung fertig!',
            'body': f'Das Essen für Tisch {table.nr} ist abholbereit.',
            'basket': f'{basket.id}'
        }
        send_to_token(get_object_or_404(Device, user=table.waiter).token, notification_data)
        return 200
    else:
        return 401


@api.post('/print-basket', tags=['Kitchen'])
def print_kitchen(request, data: FinishBasket = Form(...)):
    pass
