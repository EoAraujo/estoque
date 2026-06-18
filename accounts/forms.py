from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from .models import UserProfile

User = get_user_model()


ESTILO = (
    "mt-1 block w-full rounded-md border-gray-300 shadow-sm "
    "focus:border-emerald-500 focus:ring-emerald-500 sm:text-sm"
)


class LoginFormEstilizado(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "class": ESTILO, "placeholder": "Seu usuário", "autofocus": True,
        })
        self.fields["password"].widget.attrs.update({
            "class": ESTILO, "placeholder": "Sua senha",
        })


class UsuarioForm(UserCreationForm):
    """Cadastro/edição de usuários do sistema."""
    email = forms.EmailField(required=True, label="E-mail")
    first_name = forms.CharField(required=False, label="Nome")
    last_name = forms.CharField(required=False, label="Sobrenome")
    is_active = forms.BooleanField(
        required=False, initial=True, label="Usuário ativo",
    )

    class Meta:
        model = User
        fields = (
            "username", "first_name", "last_name", "email",
            "is_active", "password1", "password2",
        )
        labels = {
            "username": "Login (usuário)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "rounded border-gray-300 text-emerald-600 "
                    "shadow-sm focus:ring-emerald-500"
                )
            else:
                field.widget.attrs.setdefault("class", ESTILO)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True  # qualquer usuário cadastrado pode acessar
        if commit:
            user.save()
            # Atualiza dados extras do perfil
            profile, _ = UserProfile.objects.get_or_create(user=user)
            return user
        return user


class UsuarioUpdateForm(forms.ModelForm):
    """Edição de um usuário existente (sem troca obrigatória de senha)."""
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "is_active")
        labels = {"first_name": "Nome", "last_name": "Sobrenome"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault(
                    "class",
                    "rounded border-gray-300 text-emerald-600 "
                    "shadow-sm focus:ring-emerald-500"
                )
            else:
                field.widget.attrs.setdefault("class", ESTILO)


class RedefinirSenhaForm(forms.Form):
    nova_senha1 = forms.CharField(
        label="Nova senha", widget=forms.PasswordInput,
    )
    nova_senha2 = forms.CharField(
        label="Confirme a nova senha", widget=forms.PasswordInput,
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", ESTILO)

    def clean(self):
        cleaned = super().clean()
        s1 = cleaned.get("nova_senha1")
        s2 = cleaned.get("nova_senha2")
        if s1 and s1 != s2:
            self.add_error("nova_senha2", "As senhas não coincidem.")
        if s1 and len(s1) < 6:
            self.add_error("nova_senha1", "A senha deve ter ao menos 6 caracteres.")
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data["nova_senha1"])
        self.user.save()
        return self.user
