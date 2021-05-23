from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls.base import translate_url
from .models import User, Order, Lot
from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages

import io
import dateutil.parser
import csv


def index(request):
    return render(request, "investalyze/index.html")


def login_view(request):
    if request.method == "POST":
        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("dashboard"))
        else:
            messages.error(request, "Invalid username and/or password.")
            return HttpResponseRedirect(reverse("login"))
    else:
        return render(request, "investalyze/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]

        # Ensure passwords match
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            messages.error(request, "Passwords must match.")
            return HttpResponseRedirect(reverse("register"))

        # Try to create new user
        try:
            user = User.objects.create_user(username, password)
            user.save()
        except IntegrityError:
            messages.error(request, "Username already taken.")
            return HttpResponseRedirect(reverse("register"))

        login(request, user)
        return HttpResponseRedirect(reverse("dashboard"))
    else:
        return render(request, "investalyze/register.html")


@login_required
def dashboard(request):
    if request.method == "POST":
        file = request.FILES['file']

        if not file.name.endswith('.csv'):
            messages.error(request, 'Trading history must be in a CSV file.')
            return HttpResponseRedirect(reverse("dashboard"))

        data_set = file.read().decode('UTF-8')
        # Convert django file object into in-memory text stream
        data = io.StringIO(data_set)

        records = csv.DictReader(data)

        orders = request.user.orders.all()

        try:
            order_instances = [Order(
                ticker=record['Symbol'],
                side=record['Side'],
                quantity=record['Total Qty'],
                price=record['Price'].replace('@', ''),
                time=dateutil.parser.parse(record['Filled Time'][:-3]),
                user=request.user)
                for record in records
                if record['Status'] == 'Filled' and not isDuplicate(record, orders)]
        except Exception:
            messages.error(
                request,
                'No trade executions were found in the file selected.')

        if order_instances:
            Order.objects.bulk_create(order_instances)

            all_orders = request.user.orders.all().order_by('time')
            for sell_order in all_orders.filter(side='Sell', lot=None):
                create_lot(sell_order, all_orders)

            messages.success(
                request, 'Trade executions were imported successfully.')

        else:
            messages.info(
                request,
                'Novel trade executions were not found in the file selected.')

        return HttpResponseRedirect(reverse("dashboard"))
    else:
        return render(request, "investalyze/dashboard.html")


def isDuplicate(record, orders):
    queryset = orders.filter(
        ticker=record['Symbol'],
        side=record['Side'],
        price=record['Price'].replace('@', ''),
        time=dateutil.parser.parse(record['Filled Time'][:-3])
    )
    return queryset.exists()


def create_lot(sell_order, all_orders):
    ''' Creates a lot instance for the sell_order and adds respective buy orders to lot.orders.
        If a buy order is only partially needed to complete a given sell_order, the buy order is split.
    '''
    lot = Lot(user=sell_order.user)
    lot.save()

    lot.orders.add(sell_order)

    num_accounted = 0
    num_sold = sell_order.quantity

    # while qty of shares accounted for != qty of shares sold
    while num_accounted != num_sold:
        buy_order_queryset = all_orders.filter(
            ticker=sell_order.ticker, side='Buy', lot=None)

        # negative buy orders
        if not buy_order_queryset:
            return

        buy_order = buy_order_queryset[0]   # oldest order not already in a lot
        num_bought = buy_order.quantity
        num_unaccounted = num_sold - num_accounted     # qty of unaccounted shares

        # transfer max qty of shares from buy_order to num_accounted
        if num_bought <= num_unaccounted:
            lot.orders.add(buy_order)
            num_accounted += num_bought
        else:
            # split buy_order
            buy_order.quantity -= num_unaccounted

            buy_order.pk = None                     
            buy_order.quantity = num_unaccounted
            buy_order.save()
            lot.orders.add(buy_order)

            num_accounted += num_unaccounted
