from django import forms
from .models import User

class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    class Meta:
        model = User
        # Lưu ý: confirm_password không nằm trong model nên không cho vào fields của Meta
        fields = ['username', 'email', 'password', 'avatar', 'first_name', 'last_name', 'country']

    # Sắp xếp đúng thứ tự các ô giống hệt hình đề bài
    field_order = ['username', 'email', 'password', 'confirm_password', 'avatar', 'first_name', 'last_name', 'country']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Mật khẩu xác nhận không khớp.')
        return cleaned_data