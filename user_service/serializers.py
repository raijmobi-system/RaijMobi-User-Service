# from rest_framework import serializers
# from .models import Usuario


# class UserRegistrationSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, min_length=6)

#     class Meta:
#         model = Usuario
#         fields = [
#             'email', 'nome', 'cpf', 'telefone', 'tipo_usuario',
#             'tipo_campus', 'foto', 'password'
#         ]

#     def validate_email(self, value):
#         if Usuario.objects.filter(email=value).exists():
#             raise serializers.ValidationError("Este e-mail já está cadastrado.")
#         return value

#     def create(self, validated_data):
#         password = validated_data.pop('password')
#         validated_data['is_motorista'] = (validated_data.get('tipo_usuario') == 'Motorista')
#         user = Usuario.objects.create(**validated_data)
#         user.set_password(password)
#         user.save()
#         return user


# class UserProfileSerializer(serializers.ModelSerializer):
#     foto = serializers.ImageField(required=False)

#     class Meta:
#         model = Usuario
#         fields = [
#             'id', 'nome', 'email', 'cpf', 'telefone', 'tipo_usuario',
#             'tipo_campus', 'foto', 'is_motorista'
#         ]
#         read_only_fields = ['cpf', 'tipo_usuario', 'is_motorista']



# serializers.py
from rest_framework import serializers
from .models import Usuario, Perfil
from .validators import validar_cpf   

class UserRegistrationSerializer(serializers.ModelSerializer):
    # campos do Perfil que virão na requisição
    cpf = serializers.CharField(max_length=14, validators=[validar_cpf])
    telefone = serializers.CharField(max_length=15)
    tipo_usuario = serializers.ChoiceField(choices=Perfil.TIPO_CHOICES)
    foto = serializers.ImageField(required=False)

    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Usuario
        fields = ['email', 'nome', 'password', 'cpf', 'telefone', 'tipo_usuario', 'tipo_campus', 'foto']

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este e-mail já está cadastrado.")
        return value

    def create(self, validated_data):
        # extrai os campos do Perfil
        perfil_data = {
            'cpf': validated_data.pop('cpf'),
            'telefone': validated_data.pop('telefone'),
            'tipo_usuario': validated_data.pop('tipo_usuario'),
            'tipo_campus': validated_data.pop('tipo_campus'),
            'foto': validated_data.pop('foto', None),
        }
        password = validated_data.pop('password')

        # cria o usuário
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()

        # define is_motorista automaticamente
        perfil_data['is_motorista'] = (perfil_data['tipo_usuario'] == 'Motorista')

        # cria o perfil vinculado
        Perfil.objects.create(usuario=user, **perfil_data)

        return user
    
class UserProfileSerializer(serializers.ModelSerializer):
    # podemos incluir alguns dados de leitura do usuário se quisermos exibir nome/email
    nome = serializers.CharField(source='usuario.nome', read_only=True)
    email = serializers.EmailField(source='usuario.email', read_only=True)

    class Meta:
        model = Perfil
        fields = ['id', 'nome', 'email', 'cpf', 'telefone', 'tipo_usuario', 'tipo_campus', 'foto', 'is_motorista']
        read_only_fields = ['cpf', 'tipo_usuario', 'is_motorista']   # dados imutáveis normalmente