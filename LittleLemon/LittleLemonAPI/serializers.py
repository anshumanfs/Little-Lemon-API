from rest_framework import serializers
from django.contrib.auth.models import User
from decimal import Decimal
from .models import Category, MenuItem, Cart, Order, OrderItem
from django.utils.text import slugify


class CategorySerializer(serializers.ModelSerializer):
    slug = serializers.SerializerMethodField(method_name="generateSlug", read_only=True)

    class Meta:
        model = Category
        fields = ("id", "title", "slug")

    def generateSlug(self, obj):
        return slugify(obj.title)


class MenuItemSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())

    class Meta:
        model = MenuItem
        fields = ("id", "title", "price", "featured", "category")


class CartSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), default=serializers.CurrentUserDefault()
    )

    def validate(self, data):
        if data["quantity"] < 1:
            raise serializers.ValidationError("Quantity must be greater than 0")
        data["unit_price"] = data["menuitem"].price
        data["price"] = data["unit_price"] * data["quantity"]
        return data

    class Meta:
        model = Cart
        fields = ("id", "user", "menuitem", "quantity", "unit_price", "price")
        extra_kwargs = {"unit_price": {"read_only": True}, "price": {"read_only": True}}


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("id", "order", "menuitem", "quantity", "price")


class OrderSerializer(serializers.ModelSerializer):
    orderitem = OrderItemSerializer(many=True, read_only=True, source="order")

    class Meta:
        model = Order
        fields = ("id", "user", "delivery_crew", "status", "total", "date", "orderitem")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")
