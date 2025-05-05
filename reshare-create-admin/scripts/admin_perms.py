import json
import os
import requests
import uuid
from jinja2 import Environment, FileSystemLoader


okapi_host = os.environ.get("OKAPI_HOST")
tenant_id = os.environ.get("TENANT_ID")
admin_user = tenant_id + '_admin'
admin_password = os.environ.get("ADMIN_PASSWORD")

print(f"OKAPI Host: {okapi_host}")


def check_admin_user(okapi, tenant, admin_user):
    headers = {
        "x-okapi-tenant": tenant,
        "Content-Type": "application/json"
    }

    url = f"{okapi}/users?query=username=={admin_user}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        users = data.get("users", [])
        if users:
            return users[0].get("id")
        else:
            return False
    
def check_admin_perms(okapi, tenant, admin_id):
    headers = {
        "x-okapi-tenant": tenant,
        "Content-Type": "application/json"
    }

    url = f"{okapi}/perms/users?query=userId=={admin_id}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        permissions = data.get("permissionUsers", [])
        if permissions:
            return permissions[0].get("id")
        else:
            return False

def okapi_post_noat(url, tenant, data):
    headers = {
        "x-okapi-tenant": tenant,
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()

def okapi_put_noat(url, tenant, data):
    headers = {
        "x-okapi-tenant": tenant,
        "Content-Type": "application/json"
    }

    response = requests.put(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()

def okapi_get_noat(url, tenant):
    headers = {
        "x-okapi-tenant": tenant,
        "Content-Type": "application/json"
    }

    response = requests.put(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()

def main():
    # setup
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(script_dir, '..', 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    # does an admin user already exist
    admin_id = check_admin_user(okapi_host, tenant_id, admin_user)
    if admin_user:
        # there is already an admin user, make sure its up to date
        existing_perms_id = check_admin_perms(okapi_host, tenant_id, admin_id)
        if existing_perms_id is False:
            # there are no permissions, create them
            template = env.get_template('admin_perms.json.j2')
            perms_id = new_id = str(uuid.uuid4())
            data = template.render(admin_id=admin_id, perms_id=perms_id)
            new_perms = okapi_post_noat(okapi_host + '/perms/users', tenant_id, data)
        else:
            # there are existing perms, update them
            perms_id = existing_perms_id
            data = template.render(admin_id=admin_id, perms_id=perms_id)
            new_perms = okapi_put_noat(okapi_host + '/perms/users/' + perms_id, tenant_id, data)

            
    else: 
        # there is no admin user, create one
        admin_id = new_id = str(uuid.uuid4())
        template = env.get_template('admin_user.json.j2')
        data = template.render(admin_id=admin_id, tenant_id=tenant_id)
        new_user = okapi_post_noat(okapi_host + '/users', tenant_id, data)

        # now perms
        template = env.get_template('admin_perms.json.j2')
        perms_id = new_id = str(uuid.uuid4())
        data = template.render(admin_id=admin_id, perms_id=perms_id)
        new_perms = okapi_post_noat(okapi_host + '/perms/users', tenant_id, data)

    # always try and create credentials
    template = env.get_template('admin_creds.json.j2')
    data = template.render(tenant_id=tenant_id, admin_password=admin_password)
    try:
        new_creds = okapi_post_noat(url, tenant_id, data)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            error_json = e.response.json()
            errors = error_json.get("errors", [])
            if any("already exists" in err.get("message", "").lower() for err in errors):
                print("Credentials already exist — treating as success.")
            else:
                print("422 returned, but message is unexpected.")
                raise
        else:
            raise 

if __name__ == "__main__":
    main()
