from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import *

class RegistroFormulario(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo 8 caracteres'
        }),
        min_length=8,
        help_text="La contraseña debe tener al menos 8 caracteres.",
        required=True
    )

    class Meta:
        model = Usuario
        fields = [
            'nombre',
            'apellidos',
            'fecha_nacimiento',
            'email',
            'telefono',
            'password'  # Eliminamos 'rol' de los campos del formulario
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tu nombre'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tus apellidos'
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'ejemplo@dominio.com'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de teléfono'
            }),
        }
        help_texts = {
            'email': 'Introduce una dirección de correo electrónico válida.',
        }
        error_messages = {
            'email': {
                'unique': "Ya existe un usuario con este correo electrónico.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #si lo necesito que en algunos casos se pueda seleccionar el rol,
        # puedo hacerlo condicionalmente
        if 'initial' in kwargs and 'rol' in kwargs['initial']:
            self.fields['rol'] = forms.ChoiceField(
                choices=Usuario.Rol.choices,
                widget=forms.Select(attrs={'class': 'form-control'}),
                initial=kwargs['initial']['rol']
            )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        #establecer el rol por defecto como CLIENTE si no se especifica
        if not hasattr(user, 'rol') or not user.rol:
            user.rol = Usuario.Rol.CLIENTE
        if commit:
            user.save()
        return user

class LoginFormulario(AuthenticationForm):
    username = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ejemplo@dominio.com'
        })
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Introduce tu contraseña'
        })
    )


class AñadirProductoFormulario(forms.ModelForm):
    class Meta:
        model = Producto
        fields = '__all__'
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'fecha_creacion': forms.DateInput(attrs={'type': 'date'}),
        }


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = '__all__'
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }

##PEDIDOS POR MESA

class PedidoMesaForm(forms.ModelForm):
    class Meta:
        model = PedidoMesa
        fields = ['num_comensales', 'notas']
        widgets = {
            'num_comensales': forms.NumberInput(attrs={'min': 1, 'max': 20}),
            'notas': forms.Textarea(attrs={'rows': 3}),
        }

class LineaPedidoForm(forms.Form):
    producto_id = forms.IntegerField(widget=forms.HiddenInput())
    cantidad = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))

##FORMULARIO DEL PERFIL USUARIO

class UsuarioUpdateForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = [
            'imagen',
            'nombre',
            'apellidos',
            'fecha_nacimiento',
            'email',
            'telefono'
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer que el email sea de solo lectura
        self.fields['email'].disabled = True