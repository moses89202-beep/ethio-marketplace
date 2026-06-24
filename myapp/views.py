from django.shortcuts import redirect, render
from items.models import *
from .forms import *

# Create your views here.

def home(request):
    items = Item.objects.filter(is_sold=False).order_by('-created_at')[0:6]
    categories = Category.objects.all()
    return render(request, 'home.html', {
        'categories': categories,
        'items': items
    })

def contact(request):
    return render(request, 'contact.html')

def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('/login/')
    else:
        form = SignupForm()

    return render(request, 'signup.html', {
        'form': form
    })

