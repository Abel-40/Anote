import yaml
from sqlalchemy.orm import Session
from sqlalchemy import select
from db_connection import engine
from db_models import User,Note,Role,Permission


PERMISSION_REGISTRY = {
    "users": [
        "read",
        "create",
        "update",
        "delete",
        "assign_role",   # admin-level
    ],

    "notes": [
        "read",
        "create",
        "update",
        "delete",
    ],

    "tags": [
        "read",
        "create",
        "update",
        "delete",
    ],

    "files": [
        "read",
        "upload",
        "delete",
    ],

    "roles": [
        "read",
        "create",
        "update",
        "delete",
    ],

    "permissions": [
        "read",
        "create",
        "update",
        "delete",
    ],
}

def permission_genrator():
  permissions = []
  for model, actions in PERMISSION_REGISTRY.items():
    for action in actions:
      permissions.append(f"{model}:{action}")
  return permissions

def seed_permissions(session:Session):
  existing_permission = set(session.scalars(select(Permission.name)).all())
  new_permissions = [Permission(name = permission_name) for permission_name in permission_genrator() if permission_name not in existing_permission]
  
  if new_permissions:
    session.add_all(new_permissions)
    session.commit()
    return True
  return False


def assign_permission(session:Session):
  with open("conf/role_permissions.yaml") as f:
    data = yaml.safe_load(f)
  

  for role_name, role_data in data["roles"].items():
    role = session.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
    print(f"ROLE NAME --> {role_name}")
    if not role:
      role = Role(name = role_name)
      session.add(role)
    role.permissions.clear()
    for permission_name in role_data["permissions"]:
      permission = session.execute(select(Permission).where(Permission.name == permission_name)).scalar_one_or_none()
      print(f"PERMISSION_NAME --> {permission_name}")
      if "*" in permission_name:
        like_perm = permission_name.replace("*", "%")
        permission = session.execute(select(Permission).where(Permission.name.like(like_perm))).scalars().all()
      else:
        permission = [session.execute(select(Permission).where(Permission.name == permission_name)).scalar_one()]
      role.permissions.extend(permission)
  session.commit()