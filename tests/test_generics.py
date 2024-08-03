from asgiref.sync import async_to_sync
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory

from adrf import generics, serializers

from .models import Order, User

factory = APIRequestFactory()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username",)


class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class ListUserView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class RetrieveUserView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class DestroyUserView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UpdateUserView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class TestCreateUserView(TestCase):
    def setUp(self):
        self.view = CreateUserView.as_view()

    def test_post_succeeds(self):
        request = factory.post("/", {"username": "test"})
        response = async_to_sync(self.view)(request)
        expected = {"username": "test"}
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data == expected


class TestListUserView(TestCase):
    def setUp(self):
        self.view = ListUserView.as_view()

    def test_get_no_users(self):
        request = factory.get("/")
        response = async_to_sync(self.view)(request)
        expected = []
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected

    def test_get_one_user(self):
        User.objects.create(username="test")
        request = factory.get("/")
        response = async_to_sync(self.view)(request)
        expected = [{"username": "test"}]
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected


class TestRetrieveUserView(TestCase):
    def setUp(self):
        self.view = RetrieveUserView.as_view()

    def test_get_no_users(self):
        request = factory.get("/")
        response = async_to_sync(self.view)(request, pk=1)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_one_user(self):
        user = User.objects.create(username="test")
        request = factory.get("/")
        response = async_to_sync(self.view)(request, pk=user.id)
        expected = {"username": "test"}
        assert response.status_code == status.HTTP_200_OK
        assert response.data == expected


class TestDestroyUserView(TestCase):
    def setUp(self):
        self.view = DestroyUserView.as_view()

    def test_delete_no_users(self):
        request = factory.delete("/")
        response = async_to_sync(self.view)(request, pk=1)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_one_user(self):
        user = User.objects.create(username="test")
        Order.objects.create(name="Test order", user=user)
        request = factory.delete("/")
        response = async_to_sync(self.view)(request, pk=user.id)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Order.objects.exists()


class TestUpdateUserView(TestCase):
    def setUp(self):
        self.view = UpdateUserView.as_view()

    def test_update_user(self):
        user = User.objects.create(username="test")
        request = factory.put("/", data={"username": "not-test"})
        response = async_to_sync(self.view)(request, pk=user.id)
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.username == "not-test"
