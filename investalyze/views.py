from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls.base import translate_url
from .models import User, Order
from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages

import io, copy, dateutil.parser, csv


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

        # Convert django file object into in-memory text stream
        data_set = file.read().decode('UTF-8')
        data = io.StringIO(data_set)

        records = csv.DictReader(data)

        try:
            order_objects = [Order(
                ticker=record['Symbol'],
                side=record['Side'],
                quantity=record['Total Qty'],
                price=record['Price'].replace('@', ''),
                time=dateutil.parser.parse(record['Filled Time'][:-3]),
                user=request.user)
                for record in records
                if record['Status'] == 'Filled']

            Order.objects.bulk_create(order_objects, ignore_conflicts=True)
            messages.success(request, 'Trade executions were imported successfully.')
        except KeyError:
            messages.error(request, 'No trade executions were found in the file selected.')

        return HttpResponseRedirect(reverse("dashboard"))
    else:
        orders = request.user.orders.all().order_by('time')

        # Populate a Dict mapping each ticker to a list of its buy orders
        unique_tickers = {
            order.ticker: list(orders.filter(side='Buy', ticker=order.ticker))
            for order in orders}

        # List of transactions 
        transactions = [
            match(sell_order, unique_tickers[sell_order.ticker])
            for sell_order in orders.filter(side='Sell')]
        
        print(transactions)
        
        open = {key:value for key, value in unique_tickers.items() if value}

        return render(request, "investalyze/dashboard.html")

def match(sellOrder, buyOrderList):
    ''' Returns a dict containing the sell order and respective buy order(s) (FIFO)
        Removes all shares sold from buyOrderList
    '''

    res = {'sell': sellOrder, 'buy': []}
    numAccounted = 0
    numSold = sellOrder.quantity

    # While qty of shares accounted for != qty of shares sold
    while numAccounted != numSold:
        # Negative Buy Orders
        if not buyOrderList:
            return res

        buyOrder = buyOrderList[0]    # First order in list
        numBought = buyOrder.quantity
        numMissing = numSold - numAccounted     # Qty of unaccounted shares

        # Transfer max qty of shares from buyOrder to numAccounted so as to not exceed numMissing
        if numBought <= numMissing:
            buyOrderList.remove(buyOrder)

            res['buy'].append(buyOrder)
            numAccounted += numBought
        else:
            buyOrder.quantity -= numMissing

            transfer = copy.copy(buyOrder)
            transfer.quantity = numMissing

            res['buy'].append(transfer)
            numAccounted += numMissing
    return res