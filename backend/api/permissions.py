from rest_framework import permissions


class IsAuthorAdminOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated and (
                request.user.is_superuser or obj.author
                == request.user or request.method == 'POST'):
            return True
        return request.method in permissions.SAFE_METHODS
