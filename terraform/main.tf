# Create the IoT provisioning IAM role
resource "aws_iam_role" "iot_fleet_provisioning" {
  name = join("-", [var.name, "fleet-provisioning-role"])

  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "iot.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
}

# Attach the managed role for registering Things to the provisioning role
resource "aws_iam_role_policy_attachment" "iot_fleet_provisioning" {
  role       = aws_iam_role.iot_fleet_provisioning.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSIoTThingsRegistration"
}

# Ensure that these (managed) policies are the only ones attached to the provisioning role on every apply
resource "aws_iam_role_policy_attachments_exclusive" "iot_fleet_provisioning" {
  role_name = aws_iam_role.iot_fleet_provisioning.name
  policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AWSIoTThingsRegistration",
  ]
}

# Create a device policy
resource "aws_iot_policy" "iot_device" {
  name = join("-", [var.name, "device-policy"])

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "iot:Publish",
          "iot:Receive"
        ],
        "Resource" : [
          "arn:aws:iot:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:topic/$${iot:Connection.Thing.ThingName}/*",
        ]
      },
      {
        "Effect" : "Allow",
        "Action" : "iot:Subscribe",
        "Resource" : [
          "arn:aws:iot:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:topicfilter/$aws/things/$${iot:Connection.Thing.ThingName}/shadow/*",
        ]
      },
      {
        "Condition" : {
          "Bool" : {
            "iot:Connection.Thing.IsAttached" : [
              "true"
            ]
          }
        },
        "Effect" : "Allow",
        "Action" : "iot:Connect",
        "Resource" : "*"
      }
    ]
  })
}

# Create a Thing group
resource "aws_iot_thing_group" "provisioning" {
  name = "Provisioning"
}

# Create a Thing type
# The delete process of these is that they'll be deprecated first,
# and 5 minutes later they can be deleted.
resource "aws_iot_thing_type" "example" {
  name = "Example"

  properties {
    description = "Example"
    searchable_attributes = [
      # There's a maximum of 3 searchable attributes per Thing Type
      "environment",
      "license",
    ]
  }
}

# Create the fleet provisioning template
resource "aws_iot_provisioning_template" "fleet" {
  name                  = join("-", [var.name, "fleet-provisioning-tpl"])
  description           = "Fleet provisioning template for ${var.name}"
  provisioning_role_arn = aws_iam_role.iot_fleet_provisioning.arn
  enabled               = true

  template_body = jsonencode({
    "DeviceConfiguration" : {},
    "Parameters" : {
      "License" : {
        "Type" : "String"
      },
      "AWS::IoT::Certificate::Id" : {
        "Type" : "String"
      }
    },
    "Resources" : {
      "policy" : {
        "Type" : "AWS::IoT::Policy",
        "Properties" : {
          "PolicyName" : aws_iot_policy.iot_device.name
        }
      },
      "certificate" : {
        "Type" : "AWS::IoT::Certificate",
        "Properties" : {
          "CertificateId" : {
            "Ref" : "AWS::IoT::Certificate::Id"
          },
          "Status" : "Active"
        }
      },
      "thing" : {
        "Type" : "AWS::IoT::Thing",
        "OverrideSettings" : {
          "AttributePayload" : "MERGE",
          "ThingGroups" : "REPLACE",
          "ThingTypeName" : "REPLACE"
        },
        "Properties" : {
          "AttributePayload" : {
            "license" : { "Ref" : "License" },
          },
          "ThingGroups" : [
            aws_iot_thing_group.provisioning.name
          ],
          "ThingTypeName" : aws_iot_thing_type.example.name,
          "ThingName" : {
            "Fn::Join" : [
              "-",
              [
                "iot",
                {
                  "Ref" : "License"
                }
              ]
            ]
          }
        }
      }
    }
  })

  pre_provisioning_hook {
    target_arn      = aws_lambda_function.iot_preprovisioning.arn
    payload_version = "2020-04-01"
  }
}

# Create the claims provisioning certificate policy
resource "aws_iot_policy" "provisioning" {
  name = join("-", [var.name, "claim-certificate-policy"])

  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : "iot:Connect",
        "Resource" : "*"
      },
      {
        "Effect" : "Allow",
        "Action" : [
          "iot:Publish",
          "iot:Receive"
        ],
        "Resource" : [
          "arn:aws:iot:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:topic/$aws/certificates/create/*",
          "arn:aws:iot:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:topic/$aws/provisioning-templates/${aws_iot_provisioning_template.fleet.name}/provision/*"
        ]
      },
      {
        "Effect" : "Allow",
        "Action" : "iot:Subscribe",
        "Resource" : [
          "arn:aws:iot:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:topicfilter/$aws/certificates/create/*",
          "arn:aws:iot:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:topicfilter/$aws/provisioning-templates/${aws_iot_provisioning_template.fleet.name}/provision/*"
        ]
      }
    ]
  })
}

# Create a self-signed provisioning certificate
resource "tls_private_key" "provisioning" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_self_signed_cert" "provisioning" {
  private_key_pem = tls_private_key.provisioning.private_key_pem

  subject {
    common_name = "IoT Provisioning"
  }

  validity_period_hours = 8760 # 365 days

  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "server_auth",
  ]
}

# Add the provisioning certificate and attach the provisioning policy
resource "aws_iot_certificate" "iot_fleet_provisioning" {
  certificate_pem = tls_self_signed_cert.provisioning.cert_pem
  active          = true
}

resource "aws_iot_policy_attachment" "iot_fleet_provisioning_certificate" {
  policy = aws_iot_policy.provisioning.name
  target = aws_iot_certificate.iot_fleet_provisioning.arn
}

# Manage events that will publish messages to MQTT topics.
# Reference: https://docs.aws.amazon.com/iot/latest/developerguide/iot-events.html#iot-events-enable
resource "aws_iot_event_configurations" "this" {
  event_configurations = {
    "THING"                  = true,
    "THING_GROUP"            = false,
    "THING_TYPE"             = false,
    "THING_GROUP_MEMBERSHIP" = false,
    "THING_GROUP_HIERARCHY"  = false,
    "THING_TYPE_ASSOCIATION" = false,
    "JOB"                    = false,
    "JOB_EXECUTION"          = false,
    "POLICY"                 = false,
    "CERTIFICATE"            = false,
    "CA_CERTIFICATE"         = false,
  }
}
