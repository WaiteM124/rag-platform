terraform {
  backend "s3" {
    key          = "envs/prod/terraform.tfstate"
    region       = "eu-west-2"
    encrypt      = true
    use_lockfile = true
  }
}
