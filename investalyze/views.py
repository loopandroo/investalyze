from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from .models import User, Order
from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
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
        csv_file = request.FILES['file']

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Trading history must be in a CSV file.')
            return HttpResponseRedirect(reverse("dashboard"))
        
        data_set = csv_file.read().decode('UTF-8').split('\n')

        reader = csv.reader(data_set)

        for row in reader:
            try:
                # Check if order was filled
                if row[3] == "Filled":
                    ticker = row[1]
                    side = row[2]
                    quantity = row[5]
                    price = row[6][1:]
                    time = dateutil.parser.parse(row[10][:-3])
                    
                    order = Order(ticker=ticker, side=side, quantity=quantity, price=price, time=time, user=request.user)
                    
                    # Skip order if it already exists
                    try:
                        order.save()
                    except IntegrityError:
                        pass
                    
            except IndexError:
                pass

        return HttpResponseRedirect(reverse("dashboard"))
    else:
        return render(request, "investalyze/dashboard.html")