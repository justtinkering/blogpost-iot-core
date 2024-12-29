# Generate a new UUID whenever there's a change to the Lambda files
resource "random_uuid" "iot_preprovisioning" {
  keepers = {
    for filename in setunion(
      fileset("${path.module}/lambda_functions/iot_preprovisioning", "**"),
    ) :
  filename => filemd5("${path.module}/lambda_functions/iot_preprovisioning/${filename}") }
}

# Create a ZIP file containing the Lambda files
data "archive_file" "iot_preprovisioning" {
  source_dir = "${path.module}/lambda_functions/iot_preprovisioning"
  excludes = [
    "__pycache__",
    "venv",
  ]
  output_path = "${path.module}/temp/iot-preprovisioning-${random_uuid.iot_preprovisioning.result}.zip"
  type        = "zip"
}

# Create the IAM role used when running the Lambda (Lambda execution role)
resource "aws_iam_role" "iot_preprovisioning_lambda_exec" {
  name = join("-", [var.name, "iot-preprovisioning-lambda-exec"])
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Action" : "sts:AssumeRole",
        "Principal" : {
          "Service" : "lambda.amazonaws.com"
        },
        "Effect" : "Allow",
        "Sid" : ""
      }
    ]
  })
}

# Attach the managed policies to the Lambda execution role
resource "aws_iam_role_policy_attachment" "iot_preprovisioning_lambda_exec" {
  for_each   = toset(local.iot_preprovisioning_lambda_exec_managed_policies)
  role       = aws_iam_role.iot_preprovisioning_lambda_exec.name
  policy_arn = each.key
}

# Create the Lambda function
resource "aws_lambda_function" "iot_preprovisioning" {
  filename      = data.archive_file.iot_preprovisioning.output_path
  function_name = join("-", [var.name, "iot-preprovisioning"])
  role          = aws_iam_role.iot_preprovisioning_lambda_exec.arn
  handler       = "iot_preprovisioning.pre_provisioning_hook"
  runtime       = "python3.13"
  architectures = ["arm64"]
  # We're using the output_sha256 as source code hash. A lot of examples use output_base64sha256, 
  # but that value differs per system. The output_sha256 value is consistent across platforms.
  source_code_hash = data.archive_file.iot_preprovisioning.output_sha256
}

# Create the permission for IoT to invoke the pre-provisioning Lambda
resource "aws_lambda_permission" "iot_preprovisioning" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.iot_preprovisioning.function_name
  principal     = "iot.amazonaws.com"
  statement_id  = "AllowExecutionFromIot"
}
