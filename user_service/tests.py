from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from .models import Usuario  # Ajuste o import para o seu app

class GoogleLoginViewTestCase(APITestCase):
    def setUp(self):
        self.url = reverse('google-login') # Ajuste para o nome da sua rota

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_login_com_sucesso_usuario_novo(self, mock_verify_token):
        """Testa se o usuário é criado e logado com um token válido do Google"""
        
        # Simulando o que o Google retornaria se o token fosse válido
        mock_verify_token.return_value = {
            "email": "pablo.murilo10@hotmail.com",
            "email_verified": True,
            "name": "Fulano de Tal"
        }

        data = {"token": "token_falso_de_teste"}
        response = self.client.post(self.url, data, format='json')

        # Validações
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Verifica se o usuário foi realmente criado no banco
        self.assertTrue(Usuario.objects.filter(email="pablo.murilo10@hotmail.com").exists())

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_login_com_token_invalido(self, mock_verify_token):
        """Testa o comportamento quando o Google rejeita o token"""
        
        # Força a função do Google a levantar o erro que sua View espera
        mock_verify_token.side_effect = ValueError("Token Inválido")

        data = {"token": "token_expirado_ou_errado"}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Token Google inválido", response.data['detail'])

    def test_login_sem_enviar_token(self):
        """Testa a validação de campo obrigatório"""
        response = self.client.post(self.url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], "Token não informado")