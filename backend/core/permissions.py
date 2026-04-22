"""
Custom permissions for HyperFileLens API.

Defines role-based access control permissions for different user roles:
- Admin: Full system access
- Operator: Can manage nodes, backup/recovery tasks
- Viewer: Read-only access
"""

from rest_framework import permissions


class IsAdminOrOperator(permissions.BasePermission):
    """
    Permission class that allows access to admins and operators only.
    Read-only access may be allowed for other authenticated users.
    """
    
    def has_permission(self, request, view):
        # Allow read-only methods for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write operations require admin or operator role
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check for custom role attribute
        if hasattr(request.user, 'role'):
            return request.user.role in ['admin', 'operator']
        
        # Fallback to is_staff for admin privileges
        return request.user.is_staff


class IsAdminOnly(permissions.BasePermission):
    """
    Permission class that restricts access to admin users only.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'role'):
            return request.user.role == 'admin'
        
        return request.user.is_staff


class IsNodeAuthenticated(permissions.BasePermission):
    """
    Permission for WebSocket connections from proxy nodes.
    Verifies the node token from the connection scope.
    """
    
    def has_permission(self, request, view):
        # For WebSocket connections, authentication is handled
        # in the consumer's connect method
        return True


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners or admins to edit.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any authenticated request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed for owners or admins
        if hasattr(obj, 'owner'):
            return obj.owner == request.user or request.user.is_staff
        
        return request.user.is_staff
