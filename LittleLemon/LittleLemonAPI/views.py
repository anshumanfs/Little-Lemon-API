from django.shortcuts import render
from rest_framework import viewsets, status, generics, permissions, response
from .permissions import (
    IsManager,
    IsDeliveryCrew,
    IsUser,
    IsManagerOrAdmin,
    IsDeliveryCrewAndAbove,
)
from .models import Category, MenuItem, Cart, Order, OrderItem
from .serializers import (
    CategorySerializer,
    MenuItemSerializer,
    CartSerializer,
    OrderSerializer,
    OrderItemSerializer,
    UserSerializer,
)
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User, Group


# Create your views here.
class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        permission_classes = []
        if self.request.method != "GET":
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]


class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    search_fields = ["category__title"]
    ordering_fields = ["price"]

    def get_permissions(self):
        permission_classes = []
        if self.request.method != "GET":
            permission_classes = [
                permissions.IsAuthenticated,
                IsManagerOrAdmin,
            ]
        return [permission() for permission in permission_classes]


class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

    def get_permissions(self):
        permission_classes = []
        if self.request.method != "GET":
            permission_classes = [
                permissions.IsAuthenticated,
                IsManagerOrAdmin,
            ]

        return [permission() for permission in permission_classes]


class CartView(generics.ListCreateAPIView):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.all().filter(user=self.request.user)

    def delete(self, *args, **kwargs):
        cart = get_object_or_404(Cart, user=self.request.user)
        cart.delete()
        return response.Response(status=status.HTTP_204_NO_CONTENT)


class OrderView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # for admin
        if self.request.user.is_superuser:
            return Order.objects.all()
        # for user
        if self.request.user.groups.count() == 0:
            return Order.objects.all().filter(user=self.request.user)
        # for delivery crew
        if self.request.user.groups.filter(name="Delivery crew").exists():
            return Order.objects.all().filter(delivery_crew=self.request.user)
        # for manager
        if self.request.user.groups.filter(name="Managers").exists():
            return Order.objects.all()

        return Order.objects.all().filter(user=self.request.user)

    def get_total_amounts(self, user):
        total_amount = 0
        items = Cart.objects.filter(user=user).all()
        for order in items:
            total_amount += order.price
        return total_amount

    def create(self, request, *args, **kwargs):
        menuitem_count = Cart.objects.all().filter(user=self.request.user).count()
        if menuitem_count == 0:
            return response.Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"message": "Cart should not be empty before placing an order"},
            )
        else:
            data = request.data.copy()
            total = self.get_total_amounts(self.request.user)
            data["total"] = total
            data["user"] = self.request.user.id
            order_serializer = OrderSerializer(data=data)
            if order_serializer.is_valid(raise_exception=True):
                order = order_serializer.save()

                items = Cart.objects.all().filter(user=self.request.user).all()

                for item in items.values():
                    orderItem = OrderItem(
                        order=order,
                        menuitem_id=item["menuitem_id"],
                        quantity=item["quantity"],
                    )
                    orderItem.save()

                Cart.objects.all().filter(
                    user=self.request.user
                ).delete()  # Delete cart items

                result = order_serializer.data.copy()
                result["total"] = total
                return response.Response(order_serializer.data)


class SingleOrderView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        if self.request.user.groups.filter(name="Delivery crew").exists():
            # delivery crew can only update status
            dataKeys = request.data.keys()
            if len(dataKeys) != 1 or "status" not in dataKeys:
                return response.Response(
                    {"message": "Only status can be updated by delivery crew"},
                    status.HTTP_400_BAD_REQUEST,
                )
        return super().update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if self.request.user.groups.filter(name="Delivery crew").exists():
            return response.Response(
                {"message": "Delivery crew can't delete order"},
                status.HTTP_403_FORBIDDEN,
            )
        else:
            return super().delete(request, *args, **kwargs)


# only managers or superuser can access this viewset
class GroupViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, IsManagerOrAdmin]

    def list(self, request):
        users = User.objects.all().filter(groups__name="Managers")
        items = UserSerializer(users, many=True)
        return response.Response(items.data)

    def create(self, request):
        user = get_object_or_404(User, username=request.data["username"])
        managers = Group.objects.get(name="Managers")
        managers.user_set.add(user)
        return response.Response({"message": "user added to the manager group"}, 201)

    # create a function to remove user from manager group by parsing id from request path
    def destroy(self, request, pk=None):
        user = get_object_or_404(User, id=pk)
        managers = Group.objects.get(name="Managers")
        managers.user_set.remove(user)
        return response.Response(
            {"message": "user removed from the manager group"}, 200
        )


# only managers or superuser can access this viewset
class DeliveryCrewViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, IsManagerOrAdmin]

    def list(self, request):
        users = User.objects.all().filter(groups__name="Delivery crew")
        items = UserSerializer(users, many=True)
        return response.Response(items.data)

    def create(self, request):
        user = get_object_or_404(User, username=request.data["username"])
        dc = Group.objects.get(name="Delivery crew")
        dc.user_set.add(user)
        return response.Response(
            {"message": "user added to the delivery crew group"}, 201
        )

    def destroy(self, request, pk=None):
        user = get_object_or_404(User, id=pk)
        dc = Group.objects.get(name="Delivery crew")
        dc.user_set.remove(user)
        return response.Response(
            {"message": "user removed from the delivery crew group"}, 200
        )
