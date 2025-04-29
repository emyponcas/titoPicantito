from django.shortcuts import render
from templates import *

# Create your views here.

def go_home(request):
    return render(request, 'home.html')

def go_conocenos(request):
    return render(request, 'conocenos.html')

def go_carta(request):
    return render(request, 'carta.html')
