variable "name" {
  type        = string
  description = "Name to use when creating resources. Should not contain spaces."
  nullable    = false
}

variable "region" {
  type        = string
  description = "AWS Region to use for deployment."
  nullable    = false
}
