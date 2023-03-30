from datetime import datetime, timedelta
from random import randint
import pytz
# from io import BytesIO

from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.template.loader import get_template, render_to_string
# from weasyprint import HTML

from model.locations import Table
from model.order import Session, Basket, Order
from model.models import Notification
from model.products import Category, Product, AvailableExtra

# from xhtml2pdf import pisa

z = 275
breakfast_list = [275, 276, 277]
waiter_list = []

while z < 302:
    waiter_list.append(z)
    z += 1




breakfast_mode = False

bln = pytz.timezone('Europe/Berlin')


def choose_table(request, waiter=''):
    e = False
    if request.method == 'POST':
        table_nr = request.POST.get('table-nr')
        try:
            table = Table.objects.get(nr=table_nr)
        except Table.DoesNotExist:
            e = True
        else:
            return redirect('home', language='de', table_hash=table.table_hash, waiter=waiter)

    context = {
        'e': e,
    }
    return render(request, 'home/choose_table.html', context)


def home(request, language, table_hash):
    table = get_object_or_404(Table, table_hash=table_hash)
    has_order = False
    if Session.objects.filter(table=table, end__isnull=True).exists():
        session = Session.objects.filter(table=table, end__isnull=True).last()
        if Basket.objects.filter(session=session, finished=True).exists():
            has_order = True
    can_call_waiter = True
    try:
        waiter_call_time = request.COOKIES['waiter_call_time']
    except KeyError:
        waiter_call_time = None
    if waiter_call_time:
        time_past = datetime.now() - datetime.strptime(waiter_call_time, '%Y-%m-%d %H:%M:%S')
        if time_past < timedelta(minutes=5):
            can_call_waiter = False
    context = {
        'table_nr': table.nr,
        'table_hash': table_hash,
        'has_order': has_order,
        'language': language,
        'can_call_waiter': can_call_waiter,
    }
    return render(request, f'home/home.html', context)


def call_waiter(request, language, table_hash):
    table = get_object_or_404(Table, table_hash=table_hash)
    user = table.waiter
    log = f'Tisch {table.nr} hat Sie gerufen'
    Notification.objects.create(user=user, log=log)
    response = render(request, f'htmx_partials/called_waiter.html', context={'language': language})
    response.set_cookie('waiter_call_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    return response


def menu(request, language, table_hash):
    table = get_object_or_404(Table, table_hash=table_hash)
    in_basket = False
    basket_products = []
    if Session.objects.filter(table=table, end__isnull=True).exists():
        session = Session.objects.filter(table=table, end__isnull=True).last()
        if Basket.objects.filter(session=session, finished=False).exists():
            basket = Basket.objects.filter(session=session, finished=False).last()
            if basket.orders.exists():
                in_basket = True
                for order in basket.orders.all():
                    l_l = list(filter(lambda person: person['id'] == order.product.id, basket_products))
                    if l_l:
                        l_l[0]['amount'] += 1
                    else:
                        basket_products.append({'id': order.product.id, 'amount': 1})
    menu_topic = ''
    all_categories = ''
    if language == 'de':
        menu_topic = 'Menü'
        all_categories = 'Alle Kategorien'
    elif language == 'tr':
        menu_topic = 'Menü'
        all_categories = 'Tüm Kategoriler'
    elif language == 'en':
        menu_topic = 'Menu'
        all_categories = 'All Categories'
    categories = []
    for category in Category.objects.all():
        if language == 'de':
            categories.append({'name': category.name_de, 'name_id': f'{category.name_de}_{category.id}', 'id': category.id, 'order_id': category.order})
        elif language == 'tr':
            categories.append({'name': category.name_tr, 'name_id': f'{category.name_tr}_{category.id}', 'id': category.id, 'order_id': category.order})
        elif language == 'en':
            categories.append({'name': category.name_en, 'name_id': f'{category.name_en}_{category.id}', 'id': category.id, 'order_id': category.order})
    categories = sorted(categories, key=lambda d: d['order_id'])
    products = []
    if breakfast_mode:
        products = Product.objects.filter(id__in=breakfast_list)
    else:
        for category in categories:
            for product in Product.objects.filter(category=Category.objects.get(id=category['id']), id__lte=301).order_by('product_nr'):
                products.append(product)
    context = {
        'language': language,
        'table_hash': table_hash,
        'menu_topic': menu_topic,
        'all_categories': all_categories,
        'categories': categories,
        'products': products,
        'in_basket': in_basket,
        'basket_products': basket_products,
    }
    return render(request, 'menu/menu.html', context=context)


def category_change(request, language, table_hash, category):
    if category == 0:
        categories = []
        products = []
        for category in Category.objects.all():
            if language == 'de':
                categories.append({'id': category.id, 'order_id': category.order})
            elif language == 'tr':
                categories.append({'id': category.id, 'order_id': category.order})
            elif language == 'en':
                categories.append({'id': category.id, 'order_id': category.order})
        categories = sorted(categories, key=lambda d: d['order_id'])
        for category in categories:
            for product in Product.objects.filter(category=get_object_or_404(Category, id=category.get('id')), id__lte=301).order_by('product_nr'):
                products.append(product)
    else:
        products = Product.objects.filter(category=get_object_or_404(Category, id=category), id__lte=301).order_by('product_nr')
    context = {
        'language': language,
        'table_hash': table_hash,
        'products': products,
    }
    return render(request, 'htmx_partials/products.html', context)


def product(request, language, table_hash, product_id):
    product_obj = get_object_or_404(Product, id=product_id)
    table = get_object_or_404(Table, table_hash=table_hash)
    in_basket = False
    in_basket_amount = 0
    if Session.objects.filter(table=table, end__isnull=True).exists():
        session = Session.objects.filter(table=table, end__isnull=True).last()
        if Basket.objects.filter(session=session, finished=False).exists():
            basket = Basket.objects.filter(session=session, finished=False).last()
            if basket.orders.exists():
                in_basket = True
            for order in basket.orders.all():
                if order.product == product_obj:
                    in_basket_amount += 1
    context = {
        'language': language,
        'table_hash': table_hash,
        'product': product_obj,
        'in_basket': in_basket,
        'in_basket_amount': in_basket_amount,
        'status': 'alpha',
    }
    return render(request, 'menu/product.html', context=context)


def add_order_to_basket(request, language, table_hash, product_id):
    def session_nr_generator():
        test = randint(1000000, 9999999)
        while Session.objects.filter(session_nr=test).exists():
            test = randint(1000000, 9999999)
        return test

    product_obj = get_object_or_404(Product, id=product_id)
    table = get_object_or_404(Table, table_hash=table_hash)

    if request.method == 'POST':
        if Session.objects.filter(table=table, end__isnull=True).exists():
            session = Session.objects.filter(table=table, end__isnull=True).last()
            if Basket.objects.filter(session=session, finished=False).exists():
                basket = Basket.objects.filter(session=session, finished=False).last()
            else:
                basket = Basket.objects.create(session=session, created_time=datetime.now())
        else:
            session = Session.objects.create(table=table, start=datetime.now(), session_nr=session_nr_generator())
            basket = Basket.objects.create(session=session, created_time=datetime.now())
        amount = int(request.POST.get('hidden-amount'))
        notes = request.POST.get('additional-info-text-field')
        try:
            gang = int(request.POST.get('gang-radio'))
        except TypeError:
            gang = 1
        orders = []
        if amount > 1:
            try:
                order_group_id = Order.objects.filter(order_group_id__isnull=False).order_by(
                    '-order_group_id').first().order_group_id + 1
            except:
                order_group_id = 1
        for i in range(amount):
            if amount > 1:
                order = Order.objects.create(order_group_id=order_group_id, order_by_customer=True, product=product_obj,
                                             notes=notes, gang=gang,
                                             price=product_obj.price)
                orders.append(order)
            else:
                order = Order.objects.create(order_by_customer=True, product=product_obj, notes=notes, gang=gang,
                                             price=product_obj.price)
                orders.append(order)
        for order in orders:
            basket.orders.add(order)
        if request.POST.getlist('extras'):
            extras_list = request.POST.getlist('extras')
            extras = []
            for extra in extras_list:
                extras.append(AvailableExtra.objects.get(id=int(extra)))
            for extra in extras:
                for order in orders:
                    order.chosen_extras.add(extra)
                    order.price += extra.price
                    order.save()
        if request.POST.getlist('good_withs'):
            good_withs_list = request.POST.getlist('good_withs')
            for good_with in good_withs_list:
                good_with_product = get_object_or_404(Product, id=good_with)
                basket.orders.add(Order.objects.create(order_by_customer=True, product=good_with_product, gang=gang,
                                                       price=good_with_product.price))
    return redirect('menu', language=language, table_hash=table_hash)


def basket(request, language, table_hash):
    was_in_product = False
    prev = request.META.get('HTTP_REFERER')
    try:
        finder = prev.find('product')
        if finder != -1:
            was_in_product = True
    except AttributeError:
        pass
    table = get_object_or_404(Table, table_hash=table_hash)
    in_basket = False
    basket_obj = None
    orders = []
    total = 0
    if Session.objects.filter(table=table, end__isnull=True).exists():
        session = Session.objects.filter(table=table, end__isnull=True).last()
        if Basket.objects.filter(session=session, finished=False).exists():
            basket_obj = Basket.objects.filter(session=session, finished=False).last()
            if basket_obj.orders.exists():
                in_basket = True
                for order in basket_obj.orders.all():
                    if order.order_group_id:
                        found = False
                        for o in orders:
                            try:
                                if o['group_id'] == order.order_group_id:
                                    o['amount'] += 1
                                    o['price'] += order.price
                                    found = True
                                    break
                            except TypeError:
                                break
                        if not found:
                            extras = []
                            if order.chosen_extras:
                                for extra in order.chosen_extras.all():
                                    extras.append(extra)
                            if language == 'de':
                                orders.append({'id': order.id, 'name': order.product.name_de, 'extras': extras,
                                               'price': order.price,
                                               'amount': 1, 'group_id': order.order_group_id})
                            elif language == 'tr':
                                orders.append({'id': order.id, 'name': order.product.name_tr, 'extras': extras,
                                               'price': order.price,
                                               'amount': 1, 'group_id': order.order_group_id})
                            elif language == 'en':
                                orders.append({'id': order.id, 'name': order.product.name_en, 'extras': extras,
                                               'price': order.price,
                                               'amount': 1, 'group_id': order.order_group_id})
                    else:
                        extras = []
                        if order.chosen_extras:
                            for extra in order.chosen_extras.all():
                                extras.append(extra)
                        if language == 'de':
                            orders.append(
                                {'id': order.id, 'name': order.product.name_de, 'extras': extras, 'price': order.price,
                                 'amount': 1, 'group_id': None})
                        elif language == 'tr':
                            orders.append(
                                {'id': order.id, 'name': order.product.name_tr, 'extras': extras, 'price': order.price,
                                 'amount': 1, 'group_id': None})
                        elif language == 'en':
                            orders.append(
                                {'id': order.id, 'name': order.product.name_en, 'extras': extras, 'price': order.price,
                                 'amount': 1, 'group_id': None})
                    total += order.price
    menu_topic = ''
    if language == 'de':
        menu_topic = 'Warenkorb'
    elif language == 'tr':
        menu_topic = 'Sepet'
    elif language == 'en':
        menu_topic = 'Basket'
    context = {
        'language': language,
        'table_hash': table_hash,
        'table_nr': table.nr,
        'menu_topic': menu_topic,
        'in_basket': in_basket,
        'basket': basket_obj,
        'orders': orders,
        'total': total,
        'was_in_product': was_in_product,
    }
    return render(request, 'menu/basket.html', context=context)


def basket_poll(request, language, table_hash):
    prev = request.META.get('HTTP_REFERER')
    finder = prev.find('product')
    was_in_product = False
    if finder != -1:
        was_in_product = True
    table = get_object_or_404(Table, table_hash=table_hash)
    in_basket = False
    basket_obj = None
    orders = []
    total = 0
    if Session.objects.filter(table=table, end__isnull=True).exists():
        session = Session.objects.filter(table=table, end__isnull=True).last()
        if Basket.objects.filter(session=session, finished=False).exists():
            basket_obj = Basket.objects.filter(session=session, finished=False).last()
            if basket_obj.orders.exists():
                in_basket = True
                for order in basket_obj.orders.all():
                    if order.order_group_id:
                        found = False
                        for o in orders:
                            try:
                                if o['group_id'] == order.order_group_id:
                                    o['amount'] += 1
                                    o['price'] += order.price
                                    found = True
                                    break
                            except TypeError:
                                break
                        if not found:
                            extras = []
                            if order.chosen_extras:
                                for extra in order.chosen_extras.all():
                                    extras.append(extra)
                            if language == 'de':
                                orders.append({'id': order.id, 'name': order.product.name_de, 'extras': extras,
                                               'price': order.price,
                                               'amount': 1, 'group_id': order.order_group_id})
                            elif language == 'tr':
                                orders.append({'id': order.id, 'name': order.product.name_tr, 'extras': extras,
                                               'price': order.price,
                                               'amount': 1, 'group_id': order.order_group_id})
                            elif language == 'en':
                                orders.append({'id': order.id, 'name': order.product.name_en, 'extras': extras,
                                               'price': order.price,
                                               'amount': 1, 'group_id': order.order_group_id})
                    else:
                        extras = []
                        if order.chosen_extras:
                            for extra in order.chosen_extras.all():
                                extras.append(extra)
                        if language == 'de':
                            orders.append(
                                {'id': order.id, 'name': order.product.name_de, 'extras': extras, 'price': order.price,
                                 'amount': 1, 'group_id': None})
                        elif language == 'tr':
                            orders.append(
                                {'id': order.id, 'name': order.product.name_tr, 'extras': extras, 'price': order.price,
                                 'amount': 1, 'group_id': None})
                        elif language == 'en':
                            orders.append(
                                {'id': order.id, 'name': order.product.name_en, 'extras': extras, 'price': order.price,
                                 'amount': 1, 'group_id': None})
                    total += order.price
    menu_topic = ''
    if language == 'de':
        menu_topic = 'Warenkorb'
    elif language == 'tr':
        menu_topic = 'Sepet'
    elif language == 'en':
        menu_topic = 'Basket'
    context = {
        'language': language,
        'table_hash': table_hash,
        'table_nr': table.nr,
        'menu_topic': menu_topic,
        'in_basket': in_basket,
        'basket': basket_obj,
        'orders': orders,
        'total': total,
        'was_in_product': was_in_product
    }
    return render(request, 'htmx_partials/basket_poll.html', context=context)


def decrease_order_amount(request, language, table_hash, order_id):
    order_obj = get_object_or_404(Order, id=order_id)
    basket_obj = Basket.objects.get(orders=order_obj)
    total = 0
    extras = []
    for extra in order_obj.chosen_extras.all():
        extras.append(extra)
    group_id = None
    amount = 0
    price = 0
    if order_obj.order_group_id:
        group = Order.objects.filter(order_group_id=order_obj.order_group_id).order_by('-id')
        group_id = order_obj.order_group_id
        n = 1
        for order in group:
            if n == 0:
                amount += 1
                price += order.price
            else:
                n -= 1
                order.delete()
        if amount == 1:
            order_obj.order_group_id = None
            order_obj.save()
    for order in basket_obj.orders.all():
        total += order.price
    if language == 'de':
        order = {'id': order_obj.id, 'name': order_obj.product.name_de, 'extras': extras, 'price': price,
                 'amount': amount, 'group_id': group_id}
    elif language == 'tr':
        order = {'id': order_obj.id, 'name': order_obj.product.name_tr, 'extras': extras, 'price': price,
                 'amount': amount, 'group_id': group_id}
    elif language == 'en':
        order = {'id': order_obj.id, 'name': order_obj.product.name_en, 'extras': extras, 'price': price,
                 'amount': amount, 'group_id': group_id}
    context = {
        'language': language,
        'table_hash': table_hash,
        'order': order,
        'total': total
    }
    return render(request, 'htmx_partials/order.html', context=context)


def delete_order_prompt(request, language, table_hash, order_id):
    context = {
        'language': language,
        'table_hash': table_hash,
        'order_id': order_id
    }
    return render(request, 'htmx_partials/delete_order_modal_active.html', context)


def delete_order(request, language, table_hash, order_id):
    order_obj = get_object_or_404(Order, id=order_id)
    if order_obj.order_group_id:
        for order in Order.objects.filter(order_group_id=order_obj.order_group_id):
            order.delete()
    else:
        order_obj.delete()
    return redirect('basket', language=language, table_hash=table_hash)


def increase_order_amount(request, language, table_hash, order_id):
    order_obj = get_object_or_404(Order, id=order_id)
    basket_obj = Basket.objects.get(orders=order_obj)
    total = 0
    amount = 0
    price = 0
    group_id = None
    extras = []
    for extra in order_obj.chosen_extras.all():
        extras.append(extra)
    if order_obj.order_group_id:
        group_id = order_obj.order_group_id
        order_obj.pk = None
        order_obj.save()
        for extra in extras:
            order_obj.chosen_extras.add(extra)
        basket_obj.orders.add(order_obj)
    else:
        try:
            new_order_id = Order.objects.filter(order_group_id__isnull=False).order_by(
                '-order_group_id').first().order_group_id + 1
            order_obj.order_group_id = new_order_id
            order_obj.save()
            group_id = new_order_id
        except:
            order_obj.order_group_id = 1
            group_id = 1
            order_obj.save()
        order_obj.pk = None
        order_obj.save()
        for extra in extras:
            order_obj.chosen_extras.add(extra)
        basket_obj.orders.add(order_obj)
    for order in Order.objects.filter(order_group_id=group_id):
        price += order.price
        amount += 1
    for order in basket_obj.orders.all():
        total += order.price
    order_obj = Order.objects.filter(order_group_id=group_id)[0]
    if language == 'de':
        order = {'id': order_obj.id, 'name': order_obj.product.name_de, 'extras': extras, 'price': price,
                 'amount': amount, 'group_id': group_id}
    elif language == 'tr':
        order = {'id': order_obj.id, 'name': order_obj.product.name_tr, 'extras': extras, 'price': price,
                 'amount': amount, 'group_id': group_id}
    elif language == 'en':
        order = {'id': order_obj.id, 'name': order_obj.product.name_en, 'extras': extras, 'price': price,
                 'amount': amount, 'group_id': group_id}
    context = {
        'language': language,
        'table_hash': table_hash,
        'order': order,
        'total': total
    }
    return render(request, 'htmx_partials/order.html', context=context)


def edit_order(request, language, table_hash, order_id):
    order_obj = get_object_or_404(Order, id=order_id)
    basket_obj = get_object_or_404(Basket, orders=order_obj)
    amount = 0
    total = 0
    if order_obj.order_group_id:
        for order in Order.objects.filter(order_group_id=order_obj.order_group_id):
            amount += 1
            total += order.price
    else:
        amount = 1
        total = order_obj.price
    product_obj = order_obj.product
    chosen_extras = []
    for extra in order_obj.chosen_extras.all():
        chosen_extras.append(extra)
    if request.method == 'POST':
        amount = int(request.POST.get('hidden-amount'))
        notes = request.POST.get('additional-info-text-field')
        gang = int(request.POST.get('gang-radio'))
        if order_obj.order_group_id:
            all_orders = Order.objects.filter(order_group_id=order_obj.order_group_id)
        else:
            all_orders = Order.objects.filter(id=order_obj.id)
        extras = []
        if request.POST.getlist('extras'):
            extras_list = request.POST.getlist('extras')
            for extra in extras_list:
                extras.append(get_object_or_404(AvailableExtra, id=int(extra)))
        if amount == 1:
            if order_obj.order_group_id:
                to_deleted_orders_amount = len(all_orders) - 1
                for order in all_orders:
                    if to_deleted_orders_amount > 0:
                        order.delete()
                        to_deleted_orders_amount -= 1
        if amount == 2:
            if not order_obj.order_group_id:
                try:
                    order_group_id = Order.objects.filter(order_group_id__isnull=False).order_by(
                        '-order_group_id').first().order_group_id + 1
                except:
                    order_group_id = 1
                order_obj.order_group_id = order_group_id
                order_obj.save()
                order_obj.pk = None
                order_obj.save()
                basket_obj.orders.add(order_obj)
                basket_obj.save()
            else:
                diff = len(all_orders) - amount
                if diff > 0:
                    while diff != 0:
                        deleted_order = Order.objects.filter(order_group_id=order_obj.order_group_id).last().delete()
                        diff -= 1
                else:
                    while diff != 0:
                        order_obj.pk = None
                        order_obj.save()
                        basket_obj.orders.add(order_obj)
                        basket_obj.save()
                        diff += 1
        if amount > 2:
            if order_obj.order_group_id:
                diff = len(all_orders) - amount
                if diff > 0:
                    for order in all_orders:
                        if diff != 0:
                            order.delete()
                            diff -= 1
                else:
                    while diff != 0:
                        order_obj.pk = None
                        order_obj.save()
                        basket_obj.orders.add(order_obj)
                        basket_obj.save()
                        diff += 1
            else:
                try:
                    order_group_id = Order.objects.filter(order_group_id__isnull=False).order_by(
                        '-order_group_id').first().order_group_id + 1
                except:
                    order_group_id = 1
                order_obj.order_group_id = order_group_id
                order_obj.save()
                diff = amount - 1
                while diff != 0:
                    order_obj.pk = None
                    order_obj.save()
                    basket_obj.orders.add(order_obj)
                    basket_obj.save()
                    diff -= 1
        orders = []
        if order_obj.order_group_id:
            for order in Order.objects.filter(order_group_id=order_obj.order_group_id):
                orders.append(order)
        else:
            orders.append(order_obj)
        for order in orders:
            order.chosen_extras.clear()
            order.price = order.product.price
            order.notes = notes
            order.gang = gang
            if extras:
                for extra in extras:
                    order.chosen_extras.add(extra)
                    order.price += extra.price
            order.save()

        return redirect('basket', language=language, table_hash=table_hash)
    context = {
        'language': language,
        'table_hash': table_hash,
        'order': order_obj,
        'product': product_obj,
        'in_basket': True,
        'chosen_extras': chosen_extras,
        'amount': amount,
        'total': total
    }
    return render(request, 'menu/edit_order.html', context)


def send_basket(request, language, table_hash, basket_id):
    basket_obj = get_object_or_404(Basket, id=basket_id)
    basket_obj.finished = True
    basket_obj.finished_time = datetime.now()
    basket_obj.web_order = True
    basket_obj.save()
    context = {
        'language': language,
        'table_hash': table_hash,
    }
    return render(request, 'menu/basket_sent.html', context)


def my_orders(request, language, table_hash):
    session_obj = Session.objects.filter(table=get_object_or_404(Table, table_hash=table_hash), end__isnull=True)
    baskets_sum = 0
    if session_obj:
        session = session_obj = Session.objects.filter(table=get_object_or_404(Table, table_hash=table_hash),
                                                       end__isnull=True).last()
        baskets = Basket.objects.filter(session=session, finished=True)
        baskets_sum = 0
        for basket in baskets:
            for order in basket.orders.all():
                baskets_sum += order.price
    else:
        session = None
        baskets = None
    context = {
        'language': language,
        'table_hash': table_hash,
        'baskets': baskets,
        'sum': baskets_sum
    }
    return render(request, 'home/my_orders.html', context=context)


def finished_order_details(request, language, table_hash, order_id):
    order = get_object_or_404(Order, id=order_id)
    extras_price = None
    if order.chosen_extras:
        extras_price = 0
        for extra in order.chosen_extras.all():
            extras_price += extra.price
    context = {
        'language': language,
        'table_hash': table_hash,
        'order': order,
        'extras_price': extras_price
    }
    return render(request, 'home/finished_order_details.html', context=context)


def kitchen(request):
    baskets = Basket.objects.filter(created_time__day=datetime.now().day, cooked=False, finished=True,
                                    web_order=True).order_by(
        '-created_time')
    nc = []
    bell = False
    for b in baskets:
        nc.append(b)
        if (datetime.now(bln) - b.finished_time) < timedelta(seconds=5):
            bell = True

    print(bell)
    context = {
        'nc': nc,
        'bell': bell
    }
    return render(request, 'kitchen/kitchen_main.html', context)


def kitchen_cooked(request, b):
    basket = get_object_or_404(Basket, id=b)
    basket.cooked = True
    basket.cooked_time = datetime.now()
    basket.save()
    return redirect('kitchen')


def patron(request):
    return render(request, 'boss/patron.html')


def patron_data(request):
    context = {}
    if request.method == 'POST':
        password = request.POST.get('password')
        date = datetime.strptime(request.POST.get('date'), '%Y-%m-%d')
        tables_start = request.POST.get('table-range-start')
        tables_end = request.POST.get('table-range-end')
        if (password == '1234') and date and tables_start and tables_end:
            baskets = Basket.objects.filter(finished_time__day=date.day, finished_time__month=date.month,
                                            finished_time__year=date.year, cooked=True, finished=True, web_order=True)
            bp = {'sales': 0, 'amount': 0}
            be = {'sales': 0, 'amount': 0}
            bt = {'sales': 0, 'amount': 0}
            e = {'sales': 0, 'amount': 0}
            for b in baskets:
                for o in b.orders.all():
                    if o.product.id == 275:
                        bp['sales'] += o.product.price
                        bp['amount'] += 1
                        if o.chosen_extras.exists():
                            for ex in o.chosen_extras.all():
                                e['sales'] += ex.price
                                e['amount'] += 1
                    elif o.product.id == 276:
                        be['sales'] += o.product.price
                        be['amount'] += 1
                        if o.chosen_extras.exists():
                            for ex in o.chosen_extras.all():
                                e['sales'] += ex.price
                                e['amount'] += 1
                    elif o.product.id == 277:
                        bt['sales'] += o.product.price
                        bt['amount'] += 1
                        if o.chosen_extras.exists():
                            for ex in o.chosen_extras.all():
                                e['sales'] += ex.price
                                e['amount'] += 1
                    elif o.product.id in waiter_list:
                        e['sales'] += o.price
                        e['amount'] += 1
            context['bp'] = bp
            context['be'] = be
            context['bt'] = bt
            context['e'] = e
            subtotal_amount = bp['amount'] + be['amount'] + bt['amount']
            subtotal_sales = bp['sales'] + be['sales'] + bt['sales']
            total_amount = subtotal_amount + e['amount']
            total_sales = subtotal_sales + e['sales']
            context['subtotal'] = {'amount': subtotal_amount, 'sales': subtotal_sales}
            context['total'] = {'amount': total_amount, 'sales': total_sales}
            table_nr = int(tables_start)
            tables = []
            while table_nr <= int(tables_end):
                total: float = 0
                for basket in baskets:
                    if int(basket.session.table.nr) == table_nr:
                        for o in basket.orders.all():
                            total += o.price
                tables.append({'nr': table_nr, 'total': total})
                table_nr += 1
            context['tables'] = tables
            return render(request, 'htmx_partials/patron_data.html', context)


def menu_web(request, language):
    all_categories_title = ''
    if language == 'de':
        all_categories_title = 'Alle Kategorien'
    elif language == 'tr':
        all_categories_title = 'Tüm Kategoriler'
    elif language == 'en':
        all_categories_title = 'All Categories'
    categories = []
    products = []
    cat_list = []
    for category in Category.objects.using('default').all().order_by('order'):
        n = 0
        if language == 'de':
            categories.append(
                {'name': category.name_de, 'name_id': f'{category.name_de}_{category.id}', 'id': category.id})
        elif language == 'tr':
            categories.append(
                {'name': category.name_tr, 'name_id': f'{category.name_tr}_{category.id}', 'id': category.id})
        elif language == 'en':
            categories.append(
                {'name': category.name_en, 'name_id': f'{category.name_en}_{category.id}', 'id': category.id})
        for product in Product.objects.filter(category=category).order_by('product_nr'):
            for c in cat_list:
                if c['cat_id'] == category.id:
                    n += 1
            if n == 0:
                if language == 'de':
                    cat_list.append({'cat_id': category.id, 'cat_name': category.name_de, 'product_id': product.id})
                elif language == 'tr':
                    cat_list.append({'cat_id': category.id, 'cat_name': category.name_tr, 'product_id': product.id})
                elif language == 'en':
                    cat_list.append({'cat_id': category.id, 'cat_name': category.name_en, 'product_id': product.id})
            products.append(product)
    print(cat_list)
    # products = Product.objects.using('default').all().order_by('product_nr')
    context = {
        'language': language,
        'all_categories': True,
        'all_categories_title': all_categories_title,
        'categories': categories,
        'products': products,
        'cat_list': cat_list
    }
    return render(request, 'menu/menu_web.html', context=context)


def category_change_web(request, language, category):
    all_categories = False
    cat_list = []
    if category == 0:
        categories = []
        products = []
        for category in Category.objects.using('default').all().order_by('order'):
            n = 0
            for product in Product.objects.filter(category=category).order_by('product_nr'):
                for c in cat_list:
                    if c['cat_id'] == category.id:
                        n += 1
                if n == 0:
                    if language == 'de':
                        cat_list.append({'cat_id': category.id, 'cat_name': category.name_de, 'product_id': product.id})
                    elif language == 'tr':
                        cat_list.append({'cat_id': category.id, 'cat_name': category.name_tr, 'product_id': product.id})
                    elif language == 'en':
                        cat_list.append({'cat_id': category.id, 'cat_name': category.name_en, 'product_id': product.id})
                products.append(product)
        # products = Product.objects.all().using('default').order_by('product_nr')
        all_categories = True
    else:
        category_q = Category.objects.using('default').get(id=category)
        products = Product.objects.using('default').filter(category=category_q).order_by(
            'product_nr')
    context = {
        'language': language,
        'products': products,
        'all_categories': all_categories,
        'cat_list': cat_list
    }
    return render(request, 'htmx_partials/products_web.html', context)

# def pdf_test(request):
#     # Render the HTML template
#     context = {
#         'tables': [1, 2, 3],
#     }
#     # Render the HTML template
#     # template = get_template()
#     html = render_to_string('table_qr_template/test.html', context)
#     print(html)
#     # Create the PDF file
#     pdf_file = HTML(string=html).write_pdf()
#     # Return the PDF file as a response
#     response = HttpResponse(pdf_file, content_type='application/pdf')
#     response['Content-Disposition'] = 'filename="mypdf.pdf"'
#     return response
