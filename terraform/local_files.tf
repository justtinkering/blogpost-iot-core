# Write the config.ini for the sample client provided in this repository
resource "local_file" "config_ini" {
  filename = "${path.module}/../sample_client/config.ini"
  content  = <<-EOT
[DEFAULT]
endpoint = ${data.aws_iot_endpoint.current.endpoint_address}
out_cert_file = certificates/device_certificate.pem
out_key_file = certificates/device_privatekey.pem
enrollment_cert_file = certificates/iot-provisioning-certificate.pem
enrollment_key_file = certificates/iot-provisioning-privatekey.pem
root_ca = certificates/AmazonRootCA1.pem
fleet_template_name = ${aws_iot_provisioning_template.fleet.name}

EOT
}

# Write the certificates for the sample client provided in this repository
resource "local_file" "iot_provisioning_private_key" {
  filename = "${path.module}/../sample_client/certificates/iot-provisioning-privatekey.pem"
  content  = tls_private_key.provisioning.private_key_pem
}

resource "local_file" "iot_provisioning_cert" {
  filename = "${path.module}/../sample_client/certificates/iot-provisioning-certificate.pem"
  content  = tls_self_signed_cert.provisioning.cert_pem
}
