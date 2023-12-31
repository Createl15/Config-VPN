from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from apps.authentication import jwt_auth_check
from .serializer import *
from .models import *

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import random, string, subprocess

class AuthToken(APIView):
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

    def post(self, request):
        username = request.data.get('login')
        password = request.data.get('password')

        if not username or not password:
            return Response({"error": "Username and password are required."})

        user = authenticate(username=username, password=password)
        if not user:
            return Response({"error": "Invalid credentials."})

        token = get_tokens_for_user(user)
        serializer = UserSerializer(user)
        return Response({"user": {"last_login": serializer.data.get("last_login"), "email": serializer.data.get("email")}, "refresh_token": token['refresh'], "access_token": token['access']})
    
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class Logout(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class ServerDetail(APIView):

    @jwt_auth_check
    def get(self, _):
        serializer = ServerSerializer(Server.objects.all(), many=True)
        return JsonResponse(serializer.data, safe=False)
    
    @jwt_auth_check
    def post(self, request):
        _id = request.data.get('_id')
        ip = request.data.get('ip')
        port_ssh = request.data.get('port_ssh')
        username = request.data.get('username')
        password = request.data.get('password')
        suCommand = request.data.get('suCommand')
        serverUsername = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        serverPassword = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=12))
        port_WG = str(random.randint(1024, 65535))

        command = [
            'bash',
            'core/backend/scripts/installing.sh',
            ip,
            port_ssh,
            port_WG,
            username,
            password,
            suCommand,
            'not_vpn_at_all',
            serverUsername,
            serverPassword,
        ]

        subprocess.run(command)

        public_key = 1
        statusServer = False
        statusWG = False

        # Спарсим данные, такие как publicKey, состояние WG, состояние сервера
        # Сохраняем данные в базу данных
        server = Server(_id=_id, ip=ip, portSSH=port_ssh, portWG = port_WG, publicKey = public_key, statusServer = statusServer, statusWG = statusWG)
        server.save()

        return Response({"status": "ok"})
    
    @jwt_auth_check
    def delete(self, request):
        # Получаем данные от фронтенда, например, id сервера, suCommand, suPassword
        server_id = request.data.get('server_id')
        su_command = request.data.get('suCommand')
        su_password = request.data.get('suPassword')
        username = request.data.get('username')
        password = request.data.get('password')

        # Находим объект сервера в базе данных
        server = get_object_or_404(Server, pk=server_id)

        # Выполняем проверки возможности выполнения операции (можно использовать, например, suCommand и suPassword для проверки привилегий)
        # Выполняем скрипт с требуемыми параметрами и получаем статус выполнения
        # Удаляем из базы данных всех пользователей, связанных с этим сервером, и сам сервер
        server_users = ServerUser.objects.filter(server=server)
        for user in server_users:
            user.delete()
        server.delete()

        return Response({"status": "ok"})
    
class UserDetail(APIView):

    @jwt_auth_check
    def get(self, _):
        serializer = UserSerializer(User.objects.all(), many=True)
        return JsonResponse(serializer.data, safe=False)
    
    @jwt_auth_check
    def post(self, request):
        _id = request.data.get('_id')
        port_ssh = request.data.get('port_ssh')
        port_WG = request.data.get('port_WG')
        username = request.data.get('username')
        password = request.data.get('password')
        vpnip = request.data.get('vpnip')
        server_publickey = request.data.get('server_publickey')

        ip = 

        command = [
            'bash',
            'core/backend/scripts/addUser.sh',
            ip,
            port_ssh,
            port_WG,
            username,
            password,
            _id,
            vpnip,
            server_publickey
        ]

        subprocess.run(command)

        #Cпарсить publicKey для клиента, состояние сервера, состояние WG и сохранить необходимые данные по полям.

        # statusServer = statusServer
        # statusWG = statusWG
        #portWG = port_WG
        # portSSH=port_ssh

        user = Server(_id=_id, ip=ip, username = username, publicKey = public_key)
        user.save()

        return Response({"status": "ok"})
    
    @jwt_auth_check
    def delete(self, request):
        # Получаем данные от фронтенда, например, id сервера и id пользователя
        server_id = request.data.get('server_id')
        user_id = request.data.get('user_id')
        server = get_object_or_404(Server, pk=server_id)
        user = get_object_or_404(User, pk=user_id)

        # Проверяем возможность операции и выполняем скрипт deleteUser.sh с требуемыми параметрами
        # Дожидаемся завершения выполнения скрипта и получаем результаты (например, 3 параметра)
        # В зависимости от состояния сервера и статуса операции, удаляем или сохраняем данные в базе данных
        # Возвращаем статус фронтенду
        return Response({"status": "ok"})


class ServerStatus(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        # Получаем данные от фронтенда, например, id сервера
        server_id = request.data.get('server_id')

        # Находим объект сервера и связанных с ним пользователей в базе данных
        server = get_object_or_404(Server, pk=server_id)
        server_users = ServerUser.objects.filter(server=server)

        # Выполняем скрипт status.sh с требуемыми параметрами
        # Парсим данные, такие как статус сервера, загрузка CPU, статус VPN, последний онлайн пользователя и т. д.
        # Сохраняем и выводим необходимые данные на фронтенд
        # Проверяем список клиентов и обновляем базу данных в соответствии с результатами
        # ...
        # Возвращаем статус фронтенду
        return Response({"status": "ok"})
