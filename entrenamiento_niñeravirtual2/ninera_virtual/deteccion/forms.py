from django import forms


class UploadForm(forms.Form):
    """Formulario base para subir imagenes o videos al modelo."""

    file = forms.FileField(
        label="Archivo",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "dash-input-file",
                "id": "upload_file_input",
                "accept": "image/*,video/*",
                "capture": "environment",
            }
        ),
    )
    notes = forms.CharField(
        label="Notas",
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Notas opcionales",
                "class": "dash-input-text",
            }
        ),
    )


class WebLoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Ingresa tu email",
                "class": "nv-input",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Contrasena",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Ingresa tu contrasena",
                "class": "nv-input",
                "autocomplete": "current-password",
            }
        ),
    )


class WebRegisterForm(forms.Form):
    name = forms.CharField(
        label="Nombre completo",
        min_length=2,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nombre y apellidos",
                "class": "nv-input",
                "autocomplete": "name",
            }
        ),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "usuario@dominio.com",
                "class": "nv-input",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Contrasena",
        min_length=6,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Minimo 6 caracteres",
                "class": "nv-input",
                "autocomplete": "new-password",
            }
        ),
    )
    confirm_password = forms.CharField(
        label="Confirmar contrasena",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Repite la contrasena",
                "class": "nv-input",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
        if password and confirm and password != confirm:
            self.add_error("confirm_password", "Las contrasenas deben coincidir.")
        return cleaned
