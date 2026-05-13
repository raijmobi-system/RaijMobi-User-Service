# serializers.py
from rest_framework import serializers
from .models import Usuario, Perfil
from .validators import validar_cpf   

# class UserRegistrationSerializer(serializers.ModelSerializer):
#     # campos do Perfil que virão na requisição
#     cpf = serializers.CharField(max_length=14, validators=[validar_cpf])
#     telefone = serializers.CharField(max_length=15)
#     tipo_usuario = serializers.ChoiceField(choices=Perfil.TIPO_CHOICES)
#     foto = serializers.ImageField(required=False)

#     password = serializers.CharField(write_only=True, min_length=6)

#     class Meta:
#         model = Usuario
#         fields = ['email', 'nome', 'password', 'cpf', 'telefone', 'tipo_usuario', 'foto']

#     def validate_email(self, value):
#         if Usuario.objects.filter(email=value).exists():
#             raise serializers.ValidationError("Este e-mail já está cadastrado.")
#         return value

#     def create(self, validated_data):
#         # extrai os campos do Perfil
#         perfil_data = {
#             'cpf': validated_data.pop('cpf'),
#             'telefone': validated_data.pop('telefone'),
#             'tipo_usuario': validated_data.pop('tipo_usuario'),
#             'foto': validated_data.pop('foto', None),
#         }
#         password = validated_data.pop('password')

#         # cria o usuário
#         user = Usuario(**validated_data)
#         user.set_password(password)
#         user.save()

#         # define is_motorista automaticamente
#         perfil_data['is_motorista'] = (perfil_data['tipo_usuario'] == 'Motorista')

#         # cria o perfil vinculado
#         Perfil.objects.create(usuario=user, **perfil_data)

#         return user

# serializers.py
# serializers.py
class UserRegistrationSerializer(serializers.ModelSerializer):
    cpf = serializers.CharField(
        max_length=14, validators=[validar_cpf], write_only=True
    )
    telefone = serializers.CharField(max_length=15, write_only=True)
    tipo_usuario = serializers.ChoiceField(
        choices=Perfil.TIPO_CHOICES, write_only=True
    )
    foto = serializers.ImageField(required=False, write_only=True)

    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Usuario
        fields = ['email', 'nome', 'password', 'cpf', 'telefone', 'tipo_usuario', 'foto']
        # password já é write_only, os demais também ficarão

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este e-mail já está cadastrado.")
        return value

    def create(self, validated_data):
        perfil_data = {
            'cpf': validated_data.pop('cpf'),
            'telefone': validated_data.pop('telefone'),
            'tipo_usuario': validated_data.pop('tipo_usuario'),
            'foto': validated_data.pop('foto', None),
        }
        password = validated_data.pop('password')

        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()

        perfil_data['is_motorista'] = (perfil_data['tipo_usuario'] == 'Motorista')
        Perfil.objects.create(usuario=user, **perfil_data)

        return user

class UserProfileSerializer(serializers.ModelSerializer):
    # podemos incluir alguns dados de leitura do usuário se quisermos exibir nome/email
    nome = serializers.CharField(source='usuario.nome', read_only=True)
    email = serializers.EmailField(source='usuario.email', read_only=True)

    class Meta:
        model = Perfil
        fields = ['id', 'nome', 'email', 'cpf', 'telefone', 'tipo_usuario', 'foto', 'is_motorista']
        read_only_fields = ['cpf', 'tipo_usuario', 'is_motorista']   # dados imutáveis normalmente