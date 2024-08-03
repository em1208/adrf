from collections import ChainMap

from asgiref.sync import sync_to_async
from django.test import TestCase
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from adrf.serializers import ModelSerializer, Serializer

from .models import Order, User

factory = APIRequestFactory()


class MockObject:
    def __init__(self, **kwargs):
        self._kwargs = kwargs
        self.pk = kwargs.get("pk", None)

        for key, val in kwargs.items():
            setattr(self, key, val)


class TestSerializer(TestCase):
    def setUp(self):
        class SimpleSerializer(Serializer):
            username = serializers.CharField()
            password = serializers.CharField()
            age = serializers.IntegerField()

        class CrudSerializer(Serializer):
            username = serializers.CharField()
            password = serializers.CharField()
            age = serializers.IntegerField()

            async def acreate(self, validated_data):
                return MockObject(**validated_data)

            async def aupdate(self, instance, validated_data):
                return MockObject(**validated_data)

        self.simple_serializer = SimpleSerializer
        self.crud_serializer = CrudSerializer

        self.default_data = {
            "username": "test",
            "password": "test",
            "age": 25,
        }
        self.default_object = MockObject(**self.default_data)

    async def test_serializer_valid(self):
        data = {
            "username": "test",
            "password": "test",
            "age": 10,
        }
        serializer = self.simple_serializer(data=data)
        assert serializer.is_valid()
        assert await serializer.adata == data
        assert serializer.errors == {}

    async def test_serializer_invalid(self):
        data = {
            "username": "test",
            "password": "test",
        }
        serializer = self.simple_serializer(data=data)

        assert not serializer.is_valid()
        assert serializer.validated_data == {}
        assert await serializer.adata == data
        assert serializer.errors == {"age": ["This field is required."]}

    async def test_many_argument(self):
        data = [
            {
                "username": "test",
                "password": "test",
                "age": 10,
            }
        ]
        serializer = self.simple_serializer(data=data, many=True)

        assert serializer.is_valid()
        assert serializer.validated_data == data
        assert await serializer.adata == data

    async def test_invalid_datatype(self):
        data = [
            {
                "username": "test",
                "password": "test",
                "age": 10,
            }
        ]
        serializer = self.simple_serializer(data=data)

        assert not serializer.is_valid()
        assert serializer.validated_data == {}
        assert await serializer.adata == {}

        assert serializer.errors == {
            "non_field_errors": ["Invalid data. Expected a dictionary, but got list."]
        }

    async def test_partial_validation(self):
        data = {
            "username": "test",
            "password": "test",
        }
        serializer = self.simple_serializer(data=data, partial=True)

        assert serializer.is_valid()
        assert serializer.validated_data == data
        assert serializer.errors == {}

    async def test_serialize_chainmap(self):
        data = {"username": "test"}, {"password": "test"}, {"age": 10}

        serializer = self.simple_serializer(data=ChainMap(*data))

        assert serializer.is_valid()
        assert serializer.validated_data == {
            "username": "test",
            "password": "test",
            "age": 10,
        }
        assert serializer.errors == {}

    async def test_crud_serializer_create(self):
        # Create a valid data payload
        data = self.default_data

        # Create an instance of the serializer
        serializer = self.crud_serializer(data=data)

        assert serializer.is_valid()

        # Create the object
        created_object = await serializer.acreate(serializer.validated_data)

        # Verify the object has been created successfully
        assert isinstance(created_object, MockObject)

        # Verify the object has the correct data
        assert created_object.username == data["username"]
        assert created_object.password == data["password"]
        assert created_object.age == data["age"]

    async def test_crud_serializer_update(self):
        # Create a valid data payload
        default_object = self.default_object
        data = {
            "username": "test2",
            "password": "test2",
            "age": 30,
        }

        # Update the object using the serializer
        serializer = self.crud_serializer(default_object, data=data)

        assert serializer.is_valid()

        # Update the object
        updated_object = await serializer.aupdate(
            default_object, serializer.validated_data
        )

        # Verify the object has been updated successfully
        assert isinstance(updated_object, MockObject)
        assert updated_object.username == data["username"]
        assert updated_object.password == data["password"]
        assert updated_object.age == data["age"]

    # test asave
    async def test_crud_serializer_save(self):
        # Create a valid data payload
        data = self.default_data

        # Create an instance of the serializer
        serializer = self.crud_serializer(data=data)

        assert serializer.is_valid()

        # Create the object
        created_object = await serializer.asave()

        # Verify the object has been created successfully
        assert isinstance(created_object, MockObject)

        # Verify the object has the correct data
        assert created_object.username == data["username"]
        assert created_object.password == data["password"]
        assert created_object.age == data["age"]

    async def test_crud_serializer_to_representation(self):
        # Create a valid data payload
        default_object = self.default_object

        # Update the object using the serializer
        serializer = self.crud_serializer(default_object)

        # Update the object
        representation = await serializer.ato_representation(default_object)

        # Verify the object has been updated successfully
        assert isinstance(representation, dict)
        assert representation["username"] == default_object.username
        assert representation["password"] == default_object.password
        assert representation["age"] == default_object.age

    # test that normal non-async serializers work
    def test_sync_serializer_valid(self):
        data = {
            "username": "test",
            "password": "test",
            "age": 10,
        }
        serializer = self.simple_serializer(data=data)
        assert serializer.is_valid()
        assert serializer.data == data
        assert serializer.errors == {}


class TestModelSerializer(TestCase):
    def setUp(self) -> None:
        class UserSerializer(ModelSerializer):
            class Meta:
                model = User
                fields = ("username",)

        class OrderSerializer(ModelSerializer):
            class Meta:
                model = Order
                fields = ("id", "user", "name")

        self.user_serializer = UserSerializer
        self.order_serializer = OrderSerializer

    async def test_user_serializer_valid(self):
        data = {
            "username": "test",
        }
        serializer = self.user_serializer(data=data)
        assert await sync_to_async(serializer.is_valid)()
        assert await serializer.adata == data
        assert serializer.errors == {}

    async def test_order_serializer_valid(self):
        user = await User.objects.acreate(username="test")
        data = {"user": user.id, "name": "Test order"}
        serializer = self.order_serializer(data=data)
        assert await sync_to_async(serializer.is_valid)()
        assert await serializer.adata == data
        assert serializer.errors == {}
