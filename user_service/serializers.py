from rest_framework import serializers
from .models import Usuario


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Usuario
        fields = [
            'email', 'nome', 'cpf', 'telefone', 'tipo_usuario',
            'tipo_campus', 'foto', 'password'
        ]

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este e-mail já está cadastrado.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['is_motorista'] = (validated_data.get('tipo_usuario') == 'Motorista')
        user = Usuario.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    foto = serializers.ImageField(required=False)

    class Meta:
        model = Usuario
        fields = [
            'id', 'nome', 'email', 'cpf', 'telefone', 'tipo_usuario',
            'tipo_campus', 'foto', 'is_motorista'
        ]
        read_only_fields = ['cpf', 'tipo_usuario', 'is_motorista']

