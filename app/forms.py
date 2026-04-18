from django import forms


PROTOCOL_CHOICES = [
    ('ssh', 'SSH'),
    ('telnet', 'Telnet'),
]


class LoginForm(forms.Form):
    """Formulário de autenticação — usuário comum com protocolo e host."""

    protocol = forms.ChoiceField(
        choices=PROTOCOL_CHOICES,
        initial='ssh',
    )
    host = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'field-input',
            'autocomplete': 'off',
        }),
    )
    port = forms.IntegerField(
        min_value=1,
        max_value=65535,
        initial=22,
    )
    common_username = forms.CharField(
        max_length=128,
        widget=forms.TextInput(attrs={
            'class': 'field-input',
            'placeholder': 'usuario',
            'autocomplete': 'off',
        }),
    )
    common_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'field-input',
            'placeholder': '••••••••',
            'autocomplete': 'off',
        }),
    )


# Ações administrativas disponíveis
ACTION_CHOICES = [
    ('create', 'Adicionar Usuário'),
    ('password', 'Alterar Senha'),
    ('group', 'Alterar Grupo'),
    ('delete', 'Excluir Usuário'),
]


class OperationForm(forms.Form):

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'field-select', 'id': 'action-select'}),
    )
    target_username = forms.CharField(
        max_length=128,
        widget=forms.TextInput(attrs={
            'class': 'field-input',
            'placeholder': 'ex: 81055455',
            'autocomplete': 'off',
        }),
    )
    target_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'field-input',
            'placeholder': '••••••••',
            'autocomplete': 'off',
        }),
    )
    group_name = forms.CharField(
        required=False,
        max_length=128,
        widget=forms.TextInput(attrs={
            'class': 'field-input',
            'placeholder': 'adm',
            'autocomplete': 'off',
        }),
    )
    # Senha root enviada junto com a operação (quando o usuário não é root)
    root_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'field-input',
            'placeholder': '••••••••',
            'autocomplete': 'off',
        }),
    )

    def clean(self):
        cleaned = super().clean()
        action = cleaned.get('action')
        target = cleaned.get('target_username', '').strip()
        password = cleaned.get('target_password', '').strip()
        group = cleaned.get('group_name', '').strip()

        if not target:
            raise forms.ValidationError('O login do usuário alvo é obrigatório.')

        if action == 'create' and (not password or not group):
            raise forms.ValidationError('Para criar usuário, senha e grupo são obrigatórios.')

        if action == 'password' and not password:
            raise forms.ValidationError('Para alterar senha, a nova senha é obrigatória.')

        if action == 'group' and not group:
            raise forms.ValidationError('Para alterar grupo, o novo grupo é obrigatório.')

        return cleaned
