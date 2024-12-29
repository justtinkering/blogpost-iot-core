import json


def pre_provisioning_hook(event, context):
    print(event)

    # You can put code here to check if a device trying to connect
    # should be allowed or not, like checking if any of the provided
    # attributes are valid.
    # This function has to be able to respond within 5 seconds,
    # otherwise the provisioning request fails.
    # Reference: https://docs.aws.amazon.com/iot/latest/developerguide/pre-provisioning-hook.html

    # If you want to allow the device to connect to IoT Core, return this:
    # 'allowProvisioning': True

    # If you want to disallow the device to connect to IoT Core, return this:
    # 'allowProvisioning': False
    return {
        'allowProvisioning': True
    }
