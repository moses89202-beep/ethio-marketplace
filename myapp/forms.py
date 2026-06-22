# forms.py
from django import forms
from .models import Profile, ethiopian_phone_regex

class CustomSignupForm(forms.Form):
    phone_number = forms.CharField(
        max_length=13,
        validators=[ethiopian_phone_regex],
        widget=forms.TextInput(attrs={'placeholder': '0912345678 or +251912345678'}),
        label="Ethiopian Phone Number"
    )
    location = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Addis Ababa, Bole'}),
        label="Location"
    )
    # New Input Field
    profile_pic = forms.ImageField(
        required=False,
        label="Profile Picture"
    )

    def signup(self, request, user):
        user.save()
        
        phone = self.cleaned_data['phone_number']
        if phone.startswith('0'):
            phone = '+251' + phone[1:]
            
        # Create the profile and pass the uploaded image file if it exists
        Profile.objects.create(
            user=user,
            phone_number=phone,
            location=self.cleaned_data['location'],
            profile_pic=self.cleaned_data.get('profile_pic') # Safely grabs the file
        )