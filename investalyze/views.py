from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from .models import User, Order
from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages

import pandas as pd
import numpy as np
import io
import csv 
import dateutil.parser

# Create your views here.
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
            messages.error(request,"Invalid username and/or password.")
            return HttpResponseRedirect(reverse("login"))
    else:
        return render(request, "investalyze/login.html")

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))

def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure passwords match
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            messages.error(request, "Passwords must match.")
            return HttpResponseRedirect(reverse("register"))

        # Try to create new user
        try:
            user = User.objects.create_user(username, email, password)
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

        # Get filled orders and convert the result to dict
        df = pd.read_csv(data, sep=",")
        df = df.loc[df['Status'] == 'Filled']
        df_records = df.to_dict('records')

        # Create list of Order objects
        order_objects = [Order(
            ticker=record['Symbol'],
            side=record['Side'], 
            quantity=record['Total Qty'], 
            price=record['Price'][1:], 
            time=dateutil.parser.parse(record['Filled Time'][:-3]), 
            user=request.user
        ) for record in df_records]
        
        Order.objects.bulk_create(order_objects, ignore_conflicts=True)

        return HttpResponseRedirect(reverse("dashboard"))
    else:
        orders = request.user.orders.all()
        return render(request, "investalyze/dashboard.html")
