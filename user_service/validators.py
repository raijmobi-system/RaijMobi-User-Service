import re
from django.core.exceptions import ValidationError
import datetime


def validar_cpf(cpf):
    """
    Valida um CPF (Cadastro de Pessoa Física) brasileiro.
    Remove caracteres não numéricos e verifica os dígitos verificadores.
    """
    cpf = re.sub(r'[^0-9]', '', cpf)

    if len(cpf) != 11:
        raise ValidationError("CPF deve conter 11 dígitos.")

    if cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido.")

    soma1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma1 * 10 % 11) % 10

    soma2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma2 * 10 % 11) % 10

    if not (dig1 == int(cpf[9]) and dig2 == int(cpf[10])):
        raise ValidationError("CPF inválido.")
