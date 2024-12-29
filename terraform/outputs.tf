# output "sample_client_config" {
#   description = "Content for the config.ini file for the provided sample client"
#   value       = <<-EOT
# [DEFAULT]
# endpoint = ${data.aws_iot_endpoint.current.endpoint_address}
# out_cert_file = certificates/device_certificate.pem
# out_key_file = certificates/device_privatekey.pem
# enrollment_cert_file = certificates/iot-provisioning-certificate.pem
# enrollment_key_file = certificates/iot-provisioning-privatekey.pem
# root_ca = certificates/AmazonRootCA1.pem
# fleet_template_name = ${aws_iot_provisioning_template.fleet.name}

# EOT
# }
