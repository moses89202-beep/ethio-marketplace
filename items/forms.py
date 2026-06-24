from django import forms
from.models import Item

class NewItemForm(forms.ModelForm):
    price = forms.DecimalField(min_value=0, widget=forms.NumberInput())
    class Meta:
        model = Item
        fields = ('category', 'name', 'description', 'price', 'picture')


class EditItemForm(forms.ModelForm):
    price = forms.DecimalField(min_value=0, widget=forms.NumberInput())
    class Meta:
        model = Item
        fields = ('name', 'description', 'price', 'picture', 'is_sold')

