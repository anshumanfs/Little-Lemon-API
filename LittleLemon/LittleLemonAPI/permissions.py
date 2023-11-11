from rest_framework import permissions


class IsManager(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.groups.filter(name="Managers").exists():
            return True


class IsManagerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.groups.filter(name="Managers").exists():
            return True
        if request.user.is_superuser:
            return True


class IsDeliveryCrewAndAbove(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.groups.filter(name="Managers").exists():
            return True
        if request.user.is_superuser:
            return True
        if request.user.groups.filter(name="Delivery crew").exists():
            return True


class IsDeliveryCrew(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.groups.filter(name="Delivery crew").exists():
            return True


class IsUser(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.groups.count() == 0:
            return True
